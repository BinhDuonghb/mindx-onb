# Week 3 Architecture: CLI ↔ KB API Integration

**Authors:** ThuanTV, Cursor AI  
**Focus:** Extend CLI to query external Knowledge Base via HTTP API

---

## Current State

```
Week 2: CLI Tool
├─ build command
├─ list command
├─ TDD workflow and test coverage
└─ simple layers for commands, services, and storage

Week 3: Add KB Integration
├─ mock KB client for safe local tests
├─ HTTP KB client for real API calls
├─ kb search, kb list, kb retrieve, kb add commands
└─ same TDD workflow from Week 2
```

---

## Architecture

```
┌────────────────────┐
│   CLI Commands     │
├────────────────────┤
│ • kb search        │
│ • kb list          │
│ • kb retrieve      │
│ • kb add           │
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────┐
│ KBClient interface             │
├────────────────────────────────┤
│ (Interface)                    │
│ • search()                     │
│ • list()                       │
│ • retrieve()                   │
│ • add()                        │
└────────┬───────────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
MockKBClient   HTTPKBClient
(2-3 docs)     (Real KB server)
               └─→ HTTP POST
                   └─→ KB API
```

---

## KB Structure

Simple node-based hierarchy:

```
KB Root
├─ node-1 (/templates/email)
│  ├─ template-001.md
│  ├─ template-002.md
│  └─ README.md
│
├─ node-2 (/team/devops)
│  ├─ members.md
│  ├─ schedule.md
│  └─ README.md
│
└─ node-3 (/docs/guides)
   ├─ guide-001.md
   └─ guide-002.md
```

**Document Metadata:**
```typescript
interface Document {
  id: string;           // "doc-001"
  title: string;        // "Customer Response Template"
  content: string;      // Full markdown content
  nodePath: string;     // "/templates/email"
  tags: string[];       // ["template", "email"]
}
```

---

## API Contract

**Search:**
```json
POST /search
{
  "query": "response",
  "topK": 5
}

Response:
{
  "results": [
    {"id": "doc-001", "title": "...", "nodePath": "/templates/email"}
  ]
}
```

**List:**
```json
POST /list
{
  "nodePath": "/templates/email",
  "limit": 10
}
```

**Retrieve:**
```json
POST /retrieve
{
  "docId": "doc-001"
}
```

**Add:**
```json
POST /add
{
  "title": "New Template",
  "content": "...",
  "nodePath": "/templates/email",
  "tags": ["template"]
}
```

---

## Implementation Steps

### Days 1-2: Mock Client
1. Design KBClient interface
2. Implement MockKBClient with 2-3 test documents
3. Implement all 4 CLI commands
4. Test with mock data

### Days 3-4: HTTP Client
1. Implement HTTPKBClient (HTTP client + request builder)
2. Connect to real KB API
3. Integration testing
4. Documentation

---

## Technology Stack

- **Language:** TypeScript
- **CLI:** Commander.js
- **HTTP:** fetch or axios
- **Testing:** Jest
