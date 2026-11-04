# Week 5 — Recurring Issues Register

## Evidence base
Source: [`sample.xlsx`](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx), `Sheet1`. **131 identified ticket records** with subject and ticket sequence. The remaining 51 nonheader worksheet rows are structural/group rows and are excluded. This document lists **five candidate recurring issue families**, not an exact frequency ranking. Ticket IDs cited below are values of `Ticket IDs Sequence` in the workbook.

## 1. Candidate recurring issue families

| Candidate issue family | Verifiable ticket examples | Repetition evidence | Likely handling direction |
|---|---|---|---|
| Enrollment / learner-class allocation | `274`, `267`, `224`, `47`, `246`, `243` | Exact repeated subjects for enrollment failure; additional similar requests | Validate student/class/schedule, then apply rules or escalate |
| TMS / attendance and timekeeping | `239`, `236`, `232`, `228`, `253`, `233`, `234` | Several related reports of unavailable timekeeping information / TMS access | Check scope and system health before attempting fixes |
| CRM / telephony and payment operations | `260`, `318`, `226`, `225`, `278`, `249` | Duplicate CRM calling subject; multiple transaction problems | Separate low-risk checks from financial operations requiring approval |
| Student record corrections | `288`, `286`, `101` | Two identical student-name correction requests; related display issue | Controlled data correction with identity/authorization validation |
| Account access / passwords | `165`, `162`, `143`, `241`, `41`, `220`, `331` | Multiple login, access, locked-account or password requests across systems | Verify identity and HR status; auto-handle only approved cases |

**Counting rule:** Example IDs are supporting records, **not the total count per issue family**. Themes can overlap (e.g., TMS login belongs to both TMS and account access). Do not sum this table or interpret the rows as mutually exclusive.

## 2. Directly measurable baseline

### Product/workflow tag distribution

| Tag value | Ticket count |
|---|---:|
| CRM | 23 |
| LMS | 14 |
| TMS | 9 |
| Awaiting information | 5 |
| Numeric-like tag `31` | 24 |
| Numeric-like tag `44` | 21 |
| Numeric-like tag `307` | 7 |
| Numeric-like tag `62` | 6 |
| Other tags | 22 |
| **Total** | **131** |

Tags represent mixed concepts, and numeric-like values have not been decoded. Therefore this is **not** the top five recurring **problems**; it is a raw export distribution.

### Priority completeness

- Urgent: **13**
- High: **3**
- Medium: **1**
- Low: **6**
- Blank: **108**
- Total: **131**

## 3. Impact assessment

| Impact dimension | Result from this file | Constraint |
|---|---|---|
| Ticket volume | 131 ticket records | Does not cover a defined time window |
| Tickets by clear raw tag | CRM 23, LMS 14, TMS 9 | Product tags are not root-cause categories |
| Users affected | **Not available** | No verified affected-user count |
| Handling time per ticket | **Not available** | No worklogs or equivalent field |
| Mean time to resolution | **Not available** | No explicit created/closed timestamps |
| Actual frequency by issue family | **Not established** | Title-based taxonomy must be validated and applied to all records |
| Automation hours saved | **Not measurable from dataset** | Requires historical handling effort and automation success metrics |

## 4. Root cause versus symptom

- **Symptom:** “Cannot log into CRM.” **Possible causes:** credentials, permissions, account status or a service outage. The workbook does not identify which.
- **Symptom:** “TMS does not show timekeeping information.” **Possible causes:** UI, synchronization, permissions or backend issue. No verified diagnosis is available.
- **Symptom:** “Cannot enroll learner.” **Possible causes:** missing slots, duplicate enrollment, invalid class settings, permissions or errors. Investigate before automation.

## 5. Required follow-up for a defensible top-five ranking
1. Define mutually exclusive issue categories with keyword rules and manual review, including how to handle overlapping system and symptom tags.
2. Classify all 131 records and retain a ticket-ID-to-category mapping as audit evidence.
3. Validate ambiguous titles from ticket descriptions and resolution notes where available.
4. Calculate counts and percentages using the classified ticket set, not raw product tags.
5. Add real affected-user and support-time measures only when those data are provided.

## 6. Reporting conclusion
This sample demonstrates recurring areas of operational support but **does not establish a definitive top-five-by-frequency ranking**. It provides adequate input for training data discovery and an issue register. A verified ranking and numerical impact analysis require more complete classification and supporting fields.
