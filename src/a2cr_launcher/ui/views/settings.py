"""设置页：玩家名、内存、Java、主题和数据目录。"""

from __future__ import annotations

import flet as ft

from ... import services
from ...ui import components as ui
from ...ui.utils import memory_gb, shorten_path


def _label(text: str, p) -> ft.Text:
    return ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=p.text)


def _hint(text: str, p) -> ft.Text:
    return ft.Text(text, size=11, color=p.text_muted)


def _text_field(value: str, p, *, hint: str = "", width=None, on_submit=None,
                on_blur=None) -> ft.TextField:
    return ft.TextField(
        value=value,
        hint_text=hint,
        bgcolor=p.bg_soft,
        border_color=p.border,
        focused_border_color=p.accent,
        color=p.text,
        hint_style=ft.TextStyle(color=p.text_faint, size=12),
        text_size=13,
        border_radius=10,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        width=width,
        on_submit=on_submit,
        on_blur=on_blur,
    )


def build(app) -> ft.Control:
    p = app.p
    header = ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text("设置", size=26, weight=ft.FontWeight.W_800, color=p.text),
                    ft.Text("这些设置会保存在本地，下次启动继续使用",
                            size=12.5, color=p.text_muted),
                ],
                spacing=4,
                expand=True,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    sections = [
        _profile_section(app),
        _launch_section(app),
        _appearance_section(app),
        _data_section(app),
        _about_section(app),
    ]
    return ft.Column(
        controls=[header, *sections],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _section(title: str, subtitle: str, content: ft.Control, app) -> ft.Container:
    p = app.p
    return ui.card(
        ft.Column(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(title, size=15, weight=ft.FontWeight.W_700, color=p.text),
                        ft.Text(subtitle, size=11.5, color=p.text_muted),
                    ],
                    spacing=2,
                ),
                ft.Container(height=1, bgcolor=p.border),
                content,
            ],
            spacing=14,
        ),
        padding=20,
    )


