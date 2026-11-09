# Week 5: Reporting, Analysis & Automation Implementation

**Status:** ✅ Complete — Demo/Integration Pending  
**Test Coverage:** 483 tests passing (389 unit + 94 integration/e2e)  
**P2 Fixes:** Issue #5 (Odoo POST Idempotency & Safe Retry) complete with idempotent retry guards and ambiguous-outcome escalation  
**Automation:** Login Issue POC implemented, tested, ready for real HR/LMS integration

---

## Week 5 Overview

Week 5 focuses on analyzing ticket patterns from Week 4's production data and implementing Operating Engineer automation solutions for recurring issues. The week is split into two phases:

- **Days 1–2:** Reporting and analysis to identify recurring ticket patterns, recurring issues, and impact metrics
- **Days 3–4:** Automation implementation using Operating Engineer approach for the login issue scenario

The Operating Engineer approach prioritizes solving immediate, high-frequency support issues through bounded automation and SOPs rather than invasive code changes. For issues where root cause is unclear or risk is high, automation is scoped narrowly and wrapped with identity verification, authorization checks, and manual escalation guards.

---

## Part 1: Reporting & Analysis

### 1.1 Scope and Data

**Source:** `docs/plans/week-5/data/sample.xlsx` (Sheet1)  
**Extractable records:** 131 tickets with both ticket sequence and subject  
**Available fields:** Subject, Ticket IDs Sequence, Tags, Priority  
**Data boundaries:** No worklogs, affected-user counts, creation/close timestamps, or verified root causes in the training dataset

### 1.2 Recurring Issue Patterns

**Top 5 Provisional Issue Families** (131 records analyzed):

| Rank | Primary Issue Family | Count | % of 131 | Examples |
|---:|---|---:|---:|---|
| 1 | Account access / provisioning | 22 | 16.8% | `308`, `129`, `294`, `276`, `248` |
| 2 | Enrollment / class allocation | 18 | 13.7% | `302`, `224`, `201`, `60`, `290` |
| 3 | Timekeeping / attendance | 17 | 13.0% | `291`, `239`, `236`, `234`, `232` |
| 4 (tie) | Payment / transactions / orders | 13 | 9.9% | `287`, `278`, `249`, `153`, `305` |
| 4 (tie) | Student records / learning progress | 13 | 9.9% | `325`, `296`, `288`, `286`, `280` |

**Key Finding:** Account access tickets (22 records, 16.8%) are the highest-frequency group, but they span multiple subtypes: login/locked accounts, password resets, new account provisioning, and transfers. Not all 22 are eligible for automatic LMS reactivation; some require manual verification or explicit entitlement approval.

**Classification Method:** Each of the 131 records is assigned one primary issue family based on the reported symptom/request (not product tag alone). Test/sample records (10 rows) and cases with insufficient context (8 rows marked `Other/unclear`) are explicitly flagged and retained in the 131-row reconciliation.

**Evidence Boundaries:** This classification is a provisional title-based taxonomy with row-level confidence flags. The original Odoo ticket details are unavailable in this training assignment, so ambiguous cases remain flagged rather than silently reclassified.

### 1.3 Analysis Artifacts

Three analysis documents detail the findings:

- **`pattern-analysis.md`** — Observed data distribution, evidence conventions, and scope boundaries
- **`recurring-issues.md`** — Full 131-record mapping with primary issue family, subtype, confidence per row
- **`recommendations.md`** — Three solution options per Top 3 pattern with effort estimates, dependencies, risks, and action plan

### 1.4 Key Recommendations

**Pattern A — Account Access / Provisioning (22 tickets)**
- Short term: SOP + self-service + bounded LMS reactivation POC (Scenario 1, Week 5 exercise)
- Long term: Assess whether 30-day inactivity deactivation is intentional or fixable defect

**Pattern B — Enrollment / Class Allocation (18 tickets)**
- Short term: SOP and triage checklist
- Long term: Read-only eligibility checks and guided self-service

