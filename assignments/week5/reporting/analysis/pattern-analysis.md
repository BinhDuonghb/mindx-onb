# Week 5 — Pattern Analysis

> **Training data scope (Week 5).** The supplied `docs/plans/week-5/data/sample.xlsx` is a **limited training dataset**. The analyst can inspect the provided export but does **not** have access to its underlying Odoo ticket records, descriptions, worklogs or resolution history. The analysis is therefore deliberately limited to observable subjects, IDs, tags and other fields actually included in the sample. It is **not** an independent audit of live production incidents.
>
> **Evidence convention:** `Observed` = directly in the workbook; `Inferred / provisional` = subject-based categorization that can be reproduced using the attached ID mapping; `Scenario assumption` = specified by Week 5 tasks; `Planned` = proposal for a future real-world deployment; `N/A — not in training dataset` = cannot be calculated with the provided fields. These statuses are not interchangeable. The absence of production-only metrics or Odoo case-level verification is a **documented boundary of this exercise**, not a claim that those values have been measured or verified.

## 1. Objective and evidence source

This is a **training assignment analysis**, not a production incident investigation. The source is [`docs/plans/week-5/data/sample.xlsx`](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx), `Sheet1`. The analyst does not have access to the underlying Odoo tickets from which the file was exported. Conclusions must remain within that evidence boundary.

The workbook has **183 populated rows**: one header, **131 records with both a ticket sequence and Subject**, and **51 structural/grouping rows**. The analyzable sample contains **131** ticket subjects. Relevant usable fields are `Subject`, `Ticket IDs Sequence`, `Tags` and `Priority`. `Assigned to` is blank for these ticket records. Created/closed dates, worklogs, actual users affected, investigation notes and confirmed root causes are not provided.

The spreadsheet can support **title-based issue categorization and frequency counts**. It cannot support production-scale user impact, handling time, MTTR, daily trend or staff productivity from this source alone. Odoo report screenshots/exports produced for other training tasks are separate evidence and must not be treated as missing columns in this sample.

## 2. Method

1. Filter to 131 rows where both `Ticket IDs Sequence` and `Subject` are populated; exclude structural rows.
2. Assign **one Primary Issue Family per ticket**, based on the operational request/symptom expressed in the Subject. Store optional `System`, `Subtype`, `Confidence` separately where available. A product tag such as `CRM` or `TMS` does not by itself establish a root cause.
3. Apply explicit overlap rules: TMS **login** → Account Access; TMS **missing attendance/timekeeping data** → Timekeeping. CRM calls → Communication; payment/transaction issues → Payment; CRM lead-stage requests → CRM Lead Operations.
4. Identify `Test/sample` separately (10 records) and preserve them in the full 131-row reconciliation. Flag unknown/inadequate titles as `Other/unclear` (8 records). Do not fabricate descriptions or diagnoses.
5. Preserve the row-level mapping in [`ticket_classification.xlsx`](ticket_classification.xlsx). Calculate shares using 131 as the full-file denominator; use 121 only if explicitly excluding 10 test/sample records, with the denominator disclosed.

## 3. Observable exported-tag and priority distributions

### 3.1 Raw `Tags` (not incident categories)

| Raw tag value | Ticket records | % of 131 | Interpretation |
|---|---:|---:|---|
| `31` | 24 | 18.3% | Numeric-like value, unverified meaning |
| `CRM` | 23 | 17.6% | Product/system, not issue cause |
| `44` | 21 | 16.0% | Numeric-like value, unverified meaning |
| `LMS` | 14 | 10.7% | Product/system |
| `TMS` | 9 | 6.9% | Product/system |
| `307` | 7 | 5.3% | Numeric-like value, unverified meaning |
| `62` | 6 | 4.6% | Numeric-like value, unverified meaning |
| `Awaiting information` | 5 | 3.8% | Workflow tag |
| Other tag values | 22 | 16.8% | Remaining raw values |
| **Total** | **131** | **100.0%** | |

### 3.2 Priority completeness

