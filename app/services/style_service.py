import logging

from app.prompts import STYLE_EXTRACTION_PROMPT
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class StyleService:
    def __init__(self) -> None:
        self.llm = LLMService()

    def extract_style(self, site_pages: list[dict], sample_count: int = 5) -> dict:
        """Extract style profile from site content samples."""
        if not site_pages:
            logger.warning("No site pages provided for style extraction")
            return self._default_style()

        # Select diverse samples (prefer longer content)
        sorted_pages = sorted(
            site_pages,
            key=lambda p: len(p.get("content", "")),
            reverse=True,
        )
        samples = sorted_pages[:sample_count]

        # Build content samples for analysis
        content_samples = []
        for page in samples:
            sample = {
                "title": page.get("title", ""),
                "content_excerpt": page.get("content", "")[:1500],
            }
            content_samples.append(sample)

        logger.info("Extracting style from %d content samples", len(content_samples))

        result = self.llm.generate_json(
            system_prompt=STYLE_EXTRACTION_PROMPT,
            user_payload={"samples": content_samples},
        )

        if not result or "tone" not in result:
            logger.warning("Style extraction failed, using defaults")
            return self._default_style()

        logger.info(
            "Style extracted: tone=%s, addressing=%s",
            result.get("tone"),
            result.get("addressing"),
        )
        return result

    def merge_with_override(
        self, extracted: dict, manual_override: dict | None
    ) -> dict:
        """Merge extracted style with manual overrides (manual takes precedence)."""
        if not manual_override:
            return extracted

        merged = extracted.copy()
        for key, value in manual_override.items():
            if value is not None:
                merged[key] = value

        logger.info("Style merged with manual overrides: %s", list(manual_override.keys()))
        return merged

    def _default_style(self) -> dict:
        """Return default style profile."""
        return {
            "tone": "professional",
            "addressing": "εσείς",
            "paragraph_length": "medium",
            "technical_level": "medium",
            "structure": "mixed",
            "title_style": "statement",
            "cta_style": "indirect",
            "sample_phrases": [],
            "avoid_patterns": [],
            "summary": "Επαγγελματικό ύφος με προσφώνηση στον πληθυντικό.",
        }
