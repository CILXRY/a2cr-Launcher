"""界面设计系统：颜色、字体、圆角、渐变和常用样式。

Flet 没有 CSS，所有视觉规则集中在这里，页面只引用 ``P``（当前调色板）和
``theme_for`` 等少量入口，避免每个页面各写一套魔法颜色。
"""

import hashlib
from dataclasses import dataclass

import flet as ft


@dataclass(frozen=True)
class Palette:
    """一套主题需要的颜色 token。"""

    name: str
    bg: str
    bg_soft: str
    surface: str
    surface_alt: str
    surface_hi: str
    border: str
    border_soft: str
    text: str
    text_muted: str
    text_faint: str
    accent: str
    accent_soft: str
    accent_ink: str
    accent2: str
    warning: str
    danger: str
    success: str
    shadow: str


DARK = Palette(
    name="dark",
    bg="#0A0E14",
    bg_soft="#0D121A",
    surface="#111821",
    surface_alt="#151E2A",
    surface_hi="#1B2634",
    border="#14FFFFFF",
    border_soft="#0AFFFFFF",
    text="#E9EEF5",
    text_muted="#93A1B3",
    text_faint="#647284",
    accent="#3DDC97",
    accent_soft="#123A2B",
    accent_ink="#04150E",
    accent2="#5EEAD4",
    warning="#F6C05B",
    danger="#FF6B6B",
    success="#4ADE80",
    shadow="#66000000",
)

LIGHT = Palette(
    name="light",
    bg="#F3F5F1",
    bg_soft="#EDF1EA",
    surface="#FFFFFF",
    surface_alt="#F7F9F5",
    surface_hi="#EDF2EC",
    border="#12162116",
    border_soft="#08162116",
    text="#16211B",
    text_muted="#5C6B60",
    text_faint="#8A978D",
    accent="#17A673",
    accent_soft="#DDF4E9",
    accent_ink="#FFFFFF",
    accent2="#0F8C8C",
    warning="#B7791F",
    danger="#D64545",
    success="#16885A",
    shadow="#1A2C3A2F",
)

# 实例封面的渐变色对。用名字做稳定哈希，重启后同一实例颜色不变。
_GRADIENTS = (
    ("#123B2E", "#0C6B4F", "#5EEAD4"),
    ("#1B2440", "#334C8C", "#93C5FD"),
    ("#2E1D3A", "#6D3A86", "#F0ABFC"),
    ("#3A2417", "#8A4B2A", "#FDBA74"),
    ("#1B2D33", "#2E6470", "#67E8F9"),
    ("#302A18", "#7A6425", "#FDE68A"),
)

# 加载器的品牌色/显示名。没有官方图标的用首字母 + 颜色区分。
LOADER_META = {
    "vanilla": ("原版", "#8FA3B8"),
    "fabric": ("Fabric", "#D9B36C"),
    "quilt": ("Quilt", "#C084FC"),
    "forge": ("Forge", "#E0714A"),
    "neoforge": ("NeoForge", "#F0A35E"),
}

ACCENTS = {
    "emerald": ("#3DDC97", "#5EEAD4", "#123A2B", "#04150E"),
    "cyan": ("#38BDF8", "#67E8F9", "#102F3D", "#041018"),
    "amber": ("#F6C05B", "#FDE68A", "#3A2B10", "#1A1204"),
}


def apply_accent(palette: Palette, accent: str) -> Palette:
    """返回替换了主色的调色板副本。"""
    primary, secondary, soft, ink = ACCENTS.get(accent, ACCENTS["emerald"])
    return Palette(**{**palette.__dict__, "accent": primary, "accent2": secondary,
                      "accent_soft": soft, "accent_ink": ink})


def gradient_for(seed: str) -> tuple[ft.LinearGradient, str]:
    """根据实例名生成稳定的封面渐变，并返回一个高光色。"""
    digest = hashlib.sha1(str(seed).encode("utf-8")).digest()
    index = digest[0] % len(_GRADIENTS)
    start, end, glow = _GRADIENTS[index]
    return (
        ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[start, end],
            stops=[0.0, 1.0],
        ),
        glow,
    )


def loader_meta(loader: str) -> tuple[str, str]:
    return LOADER_META.get((loader or "vanilla").lower(), (loader or "原版", "#8FA3B8"))


def _text_theme(palette: Palette) -> ft.TextTheme:
    """正文使用系统中文字体，标题保持紧凑的字重层级。"""
    base = dict(color=palette.text, font_family="Microsoft YaHei UI")
    return ft.TextTheme(
        display_large=ft.TextStyle(size=34, weight=ft.FontWeight.W_700, **base),
        display_medium=ft.TextStyle(size=28, weight=ft.FontWeight.W_700, **base),
        display_small=ft.TextStyle(size=24, weight=ft.FontWeight.W_700, **base),
        headline_large=ft.TextStyle(size=22, weight=ft.FontWeight.W_700, **base),
        headline_medium=ft.TextStyle(size=19, weight=ft.FontWeight.W_600, **base),
        headline_small=ft.TextStyle(size=17, weight=ft.FontWeight.W_600, **base),
        title_large=ft.TextStyle(size=16, weight=ft.FontWeight.W_600, **base),
        title_medium=ft.TextStyle(size=14, weight=ft.FontWeight.W_600, **base),
        title_small=ft.TextStyle(size=13, weight=ft.FontWeight.W_500, **base),
        body_large=ft.TextStyle(size=15, **base),
        body_medium=ft.TextStyle(size=13.5, **base),
        body_small=ft.TextStyle(size=12, **base),
        label_large=ft.TextStyle(size=13, weight=ft.FontWeight.W_500, **base),
        label_medium=ft.TextStyle(size=12, **base),
        label_small=ft.TextStyle(size=11, **base),
    )


def theme_for(palette: Palette) -> ft.Theme:
    """把调色板转成 Flet Theme。"""
    scheme = ft.ColorScheme(
        primary=palette.accent,
        on_primary=palette.accent_ink,
        primary_container=palette.accent_soft,
        on_primary_container=palette.accent,
        secondary=palette.accent2,
        on_secondary=palette.accent_ink,
        secondary_container=palette.surface_hi,
        on_secondary_container=palette.text,
        surface=palette.surface,
        on_surface=palette.text,
        surface_container=palette.surface,
        surface_container_high=palette.surface_alt,
        surface_container_highest=palette.surface_hi,
        on_surface_variant=palette.text_muted,
        outline=palette.border,
        outline_variant=palette.border_soft,
        error=palette.danger,
        on_error="#FFFFFF",
        shadow=palette.shadow,
    )
    return ft.Theme(
        color_scheme=scheme,
        font_family="Microsoft YaHei UI",
        text_theme=_text_theme(palette),
        scaffold_bgcolor=palette.bg,
        card_bgcolor=palette.surface,
        divider_color=palette.border,
        divider_theme=ft.DividerTheme(color=palette.border, space=1, thickness=1),
        visual_density=ft.VisualDensity.COMFORTABLE,
    )
