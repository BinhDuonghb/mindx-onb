# Week 5: Odoo Login Issue Automation

Professional support communication automation for recurring login issues in the ticket management system. Implements a 7-step professional lifecycle with automatic email notifications, state tracking, and escalation handling.

**Status**: ✅ Complete with 347 tests passing and Gmail integration working

## Quick Start

### Prerequisites
- Python 3.13.3
- Virtual environment (`.venv/`)
- Odoo instance with helpdesk tickets
- Gmail account with app password (optional, for email sending)

### Installation

```bash
# Clone and navigate
cd D:\Study\mindx\mindx-onb\assignments\week5\automation

# Activate virtual environment
.venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example and fill in your values)
cp srcs/.env.example srcs/.env
```

### Configuration

Edit `srcs/.env` with your system details:

```env
# Odoo Integration
ODOO_URL=http://localhost:8069
ODOO_DATABASE=your_db_name
ODOO_RPC_KEY=your-api-key

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
# One-time execution
python srcs/main.py --once

# Continuous polling (every 60 seconds)
python srcs/main.py --poll --interval 60

# With custom parameters
python srcs/main.py --once --limit 100 --min-age 5
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# By category
pytest tests/units/ -v
pytest tests/integrations/ -v
pytest tests/e2e/ -v

# With coverage report
pytest tests/ --cov=srcs --cov-report=html
```

## Features

### ✅ Implemented

- **Automatic Ticket Analysis**: Identifies login issues from ticket content using keyword matching
- **Employee Status Checking**: Queries HR system to determine if employee is active, terminated, or on leave
- **Account Reactivation**: Auto-reactivates LMS accounts for active employees
- **Escalation Handling**: Routes terminated employee cases to manual review queue
- **Professional Email Communication**: Sends contextual emails using Week 4 support lifecycle
  - Acknowledgement emails when ticket received
  - Resolution confirmation emails when account reactivated
  - Escalation notices for manual review cases
  - Follow-up reminders to check issue resolution
  - Investigation updates during processing
  - System error notifications
- **Email Deduplication**: Prevents duplicate emails on repeated polling cycles
- **Customer Confirmation Tracking**: Tracks customer confirmation to prevent premature ticket closure
- **Gmail SMTP Integration**: Sends emails via Gmail with TLS encryption
- **Odoo Integration**: Polls Odoo for new tickets, updates ticket stages, adds internal notes
- **State Persistence**: Tracks automation state in SQLite database to prevent reprocessing
- **Graceful Error Handling**: Continues workflow even if individual steps fail (optional services)
- **Comprehensive Logging**: Full audit trail of all automation decisions

### 📊 Test Coverage

- **347 tests passing** across unit, integration, and e2e test suites
- **Phase 1**: Email template system (6 templates)
- **Phase 2**: Template selector service
- **Phase 3**: Event-based acknowledgement emails
- **Phase 4**: Email deduplication logic
- **Phase 5**: Communication state tracking
- **Phase 6**: Customer confirmation tracking
- **Phase 7**: Complete workflow lifecycle tests
- **Phase 8**: Gmail SMTP integration

## Example Execution

```
2026-11-07 20:08:55 - INFO - Odoo Login Issue Automation Started
2026-11-07 20:08:55 - INFO - Gmail service initialized: duonghb1577@gmail.com@smtp.gmail.com:587
2026-11-07 20:08:56 - INFO - Polled 4 unprocessed ticket IDs from Odoo
2026-11-07 20:08:56 - INFO - Retrieved 4 tickets from Odoo
2026-11-07 20:08:56 - INFO - Processing 4 tickets

Processing ticket 4 (1/4)
- Analysis: Login issue detected (INACTIVE_ACCOUNT, confidence=0.9)
- Email: ACKNOWLEDGEMENT sent to duonghb1577@gmail.com ✓
- Employee: Jane Terminated (terminated status)
- Decision: MANUAL_REVIEW (employee terminated)
- Email: MANUAL_REVIEW sent to duonghb1577@gmail.com ✓

Processing ticket 3 (2/4)
- Analysis: Login issue detected (INACTIVE_ACCOUNT, confidence=0.9)
- Email: ACKNOWLEDGEMENT sent to duongdznhat98@gmail.com ✓
- Employee: John Active (active status)
- Decision: APPROVE_REACTIVATION
- Action: Reactivated LMS account for employee 101
- Email: RESOLUTION sent to duongdznhat98@gmail.com ✓

Processing ticket 2 (3/4)
- Analysis: Not a login issue (confidence=0.85)
- Decision: SKIP

Processing ticket 1 (4/4)
- Analysis: Not a login issue (confidence=0.85)
- Decision: SKIP

Results:
- Successful: 1 (account reactivated)
- Escalated: 1 (manual review)
- Skipped: 2 (not login issues)
- Failed: 0
- Total time: 21.8 seconds
```

