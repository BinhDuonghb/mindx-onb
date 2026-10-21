import express, { Express, Request, Response } from 'express';
import { KBDatabase } from './database';
import { SearchQuery, ListQuery, AddDocumentRequest } from './types';

const app: Express = express();
const PORT = 8000;

// Middleware
app.use(express.json());

// Initialize database
const db = new KBDatabase();

// POST /search - Search documents by query
app.post('/search', (req: Request, res: Response) => {
  try {
    const { query, topK = 5 } = req.body as Partial<SearchQuery>;

    if (!query) {
      return res.status(400).json({ error: 'query is required' });
    }

    const searchQuery: SearchQuery = { query, topK: topK || 5 };
    const results = db.search(searchQuery);

    res.json({
      results,
      count: results.length
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// POST /list - List documents with optional filters
app.post('/list', (req: Request, res: Response) => {
  try {
    const { nodePath, limit = 10 } = req.body as Partial<ListQuery>;

    const listQuery: ListQuery = {
      nodePath,
      limit: limit || 10
    };

    const results = db.list(listQuery);

    res.json({
      results,
      count: results.length,
      total: db.getAllDocuments().length
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// POST /retrieve - Retrieve a single document by ID
app.post('/retrieve', (req: Request, res: Response) => {
  try {
    const { docId } = req.body as { docId?: string };

    if (!docId) {
      return res.status(400).json({ error: 'docId is required' });
    }

    const doc = db.retrieve(docId);

    if (!doc) {
      return res.status(404).json({ error: `Document ${docId} not found` });
    }

    res.json(doc);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// POST /add - Add a new document
app.post('/add', (req: Request, res: Response) => {
  try {
    const { id, title, content, nodePath, tags = [] } = req.body as AddDocumentRequest;

    // Validate required fields
    if (!id || !title || !content || !nodePath) {
      return res.status(400).json({
        error: 'id, title, content, and nodePath are required'
      });
    }

    const doc = db.add({
      id,
      title,
      content,
      nodePath,
      tags: Array.isArray(tags) ? tags : []
    });

    if (!doc) {
      return res.status(409).json({ error: `Document ${id} already exists` });
    }

    res.status(201).json({
      message: 'Document added successfully',
      document: doc
    });
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// GET /health - Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', port: PORT });
});

// GET /docs - List all documents (for debugging)
app.get('/docs', (req: Request, res: Response) => {
  res.json(db.getAllDocuments());
});

// Start server
app.listen(PORT, () => {
  console.log(`✓ KB Service running on http://localhost:${PORT}`);
  console.log(`\nAvailable endpoints:`);
  console.log(`  POST /search   - Search documents`);
  console.log(`  POST /list     - List documents`);
  console.log(`  POST /retrieve - Retrieve a document`);
  console.log(`  POST /add      - Add a new document`);
  console.log(`  GET  /health   - Health check`);
  console.log(`  GET  /docs     - List all documents (debug)`);
});
