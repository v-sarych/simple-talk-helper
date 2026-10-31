import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from ui_components import AutoScrollText
from voice_recognition import VoiceRecognition
from config_descriptioin import AppConfig


class TalkHelperApp(tk.Tk):
    _is_stopped: bool
    _voice_recognition: VoiceRecognition
    _container: ttk.PanedWindow
    _toolbar: ttk.Frame
    _speech_panel: AutoScrollText
    _translation_panel: AutoScrollText
    _tips_panel: AutoScrollText
    _audio_source_combox: ttk.Combobox
    _voice_data_queue: queue.Queue

    def __init__(self, app_config: AppConfig):
        super().__init__()
        self._is_stopped = True
        self._voice_data_queue = queue.Queue()
        self._init_ui()

        self._voice_recognition = VoiceRecognition(app_config.asr, app_config.diarization, app_config.audio)

        self.after(30, self._pull_voice_data)

    def _init_ui(self):
        self.title("simple-talk-helper")
        self.geometry(
            f"{self.winfo_screenwidth() * 2 // 5}x"
            f"{self.winfo_screenheight() * 2 // 5}"
        )
        self.minsize(
            self.winfo_screenwidth() // 4,
            self.winfo_screenheight() // 4,
        )

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("PanelTitle.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Toolbar.TFrame")

        self._container = ttk.PanedWindow(self, orient="horizontal")
        self._container.pack(fill="both", expand=True, padx=8, pady=8)

        self._speech_panel = AutoScrollText(self._container, "AudioRecognition")
        self._translation_panel = AutoScrollText(self._container, "Translation")
        self._tips_panel = AutoScrollText(self._container, "Tips")

        for panel in (self._speech_panel, self._translation_panel, self._tips_panel):
            self._container.add(panel, weight=1)

        self._toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        self._toolbar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(self._toolbar, text="Start", command=self._start_button_handler).pack(
            side="left"
        )
        ttk.Button(self._toolbar, text="Stop", command=self._stop_button_handler).pack(
            side="left"
        )
        ttk.Button(self._toolbar, text="Clear", command=self._clear_all_button_handler).pack(
            side="left", padx=(8, 0)
        ) 

        self._audio_source_combox = ttk.Combobox(self._toolbar, state="readonly", width=25)
        self._audio_source_combox.pack(pady=20)
        self._audio_source_combox.bind("<Button-1>", self._audio_source_combox_open_handler)
        self._audio_source_combox.set("devices")

    def _audio_source_combox_open_handler(self, event):
        self._audio_source_combox["values"] = VoiceRecognition.get_audio_sources()

    def _start_button_handler(self):
        if not self._is_stopped:
            return

        if not self._audio_source_combox.get() or self._audio_source_combox.get() == "devices":
            messagebox.showinfo("Attention", "Select device")
            return

        self._is_stopped = False
        threading.Thread(
            target=self._voice_recognition.loop,
            args=(self._audio_source_combox.get(), self._voice_data_queue.put),
            daemon=True,
        ).start()

    def _stop_button_handler(self):
        self._is_stopped = True
        self._voice_recognition.stop_loop()

    def _pull_voice_data(self):
        while not self._voice_data_queue.empty():
            self._speech_panel.append_line(self._voice_data_queue.get_nowait())
        self.after(30, self._pull_voice_data)

    def _clear_all_button_handler(self):
        for panel in (self._speech_panel, self._translation_panel, self._tips_panel):
            panel.clear()
