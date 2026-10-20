
from KB.clients.base import KBClient


class HTTPKBClient(KBClient):
    def __init__(self, base_url):
        self.base_url = base_url