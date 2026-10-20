
from dataclasses import dataclass


@dataclass
class Document:
    id: str
    title: str
    content: str
    node_path: str
    tags: list[str]