| Priority | Ticket records |
|---|---:|
| Blank | 108 |
| Urgent | 13 |
| High priority | 3 |
| Medium priority | 1 |
| Low priority | 6 |
| **Total** | **131** |

**108/131 (82.4%)** priority values are blank; priority is therefore not a reliable substitute for measured business impact.

## 4. Subject-based recurring patterns (provisional)

The following are **counts under a stated classification rule**, not verified shared causes. The full mapping of 131 IDs and the complete 12-family reconciliation are in [`recurring-issues.md`](recurring-issues.md) and the companion spreadsheet.

| Provisional rank | Primary issue family | Tickets | % of 131 | Evidence examples |
|---:|---|---:|---:|---|
| 1 | Account access / provisioning | 22 | 16.8% | `165`, `162`, `143`, `241`, `253`, `41`, `220` |
| 2 | Enrollment / class allocation | 18 | 13.7% | `274`, `267`, `224`, `47`, `243`, `246` |
| 3 | Timekeeping / attendance | 17 | 13.0% | `239`, `236`, `232`, `228`, `234`, `233` |
| 4 (tie) | Payment / transactions / orders | 13 | 9.9% | `278`, `249`, `226`, `225`, `287` |
| 4 (tie) | Student records / learning progress | 13 | 9.9% | `288`, `286`, `101`, `295`, `269` |

- Two tickets with similar Subjects may represent different causes and different resolutions. No root-cause clustering claim is made.
- Access tickets include login, password and provisioning; **they are not all 30-day-inactive LMS cases**. Week 5 separately specifies the LMS Login Automation POC as the implementation task, regardless of this ranking.
- The 8 `Other/unclear` cases remain unresolved because the training export is underspecified and the original Odoo tickets are unavailable. These are clearly disclosed instead of guessed.

## 5. Impact metrics — evidence-bounded

| Metric | Training result | Why |
|---|---|---|
| Total sample ticket volume | **131** | Count of records with ID + Subject; no defined time period |
| Family frequency | **Provisional counts shown above** | Reproducible subject-based mapping; no live case-level validation |
| Users affected | **N/A — not in training dataset** | No affected-user field; ticket count ≠ user count |
| Handling time / time spent | **N/A — not in training dataset** | No worklogs or handling minutes |
| MTTR | **N/A — not in training dataset** | No creation/resolution timestamps |
| Daily/weekly trend | **N/A from this dataset** | No dated observations |
| Team performance | **N/A from this dataset** | Assigned-to is blank for extracted records |
| Verified root causes | **Unverified** | No investigation or resolution data |
| Automation time saved | **Not yet measured** | Scenario 5–10 minute manual estimate is not a measured baseline |

**This is a deliberate scope distinction:** `N/A` is the correct evidence-based result for fields that the supplied training sample does not contain. It is **not** a request to fabricate metrics, and it does not imply the student can open the original Odoo records. Production-level verification would require separately authorized data in a future operating environment.

## 6. Conclusions and use in recommendations

The provided sample supports transparent **recurring-demand analysis** and a **reproducible provisional ranking**. It does **not** establish verified causal incidents or production impact metrics. The next step **within Week 5** is to compare feasible handling approaches for the Top 3 subject-based groups in [`recommendations.md`](recommendations.md), with explicit assumptions, approval boundaries, potential KPIs and an action plan. This is possible without access to the original Odoo tickets.

The Week 5 selected automation case, **Scenario 1 — Login Issue**, is a **curriculum-defined POC** rather than a production fix justified by proven 30-day account-deactivation frequency.

## 7. If this analysis were deployed to a real operating environment (future work only)

A production follow-up could seek creation/closure timestamps, actual affected-user counts, assigned-to, verified descriptions, worklogs, resolution notes and API/security authorization. Any 28-day pilot measurement in `recommendations.md` is a **proposed measurement design**, not historical data present in `sample.xlsx` and not a prerequisite for completing the available training-sample analysis.

## References

- [Week 5 requirements](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/tasks.md)
- [Mentor Issue #5](https://github.com/BinhDuonghb/mindx-onb/issues/5)
- [Training sample](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx)
