# Week 5 Tasks: Reporting, Analysis & Automation

**Authors:** ThuanTV, Cursor AI  
**Focus:** Data-driven operations, pattern analysis, and Operating Engineer automation implementation

---

## 🔧 Sys Admin / DevOps Setup

**Required Access:**

- Odoo ticket system (reporting access)
- Script execution environment (for automation)

---

## Week 5 Overview

Week 5 focuses on **analyzing ticket patterns** from Week 4 and **implementing automation solutions** using Operating Engineer approach.

**Days 1-2: Reporting & Analysis**
- Create reports in Odoo
- Identify recurring patterns
- Analyze ticket data

**Days 3-4: Automation Implementation**
- Implement automation workflow for Scenario 1: Login Issue
- **Automation workflow:**
  - Auto-analyze ticket content to identify login issue pattern
  - Auto-check employee status against HR system
  - Auto-process: reactivate if active, add note if terminated
  - Auto-send response email to user
- Integrate with Odoo ticket system (webhook/API)
- Test and document automation workflow
- Present findings and automation

---

## Days 1-2: Reporting & Analysis

### Objective

Master Odoo reporting tools and identify recurring ticket patterns from Week 4 data.

### Tasks

1. **Learn Odoo Reporting**
   - Explore built-in reports
   - Learn custom report builder
   - Export and schedule reports

2. **Create Reports**
   - Daily ticket summary report
   - Team performance report
   - Category analysis report
   - Ticket volume trends

3. **Analyze Patterns**
   - Identify top 5 recurring issues
   - Calculate impact (users affected, time spent)
   - Document patterns with evidence

### Deliverables

- Odoo reports (screenshots/exports)
- Pattern analysis document
- List of top recurring issues with impact metrics

---

## Days 3-4: Automation Implementation

### Objective

Implement Operating Engineer automation solution for a recurring issue identified in Days 1-2.

### Task: Scenario 1 - Login Issue Automation

**Original Scenario:** [→ Open](../week-3/scenarios/scenario-01-login-issue.md)  
**Automation Task Details:** See implementation steps below

**Focus:** Operating Engineer approach - Create automation instead of fixing root cause

**Selected Issue:** Scenario 1 - Login Issue (Account Reactivation)
- **Why selected:** Clear recurring pattern, high automation value, perfect Operating Engineer fit
- **Pattern:** Account deactivation after 30 days inactivity (code-level rule)
- **Manual fix:** Reactivate + reset password (5-10 min per ticket)
- **Automation workflow:** 
  - Auto-analyze ticket content to identify login issue case
  - Auto-check employee status against HR system
  - Auto-process: reactivate if active, add note if terminated
  - Auto-send response email to user

### Steps

1. **Understand the Problem**
   - Review Scenario 1: Login Issue from Week 4
   - Understand the recurring pattern (account deactivation)
   - Identify why automation is appropriate (root cause requires code fix)
   - Document why automation is better than code fix for this case

2. **Design Automation Workflow**
   - Understand the problem pattern
   - Design end-to-end automation workflow:
     - Ticket analysis (NLP/keyword matching to identify login issue)
     - HR system integration (check employee status)
     - Decision logic (active → reactivate, terminated → add note)
     - Auto-response (email to user)
   - Identify what to automate vs what to escalate
   - Plan integration with Odoo (webhook/API)
   - Plan script structure

3. **Implement Automation Workflow**
   - Write Python script/workflow for ticket automation
   - Workflow steps:
     - **Ticket Analysis:** Parse ticket content, identify login issue pattern
     - **HR Check:** Query HR system API to check employee status
     - **Decision & Action:**
       - If employee is active → Auto-reactivate account in LMS
       - If employee is terminated → Add note to ticket for manual review
     - **Auto-Response:** Generate and send email response to user
     - **Logging:** Log all actions and decisions
   - Integrate with Odoo ticket system (webhook/API)
   - Include error handling and fallback logic
   - Add comprehensive logging
   - Test workflow end-to-end
   - Set up trigger (webhook on ticket creation or scheduled check)

4. **Documentation**
   - Document what the workflow does (end-to-end process)
   - Document Odoo integration setup (webhook/API configuration)
   - Explain Operating Engineer approach (automation vs code fix)
   - Create knowledge base article
   - Document workflow trigger setup (webhook or scheduled check)

5. **Presentation**
   - Present automation solution
   - Explain Operating Engineer mindset
   - Show before/after metrics (if available)
   - Discuss when to use automation vs code fix

---

## Operating Engineer Automation Principles

### When to Create Automation

✅ **Create automation when:**
- Issue is recurring and repetitive
- Manual fix works but takes time
- Root cause fix requires code changes (dev team)
- Need immediate solution
- Automation can handle 80%+ of cases

❌ **Don't create automation when:**
- Root cause fix is simple and quick
- Issue is one-time only
- Automation would be more complex than fix
- Code fix is high priority

### Automation vs Code Fix

**Automation (Operating Engineer):**
- Quick to implement (hours/days)
- No code changes needed
- Solves immediate problem
- Can be temporary or permanent

**Code Fix (Software Engineer):**
- Requires code changes
- Needs testing and deployment
- Takes days/weeks
- Solves root cause permanently

---

## Resources

### Resources

- **Scenario 1 (Original):** [Login Issue](../week-3/scenarios/scenario-01-login-issue.md)
- **Investigation:** [Scenario Analysis for Automation](../../notes/2026-01-30/investigation-scenario-automation-analysis.md)

### Templates

- Automation workflow template (see implementation steps above)
- Documentation template
- Presentation template

### Tools

- Odoo reporting tools
- Python/Bash for scripting
- Git (for version control of scripts)

---

## Notes

- **Operating Engineer Mindset:** Focus on automation/workarounds, NOT code fixes
- **Boundary Awareness:** Know when to escalate to dev team vs create automation
- **Documentation:** Document everything - scripts, decisions, patterns
- **Testing:** Test automation workflow thoroughly end-to-end before deploying
- **Monitoring:** Monitor automation effectiveness after deployment (ticket reduction, resolution time)
