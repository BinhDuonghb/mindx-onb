# Week 2 TDD Reflection: Ticket Manager CLI

## Overview
This document reflects on the test-driven development (TDD) process used to build the Ticket Manager CLI, including decisions about test design and controlled AI usage during development.

---

## Part 1: TDD Workflow & Red-Green-Refactor Cycles

### Initial Planning Phase
Before writing any code, I researched expected behavior by asking ChatGPT: "What features should a CLI ticket manager have?" This gave me a clear scope:
- **Required features:** create, list, show, update
- **Rationale:** These cover basic CRUD operations for a ticket system
- **Design decision:** Keep scope focused; delete was implemented as a bonus feature

### Base CLI Structure (Skeleton Phase)
Built a minimal CLI shell that accepts commands but doesn't execute them:
```
tickets create ...  # parses but doesn't create
tickets list ...    # parses but doesn't list
tickets show ...    # parses but doesn't show
```

**Why this step?** Established the CLI interface first so later implementations could focus on business logic, not argument parsing.

---

## Part 2: TDD Cycles Applied

### Cycle 1: Database Layer (DBClient)

**Phase 1 - RED (Test First):**
- Created `tests/integrations/test_db_client.py` with failing tests
- Tests defined expected behavior:
  - `read()` — load all tickets from JSON
  - `write(ticket)` — append ticket to JSON
  - `update(id, data)` — modify existing ticket
  - `delete(id)` — remove ticket
  - Error handling for nonexistent tickets and corrupted files

**Why test first?** Forced me to think about the DBClient interface before implementation. Tests became the contract.

**Phase 2 - GREEN (Minimal Implementation):**
- Implemented `ticket_manager/db_client.py` to pass all tests
- Simple approach: read entire JSON, modify in memory, write back
- Focused on making tests pass, not optimization

**Phase 3 - REFACTOR (Improve Design):**
- Removed hardcoded file paths → moved to `config.py`
- Separated concerns: `_write_all()` helper method
- Added error handling for edge cases (missing file auto-creation, JSON corruption)

**Test Type: Integration**
- Why? Tests verify file I/O and data persistence
- Not unit tests because the behavior depends on file system state
- Fast enough for the scope (simple JSON operations)

---

### Cycle 2: Service Layer & Validation

**Phase 1 - RED (Validators):**
- Created `tests/units/test_validators.py` with 90 unit tests for:
  - **Email validation:** format, consecutive dots, dots at label boundaries, hyphens in domain
  - **Title validation:** 3-255 character constraint
  - **Description validation:** max 5000 characters
  - **Priority/Status validation:** only allow specific values
  - **Tags validation:** 2-50 chars each, max 10 tags

**Why write these tests first?** Email validation is complex (regex + business rules). Tests forced me to think through edge cases:
- Invalid: `user..@example.com` (consecutive dots)
- Invalid: `.user@example.com` (starts with dot)
- Invalid: `user@-example.com` (domain label starts with hyphen)

**Phase 2 - GREEN (Implementation):**
- Implemented `ticket_manager/validators/email_validator.py` with strict validation
- Implemented `ticket_manager/validators/ticket_validator.py` with field-specific rules
- Initially regex was too permissive → tests caught this → refined with additional checks

**Phase 3 - REFACTOR:**
- Moved validation logic to separate methods for reuse
- Improved error messages to be specific (not just "invalid email")

**Then - RED (Service Layer):**
- Created `tests/integrations/test_ticket_service.py`
- Tests defined TicketService interface:
  - `create(ticket)` — persist and return with UUID
  - `get_all()` — retrieve all tickets
  - `get_by_id(id)` — retrieve specific ticket
  - `update(id, **kwargs)` — modify ticket fields
  - `delete(id)` — remove ticket

**Phase 4 - GREEN (Implementation):**
- Implemented `ticket_manager/services/ticketService.py`
- Reused DBClient for persistence
- Integrated validators into create/update methods
- **Key decision:** Validate both at service level AND through CLI → defense in depth

**Test Types: Mixed Strategy**
- **Unit tests** (validators): Test logic in isolation, fast feedback, catch edge cases
- **Integration tests** (service + DB): Verify service uses DBClient correctly, validators are called

