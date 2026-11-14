"""首页：继续游玩、运行数据、最近实例和快捷入口。"""

from __future__ import annotations

import flet as ft

from ...ui import components as ui
from ...ui.utils import format_relative, loader_display
from .instances import instance_card


def build(app) -> ft.Control:
    p = app.p
    featured = _featured_instance(app)
    stats = ft.ResponsiveRow(
        controls=[
            _col(ui.stat_card(ft.Icons.VIEW_IN_AR_ROUNDED, str(len(app.instances)), "整合包实例"), 4),
            _col(ui.stat_card(ft.Icons.LAYERS_ROUNDED, str(len(app.installed_versions)), "已安装版本"), 4),
            _col(ui.stat_card(ft.Icons.COFFEE_ROUNDED, str(len(app.java_runtimes)), "可用 Java"), 4),
        ],
        spacing=12,
        run_spacing=12,
    )

    children: list[ft.Control] = [
        _hero(app, featured),
        stats,
        ui.section_header(
            "最近实例",
            "从上次离开的地方继续",
            action=ui.ghost_button("查看全部", lambda e: app.navigate("instances"),
                                   icon=ft.Icons.ARROW_FORWARD_ROUNDED),
        ),
    ]

    if app.instances_loading:
        children.append(ft.Container(
            content=ft.ProgressRing(width=24, height=24, stroke_width=2, color=p.accent),
            alignment=ft.Alignment.CENTER,
            height=120,
        ))
    elif app.instances:
        recent = []
        for item in _recent_instances(app)[:3]:
            card = instance_card(app, item)
            card.col = {"sm": 12, "md": 6, "lg": 4}
            recent.append(card)
        children.append(ft.ResponsiveRow(controls=recent, spacing=14, run_spacing=14))
    else:
        children.append(ui.empty_state(
            ft.Icons.ROCKET_LAUNCH_OUTLINED,
            "还没有可以游玩的实例",
            "导入一个整合包，或者先安装一个原版版本。",
            actions=[
                ui.primary_button("导入整合包", lambda e: app.page.run_task(app.show_import_dialog),
                                  icon=ft.Icons.ADD_ROUNDED),
                ui.tonal_button("安装原版", lambda e: app.navigate("versions"),
                                icon=ft.Icons.DOWNLOAD_ROUNDED),
            ],
        ))

    children.append(ui.section_header("快捷入口", "少点几次鼠标"))
    children.append(ft.ResponsiveRow(
        controls=[
            _quick_card(app, ft.Icons.ADD_ROUNDED, "导入整合包", "支持 .mrpack 和 .zip",
                        lambda e: app.page.run_task(app.show_import_dialog)),
            _quick_card(app, ft.Icons.DOWNLOAD_ROUNDED, "安装原版", "从 Mojang 版本库下载",
                        lambda e: app.navigate("versions")),
            _quick_card(app, ft.Icons.FOLDER_OPEN_ROUNDED, "打开数据目录", "实例、日志和运行库",
                        lambda e: app.open_data_dir()),
        ],
        spacing=12,
        run_spacing=12,
    ))

    return ft.Column(controls=children, spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)


def _col(control: ft.Control, span: int) -> ft.Container:
    return ft.Container(content=control, col={"sm": 12, "md": span, "lg": span})


def _recent_instances(app) -> list[dict]:
    """按最近游玩时间排序；没有 last_played 的实例排后面。"""
    return sorted(app.instances, key=lambda item: item.get("last_played") or "", reverse=True)


def _featured_instance(app) -> dict | None:
    if not app.instances:
        return None
    last = app.settings.get("last_instance")
    for item in app.instances:
        if item.get("folder") == last:
            return item
    return _recent_instances(app)[0]


