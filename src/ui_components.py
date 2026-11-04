#vibecoded
"""Reusable Tk widgets for the application window."""

import sys
import tkinter as tk
from tkinter import ttk


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
        factor = widget.winfo_fpixels("1i") / 96.0
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
        max_chars: int = 20000,
        *,
        font_family: str = "Segoe UI",
        body_font_size: int = 10,
        title_font_size: int = 10,
        background: str = "#1e1e1e",
        foreground: str = "#d4d4d4",
        selection_background: str = "#264f78",
        panel_min_width: int = 160,
        padding: int = 8,
        title_top_padding: int = 6,
        title_bottom_padding: int = 4,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._max_chars = max(0, max_chars)
        self._view_anchor: str | None = None

        padding_px = scale_px(self, padding)
        self.columnconfigure(
            0, weight=1, minsize=scale_px(self, panel_min_width)
        )
        self.rowconfigure(1, weight=1)

        self._title_label = tk.Label(
            self,
            text=title,
            background=background,
            foreground=foreground,
            font=(font_family, title_font_size, "bold"),
        )
        self._title_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=padding_px,
            pady=(
                scale_px(self, title_top_padding),
                scale_px(self, title_bottom_padding),
            ),
        )

        self.text = tk.Text(
            self,
            wrap="word",
            state="disabled",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=padding_px,
            pady=scale_px(self, title_top_padding),
            background=background,
            foreground=foreground,
            insertbackground=foreground,
            selectbackground=selection_background,
            font=(font_family, body_font_size),
        )
        self.text.grid(row=1, column=0, sticky="nsew")

        self._scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.text.yview
        )
        self._scrollbar.grid(row=1, column=1, sticky="ns")
        self.text.configure(yscrollcommand=self._scrollbar.set)

    def _at_bottom(self) -> bool:
        return self.text.yview()[1] >= 0.999

    def append(self, text: str) -> None:
        if not text:
            return

        stick_to_bottom = self._at_bottom()

        self.text.configure(state="normal")
        self.text.insert("end", text)
        self._trim_history()
        self.text.configure(state="disabled")

        if self._view_anchor is not None:
            self.text.yview(self._view_anchor)
            self._view_anchor = None
        elif stick_to_bottom:
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
        # talk_helper clears and re-appends the whole text on every update, so
        # remember the top line to keep a user who scrolled up in place.
        if self._at_bottom():
            self._view_anchor = None
        else:
            self._view_anchor = self.text.index("@0,0")

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
