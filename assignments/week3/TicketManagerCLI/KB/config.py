import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

@dataclass
class KBConfig:
    client_type: str
    api_url: str | None = None

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

PERSIST_FILE = DATA_DIR / "kb_mock_data.json"

def load_config() -> KBConfig:
    client_type = os.getenv("KB_CLIENT", "mock").strip().lower()
    api_url = os.getenv("KB_API_URL", "http://localhost:8000").strip() or None

    if client_type not in {"mock", "http"}:
        raise ValueError(
            f"Invalid KB_CLIENT '{client_type}'. "
            "Supported values: mock, http."
        )

    if client_type == "http" and not api_url:
        raise ValueError(
            "KB_API_URL is required when KB_CLIENT=http."
        )

    return KBConfig(
        client_type=client_type,
        api_url=api_url,
    )