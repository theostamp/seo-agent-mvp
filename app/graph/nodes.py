import logging

from app.graph.state import WorkflowState
from app.services.analysis_service import AnalysisService
from app.services.keyword_service import KeywordService
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.style_service import StyleService
from app.services.topology_service import TopologyService
from app.services.wordpress_service import WordPressService
from app.services.yoast_service import YoastService

logger = logging.getLogger(__name__)


def discover_keywords_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: discover_keywords - category=%s", state.get("category_name"))

    try:
        service = KeywordService()
        result = service.discover(
            category_name=state["category_name"],
            seed_keywords=state.get("seed_keywords", []),
            location=state.get("location"),
        )

        return {
            **state,
            "discovered_keywords": result.get("keywords", []),
            "clusters": result.get("clusters", []),
        }
    except Exception as e:
        logger.exception("Error in discover_keywords_node")
        return {**state, "error": str(e), "status": "error"}


def read_site_content_node(state: WorkflowState) -> WorkflowState:
    site_url = state.get("site_url")
    logger.info("Node: read_site_content - site=%s", site_url or "default")

    if state.get("error"):
        return state

    try:
        service = WordPressService(base_url=site_url)
        pages = service.fetch_all_content()
        categories = service.fetch_categories()

        return {
            **state,
            "site_pages": pages,
            "categories": categories,
        }
    except Exception as e:
        logger.exception("Error in read_site_content_node")
        return {**state, "error": str(e), "status": "error"}


def extract_style_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: extract_style")

    if state.get("error"):
        return state

    try:
        service = StyleService()

        # Extract style from site content
        extracted = service.extract_style(state.get("site_pages", []))

        # Merge with manual override if provided
        style_config = state.get("style_config")
        if style_config:
            style_profile = service.merge_with_override(extracted, style_config)
        else:
            style_profile = extracted

        return {
            **state,
            "style_profile": style_profile,
        }
    except Exception as e:
        logger.exception("Error in extract_style_node")
        # Non-fatal: continue with default style
        return {
            **state,
            "style_profile": StyleService()._default_style(),
        }


def analyze_topology_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: analyze_topology")

    if state.get("error"):
        return state

    try:
        service = TopologyService()

        # Analyze content topology
        topology = service.analyze_topology(
            site_pages=state.get("site_pages", []),
            categories=state.get("categories"),
        )

        # Enrich with LLM insights
        topology = service.enrich_with_llm(topology, state.get("site_pages", []))

        pillars_count = len(topology.get("pillars", []))
        satellites_count = len(topology.get("satellites", []))
        homepage = topology.get("homepage", {})

        logger.info(
            "Topology: homepage=%s, pillars=%d, satellites=%d",
            homepage.get("slug") if homepage else "N/A",
            pillars_count,
            satellites_count,
        )

        return {
            **state,
            "content_topology": topology,
        }
    except Exception as e:
        logger.exception("Error in analyze_topology_node")
        # Non-fatal: continue without topology
        return {
            **state,
            "content_topology": {},
        }


def analyze_yoast_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: analyze_yoast")

    if state.get("error"):
        return state

    try:
        service = YoastService()
        analysis = service.analyze_seo_data(state.get("site_pages", []))

        high_issues = analysis.get("issue_summary", {}).get("by_severity", {}).get("high", 0)
        total_issues = analysis.get("total_issues", 0)

        logger.info(
            "Yoast analysis: %d total issues, %d high priority",
            total_issues,
            high_issues,
        )

        return {
            **state,
            "yoast_analysis": analysis,
        }
    except Exception as e:
        logger.exception("Error in analyze_yoast_node")
        # Non-fatal: continue without Yoast analysis
        return {
            **state,
            "yoast_analysis": {},
        }


def analyze_schema_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: analyze_schema")

    if state.get("error"):
        return state

    try:
        analyzer = SchemaAnalyzer()
        analysis = analyzer.analyze_schemas(state.get("site_pages", []))

        logger.info(
            "Schema analysis: AI readiness=%.1f%%, %d/%d pages with schema",
            analysis.get("ai_readiness_score", 0),
            analysis.get("pages_with_schema", 0),
            analysis.get("total_pages", 0),
        )

        return {
            **state,
            "schema_analysis": analysis,
        }
    except Exception as e:
        logger.exception("Error in analyze_schema_node")
        # Non-fatal: continue without schema analysis
        return {
            **state,
            "schema_analysis": {},
        }


def analyze_gaps_node(state: WorkflowState) -> WorkflowState:
    logger.info("Node: analyze_gaps")

    if state.get("error"):
        return state

    try:
        service = AnalysisService()
        result = service.gap_analysis(
            category_name=state["category_name"],
            clusters=state.get("clusters", []),
            site_pages=state.get("site_pages", []),
            style_profile=state.get("style_profile"),
            topology=state.get("content_topology"),
            yoast_analysis=state.get("yoast_analysis"),
            schema_analysis=state.get("schema_analysis"),
        )

        return {
            **state,
            "analysis_result": result,
            "proposals": result.get("proposals", []),
            "status": "needs_review",
        }
    except Exception as e:
        logger.exception("Error in analyze_gaps_node")
        return {**state, "error": str(e), "status": "error"}