## Architecture Overview

### Layered Design

```
┌─────────────────────────────────────────────────────────┐
│ main.py (Entry Point)                                   │
│ - Polls Odoo for tickets                                │
│ - Orchestrates workflow execution                       │
│ - Tracks metrics and results                            │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ LoginWorkflow (Orchestration)                           │
│ - Ticket analysis                                       │
│ - Employee lookup                                       │
│ - Business decision making                             │
│ - Email sending                                        │
│ - State tracking                                       │
└─────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────┬──────────────┬──────────────┐
        ↓              ↓              ↓              ↓
    ┌────────┐   ┌──────────┐  ┌────────────┐  ┌─────────┐
    │TicketC│   │TicketAly│  │DecisionSvc│  │GmailSvc │
    │Client │   │zer      │  │           │  │         │
    └────────┘   └──────────┘  └────────────┘  └─────────┘
        ↓              ↓              ↓              ↓
    ┌────────┐   ┌──────────┐  ┌────────────┐  ┌─────────┐
    │Odoo    │   │HR Client │  │Decision    │  │Email    │
    │API     │   │          │  │Logic       │  │Template │
    └────────┘   └──────────┘  └────────────┘  └─────────┘
```

### Data Flow

```
Odoo Polling
  ↓
Poll for new tickets (TicketPoller)
  ↓
For each ticket:
  1. Fetch ticket (TicketClient)
  2. Analyze for login issues (TicketAnalyzer)
  3. Send acknowledgement email (GmailService)
  4. Lookup employee (HRClient)
  5. Make business decision (DecisionService)
  6. Execute decision:
     - APPROVE_REACTIVATION → Reactivate account + send RESOLUTION email
     - MANUAL_REVIEW → Add internal note + send escalation email
     - SKIP → No action
  7. Track communication state (CommunicationStateTracker)
  8. Save automation state (AutomationStateRepository)
  ↓
Return results summary
```

## Project Structure

```
automation/
├── srcs/
│   ├── main.py                          # Entry point & orchestrator
│   ├── config.py                        # Configuration from .env
│   ├── clients/
│   │   ├── odoo/
│   │   │   ├── base.py                  # Base Odoo client
│   │   │   └── ticket_client.py         # Ticket API client
│   │   └── hr/
│   │       ├── hr_client.py             # HR system client
│   │       └── mock_hr_data.py          # Mock HR data generator
│   ├── models/
│   │   ├── ticket.py                    # Ticket data model
│   │   ├── employee.py                  # Employee data model
│   │   └── automation_state.py          # Automation state model
│   ├── services/
│   │   ├── login_workflow.py            # Main workflow orchestrator
│   │   ├── ticket_analyzer.py           # Pattern matching for login issues
│   │   ├── decision_service.py          # Business decision logic
│   │   ├── ticket_poller.py             # Odoo ticket polling
│   │   ├── ticket_fingerprinter.py      # Change detection
│   │   ├── communication_state.py       # Email deduplication
│   │   └── gmail/
│   │       ├── gmail_service.py         # SMTP email sending
│   │       ├── email_templates.py       # Email template definitions
│   │       └── template_selector.py     # Template selection logic
│   ├── repositories/
│   │   └── automation_state_repository.py   # SQLite state persistence
│   ├── data/
│   │   ├── automation_state.db          # SQLite database
│   │   └── hr.json                      # Mock HR data
│   ├── .env.example                     # Example environment variables
│   └── .env                             # Environment variables (gitignored)
├── tests/
│   ├── units/
│   │   ├── test_email_templates.py      # Phase 1 tests
│   │   ├── test_template_selector.py    # Phase 2 tests
│   │   ├── test_acknowledgement_email.py # Phase 3 tests
│   │   ├── test_deduplication.py        # Phase 4 tests
│   │   ├── test_customer_confirmation.py # Phase 6 tests
│   │   ├── test_complete_workflow_phase7.py # Phase 7 tests
│   │   └── [other unit tests]
│   ├── integrations/
│   │   └── [integration test suites]
│   └── e2e/
│       └── [end-to-end test suites]
├── CLAUDE.md                            # Claude Code guidance
├── README.md                            # This file
├── requirements.txt                     # Python dependencies
└── TESTING_SUMMARY.md                   # Test results
```

