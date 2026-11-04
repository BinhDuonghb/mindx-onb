# Week 5 — Recommendations and Automation Decision

## 1. Decision summary
**Implement Scenario 1: Login Issue / Account Reactivation automation**, because the Week 5 task explicitly chooses this case and it has a plausible structured decision path. **Do not claim the sample proves login is the most frequent issue**; the exported workbook does not support that conclusion.

## 2. Evidence versus assumptions

| Item | Status | Basis |
|---|---|---|
| Account/access requests exist | **Observed** | Ticket sequences `165`, `162`, `143`, `241`, `41`, `220`, `331` |
| Enrollment, TMS and CRM support demand repeats | **Observed** | Repeated/similar ticket subjects documented in `recurring-issues.md` |
| Accounts deactivate after 30 days of inactivity | **Scenario assumption from Week 5 tasks** | Not established by `sample.xlsx` |
| Manual recovery takes 5–10 minutes | **Scenario estimate from Week 5 tasks** | Not measured in `sample.xlsx` |
| HR API and LMS reactivation API exist | **Integration prerequisite to verify or mock** | No endpoint specification supplied in workbook |
| Automation will reduce manual workload | **Expected benefit, not yet measured** | Requires pilot tests and monitoring |

## 3. Automation feasibility assessment (qualitative)

| Candidate area | Feasibility | Conditions / risks | Recommendation |
|---|---|---|---|
| Verified inactive LMS account; active employee | **Medium–High (conditional)** | Identity verification; HR truth; authorized LMS API; correct account cause | **Week 5 implementation target** |
| Student enrollment requests | Medium | Duplicate enrollment, available slots, enrollment policy, approval | Investigate rule-based subcases; avoid blanket auto-enrollment |
| Student data corrections | Medium–Low | Data ownership, permissions, potential unintended changes | Human approval before mutations |
| CRM calling, payment or financial changes | Low for blanket automation | Financial and customer-impact risk, diverse root causes | Triage automatically; manual approval for sensitive operations |
| TMS data/attendance failures | Low until diagnosed | Could be shared outage, synchronization or application defect | Automated detection/notification; Dev escalation if needed |

Feasibility assessments are engineering judgments based on problem descriptions, **not generated Odoo metrics**.

## 4. Proposed login automation workflow

```text
New Odoo Helpdesk ticket
  -> Trigger (webhook or scheduled polling)
  -> Normalize title/description and classify
     -> Unrelated/uncertain: record reason, route for manual triage
     -> Eligible login issue:
          -> Validate requester identity / employee mapping
          -> HR lookup
             -> Active, LMS deactivation confirmed, permitted action:
                  -> Reactivate LMS account
                  -> Verify result
                  -> Log decision, update Odoo ticket
                  -> Send resolution response with a confirmation request
             -> Terminated:
                  -> DO NOT reactivate
                  -> Add internal note and route to authorized manual review
             -> Unknown / HR timeout / LMS failure / mismatch:
                  -> DO NOT perform unsafe change
                  -> Log and route for investigation / Dev escalation as appropriate
                  -> Send status update to requester
```

Communication policy: fast confirmed fixes can use a combined acknowledgement/resolution message. Long-running or escalated cases should receive an acknowledgement and updates; do not send a success confirmation until the reactivation is verified. Actual requester confirmation should remain explicit, not inferred from sending a message.

## 5. Why automation rather than immediately changing the code-level rule?
- The Week 5 Operating Engineer objective is to provide a repeatable, controlled operational workaround while an underlying inactivity rule may require development work.
- An automation is useful **only** for verified legitimate users and correctly diagnosed deactivation cases; it must not bypass access policies.
- The root-cause fix should be separately reviewed with the responsible engineering/business owners, especially if the 30-day deactivation is an intentional security control.
- A short-term workaround is **not** a substitute for a permanent fix when the underlying behavior is incorrect.

## 6. Test and safety plan

| Scenario | Expected result |
|---|---|
| Eligible login ticket, HR active, LMS deactivated | Reactivate once, verify, log and notify |
| HR terminated | Do not reactivate; internal note/manual review |
| Non-login ticket | No LMS mutation; other/manual routing |
| HR lookup fails / employee not found | Fail closed; record error; review |
| LMS API fails | Do not report success; log and escalate |
| Duplicate webhook/poll result | Idempotency prevents duplicate reactivation/messages |
| LMS account already active | Diagnose instead of blindly changing state |
| Requester not verified | No account mutation; verification/manual review |

Tests can use mock HR/LMS/Odoo clients where production APIs or permissions are unavailable. Document which flows were real integrations versus simulations.

## 7. Monitoring and ticket-reduction action plan
- Track **total login tickets**, **eligible cases**, **automatically resolved cases**, **manual reviews**, **failures**, **reopenings** and **time-to-resolution**.
- Compare periods with consistent ticket categories and lengths. Automating resolution may **not reduce ticket creation**, but may reduce manual interventions and handling time.
- Collect measured staff effort for manual and automated cases to estimate time saved; do not present the Week 5 scenario's 5–10 minutes as a measured baseline.
- Review error logs weekly, improve classification, and provide a safe manual override and disable switch.
- Escalate recurring technical faults/root-cause evidence to Dev rather than silently retrying unsafe account changes.

## 8. Next steps
1. Validate issue taxonomy using full Odoo descriptions/resolution notes where available.
2. Confirm or mock HR and LMS API contracts and authorization model.
3. Build Odoo trigger, analyzer, decision service, clients, audit log, and notification service.
4. Test end-to-end, demonstrate safe failure handling, and save screenshots/logs.
5. Present results as **training/demo outcomes** until real monitoring metrics exist.

## References
- [Week 5 overview](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/overview.md)
- [Week 5 tasks](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/tasks.md)
- [Week 5 sample data](https://github.com/BinhDuonghb/mindx-onb/blob/master/docs/plans/week-5/data/sample.xlsx)
