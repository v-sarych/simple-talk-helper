from queue import Queue 
import tkinter as tk
import threading
from tkinter import ttk, messagebox
from ui_components import AutoScrollText
from voice_recognition import VoiceRecognition
from config_descriptioin import AppConfig
import time

RECOGNITION_DATA_PULLING_RATE = 50

class TalkHelperApp(tk.Tk):
    _audio_recognition_cancellation_token: threading.Event
    _voice_recognition: VoiceRecognition
    _container: ttk.PanedWindow
    _toolbar: ttk.Frame
    _speech_panel: AutoScrollText
    _translation_panel: AutoScrollText
    _tips_panel: AutoScrollText
    _audio_source_combox: ttk.Combobox
    _voice_data_queue: Queue
    _audio_recognition_data: dict[int, str]

    def __init__(self, app_config: AppConfig):
        super().__init__()

        self._audio_recognition_cancellation_token = threading.Event()
        self._audio_recognition_cancellation_token.set()

        self._audio_recognition_data = dict()
        self._voice_data_queue = Queue()
        self._voice_recognition = VoiceRecognition(app_config.asr, app_config.audio)

        self._init_ui()

        self.after(RECOGNITION_DATA_PULLING_RATE, self._pull_voice_data)

    def _init_ui(self):
        self.title("simple-talk-helper")
        self.geometry(
            f"{self.winfo_screenwidth() * 2 // 3}x"
            f"{self.winfo_screenheight() * 2 // 4}"
        )
        self.minsize(
            self.winfo_screenwidth() // 4,
            self.winfo_screenheight() // 4,
        )

        style = ttk.Style(self)
        style.theme_use("clam")

        background = "#1e1e1e"
        foreground = "#d4d4d4"
        field_background = "#2d2d2d"
        button_background = "#3c3c3c"
        border = "#4a4a4a"
        selection_background = "#264f78"

        self.configure(background=background)
        style.configure(
            ".",
            background=background,
            foreground=foreground,
            fieldbackground=field_background,
            bordercolor=border,
            selectbackground=selection_background,
            selectforeground=foreground,
        )
        style.configure("Toolbar.TFrame", background=background)
        style.configure("TPanedwindow", background=background)
        style.configure("Sash", background=border)
        style.configure(
            "TButton",
            background=field_background,
            lightcolor=field_background,
            darkcolor=field_background,
            bordercolor=border,
        )
        style.map("TButton", background=[("active", border)])
        style.layout(
            "Vertical.TScrollbar",
            [
                (
                    "Vertical.Scrollbar.trough",
                    {
                        "sticky": "ns",
                        "children": [
                            ("Vertical.Scrollbar.thumb", {"sticky": "nswe"})
                        ],
                    },
                )
            ],
        )
        style.configure(
            "TScrollbar",
            width=10,
            gripsize=0,
            background=button_background,
            troughcolor=background,
            bordercolor=background,
            lightcolor=background,
            darkcolor=background,
        )
        style.map(
            "TScrollbar",
            background=[("disabled", button_background)],
            troughcolor=[("disabled", background)],
            bordercolor=[("disabled", background)],
            lightcolor=[("disabled", background)],
            darkcolor=[("disabled", background)],
        )
        style.configure(
            "TCombobox",
            padding=(6, 4),
            arrowsize=14,
            background=button_background,
            fieldbackground=field_background,
            foreground=foreground,
            arrowcolor=foreground,
            bordercolor=border,
            lightcolor=button_background,
            darkcolor=button_background,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", field_background)],
            foreground=[("readonly", foreground)],
            selectbackground=[("readonly", selection_background)],
        )
        self.option_add("*TCombobox*Listbox.background", field_background)
        self.option_add("*TCombobox*Listbox.foreground", foreground)
        self.option_add(
            "*TCombobox*Listbox.selectBackground", selection_background
        )

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
        if not self._audio_recognition_cancellation_token.is_set():
            messagebox.showinfo("Attention", "Loop already started")
            return

        if not self._audio_source_combox.get() or self._audio_source_combox.get() == "devices":
            messagebox.showinfo("Attention", "Select device")
            return

        def log_handler(info):
            messagebox.showinfo("Information", info)

        self._audio_recognition_cancellation_token.clear()
        threading.Thread(
            target=self._voice_recognition.loop,
            args=(self._audio_source_combox.get(), self._voice_data_queue.put, log_handler, self._audio_recognition_cancellation_token),
            daemon=True,
        ).start()

    def _stop_button_handler(self):
        self._audio_recognition_cancellation_token.set()
        time.sleep(0.2)#waiting until all threads finish and all queues have been handled

        full_text = ""
        for text in self._audio_recognition_data.values():
            full_text += text
        self._audio_recognition_data.clear()
        self._audio_recognition_data[-1] = full_text

    def _pull_voice_data(self):
        while not self._voice_data_queue.empty():
            data = self._voice_data_queue.get_nowait()
            self._audio_recognition_data[data.id] = data.text.lower()

        full_text = ""
        for text in self._audio_recognition_data.values():
            full_text+=text
        self._speech_panel.clear()
        self._speech_panel.append(full_text) 

        self.after(RECOGNITION_DATA_PULLING_RATE, self._pull_voice_data)

    def _clear_all_button_handler(self):
        self._audio_recognition_data.clear()
        for panel in (self._speech_panel, self._translation_panel, self._tips_panel):
            panel.clear()
