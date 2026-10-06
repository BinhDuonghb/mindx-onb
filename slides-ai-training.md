---
theme: default
colorSchema: light
background: "#ffffff"
title: AI Training - Mindset & Effective Usage
info: |
  Core principles, good/bad examples, and workflows for effective AI collaboration
fonts:
  sans: "Exo"
  serif: "Exo"
  mono: "SF Mono, Monaco, Consolas"
class: text-center
drawings:
  persist: false
transition: none
mdc: true
favicon: "/favicon.svg"
---

# AI Training

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

Mindset & Effective Usage

---

## Core Mindset

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

- **AI is a collaborative tool** - Not replacement, but pair programmer
- **You are the architect** - You design, AI helps implement
- **Critical thinking required** - Always question and verify
- **Review before use** - Never blindly accept AI output
- **Iterative refinement** - Feed context, refine, iterate

---

## Why Critical Thinking Matters

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Without critical thinking:**
- Blind trust leads to bugs
- Copy-paste without understanding
- Hard to maintain later
- No learning happens

**With critical thinking:**
- Catch errors early
- Understand what you're using
- Learn through questioning
- Build better solutions

---

## How to Apply Critical Thinking

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Process:**
1. **Read & Understand** - Don't copy-paste immediately
2. **Question** - Ask essential questions (see next slide)
3. **Verify** - Test, check facts, validate independently
4. **Refine** - Fix issues, improve based on understanding

**Key:** Always question before accepting, verify independently

---

## Essential Questions to Ask

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**When reviewing AI output, ask:**

- **Understanding:** Do I understand what AI is suggesting?
- **Alignment:** Does it align with my requirements?
- **Assumptions:** What are the assumptions AI is making?
- **Risks:** What could go wrong? What edge cases?
- **Verification:** How do I verify this is correct?

**How to ask:**
- Be specific: "What edge cases should I handle?"
- Challenge assumptions: "Why did you assume X? What if Y?"
- Request verification: "How can I test this? What should I check?"

---

## Bad Example: No Review ❌

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**What happens:**
- Copy-paste AI output directly
- No understanding of what was generated
- No verification or validation
- Blind trust in AI suggestions

**Problems:**
- May contain hallucinations
- May not fit actual requirements
- No learning happens
- Hard to maintain later

---

## Good Example: Review & Refine ✅

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**What happens:**
- Read and understand AI output
- Brief summary of what AI suggested
- Identify what needs adjustment
- Refine and improve
- Feed back refined version to AI

**Benefits:**
- Catch hallucinations early
- Ensure fit with requirements
- Learn through refinement
- Better maintainability

---

## Example: Bad vs Good Comparison

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Bad ❌:**
```
AI: [provides code]
You: [copy-paste directly]
Result: May have bugs, hallucinations
```

**Good ✅:**
```
AI: [provides code]
You: [review, brief summary, refine]
You: [feed back refined version]
AI: [improves based on feedback]
Result: Better code, you understand it
```

---

## Workflow: Layered Questioning

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**When to use:** You don't know about a topic/concept, need to learn from scratch

1. **Research** - "What is X? What are the key concepts?"
2. **Brief Feature** - Feed context, "How does X fit my project?"
3. **Code Example** - "Show me a simple example for my use case"
4. **Validation** - "How do I test this? What edge cases?"

**Focus:** Learning progressively, building understanding step by step

---

## Example: Layered Questioning

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Scenario:** You've heard about TDD, but you have never applied it to a real CLI tool

**Step 1 - Research:**
"What is Test-Driven Development? What are Red, Green, and Refactor?"

**Step 2 - Brief Feature:**
"I'm building a Ticket Manager CLI. What behavior should I test before implementing create, list, show, and update commands?"

**Step 3 - Code Example:**
"Show me a small example of a failing unit test for creating a ticket, then the minimal implementation to pass it"

