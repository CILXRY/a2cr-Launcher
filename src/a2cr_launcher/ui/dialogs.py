"""对话框与导入向导。

导入向导分成三步：预检 → 进度 → 结果。所有耗时操作都通过 ``App`` 的后台
任务执行，这里只负责把 ``TaskState`` 的变化画到对话框里。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from .. import services
from ..ui import components as ui
from ..ui.theme import loader_meta
from ..ui.utils import loader_display

# 底层阶段名 -> 用户能看懂的文案
STAGE_LABELS = {
    "parse": "解析整合包",
    "resolve": "解析文件地址",
    "vanilla": "安装原版",
    "loader": "安装加载器",
    "extract": "解压整合包",
    "files": "下载整合包文件",
    "done": "完成",
}


def _dialog_width(control: ft.Control, width: int = 520) -> ft.Container:
    return ft.Container(content=control, width=width)


def show_error(app, title: str, message: str, detail: str = "") -> None:
    """统一错误对话框：一句人话 + 可选的技术细节。"""
    body: list[ft.Control] = [
        ft.Text(message, size=12.5, color=app.p.text_muted, selectable=True),
    ]
    if detail:
        body.append(ft.Container(
            content=ft.Text(detail, size=11, font_family="Consolas", color=app.p.text_muted,
                            selectable=True),
            bgcolor=app.p.bg_soft,
            border=ft.Border.all(1, app.p.border),
            border_radius=10,
            padding=12,
            width=480,
        ))

    actions = []
    if detail:
        actions.append(ui.ghost_button(
            "复制详情", lambda e: app.copy_text(detail), icon=ft.Icons.CONTENT_COPY_ROUNDED,
        ))
    actions.append(ft.TextButton("知道了", on_click=lambda e: app.page.pop_dialog()))

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=app.p.danger, size=22),
                ft.Text(title, size=17, weight=ft.FontWeight.W_700, color=app.p.text),
            ],
            spacing=10,
        ),
        content=_dialog_width(ft.Column(body, spacing=12, tight=True)),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=app.p.surface,
        shape=ft.RoundedRectangleBorder(radius=20),
    )
    app.page.show_dialog(dialog)


def show_confirm(app, title: str, message: str, on_confirm, *, confirm_text: str = "确定",
                 danger: bool = False) -> None:
    """二次确认。回调在对话框关闭之后执行。"""

    def _confirm(event):
        app.page.pop_dialog()
        on_confirm()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=17, weight=ft.FontWeight.W_700, color=app.p.text),
        content=_dialog_width(ft.Text(message, size=13, color=app.p.text_muted, selectable=True), 460),
        actions=[
            ft.TextButton("取消", on_click=lambda e: app.page.pop_dialog()),
            ft.FilledButton(
                content=confirm_text,
                on_click=_confirm,
                style=ft.ButtonStyle(
                    bgcolor=app.p.danger if danger else app.p.accent,
                    color="#FFFFFF" if danger else app.p.accent_ink,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    elevation=0,
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=app.p.surface,
        shape=ft.RoundedRectangleBorder(radius=20),
    )
    app.page.show_dialog(dialog)


class ImportDialog:
    """整合包导入/更新向导。"""

    def __init__(self, app, path: str | Path, update_folder: str | None = None):
        self.app = app
        self.page = app.page
        self.path = Path(path)
        self.update_folder = update_folder
        self.plan: dict | None = None
        self.task = None
        self.dialog: ft.AlertDialog | None = None
        self.name_field: ft.TextField | None = None
        # 进度页里需要反复更新的控件，预先留引用
        self.stage_text: ft.Text | None = None
        self.detail_text: ft.Text | None = None
        self.progress_bar: ft.ProgressBar | None = None
        self.log_text: ft.Text | None = None
        self.cancel_button: ft.Control | None = None
        self._closed = False

    # ---------- 打开与预检 ----------
    def open(self) -> None:
        title = "更新整合包" if self.update_folder else "导入整合包"
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=19, weight=ft.FontWeight.W_700, color=self.app.p.text),
            content=_dialog_width(ft.Column(
                controls=[
                    ft.ProgressRing(width=24, height=24, stroke_width=2, color=self.app.p.accent),
                    ft.Text("正在读取整合包信息…", size=12.5, color=self.app.p.text_muted),
                ],
                spacing=14,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ), 480),
            actions=[ft.TextButton("取消", on_click=lambda e: self.close())],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=self.app.p.surface,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        self.page.show_dialog(self.dialog)
        self.page.run_task(self._prepare)

    def close(self) -> None:
        self._closed = True
        self.page.pop_dialog()

    async def _prepare(self) -> None:
        try:
            plan = await asyncio.to_thread(services.inspect_modpack, str(self.path))
        except Exception as exc:
            if not self._closed:
                self._show_prepare_error(exc)
            return
        if self._closed:
            return
        self.plan = plan
        self._show_preflight(plan)

    def _show_prepare_error(self, exc: Exception) -> None:
        if self.dialog is None:
            return
        self.dialog.content = _dialog_width(ft.Column(
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=self.app.p.danger, size=22),
                    ft.Text("无法读取这个整合包", size=15, weight=ft.FontWeight.W_600,
                            color=self.app.p.text),
                ], spacing=8),
                ft.Text(str(exc), size=12.5, color=self.app.p.text_muted, selectable=True),
                ft.Text("支持 Modrinth .mrpack、CurseForge .zip、HMCL/PCL 导出的压缩包。",
                        size=11.5, color=self.app.p.text_faint),
            ],
            spacing=12,
            tight=True,
        ), 480)
        self.dialog.actions = [ft.TextButton("关闭", on_click=lambda e: self.close())]
        self.page.update()

    def _show_preflight(self, plan: dict) -> None:
        if self.dialog is None:
            return
        p = self.app.p
        label, color = loader_meta(plan.get("loader", "vanilla"))
        format_label = {
            "modrinth": "Modrinth",
            "curseforge": "CurseForge",
            "local": "HMCL / PCL",
        }.get(plan.get("format", ""), plan.get("format", "未知"))
        chips = ft.Row(
            controls=[
                ui.pill(f"MC {plan.get('mc_version', '—')}", color=p.accent, bgcolor=p.accent_soft),
                ui.pill(loader_display(plan.get("loader", "vanilla"), plan.get("loader_version", "")),
                        color=color, bgcolor=p.surface_hi),
                ui.pill(format_label, color=p.text_muted, bgcolor=p.surface_hi),
            ],
            spacing=8,
            wrap=True,
        )

        default_name = plan.get("name") or self.path.stem
        self.name_field = ft.TextField(
            label="实例名",
            value=self.update_folder if self.update_folder else default_name,
            hint_text="给这个整合包起个名字",
            bgcolor=p.bg_soft,
            border_color=p.border,
            focused_border_color=p.accent,
            color=p.text,
            label_style=ft.TextStyle(color=p.text_muted, size=12),
            text_size=13,
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            disabled=bool(self.update_folder),
        )

        info_rows = [
            ft.Row([
                ft.Text("文件数量", size=12, color=p.text_muted, expand=True),
                ft.Text(f"{plan.get('file_count', 0)} 个", size=12, color=p.text),
            ]),
            ft.Row([
                ft.Text("版本号", size=12, color=p.text_muted, expand=True),
                ft.Text(plan.get("pack_version") or "未标注", size=12, color=p.text),
            ]),
        ]

        body: list[ft.Control] = [
            ft.Row(
                controls=[
                    ui.cover_art(default_name, plan.get("loader", "vanilla"), height=84,
                                 width=96, show_loader=False),
                    ft.Column(
                        controls=[
                            ft.Text(default_name, size=18, weight=ft.FontWeight.W_700, color=p.text,
                                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            chips,
                        ],
                        spacing=8,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=1, bgcolor=p.border),
            ft.Column(info_rows, spacing=8),
        ]
        if self.update_folder:
            body.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=16, color=p.warning),
                    ft.Text(f"将更新实例「{self.update_folder}」；旧版本托管且未被修改的 mod 会被清理。",
                            size=11.5, color=p.warning, expand=True),
                ], spacing=8),
                bgcolor=p.surface_hi,
                border_radius=10,
                padding=10,
            ))
        body.append(self.name_field)

        self.dialog.content = _dialog_width(ft.Column(body, spacing=16, tight=True), 500)
        self.dialog.actions = [
            ft.TextButton("取消", on_click=lambda e: self.close()),
            ui.primary_button("开始导入" if not self.update_folder else "开始更新",
                              lambda e: self._start_import(), icon=ft.Icons.DOWNLOAD_ROUNDED),
        ]
        self.page.update()

    # ---------- 执行与进度 ----------
    def _start_import(self) -> None:
        if self.plan is None:
            return
        name = None
        if self.name_field is not None and not self.update_folder:
            name = (self.name_field.value or "").strip() or None

        self._show_progress()
        self.task = self.app.start_import_task(
            self.path, name=name, update_folder=self.update_folder, plan=self.plan,
        )
        self.page.run_task(self._poll_task)

    def _show_progress(self) -> None:
        if self.dialog is None:
            return
        p = self.app.p
        self.stage_text = ft.Text("准备中…", size=15, weight=ft.FontWeight.W_600, color=p.text)
        self.detail_text = ft.Text("正在创建任务…", size=11.5, color=p.text_muted)
        self.progress_bar = ft.ProgressBar(value=None, color=p.accent, bgcolor=p.surface_hi,
                                          bar_height=6, border_radius=3)
        self.log_text = ft.Text("", size=10.5, font_family="Consolas", color=p.text_faint,
                                selectable=True, max_lines=5)
        self.cancel_button = ui.ghost_button(
            "取消导入", lambda e: self._cancel_task(), icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            color=p.danger,
        )
        self.dialog.content = _dialog_width(ft.Column(
            controls=[
                ft.Row([
                    ft.ProgressRing(width=20, height=20, stroke_width=2, color=p.accent),
                    self.stage_text,
                ], spacing=10),
                self.progress_bar,
                self.detail_text,
                ft.Container(
                    content=self.log_text,
                    bgcolor=p.bg_soft,
                    border=ft.Border.all(1, p.border),
                    border_radius=10,
                    padding=10,
                ),
            ],
            spacing=14,
            tight=True,
        ), 500)
        self.dialog.actions = [self.cancel_button]
        self.page.update()

    def _cancel_task(self) -> None:
        if self.task is not None:
            self.task.cancel()
            if self.cancel_button is not None:
                self.cancel_button.disabled = True
            self.page.update()

    async def _poll_task(self) -> None:
        """任务在后台线程里跑，这里只以 8fps 左右刷新对话框。"""
        task = self.task
        if task is None:
            return
        while task.running and not self._closed:
            self._refresh_progress(task)
            await asyncio.sleep(0.12)
        if self._closed:
            return
        self._refresh_progress(task)
        self._show_result(task)

    def _refresh_progress(self, task) -> None:
        if self.stage_text is None or self.progress_bar is None:
            return
        self.stage_text.value = STAGE_LABELS.get(task.stage, task.stage or "处理中")
        self.progress_bar.value = task.ratio
        if task.total:
            self.detail_text.value = f"{task.detail}  ·  {task.done}/{task.total}"
        else:
            self.detail_text.value = task.detail or "请稍候…"
        if task.logs:
            self.log_text.value = "\n".join(list(task.logs)[-4:])
        self.page.update()

    def _show_result(self, task) -> None:
        if self.dialog is None:
            return
        p = self.app.p
        if task.status == "done":
            meta = task.result or {}
            body = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=34, color=p.success),
                        width=64, height=64, border_radius=20, bgcolor=p.accent_soft,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text("更新完成" if self.update_folder else "导入完成",
                            size=19, weight=ft.FontWeight.W_700, color=p.text),
                    ft.Text(f"{meta.get('name', self.path.stem)} 已经可以使用了。",
                            size=12.5, color=p.text_muted),
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.dialog.content = _dialog_width(body, 460)
            actions = []
            if meta.get("folder"):
                actions.append(ui.primary_button(
                    "启动游戏", lambda e: self._launch_and_close(meta["folder"]),
                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                ))
            actions.append(ft.TextButton("完成", on_click=lambda e: self.close()))
            self.dialog.actions = actions
        elif task.status == "cancelled":
            self.dialog.content = _dialog_width(ft.Column([
                ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE_ROUNDED, size=38, color=p.warning),
                ft.Text("已取消", size=18, weight=ft.FontWeight.W_700, color=p.text),
                ft.Text("已经下载的文件会保留，下次导入可以继续。", size=12.5, color=p.text_muted),
            ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), 440)
            self.dialog.actions = [ft.TextButton("关闭", on_click=lambda e: self.close())]
        else:
            self.dialog.content = _dialog_width(ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=38, color=p.danger),
                ft.Text("导入失败", size=18, weight=ft.FontWeight.W_700, color=p.text),
                ft.Text(task.error or "未知错误", size=12.5, color=p.text_muted, selectable=True),
            ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), 460)
            self.dialog.actions = [
                ui.ghost_button("复制错误", lambda e: self.app.copy_text(task.error)),
                ft.TextButton("关闭", on_click=lambda e: self.close()),
            ]
        self.page.update()

    def _launch_and_close(self, folder: str) -> None:
        self.close()
        self.app.launch_instance(folder)
