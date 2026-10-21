import { Document, SearchQuery, ListQuery, AddDocumentRequest, SearchResult } from './types';

export class KBDatabase {
  private documents: Map<string, Document> = new Map();

  constructor() {
    this.initializeDefaultDocuments();
  }

  private initializeDefaultDocuments(): void {
    const defaults: Document[] = [
      {
        id: 'doc-001',
        title: 'Customer Response Template',
        content: '# Customer Response Template\n\nDear {{customer_name}},\n\nThank you for contacting us. We are reviewing your request and will respond shortly.\n\nBest regards,\nCustomer Support Team',
        nodePath: '/templates/email',
        tags: ['template', 'email']
      },
      {
        id: 'doc-002',
        title: 'DevOps Team Information',
        content: '# DevOps Team Information\n\nThe DevOps team maintains CI/CD pipelines, deployment infrastructure, and monitoring systems.',
        nodePath: '/team/devops',
        tags: ['team', 'devops']
      },
      {
        id: 'doc-003',
        title: 'Developer Guide',
        content: '# Developer Guide\n\nThis guide describes development setup, coding conventions, testing, and contribution workflows.',
        nodePath: '/docs/guides',
        tags: ['documentation', 'developer']
      }
    ];

    defaults.forEach(doc => this.documents.set(doc.id, doc));
  }

  search(query: SearchQuery): SearchResult[] {
    const keyword = query.query.trim().toLowerCase();
    const results: SearchResult[] = [];

    for (const doc of this.documents.values()) {
      const searchableText = [
        doc.title,
        doc.content,
        ...doc.tags
      ].join(' ').toLowerCase();

      if (searchableText.includes(keyword)) {
        results.push({
          id: doc.id,
          title: doc.title,
          nodePath: doc.nodePath
        });

        if (results.length >= query.topK) break;
      }
    }

    return results;
  }

  list(query: ListQuery): Document[] {
    let filtered = Array.from(this.documents.values());

    if (query.nodePath) {
      filtered = filtered.filter(doc => this.matchesNodePath(doc.nodePath, query.nodePath!));
    }

    return filtered.slice(0, query.limit);
  }

  retrieve(docId: string): Document | null {
    return this.documents.get(docId) || null;
  }

  add(request: AddDocumentRequest): Document | null {
    if (this.documents.has(request.id)) {
      return null;
    }

    const doc: Document = {
      id: request.id,
      title: request.title,
      content: request.content,
      nodePath: request.nodePath,
      tags: request.tags || []
    };

    this.documents.set(doc.id, doc);
    return doc;
  }

  private matchesNodePath(docPath: string, filterPath: string): boolean {
    const normalizedFilter = filterPath.replace(/\/$/, '');
    return (
      docPath === normalizedFilter ||
      docPath.startsWith(normalizedFilter + '/')
    );
  }

  getAllDocuments(): Document[] {
    return Array.from(this.documents.values());
  }
}
