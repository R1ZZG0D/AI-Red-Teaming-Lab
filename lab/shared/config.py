from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_mode: str
    app_name: str
    base_dir: Path
    data_dir: Path
    documents_dir: Path
    db_path: Path
    secrets_file: Path
    log_dir: Path
    llm_backend: str
    openai_api_key: str
    openai_model: str
    ollama_host: str
    ollama_model: str
    system_prompt_secret: str
    emergency_token: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.from_mode(
            os.getenv("APP_MODE", "vulnerable"),
            os.getenv("APP_NAME", "AI Red Teaming Lab"),
        )

    @classmethod
    def from_mode(cls, app_mode: str, app_name: str) -> "Settings":
        data_dir = BASE_DIR / "data"
        return cls(
            app_mode=app_mode,
            app_name=app_name,
            base_dir=BASE_DIR,
            data_dir=data_dir,
            documents_dir=data_dir / "documents",
            db_path=Path(os.getenv("LAB_DB_PATH", str(data_dir / "lab.db"))),
            secrets_file=Path(os.getenv("LAB_SECRETS_FILE", str(data_dir / "secrets.txt"))),
            log_dir=BASE_DIR / "logs",
            llm_backend=os.getenv("LLM_BACKEND", "mock"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            system_prompt_secret=os.getenv("LAB_SHARED_SECRET", "MOCK-SYSTEM-PROMPT-KEY"),
            emergency_token=os.getenv("LAB_EMERGENCY_TOKEN", "MOCK-ENV-TOKEN"),
        )
