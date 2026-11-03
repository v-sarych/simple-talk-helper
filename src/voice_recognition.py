import time
import soundcard
import numpy as np
import threading
import sherpa_onnx
from queue import Queue 
from config_descriptioin import ASRConfig, AudioConfig, DiarizationConfig


class VoiceRecognition:
    _asr_config: ASRConfig
    _diarization_config: DiarizationConfig
    _audio_config: AudioConfig


    def __init__(
        self,
        asr_config: ASRConfig,
        diarization_config: DiarizationConfig,
        audio_config: AudioConfig,
    ):
        self._asr_config = asr_config
        self._diarization_config = diarization_config
        self._audio_config = audio_config


    def loop(self, device: str, voice_recognized_callback, log_callback, cancellation_token: threading.Event):
        _audio_queue = Queue()
        
        voice_recognized_callback("Audio loop started\n")
        
        threading.Thread(
            target=self._recognition_loop,
            args=(_audio_queue, voice_recognized_callback, log_callback, cancellation_token),
            daemon=True,
        ).start()

        audio_source = soundcard.get_microphone(device, include_loopback=True)
        try:
            with audio_source.recorder(self._audio_config.sample_rate, 2 if audio_source.isloopback else 1, self._audio_config.block_size) as recorder:
                while not cancellation_token.is_set():

                    recorded_data = recorder.record(self._audio_config.block_size)
                    if audio_source.isloopback:
                        recorded_data = recorded_data.mean(axis=1).reshape(-1, 1).astype(np.float32) 

                    _audio_queue.put(recorded_data)
        except:
            log_callback("Audio stream opening error, probably unsupported sample rate")

            
    def _recognition_loop(self, _audio_queue: Queue, voice_recognized_callback, log_callback, cancellation_token: threading.Event):
        voice_recognized_callback("Recognition loop started\n")
        with soundcard.default_speaker().player(self._audio_config.sample_rate, 1, self._audio_config.block_size) as speaker:
            while not cancellation_token.is_set():
                audio_batches = []
                while not _audio_queue.empty():
                    audio_batches.append(_audio_queue.get_nowait())

                if len(audio_batches) > 0:
                    audio_batch = audio_batches[0] if len(audio_batches) == 1 else np.concatenate(audio_batches, axis=0)
                    #speaker.play(audio_batch)

                    audio_batch = audio_batch.flatten().astype(np.float32)


    @staticmethod
    def get_audio_sources() -> list[str]:
        sources: list[str] = []

        for mic in soundcard.all_microphones(include_loopback=True):
            sources.append(mic.name)

        return sources