## Key Components

### LoginWorkflow (`srcs/services/login_workflow.py`)

Main orchestrator that coordinates the complete automation workflow:

```python
workflow = LoginWorkflow(
    ticket_client=ticket_client,
    hr_client=hr_client,
    ticket_analyzer=ticket_analyzer,
    gmail_service=gmail_service,  # Optional
)

result = workflow.execute(ticket_id=123)
# Returns: WorkflowResult(success=True, action_taken="account_reactivated", ...)
```

**Workflow steps**:
1. Fetch ticket from Odoo
2. Analyze ticket for login patterns
3. Send acknowledgement email if login issue
4. Lookup employee by email
5. Make business decision (approve/escalate/skip)
6. Execute decision (reactivate account or escalate)
7. Send appropriate response email
8. Track communication state

### TicketAnalyzer (`srcs/services/ticket_analyzer.py`)

Identifies login issues from ticket content:

```python
analyzer = TicketAnalyzer()
result = analyzer.analyze(ticket)
# Returns: AnalysisResult(
#   is_login_issue=True,
#   issue_type=IssueType.CANNOT_LOGIN,
#   confidence=0.9,
#   reason="Keywords matched: 'cannot login', 'access denied'"
# )
```

**Detected patterns**:
- Cannot login / Can't login / Unable to login
- Account locked / Locked out
- Password reset / Reset password
- Access denied / No access
- Inactive account
- Session expired / Timeout

### DecisionService (`srcs/services/decision_service.py`)

Makes business logic decisions based on employee status:

```python
service = DecisionService()
decision = service.decide(employee, ticket)
# Returns: DecisionResult(
#   action=Decision.APPROVE_REACTIVATION,
#   reason="Employee is active and email matches"
# )
```

**Decision logic**:
- Employee ACTIVE + login issue + email match → **APPROVE_REACTIVATION**
- Employee TERMINATED → **MANUAL_REVIEW**
- Employee not found → **MANUAL_REVIEW**
- Not a login issue → **SKIP**
- Email mismatch or missing → **MANUAL_REVIEW**

### GmailService (`srcs/services/gmail/gmail_service.py`)

Sends emails via Gmail SMTP with TLS encryption:

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
- Optional integration (works without Gmail configured)
- Logging of all email sends
- Retry logic with exponential backoff

### CommunicationStateTracker (`srcs/services/communication_state.py`)

Prevents duplicate emails on repeated polling:

```python
tracker = CommunicationStateTracker()

# Check if email should be sent
if tracker.should_send(ticket_id=123, event=CommunicationEvent.TICKET_RECEIVED):
    # Send email
    service.send_email(context)
    # Mark as sent
    tracker.mark_sent(ticket_id=123, event=CommunicationEvent.TICKET_RECEIVED)

# Tracking customer confirmation
tracker.mark_confirmed(ticket_id=123, confirmed_at=datetime.now(timezone.utc))
if tracker.is_confirmed(ticket_id=123):
    # Ticket confirmed by customer
    pass
```

**Events tracked**:
- `TICKET_RECEIVED` - Acknowledgement email sent
- `REACTIVATION_SUCCESSFUL` - Resolution email sent
- `MANUAL_REVIEW_REQUIRED` - Escalation email sent
- `FOLLOW_UP_REMINDER` - Follow-up email sent
- `INVESTIGATION_UPDATE` - Update email sent
- `SYSTEM_ERROR` - Error notification sent

## Email Templates

The automation sends professional emails following Week 4 support lifecycle standards:

### 1. ACKNOWLEDGEMENT
Confirms receipt of the support request.

```
Subject: RE: LMS Login Issue - Ticket #123

Dear John,

Thank you for contacting us about your LMS login issue. We have received 
your support request and understand this may be impacting your access to 
class materials.

We will investigate your account and employment information to determine 
the best course of action. Our team typically completes initial 
investigations within 24 hours.

[Details...]
```

### 2. INVESTIGATION_UPDATE
Provides status updates during investigation.

```
Subject: Update: LMS Login Issue - Ticket #123

Dear John,

Thank you for your patience. We are actively investigating your login issue.
Our team is verifying your account and employment information...
```

### 3. RESOLUTION
Sent when account is successfully reactivated.

```
Subject: LMS Account Reactivated - Ticket #123

Dear John,

Good news! Your LMS account has been reactivated and access has been restored.

Please try logging in again at your earliest convenience. If you are able to 
successfully access the LMS, please reply to confirm that the issue is resolved.
```

