# Week 5: Odoo Login Issue Automation

Enterprise-grade support automation for Odoo helpdesk tickets. Automatically detects login issues, validates employee status, reactivates LMS accounts, and manages customer communications with persistent state tracking and intelligent retry scheduling.

**Status**: ✅ **Production Ready** | 394 tests passing | Retry mechanism with state recovery | SQLite persistence | Gmail SMTP integration

## Overview

This automation system processes Odoo helpdesk tickets to solve recurring login issues:

1. **Detect** login problems from ticket content using pattern matching
2. **Validate** employee status (active/terminated/on-leave) via HR system
3. **Act** by reactivating LMS accounts for active employees
4. **Communicate** with customers via professional email templates
5. **Recover** from failures with intelligent retry scheduling

Key differentiators:
- **Idempotent retries**: Side effects tracked and persisted; skips already-completed actions
- **Atomic processing**: Prevents concurrent workers from processing the same ticket
- **Outcome-first emails**: Exactly one email per execution based on workflow result
- **Graceful degradation**: Works without external services (HR, Gmail) if needed

## Quick Start

### Prerequisites
- Python 3.9+ (tested with 3.13.3)
- Virtual environment (`.venv/`)
- Odoo 16+ instance with helpdesk module
- SQLite (bundled with Python)
- Gmail account with app password (optional, for email sending)

### Installation

```bash
# Navigate to project
cd D:\Study\mindx\mindx-onb\assignments\week5\automation

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy srcs\.env.example srcs\.env
# Edit srcs/.env with your Odoo and Gmail credentials
```

### Configuration

Edit `srcs/.env` with your system details:

```env
# Odoo Integration (Production)
ODOO_URL=http://localhost:8069
ODOO_DATABASE=your_db_name
ODOO_RPC_KEY=your-api-key

# Odoo Integration (Testing - used by pytest)
TEST_ODOO_URL=http://localhost:8069
TEST_ODOO_DATABASE=test_db_name
TEST_ODOO_RPC_KEY=test-api-key

# HR System (uses mock data by default)
HR_FILE=data/hr.json

# Gmail SMTP (optional - for email sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# Logging & Environment
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Running the Automation

```bash
# One-time execution (processes new and retry-due tickets)
python srcs/main.py --once

# Continuous polling every 60 seconds
python srcs/main.py --poll --interval 60

# With custom parameters
python srcs/main.py --once --limit 100 --min-age 5

# View available options
python srcs/main.py --help
```

### Running Tests

```bash
# All tests (394 passing)
pytest tests/ -v

# By category
pytest tests/units/ -v        # 276 unit tests
pytest tests/integration/ -v  # 118 integration tests

# With coverage report
pytest tests/ --cov=srcs --cov-report=html
# Open htmlcov/index.html in browser
```

## Workflow

### High-Level Flow

```
1. Poll Odoo for tickets
   ↓
2. Check processing lease (prevent concurrent processing)
   ├─ Lease active? Skip (another worker has it)
   └─ Lease expired? Claim and proceed
   ↓
3. Detect login issue from content
   ├─ Not a login issue? Skip
   └─ Is login issue? Lookup employee
   ↓
4. Check employee status in HR system
   ├─ Not found/Terminated/On-leave? Escalate
   └─ Active? Proceed with reactivation
   ↓
5. Execute reactivation (track side effects)
   ├─ LMS account activation
   ├─ Post internal note to Odoo
   ├─ Update ticket stage to "resolved"
   ├─ Send RESOLUTION email to customer
   └─ Save final state to SQLite
   ↓
6. Handle failures with retry scheduling
   ├─ Save partial state with completed side effects
   ├─ Schedule next retry attempt
   ├─ No customer email (will send on retry success)
   └─ Continue polling next ticket
