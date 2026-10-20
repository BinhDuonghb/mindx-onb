
from dataclasses import dataclass


@dataclass
class KBQuery:
    query: str
    top_k: int = 5


@dataclass
class SearchResult:
    id: str
    title: str
    node_path: str