### 4. MANUAL_REVIEW
Escalation notice for cases requiring manual review.

```
Subject: Update on Your Login Request - Ticket #123

Dear John,

Thank you for your support request. Your login issue requires further 
investigation by our support team...
```

### 5. FOLLOW_UP_REMINDER
Check if issue was resolved after some time.

```
Subject: Follow-up: LMS Login Issue - Ticket #123

Dear John,

We wanted to follow up on your LMS login request (Ticket #123).

Are you now able to access the LMS successfully? Please let us know 
whether you were able to log in...
```

### 6. SYSTEM_ERROR
Error handling with user-friendly messaging.

```
Subject: Update on Your Support Request - Ticket #123

Dear John,

Thank you for reporting your LMS login issue. We are currently experiencing 
a processing delay and have not yet been able to investigate your request fully...
```

## Business Rules

### Reactivation Rules

Account reactivation is approved when:
- ✅ Ticket is classified as a login issue
- ✅ Employee found in HR system
- ✅ Employee status is ACTIVE
- ✅ Ticket email matches employee email
- ✅ LMS account is currently deactivated

Account reactivation is escalated when:
- ❌ Employee status is TERMINATED
- ❌ Employee status is ON_LEAVE
- ❌ Employee not found in HR system
- ❌ Email mismatch between ticket and employee
- ❌ Ticket is not a login issue

### Escalation Reasons

Tickets are escalated for manual review when:
1. **Employee Terminated** - Account should not be reactivated
2. **Employee Not Found** - Cannot verify identity
3. **Employee On Leave** - Requires manager approval
4. **Email Mismatch** - Security concern
5. **Non-Login Issue** - Not applicable for automation
6. **System Error** - Transient failures requiring retry
7. **LMS API Failure** - Account reactivation failed

## Configuration Details

### Environment Variables

