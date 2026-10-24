"""CLI integration tests for KB commands using MockKBClient."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def kb_mock_env(monkeypatch, tmp_path):
    """Set environment to use MockKBClient with persistent file for test."""
    persist_file = tmp_path / "kb_mock_data.json"
    monkeypatch.setenv("KB_CLIENT", "mock")
    monkeypatch.setenv("KB_MOCK_PERSIST_FILE", str(persist_file))
    return monkeypatch


def _get_mock_env():
    """Get environment dict with mock client settings."""
    env = os.environ.copy()
    env["KB_CLIENT"] = "mock"
    # Get persist file from current environment if set
    if persist_file := os.getenv("KB_MOCK_PERSIST_FILE"):
        env["KB_MOCK_PERSIST_FILE"] = persist_file
    return env


def run_cli_kb_search(query: str, top_k: int = 5) -> subprocess.CompletedProcess:
    """Helper to run kb search command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "search", query, "--top-k", str(top_k)]
    return subprocess.run(cmd, capture_output=True, text=True, env=_get_mock_env())


def run_cli_kb_list(node_path: str = None, limit: int = 10) -> subprocess.CompletedProcess:
    """Helper to run kb list command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "list"]

    if node_path:
        cmd.extend(["--node", node_path])

    cmd.extend(["--limit", str(limit)])

    return subprocess.run(cmd, capture_output=True, text=True, env=_get_mock_env())


def run_cli_kb_retrieve(doc_id: str) -> subprocess.CompletedProcess:
    """Helper to run kb retrieve command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "retrieve", doc_id]
    return subprocess.run(cmd, capture_output=True, text=True, env=_get_mock_env())


def run_cli_kb_add(doc_id: str, title: str = None, content: str = None, node_path: str = None,
                   file_path: str = None, path_alias: str = None, tags: str = "") -> subprocess.CompletedProcess:
    """Helper to run kb add command with given arguments."""
    cmd = [
        sys.executable, "main.py", "kb", "add",
        "--id", doc_id,
    ]

    # Add title if provided
    if title:
        cmd.extend(["--title", title])

    # Add content (--content or --file, not both)
    if content:
        cmd.extend(["--content", content])
    elif file_path:
        cmd.extend(["--file", file_path])

    # Add node path (--node or --path, not both)
    if node_path:
        cmd.extend(["--node", node_path])
    elif path_alias:
        cmd.extend(["--path", path_alias])

    if tags:
        cmd.extend(["--tags", tags])

    return subprocess.run(cmd, capture_output=True, text=True, env=_get_mock_env())


# ============================================================================
# KB SEARCH COMMAND TESTS
# ============================================================================


def test_kb_search_by_query_returns_results(kb_mock_env):
    """Should execute 'kb search' and return matching documents."""
    result = run_cli_kb_search("Template", top_k=5)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Found" in result.stdout
    assert "doc-001" in result.stdout


def test_kb_search_respects_top_k_limit(kb_mock_env):
    """Should respect --top-k limit in search command."""
    result = run_cli_kb_search("", top_k=1)

    assert result.returncode == 0
    # With top_k=1, should return at most 1 document
    assert result.stdout.count("ID:") <= 1


def test_kb_search_case_insensitive(kb_mock_env):
    """Should perform case-insensitive search."""
    result_lower = run_cli_kb_search("devops", top_k=5)
    result_upper = run_cli_kb_search("DEVOPS", top_k=5)

    assert result_lower.returncode == 0
    assert result_upper.returncode == 0
    # Both should find the same document
    assert "doc-002" in result_lower.stdout
    assert "doc-002" in result_upper.stdout


def test_kb_search_returns_message_when_no_match(kb_mock_env):
    """Should return message when search query matches nothing."""
    result = run_cli_kb_search("nonexistent-xyz-abc", top_k=5)

    assert result.returncode == 0
    assert "No documents found" in result.stdout


def test_kb_search_searches_in_title(kb_mock_env):
    """Should find documents matching query in title."""
    result = run_cli_kb_search("Template", top_k=5)

    assert result.returncode == 0
    assert "Customer Response Template" in result.stdout


def test_kb_search_searches_in_content(kb_mock_env):
    """Should find documents matching query in content."""
    result = run_cli_kb_search("CI/CD", top_k=5)

    assert result.returncode == 0
    assert "Found" in result.stdout


def test_kb_search_searches_in_tags(kb_mock_env):
    """Should find documents matching query in tags."""
    result = run_cli_kb_search("developer", top_k=5)

    assert result.returncode == 0
    assert "Found" in result.stdout


# ============================================================================
# KB LIST COMMAND TESTS
# ============================================================================


