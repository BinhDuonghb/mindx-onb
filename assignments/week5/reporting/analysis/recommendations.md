# Week 5 — Recommendations, Solution Exploration & Action Plan

> **Status:** Revised draft for mentor review; **not** an approved production rollout plan.  
> **Scope:** Training-scoped reporting analysis and Operating Engineer decision for Week 5.  
> **Primary evidence:** `docs/plans/week-5/data/sample.xlsx` (`Sheet1`), the Week 5 task brief, and mentor Issue #5.  
> **Classification dependency:** Figures below follow the **provisional subject-based** 131-ticket mapping in `ticket_classification.xlsx`. Publish that mapping alongside the report and synchronize `recurring-issues.md` and `pattern-analysis.md`. Cases with insufficient context are explicitly flagged; **the original Odoo ticket details are not accessible within this training assignment**, so live-record verification is not a submission prerequisite.

> **Training data scope (Week 5).** The supplied `docs/plans/week-5/data/sample.xlsx` is a **limited training dataset**. The analyst can inspect the provided export but does **not** have access to its underlying Odoo ticket records, descriptions, worklogs or resolution history. The analysis is therefore deliberately limited to observable subjects, IDs, tags and other fields actually included in the sample. It is **not** an independent audit of live production incidents.
>
> **Evidence convention:** `Observed` = directly in the workbook; `Inferred / provisional` = subject-based categorization that can be reproduced using the attached ID mapping; `Scenario assumption` = specified by Week 5 tasks; `Planned` = proposal for a future real-world deployment; `N/A — not in training dataset` = cannot be calculated with the provided fields. These statuses are not interchangeable. The absence of production-only metrics or Odoo case-level verification is a **documented boundary of this exercise**, not a claim that those values have been measured or verified.

## 1. Executive decision

**Proceed with a restricted proof of concept (POC) for Scenario 1 — Login/Account Reactivation**, as explicitly required by Week 5. Only an independently authenticated requester with a verified active employee record, a confirmed eligible LMS deactivation state, and an approved access policy can be considered for automatic reactivation. Password resets, account creation/transfers, terminated employees, or uncertain identity are separate cases and must not be auto-reactivated by this workflow.

For the other high-frequency categories, **start with structured SOPs, validated triage and evidence collection**, then consider automation or a code-level fix when root cause, approval rules and real operational metrics are established. A faster ticket resolution does **not**, by itself, demonstrate fewer incoming tickets.

## 2. Evidence, ranking and limitations

### 2.1 Ticket classification basis

The original export contains **131 records** with a ticket sequence and subject after excluding the header and non-ticket/grouping rows. Every record has one proposed `Primary Issue Family`, based on its reported symptom/request rather than product tags such as `CRM`, `LMS` or `TMS`. Overlapping systems may be recorded separately; a ticket counts only once in the primary-family ranking.

| Provisional rank | Primary issue family | Tickets | Share of all 131 | Illustrative ticket IDs |
|---:|---|---:|---:|---|
| 1 | Account access / provisioning | **22** | **16.8%** | `165`, `162`, `143`, `241`, `253`, `41`, `220`, `308` |
| 2 | Enrollment / class allocation | **18** | **13.7%** | `274`, `267`, `224`, `47`, `243`, `246`, `221` |
| 3 | Timekeeping / attendance | **17** | **13.0%** | `239`, `236`, `232`, `228`, `234`, `235`, `233` |
| 4 (tie) | Payment / transactions / orders | **13** | **9.9%** | `287`, `278`, `249`, `226`, `225` |
| 4 (tie) | Student records / learning progress | **13** | **9.9%** | `288`, `286`, `101`, `295`, `269` |

The entire draft mapping reconciles **131/131** records, including **10 test/sample tickets** and **8 Other/Unclear tickets**. These are not hidden: the business-demand-only denominator would be **121**, not 131, after excluding the 10 test/sample rows. The Top 3 and counts are **reproducible subject-based estimates**, not verified operational root-cause statistics. Low-confidence titles remain flagged; additional Odoo verification is outside the available training scope. There is **no evidence that all 22 account-access tickets are 30-day-inactive LMS cases**. Week 5 prescribes Scenario 1 as the implementation exercise; it is not proved to be the most common root cause.