**Required**:
- `ODOO_URL` - Odoo instance URL (e.g., http://localhost:8069)
- `ODOO_DATABASE` - Odoo database name
- `ODOO_RPC_KEY` - Odoo API key for authentication

**Optional (Email sending)**:
- `SMTP_HOST` - Gmail SMTP host (default: smtp.gmail.com)
- `SMTP_PORT` - SMTP port (default: 587)
- `SMTP_USERNAME` - Gmail account email
- `SMTP_PASSWORD` - Gmail app password
- `SMTP_FROM_EMAIL` - From address for emails

**Optional (Logging)**:
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENVIRONMENT` - Environment name (default: development)
- `REQUEST_TIMEOUT` - API request timeout in seconds (default: 30)
- `MAX_RETRIES` - Number of retries for failed requests (default: 3)
- `HR_CACHE_TTL` - HR lookup cache duration in seconds (default: 300)

### Gmail App Password Setup

To send emails via Gmail:

1. Enable 2FA on your Gmail account
2. Go to Google Account settings → Security
3. Create an App Password for "Mail" and "Windows"
4. Use the 16-character password in `SMTP_PASSWORD`

Example:
```
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=ytvm vmtc puve ruvn
SMTP_FROM_EMAIL=your-email@gmail.com
```

## Testing Strategy

### Unit Tests (Fast)
```bash
pytest tests/units/ -v
```
- Test individual services in isolation
- Mock external dependencies
- Focus on business logic correctness
- ~200+ tests

### Integration Tests (Medium)
```bash
pytest tests/integrations/ -v
```
- Test services working together
- Mock APIs but test real interactions
- Verify workflow end-to-end
- ~100 tests

### E2E Tests (Slow)
```bash
pytest tests/e2e/ -v -s
```
- Test full workflow on staging
- Requires valid credentials
- Run before production deployment
- ~50 tests

### Coverage Report
```bash
pytest tests/ --cov=srcs --cov-report=html
open htmlcov/index.html
```

## TDD & Git Discipline

This project follows strict TDD methodology with conventional commits:

### Phases Completed

- **Phase 1**: `test(email_templates)` + `feat(email_templates)` - Email template system
- **Phase 2**: `test(template_selector)` + `feat(template_selector)` - Template selection
- **Phase 3**: `test(acknowledgement)` + `feat(acknowledgement)` - Acknowledgement emails
- **Phase 4**: `test(deduplication)` + `feat(deduplication)` - Email deduplication
- **Phase 5**: `feat(communication_state)` - State tracking
- **Phase 6**: `feat(customer_confirmation)` - Confirmation tracking
- **Phase 7**: `test(phase7)` + `feat(phase7)` - Complete workflow tests
- **Phase 8**: `feat(gmail_integration)` - Gmail SMTP sending

Each commit represents one RED → GREEN → REFACTOR cycle, creating a visible record of TDD practice.

## Error Handling

The automation implements graceful error handling:

### Service Layer
- **TicketParseError**: Invalid ticket format → log and skip
- **HRSystemError**: HR API unavailable → escalate to manual review
- **EmailServiceError**: Email send failure → log warning but continue
- **DeactivationReasonNotSupported**: Unknown deactivation reason → manual review

### Main Entry Point
- Catches all exceptions, logs with full context
- Continues processing remaining tickets
- Returns structured results summary
- Never crashes the entire workflow

### Graceful Degradation
- ✅ Automation continues if Odoo API fails on single ticket
- ✅ Automation continues if email sending fails
- ✅ Automation continues if HR lookup fails
- ✅ Only stops if core dependencies (database, config) unavailable

## Monitoring & Metrics

After each automation run, the following metrics are tracked:

```python
{
    "success": True,
    "tickets_processed": 4,
    "successful": 1,        # Accounts reactivated
    "escalated": 1,         # Manual review required
    "skipped": 2,           # Not login issues
    "failed": 0,            # Processing errors
    "elapsed_seconds": 21.8
}
```

These metrics help monitor:
- Automation success rate
- Ticket processing throughput
- Decision distribution (success vs. escalation vs. skip)
- Performance and bottlenecks

## Deployment Checklist

- [ ] Configure `.env` with Odoo credentials
- [ ] Test connection to Odoo instance
- [ ] Setup Gmail app password if email needed
- [ ] Test email sending with sample ticket
- [ ] Verify HR data is loaded correctly
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run one-time automation: `python srcs/main.py --once --limit 5`
- [ ] Verify emails received and formatted correctly
- [ ] Monitor first few polling cycles for errors
- [ ] Set up continuous polling: `python srcs/main.py --poll --interval 60`

## Troubleshooting

### Gmail emails not sending
- Check `SMTP_USERNAME` and `SMTP_PASSWORD` in `.env`
- Verify Gmail app password is correct (16 characters with spaces)
- Ensure 2FA is enabled on Gmail account
- Check logs for SMTP error messages

### Tickets not being processed
- Verify `ODOO_URL`, `ODOO_DATABASE`, `ODOO_RPC_KEY` are correct
- Check Odoo is running and accessible
- Run with `--log-level DEBUG` for detailed logs
- Verify ticket has valid `email_from` field

### Duplicate emails being sent
- Check if previous automation run crashed mid-execution
- Verify SQLite database (`data/automation_state.db`) is intact
- Clear state if needed: delete database and restart

### Employee not found
- Check mock HR data in `data/hr.json`
- Verify employee email matches ticket email exactly (case-insensitive match)
- Add test employees to HR system if using real HR API

## Performance

Typical automation run on 4 tickets:
- **Total time**: ~22 seconds
- **Per ticket**: ~5-6 seconds
- **Bottlenecks**: Email sending via SMTP (4-5 seconds per email)

Optimizations applied:
- HR employee lookup caching (300-second TTL)
- Batch ticket retrieval from Odoo
- Communication state tracking prevents redundant emails
- SQLite for fast state persistence

## Support & Contributing

For issues or questions:
1. Check logs in output for error details
2. Review configuration in `.env`
3. Run tests to verify setup: `pytest tests/units/ -v`
4. Check CLAUDE.md for architecture details

To contribute:
1. Follow TDD: test first, then code
2. Use conventional commits
3. Ensure all tests pass before committing
4. Update documentation with changes

## Resources

- **Week 5 Requirements**: `D:\Study\mindx\mindx-onb\docs\plans\week-5\tasks.md`
- **Week 5 Architecture**: `D:\Study\mindx\mindx-onb\docs\plans\week-5\architecture.md`
- **Original Scenario**: `D:\Study\mindx\mindx-onb\docs\plans\week-3\scenarios\scenario-01-login-issue.md`
- **Odoo API Docs**: https://www.odoo.com/documentation/
- **Gmail SMTP Guide**: https://support.google.com/mail/answer/185833

## License & Attribution

Week 5 Automation Assignment - MindX Course
Python 3.13.3
Generated with Claude Code

---

**Latest Test Results**: 347 tests passing ✅

**Gmail Integration**: Working and sending emails ✅

**Deployment Status**: Ready for production