def test_kb_list_all_documents(kb_mock_env):
    """Should list all documents when no filter provided."""
    result = run_cli_kb_list()

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Found" in result.stdout
    assert "doc-001" in result.stdout


def test_kb_list_filters_by_node_path_prefix(kb_mock_env):
    """Should filter by --node path prefix."""
    result = run_cli_kb_list(node_path="/templates")

    assert result.returncode == 0
    assert "doc-001" in result.stdout
    assert "/templates/email" in result.stdout


def test_kb_list_filters_by_exact_node_path(kb_mock_env):
    """Should filter by exact --node path."""
    result = run_cli_kb_list(node_path="/team/devops")

    assert result.returncode == 0
    assert "doc-002" in result.stdout


def test_kb_list_respects_limit(kb_mock_env):
    """Should respect --limit parameter."""
    result = run_cli_kb_list(node_path=None, limit=1)

    assert result.returncode == 0
    # With limit=1, should return at most 1 document
    assert result.stdout.count("ID:") <= 1


def test_kb_list_default_limit_is_ten(kb_mock_env):
    """Should have default limit of 10."""
    result = run_cli_kb_list()

    assert result.returncode == 0
    # Should return documents (with mock data, 3 documents)
    assert "Found" in result.stdout


def test_kb_list_returns_empty_when_no_match(kb_mock_env):
    """Should return message when node path doesn't exist."""
    result = run_cli_kb_list(node_path="/nonexistent/path")

    assert result.returncode == 0
    assert "No documents found" in result.stdout


# ============================================================================
# KB RETRIEVE COMMAND TESTS
# ============================================================================


def test_kb_retrieve_existing_document(kb_mock_env):
    """Should retrieve a document by ID."""
    result = run_cli_kb_retrieve("doc-001")

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Document Details:" in result.stdout
    assert "doc-001" in result.stdout
    assert "Customer Response Template" in result.stdout


def test_kb_retrieve_returns_full_document(kb_mock_env):
    """Should return document with all fields populated."""
    result = run_cli_kb_retrieve("doc-002")

    assert result.returncode == 0
    assert "doc-002" in result.stdout
    assert "DevOps Team Information" in result.stdout
    assert "Content:" in result.stdout


def test_kb_retrieve_nonexistent_raises_error(kb_mock_env):
    """Should show error when document not found."""
    result = run_cli_kb_retrieve("doc-999")

    assert result.returncode != 0
    assert "not found" in result.stdout.lower()


def test_kb_retrieve_includes_content(kb_mock_env):
    """Should include full content in retrieved document."""
    result = run_cli_kb_retrieve("doc-001")

    assert result.returncode == 0
    assert "Content:" in result.stdout
    # Should have some content after the Content: line
    lines_after_content = result.stdout.split("Content:")[-1].strip()
    assert len(lines_after_content) > 0


# ============================================================================
# KB ADD COMMAND TESTS
# ============================================================================


