"""a2cr Launcher 的图形界面（Flet）。

界面层只调用 services 里的三个函数，不碰 core / meta / launch 的细节。
所有耗时操作都必须放进 asyncio.to_thread，界面只在事件循环里更新。
"""

import asyncio

import flet as ft

from a2cr_launcher.services import install_version, launch_version, list_installed


def main(page: ft.Page):
    page.title = "a2cr Minecraft Launcher"
    page.window.width = 900
    page.window.height = 600

    status = ft.Text("就绪")
    launch_list = ft.ListView(expand=True, spacing=6)
    version_field = ft.TextField(hint_text="要安装的版本号，例如 1.21.1", expand=True)
    bar = ft.ProgressBar(value=0, visible=False)

    # ---------- Launch ----------
    async def start_launch(version: str):
        status.value = f"启动 {version}…"
        page.update()
        code = await asyncio.to_thread(launch_version, version)
        status.value = f"{version} 已退出（退出码 {code}）"
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

    # ---------- Install ----------
    async def do_install(e):
        version = version_field.value.strip()
        if not version:
            status.value = "先填个版本号"
            page.update()
            return

        state = {"done": 0, "total": 0, "name": ""}

        def on_progress(done, total, name, result):
            # 这里在下载线程里被调用，只改数据，不碰界面
            state.update(done=done, total=total, name=name)

        bar.visible = True
        status.value = f"准备安装 {version}…"
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
            refresh_installed()
        except Exception as exc:
            status.value = f"安装失败：{exc}"
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

    tabs = ft.Tabs(
        length=2,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(tabs=[ft.Tab(label="启动"), ft.Tab(label="安装")]),
                ft.TabBarView(
                    expand=True,
                    controls=[launch_list, install_tab],
                ),
            ],
        ),
    )

    page.add(tabs, ft.Divider(), bar, status)
    refresh_installed()


def run():
    ft.run(main)


if __name__ == "__main__":
    run()
