import asyncio
import time

import flet as ft

from a2cr_launcher.services import list_installed, launch_version


def main(page: ft.Page):
    # region 初始定义
    page.title = "a2cr Minecraft Launcher"
    # endregion


    instances: list[ft.Row] = list()
    versions = list(list_installed())

    for version in versions:
        target = version.split("\\")[-1]
        show = ft.Row(controls=[ft.Text(version), ft.Button(content=f"Launch {target}",
                                                            on_click=lambda e, t=target: launch_version(
                                                                t))])
        instances.append(show)

    tabs: ft.Tabs = ft.Tabs(length=2, expand=True, content=ft.Column(expand=True, controls=[
        ft.TabBar(
            tabs=[
                ft.Tab(label="Launch"),
                ft.Tab(label="Install"),
            ]
        ),
        ft.TabBarView(
            expand=True,
            controls=[
                ft.ListView(
                    controls=instances,
                ),
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Row(controls=[ft.TextField(hint_text="Whats versions to be done?", expand=True),
                                             ft.Button(content="Install")]),
                ), ], ), ], ))

    page.add(tabs)


def run():
    ft.run(main)
