# Week 5 — Recurring Issues Register

> **Status:** Source-bounded, subject-based classification for Week 5 training. Figures are auditable against the provided sample, not verified root causes or production incidents.
> This is a proposed revision for review, **not** a statement that the mentor has approved the work.

> **Training data scope (Week 5).** The supplied `docs/plans/week-5/data/sample.xlsx` is a **limited training dataset**. The analyst can inspect the provided export but does **not** have access to its underlying Odoo ticket records, descriptions, worklogs or resolution history. The analysis is therefore deliberately limited to observable subjects, IDs, tags and other fields actually included in the sample. It is **not** an independent audit of live production incidents.
>
> **Evidence convention:** `Observed` = directly in the workbook; `Inferred / provisional` = subject-based categorization that can be reproduced using the attached ID mapping; `Scenario assumption` = specified by Week 5 tasks; `Planned` = proposal for a future real-world deployment; `N/A — not in training dataset` = cannot be calculated with the provided fields. These statuses are not interchangeable. The absence of production-only metrics or Odoo case-level verification is a **documented boundary of this exercise**, not a claim that those values have been measured or verified.

## 1. Source and scope

- Source: [`docs/plans/week-5/data/sample.xlsx`](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx), `Sheet1`.
- Valid records: **131 tickets with both a subject and ticket sequence**. Excluded: one header and 51 non-ticket/structural rows.
- Source fields usable: `Subject`, `Ticket IDs Sequence`, `Tags`, `Priority`.
- Missing from the workbook: reliable affected-user counts, worklogs/handling time, created/closed timestamps, resolution logs, verified root causes.
- Classification artifact: [`ticket_classification.xlsx`](ticket_classification.xlsx), **131 ticket ID → one primary issue family**, with subtype, confidence, and review status.
- The count-based taxonomy is **a new proposed manual classification of titles**, not an existing validated Odoo category scheme. Confidence is recorded at row level. Underlying Odoo descriptions are not available for this exercise, so ambiguous cases remain flagged instead of silently being treated as verified.

## 2. Classification rules

1. **One ticket → exactly one primary issue family.** Assign by the central reported symptom or operational request, not by the product tag alone.
2. **System ≠ issue:** `CRM`, `LMS` and `TMS` tags identify systems, but do not identify root cause. For example, TMS **login** belongs to _Account access_, while TMS **missing timesheet data** belongs to _Timekeeping_.
3. **Split materially different operations:** CRM calling/email defects belong to _Communication/telephony_; financial confirmation belongs to _Payment/transactions_; lead stage changes belong to _CRM lead operations_.
4. **Keep test traffic separate:** identify `Tech test`, `TEST`, CC-test cases as _Test/sample_ and retain them in the reconciliation count of 131.
5. **Insufficient context:** assign _Other/unclear_ rather than inventing a root cause. Mark medium/low-confidence cases for **training-scope manual review** using the supplied row data. If the provided fields do not resolve ambiguity, keep `Other/unclear` or an explicit provisional classification; do not require inaccessible original Odoo descriptions.
6. **Repeated subjects ≠ repeated root cause:** issue families represent observable demand patterns, not diagnoses.

## 3. Proposed frequency ranking of all 131 ticket subjects

This table reconciles **all 131** extracted ticket rows. It uses a provisional taxonomy and includes test/sample records in the denominator.

| Rank | Primary issue family                    | Tickets |   % of 131 | Evidence ticket IDs (examples)    |
| ---: | --------------------------------------- | ------: | ---------: | --------------------------------- |
|    1 | **Account access / provisioning**       |  **22** |      16.8% | `308`, `129`, `294`, `276`, `248` |
|    2 | **Enrollment / class allocation**       |  **18** |      13.7% | `302`, `224`, `201`, `60`, `290`  |
|    3 | **Timekeeping / attendance**            |  **17** |      13.0% | `291`, `239`, `236`, `234`, `232` |
|    4 | **Payment / transactions / orders**     |  **13** |       9.9% | `287`, `278`, `249`, `153`, `305` |
|    5 | **Student records / learning progress** |  **13** |       9.9% | `325`, `296`, `288`, `286`, `280` |
|    6 | Test / sample                           |  **10** |       7.6% | `58`, `310`, `312`, `309`, `138`  |
|    7 | CRM lead operations                     |   **9** |       6.9% | `324`, `315`, `140`, `75`, `203`  |
|    8 | Contract / e-sign / invoice             |   **8** |       6.1% | `157`, `254`, `173`, `63`, `161`  |
|    9 | Other / unclear                         |   **8** |       6.1% | `209`, `206`, `189`, `227`, `207` |
|   10 | Communication / telephony               |   **5** |       3.8% | `275`, `260`, `05`, `318`, `20`   |
|   11 | Booking / facility                      |   **4** |       3.1% | `158`, `179`, `99`, `156`         |
|   12 | Dropout                                 |   **4** |       3.1% | `336`, `335`, `72`, `62`          |
|      | **TOTAL**                               | **131** | **100.0%** |                                   |

**Top five (provisional):** Account access/provisioning (22), Enrollment/class allocation (18), Timekeeping/attendance (17), Payment/transactions/orders (13), Student records/learning progress (13). The last two are **tied**, not strictly ranked by frequency; no unsupported priority claim is made between them.

**Important sampling note:** 10 rows are test/sample tickets. The table above intentionally uses **131** as the denominator so every source record is accounted for. For a business-demand-only view, explicitly exclude these 10 and relabel the denominator **121**; do not silently mix the two baselines. The `Other/unclear` group has 8 tickets that cannot be resolved from available context; this is **an expected data-quality limitation**, not justification to guess.

