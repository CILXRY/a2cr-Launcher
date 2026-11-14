"""实例页：卡片网格、实例详情、更新和删除。"""

from __future__ import annotations

import flet as ft

from ... import services
from ...ui import components as ui
from ...ui.dialogs import show_confirm
from ...ui.theme import loader_meta
from ...ui.utils import format_relative, loader_display, shorten_path


def build(app) -> ft.Control:
    p = app.p
    import_button = ui.primary_button(
        "导入整合包", lambda e: app.page.run_task(app.show_import_dialog),
        icon=ft.Icons.ADD_ROUNDED, height=40,
    )
    refresh_button = ui.icon_action(
        ft.Icons.REFRESH_ROUNDED, "刷新实例",
        lambda e: app.page.run_task(app.refresh_instances),
    )
    header = ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text("我的实例", size=26, weight=ft.FontWeight.W_800, color=p.text),
                    ft.Text("整合包、加载器和存档都在这里", size=12.5, color=p.text_muted),
                ],
                spacing=4,
                expand=True,
            ),
            refresh_button,
            import_button,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if app.instances_loading:
        body: ft.Control = ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressRing(width=28, height=28, stroke_width=2, color=p.accent),
                    ft.Text("正在读取实例…", size=12.5, color=p.text_muted),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            height=240,
        )
    elif not app.instances:
        body = ui.empty_state(
            ft.Icons.VIEW_IN_AR_OUTLINED,
            "还没有整合包实例",
            "支持 Modrinth .mrpack、CurseForge .zip，以及 HMCL / PCL 导出的压缩包。",
            actions=[
                ui.primary_button("导入第一个整合包",
                                  lambda e: app.page.run_task(app.show_import_dialog),
                                  icon=ft.Icons.ADD_ROUNDED),
                ui.tonal_button("安装原版", lambda e: app.navigate("versions"),
                                icon=ft.Icons.LAYERS_OUTLINED),
            ],
        )
    else:
        cards = []
        for item in app.instances:
            card = instance_card(app, item)
            card.col = {"sm": 12, "md": 6, "lg": 4}
            cards.append(card)
        body = ft.ResponsiveRow(controls=cards, spacing=14, run_spacing=14)

    return ft.Column(
        controls=[
            header,
            ft.Container(height=4),
            body,
        ],
        spacing=18,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def instance_card(app, item: dict) -> ft.Container:
    """单个实例卡片。所有动作都在卡片底部，避免点击区域互相抢事件。"""
    p = app.p
    folder = item.get("folder", "")
    name = item.get("name") or folder
    loader = item.get("loader", {}).get("type", item.get("loader_type", "vanilla"))
    loader_version = item.get("loader", {}).get("version", item.get("loader_version", ""))
    label, loader_color = loader_meta(loader)

    play = ui.primary_button(
        "启动", lambda e: app.launch_instance(folder),
        icon=ft.Icons.PLAY_ARROW_ROUNDED, height=34, width=92,
    )
    folder_button = ui.icon_action(
        ft.Icons.FOLDER_OPEN_ROUNDED, "打开实例目录",
        lambda e: app.page.run_task(_open_folder, app, folder),
    )
    update_button = ui.icon_action(
        ft.Icons.SYSTEM_UPDATE_ALT_ROUNDED, "更新整合包",
        lambda e: app.page.run_task(app.show_import_dialog, folder),
    )
    delete_button = ui.icon_action(
        ft.Icons.DELETE_OUTLINE_ROUNDED, "删除实例",
        lambda e: _confirm_delete(app, item), color=p.danger,
    )
    detail_button = ui.icon_action(
        ft.Icons.INFO_OUTLINE_ROUNDED, "实例详情",
        lambda e: show_detail(app, item),
    )

    meta = ft.Row(
        controls=[
            ui.pill(loader_display(loader, loader_version), color=loader_color, bgcolor=p.surface_hi),
            ui.pill(f"MC {item.get('mc_version', '—')}", color=p.text_muted, bgcolor=p.surface_hi),
        ],
        spacing=6,
        wrap=True,
    )
    body = ft.Column(
        controls=[
            ui.cover_art(name, loader, height=94),
            ft.Column(
                controls=[
                    ft.Text(name, size=15, weight=ft.FontWeight.W_700, color=p.text,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    meta,
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SCHEDULE_ROUNDED, size=12, color=p.text_faint),
                            ft.Text(format_relative(item.get("last_played")),
                                    size=11, color=p.text_faint),
                            ft.Text("·", size=11, color=p.text_faint),
                            ft.Text(f"{item.get('mods_count', 0)} 个 mod", size=11,
                                    color=p.text_faint),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=8,
            ),
            ft.Container(height=1, bgcolor=p.border),
            ft.Row(
                controls=[
                    play,
                    ft.Container(expand=True),
                    detail_button,
                    folder_button,
                    update_button,
                    delete_button,
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=10,
    )
    card = ui.card(body, padding=10, hover=True)
    card.tooltip = shorten_path(item.get("path", ""), 60)
    return card


async def _open_folder(app, folder: str) -> None:
    import asyncio
    try:
        await asyncio.to_thread(services.open_instance_folder, folder)
    except Exception as exc:
        app.show_toast(f"打开目录失败：{exc}", error=True)


def _confirm_delete(app, item: dict) -> None:
    folder = item.get("folder", "")
    name = item.get("name") or folder
    show_confirm(
        app,
        "删除实例",
        f"「{name}」会被移动到启动器回收站，不会立即永久删除。\n"
        f"目录：{item.get('path', '')}",
        lambda: app.page.run_task(app.trash_instance, folder),
        confirm_text="移入回收站",
        danger=True,
    )


def show_detail(app, item: dict) -> None:
    """实例详情对话框。"""
    p = app.p
    folder = item.get("folder", "")
    name = item.get("name") or folder
    loader = item.get("loader", {}).get("type", item.get("loader_type", "vanilla"))
    loader_version = item.get("loader", {}).get("version", item.get("loader_version", ""))
    source = item.get("source") or {}

    rows = [
        ("Minecraft", item.get("mc_version", "—")),
        ("启动版本", item.get("version_id", "—")),
        ("加载器", loader_display(loader, loader_version)),
        ("来源", source.get("format", "—")),
        ("整合包版本", source.get("pack_version") or "未标注"),
        ("最近游玩", format_relative(item.get("last_played"))),
        ("目录", item.get("path", "")),
    ]
    info = []
    for key, value in rows:
        info.append(ft.Row(
            controls=[
                ft.Text(key, size=12, color=p.text_muted, width=88),
                ft.Text(str(value), size=12, color=p.text, selectable=True, expand=True),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ))

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ui.cover_art(name, loader, height=56, radius=12, width=84, show_loader=False),
                ft.Column(
                    controls=[
                        ft.Text(name, size=17, weight=ft.FontWeight.W_700, color=p.text),
                        ft.Text(f"{item.get('mods_count', 0)} 个 mod", size=11, color=p.text_muted),
                    ],
                    spacing=3,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=ft.Column(info, spacing=9, tight=True),
            width=480,
        ),
        actions=[
            ft.TextButton("关闭", on_click=lambda e: app.page.pop_dialog()),
            ui.ghost_button("删除", lambda e: _delete_from_detail(app, item), color=p.danger),
            ui.tonal_button("打开目录", lambda e: app.page.run_task(_open_folder, app, folder),
                            icon=ft.Icons.FOLDER_OPEN_ROUNDED),
            ui.primary_button("启动", lambda e: _launch_from_detail(app, folder),
                              icon=ft.Icons.PLAY_ARROW_ROUNDED),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=p.surface,
        shape=ft.RoundedRectangleBorder(radius=20),
    )
    app.page.show_dialog(dialog)


def _launch_from_detail(app, folder: str) -> None:
    app.page.pop_dialog()
    app.launch_instance(folder)


def _delete_from_detail(app, item: dict) -> None:
    app.page.pop_dialog()
    _confirm_delete(app, item)
