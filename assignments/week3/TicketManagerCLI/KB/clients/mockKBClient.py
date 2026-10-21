
import json
from copy import deepcopy
from pathlib import Path

from KB.clients.base import KBClient
from KB.models.document import Document
from KB.models.search import KBQuery, SearchResult
from KB.mock_data import SAMPLE_DOCUMENTS


class MockKBClient(KBClient):
    """In-memory implementation of the Knowledge Base client with optional file persistence."""

    def __init__(self, persist_file: Path | None = None):
        """
        Initialize with an independent copy of sample documents.

        Args:
            persist_file: Optional Path to persist documents to JSON file.
                         If provided, documents are loaded from or created in this file.
        """
        self.persist_file = persist_file
        self._documents = {}

        if persist_file:
            self._load()
        else:
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

        if self.persist_file:
            self._save()

        return document

    def _load(self) -> None:
        """
        Load documents from persist file.

        If file doesn't exist or contains invalid JSON, initialize with sample documents.

        Raises:
            ValueError: If file contains invalid document structure.
        """
        if not self.persist_file:
            return

        if not self.persist_file.exists():
            # Initialize with sample documents if file doesn't exist
            documents = deepcopy(SAMPLE_DOCUMENTS)
            self._documents = {doc.id: doc for doc in documents}
            self._save()
        else:
            try:
                with open(self.persist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                # File exists but contains invalid JSON, reinitialize with samples
                print(f"Warning: Invalid JSON in {self.persist_file}, reinitializing with sample documents")
                documents = deepcopy(SAMPLE_DOCUMENTS)
                self._documents = {doc.id: doc for doc in documents}
                self._save()
                return

            # Validate that data is a list
            if not isinstance(data, list):
                raise ValueError(
                    f"Persist file must contain a JSON array, got {type(data).__name__}"
                )

            # Load documents with validation
            try:
                self._documents = {
                    doc_dict["id"]: Document(**doc_dict)
                    for doc_dict in data
                }
            except (KeyError, TypeError) as e:
                raise ValueError(
                    f"Invalid document structure in persist file: {str(e)}"
                )

    def _save(self) -> None:
        """
        Save all documents to persist file.

        Raises:
            IOError: If the file cannot be written.
        """
        if not self.persist_file:
            return

        # Ensure parent directory exists
        self.persist_file.parent.mkdir(parents=True, exist_ok=True)

        documents_data = [
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "node_path": doc.node_path,
                "tags": doc.tags,
            }
            for doc in self._documents.values()
        ]

        with open(self.persist_file, "w", encoding="utf-8") as f:
            json.dump(documents_data, f, indent=2, ensure_ascii=False)