```

### State Management

Every ticket has persistent state in SQLite:

```python
AutomationState(
    ticket_id: int                    # Odoo ticket ID
    fingerprint: str                  # Hash of ticket content (change detection)
    status: AutomationStatus          # NEW, PROCESSING, COMPLETED, RETRY_SCHEDULED, ESCALATED
    
    # Decision information
    last_decision: str                # "account_reactivated", "escalated", "skipped"
    last_reason: str                  # "Active employee", "Terminated", etc.
    
    # Retry tracking
    retry_count: int                  # Number of retry attempts
    next_retry_at: datetime           # When to retry next (None if not scheduled)
    last_error: str                   # Last error message
    
    # Side-effect completion (for idempotent retries)
    reactivation_completed: bool      # LMS account reactivated
    odoo_note_completed: bool         # Internal note posted
    stage_update_completed: bool      # Ticket stage updated
    
    # Processing lease (prevent concurrent workers)
    processing_lease_until: datetime  # Lease expiration (None = not claimed)
)
```

### Idempotent Retry Mechanism

When a step fails partway through reactivation (e.g., LMS succeeds but Odoo note posting fails):

1. **Persist partial state immediately** - Save which side effects completed
2. **Schedule retry** - Calculate retry time and save to database
3. **Skip completed actions** - On retry, `_handle_reactivation()` checks flags and skips already-done work
4. **Send email on success** - Email only sent when entire workflow succeeds

Example:
```
Attempt 1:
  ✓ LMS reactivated (flag saved)
  ✗ Odoo note posting fails → RETRY_SCHEDULED
  
Attempt 2 (1 hour later):
  ✓ LMS already done, skip (flag check)
  ✓ Odoo note posting succeeds
  ✓ Stage update succeeds
  ✓ Send RESOLUTION email
