import logging

from app.prompts import KEYWORD_DISCOVERY_PROMPT
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class KeywordService:
    def __init__(self) -> None:
        self.llm_service = LLMService()

    def discover(
        self,
        category_name: str,
        seed_keywords: list[str],
        location: str | None = None,
    ) -> dict:
        payload = {
            "category_name": category_name,
            "seed_keywords": seed_keywords,
            "location": location,
        }

        result = self.llm_service.generate_json(KEYWORD_DISCOVERY_PROMPT, payload)

        keywords = result.get("keywords", [])
        clusters = result.get("clusters", [])

        logger.info(
            "Keyword discovery complete: category=%s, keywords=%d, clusters=%d",
            category_name,
            len(keywords),
            len(clusters),
        )

        return result
