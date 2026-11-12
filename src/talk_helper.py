from queue import Queue 
import tkinter as tk
import threading
from tkinter import ttk, messagebox
from ui_components import AutoScrollText
from voice_recognition import VoiceRecognition
from config_descriptioin import AppConfig
import time
import asyncio
from speech_translation_advisor import SpeechTranslationAdvisor
from dataclasses import dataclass

RECOGNITION_DATA_PULLING_RATE = 0.08

ADVISOR_CALL_RATE = 0.5

AutoScrollText_MAX_CHARS = 4000


@dataclass
class SpeechTranslationAdvice:
    speech: str = ""
    translation: str = ""
    advice: str = ""

class TalkHelperApp(tk.Tk):
    _audio_recognition_cancellation_token: threading.Event
    _voice_recognition: VoiceRecognition
    _container: ttk.PanedWindow
    _toolbar: ttk.Frame
    _speech_panel: AutoScrollText
    _translation_panel: AutoScrollText
    _advice_panel: AutoScrollText
    _audio_source_combox: ttk.Combobox

    _voice_data_queue_for_speech: Queue
    _voice_data_queue_for_advisor: Queue

    _audio_recognition_data: dict[int, SpeechTranslationAdvice]
    _speech_translation_advisor : SpeechTranslationAdvisor

    def __init__(self, app_config: AppConfig):
        super().__init__()

        self._audio_recognition_cancellation_token = threading.Event()
        self._audio_recognition_cancellation_token.set()

        self._audio_recognition_data = dict()
        self._voice_data_queue_for_speech = Queue()
        self._voice_data_queue_for_advisor = Queue()
        self._voice_recognition = VoiceRecognition(app_config.asr, app_config.audio)
        self._speech_translation_advisor = SpeechTranslationAdvisor(app_config.llm)

        self._init_ui()

        self.last_advisor_call = time.time()
        self.after(200, self._start_async_tasks)

    def _start_async_tasks(self):#no concurency in this tasks, because only 1 thread used, in await asyncio guarantee returning to main thread
        asyncio.create_task(self._pull_voice_data_speech())
        asyncio.create_task(self._pull_voice_data_advisor())

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

        self._speech_panel = AutoScrollText(self._container, "AudioRecognition", max_chars=AutoScrollText_MAX_CHARS)
        self._translation_panel = AutoScrollText(self._container, "Translation", max_chars=AutoScrollText_MAX_CHARS)
        self._advice_panel = AutoScrollText(self._container, "Tips", max_chars=AutoScrollText_MAX_CHARS)

        for panel in (self._speech_panel, self._translation_panel, self._advice_panel):
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

        def error_handler(info):
            messagebox.showerror("Error", info)\

        def put_in_queues(data):
            self._voice_data_queue_for_speech.put(data)    
            self._voice_data_queue_for_advisor.put(data)    

        self._audio_recognition_cancellation_token.clear()
        threading.Thread(
            target=self._voice_recognition.loop,
            args=(self._audio_source_combox.get(), put_in_queues, error_handler, self._audio_recognition_cancellation_token),
            daemon=True,
        ).start()

    def _stop_button_handler(self):
        self._audio_recognition_cancellation_token.set()
        time.sleep(0.2)#waiting until all threads finish and all queues have been handled

        full_text = SpeechTranslationAdvice()
        for text in self._audio_recognition_data.values():
            full_text.speech += text.speech
            full_text.advice += text.advice
            full_text.translation += text.translation
        self._audio_recognition_data.clear()
        self._audio_recognition_data[-1] = full_text

    async def _pull_voice_data_speech(self):
        was_empty = True
        while not self._voice_data_queue_for_speech.empty():
            was_empty = False
            data = self._voice_data_queue_for_speech.get_nowait()
            if data.id in self._audio_recognition_data:
                self._audio_recognition_data[data.id].speech = data.text
            else:
                self._audio_recognition_data[data.id] = SpeechTranslationAdvice(speech=data.text)
            
        if not was_empty:
            full_speech_text = ""
            for text in self._audio_recognition_data.values():
                full_speech_text+=text.speech

            self._speech_panel.clear()
            self._speech_panel.append(full_speech_text) 

            if len(full_speech_text) >= AutoScrollText_MAX_CHARS:
                self.clear_half_audio_recognition_data()

            print("speech panel updated")
            
        await asyncio.sleep(RECOGNITION_DATA_PULLING_RATE)
        asyncio.create_task(self._pull_voice_data_speech())

    async def _pull_voice_data_advisor(self):
        while not self._voice_data_queue_for_advisor.empty():
            data = self._voice_data_queue_for_advisor.get_nowait()
            if data.is_endpoint or (self._voice_data_queue_for_advisor.empty() and time.time() - self.last_advisor_call > ADVISOR_CALL_RATE 
                                    and data.id in self._audio_recognition_data and data != self._audio_recognition_data[data.id].speech):
                recent_recognition_data = [item for item in self._audio_recognition_data.values()]#fix
                recent_speech = ''.join(item.speech for item in recent_recognition_data[-5:])

                def error_handler(info):
                    messagebox.showerror("Error", info)
                translation, advice = await asyncio.gather(self._speech_translation_advisor.translate(recent_speech, data.text, error_handler), 
                                                    self._speech_translation_advisor.get_speaking_advice(recent_speech, data.text, error_handler))
                self.last_advisor_call = time.time()
                
                if data.id in self._audio_recognition_data:# second check because of await, clear function for example can clear whole dict
                    self._audio_recognition_data[data.id].translation = "<>" + translation
                    self._audio_recognition_data[data.id].advice = "\n" + advice

                full_translation_text = ""
                full_advice_text = ""
                for text in recent_recognition_data:
                    full_translation_text+=text.translation
                    full_advice_text+=text.advice

                self._translation_panel.clear()
                self._translation_panel.append(full_translation_text) 

                self._advice_panel.clear()
                self._advice_panel.append(full_advice_text) 

                print("translation advisor panels updated")
            
        await asyncio.sleep(RECOGNITION_DATA_PULLING_RATE)
        asyncio.create_task(self._pull_voice_data_advisor())

    def clear_half_audio_recognition_data(self):
        keys = list(self._audio_recognition_data.keys())
        for key in keys[:len(keys) // 2]:
            del self._audio_recognition_data[key]
        print("clear_half_audio_recognition_data")

    def _clear_all_button_handler(self):
        for panel in (self._speech_panel, self._translation_panel, self._advice_panel):
            panel.clear()
        self._audio_recognition_data.clear()