**Pattern C — Timekeeping / Attendance (17 tickets)**
- Short term: Diagnostic SOP and payroll-cutoff escalation rules
- Long term: Read-only health checks and synchronization alerts

---

## Part 2: Automation Implementation

### 2.1 Scenario 1 — Login Issue POC

**Scope:** Automatically reactivate LMS accounts deactivated due to 30-day inactivity when:
1. Ticket is classified as a login issue
2. Requester identity is independently verified
3. HR system confirms employee is active and eligible
4. Deactivation reason is specifically 30-day inactivity
5. All checks pass and authorization is confirmed

**Boundaries (explicit non-scope):**
- Password resets, new account provisioning, terminated/on-leave employees
- Accounts already active for other reasons
- Tickets without customer email
- Ambiguous write outcomes from Odoo (escalate instead of retry)

### 2.2 Architecture Overview

```
Odoo Ticket (polling or webhook)
  ↓
[TicketFingerprinter] — generate deterministic ID for idempotency
  ↓
[TicketAnalyzer] — classify as login issue
  ↓
[Identity Verifier] — verify requester (mock POC; real provider pending)
  ↓
[Decision Service] — check HR status and LMS eligibility
  ↓
  IF APPROVE: [HR] → [Odoo] → [Gmail] → [Persist State]
  IF ESCALATE: [Escalation Note] → [Manual Review]
  ↓
[AutomationExecutor] — resume from persisted state on restart
```

### 2.3 Key Design Decisions

#### Identity Verification: Fail-Closed by Default

**Decision:** Email match alone is insufficient; all non-verified requests escalate to manual review.

**Rationale:** Account reactivation requires independent verification (SSO token, security question, etc.); mock POC uses UNAVAILABLE verifier, forcing manual review in all cases.

#### Odoo Write Outcome Handling: UNKNOWN → Escalation (P2 Issue #5)

**Decision:** Ambiguous write outcomes (timeouts, 5xx, connection errors) escalate to manual review instead of triggering blind retries.

**Three-way classification:**
- `SUCCESS` (2xx) — Operation confirmed; proceed
- `CONFIRMED_FAILURE` (4xx) — Operation did not execute; safe to retry
- `UNKNOWN` (5xx, timeout, connection error) — Ambiguous; escalate with persisted state

**What this prevents:** If add_log() times out after Odoo already created the note, we don't blindly retry and create a duplicate.

#### Restart Safety: Persisted State + Lease Claims

**Decision:** Use SQLite to persist partial completion state; lease claims prevent concurrent workers from duplicating writes.

**What this means:**
- AutomationState tracks which side effects completed (reactivation_completed, odoo_note_completed, email_sent)
- On restart, workflow resumes only outstanding steps
- Lease claims prevent concurrent workers from processing the same ticket simultaneously

#### HTTP Retry Strategy Separation

**Read operations** (search, read, search_read): Bounded exponential backoff (0.1 * 2^attempt, capped at 1.0s)

**Write operations** (message_post, write): Zero automatic retries in urllib3; escalate on ambiguity

### 2.4 Test Coverage

**Total:** 483 tests passing
- **389 unit tests** — Decision logic, state persistence, error handling
- **94 integration/e2e tests** — Real SQLite, restart scenarios, concurrent-worker protection

**Key regression tests:**
- P2 Issue #4 — Identity verification required, stage mapping from config, missing email escalation
- P2 Issue #5 — Non-idempotent writes not auto-retried, ambiguous outcomes escalate, restart safety, lease protection

**Mock adapters (current state):**
- HR System: JSON file mock (NOT connected to real HR)
- LMS System: Mock reactivation flag (NOT connected to real LMS)
- Odoo: Mocked for unit tests
- Gmail: Mocked for all tests

---

## Part 3: Integration Status & Deployment Path

### 3.1 Current State: Demo / Sandbox Ready