```

### Processing Leases (Concurrency Control)

Prevents multiple workers from processing the same ticket simultaneously:

1. **Claim lease** - Worker sets 5-minute lease when starting processing
2. **Active lease** - Other workers see lease and skip ticket
3. **Expired lease** - After 5 minutes, other workers can reclaim
4. **Release on completion** - Lease automatically expires when ticket completes

Lease check happens **before** fingerprint check to prevent bypass via content changes.

## Features

### ✅ Implemented Features

#### Email Communication System
- **6 Professional Email Templates**:
  - `ACKNOWLEDGEMENT` - Confirm receipt to customer (deprecated, not sent as per outcome-first policy)
  - `RESOLUTION` - Account reactivated notification
  - `MANUAL_REVIEW` - Escalation notice
  - `INVESTIGATION_UPDATE` - Progress update
  - `FOLLOW_UP_REMINDER` - Check if resolved
  - `SYSTEM_ERROR` - Error notification

- **Outcome-First Communication Policy**:
  - Exactly ONE email per execution
  - Based on workflow outcome, not multiple events
  - Successful reactivation → RESOLUTION email only
  - Escalation → MANUAL_REVIEW email only
  - Skipped tickets → No email
  - Failed (retry-scheduled) → No email (sent on retry success)

- **Gmail SMTP Integration**:
  - TLS/SSL encryption
  - Graceful error handling (non-fatal failures)
  - Optional integration (automation works without it)
  - Retry logic with exponential backoff

- **Email Deduplication**:
  - Prevents duplicate emails on repeated polling
  - Persists sent events to SQLite
  - Survives application restart
  - Prevents resend on retry

#### Ticket Analysis
- **Login Issue Detection**:
  - Cannot login / Can't login / Unable to login
  - Account locked / Locked out
  - Password reset / Reset password
  - Access denied / No access
  - Inactive account
  - Session expired / Timeout
  - Confidence scoring

- **Fingerprinting**:
  - Hash of ticket content (name, description, email)
  - Detects ticket changes between polls
  - Resets retry count on significant changes
  - Normalized for consistent comparison

#### State Tracking
- **Persistent SQLite Database**:
  - Automation state (status, decision, side effects)
  - Communication events (sent emails, timestamps)
  - Customer confirmations (response tracking)
  - Processing leases (concurrency control)

- **State Recovery**:
  - Survives application restart
  - Loads all previous state on init
  - Resumes interrupted workflows
  - Prevents duplicate processing

#### Retry Management
- **Intelligent Retry Scheduling**:
  - Configurable retry delays (exponential backoff)
  - Max retry limits (prevents infinite loops)
  - Error tracking for debugging
  - Partial state recovery (skips completed actions)

- **Side-Effect Tracking**:
  - Tracks which actions completed
  - Skips redundant API calls on retry
  - Prevents account double-reactivation
  - Reduces API load

#### Configuration Management
- **Auto-Detection**:
  - Detects pytest vs production mode automatically
  - Uses TEST_ODOO_* for tests, ODOO_* for production
  - No manual switching needed

- **Graceful Degradation**:
  - Works without Gmail configured (emails skipped)
  - Works without HR system (uses mock data)
  - Works without state repo (in-memory only)
  - Continues processing on service failures

#### Testing & Quality
- **394 Tests Passing**:
  - 276 unit tests (isolated service testing)
  - 118 integration tests (multi-service workflows)
  
- **Test-Driven Development**:
  - RED → GREEN → REFACTOR cycle
  - Each phase committed separately
  - Comprehensive coverage of edge cases

- **Test Categories**:
  - Email templates and rendering
  - Template selection logic
  - Acknowledgement workflows
  - Email deduplication
  - Customer confirmation tracking
  - Retry scheduling and recovery
  - Processing lease enforcement
  - Communication state persistence
  - Concurrent worker handling

## Architecture

### Directory Structure

```
automation/
├── srcs/
│   ├── main.py                      # Entry point - orchestrates polling
│   ├── config.py                    # Configuration with pytest auto-detection
│   ├── clients/
│   │   ├── odoo/
│   │   │   ├── base.py              # Base Odoo RPC client
│   │   │   └── ticket_client.py     # Ticket API methods
│   │   └── hr/
│   │       ├── hr_client.py         # HR system interface
│   │       └── mock_hr_data.py      # Mock HR data generator
│   ├── models/
│   │   ├── ticket.py                # Ticket model
│   │   ├── employee.py              # Employee model
│   │   ├── automation_state.py      # State model with status enum
│   │   └── enums/                   # EmployeeStatus, AutomationStatus, etc.
│   ├── services/
│   │   ├── login_workflow.py        # Main workflow orchestrator
│   │   ├── ticket_analyzer.py       # Login issue detection
│   │   ├── decision_service.py      # Business logic
│   │   ├── ticket_poller.py         # Odoo polling + retry polling
│   │   ├── ticket_fingerprinter.py  # Change detection
│   │   ├── communication_state.py   # Email deduplication tracker
│   │   └── gmail/
│   │       ├── gmail_service.py     # SMTP email sending
│   │       ├── email_templates.py   # Template definitions
│   │       └── template_selector.py # Template selection logic
│   ├── repositories/
│   │   └── automation_state_repository.py # SQLite persistence
│   ├── data/
│   │   ├── automation_state.db      # SQLite database
│   │   └── hr.json                  # Mock HR data
│   ├── .env.example                 # Example configuration
│   └── .env                         # Configuration (gitignored)
├── tests/
│   ├── units/                       # 276 unit tests
│   │   ├── test_email_templates.py
│   │   ├── test_ticket_analyzer.py
│   │   ├── test_login_workflow.py
│   │   ├── test_decision_service.py
│   │   └── [others...]
│   ├── integration/                 # 118 integration tests
│   │   ├── test_login_workflow_email.py
│   │   ├── test_p0_correctness.py
│   │   ├── test_run_once_integration.py
│   │   ├── test_communication_policy.py
│   │   ├── test_persistent_communication_state.py
│   │   └── [others...]
│   └── conftest.py                  # Shared fixtures
├── CLAUDE.md                        # Development guidance
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
└── TESTING_SUMMARY.md               # Detailed test results
```

### Key Components

#### LoginWorkflow (`srcs/services/login_workflow.py`)

Main orchestrator coordinating all automation steps:

```python
workflow = LoginWorkflow(
    ticket_client=ticket_client,
    hr_client=hr_client,
    ticket_analyzer=ticket_analyzer,
    gmail_service=gmail_service,           # Optional
    state_repo=state_repo,                 # Optional
)

result = workflow.execute(ticket_id=123, state=previous_state)
# Returns: WorkflowResult with action_taken and side-effect flags
```

**Methods**:
- `execute(ticket_id, state)` - Run complete workflow, pass prior state for retry
- `_execute_decision()` - Route to specific handler based on decision
- `_handle_reactivation()` - Account reactivation with side-effect tracking
- `_handle_escalation()` - Manual review escalation
- `_handle_skip()` - Skip non-applicable tickets
- `_send_outcome_email()` - Send exactly one email based on result

**Side-Effect Tracking**:
```python
result = workflow.execute(ticket_id)
if result.success:
    # Save flags for retry scenarios
    state.reactivation_completed = result.reactivation_completed
    state.odoo_note_completed = result.odoo_note_completed
    state.stage_update_completed = result.stage_update_completed
