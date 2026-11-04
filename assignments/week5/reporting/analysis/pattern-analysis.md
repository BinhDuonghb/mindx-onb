# Week 5 — Pattern Analysis

## 1. Objective
Identify recurring support issues from the Week 5 training workbook and distinguish observed patterns from unverified root causes, to inform an Operating Engineer automation decision.

## 2. Source and scope
- Source: [`docs/plans/week-5/data/sample.xlsx`](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx), `Sheet1`, `master` branch (retrieved 4 November 2026).
- Workbook contains **183 populated worksheet rows**, including **1 header**, **131 rows with both a ticket sequence and a subject**, and **51 non-ticket/group or formatting rows**. Thus the analyzable subject-bearing ticket sample is **131**, **not 182**.
- The 24 exported column headings are: Active, Activities, Activity State, Helpdesk Team, Customer Ratings, Rating count, Average Rating, Folded in Kanban, SLA Policies, Color Index, Subject, Ticket IDs Sequence, Commercial Entity, Tags, SLA Deadline, Properties, Priority, Activity Exception Decoration, Icon, Next Activity Summary, Activity Type Icon, Next Activity Type, Assigned to, Kanban State.
- Relevant fields: **Subject (K)**, **Ticket IDs Sequence (L)**, **Tags (N)**, **Priority (Q)**. `Assigned to (W)` is blank on the 131 extracted ticket rows. Some cell values (including numeric-looking tags) are not self-explanatory in the export.
- Important limitations: there are **no explicit created/closed timestamps, resolution durations, worklogs, resolution notes, number of users affected, or reliable root-cause fields** among the exported headings. Consequently daily volume trends, true team performance, mean handling time, and affected-user counts **cannot be calculated from this workbook alone**.

## 3. Method
1. Read the header and isolate actual ticket records using a populated ticket sequence **and** subject. Exclude 51 structural/group rows rather than treating them as tickets.
2. Inspect raw **Tags** distribution and **Subject** text. Keep raw tag frequencies separate from thematic issue classification: a product tag such as CRM is not an incident root cause.
3. Group similar subjects into provisional problem families (e.g., LMS enrollment, TMS timesheets/attendance, CRM transactions, account access, student data corrections). Include ticket IDs as traceable evidence.
4. Identify identical or near-identical titles as direct evidence of repetition. Do **not** assume identical symptoms imply identical root causes or solutions.
5. Evaluate potential automation only after considering whether a safe, reproducible resolution procedure and required integration/authorization exist.

## 4. Data profiling — observed results

### Tag values on the 131 extracted ticket records

| Raw exported tag value | Tickets | Share of 131 | Interpretation |
|---|---:|---:|---|
| `31` | 24 | 18.3% | Numeric-like export value; definition not confirmed |
| `CRM` | 23 | 17.6% | System/product tag, not a specific issue |
| `44` | 21 | 16.0% | Numeric-like export value; definition not confirmed |
| `LMS` | 14 | 10.7% | System/product tag |
| `TMS` | 9 | 6.9% | System/product tag |
| `307` | 7 | 5.3% | Numeric-like export value; definition not confirmed |
| `62` | 6 | 4.6% | Numeric-like export value; definition not confirmed |
| `Awaiting information` | 5 | 3.8% | Workflow tag, not an issue type |
| Other tag values | 22 | 16.8% | Remaining values combined |

**Caution:** These are raw single-cell tag values as exported, not validated mutually exclusive incident categories. Numeric-looking values must be decoded/verified before interpreting them as business categories.

### Priority field completeness

| Exported priority | Records |
|---|---:|
| Blank | 108 |
| Urgent | 13 |
| High priority | 3 |
| Medium priority | 1 |
| Low priority | 6 |
| **Total** | **131** |

The high blank rate (**108/131 = 82.4%**) limits any priority-based impact analysis.

## 5. Qualitative patterns supported by subjects

| Candidate family | Subject evidence (ticket sequence IDs) | What can be concluded |
|---|---|---|
| Enrollment/class allocation | `274` and `267` both use **KHÔNG THỂ ENROLL HỌC VIÊN**; `224` and `47` use **LỖI ENROLL**; `246` and `243` concern class enrollment errors | Repeated enrollment-related support demand; root causes need investigation |
| TMS/timekeeping data or access | `239` TMS information not showing, `236` TMS data missing, `232` timekeeping information not showing, `228` approval entries not showing, `253` cannot log into TMS | Multiple reports about TMS availability/data/access; not necessarily one outage |
| CRM call/transaction operations | `260` and `318` both **CRM không bấm gọi được**; `226` payment error; `225` payment not reflected in lead stage; `278` transaction reversal | Recurrence in CRM operations; different subproblems require separate handling rules |
| Student record/enrollment data corrections | `288` and `286` have the same subject about correcting a student name in enrollment; `101` reports incorrect student name display | Repeated data-change requests; correctness and approval checks are important |
| Account/login/password support | `165` internal login error, `162` internal login error, `143` cannot log in to CRM, `241` cannot access TMS, `41` LMS password reset, `220` ECOUNT account locked | Access issues occur, but the export **does not verify** 30-day inactivity or the same account deactivation root cause |

These are **candidate themes, not a measured top-five issue ranking**. The export includes only titles/tags, so a full classification pass with documented rules is necessary before reporting exact family frequencies.

## 6. Root-cause and impact limitations
- **Frequency:** raw tag totals and exact-title recurrence are measurable. Accurate per-issue frequency needs an explicit categorization rule and manual review for ambiguous titles.
- **Users affected:** not present; requester/commercial entity is not equivalent to a user count.
- **Time spent:** not present; do not substitute guessed minutes for measured handling time.
- **Root cause:** no ticket descriptions, investigation logs, resolution notes or application logs to verify diagnoses.
- **Time trends:** Created Date is missing; daily and weekly trend charts cannot be reproduced from this workbook alone.
- **Team performance:** Assigned to is blank on the extracted records; tickets solved per agent or SLA compliance cannot be established.

## 7. Suggested next data collection
Export ticket ID, subject, description, category/tags, creation date, close date, assigned agent, stage, requester, time spent/timesheets, response timestamps, resolution notes, and affected-user count (if available). Preserve the analysis period and filters. If these fields are inaccessible in training Odoo, state the limitation explicitly rather than inventing metrics.

## 8. Conclusion
The workbook provides credible evidence of repeated **enrollment**, **TMS**, **CRM**, **student-data**, and **access** requests. It supports preliminary pattern discovery, but it cannot establish exact root causes, time cost or the most automatable issue without more information. The Week 5 assignment separately specifies **Scenario 1 — Login Issue** as the implementation target; this is a curriculum selection, **not a measured conclusion that login dominates this dataset**.
