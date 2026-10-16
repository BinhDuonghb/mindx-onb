# Week 2: TDD Practice - Ticket Manager CLI

## Executive Summary

Successfully completed Week 2 TDD practice by building a fully functional **Ticket Manager CLI** using Test-Driven Development methodology.

The project demonstrates:

- **234 passing tests**: 90 unit tests + 144 integration tests
- Clean layered architecture with clear separation of concerns
- Test isolation using pytest's `tmp_path` fixture for clean, independent test runs
- Controlled AI assistance with rigorous validation through testing
- Comprehensive documentation and reflection on design decisions

---

## Acceptance Criteria - Completion Status

### 1. TDD Workflow Demonstrated

**Status:** ✅ COMPLETE

The project was developed through repeated **Red-Green-Refactor** cycles rather than by implementing the full application first and adding tests afterward.

The development sequence was:

1. Define the expected external behavior.
2. Write a failing test for that behavior.
3. Implement the minimum code required to make the test pass.
4. Refactor the code while keeping the tests green.
5. Start a new cycle for the next behavior.

### Initial CLI Skeleton

Before implementing business logic, I first created a base CLI using `argparse`.

The CLI could recognize the main commands:

```bash
tickets create
tickets list
tickets show
tickets update
tickets delete
```

At this point, these commands were only callable. They did not yet perform real ticket operations because the service and persistence layers had not been implemented.

This gave the project a stable command interface that could later be exercised by integration tests.

### TDD Cycle 1: Create Ticket

#### Red

The first feature developed through TDD was the `create` command.

I used Claude Code to help generate `test_create_ticket_cli.py`. The test described the expected user-visible behavior:

- the CLI accepts valid ticket input,
- the command exits successfully,
- a ticket is created,
- the ticket is persisted,
- the persisted fields match the input and defaults.

The test failed because the CLI did not yet have a working service or persistence layer.

This was the first **Red** state.

#### Discovering the Persistence Requirement

While trying to satisfy the create-ticket test, I identified that the application needed a reusable JSON persistence layer.

Instead of immediately writing implementation code, I started another TDD cycle for the database layer.

### TDD Cycle 2: DBClient

#### Red

I created `test_db_client.py` before `DBClient` existed.

The tests defined the expected behavior for interacting with `tickets.json`, including:

- reading data,
- writing data,
- updating data,
- deleting data,
- handling the file consistently.

#### Green

After the expected behavior was defined, I used Claude Code to assist with implementing `DBClient`.

I ran the tests and continued adjusting the implementation until the database tests passed.

The test suite, rather than the AI response, was treated as the source of truth for correctness.

#### Refactor

Once the tests were green, I refactored `DBClient`.

One important change was removing hard-coded assumptions about the JSON file path. The database path could instead be provided to `DBClient`.

This made the class:

- easier to reuse,
- easier to test,
- less tightly coupled to production configuration.

### TDD Cycle 3: Ticket Model, Validation, and TicketService

After the persistence layer was working, I moved to ticket-specific behavior.

I created the `Ticket` model and then used Claude Code to help generate unit tests for validation rules such as:

- title constraints,
- priority values,
- status values,
- email validation for extended fields,
- tag constraints.

These tests were intentionally written as **unit tests** because they validate small business rules in isolation and provide faster, more precise feedback than repeatedly running the full CLI.

I then created `test_ticket_service.py`.

`TicketService` reuses `DBClient`, but works specifically with `Ticket` objects and ticket-related operations such as:

- create,
- retrieve,
- find by ID,
- update,
- delete,
- validate before persistence.

The resulting dependency flow is:

```text
CLI
 ↓
TicketService
 ↓
DBClient
 ↓
tickets.json
```

### Returning to the Original Create CLI Test

After `DBClient` and `TicketService` were available, I returned to the original `test_create_ticket_cli.py`.

The integration test was updated so that, after running the CLI process, it used `TicketService` to retrieve the stored ticket and verify the result.

#### Green

I implemented `handle_create()` in the CLI layer.

Its responsibility was limited to:

1. Reading parsed arguments.
2. Converting CLI-specific input such as comma-separated tags.
3. Creating the ticket input.
4. Calling `TicketService`.
5. Displaying the result.

Once the create integration tests passed, the create feature reached the **Green** state.

#### Refactor

After the tests were green, I refactored the CLI for readability and usability.

Examples include:

- extracting command-specific handlers such as `handle_create()`,
- improving help text,
- keeping the main CLI function focused on parsing and routing.

The tests were run again after refactoring to confirm that observable behavior had not changed.

### Repeating the Cycle for Other Commands

After completing `create`, the same approach was repeated for:

- `list`,
- `show`,
- `update`,
- `delete`.

