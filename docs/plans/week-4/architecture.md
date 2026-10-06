# Week 4 Architecture: Ticket Handling & Communication

**Authors:** ThuanTV, Cursor AI  
**Focus:** Operational workflows for support and communication

---

## Overview

Week 4 builds operational skills on top of technical foundation from Weeks 2-3. Focus is on **how you work** with tickets and communicate professionally.

---

## ASCII Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEK 4: OPERATIONS FLOW                      │
│                                                                 │
  │                                                                  │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              YOUR WORKFLOW (7 Steps)                       │ │
│  │                                                            │ │
│  │  1. Reception → Log in Odoo                               │ │
│  │  2. Response  → Acknowledge promptly                      │ │
│  │  3. Diagnosis → Investigate (logs, monitoring)            │ │
│  │  4. Resolution → Fix or workaround                        │ │
│  │  5. Communication → 24h updates                           │ │
│  │  6. Follow-up → Confirm with customer                     │ │
│  │  7. Analysis  → Document patterns                         │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    TOOLS & SYSTEMS                         │ │
│  │                                                            │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐               │ │
│  │  │   Odoo   │  │   Teams   │  │ Outlook  │               │ │
│  │  │ Tickets  │  │   Chat    │  │  Email   │               │ │
│  │  └──────────┘  └───────────┘  └──────────┘               │ │
│  │                                                            │ │
│  │  ┌────────────────────┐  ┌──────────────────┐            │ │
│  │  │  Azure Monitoring  │  │  Application     │            │ │
│  │  │  Logs/Alerts       │  │  Knowledge Base  │            │ │
│  │  └────────────────────┘  └──────────────────┘            │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Ticket Flow Detail

```
Customer Issue
      ↓
┌─────────────────────────────────────────────┐
│  RECEPTION                                  │
│  • Log ticket and capture relevant details  │
│  • Prioritize using Class of Service        │
│  • Assign owner                             │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  INITIAL RESPONSE                            │
│  • Acknowledge receipt                       │
│  • Set expectations                          │
│  • Ask clarifying questions / request info   │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  DIAGNOSIS                                   │
│  • Gather information and attachments        │
│  • Attempt to reproduce the issue            │
│  • Review logs and monitoring as applicable  │
│  • Identify likely root cause                │
└──────────────────┬──────────────────────────┘
                   ↓
           ┌───────┴───────┐
           │               │
    ┌──────▼─────┐  ┌──────▼──────┐
    │ Can fix?   │  │  Escalate?  │
    │ Yes: Fix   │  │  Yes: Dev/  │
    │            │  │  Infra team │
    └──────┬─────┘  └──────┬──────┘
           │               │
           └───────┬───────┘
                   ↓
┌─────────────────────────────────────────────┐
│  RESOLUTION                                  │
│  • Determine and apply the solution          │
│  • Verify the fix and test where possible    │
│  • Document actions in Odoo                   │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  COMMUNICATION                               │
│  • Update customer / internal stakeholders   │
│  • Record progress in Odoo                   │
│  • Coordinate handoffs with teams            │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  FOLLOW-UP                                    │
│  • Confirm resolution with requester         │
│  • Collect feedback and close ticket         │
│  • Create KB entry if applicable             │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  TREND ANALYSIS                               │
│  • Analyze ticket data to identify patterns  │
│  • Flag recurring issues for remediation     │
│  • Feed findings into improvements / KB      │
└─────────────────────────────────────────────┘
```

---

## Communication Patterns

### To Customers (Email/Ticket)

```
Tone: Professional, empathetic, clear
Channel: Odoo ticket messages (primary for Week 4 training)
Structure:
  1. Acknowledge issue
  2. Current status
  3. Next steps
  4. Expectations (avoid promising fixed ETA)
  5. Contact info (Odoo ticket thread)
```

### To Dev Team (Teams/Chat)

```
Tone: Technical, concise, factual
Include:
  1. Customer impact
  2. Steps to reproduce
  3. Error logs/screenshots
  4. Urgency and impact; expected effort if available
```

### To Management (Email)

```
Tone: Business-focused, clear ask
Structure:
  1. Situation summary
  2. Business impact
  3. Options
  4. Recommendation
  5. Decision needed
```

---

## Class of Service Decision Tree

```
New Ticket
    ↓
How many users affected?
    ↓
    ├─ < 5 users ──→ STANDARD
    │               (Normal queue)
    │
    ├─ 5-25 users ─→ PRIORITY
    │               (Move up queue)
    │
    ├─ > 25 users ─→ EXPEDITE
    │               (Drop everything)
    │
    └─ Fixed date ─→ FIXED DEADLINE
                    (Time-based priority)
```

---

## Escalation Paths

```
┌──────────────────────┐
│  Standard Issues     │
│ -> Handle yourself   │
└──────────────────────┘
          ↓ (if needed)
┌──────────────────────┐
│  Senior Engineer /   │
│  Other Engineers     │
│ -> Complex technical │
└──────────────────────┘
          ↓ (if needed)
┌──────────────────────┐
│  Management          │
│ -> Business decisions│
└──────────────────────┘
```

**Escalate when:**

- Beyond your knowledge
- Needs approval
- High business risk
- Security/data concern

---

## Tools Integration

**Odoo (Primary)**

- Ticket lifecycle
- Documentation
- Reporting
- Knowledge base

**Teams**

- Quick questions
- Internal coordination
- Status updates
- Team collaboration

**Outlook**

- Customer communication (covered in Week 4 training)
- Formal requests (Week 4)
- Management updates (Week 4)
- External coordination (Week 4)

**Azure Monitoring**

- Log analysis
- Performance metrics
- Error tracking
- System health

---

## Success Indicators

**By end of Week 4 (training):**

- ✅ Handle 6 practice scenarios (01-06) successfully
- ✅ Apply 7-step process consistently
- ✅ Communicate professionally across channels
- ✅ Use Odoo correctly for all ticket work
- ✅ Make proper escalation decisions
- ✅ Demonstrate timely acknowledgement and responses (no fixed ETA)

---

## Final State

After Week 4, you will:

1. **Know the workflow** - 7-step process internalized
2. **Use the tools** - Odoo and Teams proficiently (Outlook covered in Week 4)
3. **Communicate well** - Professional across all channels
4. **Make decisions** - Prioritize and escalate appropriately
5. **Work independently** - Handle tickets without constant guidance

**Foundation complete for Week 5 real work!** 🚀
