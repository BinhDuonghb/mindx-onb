# Ticket Manager CLI with Knowledge Base Integration

A command-line ticket management system with integrated Knowledge Base support. Create, list, show, update, and delete tickets; plus search and manage a knowledge base of documents.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
  - [Ticket Commands](#ticket-commands)
  - [Knowledge Base Commands](#knowledge-base-commands)
- [Examples](#examples)
- [Testing](#testing)
- [Architecture](#architecture)

## Features

### Ticket Management
- **Create tickets** with title, description, priority, and tags
- **List tickets** with optional filtering by status, priority, or tag
- **Show ticket** details by UUID
- **Update ticket** status (open, in-progress, closed)
- **Delete tickets** by UUID
- Persistent storage using JSON files
- UUID-based ticket identification

### Knowledge Base Management
- **Search documents** by keyword with configurable result limit
- **List documents** by path hierarchy with filtering
- **Retrieve full documents** with all metadata
- **Add new documents** to the knowledge base
- Support for both mock and HTTP KB clients
- Environment-based client switching for development/production

## Project Structure

```
TicketManagerCLI/
├── main.py                          # Entry point
├── README.md                         # This file
├── pytest.ini                        # pytest configuration
├── conftest.py                       # pytest fixtures and configuration
├── run_tests.py                      # Test runner with logging
├── requirements.txt                  # Python dependencies
│
├── cli/
│   ├── commands/                     # Command implementations
│   │   ├── kb_add.py
│   │   ├── kb_list.py
│   │   ├── kb_retrieve.py
│   │   ├── kb_search.py
│   │   └── ... (ticket commands)
│   └── parsers/
│       ├── kb_parser.py              # KB argument parser
│       └── ... (ticket parsers)
│
├── data/
│   ├── db_client.py                 # Database client (JSON persistence)
│   └── tickets.json                 # Ticket storage (auto-created)
│
├── ticket_manager/
│   ├── __init__.py
│   ├── config.py                    # Configuration and storage setup
│   ├── models/
│   │   └── ticket.py                # Ticket dataclass model
│   ├── validators/
│   │   ├── email_validator.py       # Email validation logic
│   │   └── ticket_validator.py      # Ticket field validation
│   └── services/
│       └── ticketService.py         # Business logic for ticket operations
│
├── KB/
│   ├── clients/
│   │   ├── base.py                  # Base client interface
│   │   ├── mockKBClient.py          # In-memory mock KB client
│   │   └── httpKBClient.py          # HTTP client for real KB API
│   ├── models/
│   │   ├── document.py              # Document domain models
│   │   └── search.py                # Search result models
│   ├── config.py                    # KB configuration
│   ├── factory.py                   # Client factory
│   └── mock_data.py                 # Mock test data
│
└── tests/
    ├── units/
    │   ├── test_email_validator.py
    │   └── test_ticket_validator.py
    ├── integrations/
    │   ├── test_cli_error_handling.py
    │   ├── test_create_ticket_cli.py
    │   ├── test_delete_ticket_cli.py
    │   ├── test_list_ticket_cli.py
    │   ├── test_show_ticket_cli.py
    │   ├── test_update_ticket_cli.py
    │   ├── test_db_client.py
    │   ├── test_ticket_service.py
    │   └── KB/
    │       ├── test_kb_mock_client.py
    │       ├── test_kb_http_client.py
    │       ├── test_kb_mock_client_cli.py
    │       └── test_http_kb_client_cli.py
    └── e2e/
        ├── test_kb_service_e2e.py    # End-to-end KB service integration tests
        └── README.md                 # E2E test documentation
```

## Requirements

- Python 3.10+ (tested and verified with Python 3.13.3)
- pip (Python package manager)
- Node.js 18+ (for running KBService backend)

## Setup

### 1. Clone or Navigate to Project

```bash
cd d:\Study\mindx\mindx-onb\assignments\week3\TicketManagerCLI
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```bash
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Setup Knowledge Base Service (Optional)

For KB commands to work with real API, install and start KBService:

```bash
cd ../KBService
npm install
npm run build
npm start
```

KBService will listen on `http://localhost:8000`

### 6. Configure KB Client

Set environment variables in PowerShell or add to `.env`:

**Use Mock Client (default, no KBService needed):**
```powershell
$env:KB_CLIENT='mock'
```

**Use HTTP Client (requires running KBService):**
```powershell
$env:KB_CLIENT='http'
$env:KB_API_URL='http://localhost:8000'
```

Or add to `.env` file:
```
KB_CLIENT=mock
KB_API_URL=http://localhost:8000
```

### 7. Verify Installation

```bash
python main.py -h
```

You should see help for both ticket and KB commands.

## Usage

### Getting Help

```bash
# Main help
python main.py -h

# Ticket commands help
python main.py ticket -h
python main.py ticket create -h
python main.py ticket list -h

# Knowledge Base commands help
python main.py kb -h
python main.py kb search -h
python main.py kb list -h
python main.py kb retrieve -h
python main.py kb add -h
```

## Ticket Commands

### Create Ticket

Create a new ticket with a title and optional fields.

```bash
python main.py ticket create --title "TITLE" [OPTIONS]
```

**Options:**
- `--title` (required): Ticket title
- `--description`: Ticket description (default: empty)
- `--priority`: Priority level - `low`, `medium`, `high` (default: medium)
- `--tags`: Comma-separated tags (default: empty)
- `--load-seed-data`: Load seed data for testing

**Examples:**
```bash
python main.py ticket create --title "Fix login bug"

python main.py ticket create --title "New feature" --description "Add dark mode" \
  --priority high

python main.py ticket create --load-seed-data
```

### List Tickets

List all tickets or filter by status, priority, or tag.

```bash
python main.py ticket list [OPTIONS]
```

**Options:**
- `--status`: Filter by status - `open`, `in-progress`, `closed`
- `--priority`: Filter by priority - `low`, `medium`, `high`
- `--tag`: Filter by tag name

**Examples:**
```bash
python main.py ticket list
python main.py ticket list --status open --priority high
```

### Show Ticket

Display detailed information about a specific ticket.

```bash
python main.py ticket show TICKET_UUID
```

### Update Ticket

Update a ticket's status.

```bash
python main.py ticket update TICKET_UUID --status STATUS
```

### Delete Ticket

Delete a ticket permanently.

```bash
python main.py ticket delete TICKET_UUID
```

## Knowledge Base Commands

Knowledge Base commands work with both mock client (in-memory) and HTTP client (real API).

### Search Documents

Search documents by keyword.

```bash
python main.py kb search "QUERY" [--top-k K]
```

**Options:**
- `QUERY` (required): Search term
- `--top-k`: Number of results (default: 5)

**Examples:**
```bash
python main.py kb search "template"
python main.py kb search "customer response" --top-k 10
```

### List Documents

List documents by path hierarchy.

```bash
python main.py kb list [--node PATH] [--limit N]
```

**Options:**
- `--node`: Node path filter (e.g., `/templates/email`)
- `--limit`: Maximum results (default: 10)

**Examples:**
```bash
python main.py kb list
python main.py kb list --node /templates/email --limit 20
```

### Retrieve Document

Get full details of a specific document.

```bash
python main.py kb retrieve DOC_ID
```

**Examples:**
```bash
python main.py kb retrieve doc-001
python main.py kb retrieve e2e-doc-12345
```

### Add Document

Add a new document to the knowledge base.

```bash
python main.py kb add --id ID --title TITLE --content CONTENT \
  --node PATH [--tags TAGS]
```

**Options:**
- `--id` (required): Document identifier
- `--title` (required): Document title
- `--content` (required): Document content
- `--node` (required): Node path (e.g., `/templates/email`)
- `--tags`: Comma-separated tags

**Examples:**
```bash
python main.py kb add --id new-001 --title "Email Template" \
  --content "Dear customer..." --node /templates/email --tags "template,email"
```

## Examples

### Ticket Workflow

```bash
# 1. Create a bug ticket
python main.py ticket create --title "Login page CSS broken" \
  --description "CSS not loading on mobile devices" \
  --priority high --tags "bug,frontend,mobile"

# 2. List open high-priority tickets
python main.py ticket list --status open --priority high

# 3. Show ticket details
python main.py ticket show <UUID>

# 4. Update status to in-progress
python main.py ticket update <UUID> --status in-progress

# 5. Close the ticket when done
python main.py ticket update <UUID> --status closed
```

### Knowledge Base Workflow

```bash
# 1. Search for email templates
python main.py kb search "response" --top-k 5

# 2. List templates in a path
python main.py kb list --node /templates/email

# 3. Retrieve a specific template
python main.py kb retrieve doc-001

# 4. Add a new template
python main.py kb add --id new-template --title "Custom Template" \
  --content "Custom content here" --node /templates/custom \
  --tags "custom,template"
```

## Testing

The project includes comprehensive integration tests covering both ticket and KB commands, plus end-to-end tests that orchestrate the full service lifecycle.

### Run All Tests

```bash
python run_tests.py ./tests -v
```

### Run Ticket Tests

```bash
python run_tests.py ./tests/integrations -v
```

### Run KB Tests

```bash
python run_tests.py ./tests/integrations/KB -v
```

### Run E2E Tests (with KBService)

E2E tests automatically build and start KBService, run CLI commands, then stop the service.

```bash
python run_tests.py ./tests/e2e/test_kb_service_e2e.py -v
```

**Prerequisites:** Node.js installed (KBService will be built automatically)

**Output Example:**
```
[E2E] Building KBService...
[E2E] Starting KBService...
[E2E] KBService is ready!
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_service_starts_successfully PASSED
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_add_and_retrieve_document PASSED
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_add_list_and_search PASSED
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_multiple_operations_sequence PASSED
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_empty_search_returns_gracefully PASSED
tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_retrieve_nonexistent_returns_error PASSED
[E2E] Stopping KBService...
[E2E] KBService stopped.
============================== 6 passed in 6.11s ==============================
```

### Run Specific Test

```bash
python -m pytest tests/integrations/KB/test_http_kb_client_cli.py::test_http_kb_search_by_query_returns_results -v
```

### Test Coverage

**Ticket Tests:** 100+ test cases covering all CRUD operations, filtering, validation, error handling

**KB Tests:** 147 test cases covering search, list, retrieve, add, file import, and data safety with both mock and HTTP clients:
- Corrupt JSON Safety: 8 tests (data integrity, backup creation, error handling)
- Mock Client: 27 tests (basic operations + persistence)
- Mock CLI: 22 tests (command parsing and output)
- HTTP Client: 14 tests (real API integration)
- HTTP CLI: 25 tests (end-to-end CLI workflows with file import)
- Input Validation Parity: 51 tests (mock/HTTP consistency)

**E2E Tests:** 6 tests covering full service lifecycle:
- Service startup and health check
- Document add and retrieve
- Document add, list, and search workflow
- Multiple sequential operations
- Error handling (empty results, nonexistent documents)

## Architecture

### Layers

```
┌─────────────────────┐
│   CLI Commands      │ (user input parsing)
├─────────────────────┤
│   Handlers          │ (command logic)
├─────────────────────┤
│   Services          │ (business logic)
├─────────────────────┤
│   Clients/Storage   │ (data access)
└─────────────────────┘
```

### KB Integration

```
┌──────────────────┐
│  CLI KB Commands │
├──────────────────┤
│  KB Client Iface │
├────┬─────────────┤
│    │ (switched)  │
├────▼──────┐      │
│ MockKB    │ HTTPKBClient
│ Client    │  ↓ HTTP
│ (memory)  │  ↓ (real API)
│           │ KBService
└───────────┴─────┘
```

### Client Switching

Environment variable `KB_CLIENT` determines which implementation to use:

```python
# In KB/config.py
if os.getenv("KB_CLIENT") == "http":
    client = HTTPKBClient(api_url)
else:
    client = MockKBClient()  # default
```

## Troubleshooting

### KB Commands Show "No Client"

Ensure `KB_CLIENT` environment variable is set:
```bash
set KB_CLIENT=mock  # or http
```

### HTTP Client Connection Refused

- Verify KBService is running: `curl http://localhost:8000/health`
- Check `KB_API_URL` is correct: `echo %KB_API_URL%`
- Ensure Node.js is installed for building KBService

### E2E Tests Timeout

- Port 8000 may be in use: `netstat -ano | findstr :8000`
- KBService build may be slow: check `npm run build` completes successfully
- Try increasing `KB_SERVICE_START_TIMEOUT` in test file

### Mock Client vs HTTP Client Behavior Differs

- Mock client uses predefined test data
- HTTP client queries real service
- For debugging, run same query with both and compare results
- Check test data initialization in respective client files

## Data Storage

### Tickets

Tickets are stored in `data/tickets.json` in JSON format.

### Knowledge Base

- **Mock client:** Supports file-based persistence (JSON) and in-memory storage
  - Can load/save from `persist_file` parameter
  - Test data: 3 sample documents initialized on startup
  - Useful for local development and testing
- **HTTP client:** Data persisted by KBService backend
  - For tests: in-memory storage (data lost on service restart)
  - For production: can be configured with persistent backend (database, file storage)

## License

Educational project for Mindx training program.
