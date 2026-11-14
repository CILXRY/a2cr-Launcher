"""可复用的界面组件。

页面尽量只组合这里的卡片、按钮、标签和空状态，避免每个页面重复写颜色/圆角。
调色板通过 ``set_palette`` 在运行时切换；切换主题后整体重建界面。
"""

from __future__ import annotations

import flet as ft

from . import theme
from .theme import DARK, Palette
from .utils import initial_of

P: Palette = DARK


def set_palette(palette: Palette) -> None:
    """更新组件使用的调色板。切换主题后调用。"""
    global P
    P = palette


def _hover_lift(container: ft.Container, accent: str | None = None) -> None:
    """鼠标悬停时轻微上浮并描边，给卡片一点“可点击”的反馈。"""

    def on_hover(event):
        active = str(getattr(event, "data", "")).lower() == "true"
        # Flet 的 Offset 是相对控件尺寸的比例，不是像素；-0.01 约等于上浮 2px
        container.offset = ft.Offset(0, -0.012 if active else 0)
        container.border = ft.Border.all(1, (accent or P.accent) if active else P.border)
        container.shadow = ft.BoxShadow(
            blur_radius=26 if active else 16,
            color="#55000000" if active else P.shadow,
            offset=ft.Offset(0, 10 if active else 5),
        )
        if event.page:
            event.page.update()

    container.animate_offset = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
    container.animate = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
    container.on_hover = on_hover


def card(content: ft.Control, *, padding=20, height=None, bgcolor=None, radius=18,
         hover=False, expand=False) -> ft.Container:
    """统一的卡片容器。"""
    container = ft.Container(
        content=content,
        padding=padding,
        height=height,
        expand=expand,
        bgcolor=bgcolor or P.surface,
        border=ft.Border.all(1, P.border),
        border_radius=radius,
        shadow=ft.BoxShadow(blur_radius=16, color=P.shadow, offset=ft.Offset(0, 5)),
    )
    if hover:
        _hover_lift(container)
    return container


