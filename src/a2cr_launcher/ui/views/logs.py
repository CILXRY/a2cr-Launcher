"""日志页：实时显示启动器、导入器和游戏进程的输出。"""

from __future__ import annotations

import flet as ft

from ...ui import components as ui
from ...ui.state import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARN, LogEntry

LEVEL_COLORS = {
    LEVEL_INFO: "#A9B7C6",
    LEVEL_WARN: "#F6C05B",
    LEVEL_ERROR: "#FF7B7B",
}
LEVEL_COLORS_LIGHT = {
    LEVEL_INFO: "#334155",
    LEVEL_WARN: "#B45309",
    LEVEL_ERROR: "#B91C1C",
}
MAX_VISIBLE = 1500


class LogsView:
    """日志页有自己的过滤状态；日志数据仍然放在 ``App.log_entries`` 里。"""

    def __init__(self, app):
        self.app = app
        self.p = app.p
        self.level = "all"
        self.query = ""
        self.paused = False
        self.auto_scroll = True
        self.rows: list[ft.Control] = []
        self.root = self._build()

    def build(self) -> ft.Control:
        return self.root

    def _build(self) -> ft.Control:
        p = self.p
        self.list_view = ft.Column(
            controls=[],
            spacing=1,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=self.auto_scroll,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.empty_hint = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.TERMINAL_ROUNDED, size=30, color=p.text_faint),
                    ft.Text("还没有日志", size=14, color=p.text_muted),
                    ft.Text("启动游戏或导入整合包后，输出会出现在这里。",
                            size=11.5, color=p.text_faint),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
        )
        self.body = ft.Container(content=self.empty_hint, expand=True)

        self._rebuild_rows()

        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("运行日志", size=26, weight=ft.FontWeight.W_800, color=p.text),
                        ft.Text("启动器 / 导入器 / 游戏进程的实时输出",
                                size=12.5, color=p.text_muted),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ui.ghost_button("清空", lambda e: self.clear(), icon=ft.Icons.DELETE_SWEEP_ROUNDED),
                ui.ghost_button("打开数据目录", lambda e: self.app.open_data_dir(),
                                icon=ft.Icons.FOLDER_OPEN_ROUNDED),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        level_control = ft.SegmentedButton(
            segments=[
                ft.Segment(value="all", label="全部"),
                ft.Segment(value=LEVEL_INFO, label="信息"),
                ft.Segment(value=LEVEL_WARN, label="警告"),
                ft.Segment(value=LEVEL_ERROR, label="错误"),
            ],
            selected=[self.level],
            allow_empty_selection=False,
            allow_multiple_selection=False,
            on_change=self._change_level,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: p.surface, ft.ControlState.SELECTED: p.accent_soft},
                color={ft.ControlState.DEFAULT: p.text_muted, ft.ControlState.SELECTED: p.accent},
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            ),
        )
        self.search_field = ft.TextField(
            hint_text="搜索日志，回车确认",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            bgcolor=p.surface,
            border_color=p.border,
            focused_border_color=p.accent,
            color=p.text,
            hint_style=ft.TextStyle(color=p.text_faint, size=12),
            text_size=12,
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=9),
            width=240,
            on_submit=self._search,
        )
        self.auto_switch = ft.Switch(
            label="自动滚动", value=self.auto_scroll, active_color=p.accent,
            label_text_style=ft.TextStyle(color=p.text_muted, size=11),
            on_change=self._toggle_auto,
        )
        self.pause_switch = ft.Switch(
            label="暂停刷新", value=self.paused, active_color=p.accent,
            label_text_style=ft.TextStyle(color=p.text_muted, size=11),
            on_change=self._toggle_pause,
        )
        toolbar = ft.Row(
            controls=[level_control, self.search_field, ft.Container(expand=True),
                      self.pause_switch, self.auto_switch],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._rebuild_rows()
        return ft.Column(controls=[header, toolbar, self.body], spacing=14, expand=True)

    # ---------- 数据 ----------
    def _accepts(self, entry: LogEntry) -> bool:
        if self.level != "all" and entry.level != self.level:
            return False
        return not self.query or self.query in entry.text.lower()

    def append(self, entries: list[LogEntry]) -> None:
        if self.paused or not entries:
            return
        new_controls = []
        for entry in entries:
            if not self._accepts(entry):
                continue
            control = self._row(entry)
            self.rows.append(control)
            new_controls.append(control)
        if not new_controls:
            return
        if len(self.rows) > MAX_VISIBLE:
            self.rows = self.rows[-MAX_VISIBLE:]
            self.list_view.controls = self.rows
        else:
            self.list_view.controls.extend(new_controls)
        self.empty_hint.visible = False
        self.body.content = self.list_view
        if self.auto_scroll:
            self.list_view.auto_scroll = True
        try:
            self.list_view.update()
            self.body.update()
        except Exception:
            # 页面还没挂到窗口上时 update 会失败，等下一次 build 再画
            pass

    def _rebuild_rows(self) -> None:
        self.rows = [self._row(entry) for entry in self.app.log_entries if self._accepts(entry)]
        self.rows = self.rows[-MAX_VISIBLE:]
        self.list_view.controls = self.rows
        self.empty_hint.visible = not self.rows
        self.body.content = self.list_view if self.rows else self.empty_hint

    def _row(self, entry: LogEntry) -> ft.Control:
        p = self.p
        palette = LEVEL_COLORS_LIGHT if p.name == "light" else LEVEL_COLORS
        color = palette.get(entry.level, p.text_muted)
        source_color = p.accent if entry.source in ("启动器", "系统") else p.text_faint
        return ft.Row(
            controls=[
                ft.Text(entry.time, size=10, font_family="Consolas", color=p.text_faint,
                        width=58, no_wrap=True),
                ft.Text(entry.source, size=10, color=source_color, width=48, no_wrap=True),
                ft.Text(entry.text, size=10.5, font_family="Consolas", color=color,
                        selectable=True, expand=True),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    # ---------- 过滤 ----------
    def _change_level(self, event) -> None:
        selected = getattr(event.control, "selected", None) or []
        self.level = selected[0] if selected else "all"
        self._rebuild_rows()
        self.app.page.update()

    def _search(self, event) -> None:
        self.query = (event.control.value or "").strip().lower()
        self._rebuild_rows()
        self.app.page.update()

    def _toggle_auto(self, event) -> None:
        self.auto_scroll = bool(event.control.value)
        self.list_view.auto_scroll = self.auto_scroll
        self.app.page.update()

    def _toggle_pause(self, event) -> None:
        self.paused = bool(event.control.value)
        if not self.paused:
            self._rebuild_rows()
            self.app.page.update()

    def clear(self) -> None:
        self.app.log_entries.clear()
        self.rows.clear()
        self.list_view.controls.clear()
        self.empty_hint.visible = True
        self.body.content = self.empty_hint
        self.app.page.update()