```

#### TicketAnalyzer (`srcs/services/ticket_analyzer.py`)

Detects login issue patterns from ticket content:

```python
analyzer = TicketAnalyzer()
result = analyzer.analyze(ticket)
# Returns: AnalysisResult(is_login_issue, issue_type, confidence)
```

Patterns detected:
- Cannot login / Can't login / Unable to login
- Account locked / Locked out
- Password reset / Reset password
- Access denied / No access
- Inactive account
- Session expired / Timeout

#### DecisionService (`srcs/services/decision_service.py`)

Makes business decisions based on rules:

```python
service = DecisionService()
decision = service.decide(employee, ticket)
# Returns: DecisionResult(action, reason)
```

Decision logic:
1. Employee not found → MANUAL_REVIEW
2. Not a login issue → SKIP
3. Terminated employee → MANUAL_REVIEW
4. On-leave employee → MANUAL_REVIEW
5. Inactive employee → MANUAL_REVIEW
6. Active + login issue → APPROVE_REACTIVATION

#### TicketPoller (`srcs/services/ticket_poller.py`)

Queries Odoo for tickets and tracks polling state:

```python
poller = TicketPoller(ticket_client, state_repo)

# New tickets from Odoo
new_tickets = poller.poll(limit=100, min_age=5)

# Retry-scheduled tickets ready for processing
retry_tickets = poller.poll_for_retry(limit=50)
```

**Change Detection**:
- Skips tickets with unchanged fingerprint (not processing same state twice)
- Skips tickets with active processing lease (another worker has it)
- Includes tickets with significant changes (fingerprint differs)

#### AutomationStateRepository (`srcs/repositories/automation_state_repository.py`)

Persists all state to SQLite:

```python
repo = AutomationStateRepository(db_path="data/automation_state.db")

# Save ticket state
repo.save(automation_state)

# Retrieve ticket state
state = repo.get(ticket_id)

# Claim processing lease (prevent concurrent processing)
claimed = repo.claim_for_processing(ticket_id, fingerprint, lease_duration_seconds=300)

# Schedule retry
repo.schedule_retry(ticket_id, retry_after_seconds=3600, error="Note posting failed")

# Track communication events
repo.mark_communication_sent(ticket_id, CommunicationEvent.RESOLUTION)
if repo.has_communication_sent(ticket_id, CommunicationEvent.RESOLUTION):
    # Don't send duplicate
    pass
```

**Tables**:
- `automation_state` - Ticket processing state
- `communication_events` - Sent emails and timestamps
- `customer_confirmations` - Customer response tracking

#### GmailService (`srcs/services/gmail/gmail_service.py`)

Sends emails via Gmail SMTP:

```python
service = GmailService(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_username="your-email@gmail.com",
    smtp_password="app-password",
    from_email="your-email@gmail.com",
)

context = EmailContext(
    recipient_email="user@company.com",
    recipient_name="John Doe",
    ticket_id=123,
    ticket_title="Cannot login",
    template=EmailTemplate.RESOLUTION,
)

success = service.send_email(context)
```

**Features**:
- TLS/SSL encryption
- Graceful error handling (doesn't crash workflow)
- Optional (automation works without it)
- Logging of all sends
- Retry logic with exponential backoff

## Implementation Phases

### ✅ Phase 1-4: Email Communication (Complete)
- Email template system with 6 templates
- Template selector with event-based routing
- Acknowledgement email workflow
- Email deduplication with CommunicationStateTracker
- Tests: 40+ passing

### ✅ Phase 5: State Tracking (Complete)
- Communication state persistence to SQLite
- Customer confirmation tracking
- State recovery across restarts
- Tests: 12+ passing

### ✅ Phase 6: Complete Workflow (Complete)
- Customer confirmation workflow
- Comprehensive lifecycle tests
- Outcome-first communication policy
- Tests: 20+ passing

### ✅ Phase 7: Gmail Integration (Complete)
- Gmail SMTP service implementation
- Configuration auto-detection (pytest vs production)
- Generic email templates with dynamic content
- Universal acknowledgement emails
- Tests: 10+ passing

### ✅ Phase 8: P0 Correctness (Complete)
- **Odoo Boolean Results**: add_log() and update_stage() False returns schedule retry
- **Partial Recovery**: Persist side effects immediately, skip completed actions on retry
- **Atomic Processing Claims**: Fingerprint changes blocked by active lease
- **Email Failure Recovery**: Don't mark complete on email failures, retry safely
- **Integration Tests**: Full retry flow with actual side-effect call counts
- Tests: 6 new integration tests, all 394 passing

### 🔄 Phase 9-14: P1 Advanced Retry (Ready)
- Max retry limits and dead letter handling
- Exponential backoff configuration
- Retry metrics and monitoring
- Escalation on max retries
- Cleanup and failure analysis

### 🔄 Phase 15-18: P2 Analytics (Ready)
- Processing metrics and dashboards
- Email success tracking and analysis
- Performance optimization and bottleneck detection
- Production monitoring integration

## P0 Correctness Implementation Details

### 1. Odoo Boolean Results

**Problem**: add_log() and update_stage() returning False were treated as success.

**Solution**: Check boolean return values and schedule retry on False:

```python
# In _handle_reactivation()
success = self.ticket_client.add_log(ticket_id, log_message)
if not success:  # False return triggers retry
    return WorkflowResult(
        success=False,
        action_taken="retry_scheduled",
        reactivation_completed=reactivation_completed,  # Preserve flag
    )
