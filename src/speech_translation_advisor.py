from config_descriptioin import LLMConfig
from queue import Queue 
import threading

class SpeechTranslationAdvisor:
    _llm_config: LLMConfig
    def __init__(self, llm_config: LLMConfig):
        _llm_config = llm_config

    # def loop(speech_queue: Queue, translation_callback, advice_callback, cancellation_token: threading.Event):
    #     pass

    def translate(text:str):
        pass

    def get_speaking_advice(text:str):
        pass