### 2.2 Observed evidence vs planning assumptions

| Statement | Evidence status | Implication |
|---|---|---|
| Related access, enrollment and timekeeping ticket subjects recur | **Observed** (subject/ID) | Supports prioritizing investigation, not verified shared root causes |
| Family counts 22 / 18 / 17 | **Provisional classification** | Mapping is published and ambiguous titles flagged; no underlying Odoo details are available for verification |
| LMS deactivates after 30 days of inactivity | **Week 5 scenario assumption** | Confirm business/security policy; not inferred from sample |
| Manual reactivation takes 5–10 minutes | **Scenario estimate**, not measured | Do not use as actual baseline or savings claim |
| HR/LMS APIs and authorized identity verification are available | **Unverified integration dependency** | Mock adapter is not proof of live integration |
| Support workload or incoming ticket volume will decline | **Hypothesis** | Requires pilot and comparable before/after data |

### 2.3 Impact metrics available from the source

| Metric | Result | Reason / follow-up |
|---|---|---|
| Tickets in analyzed export | 131 | Source is not a defined daily/weekly reporting period |
| Frequency by proposed issue family | Provisional count and share above | Provide row-level mapping and flag uncertain titles; additional source data not available in this exercise |
| Users affected | **N/A — source does not contain field** | N/A for this exercise; collect only in a future authorized operational study |
| Time spent / manual handling time | **N/A — source lacks worklogs** | N/A for this exercise; measure prospectively only in a future authorized pilot |
| MTTR and daily/weekly trend | **N/A — no creation/close timestamps** | N/A for this exercise; do not extrapolate from undated training sample |
| Confirmed root causes | **Unverified** | Cannot verify without underlying Odoo records; treat as unknown |

**Important:** Existing Odoo daily, team, category and trend reports are separate deliverables. Their provenance, reporting dates, filters and whether data are real or demonstration data should be documented separately when existing artifacts show them; this 131-ticket workbook alone cannot validate their time trends or productivity measures. The scheduled export requires evidence of **frequency/time, report destination/format and successful delivery**, not a separate cron script when configured through Odoo.

### 2.4 What can and cannot be concluded in this training exercise

- **Can complete now:** reproduce the 131-row sample scope; assign a primary issue family and confidence to every ID; calculate sample-level group counts and percentages; describe observed patterns; compare options and produce a proposed action plan.
- **Cannot validate from the supplied source:** actual number of affected people, staff handling minutes, root causes, incident dates, production trends, or the effectiveness of a deployed automation. These are **N/A / unverified**, not missing calculations.
- **Do not conflate artifacts:** separate Odoo reporting/export practice (which may use another training environment) from the historical records behind `sample.xlsx`. A screenshot of a scheduled report does not provide missing columns for the 131-ticket sample.
- **Review standard:** judge conclusions against the **evidence actually accessible in the training assignment**; treat any production-oriented data collection or pilot measurement as an actionable *future plan*, not a claim of present access.

## 3. Solution Exploration — Top 3 priority patterns

**Comparison method.** For each family, consider three options: low-risk SOP/self-service, bounded automation/process improvement, and an investigated code/root-cause solution. `Effort`, `timeframe` and `expected impact` below are **qualitative engineering estimates or illustrative planning ranges**, not observed KPI results or committed deadlines. Final choice depends on approval, root-cause evidence and staff capacity.

### 3.1 Pattern A — Account access / provisioning (22 provisional tickets)

**Problem evidence:** Internal login problems (`165`, `162`), CRM login (`143`), TMS access/login (`241`, `253`), LMS password help (`41`), ECOUNT locked account (`220`), and account provisioning (`308`) show distinct subtypes. Treating all as one LMS reactivation root cause would be unsafe.

| Option | Effort / illustrative timeframe | Expected impact (hypothesis) | Dependencies | Main risk / trade-off |
|---|---|---|---|---|
| **A1. Identity-verified SOP and self-service guidance** | Low; ~1–3 workdays for draft and review | Reduce avoidable support contacts for common password guidance; standardize manual cases | Approved identity/reset policy, KB editor, Support owner | May only shift effort to requester; no automatic resolution |
| **A2. Bounded LMS reactivation POC (Week 5 selected)** | Medium; estimate only after P1 fixes and sandbox access | Reduce manual actions and resolution delay **for eligible 30-day deactivation cases** | Verified identity, HR/LMS contract, authorization, Odoo mapping, reliable retry/outbox, tests | Wrong-account access, duplicate side effects or misleading completion if controls fail |
| **A3. Investigate deactivation logic / access policy (Dev fix)** | Medium–High / unknown pending analysis | Potentially reduce *recurrence* if unintended behavior is proven | Security/business policy owner, Dev, regression tests, release approval | Changing intentional inactivity control may increase access risk |

