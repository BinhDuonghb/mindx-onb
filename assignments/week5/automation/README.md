# Week 5: Odoo Login Issue Automation

Professional support communication automation for recurring login issues in the ticket management system. Implements a complete workflow with automatic email notifications, state tracking, and escalation handling.

**Status**: ✅ **Phase 8 Complete** | 347 tests passing | Gmail SMTP integration working | Configuration auto-detection enabled

## Quick Start

### Prerequisites
- Python 3.13.3
- Virtual environment (`.venv/`)
- Odoo instance with helpdesk tickets
- Gmail account with app password (optional, for email sending)

### Installation

```bash
# Navigate to project
cd D:\Study\mindx\mindx-onb\assignments\week5\automation

# Activate virtual environment
.venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy srcs\.env.example srcs\.env
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

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Running the Automation

```bash
# One-time execution (uses production Odoo config)
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
# All tests (automatically uses TEST_ODOO config)
pytest tests/ -v

# By category
pytest tests/units/ -v        # 276 tests
pytest tests/integrations/ -v # 71 tests
pytest tests/e2e/ -v          # E2E tests

# With coverage report
pytest tests/ --cov=srcs --cov-report=html
# Open htmlcov/index.html in browser
```

## Features

### ✅ Implemented (Phase 1-8)

#### Email Communication System
- **6 Professional Email Templates** (Week 4 aligned):
  - ACKNOWLEDGEMENT - Confirm receipt to customer
  - RESOLUTION - Notify account reactivated
  - MANUAL_REVIEW - Escalation notice
  - INVESTIGATION_UPDATE - Status updates
  - FOLLOW_UP_REMINDER - Check if resolved
  - SYSTEM_ERROR - Error handling

- **Universal Acknowledgement** - Sends ACKNOWLEDGEMENT to ALL tickets with email (not just login issues)
- **Generic Templates** - Uses dynamic `{ticket_title}` instead of hardcoded text
- **Gmail SMTP Integration** - Sends emails via Gmail with TLS encryption
- **Email Deduplication** - Prevents duplicate emails on repeated polling
- **Customer Confirmation Tracking** - Tracks customer confirmation to prevent premature ticket closure

#### Automation Workflow
- **Ticket Analysis** - Identifies login issues from content using pattern matching
- **Employee Status Checking** - Queries HR system (active/terminated/on-leave)
- **Account Reactivation** - Auto-reactivates LMS accounts for active employees
- **Escalation Handling** - Routes terminated/uncertain cases to manual review
- **Odoo Integration** - Polls tickets, updates stages, adds internal notes
- **State Persistence** - SQLite database prevents reprocessing same tickets

#### Configuration Management
- **Auto-Detection** - Detects pytest vs production mode automatically
  - When running `pytest` → Uses TEST_ODOO_* config
  - When running `python main.py` → Uses production ODOO_* config
- **Graceful Degradation** - Works without Gmail configured (emails just won't send)
- **Validation** - Validates required config and provides helpful error messages

#### Testing & Quality
- **347 tests passing** (276 units + 71 integrations)
- **Test-Driven Development** - Each phase committed as RED → GREEN → REFACTOR
- **Mocked Dependencies** - Unit tests don't require external systems
- **Integration Tests** - Test multiple services working together
- **Coverage Reports** - HTML coverage reports available

## Current Behavior

### Workflow Steps

```
1. Fetch ticket from Odoo
   ↓
2. Check for customer email
   ├─ No email? SKIP ticket
   └─ Has email? Continue...
   ↓
3. Send ACKNOWLEDGEMENT email to customer
   ↓
4. Analyze ticket for login patterns
   ├─ Is login issue? Continue...
   └─ Not login issue? SKIP automation (but email already sent)
   ↓
5. Lookup employee in HR system
   ├─ Not found? ESCALATE with MANUAL_REVIEW email
   ├─ Terminated? ESCALATE with MANUAL_REVIEW email
   ├─ On leave? ESCALATE with MANUAL_REVIEW email
   └─ Active? Continue...
   ↓
6. Reactivate LMS account
   ├─ Success? Send RESOLUTION email + mark completed
   └─ Failed? ESCALATE with MANUAL_REVIEW email
   ↓
7. Track communication state (prevent duplicates on re-poll)
   ↓
