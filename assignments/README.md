# Five-Week Onboarding 

> **AI-assisted engineering · Test-driven development · API integration · Helpdesk operations · Reporting & automation**
>
> This repository documents my five-week MindX onboarding assignments, implementation decisions, test evidence, and reflections. It progresses from learning how to validate AI-generated work to building a training-scoped Odoo helpdesk automation proof of concept (POC).

## At a Glance

| Week | Focus | Main deliverable | Assignment & evidence |
| :-- | :-- | :-- | :-- |
| **01** | AI training, critical thinking, TDD research | Research on TDD, testing levels, CLI testing, and AI validation | [Research](week1/week1.md) · [Brief](docs/plans/week-1/overview.md) |
| **02** | TDD in practice | Python Ticket Manager CLI with JSON storage and automated tests | [Completion report](week2/week2.md) · [CLI](week2/TicketManagerCLI/README.md) · [Reflection](week2/TicketManagerCLI/REFLECTION.md) |
| **03** | Knowledge Base API integration | CLI extended with mock/HTTP KB clients and a Node.js/TypeScript test API | [Completion report](week3/week3.md) · [CLI](week3/TicketManagerCLI/README.md) · [KBService](week3/KBService/README.md) |
| **04** | Odoo ticket handling and communication | Six documented helpdesk scenarios with ticket evidence and reflections | [Scenarios](week4/) · [Brief](docs/plans/week-4/overview.md) |
| **05** | Data-driven operations and automation | Ticket-pattern analysis, improvement plan, and login automation POC | [Completion report](week5/week5.md) · [Reporting](week5/reporting/) · [Automation](week5/automation/README.md) |

**Repository status:** An onboarding/training portfolio, **not a production-ready helpdesk product**. External integrations and evidence are described at their actual level of verification below.

## Learning Journey

```text
Week 1: Understand AI + testing principles
    ↓
Week 2: Apply TDD to a working Python CLI
    ↓
Week 3: Extend the CLI through an API contract (mock → HTTP)
    ↓
Week 4: Practice Odoo helpdesk operations and communication
    ↓
Week 5: Use ticket data to prioritize problems and automate a bounded workflow
```

### Week 1 — AI Training & Critical Thinking

**Objective:** Learn to use AI as a collaborator while retaining responsibility for requirements, architecture, correctness, and validation.

The [research assignment](week1/week1.md) covers:

- **Test-Driven Development (TDD):** Red → Green → Refactor, including trade-offs and limitations.
- **Testing levels:** Unit, integration, and end-to-end (E2E), with examples and when to use each.
- **CLI testing:** Command behavior, argument validation, storage, errors, and test execution.
- **AI-assisted development:** Requirement analysis, generating and reviewing tests, finding test gaps, and validating AI output.
- **Common pitfalls:** Over-testing, weak assertions, testing implementation details, and blindly trusting AI-generated code.

The assignment brief also introduces **Layered Questioning**, **Solution Exploration**, and **Iterative Refinement** as repeatable AI collaboration workflows.

**Takeaway:** A passing response from an AI tool is not evidence of correctness; explicit requirements and meaningful tests provide the verification boundary.

**Read:** [Week 1 research](week1/week1.md) · [Week 1 requirements](docs/plans/week-1/overview.md)

### Week 2 — Ticket Manager CLI (Python + TDD)

**Objective:** Put Week 1's TDD and AI-validation principles into practice by implementing a maintainable CLI application.

**Implemented capabilities:**

- Create, list, show, update, and delete tickets.
- Filter tickets by status, priority, and tags.
- Validate ticket fields and email addresses; handle invalid inputs and missing tickets.
- Persist ticket data in JSON through a separate `DBClient` layer.
- Separate command parsing, ticket services, models, validators, and storage.

The [Week 2 report](week2/week2.md) documents **234 passing tests (90 unit + 144 integration)** in its recorded run, together with Red–Green–Refactor cycles, test isolation, and examples of tests catching AI-generated mistakes. These are **results documented by the assignment**, not a fresh test run performed for this root README.