**Decision:** **Short term:** A1 for all relevant subtypes and A2 **only in mock/sandbox** for verified Scenario 1 cases. **Long term:** assess A3 with Security and Dev before proposing production changes. The 30-day rule may be intentional; removing it is not an automatic recommendation.

**Subtype boundaries:**
- **Login/locked account:** establish requester identity, HR eligibility and confirmed lock/deactivation cause; only the explicitly approved LMS deactivation case can use A2.
- **Forgotten password:** use approved password-reset/SSO process; never email passwords or silently treat it as account reactivation.
- **New account/transfer/provisioning:** require explicit entitlement and approver; route through account-administration workflow.
- **Terminated/on leave, HR mismatch, account already active, system-wide auth outage, missing identity evidence:** no mutation; add Odoo note and route to Support/Security/Dev as applicable. A requester-email match alone is insufficient identity verification.

### 3.2 Pattern B — Enrollment / class allocation (18 provisional tickets)

**Problem evidence:** Repeated inability to enroll students (`274`, `267`, `224`, `47`, `243`, `246`) plus class/teacher/schedule/slot requests. Duplicate enrollment, full capacity and permissions are **possible causes**, not verified diagnoses.

| Option | Effort / illustrative timeframe | Expected impact (hypothesis) | Dependencies | Main risk / trade-off |
|---|---|---|---|---|
| **B1. Enrollment SOP + structured ticket form / checklist** | Low; ~2–4 workdays for review and training | Faster, more consistent initial triage; fewer requests for missing information | Support & academic-ops policy, required class/student fields | Still manual; incorrect checklist may delay complex cases |
| **B2. Read-only eligibility checks and guided self-service** | Medium; ~1–2 weeks POC subject to API access | Reduce repeatable validation effort and prevent some invalid requests | LMS/class read APIs, documented enrollment rules, permission model | Outdated schedule/capacity data could mislead; write access not approved |
| **B3. Root-cause fix for reproducible enrollment defects** | Unknown; depends on diagnostic findings | Reduce incident recurrence **if** a defect is established | Dev owner, logs, reproduction steps, test environment | A code change without confirmed diagnosis can introduce enrollment errors |

**Decision:** **Short term:** B1. Explore **read-only** B2 after policy and data checks. **Long term:** B3 only for reproducible, repeatedly evidenced defects; do not auto-enroll students without approval.

**Subtype boundaries:**
- **Cannot enroll / missing slot / class lookup:** verify student/class identifiers, class status, capacity and eligibility before any change.
- **Duplicate enrollment:** check existing enrollment, do not create another registration automatically.
- **Teacher allocation / timetable changes:** require academic-ops ownership and class scheduling approval.
- **Escalate:** repeated failures across classes, inconsistent LMS database state, required privileged correction or unavailable classroom capacity despite valid rules → LMS Dev/Academic Operations.

### 3.3 Pattern C — Timekeeping / attendance (17 provisional tickets)

**Problem evidence:** Missing TMS information (`239`, `236`), missing timesheet/approval entries (`232`, `228`), similar recurring region-wide symptoms (`233`, `234`), and individual timesheet actions. These may be separate issues, not one common outage.

| Option | Effort / illustrative timeframe | Expected impact (hypothesis) | Dependencies | Main risk / trade-off |
|---|---|---|---|---|
| **C1. Diagnostic SOP and payroll-cutoff escalation rules** | Low; ~2–3 workdays for draft/approval | Faster triage and correct urgency handling | HR Ops, Support, payroll calendar, escalation contacts | Still requires manual investigation |
| **C2. Read-only TMS health checks / synchronization alerts** | Medium; ~1–2 weeks POC when access exists | Earlier detection of shared faults; fewer repetitive checks | Monitoring/API/log access, alert ownership, privacy controls | False positives/alert fatigue; detection alone does not fix the issue |
| **C3. Investigate and fix validated sync/database defects** | Unknown, potentially high | Reduce repeat incidents after cause is confirmed | TMS Dev/DB, HR data owner, reproducible logs and tests | Data integrity/payroll risk; incorrect automated reconciliation can be harmful |

