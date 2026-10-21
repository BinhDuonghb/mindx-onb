"""Knowledge base command parsers."""


def add_kb_commands(subparsers):
    """Add knowledge base commands to the parser."""
    # KB SEARCH command
    kb_search_parser = subparsers.add_parser(
        "kb-search",
        help="Search knowledge base documents",
        epilog="""
Examples:
  tickets kb-search "Template"
  tickets kb-search "CI/CD" --top-k 5
  tickets kb-search "email" --top-k 10
        """
    )
    kb_search_parser.add_argument(
        "query",
        help="Search query (required)"
    )
    kb_search_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of results to return (optional, default: 5)"
    )

    # KB LIST command
    kb_list_parser = subparsers.add_parser(
        "kb-list",
        help="List knowledge base documents",
        epilog="""
Examples:
  tickets kb-list                                     # List all documents
  tickets kb-list --node /templates/email            # List by path prefix
  tickets kb-list --node /team/devops --limit 5      # Combine filters
        """
    )
    kb_list_parser.add_argument(
        "--node",
        dest="node_path",
        default=None,
        help="Filter by node path prefix (optional)"
    )
    kb_list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of documents to return (optional, default: 10)"
    )

    # KB RETRIEVE command
    kb_retrieve_parser = subparsers.add_parser(
        "kb-retrieve",
        help="Retrieve a knowledge base document by ID",
        epilog="""
Examples:
  tickets kb-retrieve doc-001
  tickets kb-retrieve doc-002
        """
    )
    kb_retrieve_parser.add_argument(
        "id",
        help="Document ID (required)"
    )

    # KB ADD command
    kb_add_parser = subparsers.add_parser(
        "kb-add",
        help="Add a new document to knowledge base",
        epilog="""
Examples:
  tickets kb-add --id doc-new-001 --title "New Template" --content "Template content" --node /templates/email --tags "template,email"
        """
    )
    kb_add_parser.add_argument(
        "--id",
        required=True,
        help="Document ID (required)"
    )
    kb_add_parser.add_argument(
        "--title",
        required=True,
        help="Document title (required)"
    )
    kb_add_parser.add_argument(
        "--content",
        required=True,
        help="Document content (required)"
    )
    kb_add_parser.add_argument(
        "--node",
        dest="node_path",
        required=True,
        help="Document node path (required)"
    )
    kb_add_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (optional, default: empty)"
    )
