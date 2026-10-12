**# Week 2: TDD Practice - Ticket Manager CLI**

**## Executive Summary**

Successfully completed Week 2 TDD practice by building a fully functional Ticket Manager CLI using Test-Driven Development methodology. The project demonstrates:

\- **\*\*217 passing tests\*\*** (90 unit + 127 integration)

\- Clean layered architecture with separation of concerns

\- Controlled AI assistance with rigorous validation through testing

\- Comprehensive documentation and reflection on design decisions

\---

**## Acceptance Criteria - Completion Status**

\*\*### 1. TDD Workflow Demonstrated

**Status:** COMPLETE

The project was developed through repeated **Red–Green–Refactor** cycles rather than by implementing the full application first and adding tests afterward.

The development sequence was:

1. Define the expected external behavior.
2. Write a failing test for that behavior.
3. Implement the minimum code required to make the test pass.
4. Refactor the code while keeping the tests green.
5. Start a new cycle for the next behavior.

### Initial CLI Skeleton

Before implementing business logic, I first created a base CLI with `argparse`.

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

This produced the following separation:

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

1. reading parsed arguments,
2. converting CLI-specific input such as comma-separated tags,
3. creating the ticket input,
4. calling `TicketService`,
5. displaying the result.

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

| Component           | Red                         | Green                                | Refactor                                                  |
| ------------------- | --------------------------- | ------------------------------------ | --------------------------------------------------------- |
| **DBClient**        | `test_db_client.py`         | Implement read/write/update/delete   | Remove hardcoding, allow configurable file path           |
| **TicketValidator** | `test_validators.py`        | Implement validation rules           | Separate validation responsibilities and improve messages |
| **TicketService**   | `test_ticket_service.py`    | Implement ticket-specific operations | Reuse `DBClient`, centralize validation                   |
| **CLI Create**      | `test_create_ticket_cli.py` | Implement `handle_create()`          | Improve command structure and help text                   |
| **CLI List**        | `test_list_ticket_cli.py`   | Implement `handle_list()`            | Improve output formatting                                 |
| **CLI Show**        | `test_show_ticket_cli.py`   | Implement `handle_show()`            | Improve field display                                     |
| **CLI Update**      | `test_update_ticket_cli.py` | Implement `handle_update()`          | Preserve unchanged fields and improve handler structure   |
| **CLI Delete**      | `test_delete_ticket_cli.py` | Implement `handle_delete()`          | Clean up command flow                                     |

**Key point:** tests were used to define expected behavior before or during implementation, and regression tests were rerun after refactoring.

**Evidence:** See [REFLECTION.md](./REFLECTION.md) for the detailed design and AI usage discussion.

-----------|-----|-------|----------|

\| **\*\*DBClient\*\*** | test_db_client.py | Implement read/write/update/delete | Remove hardcoding, use config.py |

\| **\*\*TicketValidator\*\*** | test_validators.py (90 tests) | email_validator.py, ticket_validator.py | Separate methods, improve messages |

\| **\*\*TicketService\*\*** | test_ticket_service.py | Implement service logic | Integrate validators, add helper methods |

\| **\*\*CLI Create\*\*** | test_create_ticket_cli.py | handle_create() in cli.py | Add help text, support new fields |

\| **\*\*CLI List\*\*** | test_list_ticket_cli.py | handle_list() with filters | Improve output formatting |

\| **\*\*CLI Show\*\*** | test_show_ticket_cli.py | handle_show() | Display all fields |

\| **\*\*CLI Update\*\*** | test_update_ticket_cli.py | handle_update() | Support new fields |

\| **\*\*CLI Delete\*\*** | test_delete_ticket_cli.py | handle_delete() (bonus) | Clean up after deletion |

**\*\*Evidence:\*\*** See [REFLECTION.md]\(./REFLECTION.md) for detailed cycle breakdown with code examples.

\---

**### 2. CLI Tool Basic Functions Working**

**\*\*Status:\*\*** COMPLETE + BONUS

All required commands implemented and tested:

