import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.graph.workflow import workflow
from app.models import ContentProposal, WorkflowRun
from app.schemas import (
    ProposalOut,
    ProposalResponse,
    SchemaSummaryOut,
    StyleProfileOut,
    TopologySummaryOut,
    WorkflowInput,
    WorkflowOutput,
    YoastSummaryOut,
)
from app.services.content_generator import ContentGenerator
from app.services.homepage_service import HomepageService
from app.services.proposal_service import ProposalService
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.topology_service import TopologyService
from app.services.wordpress_service import WordPressService
from app.services.yoast_service import YoastService


class GenerateHtmlRequest(BaseModel):
    """Request body for HTML generation with optional custom instructions."""
    custom_instructions: Optional[str] = None


class HomepageGenerateRequest(BaseModel):
    """Request body for AI homepage structure and copy generation."""
    custom_instructions: Optional[str] = None


class ProposalStatusUpdate(BaseModel):
    """Request body for manually reviewing a proposal."""
    status: Literal["needs_review", "approved", "rejected"]


logger = logging.getLogger(__name__)
router = APIRouter()
proposal_service = ProposalService()
content_generator = ContentGenerator()
VALID_PROPOSAL_STATUSES = {"needs_review", "approved", "rejected"}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "seo-agent-mvp"}


@router.get("/site/audit")
def audit_site(site_url: str | None = None, include_pages: bool = False) -> dict:
    """
    Run a fast deterministic site audit without generating proposals.
    This reads WordPress content and returns topology, Yoast, and schema summaries.
    """
    logger.info("Starting site audit for site: %s", site_url or "default")

    try:
        wp = WordPressService(base_url=site_url)
        site_pages = wp.fetch_all_content()
        categories = wp.fetch_categories()

        topology_service = TopologyService()
        topology = topology_service.analyze_topology(site_pages, categories)
        homepage_analysis = HomepageService().analyze(site_pages, topology)

        yoast_service = YoastService()
        yoast_analysis = yoast_service.analyze_seo_data(site_pages)

        schema_analysis = SchemaAnalyzer().analyze_schemas(site_pages)
        post_type_counts: dict[str, int] = {}
        for page in site_pages:
            post_type = page.get("post_type", "unknown")
            post_type_counts[post_type] = post_type_counts.get(post_type, 0) + 1

        audit = {
            "site_url": site_url or wp.base_url,
            "site_pages_found": len(site_pages),
            "post_type_counts": post_type_counts,
            "topology": {
                "homepage": topology.get("homepage"),
                "pillars_count": len(topology.get("pillars", [])),
                "satellites_count": len(topology.get("satellites", [])),
                "orphans_count": len(topology.get("orphans", [])),
                "orphan_pages": [
                    {"title": p.get("title"), "slug": p.get("slug")}
                    for p in topology.get("orphans", [])[:20]
                ],
            },
            "homepage": homepage_analysis,
            "yoast": {
                "pages_with_yoast": yoast_analysis.get("pages_with_yoast", 0),
                "pages_without_yoast": yoast_analysis.get("pages_without_yoast", 0),
                "total_issues": yoast_analysis.get("total_issues", 0),
                "issue_summary": yoast_analysis.get("issue_summary", {}),
                "priority_pages": yoast_service.get_optimization_priorities(yoast_analysis),
            },
            "schema": {
                "pages_with_schema": schema_analysis.get("pages_with_schema", 0),
                "schema_coverage_percent": schema_analysis.get("schema_coverage_percent", 0),
                "ai_readiness_score": schema_analysis.get("ai_readiness_score", 0),
                "schema_types_found": schema_analysis.get("schema_types_found", {}),
                "improvement_suggestions": schema_analysis.get("improvement_suggestions", [])[:10],
            },
        }

        if include_pages:
            audit["pages"] = [
                {
                    "title": page.get("title"),
                    "slug": page.get("slug"),
                    "url": page.get("url"),
                    "post_type": page.get("post_type"),
                    "has_yoast": page.get("yoast", {}).get("available", False),
                    "schema_types": page.get("yoast", {}).get("schema_types", []),
                }
                for page in site_pages
            ]

        return audit
    except Exception as e:
        logger.exception("Site audit failed")
        raise HTTPException(status_code=500, detail=f"Site audit failed: {str(e)}")