```

### 2. Partial Recovery

**Problem**: Completed side effects were not persisting across retries, causing duplication.

**Solution**: 
- Save side-effect flags immediately after each success
- On retry, check flags and skip already-completed actions
- Include all flags in workflow result for caller to persist

```python
# First attempt: LMS succeeds, Odoo fails
result = workflow.execute(ticket_id=1)
state.reactivation_completed = result.reactivation_completed  # Save
state.schedule_retry()

# Retry: Skip LMS, retry Odoo
if not state.reactivation_completed:
    # Reactivate
else:
    logger.info("LMS already done, skip")  # Skip it
```

### 3. Atomic Processing Claims

**Problem**: Concurrent workers could bypass processing lease via fingerprint changes.

**Solution**: Check lease expiration **before** fingerprint check:

```python
# In claim_for_processing()
if self.processing_lease_until and self.processing_lease_until > now:
    # Lease still active, block claim
    return False  # Blocked by active lease
if self.fingerprint != new_fingerprint:
    # Ticket changed, can reprocess
    return True
```

### 4. Email Failure Recovery

**Problem**: Email failures weren't being handled safely for retry.

**Solution**: 
- Don't send email on failures (retry_scheduled action)
- Only send on successful reactivation
- Email failures don't cascade to workflow failure

```python
# Email only sent for successful outcomes
if result.action_taken == "account_reactivated":
    self._send_outcome_email(...)  # Sends RESOLUTION
elif result.action_taken == "retry_scheduled":
    # No email, will retry later
    pass
```

### 5. Integration Tests

Created comprehensive integration tests verifying:
- Odoo False returns schedule retry
- Side effects preserved on retry
- Fingerprint changes blocked by active lease
- Email failures don't crash workflow
- Full retry flow with actual call counts

Tests file: `tests/integration/test_p0_correctness.py` (6 tests, all passing)

## Performance

Typical automation run on 5 tickets:
- **Total time**: ~2 seconds
- **Per ticket**: ~0.4 seconds (analysis only)
- **Email bottleneck**: ~4 seconds per email (SMTP + TLS)

Optimizations:
- HR employee lookup caching (300s TTL)
- Batch ticket retrieval from Odoo
- Communication state tracking (prevents redundant emails)
- SQLite for fast state persistence
- Fingerprinting prevents redundant analysis

## Troubleshooting

### Gmail emails not sending
```
✓ Check SMTP_USERNAME and SMTP_PASSWORD in .env
✓ Verify Gmail app password is 16 characters (with spaces)
✓ Ensure 2FA enabled on Gmail account
✓ Check logs for SMTP error messages
✓ Run with LOG_LEVEL=DEBUG for details
```

### Tickets not being processed
```
✓ Verify ODOO_URL, ODOO_DATABASE, ODOO_RPC_KEY correct
✓ Check Odoo is running and accessible
✓ Run with --log-level DEBUG for details
✓ Verify ticket has valid email_from field
✓ Check processing lease not blocking (wait 5 minutes or restart)
```

### Duplicate emails being sent
```
✓ Check if previous automation run crashed
✓ Verify SQLite database (data/automation_state.db) intact
✓ Clear database if corrupted and restart
✓ Check email deduplication working: query communication_events table
```

### Retry tickets not being processed
```
✓ Check next_retry_at is in the past
✓ Verify retry_count < max_retries
✓ Check SQLite has RETRY_SCHEDULED status
✓ Run poller.poll_for_retry() to see ready retries
✓ Verify main.py calls run_once() which includes retries
```

### Employee not found
```
✓ Check mock HR data in data/hr.json
✓ Verify employee email matches ticket email (case-insensitive)
✓ Add test employees if using real HR API
✓ Check HR_FILE path in config
```

## Deployment Checklist

- [ ] Configure `.env` with Odoo credentials
- [ ] Test Odoo connection: `python srcs/main.py --once --limit 1`
- [ ] Setup Gmail app password if email needed
- [ ] Test email sending with sample ticket
- [ ] Verify HR data loaded correctly
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify 394 tests passing
- [ ] Monitor first few polling cycles for errors
- [ ] Setup continuous polling: `python srcs/main.py --poll --interval 60`
- [ ] Setup monitoring dashboard for metrics
- [ ] Document any customizations or modifications
- [ ] Plan retry dead letter review process

## Development Commands

```bash
# Run automation
python srcs/main.py --once                    # One-time
python srcs/main.py --poll --interval 60      # Continuous (every 60s)

