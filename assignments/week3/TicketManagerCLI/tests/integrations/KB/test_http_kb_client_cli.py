"""CLI integration tests for KB commands using HTTPKBClient."""
import os
import subprocess
import sys
import time
import pytest


def _get_http_env():
    """Get environment dict with HTTP client settings."""
    env = os.environ.copy()
    env["KB_CLIENT"] = "http"
    env["KB_API_URL"] = "http://localhost:8000"
    return env


def run_cli_kb_search(query: str, top_k: int = 5) -> subprocess.CompletedProcess:
    """Helper to run kb search command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "search", query, "--top-k", str(top_k)]
    return subprocess.run(cmd, capture_output=True, text=True, env=_get_http_env())


def run_cli_kb_list(node_path: str = None, limit: int = 10) -> subprocess.CompletedProcess:
    """Helper to run kb list command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "list"]

    if node_path:
        cmd.extend(["--node", node_path])

    cmd.extend(["--limit", str(limit)])

    return subprocess.run(cmd, capture_output=True, text=True, env=_get_http_env())


def run_cli_kb_retrieve(doc_id: str) -> subprocess.CompletedProcess:
    """Helper to run kb retrieve command with given arguments."""
    cmd = [sys.executable, "main.py", "kb", "retrieve", doc_id]
    return subprocess.run(cmd, capture_output=True, text=True, env=_get_http_env())


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

    return subprocess.run(cmd, capture_output=True, text=True, env=_get_http_env())


# ============================================================================
# KB SEARCH COMMAND TESTS
# ============================================================================


def test_http_kb_search_by_query_returns_results():
    """Should execute 'kb search' via HTTP and return matching documents."""
    result = run_cli_kb_search("Template", top_k=5)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Found" in result.stdout
    assert "doc-001" in result.stdout


def test_http_kb_search_respects_top_k_limit():
    """Should respect --top-k limit in search command via HTTP."""
    result = run_cli_kb_search("e", top_k=1)

    assert result.returncode == 0
    # With top_k=1, should return at most 1 document
    assert result.stdout.count("ID:") <= 1


def test_http_kb_search_case_insensitive():
    """Should perform case-insensitive search via HTTP."""
    result_lower = run_cli_kb_search("devops", top_k=5)
    result_upper = run_cli_kb_search("DEVOPS", top_k=5)

    assert result_lower.returncode == 0
    assert result_upper.returncode == 0
    # Both should find the same document
    assert "doc-002" in result_lower.stdout
    assert "doc-002" in result_upper.stdout


def test_http_kb_search_returns_message_when_no_match():
    """Should return message when search query matches nothing via HTTP."""
    result = run_cli_kb_search("nonexistent-xyz-abc", top_k=5)

    assert result.returncode == 0
    assert "No documents found" in result.stdout


def test_http_kb_search_searches_in_title():
    """Should find documents matching query in title via HTTP."""
    result = run_cli_kb_search("Template", top_k=5)

    assert result.returncode == 0
    assert "Customer Response Template" in result.stdout


# ============================================================================
# KB LIST COMMAND TESTS
# ============================================================================


def test_http_kb_list_all_documents():
    """Should list all documents when no filter provided via HTTP."""
    result = run_cli_kb_list()

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Found" in result.stdout
    assert "doc-001" in result.stdout


def test_http_kb_list_filters_by_node_path_prefix():
    """Should filter by --node path prefix via HTTP."""
    result = run_cli_kb_list(node_path="/templates")

    assert result.returncode == 0
    assert "doc-001" in result.stdout
    assert "/templates/email" in result.stdout


def test_http_kb_list_filters_by_exact_node_path():
    """Should filter by exact --node path via HTTP."""
    result = run_cli_kb_list(node_path="/team/devops")

    assert result.returncode == 0
    assert "doc-002" in result.stdout


def test_http_kb_list_respects_limit():
    """Should respect --limit parameter via HTTP."""
    result = run_cli_kb_list(node_path=None, limit=1)

    assert result.returncode == 0
    # With limit=1, should return at most 1 document
    assert result.stdout.count("ID:") <= 1


def test_http_kb_list_returns_empty_when_no_match():
    """Should return message when node path doesn't exist via HTTP."""
    result = run_cli_kb_list(node_path="/nonexistent/path")

    assert result.returncode == 0
    assert "No documents found" in result.stdout