def _profile_section(app) -> ft.Container:
    p = app.p
    field = _text_field(
        app.settings.get("player_name", "a2Cr"), p, hint="游戏内显示的离线玩家名", width=280,
        on_submit=lambda e: _save_name(app, e),
        on_blur=lambda e: _save_name(app, e),
    )
    content = ft.Row(
        controls=[
            ft.Column(
                controls=[_label("玩家名", p), _hint("离线登录使用，不验证正版账号", p)],
                spacing=3,
                expand=True,
            ),
            field,
        ],
        spacing=20,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return _section("账号", "本地离线登录", content, app)


def _save_name(app, event) -> None:
    value = (event.control.value or "").strip() or "a2Cr"
    app.apply_settings({"player_name": value})


def _launch_section(app) -> ft.Container:
    p = app.p
    current_gb = memory_gb(app.settings.get("max_memory", "4G"))
    memory_label = ft.Text(f"{current_gb} GB", size=12, color=p.accent,
                           font_family="Consolas", width=58, text_align=ft.TextAlign.RIGHT)

    def change_memory(event):
        value = int(float(event.control.value))
        memory_label.value = f"{value} GB"
        app.page.update()

    def commit_memory(event):
        value = int(float(event.control.value))
        app.apply_settings({"max_memory": f"{value}G"})

    memory = ft.Row(
        controls=[
            ft.Column(
                controls=[_label("最大内存", p), _hint("大型整合包建议 6–10 GB", p)],
                spacing=3,
                width=170,
            ),
            ft.Slider(
                min=1, max=32, divisions=31, value=current_gb,
                active_color=p.accent, inactive_color=p.surface_hi,
                thumb_color=p.accent,
                label="{value} GB",
                expand=True,
                on_change=change_memory,
                on_change_end=commit_memory,
            ),
            memory_label,
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    java_options = [ft.DropdownOption(key="", text="自动选择（推荐）")]
    current_java = app.settings.get("java_path", "")
    known = {item["path"] for item in app.java_runtimes}
    if current_java and current_java not in known:
        java_options.append(ft.DropdownOption(key=current_java,
                                              text=f"自定义 · {shorten_path(current_java, 42)}"))
    for item in app.java_runtimes:
        java_options.append(ft.DropdownOption(
            key=item["path"],
            text=f"Java {item['major']} · {item.get('version', '')} · {shorten_path(item['path'], 38)}",
        ))

    dropdown = ft.Dropdown(
        value=current_java if current_java else "",
        options=java_options,
        bgcolor=p.bg_soft,
        border_color=p.border,
        focused_border_color=p.accent,
        color=p.text,
        text_size=12,
        border_radius=10,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        expand=True,
        on_select=lambda e: app.apply_settings({"java_path": e.control.value or ""}),
    )

    java_actions = ft.Row(
        controls=[
            ui.ghost_button("选择 Java 目录", lambda e: app.page.run_task(app.pick_java_directory),
                            icon=ft.Icons.FOLDER_OPEN_ROUNDED),
            ui.ghost_button("重新扫描", lambda e: app.page.run_task(app.refresh_java),
                            icon=ft.Icons.REFRESH_ROUNDED),
        ],
        spacing=4,
    )
    if not app.java_runtimes:
        java_hint = ft.Text("没有自动发现 Java，可以手动选择一个 Java 安装目录。",
                            size=11, color=p.warning)
    else:
        java_hint = _hint(f"已发现 {len(app.java_runtimes)} 个 Java；启动器会按版本自动匹配，固定后会优先使用。", p)

    content = ft.Column(
        controls=[
            memory,
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[_label("Java 运行时", p), java_hint],
                        spacing=3,
                        width=170,
                    ),
                    dropdown,
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            java_actions,
        ],
        spacing=14,
    )
    return _section("启动", "内存与 Java", content, app)


def _appearance_section(app) -> ft.Container:
    p = app.p
    mode = app.settings.get("theme", "dark")
    control = ft.SegmentedButton(
        segments=[
            ft.Segment(value="dark", label="深色", icon=ft.Icons.DARK_MODE_ROUNDED),
            ft.Segment(value="light", label="浅色", icon=ft.Icons.LIGHT_MODE_ROUNDED),
            ft.Segment(value="system", label="跟随系统", icon=ft.Icons.SETTINGS_BRIGHTNESS_ROUNDED),
        ],
        selected=[mode],
        allow_empty_selection=False,
        allow_multiple_selection=False,
        on_change=lambda e: _change_theme(app, e),
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: p.surface, ft.ControlState.SELECTED: p.accent_soft},
            color={ft.ControlState.DEFAULT: p.text_muted, ft.ControlState.SELECTED: p.accent},
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=14, vertical=9),
        ),
    )
    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[_label("主题", p),
                                  _hint("浅色主题适合白天；跟随系统会使用系统深浅色设置", p)],
                        spacing=3,
                        expand=True,
                    ),
                    control,
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=1, bgcolor=p.border),
            ft.Row(
                controls=[
                    ft.Column(controls=[_label("界面缩放", p),
                                        _hint("当前使用系统默认缩放，窄窗口会自动收起侧边栏", p)],
                              spacing=3, expand=True),
                    ui.pill("自动", color=p.text_muted, bgcolor=p.surface_hi),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=14,
    )
    return _section("外观", "主题与界面", content, app)


def _change_theme(app, event) -> None:
    selected = getattr(event.control, "selected", None) or []
    if selected:
        app.set_theme(selected[0])


def _data_section(app) -> ft.Container:
    p = app.p
    paths = services.data_dirs()
    rows = []
    for label, key in (("启动器目录", "root"), ("实例", "instances"),
                       ("版本", "versions"), ("回收站", "trash")):
        path = paths[key]
        rows.append(ft.Row(
            controls=[
                ft.Text(label, size=11.5, color=p.text_muted, width=86),
                ft.Text(shorten_path(path, 56), size=11.5, color=p.text,
                        font_family="Consolas", selectable=True, expand=True),
                ui.icon_action(ft.Icons.COPY_ROUNDED, "复制路径",
                               lambda e, value=path: app.copy_text(value)),
                ui.icon_action(ft.Icons.FOLDER_OPEN_ROUNDED, "打开目录",
                               lambda e, value=path: _open_path(app, value)),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ))
    content = ft.Column(controls=rows, spacing=6)
    return _section("数据", "所有文件都在本地启动器目录中", content, app)


def _open_path(app, path: str) -> None:
    try:
        services.open_path(path)
    except Exception as exc:
        app.show_toast(f"打开目录失败：{exc}", error=True)


def _about_section(app) -> ft.Container:
    p = app.p
    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ui.block_logo(44),
                    ft.Column(
                        controls=[
                            ft.Text("a2Cr Launcher", size=15, weight=ft.FontWeight.W_700,
                                    color=p.text),
                            ft.Text("一个迷你 Minecraft 启动器 · MIT License",
                                    size=11.5, color=p.text_muted),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ui.pill("v0.3.0", color=p.accent, bgcolor=p.accent_soft),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("由 CILXRY 制作的启动器",
                    size=11.5, color=p.text_muted),
            ft.Row(
                controls=[
                    ft.TextButton(
                        content="GitHub 仓库",
                        icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                        url="https://github.com/CILXRY/a2cr-Launcher",
                        style=ft.ButtonStyle(color=p.accent,
                                             shape=ft.RoundedRectangleBorder(radius=10)),
                    ),
                    ft.TextButton(
                        content="问题反馈",
                        icon=ft.Icons.BUG_REPORT_ROUNDED,
                        url="https://github.com/CILXRY/a2cr-Launcher/issues",
                        style=ft.ButtonStyle(color=p.text_muted,
                                             shape=ft.RoundedRectangleBorder(radius=10)),
                    ),
                ],
                spacing=4,
            ),
        ],
        spacing=12,
    )
    return _section("关于", "版本与反馈", content, app)
