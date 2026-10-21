"""Integration tests for HTTPKBClient with real KB API."""
import pytest
from KB.clients.httpKBClient import HTTPKBClient
from KB.models.document import Document
from KB.models.search import KBQuery


@pytest.fixture
def http_kb_client():
    """Create HTTP KB client pointing to local service."""
    return HTTPKBClient(base_url="http://localhost:8000")


# ============================================================================
# RETRIEVE TESTS
# ============================================================================


def test_http_retrieve_existing_document(http_kb_client):
    """Should retrieve a document by ID from HTTP API."""
    doc_id = "doc-001"

    document = http_kb_client.retrieve(doc_id)

    assert document is not None
    assert document.id == doc_id
    assert document.title == "Customer Response Template"
    assert document.node_path == "/templates/email"


def test_http_retrieve_nonexistent_document_raises_error(http_kb_client):
    """Should raise ValueError when document ID not found."""
    doc_id = "doc-999"

    with pytest.raises(ValueError, match="not found"):
        http_kb_client.retrieve(doc_id)


def test_http_retrieve_returns_full_document(http_kb_client):
    """Should return document with all fields populated."""
    document = http_kb_client.retrieve("doc-002")

    assert document.id == "doc-002"
    assert document.title == "DevOps Team Information"
    assert document.content
    assert document.node_path == "/team/devops"
    assert document.tags == ["team", "devops"]


# ============================================================================
# SEARCH TESTS
# ============================================================================


def test_http_search_by_query(http_kb_client):
    """Should find documents matching query."""
    query = KBQuery(query="Template", top_k=5)

    results = http_kb_client.search(query)

    assert len(results) == 1
    assert results[0].id == "doc-001"
    assert results[0].title == "Customer Response Template"


def test_http_search_respects_top_k(http_kb_client):
    """Should respect top_k limit in search."""
    query = KBQuery(query="e", top_k=2)  # "e" matches many documents

    results = http_kb_client.search(query)

    assert len(results) <= 2


def test_http_search_case_insensitive(http_kb_client):
    """Should perform case-insensitive search."""
    query_lower = KBQuery(query="devops", top_k=5)
    query_upper = KBQuery(query="DEVOPS", top_k=5)

    results_lower = http_kb_client.search(query_lower)
    results_upper = http_kb_client.search(query_upper)

    assert len(results_lower) > 0
    assert len(results_upper) > 0
    assert results_lower[0].id == results_upper[0].id


def test_http_search_no_matches(http_kb_client):
    """Should return empty list when no matches."""
    query = KBQuery(query="nonexistent-xyz-abc", top_k=5)

    results = http_kb_client.search(query)

    assert results == []


# ============================================================================
# LIST TESTS
# ============================================================================


def test_http_list_all_documents(http_kb_client):
    """Should list all documents when no filter."""
    documents = http_kb_client.list()

    assert len(documents) >= 3
    assert any(doc.id == "doc-001" for doc in documents)
    assert any(doc.id == "doc-002" for doc in documents)
    assert any(doc.id == "doc-003" for doc in documents)


def test_http_list_filters_by_node_path(http_kb_client):
    """Should filter by node_path."""
    documents = http_kb_client.list(node_path="/templates/email")

    assert len(documents) == 1
    assert documents[0].id == "doc-001"
    assert documents[0].node_path == "/templates/email"


def test_http_list_respects_limit(http_kb_client):
    """Should respect limit parameter."""
    documents = http_kb_client.list(limit=1)

    assert len(documents) <= 1


def test_http_list_no_match(http_kb_client):
    """Should return empty list when no documents match."""
    documents = http_kb_client.list(node_path="/nonexistent/path")

    assert documents == []


# ============================================================================
# ADD TESTS
# ============================================================================


def test_http_add_new_document(http_kb_client):
    """Should add a new document to HTTP API."""
    import time
    unique_id = f"doc-http-{int(time.time() * 1000)}"

    new_doc = Document(
        id=unique_id,
        title="HTTP Test Document",
        content="This is a test document",
        node_path="/test/http",
        tags=["http", "test"],
    )

    result = http_kb_client.add(new_doc)

    assert result.id == unique_id
    assert result.title == "HTTP Test Document"

    # Verify it's retrievable
    retrieved = http_kb_client.retrieve(unique_id)
    assert retrieved.id == unique_id


def test_http_add_duplicate_raises_error(http_kb_client):
    """Should raise error when adding duplicate ID."""
    duplicate = Document(
        id="doc-001",  # already exists
        title="Duplicate",
        content="This is a duplicate",
        node_path="/test/dup",
        tags=["dup"],
    )

    with pytest.raises(ValueError, match="already exists"):
        http_kb_client.add(duplicate)


def test_http_add_makes_document_listable(http_kb_client):
    """Should make added document appear in list."""
    import time
    unique_id = f"doc-http-listable-{int(time.time() * 1000)}"

    new_doc = Document(
        id=unique_id,
        title="Listable Document",
        content="Should appear in list",
        node_path="/test/listable",
        tags=["test"],
    )

    http_kb_client.add(new_doc)
    documents = http_kb_client.list(node_path="/test/listable")

    assert any(doc.id == unique_id for doc in documents)