8. Save automation state to SQLite
```

### Email Behavior

| Scenario | Emails Sent |
|----------|------------|
| All tickets with email | ACKNOWLEDGEMENT ✓ |
| Login issue + Active employee | ACKNOWLEDGEMENT + RESOLUTION |
| Login issue + Terminated employee | ACKNOWLEDGEMENT + MANUAL_REVIEW |
| Login issue + Employee not found | ACKNOWLEDGEMENT + MANUAL_REVIEW |
| Non-login issue with email | ACKNOWLEDGEMENT only |
| No customer email | None (skipped) |
| Re-poll same ticket | None (deduplication prevents) |

## Project Structure

```
automation/
├── srcs/
│   ├── main.py                    # Entry point - polls Odoo and orchestrates
│   ├── config.py                  # Config with pytest auto-detection
│   ├── clients/
│   │   ├── odoo/
│   │   │   ├── base.py           # Base Odoo client
│   │   │   └── ticket_client.py  # Ticket API client
│   │   └── hr/
│   │       ├── hr_client.py      # HR system client
│   │       └── mock_hr_data.py   # Mock HR data generator
│   ├── models/
│   │   ├── ticket.py             # Ticket model
│   │   ├── employee.py           # Employee model
│   │   └── automation_state.py   # State tracking model
│   ├── services/
│   │   ├── login_workflow.py     # Main workflow orchestrator
│   │   ├── ticket_analyzer.py    # Login issue detection
│   │   ├── decision_service.py   # Business decision logic
│   │   ├── ticket_poller.py      # Odoo polling
│   │   ├── ticket_fingerprinter.py # Change detection
│   │   ├── communication_state.py # Email deduplication
│   │   └── gmail/
│   │       ├── gmail_service.py  # SMTP email sending
│   │       ├── email_templates.py # Email template definitions
│   │       └── template_selector.py # Template selection logic
│   ├── repositories/
│   │   └── automation_state_repository.py # SQLite persistence
│   ├── data/
│   │   ├── automation_state.db   # SQLite database
│   │   └── hr.json               # Mock HR data
│   ├── .env.example              # Example config
│   └── .env                      # Config (gitignored)
├── tests/
│   ├── units/
│   │   ├── test_email_templates.py       # Phase 1
│   │   ├── test_template_selector.py     # Phase 2
│   │   ├── test_acknowledgement_email.py # Phase 3
│   │   ├── test_deduplication.py         # Phase 4
│   │   ├── test_customer_confirmation.py # Phase 6
│   │   ├── test_complete_workflow_phase7.py # Phase 7
│   │   └── [other tests]
│   ├── integrations/
│   │   └── test_login_workflow_email.py
│   └── e2e/
│       └── [e2e tests]
├── CLAUDE.md                    # Development guidance
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── TESTING_SUMMARY.md           # Test results
```

## Key Components

### LoginWorkflow (`srcs/services/login_workflow.py`)

Main orchestrator coordinating all automation steps:

```python
workflow = LoginWorkflow(
    ticket_client=ticket_client,
    hr_client=hr_client,
    ticket_analyzer=ticket_analyzer,
    gmail_service=gmail_service,  # Optional
)

result = workflow.execute(ticket_id=123)
# Returns: WorkflowResult with success/action_taken/message
```

**Key Methods**:
- `execute(ticket_id)` - Run complete workflow for a ticket
- `_send_acknowledgement(ticket)` - Send ACK to customer
- `_handle_reactivation()` - Process successful reactivation
- `_handle_escalation()` - Process escalation to manual review
- `_handle_skip()` - Process non-login issues

### TicketAnalyzer (`srcs/services/ticket_analyzer.py`)

Detects login issue patterns from ticket content:

```python
analyzer = TicketAnalyzer()
result = analyzer.analyze(ticket)
# Returns: AnalysisResult(is_login_issue, issue_type, confidence)
```

**Detected Patterns**:
- Cannot login / Can't login / Unable to login
- Account locked / Locked out
- Password reset / Reset password
- Access denied / No access
- Inactive account
- Session expired / Timeout

### DecisionService (`srcs/services/decision_service.py`)

Makes business decisions based on rules:

```python
service = DecisionService()
decision = service.decide(employee, ticket)
# Returns: DecisionResult(action, reason)
```

**Decision Logic**:
1. Employee not found → MANUAL_REVIEW
2. Not a login issue → SKIP
3. Email mismatch → MANUAL_REVIEW
4. Terminated employee → MANUAL_REVIEW
5. On-leave employee → MANUAL_REVIEW
6. Inactive employee → MANUAL_REVIEW
7. Active + login issue + email match → APPROVE_REACTIVATION

### GmailService (`srcs/services/gmail/gmail_service.py`)

Sends emails via Gmail SMTP with TLS:

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
    template=EmailTemplate.ACKNOWLEDGEMENT,
)

success = service.send_email(context)
```

