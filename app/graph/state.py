from typing import TypedDict


class WorkflowState(TypedDict, total=False):
    # Input
    category_name: str
    seed_keywords: list[str]
    location: str | None
    objective: str
    style_config: dict | None  # Manual style override from user
    site_url: str | None  # Override WordPress site URL

    # Keyword discovery results
    discovered_keywords: list[str]
    clusters: list[dict]

    # WordPress content
    site_pages: list[dict]
    categories: dict[int, str]  # Category id -> name mapping

    # Style analysis
    style_profile: dict  # Extracted + merged style profile

    # Content topology
    content_topology: dict  # Pillars, satellites, homepage, link graph

    # Yoast SEO analysis
    yoast_analysis: dict  # SEO issues, meta data, focus keyphrases

    # Schema analysis
    schema_analysis: dict  # Existing schemas, AI readiness, suggestions

    # Analysis results
    analysis_result: dict
    proposals: list[dict]

    # Metadata
    workflow_run_id: int
    status: str
    error: str | None
