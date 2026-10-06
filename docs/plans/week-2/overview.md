# Week 2: TDD Practice - Ticket Manager CLI

## Objectives

Build a **Ticket Manager CLI** using Test-Driven Development and controlled AI usage during development.

**Focus Areas:**
- Practice TDD through Red-Green-Refactor cycles
- Use AI with control through proper guardrails and validation (apply workflows from Week 1)
- Build maintainable CLI code with simple layers: commands, services, models, and JSON storage
- Write meaningful tests for normal flows, invalid input, and error cases

## Training Materials

- AI Training Slides: [`slides-ai-training.md`](../../../slides-ai-training.md) - Controlled AI Usage (from Week 1)

## Problem Statement

Build a CLI tool to manage tickets stored locally in JSON files. The tool should support:
- Creating tickets with title, description, status, priority, tags
- Listing tickets with filters (by status, priority, tags)
- Showing ticket details
- Updating ticket status

### Week 2 Focus: TDD & CLI Foundation

This week focuses on building a Ticket Manager CLI through TDD. Candidates will write failing tests first, implement the smallest working behavior, refactor with AI assistance, and build basic CLI commands (`tickets create`, `tickets list`, `tickets show`, `tickets update`) with simple separation between command handling, ticket logic, and JSON file storage.

## Acceptance Criteria

- [ ] TDD workflow is demonstrated: failing test → implementation → passing test → refactor
- [ ] CLI tool basic functions are working: `tickets create`, `tickets list`, `tickets show <id>`, `tickets update <id>`
- [ ] Unit tests cover ticket logic and validation rules
- [ ] Integration tests cover JSON file storage and CLI command behavior
- [ ] Error cases are tested: invalid input, ticket not found, missing/corrupted JSON file
- [ ] Setup instructions are documented: Installation, configuration, usage
- [ ] Questions about TDD, test types, and AI-assisted validation can be answered based on research and implementation
