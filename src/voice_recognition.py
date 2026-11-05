import time
import soundcard
import soxr
import numpy as np
import threading
import sherpa_onnx
from queue import Queue 
from dataclasses import dataclass
from config_descriptioin import ASRConfig, AudioConfig, SherpaOnnxConfig

@dataclass
class RecognizedTextBatch:
    id: int
    text: str
    is_endpoint: bool = False

class VoiceRecognition:
    _asr_config: ASRConfig
    _audio_config: AudioConfig
    _sherpa_recognizer: sherpa_onnx.OnlineRecognizer

    def __init__(
        self,
        asr_config: ASRConfig,
        audio_config: AudioConfig,
    ):
        self._asr_config = asr_config
        self._audio_config = audio_config
        self._sherpa_recognizer = self.create_sherpa_recognizer(self._asr_config.sherpa_onnx)

    @staticmethod
    def create_sherpa_recognizer(config: SherpaOnnxConfig) -> sherpa_onnx.OnlineRecognizer:
        return sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=config.tokens,
            encoder=config.encoder,
            decoder=config.decoder,
            joiner=config.joiner,
            num_threads=config.num_threads,
            sample_rate=config.sample_rate,
            feature_dim=config.feature_dim,
            enable_endpoint_detection=config.enable_endpoint_detection,
            rule1_min_trailing_silence=config.rule1_min_trailing_silence,
            rule2_min_trailing_silence=config.rule2_min_trailing_silence,
            rule3_min_utterance_length=config.rule3_min_utterance_length,
            decoding_method=config.decoding_method,
            provider=config.provider,
            debug=config.debug,
        )


    def loop(self, device: str, voice_recognized_callback, error_callback, cancellation_token: threading.Event):
        _audio_queue = Queue()
        
        threading.Thread(
            target=self._recognition_loop,
            args=(_audio_queue, voice_recognized_callback, error_callback, cancellation_token),
            daemon=True,
        ).start()

        audio_source = soundcard.get_microphone(device, include_loopback=True)
        try:
            with audio_source.recorder(self._audio_config.sample_rate, 2 if audio_source.isloopback else 1, self._audio_config.block_size) as recorder:
                while not cancellation_token.is_set():
                    recorded_data = recorder.record(self._audio_config.block_size)
                    if audio_source.isloopback:# lobback bag(in windows mostly), to fix i do stereo capture and combine into mono for recognition
                        recorded_data = recorded_data.mean(axis=1).reshape(-1, 1).astype(np.float32) 

                    _audio_queue.put(recorded_data)
        except Exception as e:
            cancellation_token.set()
            error_callback(f"Recognition loop crashed: {e}")

            
    def _recognition_loop(self, _audio_queue: Queue, voice_recognized_callback, error_callback, cancellation_token: threading.Event):
        recognizing_stream: sherpa_onnx.OnlineStream = self._sherpa_recognizer.create_stream()
        resampler = soxr.ResampleStream(self._audio_config.sample_rate, self._asr_config.sherpa_onnx.sample_rate, 1, dtype='float32')
        
        endpoint_id = 0
        previous_partial_text = ""
        while not cancellation_token.is_set():
            audio_batches = []
            while not _audio_queue.empty():
                audio_batches.append(_audio_queue.get_nowait())

            if len(audio_batches) > 0:
                audio_batch = audio_batches[0] if len(audio_batches) == 1 else np.concatenate(audio_batches, axis=0)
                audio_batch = audio_batch.flatten().astype(np.float32)
                audio_batch = resampler.resample_chunk(audio_batch)

                recognizing_stream.accept_waveform(self._asr_config.sherpa_onnx.sample_rate, audio_batch)
                while self._sherpa_recognizer.is_ready(recognizing_stream):
                    self._sherpa_recognizer.decode_stream(recognizing_stream)

                if self._sherpa_recognizer.is_endpoint(recognizing_stream):
                    final_text = self._sherpa_recognizer.get_result(recognizing_stream)
                    if final_text:
                        voice_recognized_callback(RecognizedTextBatch(endpoint_id, final_text + "<>", True))
                        endpoint_id += 1
                    self._sherpa_recognizer.reset(recognizing_stream)
                else:
                    partial_text = self._sherpa_recognizer.get_result(recognizing_stream)
                    if partial_text and previous_partial_text != partial_text:
                           previous_partial_text = partial_text
                           voice_recognized_callback(RecognizedTextBatch(endpoint_id, partial_text))

            time.sleep(0.03)

                    



    @staticmethod
    def get_audio_sources() -> list[str]:
        sources: list[str] = []

        for mic in soundcard.all_microphones(include_loopback=True):
            sources.append(mic.name)

        return sources