| Component | Status | Notes |
|---|---|---|
| **Login workflow logic** | ✅ Complete | All decision paths, error handling, escalation guards tested |
| **P2 Issue #5 fixes** | ✅ Complete | UNKNOWN escalation, restart safety, idempotent guards in place |
| **Unit tests** | ✅ 389 passing | Decision logic, state, error handling verified |
| **Integration tests** | ✅ 94 passing | Real SQLite, restart scenarios, concurrent protection verified |
| **HR System** | 🔄 Mock only | Real API integration pending |
| **LMS System** | 🔄 Mock only | Real API integration pending |
| **Odoo** | 🔄 Partial | Reads work; writes have idempotent guards but need real instance |
| **Identity verification** | 🔄 Mock only | Real provider (SSO, LDAP, MFA) required |
| **Gmail** | 🔄 Disabled | Requires credentials; mocked for tests |

### 3.2 Pre-Deployment Checklist

**Before Sandbox:**
- [ ] Real HR API credentials and contract finalized
- [ ] Real LMS API credentials and contract finalized
- [ ] Real Odoo instance with stage mapping configured
- [ ] Identity verification provider selected and integrated
- [ ] Database backup and rollback procedures documented
- [ ] Audit logging for account reactivation enabled
- [ ] Manual escalation queue/workflow configured

**Before Production:**
- [ ] 4-week sandbox pilot: no wrong-account access, no duplicate side effects
- [ ] Security and business approval for reactivation criteria
- [ ] Incident response procedure documented and tested
- [ ] Monitoring and alerting configured
- [ ] Kill-switch documented and tested
- [ ] Support team trained on escalation and manual resolution
- [ ] 28-day baseline measurement completed

### 3.3 Documentation Updates

**README.md:**
- Changed from "✅ **Production Ready**" to "🔄 **Demo / Integration Pending**"
- Added HR/LMS mock adapter disclosure
- Updated test count to "483 tests passing (mocked-only)" with 389+94 breakdown
- Added "Integration Status" section
- Updated deployment checklist

**Code documentation:**
- HRClient marked as "Mock/Demo Implementation"
- TicketClient uses post_readonly() for bounded read retries
- LoginWorkflow includes detailed docstrings on verification and escalation
- WriteOutcome enum clearly documents SUCCESS / CONFIRMED_FAILURE / UNKNOWN semantics

---

## Part 4: Operating Engineer Approach

### What is it?

Prioritizes solving immediate, high-frequency support issues through:
1. **Bounded automation** — narrow scope, explicit guards, manual escalation
2. **Process improvement** — SOPs, checklists, guided self-service before code changes
3. **Risk minimization** — verify decisions, fail-closed on ambiguity, preserve auditability
4. **Evidence-driven** — solutions only for patterns with clear recurring demand

### Why automate instead of changing deactivation logic?

| Aspect | Code Fix | Automation |
|---|---|---|
| **Risk** | High — changes policy | Low — guards sensitive decisions |
| **Approval** | Security + business review | Supports existing decisions |
| **Scope** | Global — all login cases | Bounded — verified cases only |
| **Reversibility** | Hard — requires release | Easy — disable flag instantly |
| **Evidence** | Root cause (is 30-day rule intentional?) | Recurring pattern (22 tickets) |
| **Time** | 2–4 weeks | 1–2 weeks |

**Decision:** Automate symptoms now, investigate root cause later, implement code changes only with full context.

### When to automate (safely)

- High-frequency, repeatable request (clear pattern)
- Idempotent operation (running twice = running once)
- Verified authorization (policy, approver, identity checks in place)
- Fail-closed behavior (ambiguity escalates; never silently discard)
- Measurable outcome (can verify automation worked)

---

## Part 5: Key Metrics & Evidence

### Week 5 Deliverables Completed

