"""Knowledge base command parsers."""


def add_kb_commands(subparsers):
    """Add knowledge base commands to the parser."""
    # KB parent command
    kb_parser = subparsers.add_parser(
        "kb",
        help="Knowledge base operations",
        epilog="Use 'tickets kb <command> -h' for help on a specific command"
    )

    # KB subparsers
    kb_subparsers = kb_parser.add_subparsers(
        dest="kb_command",
        help="KB subcommands"
    )

    # KB SEARCH command
    kb_search_parser = kb_subparsers.add_parser(
        "search",
        help="Search knowledge base documents",
        epilog="""
Examples:
  tickets kb search "Template"
  tickets kb search "response" --top-k 3
  tickets kb search "email" --top-k 10
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
    kb_list_parser = kb_subparsers.add_parser(
        "list",
        help="List knowledge base documents",
        epilog="""
Examples:
  tickets kb list                                     # List all documents
  tickets kb list --node /templates/email            # List by path prefix
  tickets kb list --node /team/devops --limit 5      # Combine filters
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
    kb_retrieve_parser = kb_subparsers.add_parser(
        "retrieve",
        help="Retrieve a knowledge base document by ID",
        epilog="""
Examples:
  tickets kb retrieve doc-001
  tickets kb retrieve doc-002
        """
    )
    kb_retrieve_parser.add_argument(
        "id",
        help="Document ID (required)"
    )

    # KB ADD command
    kb_add_parser = kb_subparsers.add_parser(
        "add",
        help="Add a new document to knowledge base",
        epilog="""
Examples:
  Direct content:
    tickets kb add --id doc-new-001 --title "New Template" --content "Template content" --node /templates/email --tags "template,email"

  From file:
    tickets kb add --id doc-new-001 --file template.md --node /templates/email --tags "template,email"
    tickets kb add --id doc-new-001 --file template.md --path /templates/email
        """
    )
    kb_add_parser.add_argument(
        "--id",
        required=True,
        help="Document ID (required)"
    )
    kb_add_parser.add_argument(
        "--title",
        help="Document title (required for direct content, optional with --file)"
    )
    kb_add_parser.add_argument(
        "--content",
        help="Document content (use --content or --file, not both)"
    )
    kb_add_parser.add_argument(
        "--file",
        help="Path to file containing document content (use --file or --content, not both)"
    )
    kb_add_parser.add_argument(
        "--node",
        dest="node_path",
        help="Document node path (use --node or --path)"
    )
    kb_add_parser.add_argument(
        "--path",
        dest="path_alias",
        help="Alias for --node (use --node or --path)"
    )
    kb_add_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (optional, default: empty)"
    )

