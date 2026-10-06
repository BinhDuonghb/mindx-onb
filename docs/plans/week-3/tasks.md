# Week 3 Tasks: Integrating CLI with Knowledge Base

**Authors:** ThuanTV, Cursor AI  
**Focus:** Build Knowledge Base CLI with API integration

---

## 🔧 Sys Admin / DevOps Setup

**Required Access:**
- TypeScript/Node.js development environment
- HTTP client library for API calls
- Access to KB API server (mock or real)

---

## Week 3 Overview

Week 3 focuses on **integrating CLI with external Knowledge Base API**. Real-world use cases: query email templates, business documents, team information, FAQs, etc.

**Days 1-2: Foundation & Mock Client**
- Learn KB API contract
- Build mock KB client with 2-3 minimal test documents
- Implement domain entities (Document, SearchResult)
- Create CLI commands (kb search, kb list, kb retrieve, kb add)
- All working with mock data

**Days 3-4: HTTP Client & Real Integration**
- Build HTTP client for real KB API
- Connect to production KB service
- Test all 4 commands with real data
- Integration testing and documentation

---

## Learning Hints: Self-Direction & AI Usage

### Where to Start
- Read: architecture.md (Key Concepts section)
- Understand: What real KB data looks like (templates, docs, team info)
- Code: Start with domain entities (Document interface)

### Key Points to Learn
1. **API Contract:** JSON request/response format
2. **Mock-first integration:** Mock client vs HTTP client
3. **Real-world KB types:** Templates, documents, team info, etc.
4. **Error handling:** Graceful failure for missing/invalid data

### Plan to Follow
1. Write tests for expected KB command behavior
2. Mock client (simple, in-memory)
3. CLI commands (use the mock client first)
4. HTTP client (same behavior against real API)
5. Tests (validate both clients work)

### Troubleshooting
- **API unclear?** → Check API structure in architecture.md
- **Mock vs real API behavior differs?** → Add a failing test that shows the difference, then fix the client behavior
- **HTTP calls?** → Test with curl first before CLI integration

---

## Days 1-2: Foundation & Mock Client

### Objective

Understand KB API contract and implement a minimal mock client to test expected behavior locally.

### Tasks

1. **Learn KB API Contract**
   - Read: architecture.md (Key Concepts section)
   - Understand: Real KB use cases (templates, docs, team info)
   - Understand: JSON request/response format

2. **Design Domain Entities**
   - Document interface (id, title, content, nodePath, tags)
   - SearchResult interface (document, matchType)
   - KBQuery interface (query, filters, topK)

3. **Implement Mock Client (Minimal)**
   - Create a KB client interface for search, list, retrieve, and add
   - Implement MockKBClient with 2-3 test documents (e.g., 1 email template + 1 team doc)
   - Implement all 4 operations: search, list, retrieve, add
   - Keep it simple - just enough to test behavior

4. **Implement All 4 CLI Commands**
   - `kb search "response" --top-k 3`
   - `kb list --node /templates/email --limit 10`
   - `kb retrieve doc-001`
   - `kb add --file new-template.md --path /templates/sms --tags sms`

### Deliverables

- Domain entities TypeScript interfaces
- MockKBClient with minimal data (2-3 docs)
- All 4 CLI commands working with mock client
- Examples: query template, lookup team info

---

## Days 3-4: HTTP Client & Real Integration

### Objective

Implement HTTP client to call real KB API and validate all operations work end-to-end.

### Tasks

1. **Study HTTP API Integration**
   - Read: architecture.md (API Protocol section)
   - Understand: HTTP client setup (fetch/axios)
   - Review: Real KB API endpoints

2. **Implement HTTP Client**
   - HTTPKBClient follows the same behavior as MockKBClient
   - HTTP client for all 4 operations
   - JSON request/response builder
   - Error handling and logging

3. **Integration Testing**
   - Test all 4 commands with mock client (regression)
   - Test all 4 commands with HTTP client (real KB)
   - Client switching via environment variable
   - All tests pass

### Deliverables

- HTTPKBClient implementation
- Integration tests (both clients)
- CLI commands fully tested end-to-end
- Setup guide for KB API connection

---

## Day 5: Documentation & Final Validation

### Objective

Document architecture and deployment guide, then validate all acceptance criteria are met.

### Tasks

1. **Architecture Documentation**
   - Diagram: CLI → KB client interface → MockKBClient/HTTPKBClient
   - Document API contract (request/response format)

2. **Setup & Deployment Guide**
   - How to run with mock client (development)
   - How to run with HTTP client (production)
   - Environment variable configuration

3. **Final Validation**
   - All 4 acceptance criteria from overview met
   - Tests pass (both clients)
   - Code follows Week 2 TDD and simple-layer approach
   - Documentation complete and clear

### Deliverables

- Architecture diagram and API contract documentation
- Setup & deployment guide
- Complete project with tests and documentation

---

## Tips & Best Practices

### Mock-first Integration
- Mock client first (simple, testable)
- HTTP client second (production-ready)
- Same behavior = easy to compare and test

### CLI Design
- Clear command names (kb search, kb add)
- Help text for each command
- Error messages tell user what went wrong
- Options: --node, --limit, --top-k, --tags, --file, --path

### Testing
- Test mock client thoroughly
- Integration tests for end-to-end flow
- Test error cases (invalid input, missing files)
- Both clients independently testable

### Documentation
- Why each piece exists (not just what)
- Show data flow (user input → client → results)
- Include API examples
- Setup steps for both mock and production

### API Integration
- Use fetch or axios for HTTP calls
- Handle JSON request/response format
- Error handling: connection, parsing, API errors
- Logging to debug integration issues

---

## Reference Materials

- `/docs/plans/week-2/overview.md` - TDD and CLI foundation
- `architecture.md` - API contract and KB structure
