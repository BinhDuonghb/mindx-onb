import os
from dataclasses import dataclass


@dataclass
class KBConfig:
    client_type: str
    api_url: str | None = None


def load_config() -> KBConfig:
    client_type = os.getenv("KB_CLIENT", "mock").strip().lower()
    api_url = os.getenv("KB_API_URL", "").strip() or None

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