**Decision:** **Short term:** C1 with a time-sensitive escalation path; consider **read-only** C2. **Long term:** C3 if diagnostics establish a repeatable synchronization/backend defect. No automated timesheet or payroll data modification is proposed in this assignment.

**Subtype boundaries:**
- **Cannot view timekeeping data:** distinguish permission/UI display from verified missing backend data.
- **Cannot submit or approve entries:** check role, deadline and current state; escalate policy or authorization blockers to HR Ops.
- **Multiple affected users, recurring timeouts, possible database/sync fault, payroll deadline at risk:** escalate promptly to TMS Dev/HR Ops, provide ticket IDs, impact, logs and timestamps. Do not bypass approvals or change attendance records blindly.

### 3.4 Prioritization rationale and cross-pattern decision

Frequency identifies **where investigation may have value**, not what is safe to automate. Account-access requests are provisionally first (22/131), but the selected *LMS 30-day deactivation* subtype is only a subset that the export does not quantify. Enrollment and TMS may require different domain owners, and unsafe write actions are deliberately excluded. **Only Scenario 1 Login Automation is implemented as the Week 5 exercise; the other options are proposed decisions, not completed implementations.**

## 4. Week 5 Scenario 1 — proposed workflow and safe boundaries

```text
Odoo new/updated ticket (polling or approved webhook)
  -> Record ticket ID + classification + idempotency key
  -> Not an eligible login subtype / unclear request? -> manual triage
  -> Independently verify requester identity and authorization
  -> HR lookup -> terminated/on leave/not found/mismatch? -> fail closed + manual review
  -> Check LMS state, deactivation reason, and policy approval
  -> Eligible 30-day inactive LMS account? -> reactivate once
       -> Verify LMS outcome
       -> Persist pending Odoo note/stage and email actions
       -> Retry only outstanding effects with idempotency guards
       -> Notify requester; mark technical fix awaiting confirmation
  -> Account active for other reason / API uncertain? -> diagnose or escalate
  -> Close only when Odoo stage semantics and approved confirmation policy permit
```

The implementation in Week 5 remains a **training/demo workflow** until live identity, HR/LMS APIs and Odoo-stage configuration are validated. Partial retries, processing lease claims, and durable email delivery are explicit P1 prerequisites from mentor Issue #5; this document does **not** assert they have already been fixed. If Odoo returns an ambiguous failure after a write, check whether the note/action occurred before issuing another non-idempotent POST.

## 5. Action Plan — accountable, testable, and measurable

**Planning convention:** Owners below are **proposed roles**, not confirmed assignees. Relative deadlines are **proposed planning milestones after kickoff**, not actual work completion dates. Where historical baselines are absent, targets are defined as evidence/completion gates or marked **TBD after baseline collection**; do not invent business-impact targets.

