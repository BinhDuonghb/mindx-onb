from ticket_manager.models.ticket import Ticket


def get_seed_data() -> list[Ticket]:
    """Return predefined sample tickets for seeding."""
    return [
        Ticket(
            id=None,
            title="Fix login authentication bug",
            description="Users are unable to login with correct credentials. Error 500 returned.",
            status="open",
            priority="high",
            tags=["bug", "auth", "critical"],
            creator="dev@company.com",
            assignee="qa@company.com",
            estimated_time=4.5
        ),
        Ticket(
            id=None,
            title="Implement dark mode theme",
            description="Add dark mode toggle to user preferences. Should respect system theme.",
            status="open",
            priority="medium",
            tags=["feature", "frontend", "ui"],
            creator="designer@company.com",
            assignee="frontend@company.com",
            estimated_time=8.0
        ),
        Ticket(
            id=None,
            title="Optimize database query performance",
            description="Dashboard page loads slowly. Profile queries and optimize N+1 problems.",
            status="in-progress",
            priority="high",
            tags=["performance", "backend", "database"],
            creator="devops@company.com",
            assignee="senior-backend@company.com",
            estimated_time=6.0
        ),
        Ticket(
            id=None,
            title="Update API documentation",
            description="Add missing endpoints to OpenAPI spec and update examples.",
            status="open",
            priority="low",
            tags=["documentation", "api"],
            creator="tech-lead@company.com",
            assignee="junior-dev@company.com",
            estimated_time=3.0
        ),
        Ticket(
            id=None,
            title="Set up CI/CD pipeline",
            description="Implement automated testing and deployment to staging/production.",
            status="closed",
            priority="high",
            tags=["devops", "infrastructure", "automation"],
            creator="devops@company.com",
            assignee="devops@company.com",
            estimated_time=12.0
        ),
        Ticket(
            id=None,
            title="Fix memory leak in user service",
            description="Memory usage increases over time. Investigate cached objects and connection pooling.",
            status="in-progress",
            priority="high",
            tags=["bug", "performance", "backend"],
            creator="senior-dev@company.com",
            assignee="backend@company.com",
            estimated_time=5.0
        ),
        Ticket(
            id=None,
            title="Add unit tests for payment module",
            description="Coverage for payment processing is below 60%. Add tests for edge cases.",
            status="open",
            priority="medium",
            tags=["testing", "payment", "quality"],
            creator="qa-lead@company.com",
            assignee="qa@company.com",
            estimated_time=7.0
        ),
        Ticket(
            id=None,
            title="Implement email notification system",
            description="Send email notifications for important user actions. Integrate with SendGrid.",
            status="open",
            priority="medium",
            tags=["feature", "notifications", "backend"],
            creator="product@company.com",
            assignee="backend@company.com",
            estimated_time=9.0
        ),
        Ticket(
            id=None,
            title="Update dependencies and security patches",
            description="Update npm packages to latest versions. Review and apply security patches.",
            status="closed",
            priority="high",
            tags=["maintenance", "security", "dependencies"],
            creator="devops@company.com",
            assignee="frontend@company.com",
            estimated_time=4.0
        ),
        Ticket(
            id=None,
            title="Design database schema for analytics",
            description="Plan tables and relationships for event tracking and analytics.",
            status="open",
            priority="medium",
            tags=["database", "analytics", "design"],
            creator="architect@company.com",
            assignee="senior-dev@company.com",
            estimated_time=6.5
        ),
        Ticket(
            id=None,
            title="Create user onboarding flow",
            description="Design and implement step-by-step onboarding tutorial for new users.",
            status="in-progress",
            priority="medium",
            tags=["feature", "frontend", "ux"],
            creator="product@company.com",
            assignee="frontend@company.com",
            estimated_time=10.0
        ),
        Ticket(
            id=None,
            title="Fix SSL certificate expiration warning",
            description="Renew SSL certificate for production domain. Update certificate chain.",
            status="closed",
            priority="high",
            tags=["infrastructure", "security", "production"],
            creator="devops@company.com",
            assignee="devops@company.com",
            estimated_time=2.0
        ),
        Ticket(
            id=None,
            title="Implement rate limiting for API",
            description="Prevent API abuse by implementing rate limiting. Use Redis for tracking.",
            status="open",
            priority="high",
            tags=["security", "api", "backend"],
            creator="security@company.com",
            assignee="senior-dev@company.com",
            estimated_time=5.5
        ),
        Ticket(
            id=None,
            title="Add search functionality to dashboard",
            description="Allow users to search tickets and users. Implement full-text search with Elasticsearch.",
            status="open",
            priority="medium",
            tags=["feature", "search", "frontend"],
            creator="product@company.com",
            assignee="frontend@company.com",
            estimated_time=8.5
        ),
        Ticket(
            id=None,
            title="Improve error handling and logging",
            description="Add structured logging. Implement better error messages and monitoring.",
            status="in-progress",
            priority="medium",
            tags=["quality", "backend", "monitoring"],
            creator="tech-lead@company.com",
            assignee="senior-dev@company.com",
            estimated_time=7.0
        ),
        Ticket(
            id=None,
            title="Create admin dashboard",
            description="Build admin panel for user management, analytics, and system configuration.",
            status="open",
            priority="low",
            tags=["feature", "admin", "frontend"],
            creator="product@company.com",
            assignee="frontend@company.com",
            estimated_time=15.0
        ),
        Ticket(
            id=None,
            title="Migrate legacy code to new framework",
            description="Refactor old authentication module to use new framework and patterns.",
            status="closed",
            priority="medium",
            tags=["refactor", "backend", "maintenance"],
            creator="tech-lead@company.com",
            assignee="senior-dev@company.com",
            estimated_time=11.0
        ),
    ]