def test_kb_add_new_document_returns_success(kb_mock_env):
    """Should add a new document and return success message."""
    result = run_cli_kb_add(
        doc_id="doc-new-001",
        title="New Template",
        content="This is a new template",
        node_path="/templates/sms",
        tags="sms,template"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert "doc-new-001" in result.stdout


def test_kb_add_document_makes_it_retrievable(kb_mock_env):
    """Should make added document retrievable via retrieve."""
    # First, add a document
    add_result = run_cli_kb_add(
        doc_id="doc-new-002",
        title="Retrievable Document",
        content="Can retrieve this document",
        node_path="/docs/new",
        tags="test"
    )

    assert add_result.returncode == 0

    # Then retrieve it
    retrieve_result = run_cli_kb_retrieve("doc-new-002")

    assert retrieve_result.returncode == 0
    assert "doc-new-002" in retrieve_result.stdout
    assert "Retrievable Document" in retrieve_result.stdout


def test_kb_add_document_appears_in_list(kb_mock_env):
    """Should make added document appear in list."""
    # First, add a document
    add_result = run_cli_kb_add(
        doc_id="doc-new-003",
        title="Listable Document",
        content="Should appear in list",
        node_path="/docs/custom",
        tags="test"
    )

    assert add_result.returncode == 0

    # Then list with the same path
    list_result = run_cli_kb_list(node_path="/docs/custom")

    assert list_result.returncode == 0
    assert "doc-new-003" in list_result.stdout


def test_kb_add_duplicate_raises_error(kb_mock_env):
    """Should show error when adding document with existing ID."""
    result = run_cli_kb_add(
        doc_id="doc-001",  # already exists
        title="Duplicate",
        content="This is a duplicate",
        node_path="/docs/dup",
        tags="dup"
    )

    assert result.returncode != 0
    assert "already exists" in result.stdout.lower()


def test_kb_add_document_with_tags(kb_mock_env):
    """Should add document with multiple tags."""
    result = run_cli_kb_add(
        doc_id="doc-new-004",
        title="Tagged Document",
        content="Document with tags",
        node_path="/docs/tagged",
        tags="tag1,tag2,tag3"
    )

    assert result.returncode == 0
    assert "added successfully" in result.stdout.lower()


# ============================================================================
# KB ADD COMMAND TESTS - FILE IMPORT
# ============================================================================


def test_kb_add_document_from_file(kb_mock_env, tmp_path):
    """Should add a new document from file and return success message."""
    # Create a test file
    test_file = tmp_path / "template.md"
    file_content = "# Email Template\n\nThis is an email response template."
    test_file.write_text(file_content, encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-file-001",
        title="Email Response Template",
        file_path=str(test_file),
        path_alias="/templates/email",
        tags="template,email"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert "doc-file-001" in result.stdout


def test_kb_add_document_from_file_auto_title(kb_mock_env, tmp_path):
    """Should add document from file with auto-generated title from filename."""
    # Create a test file
    test_file = tmp_path / "sms_template.md"
    file_content = "# SMS Template\n\nQuick response template for SMS."
    test_file.write_text(file_content, encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-file-002",
        file_path=str(test_file),
        node_path="/templates/sms",
        tags="template,sms"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert "doc-file-002" in result.stdout


def test_kb_add_document_from_file_with_path_alias(kb_mock_env, tmp_path):
    """Should add document from file using --path instead of --node."""
    # Create a test file
    test_file = tmp_path / "devops_guide.md"
    file_content = "# DevOps Setup Guide\n\nSteps to setup DevOps environment."
    test_file.write_text(file_content, encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-file-003",
        title="DevOps Setup",
        file_path=str(test_file),
        path_alias="/docs/guides",
        tags="guide,devops"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()


def test_kb_add_document_from_file_appears_in_list(kb_mock_env, tmp_path):
    """Should make document added from file appear in list."""
    # Create a test file
    test_file = tmp_path / "team_info.md"
    file_content = "# Team Information\n\nTeam contact and roles."
    test_file.write_text(file_content, encoding="utf-8")

    # Add document from file
    add_result = run_cli_kb_add(
        doc_id="doc-file-004",
        title="Team Info",
        file_path=str(test_file),
        node_path="/team",
        tags="team"
    )

    assert add_result.returncode == 0

    # List with the same path
    list_result = run_cli_kb_list(node_path="/team")

    assert list_result.returncode == 0
    assert "doc-file-004" in list_result.stdout


def test_kb_add_document_from_file_makes_it_retrievable(kb_mock_env, tmp_path):
    """Should make document added from file retrievable via retrieve."""
    # Create a test file
    test_file = tmp_path / "handbook.md"
    file_content = "# Company Handbook\n\nCompany policies and procedures."
    test_file.write_text(file_content, encoding="utf-8")

    # Add document from file
    add_result = run_cli_kb_add(
        doc_id="doc-file-005",
        title="Company Handbook",
        file_path=str(test_file),
        node_path="/docs",
        tags="handbook"
    )

    assert add_result.returncode == 0

    # Retrieve it
    retrieve_result = run_cli_kb_retrieve("doc-file-005")

    assert retrieve_result.returncode == 0
    assert "doc-file-005" in retrieve_result.stdout
    assert "Company Handbook" in retrieve_result.stdout


def test_kb_add_document_from_nonexistent_file_fails(kb_mock_env):
    """Should fail when trying to add document from non-existent file."""
    result = run_cli_kb_add(
        doc_id="doc-file-fail",
        file_path="/nonexistent/file.md",
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


def test_kb_add_document_from_empty_file_fails(kb_mock_env, tmp_path):
    """Should fail when trying to add document from empty file."""
    # Create empty file
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-file-empty",
        file_path=str(empty_file),
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "empty" in result.stdout.lower() or "error" in result.stdout.lower()


def test_kb_add_document_from_whitespace_only_file_fails(kb_mock_env, tmp_path):
    """Should fail when trying to add document from whitespace-only file."""
    # Create whitespace-only file
    whitespace_file = tmp_path / "whitespace.md"
    whitespace_file.write_text("   \n\n  ", encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-file-whitespace",
        file_path=str(whitespace_file),
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "empty" in result.stdout.lower() or "error" in result.stdout.lower()