| Action | Owner (proposed) | Baseline / Metric & Target | Deadline (proposed) | Deliverable / DoD | Dependency | Measurement window |
|---|---|---|---|---|---|---|
| **AP1. Review and lock 131-ticket taxonomy** | Operating Engineer | Baseline: 131 ticket rows; target: **131/131** with one primary family; all medium/low cases documented | End of week 1 | Mapping workbook, review log, corrected Top 5 frequency/share; 131-row reconciliation | `sample.xlsx` and a documented title-based rule; underlying Odoo descriptions unavailable | One-time historical sample review |
| **AP2. Document impact-data gaps within the training scope** | Support / Odoo Admin | Baseline: affected users, worklogs, timestamps missing in sample; target: explicit **N/A — not in training dataset** for each unavailable field | End of week 1 | Data dictionary, fields, export date/filter; missing-data rationale, no invented measures | Available `sample.xlsx`; no live-record access assumed | One-time training-sample data audit |
| **AP3. Publish account-access SOP and subtype rules** | Support Lead + Security/HR reviewer | Baseline: no approved SOP evidenced in this submission; target: reviewed SOP and triage decision table | End of week 2 | KB/SOP, identity-verification and escalation rules, sample ticket walkthrough | Identity and entitlement policies | Review support cases during pilot |
| **AP4. Validate Login POC in controlled environment** | Operating Engineer + Dev reviewer | Baseline: mock workflow with known P1 defects; target: P1 regression scenarios pass, no unauthorized mutations or duplicate side effects in tests; live KPI TBD | After P1 fixes, identity approval and sandbox readiness | Test run output, partial-retry/lease/email evidence, demo logs and rollback/disable instructions | Agent's P1 fixes, HR/LMS API contract, Odoo stage mapping | POC runs; subsequent monitored pilot only after approval |
| **AP5. Publish enrollment triage SOP** | Academic Ops + Support | Baseline: no verified handling-time baseline; target: approved checklist covering enrollment, duplicates, slots and teacher scheduling | End of week 2 | SOP, owner routing and escalation triggers validated against example cases | Enrollment rules and class ownership | Initial training then 4-week pilot |
| **AP6. Publish TMS triage & cutoff escalation SOP** | HR Ops + Support | Baseline: no validated TMS root-cause baseline; target: approved escalation matrix | End of week 2 | SOP for view, submit, approve, multi-user outage, payroll deadline; sample case review | TMS/HR policies, deadline and on-call owners | Initial training then 4-week pilot |
| **AP7. Instrument pilot and establish comparable baseline** | Support Analyst / Odoo Admin | Baseline: dated operational metrics unavailable in 131-row export; target: capture fields needed for consistent comparison (no arbitrary improvement % yet) | Before pilot | Measurement specification and baseline extract with dates, filters, event/worklog definitions | Odoo timestamps, assigned owner, action logs, issue taxonomy | 28 calendar days before pilot if historical logs available |
| **AP8. Review pilot outcomes and decide go/no-go** | Operating Engineer + Support Lead + Security | Baseline: TBD by AP7; target: report actual success, failures, escalation, reopen, duplicate actions and manual-time change, with safety exceptions reviewed | End of 4-week approved pilot | Before/after report, case audit, risk register and explicit continue/stop decision | AP4–AP7; approved sandbox/live data collection | 28 calendar days after approved pilot start |
| **AP9. Escalate evidenced recurring defects to product Dev owners** | Dev Lead + Domain owner | Baseline: root causes unverified; target: documented reproduction/evidence and decision per selected recurring defect | After AP1 and diagnostic evidence | Issue/decision log with owner, acceptance tests and explicit no-fix rationale if applicable | Case descriptions, system logs, security/business policies | At triage and subsequent release monitoring |
| **AP10. Verify Odoo reporting/export evidence** | Support / Odoo Admin | Baseline: report artefacts submitted; scheduled run details not independently verified | Before mentor resubmission | README/evidence index showing source, filters, report period and any available schedule frequency/time, format/destination, delivered export; note any unverified setting | Existing screenshots/PDF/XLSX; training Odoo access if available | Dated schedule execution evidence |

**Do not combine unrelated actions:** writing a KB, developing a POC, and changing an Odoo form are separate, independently reviewable outputs. AP3/AP5/AP6 are proposals, not claims that those SOPs already exist.

## 6. Measurement: how to tell whether the intervention works

### 6.1 Comparison design

1. Use the **same category taxonomy**, ticket creation channel, and inclusion/exclusion rules in baseline and pilot. Separate operational tickets from test/sample records.
2. Compare **28 days before** versus **28 days after** an approved pilot when reliable dated records exist; if no pre-pilot worklogs are available, **do not backfill invented values**—state that the first pilot period establishes a prospective baseline.
3. Report both **incoming volume per family** (demand) and **manual handling time per ticket** (efficiency). They measure different outcomes.
4. Stratify LMS access issues by subtype/eligibility and exclude non-login access cases from automatic resolution denominators.
5. Check seasonal/operational events (school calendar, payroll cutoff, changes in ticket creation) before attributing trends to automation.

### 6.2 Operational metrics and formulas