| Deliverable | Status | Location |
|---|---|---|
| Recurring issue analysis (131 tickets) | ✅ | reporting/analysis/recurring-issues.md |
| Pattern analysis with boundaries | ✅ | reporting/analysis/pattern-analysis.md |
| Top 3 solution options | ✅ | reporting/analysis/recommendations.md |
| Action plan (AP1–AP10) | ✅ | recommendations.md section 5 |
| Login workflow POC | ✅ | srcs/services/login_workflow.py |
| P2 Issue #5 fixes | ✅ | srcs/clients/odoo/base.py, ticket_client.py |
| 389 unit tests | ✅ | tests/units/*.py |
| 94 integration tests | ✅ | tests/integration/*.py |
| Documentation updates | ✅ | README.md |

### Test Results

```
Unit Tests (389):
  - Decision logic and verification: 127
  - State persistence and restart: 89
  - HR/LMS/Odoo client: 173

Integration/E2E Tests (94):
  - Real SQLite scenarios: 45
  - Concurrent-worker protection: 28
  - P2 Issue #4 regressions: 21

Total: 483 tests passing
```

### Metrics NOT Yet Measured

| Metric | Why |
|---|---|
| Support workload reduction | Real APIs not integrated |
| Manual handling time baseline | Training sample lacks worklogs |
| Wrong-account reactivation incidents | 0 in tests; production needs real identity provider |
| Duplicate note/email incidents | 0 in tests; needs production monitoring |
| Auto-resolution rate | Requires production pilot and baseline |

---

## Part 6: Decisions & Trade-Offs

**Decision 1:** Automate + SOP approach vs. code fix
- Trade-off: Requires verification/authorization (adds complexity) vs. addressing root cause (requires approval)
- Why: Automation is reversible and scoped; changing logic is not

**Decision 2:** UNKNOWN outcomes → escalation
- Trade-off: Requires manual intervention vs. hoping retry succeeds without duplicating
- Why: Non-idempotent operations are risky to retry blindly

**Decision 3:** Restart safety via persisted state
- Trade-off: Adds database complexity vs. simpler in-memory state
- Why: Production systems crash; persisted state prevents replaying completed side effects

**Decision 4:** Mock HR/LMS in training
- Trade-off: Can't measure actual impact vs. proven workflow logic
- Why: Real APIs unavailable; mock enables full testing

---

## Part 7: Next Steps

### Immediate (Before Sandbox)
1. Finalize real HR API integration (contract, credentials, endpoint mapping)
2. Finalize real LMS API integration (reactivation endpoint, permission model)
3. Configure Odoo stage mapping
4. Select identity verification provider (SSO, LDAP, MFA)
5. Set up audit logging for reactivation actions
6. Document manual escalation queue workflow

### Before Production
1. 4-week sandbox pilot with approved test accounts
2. Establish 28-day baseline (ticket volume, handling time, escalation rate)
3. Support team training
4. Security and business approval
5. Monitoring and alerting configuration
6. Kill-switch testing

### Parallel Investigations
1. Enrollment triage SOP (checklist, duplicates, capacity rules)
2. Timekeeping SOP (diagnostics, payroll-cutoff escalation)
3. Root-cause analysis for reproducible defects; code fixes only with clear evidence

---

## Conclusion

Week 5 successfully completed both phases:

**Reporting Phase (Days 1–2):**
- Analyzed 131 tickets; identified Top 5 recurring issue families
- Account access (22), enrollment (18), timekeeping (17) are highest-frequency groups
- Documented evidence boundaries and data limitations explicitly
- Produced recommendations with 3 solution options per pattern
- Created action plan (AP1–AP10) with owners, metrics, gates

**Automation Phase (Days 3–4):**
- Implemented Login Issue POC with Operating Engineer approach
- Applied P2 Issue #5 fixes: idempotent retry guards, UNKNOWN escalation, restart safety
- Achieved 483 tests passing (389 unit + 94 integration)
- Updated documentation: mock status disclosed, integration status clear, deployment checklist provided
- Prepared for real HR/LMS integration: abstracted APIs, clear contracts, error handling in place

**Current State:** Demo-ready with all guardrails for production integration. Real HR/LMS credentials, identity verification provider, and sandbox approval are the remaining gates.

**Next Phase:** Real HR/LMS integration + 4-week sandbox pilot + 28-day baseline measurement → production rollout decision.
