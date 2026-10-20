import pytest

from KB.clients.mockKBClient import MockKBClient
from KB.models.document import Document
from KB.models.search import KBQuery


@pytest.fixture
def kb_client():
    """Create a fresh client for each test."""
    return MockKBClient()


# ============================================================================
# RETRIEVE TESTS
# ============================================================================


def test_retrieve_existing_document_returns_document(kb_client):
    """Should retrieve a document by ID."""
    doc_id = "doc-001"

    document = kb_client.retrieve(doc_id)

    assert document is not None
    assert document.id == doc_id
    assert document.title == "Customer Response Template"
    assert document.node_path == "/templates/email"


def test_retrieve_nonexistent_document_raises_error(kb_client):
    """Should raise ValueError when document ID not found."""
    doc_id = "doc-999"

    with pytest.raises(ValueError, match="not found"):
        kb_client.retrieve(doc_id)


def test_retrieve_returns_full_document_with_content(kb_client):
    """Should return document with all fields populated."""
    document = kb_client.retrieve("doc-002")

    assert document.id == "doc-002"
    assert document.title == "DevOps Team Information"
    assert document.content  # has content
    assert document.node_path == "/team/devops"
    assert document.tags == ["team", "devops"]


# ============================================================================
# SEARCH TESTS
# ============================================================================


def test_search_by_title_returns_matching_documents(kb_client):
    """Should find documents matching query in title."""
    query = KBQuery(query="Template", top_k=5)

    results = kb_client.search(query)

    assert len(results) == 1
    assert results[0].id == "doc-001"
    assert results[0].title == "Customer Response Template"


def test_search_by_content_returns_matching_documents(kb_client):
    """Should find documents matching query in content."""
    query = KBQuery(query="CI/CD", top_k=5)

    results = kb_client.search(query)

    assert len(results) == 1
    assert results[0].id == "doc-002"


def test_search_by_tag_returns_matching_documents(kb_client):
    """Should find documents matching query in tags."""
    query = KBQuery(query="developer", top_k=5)

    results = kb_client.search(query)

    assert len(results) == 1
    assert results[0].id == "doc-003"


def test_search_is_case_insensitive(kb_client):
    """Should find documents regardless of case."""
    query = KBQuery(query="DEVOPS", top_k=5)

    results = kb_client.search(query)

    assert len(results) == 1
    assert results[0].id == "doc-002"


def test_search_respects_top_k_limit(kb_client):
    """Should return at most top_k results."""
    query = KBQuery(query="", top_k=2)  # empty query matches all

    results = kb_client.search(query)

    assert len(results) <= 2


def test_search_returns_search_result_objects(kb_client):
    """Should return SearchResult objects with id, title, node_path."""
    query = KBQuery(query="Guide", top_k=5)

    results = kb_client.search(query)

    assert len(results) == 1
    result = results[0]
    assert hasattr(result, "id")
    assert hasattr(result, "title")
    assert hasattr(result, "node_path")
    assert result.id == "doc-003"
    assert result.title == "Developer Guide"
    assert result.node_path == "/docs/guides"


def test_search_returns_empty_list_when_no_matches(kb_client):
    """Should return empty list when query doesn't match anything."""
    query = KBQuery(query="nonexistent-query-xyz", top_k=5)

    results = kb_client.search(query)

    assert results == []


# ============================================================================
# LIST TESTS
# ============================================================================


def test_list_returns_all_documents_when_no_filter(kb_client):
    """Should return all documents when node_path is None."""
    documents = kb_client.list(node_path=None)

    assert len(documents) == 3
    assert any(doc.id == "doc-001" for doc in documents)
    assert any(doc.id == "doc-002" for doc in documents)
    assert any(doc.id == "doc-003" for doc in documents)


def test_list_filters_by_node_path_prefix(kb_client):
    """Should return documents matching node_path prefix."""
    documents = kb_client.list(node_path="/templates")

    assert len(documents) == 1
    assert documents[0].id == "doc-001"
    assert documents[0].node_path == "/templates/email"


def test_list_filters_by_exact_node_path(kb_client):
    """Should return documents with exact node_path match."""
    documents = kb_client.list(node_path="/team/devops")

    assert len(documents) == 1
    assert documents[0].id == "doc-002"


def test_list_respects_limit(kb_client):
    """Should return at most limit documents."""
    documents = kb_client.list(node_path=None, limit=2)

    assert len(documents) <= 2


def test_list_default_limit_is_ten(kb_client):
    """Should have default limit of 10."""
    # With only 3 sample docs, all should be returned even with default limit
    documents = kb_client.list()

    assert len(documents) == 3


def test_list_returns_full_document_objects(kb_client):
    """Should return Document objects with all fields."""
    documents = kb_client.list(limit=1)

    assert len(documents) >= 1
    doc = documents[0]
    assert hasattr(doc, "id")
    assert hasattr(doc, "title")
    assert hasattr(doc, "content")
    assert hasattr(doc, "node_path")
    assert hasattr(doc, "tags")


# ============================================================================
# ADD TESTS
# ============================================================================


def test_add_new_document_returns_document(kb_client):
    """Should add a new document and return it."""
    new_doc = Document(
        id="doc-004",
        title="New Document",
        content="This is a new document",
        node_path="/docs/new",
        tags=["new"],
    )

    result = kb_client.add(new_doc)

    assert result.id == "doc-004"
    assert result.title == "New Document"


def test_add_document_makes_it_retrievable(kb_client):
    """Should make added document retrievable via retrieve()."""
    new_doc = Document(
        id="doc-005",
        title="Retrievable Document",
        content="Can retrieve this",
        node_path="/docs/new",
        tags=["test"],
    )

    kb_client.add(new_doc)
    retrieved = kb_client.retrieve("doc-005")

    assert retrieved.id == "doc-005"
    assert retrieved.title == "Retrievable Document"


def test_add_document_appears_in_list(kb_client):
    """Should make added document appear in list()."""
    new_doc = Document(
        id="doc-006",
        title="Listable Document",
        content="Should appear in list",
        node_path="/docs/custom",
        tags=["test"],
    )

    kb_client.add(new_doc)
    documents = kb_client.list(node_path="/docs/custom")

    assert any(doc.id == "doc-006" for doc in documents)


def test_add_duplicate_document_raises_error(kb_client):
    """Should raise ValueError when adding document with existing ID."""
    duplicate = Document(
        id="doc-001",  # already exists
        title="Duplicate",
        content="This is a duplicate",
        node_path="/docs/dup",
        tags=["dup"],
    )

    with pytest.raises(ValueError, match="already exists"):
        kb_client.add(duplicate)