def _hero(app, featured: dict | None) -> ft.Container:
    p = app.p
    if featured is not None:
        loader = featured.get("loader", {}).get("type", "vanilla")
        loader_version = featured.get("loader", {}).get("version", "")
        title = featured.get("name") or featured.get("folder", "")
        subtitle = (f"MC {featured.get('mc_version', '—')} · "
                    f"{loader_display(loader, loader_version)} · "
                    f"{format_relative(featured.get('last_played'))}")
        chips = ft.Row(
            controls=[
                ui.pill(f"MC {featured.get('mc_version', '—')}", color="#FFFFFF",
                        bgcolor="#30000000"),
                ui.pill(loader_display(loader, loader_version), color="#FFFFFF",
                        bgcolor="#30000000"),
                ui.pill(f"{featured.get('mods_count', 0)} 个 mod", color="#FFFFFF",
                        bgcolor="#30000000"),
            ],
            spacing=8,
            wrap=True,
        )
        actions = ft.Row(
            controls=[
                ui.primary_button("启动游戏", lambda e: app.launch_instance(featured["folder"]),
                                  icon=ft.Icons.PLAY_ARROW_ROUNDED, height=46),
                ft.TextButton(
                    content=ft.Text("查看详情", color="#FFFFFFCC", size=12),
                    on_click=lambda e: app.navigate("instances"),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            spacing=8,
        )
        eyebrow = "继续游玩"
    else:
        title = "把世界装进启动器"
        subtitle = "导入整合包，或安装一个原版版本，然后按下开始。"
        chips = ft.Row(
            controls=[
                ui.pill("Modrinth", color="#FFFFFF", bgcolor="#30000000"),
                ui.pill("CurseForge", color="#FFFFFF", bgcolor="#30000000"),
                ui.pill("HMCL / PCL", color="#FFFFFF", bgcolor="#30000000"),
            ],
            spacing=8,
            wrap=True,
        )
        actions = ft.Row(
            controls=[
                ui.primary_button("导入整合包", lambda e: app.page.run_task(app.show_import_dialog),
                                  icon=ft.Icons.ADD_ROUNDED, height=46),
                ft.TextButton(
                    content=ft.Text("安装原版", color="#FFFFFFCC", size=12),
                    on_click=lambda e: app.navigate("versions"),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            spacing=8,
        )
        eyebrow = "开始之前"

    left = ft.Column(
        controls=[
            ft.Row([
                ft.Container(width=6, height=6, border_radius=3, bgcolor=p.accent),
                ft.Text(eyebrow, size=11.5, color="#B8FFFFFF", weight=ft.FontWeight.W_600),
            ], spacing=7),
            ft.Text(title, size=30, weight=ft.FontWeight.W_800, color="#FFFFFF",
                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(subtitle, size=12.5, color="#B0FFFFFF"),
            chips,
            actions,
        ],
        spacing=12,
        expand=True,
    )

    # 浅色主题里如果仍用淡色渐变，白色标题会看不清；给 hero 换一块深绿色
    # 背景，保持和深色主题一致的“白色大字 + 绿色按钮”对比度。
    if p.name == "light":
        hero_colors = ["#0C3B2D", "#156B4E", "#0C3B2D"]
    else:
        hero_colors = [p.accent_soft, p.surface_hi, p.surface]

    return ft.Container(
        content=ft.Stack(
            controls=[
                # 背景光斑：用大圆角容器 + 半透明色制造渐变层次
                ft.Container(width=360, height=360, border_radius=200, bgcolor="#0BFFFFFF",
                             right=-120, top=-150),
                ft.Container(width=180, height=180, border_radius=100, bgcolor="#10FFFFFF",
                             right=150, bottom=-90),
                ft.Container(
                    content=left,
                    padding=ft.Padding.only(left=28, right=200, top=24, bottom=24),
                ),
                ft.Container(
                    content=ui.block_logo(92),
                    right=44,
                    top=54,
                    rotate=-0.08,
                ),
                ft.Container(
                    content=ft.Container(width=26, height=26, border_radius=8,
                                         bgcolor="#22FFFFFF"),
                    right=160,
                    top=44,
                    rotate=0.2,
                ),
                ft.Container(
                    content=ft.Container(width=16, height=16, border_radius=5,
                                         bgcolor="#18FFFFFF"),
                    right=32,
                    top=170,
                ),
            ],
        ),
        height=236,
        border_radius=24,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=hero_colors,
            stops=[0.0, 0.55, 1.0],
        ),
        border=ft.Border.all(1, p.border),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def _quick_card(app, icon: str, title: str, subtitle: str, on_click) -> ft.Container:
    p = app.p
    card = ui.card(
        ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=20, color=p.accent),
                    width=42, height=42, border_radius=12, bgcolor=p.accent_soft,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=p.text),
                        ft.Text(subtitle, size=11, color=p.text_muted),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=16, color=p.text_faint),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
        hover=True,
    )
    card.on_click = on_click
    card.col = {"sm": 12, "md": 4, "lg": 4}
    return card