Because these commands followed patterns already established by the create flow, Claude Code was used more heavily for test scaffolding and implementation suggestions.

However, each generated change was still validated by the existing test suite before being accepted.

| Component | Red | Green | Refactor |
| --- | --- | --- | --- |
| **DBClient** | `test_db_client.py` | Implement read/write/update/delete | Remove hardcoding and allow configurable file paths |
| **TicketValidator** | `test_ticket_validator.py` | Implement validation rules | Separate validation responsibilities and improve messages |
| **EmailValidator** | `test_email_validator.py` | Implement email validation | Isolate reusable email validation logic |
| **TicketService** | `test_ticket_service.py` | Implement ticket-specific operations | Reuse `DBClient` and centralize validation |
| **CLI Create** | `test_create_ticket_cli.py` | Implement `handle_create()` | Improve command structure and help text |
| **CLI List** | `test_list_ticket_cli.py` | Implement `handle_list()` | Improve output formatting |
| **CLI Show** | `test_show_ticket_cli.py` | Implement `handle_show()` | Improve field display |
| **CLI Update** | `test_update_ticket_cli.py` | Implement `handle_update()` | Preserve unchanged fields and improve handler structure |
| **CLI Delete** | `test_delete_ticket_cli.py` | Implement `handle_delete()` | Clean up command flow |

**Key point:** tests were used to define expected behavior before or during implementation, and regression tests were rerun after refactoring.

**Evidence:** See [`TicketManagerCLI/REFLECTION.md`](./TicketManagerCLI/REFLECTION.md) for the detailed design and AI usage discussion.

---

### 2. CLI Tool Basic Functions Working

**Status:** ✅ COMPLETE + BONUS

All required commands are implemented and tested.

#### Create Ticket

```bash
tickets create \
  --title "Fix login bug" \
  --description "Users get 500 error" \
  --priority high \
  --tags "bug,backend" \
  --creator "dev@example.com" \
  --assignee "qa@example.com" \
  --estimated_time 5.5
```

#### List Tickets

```bash
tickets list
tickets list --status open
tickets list --priority high
tickets list --tag bug
```

#### Show Ticket Details

```bash
tickets show 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9
```

#### Update Ticket

```bash
tickets update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status closed
```

#### Delete Ticket

```bash
tickets delete 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9
```

The delete command was implemented as an additional feature beyond the core requirements.

---

### 3. Unit Tests Cover Ticket Logic and Validation

**Status:** ✅ COMPLETE

#### Files

- `tests/units/test_email_validator.py`
- `tests/units/test_ticket_validator.py`

**Total:** 90 unit tests

#### Coverage Areas

##### Email Validation

- valid and invalid formats,
- missing `@`,
- multiple `@`,
- empty and whitespace-only input,
- consecutive dots,
- domain boundary rules,
- local-part length,
- maximum email length.

##### Ticket Title Validation

- valid title,
- minimum length,
- title too short,
- title too long,
- empty or whitespace-only title,
- invalid data type.

##### Description Validation

- valid description,
- empty description,
- description too long,
- invalid data type.

##### Priority Validation

Supported values:

- `low`
- `medium`
- `high`

Tests also cover invalid priority values.

##### Status Validation

Supported values:

- `open`
- `in-progress`
- `closed`

Tests also cover invalid status values.

##### Tags Validation

- empty tag list,
- single tag,
- multiple tags,
- maximum number of tags,
- invalid type,
- empty individual tags,
- tag-length boundaries.

##### Creator and Assignee Validation

- valid email,
- optional `None`,
- invalid email,
- empty values.

**Result:** 90 unit tests passing.

---

### 4. Integration Tests Cover JSON Storage and CLI

**Status:** ✅ COMPLETE

Integration tests verify collaboration between multiple application components, including the CLI, service layer, validation layer, and JSON persistence.

| File | Coverage |
| --- | --- |
| `test_db_client.py` | JSON read/write/update/delete and error handling |
| `test_create_ticket_cli.py` | Create command, tag parsing, validation, and special characters |
| `test_list_ticket_cli.py` | Filtering by status, priority, tags, and filter combinations |
| `test_show_ticket_cli.py` | Ticket detail display and nonexistent ticket handling |
| `test_update_ticket_cli.py` | Updating fields, status changes, and field preservation |
| `test_delete_ticket_cli.py` | Delete operations and data integrity |
| `test_ticket_service.py` | Service CRUD operations and validation integration |

**Total:** 144 integration tests passing.

---

### 5. Error Cases Tested

**Status:** ✅ COMPLETE

The project includes tests for normal flows as well as failure and edge cases.

#### Invalid Input

Examples include:

- invalid creator or assignee email,
- title too short,
- title too long,
- invalid priority,
- invalid status,
- description exceeding the maximum length,
- invalid tag values.

Example test cases:

```text
test_create_with_invalid_creator_email
test_validate_title_too_short
test_validate_title_too_long
test_validate_priority_invalid
test_validate_status_invalid
test_create_with_invalid_description_too_long
```

#### Ticket Not Found

Nonexistent ticket IDs are tested for:

- `show`,
- `update`,
- `delete`.

The CLI returns an appropriate error rather than crashing.

#### JSON File Issues

Tests also cover:

- corrupted JSON,
- missing JSON files,
- automatic file creation,
- preservation of stored data.

Example tests:

```text
test_handles_corrupted_json_gracefully
test_file_is_created_if_not_exists
```

---

### 6. Setup Instructions Documented

**Status:** ✅ COMPLETE

The project includes a `README.md` containing:

- features overview,
- project structure,
- installation instructions,
- setup instructions,
- usage examples,
- testing commands,
- architecture explanation.

---

### 7. Understanding of TDD, Test Types, and AI Usage

**Status:** ✅ COMPLETE

The project includes a `REFLECTION.md` containing discussion of:

- why TDD was used,
- benefits experienced from TDD,
- why both unit and integration tests were needed,
- why validation was separated into different responsibilities,
- how AI was used during development,
- guardrails applied to AI-generated code,
- concrete cases where tests caught problems in AI-generated implementations.

---

## Project Statistics

| Metric | Count |
| --- | ---: |
| **Total Tests** | **234** |
| Unit Tests | 90 |
| Integration Tests | 144 |
| Test Pass Rate | 100% |
| Source Files | 12 |
| Test Files | 10 |
| Approximate Lines of Code | ~1,300 |

---

## Architecture Overview

```text
┌─────────────────────────────────────┐
│          CLI Layer                  │
│          cli.py                     │
│                                     │
│ handle_create()                     │
│ handle_list()                       │
│ handle_show()                       │
│ handle_update()                     │
│ handle_delete()                     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│          Service Layer              │
│       ticketService.py              │
│                                     │
│ create / read / update / delete     │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────────┐   ┌───────────────────┐
│ Validation Layer  │   │    Data Layer     │
│                   │   │                   │
│ TicketValidator   │   │    DBClient       │
│ EmailValidator    │   │                   │
│                   │   │ read()            │
│                   │   │ write()           │
│                   │   │ update()          │
│                   │   │ delete()          │
└───────────────────┘   └─────────┬─────────┘
                                  │
                                  ▼
                        ┌────────────────────┐
                        │   tickets.json     │
                        └────────────────────┘
```

### Responsibility of Each Layer

**CLI Layer**

Responsible for:

- parsing command-line arguments,
- converting CLI-specific inputs,
- invoking application services,
- displaying results and errors.

**Service Layer**

Responsible for:

- ticket-specific business operations,
- coordinating validation,
- interacting with the persistence layer.

**Validation Layer**

Responsible for:

- ticket-field business rules,
- reusable email validation.

**Data Layer**

Responsible for:

- reading JSON data,
- writing JSON data,
- updating stored data,
- deleting stored data,
- managing the storage file.

---

## Features Beyond the Original Requirements

### 1. Delete Command

The application supports full CRUD behavior by adding:

```bash
tickets delete <ticket-id>
```

### 2. Extended Ticket Model

Additional ticket fields were introduced:

- `creator`,
- `assignee`,
- `estimated_time`.

### 3. Enhanced Validation

The project includes stricter validation for:

- email addresses,
- title boundaries,
- description length,
- tags,
- status values,
- priority values.

### 4. Improved CLI Help

The CLI includes clearer command descriptions and usage examples.

---

## Key Design Decisions

### Separate Validation Responsibilities

Validation is applied at appropriate boundaries.

#### CLI Argument Parsing

`argparse` catches command-line-specific errors early.

For example, fields with a fixed set of CLI options can use `choices`.

#### TicketValidator

`TicketValidator` enforces ticket-domain rules independently of the CLI.

This is important because `TicketService` may also be used directly by tests or future application interfaces.

#### EmailValidator

Email validation was separated into its own validator because both `creator` and `assignee` use the same rule.

This avoids duplication and makes email validation independently testable.

### Why Multiple Validation Layers?

The layers do not exist simply to repeat the same checks.

Instead, they protect different boundaries:

```text
CLI input
   ↓
argparse validation
   ↓
TicketService
   ↓
TicketValidator / EmailValidator
   ↓
DBClient
```

This means business rules remain enforced even if `TicketService` is called without using the CLI.

---

## Test Structure Strategy

### Unit Tests