```bash
cd week2/TicketManagerCLI
python -m venv .venv
# Activate the virtual environment for your operating system
pip install -r requirements.txt
python main.py --help
python main.py create --title "Investigate login issue" --priority high
python main.py list
python -m pytest tests/ -q
```

**Read:** [CLI usage and setup](week2/TicketManagerCLI/README.md) · [Implementation report](week2/week2.md) · [TDD reflection](week2/TicketManagerCLI/REFLECTION.md)

### Week 3 — Knowledge Base Integration

**Objective:** Extend the Week 2 CLI to work against a defined Knowledge Base (KB) API without coupling the command layer to one backend.

**Implemented capabilities:**

- Four KB commands: **`kb search`**, **`kb list`**, **`kb retrieve`**, and **`kb add`**.
- Domain models and a common client contract with swappable **`MockKBClient`** and **`HTTPKBClient`** implementations.
- Environment-based client selection (`KB_CLIENT=mock` or `KB_CLIENT=http`).
- Input validation and behavior-parity testing across mock and HTTP clients.
- A separate **Node.js + Express + TypeScript** KBService, exposing JSON endpoints for search, list, retrieve, and add.
- Automated E2E checks that build/start the local KBService, exercise the CLI/API, and stop the service.

The [Week 3 report](week3/week3.md) includes evidence of **six passing KBService E2E tests**. The KBService uses **in-memory storage** for the training exercise; it is not a production KB datastore.

**Quick start (mock client):**

```bash
cd week3/TicketManagerCLI
pip install -r requirements.txt
python main.py kb search "template"
python main.py kb list --node /templates/email
```

**Run the local HTTP test backend (separate terminal):**

```bash
cd week3/KBService
npm install
npm run build
npm start
# http://localhost:8000
```

