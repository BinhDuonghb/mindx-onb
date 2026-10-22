"""E2E tests for KBService and CLI integration.

This test module orchestrates the full lifecycle:
1. Build and start the KBService
2. Run CLI commands against the service
3. Verify the end-to-end flow
4. Stop the service and clean up
"""
import os
import subprocess
import sys
import time
import pytest
import requests
from pathlib import Path


# ============================================================================
# CONSTANTS AND PATHS
# ============================================================================

KB_SERVICE_DIR = Path(__file__).parent.parent.parent.parent / "KBService"
KB_API_URL = "http://localhost:8000"
KB_API_HEALTH = f"{KB_API_URL}/health"
KB_SERVICE_START_TIMEOUT = 30  # seconds
KB_SERVICE_STOP_TIMEOUT = 10  # seconds


# ============================================================================
# FIXTURES FOR SERVICE LIFECYCLE MANAGEMENT
# ============================================================================


@pytest.fixture(scope="session")
def kb_service_process():
    """
    Session-scoped fixture that builds and starts the KBService.

    Ensures the service runs for the duration of all e2e tests,
    then stops and cleans up after all tests complete.
    """
    print("\n[E2E] Building KBService...")
    build_result = subprocess.run(
        "npm run build",
        cwd=KB_SERVICE_DIR,
        capture_output=True,
        text=True,
        shell=True
    )

    if build_result.returncode != 0:
        raise RuntimeError(
            f"Failed to build KBService:\n{build_result.stderr}"
        )

    print("[E2E] Starting KBService...")
    process = subprocess.Popen(
        "npm start",
        cwd=KB_SERVICE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True
    )

    # Wait for service to be ready
    service_ready = _wait_for_service(KB_API_HEALTH, KB_SERVICE_START_TIMEOUT)

    if not service_ready:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError(
            "KBService failed to start within timeout. "
            "Check service logs or port availability."
        )

    print("[E2E] KBService is ready!")

    yield process

    # Cleanup: stop the service
    print("\n[E2E] Stopping KBService...")
    process.terminate()

    try:
        process.wait(timeout=KB_SERVICE_STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("[E2E] Service did not stop gracefully, force killing...")
        process.kill()
        process.wait()

    print("[E2E] KBService stopped.")


@pytest.fixture
def kb_cli_env():
    """
    Fixture providing environment variables configured for HTTP KB client.

    Ensures all CLI commands run against the KBService via HTTP.
    """
    env = os.environ.copy()
    env["KB_CLIENT"] = "http"
    env["KB_API_URL"] = KB_API_URL
    return env


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _wait_for_service(url: str, timeout: int) -> bool:
    """
    Poll the service health endpoint until it responds or timeout expires.

    Args:
        url: Service health check URL
        timeout: Maximum seconds to wait

    Returns:
        True if service responds, False if timeout reached
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(0.5)
            continue
        except Exception:
            time.sleep(0.5)
            continue

    return False


def run_cli_kb_search(
    query: str,
    top_k: int = 5,
    env: dict = None
) -> subprocess.CompletedProcess:
    """Helper to run kb search command via CLI."""
    if env is None:
        env = os.environ.copy()

    cmd = [sys.executable, "main.py", "kb", "search", query, "--top-k", str(top_k)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def run_cli_kb_add(
    doc_id: str,
    title: str,
    content: str,
    node_path: str,
    tags: str = "",
    env: dict = None
) -> subprocess.CompletedProcess:
    """Helper to run kb add command via CLI."""
    if env is None:
        env = os.environ.copy()

    cmd = [
        sys.executable, "main.py", "kb", "add",
        "--id", doc_id,
        "--title", title,
        "--content", content,
        "--node", node_path,
    ]

    if tags:
        cmd.extend(["--tags", tags])

    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def run_cli_kb_list(
    node_path: str = None,
    limit: int = 10,
    env: dict = None
) -> subprocess.CompletedProcess:
    """Helper to run kb list command via CLI."""
    if env is None:
        env = os.environ.copy()

    cmd = [sys.executable, "main.py", "kb", "list"]

    if node_path:
        cmd.extend(["--node", node_path])

    cmd.extend(["--limit", str(limit)])

    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def run_cli_kb_retrieve(
    doc_id: str,
    env: dict = None
) -> subprocess.CompletedProcess:
    """Helper to run kb retrieve command via CLI."""
    if env is None:
        env = os.environ.copy()

    cmd = [sys.executable, "main.py", "kb", "retrieve", doc_id]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


# ============================================================================
# E2E TEST CASES
# ============================================================================


class TestKBServiceE2E:
    """End-to-end tests for KBService and CLI integration."""

    def test_service_starts_successfully(self, kb_service_process):
        """Should start KBService successfully."""
        # Check that process is still running
        assert kb_service_process.poll() is None, \
            "KBService process terminated unexpectedly"

        # Check that health endpoint responds
        response = requests.get(KB_API_HEALTH)
        assert response.status_code == 200

    def test_e2e_add_and_retrieve_document(self, kb_service_process, kb_cli_env):
        """Should add a document via CLI and retrieve it via the service."""
        unique_id = f"e2e-doc-{int(time.time() * 1000)}"

        # Step 1: Add document via CLI
        add_result = run_cli_kb_add(
            doc_id=unique_id,
            title="E2E Test Document",
            content="This is an end-to-end test document",
            node_path="/e2e/test",
            tags="e2e,test",
            env=kb_cli_env
        )

        assert add_result.returncode == 0, \
            f"CLI add failed: {add_result.stderr}"
        assert "added successfully" in add_result.stdout.lower()
        assert unique_id in add_result.stdout

        # Step 2: Retrieve document via CLI
        retrieve_result = run_cli_kb_retrieve(unique_id, env=kb_cli_env)

        assert retrieve_result.returncode == 0, \
            f"CLI retrieve failed: {retrieve_result.stderr}"
        assert unique_id in retrieve_result.stdout
        assert "E2E Test Document" in retrieve_result.stdout
        assert "This is an end-to-end test document" in retrieve_result.stdout

    def test_e2e_add_list_and_search(self, kb_service_process, kb_cli_env):
        """Should add documents, list them, and search for them."""
        unique_id = f"e2e-search-{int(time.time() * 1000)}"

        # Step 1: Add document
        add_result = run_cli_kb_add(
            doc_id=unique_id,
            title="Searchable E2E Document",
            content="This document contains unique search terms",
            node_path="/e2e/search",
            env=kb_cli_env
        )

        assert add_result.returncode == 0

        # Step 2: List documents in the node path
        list_result = run_cli_kb_list(node_path="/e2e/search", env=kb_cli_env)

        assert list_result.returncode == 0
        assert unique_id in list_result.stdout

        # Step 3: Search for document by keyword
        search_result = run_cli_kb_search(
            "Searchable",
            top_k=10,
            env=kb_cli_env
        )

        assert search_result.returncode == 0
        assert unique_id in search_result.stdout

    def test_e2e_multiple_operations_sequence(self, kb_service_process, kb_cli_env):
        """Should handle a sequence of add, list, retrieve, search operations."""
        # Use unique timestamp to isolate this test run's data from previous runs
        test_timestamp = int(time.time() * 1000)
        unique_node_path = f"/e2e/sequence/{test_timestamp}"
        doc_ids = []

        # Add multiple documents
        for i in range(3):
            unique_id = f"e2e-seq-{i}-{test_timestamp}"
            doc_ids.append(unique_id)

            result = run_cli_kb_add(
                doc_id=unique_id,
                title=f"Sequential Document {i}",
                content=f"This is sequential document number {i}",
                node_path=unique_node_path,
                tags=f"seq,test,{i}",
                env=kb_cli_env
            )

            assert result.returncode == 0, \
                f"Failed to add document {i}: {result.stderr}"

        # List all documents in the path with higher limit to ensure we get all newly added docs
        list_result = run_cli_kb_list(node_path=unique_node_path, limit=100, env=kb_cli_env)
        assert list_result.returncode == 0

        # Verify all documents are listed
        for doc_id in doc_ids:
            assert doc_id in list_result.stdout, \
                f"Document {doc_id} not found in list"

        # Retrieve each document
        for doc_id in doc_ids:
            result = run_cli_kb_retrieve(doc_id, env=kb_cli_env)

            assert result.returncode == 0, \
                f"Failed to retrieve {doc_id}: {result.stderr}"
            assert doc_id in result.stdout

        # Search and verify results using a higher top_k to bypass accumulation from previous tests
        search_result = run_cli_kb_search(
            "Sequential",
            top_k=100,  # Increase to ensure we capture newly added documents
            env=kb_cli_env
        )

        assert search_result.returncode == 0
        for doc_id in doc_ids:
            assert doc_id in search_result.stdout, \
                f"Document {doc_id} not found in search results"

    def test_e2e_empty_search_returns_gracefully(self, kb_service_process, kb_cli_env):
        """Should handle search with no results gracefully."""
        result = run_cli_kb_search(
            "nonexistent-e2e-xyz-abc-123",
            top_k=5,
            env=kb_cli_env
        )

        assert result.returncode == 0
        assert "No documents found" in result.stdout

    def test_e2e_retrieve_nonexistent_returns_error(self, kb_service_process, kb_cli_env):
        """Should return error when retrieving nonexistent document."""
        result = run_cli_kb_retrieve(
            "e2e-nonexistent-doc-xyz",
            env=kb_cli_env
        )

        assert result.returncode != 0
        assert "not found" in result.stdout.lower()
