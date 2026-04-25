from datetime import datetime

from pydantic import BaseModel, Field


class StyleConfig(BaseModel):
    """Manual style override configuration."""
    tone: str | None = Field(default=None, description="formal|professional|friendly|casual")
    addressing: str | None = Field(default=None, description="εσείς|εσύ|απρόσωπο")
    paragraph_length: str | None = Field(default=None, description="short|medium|long")
    technical_level: str | None = Field(default=None, description="high|medium|low")
    structure: str | None = Field(default=None, description="bullets|paragraphs|mixed")
    title_style: str | None = Field(default=None, description="question|statement|how-to")
    cta_style: str | None = Field(default=None, description="direct|indirect|none")
    sample_phrases: list[str] | None = Field(default=None, description="Φράσεις να χρησιμοποιηθούν")
    avoid_patterns: list[str] | None = Field(default=None, description="Patterns να αποφευχθούν")


class WorkflowInput(BaseModel):
    category_name: str = Field(..., description="Κύρια κατηγορία θέματος")
    seed_keywords: list[str] = Field(default_factory=list, description="Αρχικά keywords")
    location: str | None = Field(default=None, description="Τοποθεσία (π.χ. Αθήνα)")
    objective: str = Field(default="suggest_improvements", description="Στόχος workflow")
    style_config: StyleConfig | None = Field(default=None, description="Manual style override")
    site_url: str | None = Field(default=None, description="WordPress site URL (αν διαφέρει από default)")


class ProposalOut(BaseModel):
    id: int
    proposal_type: str
    target_title: str
    parent_pillar: str | None = None
    summary: str
    outline: str
    suggested_schema: str
    faq_suggestions: str | None = None
    schema_additions: str | None = None
    seo_meta_suggestions: str | None = None
    priority: str | None = None
    status: str

    model_config = {"from_attributes": True}


class StyleProfileOut(BaseModel):
    """Extracted/merged style profile."""
    tone: str | None = None
    addressing: str | None = None
    paragraph_length: str | None = None
    technical_level: str | None = None
    structure: str | None = None
    title_style: str | None = None
    cta_style: str | None = None
    summary: str | None = None


class TopologySummaryOut(BaseModel):
    """Summary of content topology analysis."""
    homepage_title: str | None = None
    pillars_count: int = 0
    satellites_count: int = 0
    orphans_count: int = 0
    coverage_gaps: list[str] = Field(default_factory=list)


class YoastSummaryOut(BaseModel):
    """Summary of Yoast SEO analysis."""
    pages_analyzed: int = 0
    total_issues: int = 0
    high_priority_issues: int = 0
    missing_focus_keyphrase: int = 0
    missing_meta_description: int = 0


class SchemaSummaryOut(BaseModel):
    """Summary of Schema.org analysis."""
    pages_with_schema: int = 0
    ai_readiness_score: float = 0.0
    has_faq_schema: bool = False
    has_howto_schema: bool = False
    schema_types_found: list[str] = Field(default_factory=list)


class WorkflowOutput(BaseModel):
    workflow_run_id: int
    category_name: str
    discovered_keywords: list[str]
    clusters_count: int
    site_pages_found: int
    style_profile: StyleProfileOut | None = None
    topology: TopologySummaryOut | None = None
    yoast_summary: YoastSummaryOut | None = None
    schema_summary: SchemaSummaryOut | None = None
    proposals: list[ProposalOut]
    status: str


class ProposalResponse(BaseModel):
    id: int
    workflow_run_id: int
    proposal_type: str
    target_title: str
    parent_pillar: str | None = None
    summary: str
    outline: str
    suggested_schema: str
    faq_suggestions: str | None = None
    schema_additions: str | None = None
    seo_meta_suggestions: str | None = None
    priority: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