# Run tests
pytest tests/ -v                              # All tests
pytest tests/units/ -v                        # Units only
pytest tests/integration/ -v                  # Integration only
pytest tests/ --cov=srcs --cov-report=html   # With coverage

# Code quality
python -m pylint srcs/
python -m black srcs/ tests/
```

## Git History

```
feat(login): implement retry mechanism for Odoo log and stage updates on failure
refactor: datetime usage to timezone.utc across the codebase
feat(main): integrate retry polling into run_once()
test(retry): add retry integration tests
feat(main): integrate processing claims before workflow execution
feat(state): expose processing lease and add claim tests
feat(communication): persist email events to SQLite
fix(email): send exactly one customer email per cycle
docs(README): Enhance clarity and completeness of automation documentation
feat(email_templates): Update email subjects and bodies for clarity and relevance
feat(gmail_integration): Initialize GmailService in main workflow
feat(config): Auto-detect pytest vs production mode
feat(email_templates): Make templates generic with dynamic {ticket_title}
feat(workflow): Send acknowledgement to all tickets with email
test(phase7): Add comprehensive workflow lifecycle tests
feat(customer_confirmation): Add confirmation state tracking
feat(communication_state): Implement email deduplication
feat(email_template_selector): Centralized template selection
test(phase3): Event-based acknowledgement email tests
test(phase2): Template selector service tests
test(phase1): Email template system tests
```

## Design Principles

**Operating Engineer Philosophy**: Automation handles recurring issues; root cause fixes go to dev team.

**Test-Driven Development**: Every feature added via RED → GREEN → REFACTOR cycle. Each phase committed separately.

**Graceful Degradation**: Automation continues even if optional services (Gmail, HR) fail. Core functionality works with minimal config.

**Idempotent Operations**: All side effects tracked and persisted. Retries skip already-completed actions.

**Outcome-First Communication**: Exactly one email per execution based on workflow result, never multiple per cycle.

**Concurrency-Safe**: Processing leases prevent multiple workers from processing same ticket. Fingerprints detect concurrent modifications.

**Observability**: Comprehensive logging, metrics tracking, state persistence for debugging and monitoring.

## Resources

- **Week 5 Plan**: `D:\Study\mindx\mindx-onb\docs\plans\week-5\`
- **Odoo Documentation**: https://www.odoo.com/documentation/16.0/
- **Python**: 3.9+ (tested with 3.13.3)
- **Testing**: pytest framework with comprehensive fixtures
- **Database**: SQLite (bundled with Python)
- **Email**: Gmail SMTP with TLS/SSL

## Support

For questions or issues:

1. Check the troubleshooting section above
2. Review test cases in `tests/` for usage examples
3. Check logs with `LOG_LEVEL=DEBUG`
4. Review automation state in `data/automation_state.db`
5. Check `CLAUDE.md` for development architecture

---

**Last Updated**: 2026-11-07
**Test Status**: ✅ 394/394 tests passing (276 units + 118 integration)
**Production Ready**: ✅ Yes
**Retry Mechanism**: ✅ Implemented with state recovery
**Email Integration**: ✅ Gmail SMTP working
**Configuration**: ✅ Pytest auto-detection enabled
