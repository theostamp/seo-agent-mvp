import re
from difflib import SequenceMatcher


TOKEN_RE = re.compile(r"[\wά-ώΆ-Ώ]+", re.UNICODE)


class DeduplicationService:
    """Detect likely overlap between proposed topics and existing site content."""

    def find_best_match(self, proposal_text: str, site_pages: list[dict]) -> dict | None:
        if not proposal_text.strip() or not site_pages:
            return None

        best_match = None
        best_score = 0.0
        proposal_norm = self._normalize(proposal_text)

        for page in site_pages:
            page_text = " ".join([
                page.get("title", ""),
                page.get("excerpt", ""),
                page.get("content", "")[:2000],
            ])
            score = self.similarity(proposal_text, page_text)
            page_title = self._normalize(page.get("title", ""))
            if page_title and page_title in proposal_norm:
                score = max(score, 0.75)
            if score > best_score:
                best_score = score
                best_match = page

        if not best_match:
            return None

        return {
            "score": round(best_score, 3),
            "risk": self.risk_level(best_score),
            "page": {
                "title": best_match.get("title", ""),
                "slug": best_match.get("slug", ""),
                "url": best_match.get("url", ""),
                "post_type": best_match.get("post_type", ""),
            },
        }

    def similarity(self, left: str, right: str) -> float:
        left_norm = self._normalize(left)
        right_norm = self._normalize(right)

        if not left_norm or not right_norm:
            return 0.0

        title_ratio = SequenceMatcher(None, left_norm[:250], right_norm[:250]).ratio()

        left_tokens = set(self._tokens(left_norm))
        right_tokens = set(self._tokens(right_norm))
        if not left_tokens or not right_tokens:
            token_ratio = 0.0
        else:
            token_ratio = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

        return max(title_ratio * 0.45 + token_ratio * 0.55, token_ratio)

    def risk_level(self, score: float) -> str:
        if score >= 0.55:
            return "high"
        if score >= 0.35:
            return "medium"
        return "low"

    def _normalize(self, text: str) -> str:
        return " ".join(self._tokens(text))

    def _tokens(self, text: str) -> list[str]:
        return [
            token
            for token in TOKEN_RE.findall(text.lower())
            if len(token) > 2
        ]
