from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _detect_platform() -> str:
    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine == "aarch64":
        return "jetson"
    if system == "Darwin":
        return "mac"
    return "linux"


class Settings(BaseSettings):
    model_config = {"env_prefix": "LT_"}

    app_name: str = "Legacy Tape"
    host: str = "0.0.0.0"
    port: int = 8000
    platform: str = _detect_platform()

    # Paths
    data_dir: str = "~/.legacy-tape"
    recordings_dir: str = "~/.legacy-tape/recordings"
    db_path: str = "~/.legacy-tape/legacy_tape.db"

    # Audio
    sample_rate: int = 16000
    channels: int = 1
    audio_device: Optional[str] = None

    # Whisper — "mock" uses fake transcripts for UI development
    whisper_backend: str = "auto"  # "whisper_cpp", "mock", or "auto"
    whisper_cpp_bin: str = ""  # path to whisper.cpp main binary; auto-detected if empty
    whisper_model_path: str = ""  # path to ggml model file; auto-detected if empty
    whisper_model_size: str = "base.en"
    whisper_language: str = "en"

    # Pico 2 serial
    pico_port: str = "/dev/ttyACM0"
    pico_baud: int = 115200

    # Cloud sync
    sync_api_url: str = "https://api.legacytape.com"
    sync_api_key: str = ""
    sync_enabled: bool = False

    # Recording modes
    default_mode: str = "clean"

    def resolve_paths(self) -> None:
        self.data_dir = str(Path(self.data_dir).expanduser())
        self.recordings_dir = str(Path(self.recordings_dir).expanduser())
        self.db_path = str(Path(self.db_path).expanduser())

        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.recordings_dir).mkdir(parents=True, exist_ok=True)

        models_dir = Path(self.data_dir) / "models"
        models_dir.mkdir(exist_ok=True)

        if self.whisper_backend == "auto":
            if self._find_whisper_cpp():
                self.whisper_backend = "whisper_cpp"
            else:
                self.whisper_backend = "mock"

        if self.whisper_backend == "whisper_cpp" and not self.whisper_cpp_bin:
            self.whisper_cpp_bin = self._find_whisper_cpp() or ""

        if self.whisper_backend == "whisper_cpp" and not self.whisper_model_path:
            candidate = models_dir / f"ggml-{self.whisper_model_size}.bin"
            if candidate.exists():
                self.whisper_model_path = str(candidate)

    def _find_whisper_cpp(self) -> Optional[str]:
        for name in ["whisper-cli", "main", "whisper"]:
            found = shutil.which(name)
            if found:
                return found
        local = Path(self.data_dir) / "whisper.cpp" / "build" / "bin" / "whisper-cli"
        if local.exists():
            return str(local)
        return None


settings = Settings()
settings.resolve_paths()
