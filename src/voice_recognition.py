import time
import soundcard
import numpy as np
from config_descriptioin import ASRConfig, AudioConfig, DiarizationConfig


class VoiceRecognition:
    _is_stopped: bool
    asr_config: ASRConfig
    diarization_config: DiarizationConfig
    audio_config: AudioConfig

    def __init__(
        self,
        asr_config: ASRConfig,
        diarization_config: DiarizationConfig,
        audio_config: AudioConfig,
    ):
        self.asr_config = asr_config
        self.diarization_config = diarization_config
        self.audio_config = audio_config
        self._is_stopped = True

    def loop(self, device: str, voice_recognized_callback, log_callback):
        self._is_stopped = False

        audio_source = soundcard.get_microphone(device, include_loopback=True)
        try:
            with audio_source.recorder(self.audio_config.sample_rate, 2 if audio_source.isloopback else 1, self.audio_config.block_size) as recorder, \
                soundcard.default_speaker().player(self.audio_config.sample_rate, 1, self.audio_config.block_size) as speaker:
                while not self._is_stopped:
                    voice_recognized_callback("looped " + device)
                    time.sleep(0.5)
                    recorded_data = recorder.record()
                    if audio_source.isloopback:
                        recorded_data.mean(axis=1).reshape(-1, 1).astype(np.float32) 

                    speaker.play(recorded_data)
        except:
            log_callback("Audio stream opening error, probably unsupported sample rate")


    def stop_loop(self):
        self._is_stopped = True

    @staticmethod
    def get_audio_sources() -> list[str]:
        sources: list[str] = []

        for mic in soundcard.all_microphones(include_loopback=True):
            sources.append(mic.name)

        return sources
