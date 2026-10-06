# Week 4 Tasks: Ticket Handling (Scenarios 01-06)

**Authors:** ThuanTV, Cursor AI  
**Focus:** Practice on Odoo Helpdesk about ticket workflow through 6 scenarios (01-06) + email drafts per scenario

---

## 🔧 Sys Admin / DevOps Setup

**Required Access:**

- Odoo ticket system
- Azure App Insights (read-only)

### Recommended: Create an Odoo trial account

1. Odoo offers trial accounts on its official website. See pricing and trial options at: `https://www.odoo.com/vi_VN/pricing`.
2. Create a demo account (14-day trial) to practice if no access to an internal demo instance is provided.
3. Quick signup guide:
   - Visit `https://www.odoo.com/vi_VN/pricing` → select "Try now" or "Start Now".
   - Enter name, email, phone number and create a demo database.
   - Select the apps needed for your scenarios (Helpdesk / Project / CRM) or start with one app to get familiar.
4. Important training notes:
   - This is a **demo environment** — DO NOT contact real users or modify production data.
   - Submit practice results as screenshots or exported files (do not interact with real users).
   - For sample data, use Odoo's demo data feature or import/export sample datasets.

---

## MindX 7-Step Process (Quick Reference)

1. **Reception** - Log ticket in Odoo (< 15 min)
2. **Initial Response** - Acknowledge (< 30 min)
3. **Diagnosis** - Investigate and identify issue
4. **Resolution** - Fix or provide workaround
5. **Communication** - Update every 24 hours
6. **Follow-up** - Confirm resolution with customer
7. **Trend Analysis** - Document patterns

## Class of Service

| Class          | Users | Treatment          |
| -------------- | ----- | ------------------ |
| Standard       | < 5   | Normal priority    |
| Priority       | 5-25  | Expedited handling |
| Expedite       | > 25  | Emergency response |
| Fixed Deadline | Any   | Time-driven        |

---

## 📁 Complete Scenarios in `scenarios/` Folder

All detailed scenarios are in the **`scenarios/` folder**. Each scenario includes:

- Complete situation description
- Step-by-step tasks
- Communication templates
- Evaluation checklist
- Tips and best practices

Note: This week uses scenarios **01-06** only.

---

## Days 1-2: Ticket Handling Practice

### Objective

Master Odoo workflow and MindX 7-step process through 6 ticket scenarios.

### Scenario List

| #   | Scenario            | Class          | Link                                                   |
| --- | ------------------- | -------------- | ------------------------------------------------------ |
| 1   | Login Issue         | Standard       | [→ Open](scenarios/scenario-01-login-issue.md)         |
| 2   | Performance Problem | Priority       | [→ Open](scenarios/scenario-02-performance-problem.md) |
| 3   | Critical Bug        | Expedite       | [→ Open](scenarios/scenario-03-critical-bug.md)        |
| 4   | Feature Request     | Standard       | [→ Open](scenarios/scenario-04-feature-request.md)     |
| 5   | Multi-User Issue    | Priority       | [→ Open](scenarios/scenario-05-multi-user.md)          |
| 6   | Deadline Request    | Fixed Deadline | [→ Open](scenarios/scenario-06-deadline-request.md)    |

### Skills You'll Build

**Scenarios 1-2:** Foundation

- Odoo workflow
- 7-step process
- Professional responses
- Basic investigation

**Scenarios 3-4:** Intermediate

- Emergency handling
- Expectation management
- Stakeholder coordination
- Policy application

**Scenarios 5-6:** Advanced

- Impact assessment
- Time negotiation
- Multi-user coordination
- Deadline commitments

### Deliverables Per Scenario

- Odoo ticket record (screenshot/export)
- Email drafts (ACK / update / resolution)
- Classification justification
- Reflection notes

---

## Week 4 - Completion (concise)

- Finish scenarios **01-06** and submit required deliverables: Odoo records (screenshots/exports), email drafts, and a short reflection per scenario.
- Mentor verifies core outcomes and confirms readiness for Week 5.

---

## Resources & Templates (complete)

### MindX 7-Step Process (Quick Reference)

1. **Reception**: Log ticket in Odoo system (within 15 minutes)
2. **Initial Response**: Acknowledge the request and communicate receipt within 30 minutes
3. **Diagnosis**: Investigate the issue, gather more info if needed
4. **Resolution**: Provide a fix or workaround; document actions
5. **Communication**: Update customer and stakeholders every 24 hours or as needed
6. **Follow-up**: Confirm with the customer that the solution worked
7. **Trend Analysis**: Document patterns for future improvement and share with the team

---

### Odoo Ticket Workflow

1. **Create Ticket**: Enter all relevant details (title, description, customer info, class of service, category, tags)
2. **Set Priority**: Assign priority based on class of service table
3. **Log Initial Response**: Record your acknowledgement and first communication
4. **Update Regularly**: Record diagnosis, updates, and any actions taken
5. **Document Resolution**: Add details about the solution and confirm customer satisfaction
6. **Close Ticket**: Move ticket to resolved/closed once confirmed

---

### Communication Templates

- Each scenario in the `scenarios/` folder includes:
  - **Acknowledgment email/message** to customer/requester
  - **Escalation message** templates for DevOps/Sys Admin, if needed
  - **Resolution/follow-up template** to confirm closure

**Find communication templates directly in each `scenario-xx-*.md` file. Adapt for email, Teams, or other tools as appropriate.**

---

### Escalation Guidance

- Escalate when:
  - The issue is beyond your technical or access scope
  - There is significant business impact (multiple users, critical services)
  - Security, data privacy, or compliance is involved
- Escalation steps:
  1. Gather and include all context: ticket #, summary, actions tried, error messages/logs, impact
  2. Use appropriate channel (e.g. Microsoft Teams message, email, or ticket transfer)
  3. Keep requester informed about escalation and next steps

---

### Additional Tips

- **Document everything:** Each step should be recorded in Odoo for auditability
- **Use tags/labels:** For filtering and reporting
- **Screenshots/exports:** Required for all deliverables—blur/redact sensitive info
- **Sample data:** Use only provided demo/sample data—never real user data in training

---

**For DETAILED, scenario-specific steps and communications, always refer to the corresponding files in the `scenarios/` folder. Each file contains instructions, context, and ready-to-use message templates.**
