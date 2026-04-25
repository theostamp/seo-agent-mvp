"""
SEO Score Calculator.
Evaluates content for SEO optimization before publishing.
"""

import re
from dataclasses import dataclass


@dataclass
class SEOCheck:
    """Individual SEO check result."""
    name: str
    passed: bool
    score: int  # 0-100
    message: str
    importance: str  # "critical", "important", "nice_to_have"


@dataclass
class SEOScore:
    """Overall SEO score result."""
    total_score: int  # 0-100
    grade: str  # A, B, C, D, F
    checks: list[SEOCheck]
    summary: str

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "summary": self.summary,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "score": c.score,
                    "message": c.message,
                    "importance": c.importance,
                }
                for c in self.checks
            ],
        }


class SEOScorer:
    """Calculate SEO score for generated content."""

    def calculate_score(self, content: dict) -> SEOScore:
        """
        Calculate comprehensive SEO score.

        Args:
            content: The generated content dict with html_content, meta_title, etc.

        Returns:
            SEOScore with detailed breakdown
        """
        checks = []

        # Get content data
        html_content = content.get("html_content", "")
        meta_title = content.get("meta_title", "")
        meta_description = content.get("meta_description", "")
        focus_keyphrase = content.get("focus_keyphrase", "")
        word_count = content.get("word_count", 0)
        keyword_count = content.get("keyword_count", 0)
        internal_links = content.get("internal_links", [])
        image_suggestions = content.get("image_suggestions", [])
        faq_items = content.get("faq_items", [])
        sections = content.get("sections", [])

        # 1. Meta Title Length (Critical)
        checks.append(self._check_meta_title_length(meta_title))

        # 2. Meta Description Length (Critical)
        checks.append(self._check_meta_description_length(meta_description))

        # 3. Keyword in Title (Critical)
        checks.append(self._check_keyword_in_title(meta_title, focus_keyphrase))

        # 4. Keyword in First Paragraph (Critical)
        checks.append(self._check_keyword_in_intro(html_content, focus_keyphrase))

        # 5. Keyword Density (Important)
        checks.append(self._check_keyword_density(word_count, keyword_count))

        # 6. Keyword in Headings (Important)
        checks.append(self._check_keyword_in_headings(html_content, focus_keyphrase))

        # 7. Internal Links (Important)
        checks.append(self._check_internal_links(internal_links))

        # 8. Image Alt Texts (Important)
        checks.append(self._check_images(image_suggestions, html_content))

        # 9. Word Count (Important)
        checks.append(self._check_word_count(word_count))

        # 10. FAQ Section (Nice to Have)
        checks.append(self._check_faq_section(faq_items))

        # 11. Content Structure (Nice to Have)
        checks.append(self._check_content_structure(sections, html_content))

        # 12. Meta Description has Keyword (Nice to Have)
        checks.append(self._check_keyword_in_meta_desc(meta_description, focus_keyphrase))

        # Calculate total score
        total_score = self._calculate_total_score(checks)
        grade = self._get_grade(total_score)
        summary = self._generate_summary(checks, total_score)

        return SEOScore(
            total_score=total_score,
            grade=grade,
            checks=checks,
            summary=summary,
        )

    def _check_meta_title_length(self, title: str) -> SEOCheck:
        length = len(title)
        if 50 <= length <= 60:
            return SEOCheck(
                name="Meta Title Length",
                passed=True,
                score=100,
                message=f"Τέλειο! {length} χαρακτήρες (ιδανικό: 50-60)",
                importance="critical",
            )
        elif 40 <= length < 50 or 60 < length <= 70:
            return SEOCheck(
                name="Meta Title Length",
                passed=True,
                score=70,
                message=f"Αποδεκτό: {length} χαρακτήρες (ιδανικό: 50-60)",
                importance="critical",
            )
        else:
            return SEOCheck(
                name="Meta Title Length",
                passed=False,
                score=30,
                message=f"Πρόβλημα: {length} χαρακτήρες (ιδανικό: 50-60)",
                importance="critical",
            )

    def _check_meta_description_length(self, desc: str) -> SEOCheck:
        length = len(desc)
        if 150 <= length <= 160:
            return SEOCheck(
                name="Meta Description Length",
                passed=True,
                score=100,
                message=f"Τέλειο! {length} χαρακτήρες (ιδανικό: 150-160)",
                importance="critical",
            )
        elif 120 <= length < 150 or 160 < length <= 180:
            return SEOCheck(
                name="Meta Description Length",
                passed=True,
                score=70,
                message=f"Αποδεκτό: {length} χαρακτήρες (ιδανικό: 150-160)",
                importance="critical",
            )
        else:
            return SEOCheck(
                name="Meta Description Length",
                passed=False,
                score=30,
                message=f"Πρόβλημα: {length} χαρακτήρες (ιδανικό: 150-160)",
                importance="critical",
            )

    def _check_keyword_in_title(self, title: str, keyword: str) -> SEOCheck:
        if not keyword:
            return SEOCheck(
                name="Keyword στον Τίτλο",
                passed=False,
                score=0,
                message="Δεν ορίστηκε focus keyphrase",
                importance="critical",
            )

        title_lower = title.lower()
        keyword_lower = keyword.lower()

        if keyword_lower in title_lower:
            return SEOCheck(
                name="Keyword στον Τίτλο",
                passed=True,
                score=100,
                message=f"Το keyword '{keyword}' υπάρχει στον τίτλο",
                importance="critical",
            )
        else:
            # Check for partial match
            keyword_words = keyword_lower.split()
            matches = sum(1 for w in keyword_words if w in title_lower)
            if matches >= len(keyword_words) / 2:
                return SEOCheck(
                    name="Keyword στον Τίτλο",
                    passed=True,
                    score=60,
                    message=f"Μερική αντιστοιχία: {matches}/{len(keyword_words)} λέξεις",
                    importance="critical",
                )
            return SEOCheck(
                name="Keyword στον Τίτλο",
                passed=False,
                score=0,
                message=f"Το keyword '{keyword}' δεν υπάρχει στον τίτλο",
                importance="critical",
            )

    def _check_keyword_in_intro(self, html: str, keyword: str) -> SEOCheck:
        if not keyword:
            return SEOCheck(
                name="Keyword στην Εισαγωγή",
                passed=False,
                score=0,
                message="Δεν ορίστηκε focus keyphrase",
                importance="critical",
            )

        # Extract first paragraph
        first_p_match = re.search(r"<p>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
        if not first_p_match:
            return SEOCheck(
                name="Keyword στην Εισαγωγή",
                passed=False,
                score=0,
                message="Δεν βρέθηκε εισαγωγική παράγραφος",
                importance="critical",
            )

        first_paragraph = first_p_match.group(1).lower()
        keyword_lower = keyword.lower()

        if keyword_lower in first_paragraph:
            return SEOCheck(
                name="Keyword στην Εισαγωγή",
                passed=True,
                score=100,
                message="Το keyword υπάρχει στην πρώτη παράγραφο",
                importance="critical",
            )
        else:
            keyword_words = keyword_lower.split()
            matches = sum(1 for w in keyword_words if w in first_paragraph)
            if matches >= len(keyword_words) / 2:
                return SEOCheck(
                    name="Keyword στην Εισαγωγή",
                    passed=True,
                    score=60,
                    message=f"Μερική αντιστοιχία στην εισαγωγή",
                    importance="critical",
                )
            return SEOCheck(
                name="Keyword στην Εισαγωγή",
                passed=False,
                score=0,
                message="Το keyword δεν υπάρχει στην πρώτη παράγραφο",
                importance="critical",
            )

    def _check_keyword_density(self, word_count: int, keyword_count: int) -> SEOCheck:
        if word_count == 0:
            return SEOCheck(
                name="Πυκνότητα Keyword",
                passed=False,
                score=0,
                message="Δεν υπάρχει περιεχόμενο",
                importance="important",
            )

        # For a multi-word keyphrase, calculate expected occurrences
        # Ideal: 4-8 times for ~1000 words
        min_expected = max(4, word_count // 250)
        max_expected = max(8, word_count // 125)

        if min_expected <= keyword_count <= max_expected:
            return SEOCheck(
                name="Πυκνότητα Keyword",
                passed=True,
                score=100,
                message=f"Τέλειο! {keyword_count} φορές (προτεινόμενο: {min_expected}-{max_expected})",
                importance="important",
            )
        elif keyword_count >= min_expected - 1:
            return SEOCheck(
                name="Πυκνότητα Keyword",
                passed=True,
                score=70,
                message=f"Αποδεκτό: {keyword_count} φορές (προτεινόμενο: {min_expected}-{max_expected})",
                importance="important",
            )
        else:
            return SEOCheck(
                name="Πυκνότητα Keyword",
                passed=False,
                score=30,
                message=f"Χαμηλό: {keyword_count} φορές (προτεινόμενο: {min_expected}-{max_expected})",
                importance="important",
            )

    def _check_keyword_in_headings(self, html: str, keyword: str) -> SEOCheck:
        if not keyword:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=False,
                score=0,
                message="Δεν ορίστηκε focus keyphrase",
                importance="important",
            )

        # Find all H2 and H3 headings
        headings = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.IGNORECASE | re.DOTALL)
        if not headings:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=False,
                score=0,
                message="Δεν βρέθηκαν H2/H3 headings",
                importance="important",
            )

        keyword_lower = keyword.lower()
        keyword_words = set(keyword_lower.split())
        headings_with_keyword = 0

        for heading in headings:
            heading_lower = heading.lower()
            if keyword_lower in heading_lower:
                headings_with_keyword += 1
            else:
                # Check for partial match
                matches = sum(1 for w in keyword_words if w in heading_lower)
                if matches >= len(keyword_words) / 2:
                    headings_with_keyword += 0.5

        if headings_with_keyword >= 3:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=True,
                score=100,
                message=f"Τέλειο! {int(headings_with_keyword)} headings με keyword",
                importance="important",
            )
        elif headings_with_keyword >= 2:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=True,
                score=80,
                message=f"Καλό: {int(headings_with_keyword)} headings με keyword",
                importance="important",
            )
        elif headings_with_keyword >= 1:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=True,
                score=50,
                message=f"Αποδεκτό: {int(headings_with_keyword)} heading με keyword",
                importance="important",
            )
        else:
            return SEOCheck(
                name="Keyword σε Headings",
                passed=False,
                score=0,
                message="Κανένα H2/H3 δεν περιέχει το keyword",
                importance="important",
            )

    def _check_internal_links(self, links: list) -> SEOCheck:
        count = len(links)
        if count >= 4:
            return SEOCheck(
                name="Εσωτερικοί Σύνδεσμοι",
                passed=True,
                score=100,
                message=f"Τέλειο! {count} internal links",
                importance="important",
            )
        elif count >= 3:
            return SEOCheck(
                name="Εσωτερικοί Σύνδεσμοι",
                passed=True,
                score=80,
                message=f"Καλό: {count} internal links",
                importance="important",
            )
        elif count >= 1:
            return SEOCheck(
                name="Εσωτερικοί Σύνδεσμοι",
                passed=True,
                score=50,
                message=f"Αποδεκτό: {count} internal links (προτεινόμενο: 3+)",
                importance="important",
            )
        else:
            return SEOCheck(
                name="Εσωτερικοί Σύνδεσμοι",
                passed=False,
                score=0,
                message="Δεν υπάρχουν internal links",
                importance="important",
            )

    def _check_images(self, image_suggestions: list, html: str) -> SEOCheck:
        # Count image placeholders in HTML
        image_placeholders = len(re.findall(r"<!--\s*IMAGE:", html))
        total_images = len(image_suggestions) + image_placeholders

        if total_images >= 3:
            return SEOCheck(
                name="Εικόνες με Alt Text",
                passed=True,
                score=100,
                message=f"Τέλειο! {total_images} εικόνες προτείνονται",
                importance="important",
            )
        elif total_images >= 2:
            return SEOCheck(
                name="Εικόνες με Alt Text",
                passed=True,
                score=80,
                message=f"Καλό: {total_images} εικόνες",
                importance="important",
            )
        elif total_images >= 1:
            return SEOCheck(
                name="Εικόνες με Alt Text",
                passed=True,
                score=50,
                message=f"Αποδεκτό: {total_images} εικόνα (προτεινόμενο: 2+)",
                importance="important",
            )
        else:
            return SEOCheck(
                name="Εικόνες με Alt Text",
                passed=False,
                score=0,
                message="Δεν υπάρχουν προτάσεις εικόνων",
                importance="important",
            )

    def _check_word_count(self, word_count: int) -> SEOCheck:
        if 800 <= word_count <= 1500:
            return SEOCheck(
                name="Μήκος Κειμένου",
                passed=True,
                score=100,
                message=f"Τέλειο! {word_count} λέξεις",
                importance="important",
            )
        elif 600 <= word_count < 800:
            return SEOCheck(
                name="Μήκος Κειμένου",
                passed=True,
                score=70,
                message=f"Αποδεκτό: {word_count} λέξεις (ιδανικό: 800+)",
                importance="important",
            )
        elif word_count > 1500:
            return SEOCheck(
                name="Μήκος Κειμένου",
                passed=True,
                score=90,
                message=f"Πολύ καλό: {word_count} λέξεις (εκτενές περιεχόμενο)",
                importance="important",
            )
        else:
            return SEOCheck(
                name="Μήκος Κειμένου",
                passed=False,
                score=30,
                message=f"Λίγο: {word_count} λέξεις (ιδανικό: 800+)",
                importance="important",
            )

    def _check_faq_section(self, faq_items: list) -> SEOCheck:
        count = len(faq_items)
        if count >= 3:
            return SEOCheck(
                name="FAQ Section",
                passed=True,
                score=100,
                message=f"Τέλειο! {count} FAQs με schema",
                importance="nice_to_have",
            )
        elif count >= 1:
            return SEOCheck(
                name="FAQ Section",
                passed=True,
                score=70,
                message=f"Καλό: {count} FAQs (προτεινόμενο: 3+)",
                importance="nice_to_have",
            )
        else:
            return SEOCheck(
                name="FAQ Section",
                passed=False,
                score=0,
                message="Δεν υπάρχει FAQ section",
                importance="nice_to_have",
            )

    def _check_content_structure(self, sections: list, html: str) -> SEOCheck:
        # Count headings
        h2_count = len(re.findall(r"<h2", html, re.IGNORECASE))
        h3_count = len(re.findall(r"<h3", html, re.IGNORECASE))

        if h2_count >= 4 and h3_count >= 2:
            return SEOCheck(
                name="Δομή Περιεχομένου",
                passed=True,
                score=100,
                message=f"Τέλειο! {h2_count} H2 και {h3_count} H3 sections",
                importance="nice_to_have",
            )
        elif h2_count >= 3:
            return SEOCheck(
                name="Δομή Περιεχομένου",
                passed=True,
                score=80,
                message=f"Καλό: {h2_count} H2 και {h3_count} H3 sections",
                importance="nice_to_have",
            )
        elif h2_count >= 2:
            return SEOCheck(
                name="Δομή Περιεχομένου",
                passed=True,
                score=50,
                message=f"Αποδεκτό: {h2_count} H2 sections",
                importance="nice_to_have",
            )
        else:
            return SEOCheck(
                name="Δομή Περιεχομένου",
                passed=False,
                score=0,
                message="Ελλιπής δομή headings",
                importance="nice_to_have",
            )

    def _check_keyword_in_meta_desc(self, desc: str, keyword: str) -> SEOCheck:
        if not keyword:
            return SEOCheck(
                name="Keyword στο Meta Description",
                passed=False,
                score=0,
                message="Δεν ορίστηκε focus keyphrase",
                importance="nice_to_have",
            )

        if keyword.lower() in desc.lower():
            return SEOCheck(
                name="Keyword στο Meta Description",
                passed=True,
                score=100,
                message="Το keyword υπάρχει στο meta description",
                importance="nice_to_have",
            )
        else:
            keyword_words = keyword.lower().split()
            matches = sum(1 for w in keyword_words if w in desc.lower())
            if matches >= len(keyword_words) / 2:
                return SEOCheck(
                    name="Keyword στο Meta Description",
                    passed=True,
                    score=60,
                    message="Μερική αντιστοιχία στο meta description",
                    importance="nice_to_have",
                )
            return SEOCheck(
                name="Keyword στο Meta Description",
                passed=False,
                score=0,
                message="Το keyword δεν υπάρχει στο meta description",
                importance="nice_to_have",
            )

    def _calculate_total_score(self, checks: list[SEOCheck]) -> int:
        """Calculate weighted total score."""
        weights = {
            "critical": 3.0,
            "important": 2.0,
            "nice_to_have": 1.0,
        }

        total_weight = 0
        weighted_score = 0

        for check in checks:
            weight = weights.get(check.importance, 1.0)
            weighted_score += check.score * weight
            total_weight += 100 * weight

        if total_weight == 0:
            return 0

        return int(weighted_score / total_weight * 100)

    def _get_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_summary(self, checks: list[SEOCheck], total_score: int) -> str:
        """Generate human-readable summary."""
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)

        critical_issues = [c for c in checks if not c.passed and c.importance == "critical"]
        important_issues = [c for c in checks if not c.passed and c.importance == "important"]

        if total_score >= 90:
            summary = f"Εξαιρετικό SEO! {passed}/{total} έλεγχοι επιτυχείς."
        elif total_score >= 80:
            summary = f"Πολύ καλό SEO. {passed}/{total} έλεγχοι επιτυχείς."
        elif total_score >= 70:
            summary = f"Καλό SEO, με περιθώρια βελτίωσης. {passed}/{total} έλεγχοι."
        else:
            summary = f"Χρειάζεται βελτίωση. {passed}/{total} έλεγχοι επιτυχείς."

        if critical_issues:
            summary += f" Κρίσιμα: {', '.join(c.name for c in critical_issues)}."

        return summary