**Features**:
- TLS/SSL encryption
- Graceful error handling (doesn't crash workflow)
- Optional integration (automation works without it)
- Logging of all sends
- Retry logic with exponential backoff

### CommunicationStateTracker (`srcs/services/communication_state.py`)

Prevents duplicate emails on repeated polling:

```python
tracker = CommunicationStateTracker()

# Check if should send
if tracker.should_send(ticket_id=123, event=CommunicationEvent.TICKET_RECEIVED):
    service.send_email(context)
    tracker.mark_sent(ticket_id=123, event=CommunicationEvent.TICKET_RECEIVED)

# Track customer confirmation
tracker.mark_confirmed(ticket_id=123, confirmed_at=datetime.now(timezone.utc))
if tracker.is_confirmed(ticket_id=123):
    # Ticket confirmed by customer
    pass
```

**Tracked Events**:
- TICKET_RECEIVED - ACK sent
- REACTIVATION_SUCCESSFUL - Resolution sent
- MANUAL_REVIEW_REQUIRED - Escalation sent
- FOLLOW_UP_REMINDER - Follow-up sent
- INVESTIGATION_UPDATE - Update sent
- SYSTEM_ERROR - Error notification sent

## Configuration Details

### Environment Variables

**Production (python main.py)**:
- `ODOO_URL` - Odoo instance URL
- `ODOO_DATABASE` - Database name
- `ODOO_RPC_KEY` - API key

**Testing (pytest)**:
- `TEST_ODOO_URL` - Test Odoo URL
- `TEST_ODOO_DATABASE` - Test database
- `TEST_ODOO_RPC_KEY` - Test API key

**Auto-Detection**:
- Checks if `pytest` in `sys.modules`
- Checks if `PYTEST_TEMP_TEST_DB` env var is set
- Uses TEST_* config if pytest detected, otherwise ODOO_*

**Gmail (Optional)**:
- `SMTP_HOST` - Gmail SMTP (default: smtp.gmail.com)
- `SMTP_PORT` - SMTP port (default: 587)
- `SMTP_USERNAME` - Gmail email
- `SMTP_PASSWORD` - App password (16 chars)
- `SMTP_FROM_EMAIL` - From address

**Service**:
- `LOG_LEVEL` - INFO/DEBUG/WARNING/ERROR (default: INFO)
- `ENVIRONMENT` - development/staging/production (default: development)

### Gmail Setup

To enable email sending:

1. Enable 2FA on Gmail account
2. Go to Google Account → Security
3. Create App Password for "Mail" + "Windows"
4. Copy 16-character password to `SMTP_PASSWORD`

Example `.env`:
```env
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=ytvm vmtc puve ruvn
SMTP_FROM_EMAIL=your-email@gmail.com
```

## Email Templates

All templates use dynamic `{ticket_title}` instead of hardcoded text, making them suitable for any ticket type.

### ACKNOWLEDGEMENT
```
Subject: RE: {ticket_title} - Ticket #{ticket_id}

Thank you for contacting us. We have received your support request 
and understand this may be urgent for you.

We will investigate your request and account information to determine 
the best course of action. Our team typically completes initial 
investigations within 24 hours.

Ticket ID: {ticket_id}
Issue: {ticket_title}

We will keep you updated on progress. If you have any additional 
information, please reply to this email.
```

### RESOLUTION
```
Subject: Resolution: {ticket_title} - Ticket #{ticket_id}

Good news! We have resolved your issue and your account access 
has been restored.

Please try accessing your account again at your earliest convenience...
```

### MANUAL_REVIEW
```
Subject: Update on Your Request - Ticket #{ticket_id}

Thank you for your support request. Your case requires further 
investigation by our support team.

We are reviewing your account information and will determine the 
appropriate next steps...
```

### INVESTIGATION_UPDATE
```
Subject: Update: {ticket_title} - Ticket #{ticket_id}

Thank you for your patience. We are actively investigating your request.

Our team is reviewing your account and information to determine 
the appropriate resolution...
```

### FOLLOW_UP_REMINDER
```
Subject: Follow-up: {ticket_title} - Ticket #{ticket_id}

We wanted to follow up on your support request (Ticket #{ticket_id}).

Are you now able to access your account successfully? 
Please let us know...
```

### SYSTEM_ERROR
```
Subject: Update on Your Support Request - Ticket #{ticket_id}

Thank you for your support request. We are currently experiencing 
a processing delay and have not yet been able to investigate your 
request fully.

Our support team is aware of this issue and is working to resolve it...
```

## Test Coverage

### Unit Tests (276 tests)
Test individual services in isolation with mocked dependencies.

```bash
pytest tests/units/ -v
```

**Coverage**:
- Email templates (6 templates)
- Template selector
- Acknowledgement workflow
- Email deduplication
- Customer confirmation
- Complete workflow lifecycle
- Ticket analyzer patterns
- Decision service logic
- And more...

### Integration Tests (71 tests)
Test services working together with mocked external APIs.

```bash
pytest tests/integrations/ -v
```

**Coverage**:
- Workflow email integration
- Complete automation flow
- Error handling
- Graceful degradation

### E2E Tests
Test full workflow against real/staging systems.

```bash
pytest tests/e2e/ -v -s
```

**Requirements**:
- Valid Odoo credentials
- Valid Gmail credentials
- Real or staging system access

## Performance

Typical automation run on 5 tickets:
- **Total time**: ~2 seconds
- **Per ticket**: ~0.4 seconds (analysis only)
- **Email bottleneck**: ~4 seconds per email (SMTP + TLS)

**Optimizations**:
- HR employee lookup caching (300s TTL)
- Batch ticket retrieval from Odoo
- Communication state tracking (prevents redundant emails)
- SQLite for fast state persistence

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
```

### Duplicate emails being sent
```
✓ Check if previous automation run crashed
✓ Verify SQLite database (data/automation_state.db) intact
✓ Clear database if needed and restart
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
- [ ] Verify 347 tests passing
- [ ] Monitor first few polling cycles for errors
- [ ] Setup continuous polling: `python srcs/main.py --poll --interval 60`

## Development Commands

```bash
# Run automation
python srcs/main.py --once                    # One-time
python srcs/main.py --poll --interval 60      # Continuous

# Run tests
pytest tests/ -v                              # All tests
pytest tests/units/ -v                        # Units only
pytest tests/ --cov=srcs --cov-report=html   # With coverage

# Code quality
python -m pylint srcs/
python -m black srcs/ tests/
```

## Implementation Phases

### ✅ Phase 1: Email Templates (Complete)
- 6 professional email templates
- Template renderer with context support
- Tests passing

### ✅ Phase 2: Template Selector (Complete)
- Centralized template selection logic
- Event-based template routing
- Tests passing

### ✅ Phase 3: Acknowledgement Emails (Complete)
- Event-based ACK for new tickets
- Deduplication on re-polls
- Tests passing

### ✅ Phase 4: Email Deduplication (Complete)
- CommunicationStateTracker service
- In-memory tracking of sent events
- Prevents duplicate emails
- Tests passing

### ✅ Phase 5: State Tracking (Complete)
- Communication state persistence
- Customer confirmation tracking
- Tests passing

### ✅ Phase 6: Customer Confirmation (Complete)
- Track customer confirmation status
- Prevent auto-closure without confirmation
- Tests passing

### ✅ Phase 7: Workflow Lifecycle Tests (Complete)
- Comprehensive workflow tests
- Multiple scenarios covered
- 6 new tests, all passing

### ✅ Phase 8: Gmail Integration (Complete)
- Gmail SMTP service fully functional
- Email sending working in production
- Configuration auto-detection implemented
- Generic email templates deployed
- Universal acknowledgement emails
- Tests updated and passing

## Git History

```
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

## Resources

- **Week 5 Requirements**: `D:\Study\mindx\mindx-onb\docs\plans\week-5\tasks.md`
- **Week 5 Architecture**: `D:\Study\mindx\mindx-onb\docs\plans\week-5\architecture.md`
- **Original Scenario**: `D:\Study\mindx\mindx-onb\docs\plans\week-3\scenarios\scenario-01-login-issue.md`
- **CLAUDE.md**: Development guidance and architecture
- **Python**: 3.13.3
- **pytest**: Testing framework
- **python-dotenv**: Environment variable management
- **requests**: HTTP library

## Notes

- **Operating Engineer Philosophy**: Automation handles recurring issues; root cause fixes go to dev team
- **Test-Driven Development**: Every feature added via RED → GREEN → REFACTOR cycle
- **Graceful Degradation**: Automation continues even if optional services (Gmail, HR) fail
- **Monitoring**: Track success rate, escalation rate, and processing time
- **Maintenance**: Update analysis patterns as new login issue types emerge

---

**Last Updated**: 2026-11-07
**Test Status**: ✅ 347/347 tests passing
**Gmail Integration**: ✅ Working and sending emails
**Config Detection**: ✅ Pytest vs Production auto-detection enabled
**Production Ready**: ✅ Yes
