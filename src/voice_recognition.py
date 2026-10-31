import time
import soundcard
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

    def loop(self, device: str, voice_recognized_callback):
        self._is_stopped = False
        while not self._is_stopped:
            voice_recognized_callback("looped " + device)

            time.sleep(0.5)

    def stop_loop(self):
        self._is_stopped = True

    @staticmethod
    def get_audio_sources() -> list[str]:
        sources: list[str] = []

        for mic in soundcard.all_microphones(include_loopback=True):
            sources.append(mic.name)
        for speaker in soundcard.all_speakers():
            sources.append(speaker.name)

        return sources