def section_header(title: str, subtitle: str | None = None, action: ft.Control | None = None) -> ft.Row:
    """页面里的分组标题，右侧可以放一个操作按钮。"""
    texts = [
        ft.Text(title, size=18, weight=ft.FontWeight.W_700, color=P.text),
    ]
    if subtitle:
        texts.append(ft.Text(subtitle, size=12, color=P.text_muted))
    return ft.Row(
        controls=[
            ft.Column(texts, spacing=3, expand=True),
            *([action] if action is not None else []),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def pill(text: str, *, color: str | None = None, bgcolor: str | None = None,
         icon: str | None = None, border: bool = False) -> ft.Container:
    """小圆角标签，用于加载器、版本类型、状态。"""
    controls: list[ft.Control] = []
    if icon:
        controls.append(ft.Icon(icon, size=12, color=color or P.accent))
    controls.append(ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=color or P.accent))
    return ft.Container(
        content=ft.Row(controls, spacing=4, tight=True),
        padding=ft.Padding.symmetric(horizontal=9, vertical=4),
        bgcolor=bgcolor or P.accent_soft,
        border=ft.Border.all(1, color or P.accent) if border else None,
        border_radius=999,
    )


def primary_button(text: str, on_click, *, icon: str | None = None, disabled: bool = False,
                   width=None, height=42, tooltip: str | None = None) -> ft.FilledButton:
    """主操作按钮，绿色实心。"""
    row_controls: list[ft.Control] = []
    if icon:
        row_controls.append(ft.Icon(icon, size=18, color=P.accent_ink))
    row_controls.append(ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=P.accent_ink))
    return ft.FilledButton(
        content=ft.Row(row_controls, spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click,
        disabled=disabled,
        tooltip=tooltip,
        width=width,
        height=height,
        style=ft.ButtonStyle(
            bgcolor=P.accent,
            color=P.accent_ink,
            elevation=0,
            padding=ft.Padding.symmetric(horizontal=18, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )


def tonal_button(text: str, on_click, *, icon: str | None = None, disabled: bool = False,
                 height=42, width=None) -> ft.FilledTonalButton:
    """次级按钮，使用淡色底。"""
    row_controls: list[ft.Control] = []
    if icon:
        row_controls.append(ft.Icon(icon, size=17, color=P.text))
    row_controls.append(ft.Text(text, size=13, color=P.text))
    return ft.FilledTonalButton(
        content=ft.Row(row_controls, spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        on_click=on_click,
        disabled=disabled,
        height=height,
        width=width,
        style=ft.ButtonStyle(
            bgcolor=P.surface_hi,
            color=P.text,
            elevation=0,
            padding=ft.Padding.symmetric(horizontal=16, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )


def ghost_button(text: str, on_click, *, icon: str | None = None, disabled: bool = False,
                 height=38, color: str | None = None) -> ft.TextButton:
    """无底色操作按钮。"""
    row_controls: list[ft.Control] = []
    if icon:
        row_controls.append(ft.Icon(icon, size=16, color=color or P.text_muted))
    row_controls.append(ft.Text(text, size=12, color=color or P.text_muted))
    return ft.TextButton(
        content=ft.Row(row_controls, spacing=6, tight=True),
        on_click=on_click,
        disabled=disabled,
        height=height,
        style=ft.ButtonStyle(
            color=color or P.text_muted,
            padding=ft.Padding.symmetric(horizontal=10, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )


def icon_action(icon: str, tooltip: str, on_click, *, color: str | None = None,
                disabled: bool = False) -> ft.IconButton:
    """只有图标的操作按钮，带 tooltip。"""
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        on_click=on_click,
        disabled=disabled,
        icon_size=18,
        width=36,
        height=36,
        icon_color=color or P.text_muted,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            overlay_color=P.surface_hi,
        ),
    )


def stat_card(icon: str, value: str, label: str, *, color: str | None = None) -> ft.Container:
    """首页的三张小统计卡。"""
    accent = color or P.accent
    return card(
        ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=18, color=accent),
                    width=38,
                    height=38,
                    border_radius=11,
                    bgcolor=P.accent_soft if accent == P.accent else P.surface_hi,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(value, size=18, weight=ft.FontWeight.W_700, color=P.text),
                        ft.Text(label, size=11, color=P.text_muted),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
        expand=True,
    )


def empty_state(icon: str, title: str, description: str,
                actions: list[ft.Control] | None = None) -> ft.Container:
    """没有实例/没有日志时的引导状态。"""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=30, color=P.accent),
                    width=68,
                    height=68,
                    border_radius=22,
                    bgcolor=P.accent_soft,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(title, size=18, weight=ft.FontWeight.W_700, color=P.text,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(description, size=12.5, color=P.text_muted,
                        text_align=ft.TextAlign.CENTER),
                ft.Row(actions or [], spacing=10, alignment=ft.MainAxisAlignment.CENTER, wrap=True),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.Padding.symmetric(vertical=30, horizontal=24),
        border=ft.Border.all(1, P.border),
        border_radius=20,
        bgcolor=P.bg_soft,
        alignment=ft.Alignment.CENTER,
    )


def cover_art(name: str, loader: str, *, height=116, radius=16, width=None,
              show_loader: bool = True) -> ft.Container:
    """实例封面：稳定渐变 + 方块装饰 + 首字，不依赖外部图片。"""
    gradient, glow = theme.gradient_for(name)
    label, _loader_color = theme.loader_meta(loader)
    initial_size = max(26, min(56, int(height * 0.46)))
    blocks = ft.Row(
        controls=[
            ft.Container(width=10, height=10, bgcolor="#22FFFFFF", border_radius=2),
            ft.Container(width=18, height=18, bgcolor="#18FFFFFF", border_radius=3),
            ft.Container(width=8, height=8, bgcolor="#33FFFFFF", border_radius=2),
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.END,
    )
    top_right_items: list[ft.Control] = [blocks]
    if show_loader:
        top_right_items.append(ft.Row(
            controls=[pill(label, color="#FFFFFF", bgcolor="#33000000")],
            alignment=ft.MainAxisAlignment.END,
        ))
    return ft.Container(
        height=height,
        width=width,
        border_radius=radius,
        gradient=gradient,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Stack(
            controls=[
                # 两个半透明圆形制造一点景深，避免纯色封面太单调
                ft.Container(width=160, height=160, border_radius=100, bgcolor="#0DFFFFFF",
                             right=-36, top=-64),
                ft.Container(width=90, height=90, border_radius=100, bgcolor="#12FFFFFF",
                             left=-28, bottom=-38),
                ft.Container(
                    content=ft.Text(initial_of(name), size=initial_size,
                                    weight=ft.FontWeight.W_800, color="#CCFFFFFF"),
                    left=18, top=14,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=top_right_items,
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    right=12,
                    top=12,
                    bottom=12,
                ),
                ft.Container(
                    content=ft.Icon(ft.Icons.VIEW_IN_AR_ROUNDED, size=20, color=f"{glow}CC"),
                    right=14,
                    bottom=12,
                ),
            ],
        ),
    )


def block_logo(size: int = 36) -> ft.Container:
    """用 3×3 色块拼一个像素方块，作为启动器 logo。"""
    colors = [
        [P.accent, P.accent2, P.accent],
        [P.accent2, P.accent, P.accent2],
        [P.accent, P.accent2, P.accent],
    ]
    rows = []
    for row in colors:
        rows.append(ft.Row(
            controls=[ft.Container(width=size / 4.2, height=size / 4.2, bgcolor=color,
                                   border_radius=2) for color in row],
            spacing=2,
            tight=True,
        ))
    return ft.Container(
        content=ft.Column(rows, spacing=2, tight=True),
        width=size,
        height=size,
        padding=4,
        border_radius=10,
        bgcolor=P.surface_hi,
        alignment=ft.Alignment.CENTER,
        border=ft.Border.all(1, P.border),
    )


def divider() -> ft.Container:
    """1px 分隔线，比 Divider 更可控。"""
    return ft.Container(height=1, bgcolor=P.border, margin=ft.Margin.symmetric(vertical=8))