| KPI | Definition | Data required | Interpretation |
|---|---|---|---|
| Incoming ticket volume | Count of created **non-test** tickets per issue family in the period | Created timestamp, category, test flag | Demand; **automation alone may not reduce it** |
| Auto-resolution rate | Auto-resolved eligible tickets / eligible tickets * 100% | Eligibility decision, confirmed outcome | Efficiency/coverage of bounded automation |
| Manual intervention rate | Eligible tickets requiring a human action / eligible tickets * 100% | Action audit, eligibility | Manual load, including escalations |
| Manual handling time | Sum of measured human work minutes / relevant tickets (also report median) | Worklogs or timed handling | Direct labor efficiency; **N/A** until captured |
| Escalation rate | Escalated cases / cases in measured scope * 100% | Escalation event, scope | Safety/triage pattern, not automatically failure |
| Reopen rate | Reopened resolved tickets / resolved tickets in a defined follow-up window * 100% | Resolution, reopen timestamps | Sustainability; use consistent 7-day observation window if supported |
| Delivery success | Confirmed delivered or accepted notifications / attempted notifications * 100% | Outbox ID, provider response/status | Communication reliability; distinguish queued vs delivered |
| Safety incidents / duplicate effects | Count of wrong-account actions and confirmed duplicate mutations/notes/emails | Audited identity/action IDs, incident review | Safety gate; investigate **any** occurrence |

**No numeric business improvement target is claimed** before AP7 establishes a usable baseline. Savings in hours, cost, SLA improvement and ticket reduction must be calculated from actual observations, not the Week 5 scenario estimate of 5–10 minutes.

## 7. POC → sandbox → production: operational safety gates

| Stage | Allowed activity | Gate to proceed |
|---|---|---|
| **POC / mock** | Simulate HR/LMS/Odoo/email actions; test decision branches and failures | Run unit/integration tests including all three P1 regressions; document test environment |
| **Sandbox / dry-run** | Use approved non-production accounts; read-only/dry-run first, then tightly authorized test writes | Written identity/entitlement rules, service-account permissions, Odoo stage mapping, audit logs, fail-closed and stop switch |
| **Production (not claimed)** | Only after owner approval and an explicit rollout plan | Validated real APIs, security/privacy review, incident escalation, monitored retries/idempotency and verified customer confirmation policy |

**Mandatory controls before account writes:** requester authentication beyond email equality; HR and LMS eligibility checks; least-privilege credentials; no passwords in email/logs; durable state for reactivation, Odoo note/stage and email; processing lease/concurrency protection; idempotent retries including ambiguous Odoo POST responses; retry limit, alert/manual escalation, audit trail, safe disable switch and stage mapping confirmed against Odoo configuration. An environment variable named `development` does **not** prove that a dry-run exists.

**Communication:** acknowledgement/update/resolution are aligned with Week 4. A technically successful reactivation can be marked *awaiting requester confirmation*; do not assume sending an email is the same as receiving confirmation. If customer contact is missing, queue manual review rather than silently discard the case.

## 8. Submission evidence and unresolved dependencies

**Training-scoped submission evidence (not proof of live operations):**
- Ticket classification workbook (131 records), explicit confidence/uncertainty flags, and **sample-based** Top 5 in `recurring-issues.md`. No claim of independently verified root causes.
- Source and impact limitations in `pattern-analysis.md`; Odoo report provenance and scheduled-export evidence (screenshots/exports already submitted; verify schedule details).
- This file's three comparison tables, subtype/escalation decisions, AP1–AP10 plan, 28-day measurement method and rollout gates.
- Automation P1 fix evidence, actual pytest output and mock-vs-real integration disclaimer from the separately developed automation code/README.

**Remaining limits due to training scope:** classifications are reproducible but subject-based, and the original Odoo tickets are unavailable. The 131-ticket export has no reliable worklogs, affected-user field or comparable dated trend data; live HR/LMS integration and successful P1 regressions have not been verified in this reporting document. These are **explicit boundaries of the training dataset and dependencies of any future production rollout**, not deficiencies to conceal with invented data.

## References

- [Week 5 overview](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/overview.md)
- [Week 5 tasks](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/tasks.md)
- [Mentor Week 5 review — Issue #5](https://github.com/BinhDuonghb/mindx-onb/issues/5)
- [Sample workbook](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx)
- [Recurring issues](recurring-issues.md)
- [Pattern analysis](pattern-analysis.md)
