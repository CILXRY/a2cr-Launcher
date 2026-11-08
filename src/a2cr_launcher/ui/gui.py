"""a2cr Launcher 的图形界面（Flet）。

界面层只调用 services 里的三个函数，不碰 core / meta / launch 的细节。
所有耗时操作都必须放进 asyncio.to_thread，界面只在事件循环里更新。
"""

import asyncio
import queue
import sys

import flet as ft

from a2cr_launcher.services import install_version, launch_version, list_installed

MAX_LOG_LINES = 2000


class StdoutTee:
    """把 stdout 同时写到原来的终端和界面的日志队列。

    打包后的应用里 stdout 是 None，所有 print 都会落到 Flet 的 console.log；
    这里接一份出来显示在界面上。
    """

    def __init__(self, original, sink):
        self._original = original
        self._sink = sink

    def write(self, text):
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        if text and text.strip():
            self._sink(text.rstrip("\n"))
        return len(text)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self):
        return False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8") or "utf-8"


def main(page: ft.Page):
    page.title = "a2cr Minecraft Launcher"
    page.window.width = 900
    page.window.height = 640

    log_queue: queue.Queue[str] = queue.Queue()

    def push_log(text: str) -> None:
        """任何线程都可以调，只入队，不碰界面。"""
        log_queue.put(text)

    # 让 core 里所有 print 都能进日志面板
    sys.stdout = StdoutTee(sys.stdout, push_log)

    status = ft.Text("就绪")
    launch_list = ft.ListView(expand=True, spacing=6)
    log_view = ft.ListView(expand=True, spacing=1, auto_scroll=True)
    version_field = ft.TextField(hint_text="要安装的版本号，例如 1.21.1", expand=True)
    bar = ft.ProgressBar(value=0, visible=False)

    # ---------- 日志泵 ----------
    async def pump_logs():
        while True:
            count = 0
            while count < 200 and not log_queue.empty():
                line = log_queue.get()
                log_view.controls.append(
                    ft.Text(line, size=11, font_family="Consolas", selectable=True)
                )
                count += 1
            if count:
                if len(log_view.controls) > MAX_LOG_LINES:
                    del log_view.controls[: len(log_view.controls) - MAX_LOG_LINES]
                page.update()
            await asyncio.sleep(0.2)

    # ---------- 启动 ----------
    async def start_launch(version: str):
        status.value = f"启动 {version}…"
        page.update()
        try:
            code = await asyncio.to_thread(launch_version, version, on_log=push_log)
            push_log(f"[launcher] {version} 已退出，退出码 {code}")
        except Exception as exc:
            push_log(f"[launcher] 启动失败: {type(exc).__name__}: {exc}")
            status.value = f"启动失败：{exc}"
        else:
            status.value = f"{version} 已退出"
        page.update()

    def make_row(version: str) -> ft.Row:
        async def on_click(e):
            await start_launch(version)

        return ft.Row(
            controls=[
                ft.Text(version, expand=True),
                ft.Button(content="启动", on_click=on_click),
            ]
        )

    def refresh_installed():
        launch_list.controls.clear()
        for version in list_installed():
            launch_list.controls.append(make_row(version))
        page.update()

    # ---------- 安装 ----------
    async def do_install(e):
        version = version_field.value.strip()
        if not version:
            status.value = "先填个版本号"
            page.update()
            return

        state = {"done": 0, "total": 0, "name": ""}

        def on_progress(done, total, name, result):
            # 在下载线程里被调用，只改数据，不碰界面
            state.update(done=done, total=total, name=name)

        bar.visible = True
        status.value = f"准备安装 {version}…"
        push_log(f"[launcher] 开始安装 {version}")
        page.update()

        task = asyncio.create_task(asyncio.to_thread(install_version, version, on_progress))
        while not task.done():
            if state["total"]:
                bar.value = state["done"] / state["total"]
                status.value = f'{state["done"]}/{state["total"]}  {state["name"]}'
            page.update()
            await asyncio.sleep(0.1)

        try:
            await task
            status.value = f"{version} 安装完成"
            push_log(f"[launcher] {version} 安装完成")
            refresh_installed()
        except Exception as exc:
            status.value = f"安装失败：{exc}"
            push_log(f"[launcher] 安装失败: {type(exc).__name__}: {exc}")
        bar.visible = False
        page.update()

    install_tab = ft.Container(
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            controls=[
                ft.Text("安装新版本（会自动下载 client / 运行库 / 资源 / 日志配置）"),
                ft.Row(controls=[version_field, ft.Button(content="安装", on_click=do_install)]),
            ],
            spacing=16,
        ),
    )

    log_tab = ft.Column(
        expand=True,
        controls=[
            ft.Row(
                controls=[
                    ft.Text("日志", expand=True),
                    ft.Button(content="清空", on_click=lambda e: (log_view.controls.clear(), page.update())),
                ]
            ),
            log_view,
        ],
    )

    tabs = ft.Tabs(
        length=3,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[ft.Tab(label="启动"), ft.Tab(label="安装"), ft.Tab(label="日志")]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[launch_list, install_tab, log_tab],
                ),
            ],
        ),
    )

    page.add(tabs, ft.Divider(), bar, status)
    refresh_installed()
    push_log("[launcher] 界面已启动")
    page.run_task(pump_logs)


def run():
    ft.run(main)


if __name__ == "__main__":
    run()
