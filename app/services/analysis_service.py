import logging

from app.prompts import build_geo_enhanced_prompt
from app.services.deduplication_service import DeduplicationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self) -> None:
        self.llm_service = LLMService()
        self.deduplication_service = DeduplicationService()

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
            "duplicate_risks": self._cluster_duplicate_risks(clusters, site_pages),
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
        if not proposals:
            proposals = self._fallback_proposals(
                category_name=category_name,
                clusters=clusters,
                yoast_analysis=yoast_analysis,
                schema_analysis=schema_analysis,
            )
            result["proposals"] = proposals

        result["proposals"] = self._annotate_duplicate_risks(proposals, site_pages)

        logger.info(
            "Gap analysis complete: category=%s, proposals=%d",
            category_name,
            len(result["proposals"]),
        )

        return result

    def _cluster_duplicate_risks(self, clusters: list[dict], site_pages: list[dict]) -> list[dict]:
        risks = []
        for cluster in clusters[:10]:
            cluster_text = " ".join([
                cluster.get("name", ""),
                " ".join(cluster.get("keywords", [])),
            ])
            match = self.deduplication_service.find_best_match(cluster_text, site_pages)
            if match and match["risk"] != "low":
                risks.append({
                    "cluster": cluster.get("name"),
                    "keywords": cluster.get("keywords", []),
                    "duplicate_score": match["score"],
                    "duplicate_risk": match["risk"],
                    "matching_page": match["page"],
                })
        return risks

    def _annotate_duplicate_risks(
        self,
        proposals: list[dict],
        site_pages: list[dict],
    ) -> list[dict]:
        annotated = []
        for proposal in proposals:
            proposal_text = " ".join([
                proposal.get("target_title", ""),
                proposal.get("summary", ""),
                " ".join(proposal.get("outline", [])) if isinstance(proposal.get("outline"), list) else str(proposal.get("outline", "")),
            ])
            match = self.deduplication_service.find_best_match(proposal_text, site_pages)
            if not match:
                annotated.append(proposal)
                continue

            proposal["duplicate_check"] = match
            if match["risk"] == "high" and proposal.get("proposal_type") in {
                "create_satellite_post",
                "create_pillar_page",
                "create_new_page",
                "create_new_category",
            }:
                proposal["priority"] = "low"
                proposal["summary"] = (
                    f"[Πιθανό duplicate με {match['page'].get('title')}] "
                    f"{proposal.get('summary', '')}"
                )
                proposal["seo_meta_suggestions"] = {
                    **(proposal.get("seo_meta_suggestions") if isinstance(proposal.get("seo_meta_suggestions"), dict) else {}),
                    "duplicate_check": match,
                    "recommendation": "Προτιμήστε update ή internal linking αντί για νέο content.",
                }
            annotated.append(proposal)

        return annotated

    def _fallback_proposals(
        self,
        category_name: str,
        clusters: list[dict],
        yoast_analysis: dict | None,
        schema_analysis: dict | None,
    ) -> list[dict]:
        """Create deterministic proposals when the LLM returns no usable output."""
        proposals: list[dict] = []

        for page in (yoast_analysis or {}).get("pages_analysis", [])[:3]:
            if page.get("issues_count", 0) <= 0:
                continue
            proposals.append({
                "proposal_type": "improve_seo_meta",
                "target_title": page.get("title") or page.get("slug") or category_name,
                "parent_pillar": None,
                "summary": "Βελτίωση Yoast SEO metadata με βάση τα εντοπισμένα issues.",
                "outline": [
                    "Έλεγχος focus keyphrase",
                    "Βελτίωση meta title",
                    "Βελτίωση meta description",
                    "Προσθήκη keyphrase στα βασικά σημεία της σελίδας",
                ],
                "suggested_schema": page.get("schema_types") or ["Article"],
                "seo_meta_suggestions": {
                    "issues": page.get("issues", []),
                },
                "priority": "high",
            })

        for suggestion in (schema_analysis or {}).get("improvement_suggestions", [])[:3]:
            schema = suggestion.get("schema", "FAQPage")
            proposal_type = "add_faq_section" if schema == "FAQPage" else "improve_schema"
            proposals.append({
                "proposal_type": proposal_type,
                "target_title": suggestion.get("page_slug") or category_name,
                "parent_pillar": None,
                "summary": suggestion.get("reason") or f"Προσθήκη/βελτίωση schema {schema}.",
                "outline": [
                    "Έλεγχος υπάρχοντος structured data",
                    f"Προσθήκη schema {schema}",
                    "Έλεγχος απαιτούμενων properties",
                ],
                "suggested_schema": [schema],
                "schema_additions": [schema],
                "priority": suggestion.get("priority", "medium"),
            })

        if proposals:
            return proposals[:5]

        for cluster in clusters[:3]:
            keywords = cluster.get("keywords", [])
            target_title = cluster.get("name") or category_name
            proposals.append({
                "proposal_type": "create_satellite_post",
                "target_title": target_title,
                "parent_pillar": None,
                "summary": "Fallback πρόταση δημιουργίας υποστηρικτικού περιεχομένου από keyword cluster.",
                "outline": [
                    "Σύντομη απάντηση στο βασικό ερώτημα",
                    "Ανάλυση προβλήματος και λύσης",
                    "Συχνές ερωτήσεις",
                    "Internal links προς σχετικές υπηρεσίες",
                ],
                "suggested_schema": ["Article", "FAQPage"],
                "priority": "medium",
                "seo_meta_suggestions": {
                    "focus_keywords": keywords,
                },
            })

        return proposals
