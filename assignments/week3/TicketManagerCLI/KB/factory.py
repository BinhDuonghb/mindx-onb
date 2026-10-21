import os
from pathlib import Path

from KB.config import PERSIST_FILE, load_config
from KB.clients.httpKBClient import HTTPKBClient
from KB.clients.mockKBClient import MockKBClient

def create_kb_client():
    config = load_config()

    if config.client_type == "mock":
        persist_file = None
        if persist_path := os.getenv("KB_MOCK_PERSIST_FILE"):
            persist_file = Path(persist_path)
        else:
            persist_file = PERSIST_FILE
            
        return MockKBClient(persist_file=persist_file)

    if config.client_type == "http":
        return HTTPKBClient(base_url=config.api_url)

    raise ValueError(
        f"Unsupported client type: {config.client_type}"
    )