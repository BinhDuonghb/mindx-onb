# KBService - Test Knowledge Base API

A lightweight Node.js/Express-based Knowledge Base API service designed for testing and integration with the TicketManagerCLI application.

## Purpose

KBService provides a simple HTTP API for document storage and retrieval operations. It's used as a test backend for the TicketManagerCLI's Knowledge Base (KB) commands. This service:

- Manages documents organized in hierarchical node paths
- Supports search, list, retrieve, and add operations
- Returns consistent JSON responses for CLI integration
- Persists data in memory during a session
- Serves as the reference implementation for KB integration

## Architecture

```
┌─────────────────────────────┐
│   TicketManagerCLI          │
│   (KB commands)             │
└──────────────┬──────────────┘
               │
        HTTP (port 8000)
               │
               ▼
┌─────────────────────────────┐
│   KBService (This)          │
│   ├─ /search (POST)         │
│   ├─ /list (POST)           │
│   ├─ /retrieve (POST)       │
│   ├─ /add (POST)            │
│   └─ /health (GET)          │
└─────────────────────────────┘
```

## Setup

### Prerequisites

- Node.js 18+ and npm
- TypeScript (installed via dependencies)

### Installation

```bash
cd d:\Study\mindx\mindx-onb\assignments\week3\KBService

# Install dependencies
npm install
```

### Build

```bash
npm run build
```

Compiles TypeScript source files in `src/` to JavaScript in `dist/`.

### Start the Service

```bash
npm start
```

The service listens on **http://localhost:8000** by default.

Expected output:
```
[KBService] Initializing database...
[KBService] Starting server on port 8000
```

## API Endpoints

### Health Check

**Request:**
```
GET /health
```

**Response:**
```json
{"status": "ok"}
```

### Search Documents

**Request:**
```
POST /search
Content-Type: application/json

{
  "query": "template",
  "topK": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc-001",
      "title": "Customer Response Template",
      "nodePath": "/templates/email",
      "tags": ["template", "email"]
    }
  ]
}
```

### List Documents

**Request:**
```
POST /list
Content-Type: application/json

{
  "nodePath": "/templates",
  "limit": 10
}
```

**Response:**
```json
{
  "documents": [
    {
      "id": "doc-001",
      "title": "Customer Response Template",
      "nodePath": "/templates/email"
    }
  ]
}
```

### Retrieve Document

**Request:**
```
POST /retrieve
Content-Type: application/json

{
  "docId": "doc-001"
}
```

**Response:**
```json
{
  "id": "doc-001",
  "title": "Customer Response Template",
  "content": "Dear customer...",
  "nodePath": "/templates/email",
  "tags": ["template", "email"]
}
```

### Add Document

**Request:**
```
POST /add
Content-Type: application/json

{
  "id": "doc-new",
  "title": "New Template",
  "content": "Document content here",
  "nodePath": "/templates/custom",
  "tags": ["new", "custom"]
}
```

**Response:**
```json
{
  "id": "doc-new",
  "title": "New Template",
  "message": "Document added successfully"
}
```

## Test Data

On startup, KBService initializes with sample documents for testing:

- **doc-001**: Customer Response Template (templates/email)
- **doc-002**: DevOps Team Information (team/devops)
- Plus additional documents for comprehensive testing

## Integration with TicketManagerCLI

### Configuration

Set environment variables in PowerShell or add to `.env`:

```powershell
# Use HTTP client to connect to KBService
$env:KB_CLIENT='http'
$env:KB_API_URL='http://localhost:8000'
```

Or in `.env` file:
```
KB_CLIENT=http
KB_API_URL=http://localhost:8000
```

### CLI Commands

Once KBService is running, CLI commands work end-to-end:

```bash
# Search
python main.py kb search "template"

# List documents in a path
python main.py kb list --node /templates

# Retrieve a document
python main.py kb retrieve doc-001

# Add a new document
python main.py kb add --id new-doc --title "New Title" \
  --content "Content" --node /templates/new
```

## Running Tests

### E2E Tests

Tests verify the full integration: KBService startup → CLI commands → API responses.

```bash
cd ..\TicketManagerCLI

# Run all e2e tests (starts KBService automatically)
python run_tests.py ./tests/e2e/test_kb_service_e2e.py -v

# Run specific test
python -m pytest tests/e2e/test_kb_service_e2e.py::TestKBServiceE2E::test_e2e_add_and_retrieve_document -v
```

### Manual Testing

```bash
# Terminal 1: Start KBService
cd d:\Study\mindx\mindx-onb\assignments\week3\KBService
npm start

# Terminal 2: Test with curl
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"template\", \"topK\": 5}"

curl -X GET http://localhost:8000/health
```

## Project Structure

```
KBService/
├── src/
│   ├── server.ts          # Express server and routes
│   ├── database.ts        # In-memory document storage
│   ├── types.ts           # TypeScript interfaces
│   └── index.ts           # Entry point (if used)
├── dist/                  # Compiled JavaScript (generated)
├── package.json           # Dependencies and build scripts
├── tsconfig.json          # TypeScript configuration
└── README.md              # This file
```

## Troubleshooting

### Port 8000 Already in Use

```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

Then start the service again.

### TypeScript Compilation Errors

```bash
# Clean and rebuild
rm -r dist
npm run build
```

### E2E Tests Fail to Connect

- Verify KBService is running: `curl http://localhost:8000/health`
- Check environment variables are set: `set | findstr KB_`
- Increase timeout if on slow machine (edit `KB_SERVICE_START_TIMEOUT` in e2e test)

### Service Exits Immediately

Check for startup errors:
```bash
npm start 2>&1 | head -20
```

## Development

### Add New Documents to Test Data

Edit `src/database.ts` and add entries to the sample data initialization.

### Modify API Endpoints

Edit `src/server.ts` and define new route handlers. Remember to compile with `npm run build`.

### Run in Development Mode (with ts-node)

```bash
npm run dev
```

This uses ts-node to run TypeScript directly without compilation.

## API Error Responses

All errors follow this format:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common status codes:
- `200` - Success
- `400` - Bad request (missing required fields)
- `404` - Document not found
- `500` - Server error

## Notes

- Data is **not persisted** between restarts (in-memory only)
- Service is designed for testing, not production use
- All responses are JSON
- CORS is not enabled (CLI calls from same machine)

## Reference

- [Architecture Plan](../../docs/plans/week-3/architecture.md) - API contract and design
- [Week 3 Tasks](../../docs/plans/week-3/tasks.md) - Implementation requirements
- [TicketManagerCLI KB Integration](../TicketManagerCLI/KB/) - CLI KB client implementation
