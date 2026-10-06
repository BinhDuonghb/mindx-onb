# Week 3: Integrate CLI with Knowledge Base API

## Objectives

Extend the CLI tool from Week 2 to integrate with an external Knowledge Base API. Learn to query structured knowledge bases for real-world use cases (email templates, business documents, team information, etc.).

**Focus Areas:**

- Understand KB API contract and integration patterns
- Implement HTTP client module to call external KB API
- Build CLI commands for KB operations (search, list, retrieve, add)
- Apply TDD and mock-based testing from Week 2 for safe API integration

**Training Materials:**

- AI Training Slides: [`slides-ai-training.md`](../../../slides-ai-training.md) - Controlled AI Usage and validation

### Week 3 Focus: KB API Integration

This week extends the CLI tool from Week 2 to integrate with an external Knowledge Base API. Real-world example: query KB for email templates, business documents, or team information. Candidates will implement a mock KB client first, then an HTTP KB client, while keeping CLI commands (`kb search`, `kb list`, `kb retrieve`, `kb add`) covered by tests.

## Key Concepts

**API Protocol:** Simple JSON request/response over HTTP to communicate with KB server

**Mock-first API integration:** Mock KB client for learning/testing, HTTP KB client for production - teaches safe integration before calling real services

**Node-based Structure:** Documents organized in hierarchical nodes (/docs/guides, /docs/api, etc.)

## Acceptance Criteria

- [ ] CLI can query external Knowledge Base API for real-world use cases (templates, documents, team info)
- [ ] Both mock and HTTP clients work correctly, swappable via environment variable
- [ ] All 4 commands (search, list, retrieve, add) functional end-to-end
- [ ] Integration with real KB API tested and documented
