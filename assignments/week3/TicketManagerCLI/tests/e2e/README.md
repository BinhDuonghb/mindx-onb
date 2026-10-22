# E2E Tests for KBService

End-to-end tests that orchestrate the full lifecycle of KBService and CLI integration.

## What This Test Suite Does

1. **Builds** the KBService (`npm build`)
2. **Starts** the service (`npm start`) and waits for it to be ready
3. **Runs CLI commands** against the running service
4. **Verifies** the complete workflow (add, retrieve, list, search)
5. **Stops** the service and cleans up

## Running the Tests

### Prerequisites

- Node.js and npm installed
- KBService dependencies installed: `cd ../KBService && npm install`
- Python dependencies installed: `pip install -r requirements.txt`

### Run All E2E Tests

```bash
cd d:\Study\mindx\mindx-onb\assignments\week3\TicketManagerCLI
python -m pytest tests/e2e/test_kb_service_e2e.py -v
```

### Run Specific Test

```bash
python -m pytest tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_add_and_retrieve_document -v
```

### Run with Detailed Output

```bash
python -m pytest tests/e2e/test_kb_service_e2e.py -v -s
```

## Test Coverage

- **test_service_starts_successfully** — Verifies KBService starts and health endpoint responds
- **test_e2e_add_and_retrieve_document** — Add document via CLI, retrieve it back
- **test_e2e_add_list_and_search** — Add, list, and search for documents
- **test_e2e_multiple_operations_sequence** — Multiple operations in sequence
- **test_e2e_empty_search_returns_gracefully** — Handles empty search results
- **test_e2e_retrieve_nonexistent_returns_error** — Error handling for missing documents

## Important Notes

- The `kb_service_process` fixture is **session-scoped**, meaning the service starts once at the beginning and runs for all tests, then stops once at the end.
- The service must be built successfully before tests run.
- The service listens on `http://localhost:8000` by default.
- If the service fails to start, check:
  - Port 8000 is not in use
  - Node dependencies are installed
  - TypeScript build completes without errors

## Troubleshooting

### "KBService failed to start within timeout"

- Ensure port 8000 is free: `netstat -ano | findstr :8000` (Windows)
- Check KBService is buildable: `cd KBService && npm build`
- Increase `KB_SERVICE_START_TIMEOUT` if needed (slow machine)

### "Connection refused" in CLI tests

- Verify service is running: `curl http://localhost:8000/health`
- Check environment variables are set: `KB_CLIENT=http`, `KB_API_URL=http://localhost:8000`

### Tests pass individually but fail together

- This usually indicates state contamination. Each test should be independent.
- If needed, you can scope fixtures differently (see pytest fixture scoping).
