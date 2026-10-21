export interface Document {
  id: string;
  title: string;
  content: string;
  nodePath: string;
  tags: string[];
}

export interface SearchQuery {
  query: string;
  topK: number;
}

export interface SearchResult {
  id: string;
  title: string;
  nodePath: string;
}

export interface ListQuery {
  nodePath?: string;
  limit: number;
}

export interface AddDocumentRequest {
  id: string;
  title: string;
  content: string;
  nodePath: string;
  tags?: string[];
}
