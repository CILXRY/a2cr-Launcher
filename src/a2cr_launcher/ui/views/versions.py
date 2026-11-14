"""版本页：浏览 Mojang 版本列表并安装原版。"""

from __future__ import annotations

import flet as ft

from ...ui import components as ui
from ...ui.utils import format_date


def build(app) -> ft.Control:
    p = app.p
    header = ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text("版本库", size=26, weight=ft.FontWeight.W_800, color=p.text),
                    ft.Text("安装原版客户端；整合包会自动处理对应的加载器",
                            size=12.5, color=p.text_muted),
                ],
                spacing=4,
                expand=True,
            ),
            ui.icon_action(ft.Icons.REFRESH_ROUNDED, "刷新版本列表",
                           lambda e: app.page.run_task(app.load_remote_versions, app.version_filter,
                                                       False)),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    filter_control = ft.SegmentedButton(
        segments=[
            ft.Segment(value="release", label="正式版"),
            ft.Segment(value="snapshot", label="快照"),
            ft.Segment(value="all", label="全部"),
        ],
        selected=[app.version_filter],
        allow_empty_selection=False,
        allow_multiple_selection=False,
        on_change=lambda e: _change_filter(app, e),
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: p.surface, ft.ControlState.SELECTED: p.accent_soft},
            color={ft.ControlState.DEFAULT: p.text_muted, ft.ControlState.SELECTED: p.accent},
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        ),
    )

    search = ft.TextField(
        hint_text="搜索版本号，例如 1.21",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        bgcolor=p.surface,
        border_color=p.border,
        focused_border_color=p.accent,
        color=p.text,
        hint_style=ft.TextStyle(color=p.text_faint, size=12),
        text_size=12.5,
        border_radius=10,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        width=260,
    )

    toolbar = ft.Row(
        controls=[filter_control, ft.Container(expand=True), search],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if app.version_loading:
        body: ft.Control = ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressRing(width=28, height=28, stroke_width=2, color=p.accent),
                    ft.Text("正在获取版本列表…", size=12.5, color=p.text_muted),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            height=220,
        )
    elif not app.remote_versions:
        message = app.version_error or "没有拿到版本列表"
        body = ui.empty_state(
            ft.Icons.CLOUD_OFF_OUTLINED,
            "版本列表不可用",
            f"{message}\n如果是网络问题，检查代理后点刷新。",
            actions=[ui.tonal_button(
                "重试", lambda e: app.page.run_task(app.load_remote_versions, app.version_filter),
                icon=ft.Icons.REFRESH_ROUNDED,
            )],
        )
    else:
        installed = {item.get("id") for item in app.installed_versions}
        rows = []
        lookup: list[tuple[str, ft.Control]] = []
        for item in app.remote_versions:
            row = _version_row(app, item, item.get("id") in installed)
            rows.append(row)
            lookup.append((str(item.get("id", "")).lower(), row))

        def filter_rows(event):
            query = (event.control.value or "").strip().lower()
            for version_id, row in lookup:
                row.visible = query in version_id
            app.page.update()

        search.on_change = filter_rows
        # 80 个版本用 Column 足够；ListView 在部分 Flet 版本里对 expand 的父容器
        # 约束比较敏感，会渲染成一块空白/灰色占位。
        body = ft.Column(controls=rows, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    warning = None
    if app.version_error and app.remote_versions:
        warning = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, size=15, color=p.warning),
                ft.Text(f"远程版本列表获取失败，正在显示缓存：{app.version_error}",
                        size=11.5, color=p.warning, expand=True),
            ], spacing=8),
            bgcolor=p.surface_hi,
            border_radius=10,
            padding=10,
        )

    controls = [header, toolbar]
    if warning is not None:
        controls.append(warning)
    controls.append(body)
    return ft.Column(controls=controls, spacing=14, expand=True)


def _change_filter(app, event) -> None:
    selected = getattr(event.control, "selected", None) or []
    if selected:
        app.set_version_filter(selected[0])


def _version_row(app, item: dict, installed: bool) -> ft.Container:
    p = app.p
    version_id = str(item.get("id", ""))
    version_type = item.get("type", "release")
    is_snapshot = version_type == "snapshot"
    type_label = "快照" if is_snapshot else "正式版"
    type_color = p.warning if is_snapshot else p.accent

    if installed:
        action: ft.Control = ui.pill("已安装", color=p.success, bgcolor=p.surface_hi,
                                     icon=ft.Icons.CHECK_ROUNDED)
    else:
        action = ui.tonal_button(
            "安装", lambda e, version=version_id: app.start_install_task(version),
            icon=ft.Icons.DOWNLOAD_ROUNDED, height=34,
        )

    row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Icon(ft.Icons.LAYERS_ROUNDED, size=17,
                                color=p.accent if not is_snapshot else p.warning),
                width=34, height=34, border_radius=10, bgcolor=p.surface_hi,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Text(version_id, size=13, weight=ft.FontWeight.W_600, color=p.text),
                    ft.Text(format_date(item.get("release_time")), size=11, color=p.text_faint),
                ],
                spacing=2,
                expand=True,
            ),
            ui.pill(type_label, color=type_color, bgcolor=p.surface_hi),
            action,
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return ui.card(row, padding=12, hover=not installed)
