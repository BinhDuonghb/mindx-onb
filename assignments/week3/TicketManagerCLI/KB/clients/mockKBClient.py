
from copy import deepcopy

from KB.clients.base import KBClient
from KB.models.document import Document
from KB.models.search import KBQuery, SearchResult
from KB.mock_data import SAMPLE_DOCUMENTS


class MockKBClient(KBClient):
    """In-memory implementation of the Knowledge Base client."""

    def __init__(self):
        """Initialize with an independent copy of sample documents."""
        documents = deepcopy(SAMPLE_DOCUMENTS)
        self._documents = {doc.id: doc for doc in documents}

    def retrieve(self, doc_id: str) -> Document:
        """Retrieve a document by ID."""
        document = self._documents.get(doc_id)

        if document is None:
            raise ValueError(f"Document {doc_id} not found")

        return document

    def search(self, query: KBQuery) -> list[SearchResult]:
        """Search document titles, content, and tags."""
        keyword = query.query.strip().casefold()
        results = []

        for doc in self._documents.values():
            searchable_text = [
                doc.title,
                doc.content,
                *doc.tags,
            ]

            if any(
                keyword in text.casefold()
                for text in searchable_text
            ):
                results.append(
                    SearchResult(
                        id=doc.id,
                        title=doc.title,
                        node_path=doc.node_path,
                    )
                )

        return results[:query.top_k]

    def _matches_node_path(
        self,
        doc: Document,
        node_path: str,
    ) -> bool:
        """Check whether a document belongs to a node or its descendants."""
        normalized_path = node_path.rstrip("/")

        return (
            doc.node_path == normalized_path
            or doc.node_path.startswith(normalized_path + "/")
        )

    def list(
        self,
        node_path: str | None = None,
        limit: int = 10,
    ) -> list[Document]:
        """List documents, optionally filtered by node path."""
        documents = self._documents.values()

        if node_path is not None:
            documents = (
                doc
                for doc in documents
                if self._matches_node_path(doc, node_path)
            )

        return list(documents)[:limit]

    def add(self, document: Document) -> Document:
        """Add a document, rejecting duplicate IDs."""
        if document.id in self._documents:
            raise ValueError(
                f"Document {document.id} already exists"
            )

        self._documents[document.id] = document
        return document