The **90 unit tests** focus mainly on small validation rules in isolation.

Benefits include:

- fast execution,
- precise failure messages,
- easy identification of edge cases,
- reduced dependency on filesystem or CLI behavior.

### Integration Tests

The **127 integration tests** validate collaboration between application components.

They cover:

```text
CLI
 ↓
TicketService
 ↓
Validators
 ↓
DBClient
 ↓
Temporary JSON storage
```

Integration tests help detect problems that unit tests cannot, such as:

- incorrect argument routing,
- incorrect tag parsing,
- service and persistence integration errors,
- incorrect data preservation during updates,
- output and exit-code problems.

### Why Both?

Unit and integration tests target different failure modes.

Unit tests answer:

> Does this individual rule or component behave correctly?

Integration tests answer:

> Do these components work correctly together from the application's external interface?

---

## Controlled AI Usage

AI was used as a development assistant, but AI-generated output was not treated as automatically correct.

### AI Tools Used

- **ChatGPT** for feature exploration and design discussion.
- **Claude Code** for test scaffolding and implementation assistance.

### AI-Assisted Tasks

AI was used for:

- identifying possible ticket-manager features,
- suggesting edge cases,
- generating initial test scaffolding,
- generating implementation suggestions,
- reviewing possible validation rules,
- assisting with repetitive CLI handlers.

### Guardrails Applied

The following guardrails were used:

- tests were run immediately after AI-generated changes,
- implementation was reviewed before being accepted,
- tests remained the source of truth,
- AI-generated code was modified when it did not satisfy the expected behavior,
- refactoring was followed by regression-test execution.

### Examples of Tests Catching AI Mistakes

#### Email Regex Too Permissive

An initial email validation implementation accepted invalid edge cases.

Tests involving:

- consecutive dots,
- invalid boundary dots,
- malformed domains

failed.

The validator was then corrected until the tests passed.

#### Missing Validation in TicketService

An implementation initially allowed the service layer to persist data without invoking the required validator.

The service integration tests failed.

Validation was then added to the service flow:

```text
TicketService
    ↓
TicketValidator
    ↓
DBClient
```

This demonstrated an important controlled-AI principle:

> AI can propose implementation code, but automated tests determine whether the implementation actually satisfies the defined behavior.

---

## Configuration

The application uses local JSON storage by default:

```text
data/tickets.json
```

Core constraints are defined in the application validators, including:

- allowed ticket statuses,
- allowed ticket priorities,
- title length rules,
- description rules,
- tag constraints,
- optional extended-field validation.

`DBClient` accepts a file path so tests can use isolated temporary JSON files rather than depending on the production storage file.

This improves:

- test isolation,
- repeatability,
- maintainability,
- separation between production and test data.

---

## How to Run

### Create a Virtual Environment

```bash
python -m venv .venv
```

### Activate the Environment

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

Verbose mode:

```bash
python -m pytest tests/ -v
```

Summary mode:

```bash
python -m pytest tests/ -q
```

### Run the CLI

Create a ticket:

```bash
python main.py create --title "My task" --priority high
```

List open tickets:

```bash
python main.py list --status open
```

---

## Files Overview

### Core Application

- `main.py` — application entry point
- `ticket_manager/cli.py` — CLI parsing and command handlers
- `ticket_manager/services/ticketService.py` — ticket business logic
- `ticket_manager/models/ticket.py` — Ticket model
- `ticket_manager/validators/email_validator.py` — reusable email validation
- `ticket_manager/validators/ticket_validator.py` — ticket-field validation
- `data/db_client.py` — JSON persistence

### Documentation

- `README.md` — setup and usage guide
- `REFLECTION.md` — TDD process, design decisions, and AI usage
- `week2.md` — Week 2 completion report

### Tests

- `tests/units/test_email_validator.py`
- `tests/units/test_ticket_validator.py`
- `tests/integrations/test_db_client.py`
- `tests/integrations/test_create_ticket_cli.py`
- `tests/integrations/test_list_ticket_cli.py`
- `tests/integrations/test_show_ticket_cli.py`
- `tests/integrations/test_update_ticket_cli.py`
- `tests/integrations/test_delete_ticket_cli.py`
- `tests/integrations/test_ticket_service.py`

**Total:** 234 tests

- 90 unit tests
- 144 integration tests

---

## Final Status

**Status:** ✅ COMPLETE AND TESTED

The Ticket Manager CLI satisfies the Week 2 objectives by demonstrating:

- repeated Red-Green-Refactor TDD cycles,
- working CLI functionality,
- JSON persistence,
- isolated business-rule tests,
- full-flow integration tests,
- error-case coverage,
- clear architectural separation,
- documented setup and usage,
- controlled and validated AI assistance.