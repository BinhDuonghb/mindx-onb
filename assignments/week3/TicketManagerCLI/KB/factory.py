from KB.config import load_config
from KB.clients.httpKBClient import HTTPKBClient
from KB.clients.mockKBClient import MockKBClient

def create_kb_client():
    config = load_config()

    if config.client_type == "mock":
        return MockKBClient() # havent implemented yet 

    if config.client_type == "http":
        return HTTPKBClient(base_url=config.api_url) # havent implemented yet

    raise ValueError(
        f"Unsupported client type: {config.client_type}"
    )