@router.get("/site/homepage-guidance")
def homepage_guidance(site_url: str | None = None) -> dict:
    """
    Build a homepage-specific correction plan from site-wide content and topology.
    """
    logger.info("Starting homepage guidance for site: %s", site_url or "default")

    try:
        wp = WordPressService(base_url=site_url)
        site_pages = wp.fetch_all_content()
        categories = wp.fetch_categories()
        topology = TopologyService().analyze_topology(site_pages, categories)
        guidance = HomepageService().build_guidance(site_pages, topology)

        return {
            "site_url": site_url or wp.base_url,
            "site_pages_found": len(site_pages),
            "guidance": guidance,
        }
    except Exception as e:
        logger.exception("Homepage guidance failed")
        raise HTTPException(status_code=500, detail=f"Homepage guidance failed: {str(e)}")


@router.post("/site/homepage-generate")
def generate_homepage_plan(
    request: HomepageGenerateRequest = None,
    site_url: str | None = None,
) -> dict:
    """
    Generate an AI-assisted homepage structure, draft copy, visual guidance, and Yoast meta plan.
    """
    logger.info("Starting AI homepage generation for site: %s", site_url or "default")

    try:
        wp = WordPressService(base_url=site_url)
        site_pages = wp.fetch_all_content()
        categories = wp.fetch_categories()
        topology = TopologyService().analyze_topology(site_pages, categories)
        custom_instructions = request.custom_instructions if request else None

        result = HomepageService().generate_ai_homepage_plan(
            site_pages=site_pages,
            topology=topology,
            custom_instructions=custom_instructions,
        )

        return {
            "site_url": site_url or wp.base_url,
            "site_pages_found": len(site_pages),
            "result": result,
        }
    except Exception as e:
        logger.exception("AI homepage generation failed")
        raise HTTPException(status_code=500, detail=f"Homepage generation failed: {str(e)}")


@router.post("/site/cache/clear")
def clear_site_cache(site_url: str | None = None) -> dict:
    WordPressService.clear_cache(site_url)
    return {
        "status": "ok",
        "message": "WordPress cache cleared",
        "site_url": site_url,
    }


