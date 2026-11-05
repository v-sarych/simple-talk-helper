import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SherpaOnnxConfig:
    encoder: str
    decoder: str
    joiner: str
    tokens: str
    num_threads: int = 2
    provider: str = "cpu"
    decoding_method: str = "greedy_search"
    sample_rate: float = 16000
    feature_dim: int = 80
    enable_endpoint_detection: bool = True
    rule1_min_trailing_silence: float = 2.4
    rule2_min_trailing_silence: float = 1.2
    rule3_min_utterance_length: float = 20.0
    debug: bool = False

    def __post_init__(self):
        if self.provider not in ["cpu", "cuda", "auto"]:
            raise ValueError(f"provider must be 'cpu', 'cuda' or 'auto', got: {self.provider}")

        valid_methods = ["greedy_search", "modified_beam_search"]
        if self.decoding_method not in valid_methods:
            raise ValueError(f"decoding_method must be one of {valid_methods}, got: {self.decoding_method}")


@dataclass
class ASRConfig:
    sherpa_onnx: SherpaOnnxConfig


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    max_tokens: int
    translator_prompt: str
    advisor_prompt: str


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    block_size: int = 256


@dataclass
class AppConfig:
    llm: LLMConfig
    audio: AudioConfig
    asr: ASRConfig

    @classmethod
    def from_json(cls, config_path: str) -> 'AppConfig':
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        sherpa_onnx_config = SherpaOnnxConfig(**data['asr']['sherpa_onnx'])
        asr_config = ASRConfig(sherpa_onnx=sherpa_onnx_config)
        llm_config = LLMConfig(**data['llm'])
        audio_config = AudioConfig(**data['audio'])

        return AppConfig(
            llm=llm_config,
            audio=audio_config,
            asr=asr_config
        )
