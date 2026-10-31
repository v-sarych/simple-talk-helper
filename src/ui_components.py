#vibecoded
"""Reusable Tk widgets for the application window."""

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Optional

FONT_FAMILY = "Segoe UI"
BODY_FONT_SIZE = 10
TITLE_FONT_SIZE = 10

BACKGROUND = "#ffffff"
FOREGROUND = "#1f2328"
SELECTION_BACKGROUND = "#b6d7ff"

# Logical 96 DPI values, scaled to the real screen DPI at runtime.
BASE_DPI = 96.0
PANEL_MIN_WIDTH = 160
PANEL_PADDING = 8
TITLE_TOP_PADDING = 6
TITLE_BOTTOM_PADDING = 4

# Re-wrapping a long transcript is expensive, so the text area keeps its size
# while the window moves and catches up once the drag settles.
RESIZE_SETTLE_MS = 200

# Old lines are dropped above this many characters per panel so a long session
# does not make re-wrapping slower and slower. Use 0 to keep all history.
MAX_CHARS = 20000


def _enable_dpi_awareness() -> None:
    """Opt the process into DPI awareness before any Tk window exists.

    A DPI-unaware process is rendered at 96 DPI and then bitmap-stretched by
    Windows, which makes text blurry on displays with scaling other than 100%.
    Must run before ``tkinter.Tk()`` is created, so it runs at import time.
    """
    if sys.platform != "win32":
        return

    import ctypes

    try:
        # 1 == PROCESS_SYSTEM_DPI_AWARE. Per-monitor awareness is avoided on
        # purpose: Tk does not handle DPI changes when moving between monitors
        # and would leave the text blurry there.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        # Windows 7 fallback, or awareness already set by the host process.
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_dpi_awareness()


def scale_px(widget: tk.Misc, value: float) -> int:
    """Convert a logical 96 DPI pixel value to the actual screen DPI."""
    try:
        factor = widget.winfo_fpixels("1i") / BASE_DPI
    except tk.TclError:
        factor = 1.0
    return max(1, int(round(value * factor)))


class AutoScrollText(ttk.Frame):
    """A titled text block with a scrollbar.

    New text sticks to the bottom automatically, but only while the user is
    already at the bottom. If the user scrolled up, autoscroll stays out of the
    way so the text can be read comfortably.
    """

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        max_chars: int = MAX_CHARS,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._max_chars = max(0, max_chars)
        self._resize_job: Optional[str] = None
        self._resize_active = False

        self.columnconfigure(0, weight=1, minsize=scale_px(self, PANEL_MIN_WIDTH))
        self.rowconfigure(1, weight=1)

        # Named fonts keep a single source of truth and stay crisp because
        # their sizes are given in points rather than device pixels.
        self._body_font = tkfont.Font(
            self, family=FONT_FAMILY, size=BODY_FONT_SIZE
        )
        self._title_font = tkfont.Font(
            self, family=FONT_FAMILY, size=TITLE_FONT_SIZE, weight="bold"
        )

        self.title_label = ttk.Label(
            self,
            text=title,
            style="PanelTitle.TLabel",
            font=self._title_font,
        )
        self.title_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=scale_px(self, PANEL_PADDING),
            pady=(
                scale_px(self, TITLE_TOP_PADDING),
                scale_px(self, TITLE_BOTTOM_PADDING),
            ),
        )

        # The text lives in its own viewport, so it can keep its pixel size
        # while the window is dragged and only re-wrap once the drag settles.
        self._viewport = tk.Frame(
            self,
            background=BACKGROUND,
            borderwidth=0,
            highlightthickness=0,
        )
        self._viewport.grid(row=1, column=0, sticky="nsew")
        self._viewport.bind("<Configure>", self._on_viewport_configure, add="+")

        self.text = tk.Text(
            self._viewport,
            wrap="word",
            state="disabled",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=scale_px(self, PANEL_PADDING),
            pady=scale_px(self, TITLE_TOP_PADDING),
            background=BACKGROUND,
            foreground=FOREGROUND,
            insertbackground=FOREGROUND,
            selectbackground=SELECTION_BACKGROUND,
            font=self._body_font,
        )
        self.text.place(x=0, y=0, width=1, height=1)

        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.text.yview
        )
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.text.configure(yscrollcommand=self.scrollbar.set)

    def _on_viewport_configure(self, event: tk.Event) -> None:
        # Leading edge: follow the first size change right away so the panel
        # never looks stale when a drag begins.
        if not self._resize_active:
            self._resize_active = True
            self._apply_text_size()

        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(RESIZE_SETTLE_MS, self._finish_resize)

    def _finish_resize(self) -> None:
        self._resize_job = None
        self._resize_active = False
        self._apply_text_size()

    def _apply_text_size(self) -> None:
        width = self._viewport.winfo_width()
        height = self._viewport.winfo_height()
        if width > 1 and height > 1:
            self.text.place_configure(width=width, height=height)

    def destroy(self) -> None:
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None
        super().destroy()

    def _at_bottom(self) -> bool:
        return self.text.yview()[1] >= 0.999

    def append(self, text: str) -> None:
        self._insert(text)

    def append_line(self, text: str = "") -> None:
        self._insert(text + "\n")

    def _insert(self, text: str) -> None:
        if not text:
            return
        stick_to_bottom = self._at_bottom()

        self.text.configure(state="normal")
        self.text.insert("end", text)
        self._trim_history()
        self.text.configure(state="disabled")

        if stick_to_bottom:
            self.text.see("end")

    def _trim_history(self) -> None:
        """Drop the oldest full lines once the buffer exceeds ``max_chars``."""
        if self._max_chars <= 0:
            return
        total = self.text.count("1.0", "end-1c", "chars")
        if not total:
            return
        excess = int(total[0]) - self._max_chars
        if excess <= 0:
            return
        # Jump to the beginning of a later line so whole lines stay intact and
        # the buffer never keeps a partially trimmed line.
        start = self.text.index(f"1.0 + {excess} chars")
        end = self.text.index(f"{start} + 1 lines linestart")
        self.text.delete("1.0", end)

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
