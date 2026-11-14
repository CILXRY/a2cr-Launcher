"""a2cr Launcher 的图形界面（Flet）。

界面层只调用 services 里的函数，不碰 core / meta / launch 的细节。
所有耗时操作都放进 asyncio.to_thread；工作线程只写队列/状态，界面在事件循环
里用定时 pump 更新控件。
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import flet as ft

from a2cr_launcher import services

from . import components as ui
from . import theme
from .dialogs import ImportDialog, show_error
from .state import GameSession, LogBus, StdoutTee, TaskState
from .utils import format_duration
from .views import home, instances, logs, settings as settings_view, versions

NAV_ITEMS = (
    ("home", "首页", ft.Icons.HOME_ROUNDED, ft.Icons.HOME_OUTLINED),
    ("instances", "实例", ft.Icons.VIEW_IN_AR_ROUNDED, ft.Icons.VIEW_IN_AR_OUTLINED),
    ("versions", "版本", ft.Icons.LAYERS_ROUNDED, ft.Icons.LAYERS_OUTLINED),
    ("logs", "日志", ft.Icons.TERMINAL_ROUNDED, ft.Icons.TERMINAL_OUTLINED),
    ("settings", "设置", ft.Icons.SETTINGS_ROUNDED, ft.Icons.SETTINGS_OUTLINED),
)

APP_VERSION = "0.3.0"


class LauncherApp:
    """把页面、后台任务、日志和游戏会话粘在一起的应用对象。"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.settings = services.load_settings()
        self.p = self._palette_for(self.settings.get("theme", "dark"))
        ui.set_palette(self.p)

        self.log_bus = LogBus()
        self.log_entries: list = []
        self.instances: list[dict] = []
        self.installed_versions: list[dict] = []
        self.java_runtimes: list[dict] = []
        self.remote_versions: list[dict] = []
        self.version_filter = "release"
        self.version_search = ""
        self.version_loading = False
        self.version_error = ""
        self.instances_loading = True
        self.task: TaskState | None = None
        self.session: GameSession | None = None
        self.current_page = "home"
        self.compact = False
        self.logs_page = None
        self.file_picker = ft.FilePicker()
        self.clipboard = ft.Clipboard()
        self.nav_controls: dict[str, tuple[ft.Container, ft.Container, ft.Icon, ft.Text]] = {}
        self._started = False
        self._stdout_tee = None
        self._task_hide_at = 0.0
        self._session_cleanup = False
        self._session_had_process = False

        self._configure_page()
        self._build_shell()

        # FilePicker / Clipboard 是 Service，需要挂到 page 上才能调用
        page.services.append(self.file_picker)
        page.services.append(self.clipboard)
        page.on_resize = self._on_resize
        page.on_close = self._on_close
        page.on_error = self._on_error

        # 让 core 里所有 print 都能进日志面板；退出时恢复
        self._stdout_tee = StdoutTee(sys.stdout, lambda text: self.log_bus.push(text, "系统"))
        sys.stdout = self._stdout_tee

        page.run_task(self._startup)

    # ---------- 初始化 ----------
    def _palette_for(self, mode: str) -> theme.Palette:
        if mode == "light":
            return theme.LIGHT
        if mode == "system":
            # 系统主题在 page 挂载后才拿到亮度；拿不到时保持深色，避免闪白
            brightness = getattr(self.page, "platform_brightness", None)
            if "light" in str(brightness).lower():
                return theme.LIGHT
        return theme.DARK

    def _configure_page(self) -> None:
        page = self.page
        page.title = "a2cr Launcher"
        page.padding = 0
        page.spacing = 0
        page.window.width = self.settings.get("window_width", 1180)
        page.window.height = self.settings.get("window_height", 760)
        page.window.min_width = 960
        page.window.min_height = 640
        page.window.bgcolor = self.p.bg
        page.bgcolor = self.p.bg
        page.theme_mode = self._theme_mode()
        page.theme = theme.theme_for(theme.LIGHT)
        page.dark_theme = theme.theme_for(theme.DARK)

    def _theme_mode(self) -> ft.ThemeMode:
        mode = self.settings.get("theme", "dark")
        return {
            "dark": ft.ThemeMode.DARK,
            "light": ft.ThemeMode.LIGHT,
            "system": ft.ThemeMode.SYSTEM,
        }.get(mode, ft.ThemeMode.DARK)

    async def _startup(self) -> None:
        """创建目录并加载数据。issue #4：目录不存在时给出可操作提示，而不是崩溃。"""
        if self._started:
            return
        try:
            await asyncio.to_thread(services.ensure_data_dirs)
        except Exception as exc:
            self.content.content = self._fatal_page(exc)
            self.page.update()
            return

        self._started = True
        try:
            self.page.window.center()
        except Exception:
            # 某些平台/旧客户端没有 center，不影响主流程
            pass
        # 系统主题要等窗口真正连上客户端后才知道当前是深色还是浅色
        if self.settings.get("theme") == "system" and self._palette_for("system").name != self.p.name:
            self.p = self._palette_for("system")
            ui.set_palette(self.p)
            self._build_shell()
        self.navigate("home")
        self.log_bus.push("[启动器] 界面已启动", "启动器")
        self.page.run_task(self._pump_logs)
        self.page.run_task(self._pump_tasks)
        self.page.run_task(self._pump_session)
        await self.refresh_all()
        self.log_bus.push(
            f"[启动器] 已加载 {len(self.instances)} 个实例、"
            f"{len(self.installed_versions)} 个版本、{len(self.java_runtimes)} 个 Java",
            "启动器",
        )

    def _fatal_page(self, exc: Exception) -> ft.Control:
        """数据目录不可写时的兜底页，告诉用户具体路径和错误。"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.FOLDER_OFF_ROUNDED, size=40, color=self.p.danger),
                        width=84, height=84, border_radius=26, bgcolor=self.p.surface_hi,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text("无法初始化启动器目录", size=22, weight=ft.FontWeight.W_700,
                            color=self.p.text),
                    ft.Text("请检查磁盘空间、目录权限，或安全软件是否拦截了写入。",
                            size=13, color=self.p.text_muted, text_align=ft.TextAlign.CENTER),
                    ft.Text(str(exc), size=11, font_family="Consolas", color=self.p.danger,
                            selectable=True, text_align=ft.TextAlign.CENTER),
                    ui.tonal_button("重试", lambda e: self.page.run_task(self._startup),
                                    icon=ft.Icons.REFRESH_ROUNDED),
                ],
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=40,
        )

    # ---------- 壳与导航 ----------
    def _build_shell(self) -> None:
        self.p = self._palette_for(self.settings.get("theme", "dark"))
        ui.set_palette(self.p)
        self.sidebar = self._build_sidebar()
        self.content = ft.AnimatedSwitcher(
            content=ft.Container(),
            duration=200,
            reverse_duration=120,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            transition=ft.AnimatedSwitcherTransition.FADE,
            expand=True,
        )
        content_wrap = ft.Container(
            content=self.content,
            expand=True,
            padding=ft.Padding.only(left=28, right=28, top=24, bottom=18),
        )
        body = ft.Row(
            controls=[self.sidebar, content_wrap],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.footer = ft.Column(controls=[], spacing=0)
        self.root = ft.Container(
            content=ft.Column(controls=[body, self.footer], spacing=0, expand=True),
            expand=True,
            bgcolor=self.p.bg,
        )
        self.page.controls.clear()
        self.page.add(self.root)
        self._rebuild_footer()

    def _build_sidebar(self) -> ft.Container:
        p = self.p
        logo = ft.Row(
            controls=[
                ui.block_logo(36),
                ft.Column(
                    controls=[
                        ft.Text("a2Cr", size=19, weight=ft.FontWeight.W_800, color=p.text),
                        ft.Text("Launcher", size=10, color=p.text_faint),
                    ],
                    spacing=-2,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.logo_text = logo.controls[1]

        nav_controls = []
        for key, label, active_icon, inactive_icon in NAV_ITEMS:
            indicator = ft.Container(width=3, height=18, bgcolor="transparent", border_radius=2)
            icon = ft.Icon(inactive_icon, size=19, color=p.text_muted)
            text = ft.Text(label, size=13, color=p.text_muted, weight=ft.FontWeight.W_500)
            row = ft.Row(
                controls=[indicator, icon, text],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            item = ft.Container(
                content=row,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                border_radius=12,
                on_click=lambda e, target=key: self.navigate(target),
                on_hover=lambda e, target=key: self._nav_hover(target, e),
                animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            )
            self.nav_controls[key] = (item, indicator, icon, text)
            nav_controls.append(item)

        bottom = ft.Column(
            controls=[
                ft.Container(height=1, bgcolor=p.border, margin=ft.Margin.symmetric(vertical=10)),
                ft.Row(
                    controls=[
                        ui.icon_action(ft.Icons.DARK_MODE_ROUNDED, "切换主题",
                                       lambda e: self.cycle_theme()),
                    ],
                ),
                ft.Text(f"v{APP_VERSION}", size=10, color=p.text_faint),
            ],
            spacing=6,
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    logo,
                    ft.Container(height=18),
                    *nav_controls,
                    ft.Container(expand=True),
                    bottom,
                ],
                spacing=4,
                expand=True,
            ),
            width=232,
            bgcolor=p.bg_soft,
            padding=ft.Padding.symmetric(horizontal=14, vertical=20),
            border=ft.Border.only(right=ft.BorderSide(1, p.border)),
        )

    def _nav_hover(self, key: str, event) -> None:
        if key == self.current_page:
            return
        active = str(getattr(event, "data", "")).lower() == "true"
        item, indicator, icon, text = self.nav_controls[key]
        item.bgcolor = self.p.surface if active else None
        if event.page:
            event.page.update()

    def _refresh_nav(self) -> None:
        """根据当前页更新导航高亮。"""
        for key, (item, indicator, icon, text) in self.nav_controls.items():
            active = key == self.current_page
            item.bgcolor = self.p.accent_soft if active else None
            indicator.bgcolor = self.p.accent if active else "transparent"
            active_icon, inactive_icon = next((a, i) for nav_key, _, a, i in NAV_ITEMS if nav_key == key)
            icon.icon = active_icon if active else inactive_icon
            icon.color = self.p.accent if active else self.p.text_muted
            text.color = self.p.text if active else self.p.text_muted
            text.weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_500

    def _on_resize(self, event) -> None:
        compact = self.page.width < 1040
        if compact == self.compact:
            return
        self.compact = compact
        self.sidebar.width = 82 if compact else 232
        self.logo_text.visible = not compact
        for key, (item, indicator, icon, text) in self.nav_controls.items():
            text.visible = not compact
            item.padding = ft.Padding.symmetric(horizontal=10 if compact else 12, vertical=10)
            item.alignment = ft.Alignment.CENTER if compact else None
        self.page.update()

    def navigate(self, key: str) -> None:
        self.current_page = key
        self._refresh_nav()
        if key == "versions" and not self.remote_versions and not self.version_loading:
            self.page.run_task(self.load_remote_versions, self.version_filter, True)
        if key == "logs":
            self.logs_page = logs.LogsView(self)
        self.render()

    def render(self) -> None:
        """重建当前页面。页面本身不保存状态，状态都在 App / LogsView 里。"""
        try:
            if self.current_page == "home":
                view = home.build(self)
            elif self.current_page == "instances":
                view = instances.build(self)
            elif self.current_page == "versions":
                view = versions.build(self)
            elif self.current_page == "logs":
                view = self.logs_page.build() if self.logs_page else ft.Container()
            elif self.current_page == "settings":
                view = settings_view.build(self)
            else:
                view = home.build(self)
        except Exception as exc:  # 页面构建失败也不应该把整个窗口带走
            view = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.BUG_REPORT_ROUNDED, size=40, color=self.p.danger),
                    ft.Text("页面加载失败", size=20, weight=ft.FontWeight.W_700, color=self.p.text),
                    ft.Text(f"{type(exc).__name__}: {exc}", size=12, color=self.p.text_muted,
                            selectable=True),
                    ui.tonal_button("回到首页", lambda e: self.navigate("home")),
                ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )
        self.content.content = view
        self._refresh_nav()
        self.page.update()

    # ---------- 数据刷新 ----------
    async def refresh_all(self) -> None:
        await asyncio.gather(
            self.refresh_instances(render=False),
            self.refresh_installed(render=False),
            self.refresh_java(render=False),
        )
        self.instances_loading = False
        self.render()

    async def refresh_instances(self, render: bool = True) -> None:
        try:
            self.instances = await asyncio.to_thread(services.list_instances)
        except Exception as exc:
            self.log_bus.push(f"[启动器] 读取实例失败：{exc}", "启动器", "ERROR")
            self.instances = []
        if render and self.current_page in ("home", "instances"):
            self.render()

    async def refresh_installed(self, render: bool = True) -> None:
        try:
            self.installed_versions = await asyncio.to_thread(services.list_installed_versions)
        except Exception as exc:
            self.log_bus.push(f"[启动器] 读取已安装版本失败：{exc}", "启动器", "ERROR")
            self.installed_versions = []
        if render and self.current_page == "versions":
            self.render()

    async def trash_instance(self, folder: str) -> None:
        """把实例移入回收站；失败时保留原实例并提示。"""
        try:
            target = await asyncio.to_thread(services.trash_instance, folder)
        except Exception as exc:
            self.show_toast(f"删除失败：{exc}", error=True)
            return
        self.log_bus.push(f"[实例] 已移入回收站：{target}", "启动器", "WARN")
        self.show_toast("实例已移入回收站")
        await self.refresh_instances(render=True)

    async def refresh_java(self, render: bool = True) -> None:
        try:
            self.java_runtimes = await asyncio.to_thread(services.list_java_runtimes)
        except Exception as exc:
            self.log_bus.push(f"[启动器] 扫描 Java 失败：{exc}", "启动器", "WARN")
            self.java_runtimes = []
        if render and self.current_page == "settings":
            self.render()

    async def load_remote_versions(self, version_type: str, prefer_cache: bool = False) -> None:
        self.version_loading = True
        self.version_error = ""
        if self.current_page == "versions":
            self.render()
        try:
            self.remote_versions = await asyncio.to_thread(
                services.list_versions, version_type, 80, prefer_cache,
            )
        except Exception as exc:
            self.version_error = str(exc)
            self.remote_versions = []
        self.version_loading = False
        if self.current_page == "versions":
            self.render()

    def set_version_filter(self, version_type: str) -> None:
        if version_type == self.version_filter:
            return
        self.version_filter = version_type
        self.remote_versions = []
        self.page.run_task(self.load_remote_versions, version_type, True)

    # ---------- 导入 / 安装 ----------
    async def show_import_dialog(self, update_folder: str | None = None) -> None:
        if self.task is not None and self.task.running:
            self.show_toast("有任务正在进行，请等它完成或取消", error=True)
            return
        try:
            files = await self.file_picker.pick_files(
                dialog_title="选择整合包",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["mrpack", "zip"],
            )
        except Exception as exc:
            show_error(self, "无法打开文件选择器", str(exc))
            return
        if not files or not files[0].path:
            return
        ImportDialog(self, files[0].path, update_folder=update_folder).open()

    def start_import_task(self, path, name=None, update_folder=None, plan=None) -> TaskState:
        title = f"更新 {update_folder}" if update_folder else f"导入 {(plan or {}).get('name') or Path(path).stem}"
        task = TaskState(kind="import", title=title)
        self.task = task
        self._task_hide_at = 0.0
        self._rebuild_footer()
        self.page.run_task(self._run_import_task, task, path, name, update_folder)
        return task

    async def _run_import_task(self, task: TaskState, path, name, update_folder) -> None:
        def on_log(text):
            self.log_bus.push(text, "导入")
            task.add_log(text)

        def on_progress(stage, done, total, detail):
            task.update(stage=stage, done=done, total=total, detail=detail)

        try:
            meta = await asyncio.to_thread(
                services.import_modpack,
                path,
                name,
                on_log=on_log,
                on_progress=on_progress,
                cancel=task.cancel_event.is_set,
                update_folder=update_folder,
            )
        except services.DownloadCancelled:
            task.cancelled()
            self.log_bus.push("[导入] 用户取消了导入", "导入", "WARN")
        except Exception as exc:
            task.fail(f"{type(exc).__name__}: {exc}")
            self.log_bus.push(f"[导入] 失败：{type(exc).__name__}: {exc}", "导入", "ERROR")
        else:
            task.finish(meta)
            self.log_bus.push(f"[导入] 完成：{meta.get('name', '')}", "导入")
            await self.refresh_instances(render=False)
            await self.refresh_installed(render=False)
            if self.current_page in ("home", "instances", "versions"):
                self.render()

    def start_install_task(self, version_id: str) -> TaskState:
        if self.task is not None and self.task.running:
            self.show_toast("有任务正在进行，请等它完成或取消", error=True)
            return self.task
        task = TaskState(kind="install", title=f"安装 Minecraft {version_id}")
        self.task = task
        self._task_hide_at = 0.0
        self._rebuild_footer()
        self.page.run_task(self._run_install_task, task, version_id)
        return task

    async def _run_install_task(self, task: TaskState, version_id: str) -> None:
        def on_progress(done, total, name, status):
            task.update(stage="下载文件", done=done, total=total, detail=name)

        try:
            await asyncio.to_thread(services.install_version, version_id,
                                    on_progress=on_progress, cancel=task.cancel_event.is_set)
        except services.DownloadCancelled:
            task.cancelled()
            self.log_bus.push(f"[安装] {version_id} 已取消", "安装", "WARN")
        except Exception as exc:
            task.fail(f"{type(exc).__name__}: {exc}")
            self.log_bus.push(f"[安装] {version_id} 失败：{type(exc).__name__}: {exc}", "安装", "ERROR")
        else:
            task.finish(version_id)
            self.log_bus.push(f"[安装] {version_id} 安装完成", "安装")
            await self.refresh_installed(render=False)
            await self.refresh_instances(render=False)
            if self.current_page in ("home", "instances", "versions"):
                self.render()

    # ---------- 启动 / 停止 ----------
    def launch_instance(self, folder: str) -> None:
        if self.session is not None and self.session.running:
            self.show_toast("已经有一个游戏在运行了", error=True)
            return
        item = next((instance for instance in self.instances if instance.get("folder") == folder), None)
        if item is None:
            self.show_toast("找不到这个实例", error=True)
            return
        self._begin_session(item.get("name") or folder, item.get("version_id") or "", folder=folder)

    def launch_version(self, version_id: str) -> None:
        if self.session is not None and self.session.running:
            self.show_toast("已经有一个游戏在运行了", error=True)
            return
        self._begin_session(version_id, version_id)

    def _begin_session(self, label: str, version_id: str, *, folder: str | None = None) -> None:
        self.session = GameSession(label=label, version_id=version_id)
        self._session_cleanup = False
        self._session_had_process = False
        if folder:
            # 首页的“继续游玩”卡片依赖这个字段；下次启动时优先展示最近实例
            self.settings["last_instance"] = folder
            try:
                services.save_settings(self.settings)
            except Exception:
                pass
        self._rebuild_footer()
        self.show_toast(f"正在启动 {label}…")
        if folder:
            self.page.run_task(self._run_instance_game, folder)
        else:
            self.page.run_task(self._run_version_game, self.session.version_id)

    def _missing_detail(self, exc: Exception) -> str:
        """把 MissingFilesError 的文件列表变成可复制的细节。"""
        missing = getattr(exc, "missing", None)
        return "\n".join(missing) if missing else ""

    async def _run_instance_game(self, folder: str) -> None:
        session = self.session
        if session is None:
            return

        def on_log(text):
            self.log_bus.push(text, "游戏")

        def on_process(proc):
            session.process = proc

        try:
            code = await asyncio.to_thread(
                services.launch_instance,
                folder,
                max_memory=self.settings.get("max_memory", "4G"),
                name=self.settings.get("player_name", "a2Cr"),
                on_log=on_log,
                on_process=on_process,
                java_path=self.settings.get("java_path") or None,
            )
        except Exception as exc:
            session.running = False
            session.exit_code = -1
            self.log_bus.push(f"[启动] 失败：{type(exc).__name__}: {exc}", "启动器", "ERROR")
            show_error(self, "启动失败", str(exc), detail=self._missing_detail(exc))
        else:
            session.running = False
            session.exit_code = code
            self.log_bus.push(f"[启动] {session.label} 已退出，退出码 {code}", "启动器",
                              "ERROR" if code else "INFO")
            self.show_toast(f"{session.label} 已退出（{code}）")
            await self.refresh_instances(render=True)
        self._rebuild_footer()

    async def _run_version_game(self, version_id: str) -> None:
        session = self.session
        if session is None:
            return

        def on_log(text):
            self.log_bus.push(text, "游戏")

        def on_process(proc):
            session.process = proc

        try:
            code = await asyncio.to_thread(
                services.launch_version,
                version_id,
                max_memory=self.settings.get("max_memory", "4G"),
                name=self.settings.get("player_name", "a2Cr"),
                on_log=on_log,
                on_process=on_process,
                java_path=self.settings.get("java_path") or None,
            )
        except Exception as exc:
            session.running = False
            session.exit_code = -1
            self.log_bus.push(f"[启动] 失败：{type(exc).__name__}: {exc}", "启动器", "ERROR")
            show_error(self, "启动失败", str(exc), detail=self._missing_detail(exc))
        else:
            session.running = False
            session.exit_code = code
            self.log_bus.push(f"[启动] {session.label} 已退出，退出码 {code}", "启动器",
                              "ERROR" if code else "INFO")
            self.show_toast(f"{session.label} 已退出（{code}）")
            await self.refresh_instances(render=True)
        self._rebuild_footer()

    def stop_game(self) -> None:
        session = self.session
        if session is None or not session.running:
            return
        proc = session.process
        if proc is None:
            session.stop_requested = True
            self.show_toast("进程还没有完全启动，稍后再试", error=True)
            return
        session.stop_requested = True
        try:
            proc.terminate()
            self.log_bus.push("[启动器] 已请求停止游戏", "启动器", "WARN")
            self.show_toast("正在停止游戏…")
        except Exception as exc:
            self.show_toast(f"停止失败：{exc}", error=True)

    # ---------- 页脚状态条 ----------
    def _rebuild_footer(self) -> None:
        """任务条和游戏状态条放在窗口底部，切换页面也不会消失。"""
        self.footer.controls.clear()
        if self.session is not None:
            self.footer.controls.append(self._build_session_bar())
        if self.task is not None:
            self.footer.controls.append(self._build_task_bar())
        if self.footer.page:
            self.page.update()

    def _build_session_bar(self) -> ft.Container:
        p = self.p
        session = self.session
        starting = session.process is None
        self.session_time = ft.Text(format_duration(session.elapsed), size=11,
                                    font_family="Consolas", color=p.text_muted)
        self.session_stop = ui.ghost_button(
            "准备中" if starting else "停止", lambda e: self.stop_game(),
            icon=ft.Icons.STOP_ROUNDED, color=p.text_muted if starting else p.danger,
            disabled=starting,
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=8, height=8, border_radius=4,
                                 bgcolor=p.warning if starting else p.success),
                    ft.Text(f"{'正在启动' if starting else '正在运行'} · {session.label}",
                            size=12, color=p.text, weight=ft.FontWeight.W_600),
                    ft.Text("·", size=12, color=p.text_faint),
                    self.session_time,
                    ft.Container(expand=True),
                    self.session_stop,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=24, vertical=8),
            bgcolor=p.surface,
            border=ft.Border.only(top=ft.BorderSide(1, p.border)),
        )

    def _build_task_bar(self) -> ft.Container:
        p = self.p
        task = self.task
        self.task_bar_title = ft.Text(task.title, size=12, color=p.text,
                                      weight=ft.FontWeight.W_600)
        self.task_bar_stage = ft.Text(task.stage, size=11, color=p.text_muted)
        self.task_bar_progress = ft.ProgressBar(
            value=task.ratio, color=p.accent, bgcolor=p.surface_hi, bar_height=4,
            border_radius=2, expand=True,
        )
        self.task_bar_cancel = ui.ghost_button("取消", lambda e: self.cancel_task(),
                                               icon=ft.Icons.CLOSE_ROUNDED, color=p.text_muted)
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=p.accent)
                    if task.running else ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=16,
                                                 color=p.success if task.status == "done" else p.danger),
                    ft.Column(
                        controls=[self.task_bar_title,
                                  ft.Row([self.task_bar_stage, self.task_bar_progress],
                                         spacing=10, expand=True)],
                        spacing=5,
                        expand=True,
                    ),
                    self.task_bar_cancel if task.running else ft.Container(),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=24, vertical=8),
            bgcolor=p.surface,
            border=ft.Border.only(top=ft.BorderSide(1, p.border)),
        )

    def cancel_task(self) -> None:
        if self.task is not None and self.task.running:
            self.task.cancel()

    async def _pump_tasks(self) -> None:
        while True:
            task = self.task
            if task is not None and hasattr(self, "task_bar_title"):
                self.task_bar_stage.value = task.stage
                self.task_bar_progress.value = task.ratio
                if not task.running:
                    self.task_bar_cancel.visible = False
                    if not self._task_hide_at:
                        self._task_hide_at = time.time() + 2.5
                    elif time.time() >= self._task_hide_at:
                        # 任务条收起，但 TaskState 还给导入对话框留着
                        self.task = None
                        self._task_hide_at = 0.0
                        self._rebuild_footer()
            await asyncio.sleep(0.2)

    async def _pump_session(self) -> None:
        while True:
            if self.session is not None and hasattr(self, "session_time"):
                self.session_time.value = format_duration(self.session.elapsed)
                # 进程真正创建后把“正在启动”换成“正在运行”，并启用停止按钮
                if self.session.process is not None and not self._session_had_process:
                    self._session_had_process = True
                    self._rebuild_footer()
                if not self.session.running and not self._session_cleanup:
                    self._session_cleanup = True
                    self.page.run_task(self._clear_session_later, self.session)
            await asyncio.sleep(1)

    async def _clear_session_later(self, session: GameSession) -> None:
        await asyncio.sleep(4)
        # 如果这期间又启动了一个游戏，不要把新会话清掉
        if self.session is session:
            self.session = None
            self._session_cleanup = False
            self._rebuild_footer()

    async def _pump_logs(self) -> None:
        while True:
            entries = self.log_bus.drain()
            if entries:
                self.log_entries.extend(entries)
                if len(self.log_entries) > 4000:
                    del self.log_entries[: len(self.log_entries) - 4000]
                if self.logs_page is not None:
                    self.logs_page.append(entries)
            await asyncio.sleep(0.15)

    # ---------- 设置 / 小工具 ----------
    def cycle_theme(self) -> None:
        order = ["dark", "light", "system"]
        current = self.settings.get("theme", "dark")
        self.set_theme(order[(order.index(current) + 1) % len(order)] if current in order else "dark")

    def set_theme(self, mode: str) -> None:
        """切换主题并重建界面，让所有组件拿到新调色板。"""
        self.settings["theme"] = mode
        try:
            services.save_settings(self.settings)
        except Exception as exc:
            self.show_toast(f"主题已切换，但保存设置失败：{exc}", error=True)
        self.p = self._palette_for(mode)
        ui.set_palette(self.p)
        self.page.theme_mode = self._theme_mode()
        self.page.bgcolor = self.p.bg
        self.page.window.bgcolor = self.p.bg
        current = self.current_page
        self._build_shell()
        self.navigate(current)

    def apply_settings(self, changes: dict) -> None:
        self.settings.update(changes)
        try:
            self.settings = services.save_settings(self.settings)
        except Exception as exc:
            self.show_toast(f"保存设置失败：{exc}", error=True)
            return
        if "theme" in changes:
            self.set_theme(self.settings["theme"])
        else:
            self.show_toast("设置已保存")

    def copy_text(self, text: str) -> None:
        if not text:
            return
        self.page.run_task(self.clipboard.set, str(text))
        self.show_toast("已复制到剪贴板")

    def show_toast(self, message: str, *, error: bool = False) -> None:
        """轻量提示。用 SnackBar，不打断当前操作。"""
        bar = ft.SnackBar(
            content=ft.Text(message, size=12, color="#FFFFFF"),
            bgcolor=self.p.danger if error else self.p.surface_hi,
            duration=3200,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=ft.Margin.only(left=24, right=24, bottom=16),
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        self.page.show_dialog(bar)

    async def pick_java_directory(self) -> None:
        """让用户选一个 Java 安装目录，校验后写入设置。"""
        try:
            path = await self.file_picker.get_directory_path(dialog_title="选择 Java 安装目录")
        except Exception as exc:
            show_error(self, "无法打开目录选择器", str(exc))
            return
        if not path:
            return
        if not services.is_valid_java_path(path):
            show_error(self, "这个目录不是有效的 Java",
                       "请选择包含 bin\\java.exe 的 Java 安装目录（例如 C:\\Program Files\\Zulu\\zulu-25）。")
            return
        self.apply_settings({"java_path": path})
        await self.refresh_java(render=False)
        if self.current_page == "settings":
            self.render()

    def open_data_dir(self) -> None:
        try:
            services.open_path(services.data_dirs()["root"])
        except Exception as exc:
            self.show_toast(f"打开目录失败：{exc}", error=True)

    def _on_close(self, event) -> None:
        # 恢复 stdout，避免测试/后续代码拿到被包装的对象
        if self._stdout_tee is not None:
            sys.stdout = self._stdout_tee._original
        try:
            self.settings["window_width"] = int(self.page.window.width or 1180)
            self.settings["window_height"] = int(self.page.window.height or 760)
            services.save_settings(self.settings)
        except Exception:
            pass

    def _on_error(self, event) -> None:
        """Flet 运行时错误也写进日志，方便用户反馈时带上上下文。"""
        detail = getattr(event, "data", None) or str(event)
        self.log_bus.push(f"[界面错误] {detail}", "启动器", "ERROR")


def main(page: ft.Page):
    """Flet 入口。"""
    page.title = "a2cr Launcher"
    LauncherApp(page)


def run():
    ft.run(main)


if __name__ == "__main__":
    run()
