from KB.models.document import Document


SAMPLE_DOCUMENTS: list[Document] = [
    Document(
        id="doc-001",
        title="Customer Response Template",
        content=(
            "# Customer Response Template\n\n"
            "Dear {{customer_name}},\n\n"
            "Thank you for contacting us. "
            "We are reviewing your request and will respond shortly.\n\n"
            "Best regards,\n"
            "Customer Support Team"
        ),
        node_path="/templates/email",
        tags=["template", "email"],
    ),
    Document(
        id="doc-002",
        title="DevOps Team Information",
        content=(
            "# DevOps Team Information\n\n"
            "The DevOps team maintains CI/CD pipelines, "
            "deployment infrastructure, and monitoring systems."
        ),
        node_path="/team/devops",
        tags=["team", "devops"],
    ),
    Document(
        id="doc-003",
        title="Developer Guide",
        content=(
            "# Developer Guide\n\n"
            "This guide describes development setup, "
            "coding conventions, testing, and contribution workflows."
        ),
        node_path="/docs/guides",
        tags=["documentation", "developer"],
    ),
]