Configure `KB_CLIENT=http` and `KB_API_URL=http://localhost:8000` in the CLI environment to switch to the HTTP client; see the [setup guide](week3/TicketManagerCLI/README.md#setup).

**Read:** [Week 3 report](week3/week3.md) · [CLI reference](week3/TicketManagerCLI/README.md) · [KBService API](week3/KBService/README.md) · [API contract](docs/plans/week-3/architecture.md)

### Week 4 — Odoo Helpdesk Operations & Communication

**Objective:** Practice the Operating Engineer role through ticket triage, Class of Service, escalation, customer communication, and follow-up.

The Week 4 framework uses seven stages: **Reception → Response → Diagnosis → Resolution → Updates/Communication → Follow-up → Analysis**. Each submitted scenario includes Odoo ticket evidence, communication artifacts, and a reflection.

| Scenario | Exercise | Main lesson | Submission |
| :-- | :-- | :-- | :-- |
| 01 | LMS login issue (**Standard**) | Verify account context and confirm with the requester before closing | [Evidence & reflection](week4/scenario-01/) |
| 02 | LMS performance degradation (**Priority**) | Investigate before escalating; provide useful evidence and updates | [Evidence & reflection](week4/scenario-02/) |
| 03 | Assignment submission outage (**Expedite**) | Coordinate urgent response, workaround, and post-fix verification | [Evidence & reflection](week4/scenario-03/) |
| 04 | Weekly progress report feature request | Separate support from product feedback; manage expectations | [Evidence & reflection](week4/scenario-04/) |
| 05 | Video playback issue affecting 12 learners (**Priority**) | Correlate reports, investigate multiple possible causes, synchronize communication | [Evidence & reflection](week4/scenario-05/) |
| 06 | Enrollment report with a hard deadline (**Fixed Deadline**) | Negotiate scope, minimum deliverable, and delivery risk | [Evidence & reflection](week4/scenario-06/) |

**Deliverables:** Six ticket exports (`.pdf`), communication screenshots (`.png`), and six `Reflection.md` files. These are training scenario artifacts, not a claim of intervention in a live production incident.

**Read:** [Week 4 requirements](docs/plans/week-4/tasks.md) · [7-step process and Class of Service](docs/plans/week-4/overview.md) · [Scenario reflections](week4/)

### Week 5 — Reporting, Pattern Analysis & Login Automation

**Objective:** Use ticket evidence to identify recurring requests, compare intervention options, and implement a narrowly scoped automation for Scenario 1 (login/account reactivation).

#### Part A: Reporting & evidence-based analysis

The reporting submission contains Odoo report exports and evidence for **daily ticket summaries**, **team performance**, **category analysis**, **ticket-volume trends**, and a configured scheduled-report workflow.

The provided training workbook supports a **provisional classification of 131 ticket subjects** into one primary issue family per record. The highest-frequency families are:

| Issue family (provisional) | Tickets | Share of 131 |
| :-- | --: | --: |
| Account access / provisioning | **22** | 16.8% |
| Enrollment / class allocation | **18** | 13.7% |
| Timekeeping / attendance | **17** | 13.0% |
| Payment / transactions / orders | **13** | 9.9% |
| Student records / learning progress | **13** | 9.9% |

Payment and student records are tied by frequency. The 131-record reconciliation also flags **10 test/sample tickets** and **8 Other/unclear records**. This is **subject-based issue categorization, not verified root-cause analysis**. The workbook does not provide reliable affected-user counts, worklogs, or MTTR, so those metrics are recorded as **N/A**, not invented.

For the Top 3 families, the [recommendations](week5/reporting/analysis/recommendations.md) compare **SOP/self-service**, **bounded automation**, and **root-cause/process fixes**, including risks, effort, dependencies, and trade-offs. They also define **AP1–AP10** as *proposed* actions with owners, dates, targets/measurement windows, and acceptance criteria—not claims that all actions have been deployed.

**Explore:** [Ticket-level classification](week5/reporting/analysis/ticket_classification.xlsx) · [Pattern analysis](week5/reporting/analysis/pattern-analysis.md) · [Recurring issues](week5/reporting/analysis/recurring-issues.md) · [Recommendations and action plan](week5/reporting/analysis/recommendations.md) · [Reports](week5/reporting/reports/) · [Scheduler evidence](week5/reporting/evidences/)

#### Part B: Login Issue Automation POC

The automation covers the Week 5 prescribed login scenario, not every ticket in the account-access category.

```text
Odoo Helpdesk tickets (polling)
            │
            ▼
TicketAnalyzer → HR/employee lookup → DecisionService / identity gate
                                          │
                     ┌────────────────────┴───────────────────┐
                     ▼                                        ▼
          Eligible + verified                       Ineligible / unverified
                     │                                        │
            LMS reactivation                          Manual review / note
              (JSON mock)                                    │
                     └────────────────────┬───────────────────┘
                                          ▼
                                Odoo note/stage + email
                                          │
                                          ▼
                            SQLite side-effect state & retry
```

The Python implementation combines **Odoo JSON-2 API integration**, ticket analysis, deterministic decisions, an **HR/LMS JSON mock**, Gmail SMTP support, and SQLite state persistence. Reliability and safety mechanisms include:

- Fingerprint-based work detection; atomic `PROCESSING` claims with lease ownership.
- Durable tracking of authorization and completed side effects to resume **only authorized** partial workflows.
- Retry scheduling and email-delivery tracking without rerunning confirmed LMS actions.
- Fail-closed identity verification when no trusted proof is available.
- Safe handling of ambiguous Odoo write outcomes (`UNKNOWN`); avoid blind `message_post` replay and duplicate notes.
- Configurable non-terminal Odoo stage mapping so a ticket is not assumed to be **Done** before customer confirmation.

**Scope and safety:** HR/LMS operations and identity-provider verification are simulated or pending real integration. The default POC verifier does not authorize real account reactivation solely on matching email. Successful authorization branches can be exercised with explicit test doubles in isolated tests. A real deployment requires approved identity/permission checks, verified Odoo stage IDs, backend contracts, and operational controls.

**Test evidence recorded for the Week 5 automation snapshot:**

| Test scope | Recorded result | Interpretation |
| :-- | :-- | :-- |
| Unit + offline integration suites (`tests/units/`, `tests/integration/`, `tests/integrations/`) | **494 passed** | Independently checked in a prior offline review; no real external-service calls intended |
| Full local suite (`tests/`, including `tests/e2e/`) | **518 passed in 33.27s** | Developer-reported run; E2E may require a dedicated authorized Odoo test instance |

These counts are a **snapshot, not a permanent project guarantee or production-readiness claim**. The Week 5 completion report contains an older test count; use the more recent [automation README](week5/automation/README.md#running-tests) for test commands and caveats.

```bash
cd week5/automation
pip install -r requirements.txt
# Configure TEST_ODOO_* with safe test values for offline pytest collection.
python -m pytest tests/units/ tests/integration/ tests/integrations/ -q --tb=short
```

**Do not run the live polling/one-time automation against a production Odoo instance or real user accounts without authorization and the required verification and stage settings.** Follow the [automation README](week5/automation/README.md) for full setup and the distinction between demo, sandbox, and production.

**Read:** [Week 5 report](week5/week5.md) · [Automation setup, architecture and tests](week5/automation/README.md) · [Reporting analysis](week5/reporting/analysis/) · [Week 5 task brief](docs/plans/week-5/tasks.md) · [Mentor review](https://github.com/BinhDuonghb/mindx-onb/issues/5)

## Repository Guide

```text
mindx-onb/
├── README.md                         # Five-week portfolio overview (this file)
├── docs/plans/
│   ├── week-1/                      # Objectives and research requirements
│   ├── week-2/                      # CLI/TDD requirements
│   ├── week-3/                      # KB API contract and integration plan
│   ├── week-4/                      # Operational framework and 6 scenario briefs
│   └── week-5/                      # Reporting and automation requirements + sample data
└── assignments/
    ├── week1/week1.md              # TDD and AI-assisted testing research
    ├── week2/
    │   ├── week2.md                 # Implementation report
    │   └── TicketManagerCLI/       # CLI source, tests and reflection
    ├── week3/
    │   ├── week3.md                 # Integration report
    │   ├── TicketManagerCLI/       # Ticket + KB CLI and Python tests
    │   └── KBService/              # Express/TypeScript test API
    ├── week4/scenario-01..06/      # Odoo ticket evidence and reflections
    └── week5/
        ├── week5.md                 # Assignment report
        ├── reporting/              # Analysis, report exports, scheduler evidence
        └── automation/             # Python login automation, SQLite, tests and docs
```

## Technologies & Practices

| Area | Tools / concepts used |
| :-- | :-- |
| Development & testing | Python, `argparse`, `pytest`, TDD, fixtures, unit/integration/E2E tests |
| API integration | HTTP/JSON, mock vs. real client contracts, Node.js, TypeScript, Express |
| Helpdesk operations | Odoo Helpdesk, Class of Service, incident escalation, professional communication |
| Reporting | Odoo reporting/export, Excel analysis, ticket classification and action planning |
| Automation | Odoo JSON-2, simulated HR/LMS, Gmail SMTP, SQLite, polling, lease ownership, safe retries |
| Engineering approach | AI-assisted development with human review, evidence-based decisions, failure-mode analysis, explicit security boundaries |

## Key Lessons

1. **Validate AI-generated work:** Write behavior-oriented tests, inspect edge cases, and review assumptions rather than equating generated code with correct code.
2. **Design against contracts:** Mock and HTTP implementations should agree on validation, behavior, and errors.
3. **Treat support as a process:** Correct technical actions must be paired with prioritization, documentation, timely updates, and confirmation.
4. **Respect data limitations:** Do not convert ticket subjects or scenario estimates into unverified root causes, savings, or business KPIs.
5. **Make automation safe to retry:** Persist authorization and side-effect progress, guard non-idempotent writes, and escalate uncertain outcomes instead of guessing.

---

**Reference:** [Assignment briefs](docs/plans/) 

*This README summarizes evidence and implementation present in the repository; it does not claim formal mentor approval, production deployment, or validation of unavailable external data.*