\`\`\`bash

\# Create ticket with all fields including new ones

tickets create --title "Fix login bug" \\

  --description "Users get 500 error" \\

  --priority high \\

  --tags "bug,backend" \\

  --creator "dev\@example.com" \\

  --assignee "qa\@example.com" \\

  --estimated_time 5.5

\# List with filters

tickets list                          # All tickets

tickets list --status open            # Open tickets

tickets list --priority high          # High priority

tickets list --tag bug                # With 'bug' tag

\# Show ticket details

tickets show 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

\# Update ticket status

tickets update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status closed

\# Delete ticket (bonus)

tickets delete 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9

\`\`\`

**\*\*Test Coverage:\*\*** 15 tests for create command, 17 for list, 11 for show, 14 for update, 18 for delete.

\---

**### 3. Unit Tests Cover Ticket Logic & Validation**

**\*\*Status:\*\*** COMPLETE

### Unit Tests Cover Ticket Logic & Validation

**Status:** COMPLETE

**Files:**

- `tests/units/test_email_validator.py`
- `tests/units/test_ticket_validator.py`

**Total:** 90 unit tests

**Coverage Areas:**

- Email validation
  - valid and invalid formats
  - missing `@`
  - multiple `@`
  - empty/whitespace input
  - consecutive dots
  - domain boundary rules
  - local-part length
  - maximum email length
- Ticket title validation
  - valid title
  - minimum length
  - too short
  - too long
  - empty/whitespace
  - invalid type
- Description validation
  - valid description
  - empty description
  - too long
  - invalid type
- Priority validation
  - `low`
  - `medium`
  - `high`
  - invalid values
- Status validation
  - `open`
  - `in-progress`
  - `closed`
  - invalid values
- Tags validation
  - empty tags
  - single/multiple tags
  - maximum number of tags
  - invalid type
  - empty tags
  - tag length boundaries
- Creator and assignee validation
  - valid email
  - optional `None`
  - invalid email
  - empty values

**Result:** 90 passed.

\---

**### ✅ 4. Integration Tests Cover JSON Storage & CLI**

**\*\*Status:\*\*** COMPLETE

**\*\*Files:\*\*** 6 integration test files, 127 total tests

\| File | Tests | Coverage |

\|------|-------|----------|

\| test_db_client.py | 27 | Read/write/update/delete JSON, error handling |

\| test_create_ticket_cli.py | 21 | CLI create command, tag parsing, special characters |

\| test_list_ticket_cli.py | 17 | Filtering by status/priority/tag, combinations |

\| test_show_ticket_cli.py | 12 | Display ticket details, nonexistent tickets |

\| test_update_ticket_cli.py | 14 | Status transitions, field preservation |

\| test_delete_ticket_cli.py | 18 | Delete operations, data integrity |

\| test_ticket_service.py | 41 | Service CRUD, validation integration |

**\*\*Test Results:\*\*** All 127 integration tests passing ✅

\---

**### ✅ 5. Error Cases Tested**

**\*\*Status:\*\*** COMPLETE

**\*\*Invalid Input:\*\***

\- Invalid email format (test_create_with_invalid_creator_email)

\- Title too short/long (test_validate_title_too_short, test_validate_title_too_long)

\- Invalid priority/status (test_validate_priority_invalid, test_validate_status_invalid)

\- Description too long (test_create_with_invalid_description_too_long)

**\*\*Ticket Not Found:\*\***

\- Nonexistent UUID for show/update/delete operations

\- Appropriate error messages returned

**\*\*JSON File Issues:\*\***

\- Corrupted JSON handling (test_handles_corrupted_json_gracefully)

\- Missing file auto-creation (test_file_is_created_if_not_exists)

\---

**### ✅ 6. Setup Instructions Documented**

**\*\*Status:\*\*** COMPLETE

**\*\*File:\*\*** \`README.md\` with comprehensive sections:

\- Features overview

\- Project structure diagram

\- Installation and setup instructions

\- Usage examples for all commands

\- Testing instructions

\- Architecture explanation

\---

**### ✅ 7. Can Answer Questions About TDD, Test Types, and AI Usage**

**\*\*Status:\*\*** COMPLETE

**\*\*File:\*\*** \`REFLECTION.md\` with detailed answers to:

\- Why TDD was used and benefits experienced

\- Why both unit and integration tests

\- Why three levels of validation

\- How AI was used responsibly with guardrails

\- Concrete examples of how tests caught AI mistakes

\---

**## Project Statistics**

\| Metric | Count |

\|--------|-------|

\| **\*\*Total Tests\*\*** | 223 |

\| Unit Tests | 90 |

\| Integration Tests | 127 |

\| Test Pass Rate | 100% ✅ |

\| Source Files | 12 |

\| Test Files | 7 |

\| Lines of Code | \~1,200 |

\---

**## Architecture Overview**

\`\`\`

┌─────────────────────────────────────┐

│       CLI Layer (cli.py)            │

│  handle_create, handle_list, ...    │

└────────────────┬────────────────────┘

                 ↓

┌─────────────────────────────────────┐

│   Service Layer (ticketService.py)  │

│  create, read, update, delete ops   │

└────────────────┬────────────────────┘

                 ↓

┌──────────────────────────┬──────────────────────────┐

│  Validation Layer        │   Data Layer             │

│  (validators.py)         │   (db_client.py)         │

│  - EmailValidator        │   - read()               │

│  - TicketValidator       │   - write()              │

│                          │   - update()             │

│                          │   - delete()             │

└──────────────────────────┴──────────────────────────┘

                 ↓

┌─────────────────────────────────────┐

│      JSON File (tickets.json)        │

└─────────────────────────────────────┘

\`\`\`

\---

**## New Features Beyond Requirements**

1\. **\*\*Delete Command\*\*** — Full CRUD support

2\. **\*\*Extended Ticket Model\*\*** — creator, assignee, estimated_time fields

3\. **\*\*Enhanced Validation\*\*** — Strict email validation with edge case handling

4\. **\*\*Comprehensive Help\*\*** — Usage examples in CLI epilog

\---

**## Key Design Decisions**

**### Layered Validation (Three Levels)**

1\. **\*\*CLI Argument Parsing\*\*** — Catch obvious errors immediately (argparse choices)

2\. **\*\*Service Layer Validation\*\*** — Enforce business rules (TicketValidator)

3\. **\*\*Email Validator\*\*** — Reusable, strict email validation

**\*\*Why?\*\*** Defense in depth. Each layer catches different classes of errors.

**### Test Structure Strategy**

\- **\*\*Unit Tests (90):\*\*** Validators tested in isolation, fast feedback, catch logic errors

\- **\*\*Integration Tests (127):\*\*** Full command flow tested, catch architecture errors

**\*\*Why both?\*\*** Different failure modes require different test types.

\---

**## Controlled AI Usage**

**\*\*What I Used AI For:\*\***

\- Feature research (ChatGPT: "What should a ticket manager CLI have?")

\- Test generation (Claude Code: generate test files)

\- Implementation (Claude Code: generate validators, service, CLI handlers)

**\*\*Guardrails Applied:\*\***

\- Ran tests immediately after AI-generated code

\- Reviewed code for error handling and structure adherence

\- Did NOT accept all AI code blindly

**\*\*How Tests Caught AI Mistakes:\*\***

1\. **\*\*Email regex too permissive\*\*** — Tests for consecutive dots, boundary dots failed → refined validator

2\. **\*\*Missing validator call\*\*** — Service layer test failed → added validation integration

\---

\*\*

### Configuration

The application uses local JSON storage by default.

```text
data/tickets.json
```

Core constraints are defined in the application code and validators, including:

- allowed ticket statuses,
- allowed priorities,
- title length rules,
- tag constraints,
- optional extended-field validation.

`DBClient` accepts a file path so tests can use isolated JSON files instead of relying on the production storage file.

---

## How to Run\*\*

\`\`\`bash

\# Setup

python -m venv .venv

source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt

\# Run tests

python -m pytest tests/ -v   # All tests

python -m pytest tests/ -q   # Summary

\# Run CLI

python main.py create --title "My task" --priority high

python main.py list --status open

\`\`\`

\---

**## Files Overview**

**### Core Application**

\- \`main.py\` — Entry point

\- \`ticket_manager/cli.py\` — Command handlers

\- \`ticket_manager/services/ticketService.py\` — Business logic

\- \`ticket_manager/models/ticket.py\` — Ticket model

\- \`ticket_manager/validators/\` — Email and field validators

\- \`data/db_client.py\` — JSON persistence

**### Documentation**

\- \`README.md\` — User guide

\- \`REFLECTION.md\` — TDD process and design decisions

\- \`week2.md\` — This completion report

**### Tests (217 total)**

\- \`tests/units/test\_\*.py\` — 90 unit tests

\- \`tests/integrations/test\_\*.py\` — 127 integration tests

\---

**\*\*Status:\*\*** ✅ COMPLETE AND TESTED
