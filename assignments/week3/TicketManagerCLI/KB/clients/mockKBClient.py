from KB.clients.base import KBClient
from KB.models.document import Document
from KB.models.search import KBQuery, SearchResult
from KB.mock_data import SAMPLE_DOCUMENTS


class MockKBClient(KBClient):
    """Mock KB client with in-memory storage for testing."""

    def __init__(self):
        """Initialize with sample data."""
        self._documents = {doc.id: doc for doc in SAMPLE_DOCUMENTS}

    def retrieve(self, doc_id: str) -> Document:
        """Retrieve a document by ID."""
        if doc_id not in self._documents:
            raise ValueError(f"Document {doc_id} not found")
        return self._documents[doc_id]

    def search(self, query: KBQuery) -> list[SearchResult]:
        """Search documents by query in title, content, and tags."""
        results = []
        query_lower = query.query.lower()

        for doc in self._documents.values():
            # Check if query matches title, content, or tags (case-insensitive)
            title_match = query_lower in doc.title.lower()
            content_match = query_lower in doc.content.lower()
            tags_match = any(query_lower in tag.lower() for tag in doc.tags)

            if title_match or content_match or tags_match:
                results.append(
                    SearchResult(
                        id=doc.id,
                        title=doc.title,
                        node_path=doc.node_path,
                    )
                )

        # Respect top_k limit
        return results[: query.top_k]

    def list(
        self,
        node_path: str | None = None,
        limit: int = 10,
    ) -> list[Document]:
        """List documents, optionally filtered by node_path prefix."""
        results = []

        for doc in self._documents.values():
            # Filter by node_path prefix if provided
            if node_path is None or doc.node_path.startswith(node_path):
                results.append(doc)

        # Respect limit
        return results[:limit]

    def add(self, document: Document) -> Document:
        """Add a new document."""
        if document.id in self._documents:
            raise ValueError(f"Document {document.id} already exists")
        self._documents[document.id] = document
        return document