**Step 4 - Validation:**
"What edge cases should I test for invalid input, missing tickets, and corrupted JSON storage?"

**Result:** Deep understanding through progressive learning

---

## Workflow: Solution Exploration

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**When to use:** You have a specific problem, need to explore multiple solutions before choosing

1. **Present problem** - Provide full context
2. **Identify problems** - AI identifies and prioritizes
3. **Explore options** - "What are possible solutions? Pros/cons of each?"
4. **Choose with context** - Feed additional context, select best fit
5. **Synthesize** - Root cause, solution chosen, risks

**Focus:** Exploration and decision-making, not implementation

---

## Example: Solution Exploration

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Scenario:** Your CLI tool has performance issues, need to explore solutions

**Step 1:** "Here's my CLI tool code [paste context]. What problems do you see? Prioritize them."

**Step 2:** "For problem #1 (slow file reading), what are possible solutions? List all options with pros/cons."

**Step 3:** "Given my context: [constraints, team size, timeline], which solution fits best? Why?"

**Step 4:** "Summarize: root cause, solution chosen, risks, and what to watch for."

**Result:** Clear decision on which solution to implement (then use Iterative Refinement to implement)

---

## Workflow: Iterative Refinement

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**When to use:** You already have code/solution from AI, need to improve quality

1. **Get AI suggestion** - Receive initial output
2. **Review carefully** - Read, understand, identify specific issues
3. **Summarize problems** - List what's wrong and why
4. **Refine yourself** - Fix issues, improve code
5. **Feed back with context** - "Here's what I changed and why. Review this version."
6. **Validate together** - AI reviews your changes, suggests further improvements

**Focus:** Improving existing code quality through review-feedback loop

---

## Example: Iterative Refinement

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Scenario:** AI gave you code, but it needs improvement

<div class="grid grid-cols-2 gap-6 text-sm">

<div>

**1. AI suggests:**
```typescript
async function readConfig(path: string) {
  return fs.readFile(path, 'utf-8');
}
```

**2. You review:**
- Missing error handling
- No path validation
- Security risk (path traversal)

**3. You summarize:**
"Missing error handling, path validation, security checks"
</div>

<div>

**4. You refine:**
```typescript
async function readConfig(path: string) {
  if (!path || path.includes('..')) {
    throw new Error('Invalid path');
  }
  try {
    return await fs.readFile(path, 'utf-8');
  } catch (error) {
    throw new Error(`Failed: ${error.message}`);
  }
}
```

**5. You feed back:**
"Added validation & error handling. Review this version."

**6. AI validates:**
"Good. Consider path normalization for Windows paths."

</div>

</div>

---

## Watch Out: Hallucinations

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**AI May:**
- Hallucinate facts or code
- Create unnecessary icons/emojis
- Make up non-existent APIs
- Provide outdated information

**Always:**
- Verify facts independently
- Test code before using
- Review output carefully
- **Teach AI:** Correct mistakes explicitly, provide detailed context and up-to-date documents

---

## Example: Teaching AI

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**AI:** "Use `odoo.getTickets()` method"

**You:** "That method doesn't exist. The correct Odoo API is `/api/helpdesk.ticket/search_read`. Please use the actual API."

**Result:** AI learns and provides better suggestions next time

**Key:** Explicitly correct hallucinations, don't silently fix

---

## Homework: Research Practice

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

**Task:** Research Test-Driven Development using controlled AI workflows

**Research focus:**
- **Core principles** - What is TDD? What are Red, Green, and Refactor?
- **Testing levels** - Unit tests, integration tests, and end-to-end tests
- **AI validation** - How tests help verify AI-generated code
- **CLI testing** - What to test for commands, validation, file storage, and errors

**Deliverable:** Research document with TDD principles, testing levels, CLI test examples, and how tests help control AI-generated implementation

---

# Thank You

<img src="https://mindx.edu.vn/logo.svg" alt="MindX Logo" class="mindx-logo" />

Questions?