**Why both?** 
- Unit tests catch logic errors early (email regex bugs)
- Integration tests catch interface errors (service doesn't call validator at right time)
- Speeds up debugging: failing unit test → logic issue; failing integration test → architecture issue

---

### Cycle 3: CLI Command Implementation (Create)

**Phase 1 - RED (CLI Test):**
- Created `tests/integrations/test_create_ticket_cli.py`
- Tests ran CLI subprocess and verified:
  - Success case: ticket created and stored
  - Error cases: invalid priority, missing title
  - Data integrity: tags parsed correctly, description preserved

**Phase 2 - GREEN (Implementation):**
- Implemented `handle_create()` in `ticket_manager/cli.py`
- Parsed arguments, created Ticket object, called TicketService

**Phase 3 - REFACTOR:**
- Added helpful error messages and usage examples in CLI epilog
- Added support for new fields: creator, assignee, estimated_time (with email validation)

**Test Type: Integration**
- Why? Must test the full path: CLI parsing → Service validation → DB persistence
- Subprocess testing ensures real command-line behavior (not just function calls)

---

### Cycles 4-7: Other Commands (Update, List, Show, Delete)

Repeated the same pattern for each command:
1. **RED:** Write failing integration test for the command
2. **GREEN:** Implement the handler in CLI
3. **REFACTOR:** Improve code structure, add helpful output

**AI Usage Efficiency:** After establishing the pattern for `create`, I asked Claude Code to:
- Generate similar test structures for other commands
- Implement handlers following the same design
- This maintained consistency while speeding up development

---

## Part 3: Test Design Decisions & Rationale

### Why Layered Validation?

The system validates tickets at **three levels**:

1. **CLI Argument Parsing** (argparse)
   - Example: `--priority` choices limited to ["low", "medium", "high"]
   - Benefit: Catches obvious errors immediately, prevents invalid strings from reaching service

2. **Service Layer** (TicketValidator)
   - Example: Title must be 3-255 characters
   - Benefit: Enforces business rules regardless of how TicketService is called (CLI or other client)

3. **Email Validator**
   - Example: Regex + edge case checks (no consecutive dots, no dots at boundaries)
   - Benefit: Reusable across creator and assignee fields

**Why not just one level?** 
- CLI validation alone wouldn't work if TicketService is used by another client (API, other CLI)
- Service validation alone would miss CLI mistakes (doesn't prevent passing invalid argparse data)
- This is "defense in depth" — multiple boundaries catch different classes of errors

### Test Structure: Unit vs. Integration

**Unit Tests (90 tests in `test_validators.py`):**
- Test validators in isolation with hardcoded inputs
- Fast (no file I/O, no subprocess calls)
- Easy to debug (failure points to exact validation logic)
- Cover edge cases that integration tests might miss

**Integration Tests (127 tests across 6 files):**
- Test full command flow: CLI → Service → DB → JSON file
- Slower but verify pieces work together
- Catch interface/data-format bugs (e.g., did CLI pass the right argument type to Service?)
- More realistic; closer to actual usage

**Trade-off:** More tests to maintain, but catches more bugs earlier.

---

## Part 4: AI-Assisted Development & Guardrails

### What I Used AI For

1. **Feature Research**
   - Asked ChatGPT: "What should a ticket manager CLI include?"
   - Validated my feature list against conventions

2. **Test Generation**
   - Asked Claude Code to generate unit tests for validators
   - **Guardrail applied:** I reviewed each test to verify:
     - Tests were realistic (not just happy-path)
     - Edge cases were actually edge cases (not overlapping tests)
     - Error messages matched the implementation

3. **Integration Test Generation**
   - Asked Claude Code to generate test files for each CLI command
   - **Guardrail applied:** Ran tests immediately to catch AI hallucinations
     - Example: AI generated tests before TicketService was fully updated → caught mismatches

4. **Implementation Assistance**
   - Asked Claude Code to implement service handlers, validators, CLI commands
   - **Guardrail applied:** Did NOT accept all generated code blindly
     - Reviewed code for:
       - Adherence to project structure (no unexpected dependencies)
       - Error handling (not silently failing)
       - Test compatibility (generated code must pass existing tests)

### How Tests Caught AI Mistakes

**Email Validator Bug Discovery:**
1. I asked Claude Code to generate an email validator using regex
2. Tests initially failed on edge cases:
   - `user..@example.com` (consecutive dots) — regex didn't catch
   - `user@-example.com` (domain label starts with hyphen) — regex didn't catch
3. **I revised the validator** to add explicit edge-case checks
4. Tests passed after refinement

**Key insight:** AI-generated regex was 90% correct but missed subtle cases. Tests forced the issue to surface immediately, rather than discovering it in production.

**Validation Integration Bug:**
1. AI generated TicketService.create() without calling validators
2. Test `test_create_with_invalid_title_too_short` failed
3. **I added validator calls** to the service layer
4. Tests passed

**Key insight:** AI generated working code structure but missed business requirements. Tests served as a spec that AI couldn't work around.

### Guardrails Applied Throughout

| When | Guardrail | Why |
|------|-----------|-----|
| AI generates test | Run immediately | Catch hallucinated method names, wrong assertions |
| AI generates implementation | Read code before committing | Verify error handling, no shortcuts |
| AI generates CLI handler | Check against passing test | Ensure behavior matches test expectations |
| After refactor | Run full test suite | Verify AI didn't introduce regressions |

---

## Part 5: What This Taught About TDD

### Benefits Realized

1. **Tests Clarified Intent**
   - Writing tests first forced me to think about the interface before implementation
   - Example: Deciding TicketService needed both `get_by_status()` and `get_by_priority()` emerged from test requirements

2. **Faster Debugging**
   - When tests failed, the failure was pinpoint (specific assertion)
   - Much easier than code-first debugging where bugs are discovered through manual testing

3. **Confidence in Refactoring**
   - Could refactor DBClient structure (hardcoding → config) without fear
   - Tests verified no behavior changed

4. **AI Code Validation**
   - Tests forced AI implementations to be correct
   - Couldn't pass tests with buggy code, unlike manual code review

### Challenges Encountered

1. **Test Writing Takes Time**
   - Spent significant time upfront writing test_db_client.py before DBClient existed
   - Required discipline to not "just code it first"

2. **Test Maintenance**
   - When I added new fields (creator, assignee, estimated_time), had to update both:
     - Test assertions (what fields to check)
     - Test data (include new fields)
   - More tests = more to maintain

3. **Balancing Unit vs. Integration**
   - Had to decide: Is this a unit test or integration test?
   - Made mistakes initially (e.g., trying to test DBClient without file I/O)
   - Refactored to proper integration tests

---

## Part 6: Design Patterns & Architecture Decisions

### Layered Architecture

```
CLI Layer (handle_create, handle_list, ...)
    ↓
Service Layer (TicketService)
    ↓
Validators (TicketValidator, EmailValidator)
    ↓
Data Layer (DBClient)
    ↓
JSON File (tickets.json)
```

**Why layers?**
- Each layer has single responsibility
- Validators are reusable (used by Service, testable independently)
- Service can be called from different CLIs without duplicating logic
- Easier to test each layer independently

### Validation at Service Boundary

TicketService calls validators before persisting:
```python
def create(self, ticket: Ticket) -> Ticket:
    validator = TicketValidator()
    validator.validate_title(ticket.title)
    validator.validate_creator(ticket.creator)
    # ... then persist
```

**Why here?** Validation happens before mutation of state. If validation fails, nothing is persisted.

---

## Summary

### TDD Impact
- 223 passing tests provide high confidence in the system
- Red-Green-Refactor cycles led to clean, layered architecture
- Tests served as specifications that even AI code had to satisfy

### AI Usage
- AI accelerated implementation but didn't replace testing
- Tests caught AI mistakes (regex bugs, missing validation calls)
- Guardrails (immediate test runs, code review) ensured quality

### Key Takeaway
TDD + testing AI-generated code = faster development with fewer bugs. The tests were not overhead; they were the foundation that made AI assistance safe and effective.

---

## How to Answer Week 2 Assessment Questions

**Q: Why use TDD?**
A: TDD clarified the interface before implementation and caught bugs early (both in my code and AI-generated code). Tests served as the specification.

**Q: Why both unit and integration tests?**
A: Unit tests catch logic errors fast (email validation edge cases). Integration tests catch architecture errors (validators not being called). Together they provide comprehensive coverage.

**Q: Why three levels of validation?**
A: Defense in depth. CLI validates basic format; Service validates business rules; each can be tested independently. If TicketService is used by other clients later, validation still works.

**Q: How did you use AI responsibly?**
A: Tests forced AI code to be correct. Every AI-generated test and implementation had to pass tests before acceptance. Tests caught the email regex bug and the missing validator call that AI made.