## 4. Top 3 recurring issue families and important subtypes

| Primary family                         | Examples                                              | Notable subtypes                                                                   | Investigation / escalation boundary                                                                                         |
| -------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Account access / provisioning (22)** | `165`, `162`, `143`, `241`, `253`, `41`, `220`, `308` | Login/locked accounts vs password/credential requests vs account creation/transfer | Identity and HR/authorization checks are required; do not treat all 22 as eligible for LMS auto-reactivation                |
| **Enrollment / class allocation (18)** | `274`, `267`, `224`, `47`, `243`, `246`, `221`        | Student enrollment failures vs class/teacher/schedule/slot requests                | Validate class capacity, enrollment policy, duplication and authorization before changes                                    |
| **Timekeeping / attendance (17)**      | `239`, `236`, `232`, `228`, `234`, `235`, `233`       | Missing timekeeping data vs inability to submit/approve attendance actions         | Determine whether individual permission issue, synchronization fault or widespread outage; escalate backend/system problems |

These are **frequency-based candidate priorities**, not proof that any one subtype has a shared root cause. Under Week 5 instructions, Scenario 1 (Login Automation) is the prescribed automation implementation target; it is **not established by this sample** that 30-day LMS deactivation explains all account-access tickets.

## 5. Evidence and impact metrics

| Dimension                      | Measurable result                             | Limitation                                                                                          |
| ------------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Source ticket volume           | **131 ticket records**                        | No dated reporting window in the sample                                                             |
| Family frequency               | **Counts and shares above**                   | Provisional title-based taxonomy; flag medium/low-confidence cases (underlying records unavailable) |
| Product tag distribution       | Available separately in `pattern-analysis.md` | Tags are not root-cause families                                                                    |
| Priority completeness          | **108/131 (82.4%) blank**                     | Priority is not a reliable proxy for user impact                                                    |
| Users affected                 | **N/A — source does not contain this field**  | One ticket may impact one or many users                                                             |
| Time spent / handling duration | **N/A — source lacks worklogs**               | Do not present 5–10 min scenario estimate as actual measured time                                   |
| MTTR / SLA trends              | **N/A — no reliable timestamps**              | Cannot calculate historical resolution time                                                         |
| Confirmed root cause           | **Unverified**                                | Descriptions, diagnosis and resolution logs not included                                            |
| Automation time saved          | **Not yet measured**                          | Needs manual baseline and a monitored pilot                                                         |

## 6. Audit mapping (131 records)

The companion spreadsheet preserves the row-level ID-to-family mapping. Full IDs by family are included here for an additional quick audit:

- **Account access / provisioning (22):** `308`, `129`, `294`, `276`, `248`, `241`, `237`, `230`, `174`, `172`, `331`, `255`, `220`, `165`, `41`, `265`, `259`, `253`, `162`, `143`, `141`, `137`
- **Enrollment / class allocation (18):** `302`, `224`, `201`, `60`, `290`, `274`, `267`, `210`, `268`, `219`, `54`, `47`, `37`, `39`, `246`, `243`, `221`, `06`
- **Timekeeping / attendance (17):** `291`, `239`, `236`, `234`, `232`, `228`, `218`, `215`, `238`, `231`, `211`, `194`, `152`, `124`, `297`, `235`, `233`
- **Payment / transactions / orders (13):** `287`, `278`, `249`, `153`, `305`, `247`, `226`, `225`, `186`, `135`, `125`, `159`, `134`
- **Student records / learning progress (13):** `325`, `296`, `288`, `286`, `280`, `104`, `222`, `295`, `284`, `269`, `87`, `176`, `101`
- **Test / sample (10):** `58`, `310`, `312`, `309`, `138`, `136`, `57`, `26`, `25`, `19`
- **CRM lead operations (9):** `324`, `315`, `140`, `75`, `203`, `187`, `150`, `46`, `245`
- **Contract / e-sign / invoice (8):** `157`, `254`, `173`, `63`, `161`, `155`, `145`, `42`
- **Other / unclear (8):** `209`, `206`, `189`, `227`, `207`, `175`, `61`, `229`
- **Communication / telephony (5):** `275`, `260`, `05`, `318`, `20`
- **Booking / facility (4):** `158`, `179`, `99`, `156`
- **Dropout (4):** `336`, `335`, `72`, `62`

## 7. Training-scope validation and next use

- Review medium- and low-confidence classifications **within the provided export**; leave unverifiable cases flagged. The original Odoo descriptions are not accessible in this training exercise.
- Keep a record of any reclassifications and recalculate frequency counts; do not claim the preliminary numbers are final.
- Keep `N/A — not in training dataset` for users affected, handling time, creation/resolution timestamps and owner-based performance. Additional Odoo extraction is **outside the available Week 5 training scope**; collecting these fields belongs to a future real-world operational study.
- Use the **top three subject-based, provisional patterns** as input for `recommendations.md`: compare 2–3 solutions within each pattern (effort, expected impact, timeframe, dependencies, security risks), select a short-term and longer-term approach, and state escalation boundaries.
- In `recommendations.md` action plan, add owner, deadline, baseline/metric and target, deliverable/DoD, dependency and measurement window for each action.

## Reference

- [Week 5 Mentor Review — Issue #5](https://github.com/BinhDuonghb/mindx-onb/issues/5)
- [Week 5 tasks](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/tasks.md)
- [Sample ticket export](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx)
