import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# Schema types recommended for different content types
RECOMMENDED_SCHEMAS = {
    "service_page": ["Service", "LocalBusiness", "FAQPage", "BreadcrumbList"],
    "blog_post": ["Article", "BlogPosting", "FAQPage", "HowTo", "BreadcrumbList"],
    "how_to": ["HowTo", "Article", "FAQPage", "BreadcrumbList"],
    "faq": ["FAQPage", "Article", "BreadcrumbList"],
    "contact": ["LocalBusiness", "ContactPage", "BreadcrumbList"],
    "about": ["AboutPage", "Organization", "BreadcrumbList"],
    "homepage": ["WebSite", "Organization", "LocalBusiness", "BreadcrumbList"],
}

# AI-friendly schema enhancements
AI_FRIENDLY_SCHEMAS = [
    "FAQPage",      # Clear Q&A for AI extraction
    "HowTo",        # Step-by-step for AI understanding
    "Article",      # Structured content
    "ItemList",     # Lists that AI can parse
    "DefinedTerm",  # Definitions for knowledge graphs
]


class SchemaAnalyzer:
    """Analyzes existing Schema.org markup and suggests improvements."""

    def __init__(self) -> None:
        self.llm = LLMService()

    def analyze_schemas(self, site_pages: list[dict]) -> dict:
        """
        Analyze Schema.org markup across all pages.

        Returns:
            {
                "total_pages": int,
                "pages_with_schema": int,
                "schema_coverage": {...},
                "missing_schemas": [...],
                "improvement_suggestions": [...],
                "ai_readiness_score": float,
            }
        """
        total_pages = len(site_pages)
        pages_with_schema = 0
        schema_types_found = {}
        pages_analysis = []

        for page in site_pages:
            yoast = page.get("yoast", {})
            schema_types = yoast.get("schema_types", [])
            schema_graph = yoast.get("schema_graph", [])

            if schema_types:
                pages_with_schema += 1

            # Count schema types
            for schema_type in schema_types:
                # Handle cases where schema_type is a list (e.g., ["Article", "BlogPosting"])
                if isinstance(schema_type, list):
                    for st in schema_type:
                        schema_types_found[st] = schema_types_found.get(st, 0) + 1
                else:
                    schema_types_found[schema_type] = schema_types_found.get(schema_type, 0) + 1

            # Analyze this page
            page_analysis = self._analyze_page_schema(page, schema_types, schema_graph)
            pages_analysis.append(page_analysis)

        # Calculate AI readiness score
        ai_score = self._calculate_ai_readiness(pages_analysis, schema_types_found)

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(pages_analysis, schema_types_found)

        logger.info(
            "Schema analysis: %d/%d pages with schema, AI readiness: %.1f%%",
            pages_with_schema,
            total_pages,
            ai_score * 100,
        )

        return {
            "total_pages": total_pages,
            "pages_with_schema": pages_with_schema,
            "schema_coverage_percent": round(pages_with_schema / total_pages * 100, 1) if total_pages > 0 else 0,
            "schema_types_found": schema_types_found,
            "pages_analysis": pages_analysis,
            "improvement_suggestions": suggestions,
            "ai_readiness_score": round(ai_score * 100, 1),
        }

    def _analyze_page_schema(
        self,
        page: dict,
        schema_types: list[str],
        schema_graph: list[dict],
    ) -> dict:
        """Analyze schema markup for a single page."""
        slug = page.get("slug", "")
        post_type = page.get("post_type", "page")
        is_front_page = page.get("is_front_page", False)

        # Determine expected content type
        content_type = self._infer_content_type(page, schema_types)

        # Get recommended schemas for this content type
        recommended = RECOMMENDED_SCHEMAS.get(content_type, RECOMMENDED_SCHEMAS["blog_post"])

        # Find missing recommended schemas
        missing = [s for s in recommended if s not in schema_types]

        # Find AI-friendly schemas that could be added
        ai_suggestions = [s for s in AI_FRIENDLY_SCHEMAS if s not in schema_types]

        # Analyze schema quality
        quality_issues = self._check_schema_quality(schema_graph)

        return {
            "slug": slug,
            "title": page.get("title", ""),
            "content_type": content_type,
            "current_schemas": schema_types,
            "recommended_schemas": recommended,
            "missing_schemas": missing,
            "ai_friendly_suggestions": ai_suggestions[:3],
            "quality_issues": quality_issues,
            "has_faq": "FAQPage" in schema_types,
            "has_howto": "HowTo" in schema_types,
        }

    def _infer_content_type(self, page: dict, schema_types: list[str]) -> str:
        """Infer the content type based on page data and existing schemas."""
        slug = page.get("slug", "").lower()
        title = page.get("title", "").lower()
        post_type = page.get("post_type", "page")
        is_front_page = page.get("is_front_page", False)

        if is_front_page or slug in ("", "home", "αρχικη", "αρχική"):
            return "homepage"

        if any(kw in slug for kw in ("contact", "επικοινωνια", "επικοινωνία")):
            return "contact"

        if any(kw in slug for kw in ("about", "σχετικα", "σχετικά", "ποιοι-ειμαστε")):
            return "about"

        if "HowTo" in schema_types or any(kw in title for kw in ("πως", "πώς", "how to", "οδηγός")):
            return "how_to"

        if "FAQPage" in schema_types or any(kw in title for kw in ("faq", "ερωτήσεις", "απαντήσεις")):
            return "faq"

        if post_type == "page":
            return "service_page"

        return "blog_post"

    def _check_schema_quality(self, schema_graph: list[dict]) -> list[str]:
        """Check for common schema quality issues."""
        issues = []

        if not schema_graph:
            return ["Δεν βρέθηκε schema graph"]

        for schema in schema_graph:
            schema_type = schema.get("@type", "")

            # Normalize schema_type to list for easier checking
            if isinstance(schema_type, list):
                types = schema_type
            else:
                types = [schema_type] if schema_type else []

            type_label = ", ".join(types) if types else "Unknown"

            # Check for missing important properties
            if "Article" in types or "BlogPosting" in types:
                if not schema.get("author"):
                    issues.append(f"{type_label}: Λείπει το author")
                if not schema.get("datePublished"):
                    issues.append(f"{type_label}: Λείπει το datePublished")
                if not schema.get("image"):
                    issues.append(f"{type_label}: Λείπει το image")

            if "LocalBusiness" in types:
                if not schema.get("address"):
                    issues.append("LocalBusiness: Λείπει η διεύθυνση")
                if not schema.get("telephone"):
                    issues.append("LocalBusiness: Λείπει το τηλέφωνο")
                if not schema.get("openingHours"):
                    issues.append("LocalBusiness: Λείπουν οι ώρες λειτουργίας")

            if "Service" in types:
                if not schema.get("provider"):
                    issues.append("Service: Λείπει ο provider")
                if not schema.get("areaServed"):
                    issues.append("Service: Λείπει το areaServed")

        return issues[:5]  # Limit to top 5 issues

    def _calculate_ai_readiness(
        self,
        pages_analysis: list[dict],
        schema_types: dict,
    ) -> float:
        """Calculate AI readiness score (0-1)."""
        if not pages_analysis:
            return 0.0

        scores = []

        # Factor 1: Schema coverage (25%)
        pages_with_schema = sum(1 for p in pages_analysis if p.get("current_schemas"))
        coverage_score = pages_with_schema / len(pages_analysis) if pages_analysis else 0
        scores.append(coverage_score * 0.25)

        # Factor 2: FAQ presence (25%)
        pages_with_faq = sum(1 for p in pages_analysis if p.get("has_faq"))
        faq_score = min(pages_with_faq / max(len(pages_analysis) * 0.3, 1), 1)  # Target 30%
        scores.append(faq_score * 0.25)

        # Factor 3: HowTo presence (20%)
        pages_with_howto = sum(1 for p in pages_analysis if p.get("has_howto"))
        howto_score = min(pages_with_howto / max(len(pages_analysis) * 0.2, 1), 1)  # Target 20%
        scores.append(howto_score * 0.20)

        # Factor 4: Schema variety (15%)
        ai_friendly_count = sum(1 for t in AI_FRIENDLY_SCHEMAS if t in schema_types)
        variety_score = ai_friendly_count / len(AI_FRIENDLY_SCHEMAS)
        scores.append(variety_score * 0.15)

        # Factor 5: Quality (no issues) (15%)
        pages_without_issues = sum(1 for p in pages_analysis if not p.get("quality_issues"))
        quality_score = pages_without_issues / len(pages_analysis) if pages_analysis else 0
        scores.append(quality_score * 0.15)

        return sum(scores)

    def _generate_suggestions(
        self,
        pages_analysis: list[dict],
        schema_types: dict,
    ) -> list[dict]:
        """Generate prioritized improvement suggestions."""
        suggestions = []

        # Global suggestions
        if "FAQPage" not in schema_types:
            suggestions.append({
                "type": "add_schema",
                "priority": "high",
                "schema": "FAQPage",
                "reason": "Το FAQPage είναι κρίσιμο για AI search - προσθέστε FAQ sections",
                "pages_affected": "all service pages",
            })

        if "HowTo" not in schema_types:
            suggestions.append({
                "type": "add_schema",
                "priority": "medium",
                "schema": "HowTo",
                "reason": "Το HowTo βοηθά τα AI bots να κατανοήσουν διαδικασίες",
                "pages_affected": "how-to and guide posts",
            })

        # Page-specific suggestions
        for page in pages_analysis:
            if page.get("missing_schemas"):
                for schema in page.get("missing_schemas", [])[:2]:
                    suggestions.append({
                        "type": "add_schema",
                        "priority": "medium",
                        "schema": schema,
                        "page_slug": page.get("slug"),
                        "reason": f"Προτείνεται για {page.get('content_type')} pages",
                    })

            if page.get("quality_issues"):
                suggestions.append({
                    "type": "fix_schema",
                    "priority": "low",
                    "page_slug": page.get("slug"),
                    "issues": page.get("quality_issues"),
                    "reason": "Βελτίωση ποιότητας υπάρχοντος schema",
                })

        # Limit and deduplicate
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            key = (s.get("type"), s.get("schema", ""), s.get("page_slug", ""))
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(s)

        return unique_suggestions[:15]

    def generate_faq_schema_suggestions(
        self,
        page: dict,
        content_analysis: dict | None = None,
    ) -> list[dict]:
        """Generate FAQ suggestions for a page based on content."""
        # This would use LLM to analyze content and suggest FAQs
        # For now, return template
        return [
            {
                "question": "Ποια είναι τα βασικά βήματα της διαδικασίας;",
                "answer_hint": "Περιγράψτε τη διαδικασία σε 3-5 βήματα",
            },
            {
                "question": "Πόσο κοστίζει η υπηρεσία;",
                "answer_hint": "Δώστε εύρος τιμών ή παράγοντες κόστους",
            },
            {
                "question": "Πόσο χρόνο χρειάζεται;",
                "answer_hint": "Δώστε εκτιμώμενο χρόνο ολοκλήρωσης",
            },
        ]