@router.post("/workflow/run", response_model=WorkflowOutput)
def run_workflow(payload: WorkflowInput, db: Session = Depends(get_db)) -> WorkflowOutput:
    logger.info("Starting workflow for category: %s", payload.category_name)

    workflow_run = WorkflowRun(
        category_name=payload.category_name,
        site_url=payload.site_url,
        status="running",
    )
    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)

    try:
        state = workflow.invoke({
            "category_name": payload.category_name,
            "seed_keywords": payload.seed_keywords,
            "location": payload.location,
            "objective": payload.objective,
            "style_config": payload.style_config.model_dump(exclude_none=True) if payload.style_config else None,
            "site_url": payload.site_url,
            "workflow_run_id": workflow_run.id,
            "status": "running",
        })

        if state.get("error"):
            workflow_run.status = "error"
            db.commit()
            raise HTTPException(status_code=500, detail=state["error"])

        proposals = proposal_service.persist_proposals(
            db=db,
            workflow_run_id=workflow_run.id,
            proposals=state.get("proposals", []),
        )

        workflow_run.status = state.get("status", "needs_review")
        db.commit()

        # Build style profile output
        style_profile_data = state.get("style_profile")
        style_profile_out = None
        if style_profile_data:
            style_profile_out = StyleProfileOut(
                tone=style_profile_data.get("tone"),
                addressing=style_profile_data.get("addressing"),
                paragraph_length=style_profile_data.get("paragraph_length"),
                technical_level=style_profile_data.get("technical_level"),
                structure=style_profile_data.get("structure"),
                title_style=style_profile_data.get("title_style"),
                cta_style=style_profile_data.get("cta_style"),
                summary=style_profile_data.get("summary"),
            )

        # Build topology summary output
        topology_data = state.get("content_topology")
        topology_out = None
        if topology_data:
            homepage = topology_data.get("homepage")
            coverage_gaps = topology_data.get("coverage_gaps", [])
            topology_out = TopologySummaryOut(
                homepage_title=homepage.get("title") if homepage else None,
                pillars_count=len(topology_data.get("pillars", [])),
                satellites_count=len(topology_data.get("satellites", [])),
                orphans_count=len(topology_data.get("orphans", [])),
                coverage_gaps=[
                    f"{g.get('pillar_title', 'N/A')}: {g.get('current_satellites', 0)}/{g.get('suggested_minimum', 3)} satellites"
                    for g in coverage_gaps[:5]
                ],
            )

        # Build Yoast summary output
        yoast_data = state.get("yoast_analysis")
        yoast_out = None
        if yoast_data:
            issue_summary = yoast_data.get("issue_summary", {})
            by_severity = issue_summary.get("by_severity", {})
            by_type = issue_summary.get("by_type", {})
            yoast_out = YoastSummaryOut(
                pages_analyzed=yoast_data.get("pages_with_yoast", 0),
                total_issues=yoast_data.get("total_issues", 0),
                high_priority_issues=by_severity.get("high", 0),
                missing_focus_keyphrase=by_type.get("missing_focus_keyphrase", 0),
                missing_meta_description=by_type.get("missing_meta_description", 0),
            )

        # Build Schema summary output
        schema_data = state.get("schema_analysis")
        schema_out = None
        if schema_data:
            schema_types = schema_data.get("schema_types_found", {})
            schema_out = SchemaSummaryOut(
                pages_with_schema=schema_data.get("pages_with_schema", 0),
                ai_readiness_score=schema_data.get("ai_readiness_score", 0),
                has_faq_schema="FAQPage" in schema_types,
                has_howto_schema="HowTo" in schema_types,
                schema_types_found=list(schema_types.keys())[:10],
            )

        return WorkflowOutput(
            workflow_run_id=workflow_run.id,
            category_name=payload.category_name,
            discovered_keywords=state.get("discovered_keywords", []),
            clusters_count=len(state.get("clusters", [])),
            site_pages_found=len(state.get("site_pages", [])),
            style_profile=style_profile_out,
            topology=topology_out,
            yoast_summary=yoast_out,
            schema_summary=schema_out,
            proposals=[
                ProposalOut(
                    id=p.id,
                    proposal_type=p.proposal_type,
                    target_title=p.target_title,
                    parent_pillar=p.parent_pillar,
                    summary=p.summary,
                    outline=p.outline,
                    suggested_schema=p.suggested_schema,
                    faq_suggestions=p.faq_suggestions,
                    schema_additions=p.schema_additions,
                    seo_meta_suggestions=p.seo_meta_suggestions,
                    priority=p.priority,
                    status=p.status,
                )
                for p in proposals
            ],
            status=workflow_run.status,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Workflow execution failed")
        workflow_run.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals", response_model=list[ProposalResponse])
def get_proposals(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[ContentProposal]:
    query = db.query(ContentProposal).order_by(ContentProposal.id.desc())

    if status:
        if status not in VALID_PROPOSAL_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid proposal status")
        query = query.filter(ContentProposal.status == status)

    return query.all()


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)) -> ContentProposal:
    proposal = db.query(ContentProposal).filter(ContentProposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return proposal


@router.patch("/proposals/{proposal_id}/status", response_model=ProposalResponse)
def update_proposal_status(
    proposal_id: int,
    payload: ProposalStatusUpdate,
    db: Session = Depends(get_db),
) -> ContentProposal:
    proposal = db.query(ContentProposal).filter(ContentProposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.status = payload.status
    db.commit()
    db.refresh(proposal)

    logger.info("Proposal %d status updated to %s", proposal_id, payload.status)
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
def approve_proposal(proposal_id: int, db: Session = Depends(get_db)) -> ContentProposal:
    return update_proposal_status(
        proposal_id=proposal_id,
        payload=ProposalStatusUpdate(status="approved"),
        db=db,
    )


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalResponse)
def reject_proposal(proposal_id: int, db: Session = Depends(get_db)) -> ContentProposal:
    return update_proposal_status(
        proposal_id=proposal_id,
        payload=ProposalStatusUpdate(status="rejected"),
        db=db,
    )


@router.get("/proposals/{proposal_id}/preview")
def get_proposal_preview(proposal_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Generate a preview of the proposed changes.
    Returns side-by-side comparison of current vs proposed content.
    """
    proposal = db.query(ContentProposal).filter(ContentProposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == proposal.workflow_run_id).first()
    site_url = workflow_run.site_url if workflow_run else None

    logger.info("Generating preview for proposal %d: %s", proposal_id, proposal.proposal_type)

    try:
        # Convert SQLAlchemy model to dict
        proposal_dict = {
            "id": proposal.id,
            "proposal_type": proposal.proposal_type,
            "target_title": proposal.target_title,
            "parent_pillar": proposal.parent_pillar,
            "summary": proposal.summary,
            "outline": proposal.outline,
            "suggested_schema": proposal.suggested_schema,
            "faq_suggestions": proposal.faq_suggestions,
            "schema_additions": proposal.schema_additions,
            "seo_meta_suggestions": proposal.seo_meta_suggestions,
            "priority": proposal.priority,
            "site_url": site_url,
        }

        preview = content_generator.generate_preview(proposal_dict)

        return {
            "proposal_id": proposal_id,
            "proposal_type": proposal.proposal_type,
            "target_title": proposal.target_title,
            "preview": preview,
        }

    except Exception as e:
        logger.exception("Error generating preview for proposal %d", proposal_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


@router.post("/proposals/{proposal_id}/generate-html")
def generate_full_html(
    proposal_id: int,
    request: GenerateHtmlRequest = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Generate full HTML content for a proposal, ready for Elementor copy-paste.
    Saves the content to a file and returns the HTML and metadata.

    Optionally accepts custom_instructions to guide the AI generation.
    """
    proposal = db.query(ContentProposal).filter(ContentProposal.id == proposal_id).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get site_url from the workflow run
    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == proposal.workflow_run_id).first()
    site_url = workflow_run.site_url if workflow_run else None

    # Get custom instructions if provided
    custom_instructions = request.custom_instructions if request else None

    logger.info(
        "Generating full HTML for proposal %d: %s (site: %s, custom: %s)",
        proposal_id, proposal.target_title, site_url,
        "yes" if custom_instructions else "no"
    )

    try:
        proposal_dict = {
            "id": proposal.id,
            "proposal_type": proposal.proposal_type,
            "target_title": proposal.target_title,
            "parent_pillar": proposal.parent_pillar,
            "summary": proposal.summary,
            "outline": proposal.outline,
            "suggested_schema": proposal.suggested_schema,
            "faq_suggestions": proposal.faq_suggestions,
            "schema_additions": proposal.schema_additions,
            "seo_meta_suggestions": proposal.seo_meta_suggestions,
            "priority": proposal.priority,
            "site_url": site_url,
            "custom_instructions": custom_instructions,
        }

        result = content_generator.generate_full_html(proposal_dict, site_url=site_url)

        return {
            "proposal_id": proposal_id,
            "target_title": proposal.target_title,
            "result": result,
        }

    except Exception as e:
        logger.exception("Error generating full HTML for proposal %d", proposal_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate HTML: {str(e)}")
