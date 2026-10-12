# Ticket Manager CLI

A command-line ticket management system written in Python. Create, list, show, update, and delete tickets with filtering capabilities.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
  - [Create Ticket](#create-ticket)
  - [List Tickets](#list-tickets)
  - [Show Ticket](#show-ticket)
  - [Update Ticket](#update-ticket)
  - [Delete Ticket](#delete-ticket)
- [Examples](#examples)
- [Testing](#testing)

## Features

- **Create tickets** with title, description, priority, and tags
- **List tickets** with optional filtering by status, priority, or tag
- **Show ticket** details by UUID
- **Update ticket** status (open, in-progress, closed)
- **Delete tickets** by UUID
- Persistent storage using JSON files
- UUID-based ticket identification
- Comprehensive CLI help system

## Project Structure

```
TicketManagerCLI/
├── main.py                          # Entry point
├── README.md                         # This file
├── pytest.ini                        # pytest configuration
├── data/
│   └── tickets.json                 # Ticket storage (auto-created)
├── ticket_manager/
│   ├── __init__.py
│   ├── cli.py                       # CLI command handlers
│   ├── config.py                    # Configuration and storage setup
│   ├── db_client.py                 # Database client (JSON persistence)
│   ├── models/
│   │   └── ticket.py                # Ticket dataclass model
│   └── services/
│       └── ticketService.py         # Business logic for ticket operations
└── tests/
    └── integrations/
        ├── test_create_ticket_cli.py    # Create command tests (15+ cases)
        ├── test_list_ticket_cli.py      # List command tests (17+ cases)
        ├── test_show_ticket_cli.py      # Show command tests (11+ cases)
        ├── test_update_ticket_cli.py    # Update command tests (14+ cases)
        ├── test_delete_ticket_cli.py    # Delete command tests (18+ cases)
        ├── test_db_client.py            # DBClient tests
        └── test_ticket_service.py       # TicketService tests
```

## Requirements

- Python 3.9+
- pip (Python package manager)

## Setup

### 1. Clone or Navigate to Project

```bash
cd D:\Study\mindx\mindx-onb\assignments\week2\TicketManagerCLI
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

### 5. Verify Installation

```bash
python main.py -h
```

You should see the main help message with available commands.

## Usage

### Getting Help

```bash
# Main help
python main.py -h

# Command-specific help
python main.py create -h
python main.py list -h
python main.py show -h
python main.py update -h
python main.py delete -h
```

### Create Ticket

Create a new ticket with a title and optional description, priority, and tags.

**Command:**
```bash
python main.py create --title "TITLE" [--description "DESCRIPTION"] [--priority PRIORITY] [--tags TAGS]
```

**Arguments:**
- `--title` (required): Ticket title
- `--description` (optional): Ticket description (default: empty)
- `--priority` (optional): Priority level - `low`, `medium`, `high` (default: medium)
- `--tags` (optional): Comma-separated tags (default: empty)

**Examples:**
```bash
python main.py create --title "Fix login bug"

python main.py create --title "New feature" --description "Add dark mode" --priority high

python main.py create --title "Bug fix" --tags "frontend,urgent" --priority high --description "CSS issue on mobile"
```

### List Tickets

List all tickets or filter by status, priority, or tag.

**Command:**
```bash
python main.py list [--status STATUS] [--priority PRIORITY] [--tag TAG]
```

**Arguments:**
- `--status` (optional): Filter by status - `open`, `in-progress`, `closed`
- `--priority` (optional): Filter by priority - `low`, `medium`, `high`
- `--tag` (optional): Filter by tag name

**Examples:**
```bash
# List all tickets
python main.py list

# List open tickets
python main.py list --status open

# List high priority tickets
python main.py list --priority high

# List tickets with 'bug' tag
python main.py list --tag bug

# Combine filters
python main.py list --status open --priority high --tag urgent
```

### Show Ticket

Display detailed information about a specific ticket.

**Command:**
```bash
python main.py show TICKET_UUID
```

**Arguments:**
- `TICKET_UUID` (required): The UUID of the ticket to display

**Examples:**
```bash
python main.py show 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

python main.py show 550e8400-e29b-41d4-a716-446655440000
```

**Output includes:**
- Ticket ID (UUID)
- Title
- Description
- Status
- Priority
- Tags
- Creation timestamp

### Update Ticket

Update a ticket's status.

**Command:**
```bash
python main.py update TICKET_UUID --status STATUS
```

**Arguments:**
- `TICKET_UUID` (required): The UUID of the ticket to update
- `--status` (required): New status - `open`, `in-progress`, `closed`

**Examples:**
```bash
# Mark ticket as in progress
python main.py update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status in-progress

# Close a ticket
python main.py update 550e8400-e29b-41d4-a716-446655440000 --status closed

# Reopen a ticket
python main.py update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status open
```

### Delete Ticket

Delete a ticket permanently.

**Command:**
```bash
python main.py delete TICKET_UUID
```

**Arguments:**
- `TICKET_UUID` (required): The UUID of the ticket to delete

**Examples:**
```bash
python main.py delete 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

python main.py delete 550e8400-e29b-41d4-a716-446655440000
```

## Examples

### Workflow Example

```bash
# 1. Create a bug ticket
python main.py create --title "Login page CSS broken" \
  --description "CSS not loading on mobile devices" \
  --priority high \
  --tags "bug,frontend,mobile"

# Output: Ticket created successfully with ID: 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

# 2. List all open tickets
python main.py list --status open

# 3. Show ticket details
python main.py show 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

# 4. Update status to in-progress
python main.py update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status in-progress

# 5. List high priority tickets
python main.py list --priority high

# 6. Update status to closed when done
python main.py update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status closed

# 7. Delete the ticket (optional)
python main.py delete 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9
```

### Filtering Examples

```bash
# Find all bugs
python main.py list --tag bug

# Find urgent tasks that are open
python main.py list --tag urgent --status open

# Find all high priority frontend issues
python main.py list --priority high --tag frontend

# Find all in-progress tasks
python main.py list --status in-progress
```

## Testing

The project includes comprehensive integration tests covering all CLI commands.

### Run All Tests

```bash
pytest tests/integrations/ -v
```

### Run Specific Test File

```bash
# Test create command
pytest tests/integrations/test_create_ticket_cli.py -v

# Test list command
pytest tests/integrations/test_list_ticket_cli.py -v

# Test show command
pytest tests/integrations/test_show_ticket_cli.py -v

# Test update command
pytest tests/integrations/test_update_ticket_cli.py -v

# Test delete command
pytest tests/integrations/test_delete_ticket_cli.py -v
```

### Run Specific Test

```bash
pytest tests/integrations/test_create_ticket_cli.py::TestCreateTicketCLI::test_create_ticket_happy_path -v
```

### Test Coverage

The test suite includes **60+ test cases** covering:
- Happy path scenarios
- Edge cases
- Error handling
- Input validation
- Data persistence
- Filter combinations
- Special characters
- UUID validation

## Data Storage

Tickets are stored in `data/tickets.json` in JSON format:

```json
[
  {
    "id": "1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9",
    "title": "Fix login bug",
    "description": "Login returns 500",
    "status": "open",
    "priority": "high",
    "tags": ["bug", "backend"],
    "created_at": "2026-10-12T16:00:01.777187"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Add dark mode",
    "description": "",
    "status": "in-progress",
    "priority": "medium",
    "tags": ["feature", "frontend"],
    "created_at": "2026-10-12T16:05:30.123456"
  }
]
```

## Architecture

### Components

1. **CLI (`cli.py`)**: Command-line interface with argument parsing and command handlers
2. **TicketService (`services/ticketService.py`)**: Business logic layer for CRUD operations
3. **DBClient (`db_client.py`)**: Persistence layer for JSON file operations
4. **Ticket Model (`models/ticket.py`)**: Data model using Python dataclass
5. **Config (`config.py`)**: Configuration and storage initialization

### Data Flow

```
CLI Input
  ↓
Parser (argparse)
  ↓
Handler Function (create/list/show/update/delete)
  ↓
TicketService
  ↓
DBClient
  ↓
JSON File (tickets.json)
```

## Troubleshooting

### "Module not found" error

Make sure `pytest.ini` is in the project root with:
```ini
[pytest]
pythonpath = .
```

### UUID validation error

Ensure you're using a valid UUID format when using `show`, `update`, or `delete` commands. UUIDs look like: `550e8400-e29b-41d4-a716-446655440000`

### No tickets found

- Create a ticket first with `create` command
- Check that you're using correct filter values (status: open/in-progress/closed, priority: low/medium/high)

## License

Educational project for Mindx training program.
