import logging

logger = logging.getLogger(__name__)


class YoastService:
    """Analyzes Yoast SEO data and provides optimization suggestions."""

    # Minimum recommended lengths
    MIN_TITLE_LENGTH = 30
    MAX_TITLE_LENGTH = 60
    MIN_DESC_LENGTH = 120
    MAX_DESC_LENGTH = 160

    def analyze_seo_data(self, site_pages: list[dict]) -> dict:
        """
        Analyze Yoast SEO data across all pages.

        Returns:
            {
                "pages_with_yoast": int,
                "pages_without_yoast": int,
                "issues": [...],
                "pages_analysis": [...]
            }
        """
        pages_with_yoast = 0
        pages_without_yoast = 0
        all_issues = []
        pages_analysis = []

        for page in site_pages:
            yoast = page.get("yoast", {})

            if not yoast.get("available"):
                pages_without_yoast += 1
                continue

            pages_with_yoast += 1

            # Analyze this page
            page_issues = self._analyze_page(page, yoast)

            pages_analysis.append({
                "slug": page.get("slug"),
                "title": page.get("title"),
                "yoast_title": yoast.get("title", ""),
                "focus_keyphrase": yoast.get("focus_keyphrase", ""),
                "meta_description": yoast.get("description", ""),
                "schema_types": yoast.get("schema_types", []),
                "issues": page_issues,
                "issues_count": len(page_issues),
            })

            all_issues.extend(page_issues)

        # Group issues by type
        issue_summary = self._summarize_issues(all_issues)

        logger.info(
            "Yoast analysis: %d pages with Yoast, %d without, %d total issues",
            pages_with_yoast,
            pages_without_yoast,
            len(all_issues),
        )

        return {
            "pages_with_yoast": pages_with_yoast,
            "pages_without_yoast": pages_without_yoast,
            "total_issues": len(all_issues),
            "issue_summary": issue_summary,
            "pages_analysis": pages_analysis,
        }

    def _analyze_page(self, page: dict, yoast: dict) -> list[dict]:
        """Analyze a single page's Yoast data."""
        issues = []
        slug = page.get("slug", "unknown")

        # Check focus keyphrase
        focus_kw = yoast.get("focus_keyphrase", "")
        if not focus_kw:
            issues.append({
                "type": "missing_focus_keyphrase",
                "slug": slug,
                "severity": "high",
                "message": "Δεν έχει οριστεί focus keyphrase",
            })

        # Check meta title
        title = yoast.get("title", "")
        if not title:
            issues.append({
                "type": "missing_meta_title",
                "slug": slug,
                "severity": "high",
                "message": "Λείπει ο meta title",
            })
        elif len(title) < self.MIN_TITLE_LENGTH:
            issues.append({
                "type": "short_meta_title",
                "slug": slug,
                "severity": "medium",
                "message": f"Ο meta title είναι πολύ σύντομος ({len(title)} χαρακτήρες)",
            })
        elif len(title) > self.MAX_TITLE_LENGTH:
            issues.append({
                "type": "long_meta_title",
                "slug": slug,
                "severity": "low",
                "message": f"Ο meta title είναι πολύ μακρύς ({len(title)} χαρακτήρες)",
            })

        # Check meta description
        desc = yoast.get("description", "")
        if not desc:
            issues.append({
                "type": "missing_meta_description",
                "slug": slug,
                "severity": "high",
                "message": "Λείπει το meta description",
            })
        elif len(desc) < self.MIN_DESC_LENGTH:
            issues.append({
                "type": "short_meta_description",
                "slug": slug,
                "severity": "medium",
                "message": f"Το meta description είναι πολύ σύντομο ({len(desc)} χαρακτήρες)",
            })
        elif len(desc) > self.MAX_DESC_LENGTH:
            issues.append({
                "type": "long_meta_description",
                "slug": slug,
                "severity": "low",
                "message": f"Το meta description είναι πολύ μακρύ ({len(desc)} χαρακτήρες)",
            })

        # Check if focus keyphrase is in title
        if focus_kw and title and focus_kw.lower() not in title.lower():
            issues.append({
                "type": "keyphrase_not_in_title",
                "slug": slug,
                "severity": "medium",
                "message": f"Το focus keyphrase '{focus_kw}' δεν υπάρχει στον title",
            })

        # Check if focus keyphrase is in description
        if focus_kw and desc and focus_kw.lower() not in desc.lower():
            issues.append({
                "type": "keyphrase_not_in_description",
                "slug": slug,
                "severity": "low",
                "message": f"Το focus keyphrase '{focus_kw}' δεν υπάρχει στο description",
            })

        # Check schema types
        schema_types = yoast.get("schema_types", [])
        if not schema_types:
            issues.append({
                "type": "no_schema",
                "slug": slug,
                "severity": "medium",
                "message": "Δεν υπάρχει structured data (Schema.org)",
            })

        return issues

    def _summarize_issues(self, issues: list[dict]) -> dict:
        """Summarize issues by type and severity."""
        by_type = {}
        by_severity = {"high": 0, "medium": 0, "low": 0}

        for issue in issues:
            issue_type = issue.get("type", "unknown")
            severity = issue.get("severity", "low")

            by_type[issue_type] = by_type.get(issue_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "by_type": by_type,
            "by_severity": by_severity,
        }

    def get_optimization_priorities(self, analysis: dict) -> list[dict]:
        """Get prioritized list of pages to optimize."""
        pages = analysis.get("pages_analysis", [])

        # Sort by issues count (high severity first, then by count)
        def priority_score(page):
            issues = page.get("issues", [])
            high = sum(1 for i in issues if i.get("severity") == "high")
            medium = sum(1 for i in issues if i.get("severity") == "medium")
            low = sum(1 for i in issues if i.get("severity") == "low")
            return (high * 100 + medium * 10 + low, page.get("slug", ""))

        sorted_pages = sorted(pages, key=priority_score, reverse=True)

        priorities = []
        for page in sorted_pages[:10]:  # Top 10
            if page.get("issues_count", 0) > 0:
                priorities.append({
                    "slug": page.get("slug"),
                    "title": page.get("title"),
                    "issues_count": page.get("issues_count"),
                    "high_priority_issues": [
                        i for i in page.get("issues", [])
                        if i.get("severity") == "high"
                    ],
                })

        return priorities