# ============================================================================
# KB RETRIEVE COMMAND TESTS
# ============================================================================


def test_http_kb_retrieve_existing_document():
    """Should retrieve a document by ID via HTTP."""
    result = run_cli_kb_retrieve("doc-001")

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Document Details:" in result.stdout
    assert "doc-001" in result.stdout
    assert "Customer Response Template" in result.stdout


def test_http_kb_retrieve_returns_full_document():
    """Should return document with all fields populated via HTTP."""
    result = run_cli_kb_retrieve("doc-002")

    assert result.returncode == 0
    assert "doc-002" in result.stdout
    assert "DevOps Team Information" in result.stdout
    assert "Content:" in result.stdout


def test_http_kb_retrieve_nonexistent_raises_error():
    """Should show error when document not found via HTTP."""
    result = run_cli_kb_retrieve("doc-999")

    assert result.returncode != 0
    assert "not found" in result.stdout.lower()


# ============================================================================
# KB ADD COMMAND TESTS
# ============================================================================


def test_http_kb_add_new_document_returns_success():
    """Should add a new document via HTTP and return success message."""
    unique_id = f"doc-http-cli-{int(time.time() * 1000)}"
    result = run_cli_kb_add(
        doc_id=unique_id,
        title="New Template via CLI",
        content="This is a new template from CLI",
        node_path="/templates/cli",
        tags="cli,template"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert unique_id in result.stdout


def test_http_kb_add_document_makes_it_retrievable():
    """Should make added document retrievable via retrieve via HTTP."""
    unique_id = f"doc-http-retrieve-{int(time.time() * 1000)}"

    # First, add a document
    add_result = run_cli_kb_add(
        doc_id=unique_id,
        title="Retrievable Document",
        content="Can retrieve this document",
        node_path="/docs/new",
        tags="test"
    )

    assert add_result.returncode == 0

    # Then retrieve it
    retrieve_result = run_cli_kb_retrieve(unique_id)

    assert retrieve_result.returncode == 0
    assert unique_id in retrieve_result.stdout
    assert "Retrievable Document" in retrieve_result.stdout


def test_http_kb_add_document_appears_in_list():
    """Should make added document appear in list via HTTP."""
    unique_id = f"doc-http-list-{int(time.time() * 1000)}"

    # First, add a document
    add_result = run_cli_kb_add(
        doc_id=unique_id,
        title="Listable Document",
        content="Should appear in list",
        node_path="/docs/custom-http",
        tags="test"
    )

    assert add_result.returncode == 0

    # Then list with the same path
    list_result = run_cli_kb_list(node_path="/docs/custom-http")

    assert list_result.returncode == 0
    assert unique_id in list_result.stdout


def test_http_kb_add_duplicate_raises_error():
    """Should show error when adding document with existing ID via HTTP."""
    result = run_cli_kb_add(
        doc_id="doc-001",  # already exists
        title="Duplicate",
        content="This is a duplicate",
        node_path="/docs/dup",
        tags="dup"
    )

    assert result.returncode != 0
    assert "already exists" in result.stdout.lower()


def test_http_kb_add_document_with_tags():
    """Should add document with multiple tags via HTTP."""
    unique_id = f"doc-http-tags-{int(time.time() * 1000)}"

    result = run_cli_kb_add(
        doc_id=unique_id,
        title="Tagged Document",
        content="Document with tags",
        node_path="/docs/tagged",
        tags="tag1,tag2,tag3"
    )

    assert result.returncode == 0
    assert "added successfully" in result.stdout.lower()


# ============================================================================
# KB ADD COMMAND TESTS - FILE IMPORT VIA HTTP
# ============================================================================


def test_http_kb_add_document_from_file(tmp_path):
    """Should add a new document from file via HTTP and return success message."""
    # Create a test file
    test_file = tmp_path / "template.md"
    file_content = "# Email Template\n\nThis is an email response template."
    test_file.write_text(file_content, encoding="utf-8")

    unique_id = f"doc-http-file-{int(time.time() * 1000)}"
    result = run_cli_kb_add(
        doc_id=unique_id,
        title="Email Response Template",
        file_path=str(test_file),
        path_alias="/templates/email",
        tags="template,email"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert unique_id in result.stdout


def test_http_kb_add_document_from_file_auto_title(tmp_path):
    """Should add document from file via HTTP with auto-generated title from filename."""
    # Create a test file
    test_file = tmp_path / "sms_template.md"
    file_content = "# SMS Template\n\nQuick response template for SMS."
    test_file.write_text(file_content, encoding="utf-8")

    unique_id = f"doc-http-file-auto-{int(time.time() * 1000)}"
    result = run_cli_kb_add(
        doc_id=unique_id,
        file_path=str(test_file),
        node_path="/templates/sms",
        tags="template,sms"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()
    assert unique_id in result.stdout


def test_http_kb_add_document_from_file_with_path_alias(tmp_path):
    """Should add document from file via HTTP using --path instead of --node."""
    # Create a test file
    test_file = tmp_path / "devops_guide.md"
    file_content = "# DevOps Setup Guide\n\nSteps to setup DevOps environment."
    test_file.write_text(file_content, encoding="utf-8")

    unique_id = f"doc-http-file-path-{int(time.time() * 1000)}"
    result = run_cli_kb_add(
        doc_id=unique_id,
        title="DevOps Setup",
        file_path=str(test_file),
        path_alias="/docs/guides",
        tags="guide,devops"
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "added successfully" in result.stdout.lower()


def test_http_kb_add_document_from_file_appears_in_list(tmp_path):
    """Should make document added from file via HTTP appear in list."""
    # Create a test file
    test_file = tmp_path / "team_info.md"
    file_content = "# Team Information\n\nTeam contact and roles."
    test_file.write_text(file_content, encoding="utf-8")

    unique_id = f"doc-http-file-list-{int(time.time() * 1000)}"

    # Add document from file
    add_result = run_cli_kb_add(
        doc_id=unique_id,
        title="Team Info",
        file_path=str(test_file),
        node_path="/team-http",
        tags="team"
    )

    assert add_result.returncode == 0

    # List with the same path
    list_result = run_cli_kb_list(node_path="/team-http")

    assert list_result.returncode == 0
    assert unique_id in list_result.stdout


def test_http_kb_add_document_from_file_makes_it_retrievable(tmp_path):
    """Should make document added from file via HTTP retrievable via retrieve."""
    # Create a test file
    test_file = tmp_path / "handbook.md"
    file_content = "# Company Handbook\n\nCompany policies and procedures."
    test_file.write_text(file_content, encoding="utf-8")

    unique_id = f"doc-http-file-retrieve-{int(time.time() * 1000)}"

    # Add document from file
    add_result = run_cli_kb_add(
        doc_id=unique_id,
        title="Company Handbook",
        file_path=str(test_file),
        node_path="/docs-http",
        tags="handbook"
    )

    assert add_result.returncode == 0

    # Retrieve it
    retrieve_result = run_cli_kb_retrieve(unique_id)

    assert retrieve_result.returncode == 0
    assert unique_id in retrieve_result.stdout
    assert "Company Handbook" in retrieve_result.stdout


def test_http_kb_add_document_from_nonexistent_file_fails():
    """Should fail when trying to add document from non-existent file via HTTP."""
    result = run_cli_kb_add(
        doc_id="doc-http-file-fail",
        file_path="/nonexistent/file.md",
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


def test_http_kb_add_document_from_empty_file_fails(tmp_path):
    """Should fail when trying to add document from empty file via HTTP."""
    # Create empty file
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-http-file-empty",
        file_path=str(empty_file),
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "empty" in result.stdout.lower() or "error" in result.stdout.lower()


def test_http_kb_add_document_from_whitespace_only_file_fails(tmp_path):
    """Should fail when trying to add document from whitespace-only file via HTTP."""
    # Create whitespace-only file
    whitespace_file = tmp_path / "whitespace.md"
    whitespace_file.write_text("   \n\n  ", encoding="utf-8")

    result = run_cli_kb_add(
        doc_id="doc-http-file-whitespace",
        file_path=str(whitespace_file),
        node_path="/docs"
    )

    assert result.returncode != 0
    assert "empty" in result.stdout.lower() or "error" in result.stdout.lower()
