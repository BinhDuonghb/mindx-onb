# src/clients/base.py

from typing import Protocol

from KB.models.document import Document
from KB.models.search import KBQuery, SearchResult


class KBClient(Protocol):
    def search(self, query: KBQuery) -> list[SearchResult]:
        ...

    def list(
        self,
        node_path: str | None = None,
        limit: int = 10,
    ) -> list[Document]:
        ...

    def retrieve(self, doc_id: str) -> Document:
        ...

    def add(self, document: Document) -> Document:
        ...