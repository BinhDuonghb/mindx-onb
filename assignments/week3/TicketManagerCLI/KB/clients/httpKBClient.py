"""HTTP-based implementation of the Knowledge Base client."""
import requests
from typing import Optional

from KB.clients.base import KBClient
from KB.models.document import Document
from KB.models.search import KBQuery, SearchResult


class HTTPKBClient(KBClient):
    """HTTP client for Knowledge Base API."""

    def __init__(self, base_url: str):
        """
        Initialize HTTP KB client.

        Args:
            base_url: Base URL of KB API (e.g., 'http://localhost:8000')
        """
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def retrieve(self, doc_id: str) -> Document:
        """Retrieve a document by ID."""
        try:
            response = self._session.post(
                f"{self.base_url}/retrieve",
                json={"docId": doc_id},
                timeout=5
            )

            if response.status_code == 404:
                raise ValueError(f"Document {doc_id} not found")

            response.raise_for_status()
            data = response.json()

            # Convert API response format to Python format
            return self._to_document(data)

        except requests.RequestException as e:
            raise ValueError(f"Failed to retrieve document: {str(e)}")

    def search(self, query: KBQuery) -> list[SearchResult]:
        """Search documents by query."""
        # Validate top_k is positive
        if query.top_k <= 0:
            return []

        try:
            response = self._session.post(
                f"{self.base_url}/search",
                json={
                    "query": query.query,
                    "topK": query.top_k
                },
                timeout=5
            )

            response.raise_for_status()
            data = response.json()

            results = []
            for result_data in data.get("results", []):
                results.append(
                    SearchResult(
                        id=result_data["id"],
                        title=result_data["title"],
                        node_path=result_data["nodePath"],
                    )
                )

            return results

        except requests.RequestException as e:
            raise ValueError(f"Search failed: {str(e)}")

    def list(
        self,
        node_path: Optional[str] = None,
        limit: int = 10,
    ) -> list[Document]:
        """List documents with optional filters."""
        # Validate limit is positive
        if limit <= 0:
            return []

        try:
            payload = {"limit": limit}
            if node_path:
                payload["nodePath"] = node_path

            response = self._session.post(
                f"{self.base_url}/list",
                json=payload,
                timeout=5
            )

            response.raise_for_status()
            data = response.json()

            documents = []
            for doc_data in data.get("results", []):
                documents.append(
                    self._to_document(doc_data)
                )

            return documents

        except requests.RequestException as e:
            raise ValueError(f"List failed: {str(e)}")

    def add(self, document: Document) -> Document:
        """Add a new document."""
        try:
            response = self._session.post(
                f"{self.base_url}/add",
                json={
                    "id": document.id,
                    "title": document.title,
                    "content": document.content,
                    "nodePath": document.node_path,
                    "tags": document.tags,
                },
                timeout=5
            )

            if response.status_code == 409:
                raise ValueError(f"Document {document.id} already exists")

            response.raise_for_status()

            return document

        except requests.RequestException as e:
            raise ValueError(f"Add failed: {str(e)}")

    def _to_document(self, data: dict) -> Document:
        return Document(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            node_path=data["nodePath"],
            tags=data["tags"],
        )