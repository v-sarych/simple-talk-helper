import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ASRConfig:
    model_name: str
    model_path: str
    device: str  # cuda or cpu
    compute_type: str  # float16, int8, int16, float32
    batch_size: int = 16
    
    def __post_init__(self):
        if self.device not in ["cuda", "cpu"]:
            raise ValueError(f"device must be 'cuda' or 'cpu', got: {self.device}")
        
        valid_types = ["float16", "int8", "int16", "float32"]
        if self.compute_type not in valid_types:
            raise ValueError(f"compute_type must be one of {valid_types}, got: {self.compute_type}")

@dataclass
class DiarizationConfig:
    model_name: str
    segmentation_model: str
    model_path: str
    device: str = "cuda"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    
    def __post_init__(self):
        if self.device not in ["cuda", "cpu"]:
            raise ValueError(f"device must be 'cuda' or 'cpu', got: {self.device}")

@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    chunk_duration_ms: int = 1000
    silence_threshold: float = 1.5

@dataclass
class AppConfig:
    llm: LLMConfig
    prompt: str
    audio: AudioConfig
    asr: ASRConfig
    diarization: DiarizationConfig
    
    @classmethod
    def from_json(cls, config_path: str) -> 'AppConfig':
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        asr_config = ASRConfig(**data['asr'])
        diarization_config = DiarizationConfig(**data['diarization'])
        llm_config = LLMConfig(**data['llm'])
        prompts_config = "\n".join(data['prompt'])
        audio_config = AudioConfig(**data['audio'])
        
        return AppConfig(
            llm=llm_config,
            prompt=prompts_config,
            audio=audio_config,
            asr=asr_config,
            diarization=diarization_config
        )