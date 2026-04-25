import logging

from app.prompts import build_geo_enhanced_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self) -> None:
        self.llm_service = LLMService()

    def gap_analysis(
        self,
        category_name: str,
        clusters: list[dict],
        site_pages: list[dict],
        style_profile: dict | None = None,
        topology: dict | None = None,
        yoast_analysis: dict | None = None,
        schema_analysis: dict | None = None,
    ) -> dict:
        compact_pages = [
            {
                "title": page["title"],
                "slug": page["slug"],
                "url": page["url"],
                "post_type": page.get("post_type", "page"),
                "excerpt": page["excerpt"][:500] if page["excerpt"] else "",
                "content_sample": page["content"][:1500] if page["content"] else "",
                "yoast_focus_kw": page.get("yoast", {}).get("focus_keyphrase", ""),
                "current_schemas": page.get("yoast", {}).get("schema_types", []),
            }
            for page in site_pages
        ]

        payload = {
            "category_name": category_name,
            "clusters": clusters,
            "site_pages": compact_pages,
        }

        # Build GEO-enhanced prompt with all analysis data
        prompt = build_geo_enhanced_prompt(
            style_profile=style_profile,
            topology=topology,
            yoast_analysis=yoast_analysis,
            schema_analysis=schema_analysis,
        )

        if style_profile:
            logger.info(
                "Using style profile: tone=%s, addressing=%s",
                style_profile.get("tone"),
                style_profile.get("addressing"),
            )

        if topology:
            logger.info(
                "Using topology: pillars=%d, satellites=%d",
                len(topology.get("pillars", [])),
                len(topology.get("satellites", [])),
            )

        if yoast_analysis:
            logger.info(
                "Using Yoast analysis: %d issues",
                yoast_analysis.get("total_issues", 0),
            )

        if schema_analysis:
            logger.info(
                "Using Schema analysis: AI readiness=%.1f%%",
                schema_analysis.get("ai_readiness_score", 0),
            )

        result = self.llm_service.generate_json(prompt, payload)

        # Handle case where LLM returns a list directly instead of {"proposals": [...]}
        if isinstance(result, list):
            result = {"proposals": result}
        elif not isinstance(result, dict):
            logger.warning("Unexpected result type from LLM: %s", type(result))
            result = {"proposals": []}

        proposals = result.get("proposals", [])
        logger.info(
            "Gap analysis complete: category=%s, proposals=%d",
            category_name,
            len(proposals),
        )

        return result
