import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.services.llm_service import LLMService
from app.services.seo_scorer import SEOScorer
from app.services.site_config import AREAS_SERVED, get_site_config
from app.services.wordpress_service import WordPressService

logger = logging.getLogger(__name__)

# Simple in-memory cache for previews (max 50 entries)
_preview_cache: dict[str, dict] = {}
_MAX_CACHE_SIZE = 50

CONTENT_GENERATION_PROMPT = """
Είσαι SEO content specialist. Θα σου δοθεί μια πρόταση βελτίωσης και το υπάρχον περιεχόμενο.
Δημιούργησε το βελτιωμένο περιεχόμενο σύμφωνα με την πρόταση.

ΚΑΝΟΝΕΣ:
1. Διατήρησε το ύφος και τον τόνο του υπάρχοντος κειμένου
2. Μην αλλάξεις το νόημα, μόνο βελτίωσε
3. Για SEO meta, κράτησε τα όρια χαρακτήρων (title: 50-60, description: 150-160)
4. Για FAQ, δημιούργησε 3-5 ρεαλιστικές ερωτήσεις-απαντήσεις
5. Για content, πρόσθεσε clear answers και structured sections

Επίστρεψε ΜΟΝΟ JSON:
{
  "meta_title": {
    "current": "υπάρχον title",
    "proposed": "προτεινόμενο title",
    "change_reason": "γιατί άλλαξε"
  },
  "meta_description": {
    "current": "υπάρχον description",
    "proposed": "προτεινόμενο description",
    "change_reason": "γιατί άλλαξε"
  },
  "focus_keyphrase": {
    "current": "υπάρχον keyphrase ή κενό",
    "proposed": "προτεινόμενο keyphrase",
    "change_reason": "γιατί επιλέχθηκε"
  },
  "content_changes": [
    {
      "section": "τίτλος section",
      "change_type": "add|modify|restructure",
      "current": "υπάρχον κείμενο ή null",
      "proposed": "προτεινόμενο κείμενο",
      "change_reason": "γιατί"
    }
  ],
  "faq_section": [
    {
      "question": "ερώτηση",
      "answer": "απάντηση"
    }
  ],
  "schema_additions": ["FAQPage", "HowTo"],
  "summary": "Σύνοψη όλων των αλλαγών σε 2-3 προτάσεις"
}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
""".strip()


FULL_HTML_GENERATION_PROMPT = """
Είσαι expert SEO content creator. Θα σου δοθεί μια πρόταση βελτίωσης (proposal) και το υπάρχον περιεχόμενο (αν υπάρχει).
Δημιούργησε το ΠΛΗΡΕΣ νέο κείμενο της σελίδας σε μορφή HTML, έτοιμο για copy-paste στο Elementor.

ΒΑΣΙΚΟΙ ΚΑΝΟΝΕΣ HTML:
1. Χρησιμοποίησε ΜΟΝΟ: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>, <a>
2. Μην χρησιμοποιήσεις <div>, <span>, classes ή styles
3. Ένα μόνο <h1> για τον κύριο τίτλο
4. Χρησιμοποίησε <h2> για main sections και <h3> για subsections
5. Στόχος: 800-1500 λέξεις

SEO ΚΑΝΟΝΕΣ (ΚΡΙΣΙΜΟ):
1. KEYWORD ΣΤΗΝ ΕΙΣΑΓΩΓΗ: Η φράση-κλειδί ΠΡΕΠΕΙ να εμφανίζεται στην πρώτη παράγραφο
2. KEYWORD DENSITY: Η φράση-κλειδί πρέπει να εμφανίζεται 4-8 φορές στο κείμενο (φυσικά, όχι spam)
3. KEYWORD ΣΕ HEADINGS: Τουλάχιστον 2-3 από τα <h2>/<h3> να περιέχουν τη φράση-κλειδί ή συνώνυμα
4. Χρησιμοποίησε <strong> για να τονίσεις τη φράση-κλειδί 1-2 φορές

ΕΣΩΤΕΡΙΚΟΙ ΣΥΝΔΕΣΜΟΙ (ΠΟΛΥ ΣΗΜΑΝΤΙΚΟ):
Θα σου δοθεί λίστα με τις σελίδες του ΙΔΙΟΥ site (available_pages_for_internal_links).
- Χρησιμοποίησε ΜΟΝΟ URLs από αυτή τη λίστα για internal links
- Πρόσθεσε 3-5 εσωτερικούς συνδέσμους σε ΣΧΕΤΙΚΕΣ σελίδες
- Οι σύνδεσμοι πρέπει να έχουν ΝΟΗΜΑΤΙΚΗ ΣΥΝΕΠΕΙΑ με το context
- Χρησιμοποίησε anchor text που περιγράφει τη σελίδα-στόχο
- Τοποθέτησε τους συνδέσμους φυσικά μέσα στο κείμενο
- Μορφή: <a href="URL">περιγραφικό anchor text</a>

ΕΞΩΤΕΡΙΚΟΙ ΣΥΝΔΕΣΜΟΙ (ΠΡΟΑΙΡΕΤΙΚΟ):
Θα σου δοθεί επίσης λίστα με σελίδες από "αδελφικά" sites (sister_site_pages_for_external_links).
- Μπορείς να προσθέσεις 0-2 εξωτερικούς συνδέσμους αν είναι ΠΟΛΥ σχετικοί
- Πρόσθεσε rel="noopener" στους εξωτερικούς συνδέσμους
- Μορφή: <a href="URL" rel="noopener">anchor text</a>

Παράδειγμα σωστού linking:
"Για τη συντήρηση του λέβητα, δείτε τις <a href="/syntirisi-lebita">υπηρεσίες συντήρησης</a>.
Για περισσότερες πληροφορίες σχετικά με ενεργειακές λύσεις, επισκεφθείτε το <a href="https://sister-site.gr/energeia" rel="noopener">αδελφικό μας site</a>."

ΕΙΚΟΝΕΣ (IMAGE PLACEHOLDERS):
Πρόσθεσε 2-3 σημεία για εικόνες με αυτή τη μορφή:
<!-- IMAGE: [περιγραφή εικόνας] | ALT: [alt text με keyword] -->

Παράδειγμα:
<!-- IMAGE: Τεχνικός ελέγχει σωλήνωση αερίου με μανόμετρο | ALT: Έλεγχος στεγανότητας σωληνώσεων αερίου με ψηφιακό μανόμετρο -->

ΔΟΜΗ HTML:
<h1>Τίτλος με keyword</h1>

<p>Εισαγωγή με keyword στην πρώτη πρόταση...</p>

<!-- IMAGE: ... | ALT: ... -->

<h2>Section με keyword ή συνώνυμο</h2>
<p>Περιεχόμενο με <a href="...">internal link</a>...</p>

<h2>Άλλο section</h2>
<p>Περιεχόμενο...</p>

<!-- IMAGE: ... | ALT: ... -->

<h2>Συχνές Ερωτήσεις</h2>
<h3>Ερώτηση με keyword;</h3>
<p>Απάντηση...</p>

SCHEMAS - Δημιούργησε Schema.org JSON-LD για:
- FAQPage: αν υπάρχουν FAQs
- HowTo: αν υπάρχουν βήματα/οδηγίες
- Article: πάντα
- Service: για υπηρεσίες

ΣΥΜΠΛΗΡΩΜΑΤΙΚΕΣ ΟΔΗΓΙΕΣ:
Αν υπάρχει πεδίο "custom_instructions" στα δεδομένα, ακολούθησε τις οδηγίες αυτές με προτεραιότητα.
Παραδείγματα: "δώσε έμφαση στην ασφάλεια", "πρόσθεσε τιμές", "χρησιμοποίησε πιο απλή γλώσσα"

Επίστρεψε ΜΟΝΟ JSON:
{
  "html_content": "το πλήρες HTML με internal/external links και image placeholders",
  "meta_title": "SEO title (50-60 χαρακτήρες, με keyword)",
  "meta_description": "SEO description (150-160 χαρακτήρες, με keyword)",
  "focus_keyphrase": "η κύρια φράση-κλειδί",
  "word_count": αριθμός λέξεων,
  "keyword_count": πόσες φορές εμφανίζεται το keyword,
  "sections": ["τίτλος section 1", "τίτλος section 2"],
  "includes_faq": true/false,
  "faq_items": [{"question": "...", "answer": "..."}],
  "howto_steps": [{"name": "Βήμα 1", "text": "Περιγραφή..."}],
  "service_name": "Όνομα υπηρεσίας αν είναι service page",
  "internal_links": [{"url": "...", "anchor": "...", "context": "γιατί είναι σχετικό"}],
  "external_links": [{"url": "...", "anchor": "...", "site": "όνομα site"}],
  "image_suggestions": [{"description": "...", "alt_text": "..."}]
}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
""".strip()


class ContentGenerator:
    """Generates proposed content changes based on proposals."""

    def __init__(self) -> None:
        self.llm = LLMService()
        self.wp = WordPressService()
        self.seo_scorer = SEOScorer()

    def _get_cache_key(self, proposal: dict) -> str:
        """Generate a cache key for a proposal."""
        key_data = (
            f"{proposal.get('id')}:{proposal.get('proposal_type')}:"
            f"{proposal.get('target_title')}:{proposal.get('site_url')}"
        )
        return hashlib.md5(key_data.encode()).hexdigest()

    def generate_preview(self, proposal: dict, site_pages: list[dict] | None = None) -> dict:
        """
        Generate a preview of proposed changes for a proposal.

        Args:
            proposal: The proposal dict with type, title, summary, etc.
            site_pages: Optional list of site pages (will fetch if not provided)

        Returns:
            Dict with current vs proposed content comparisons
        """
        # Check cache first
        cache_key = self._get_cache_key(proposal)
        if cache_key in _preview_cache:
            logger.info("Preview cache hit for proposal %s", proposal.get("id"))
            return _preview_cache[cache_key]

        proposal_type = proposal.get("proposal_type", "")
        target_title = proposal.get("target_title", "")
        summary = proposal.get("summary", "")
        outline = proposal.get("outline", "")
        parent_pillar = proposal.get("parent_pillar")
        site_url = proposal.get("site_url")

        # Fetch current page content if this is an update proposal
        current_page = None
        if "update" in proposal_type or "improve" in proposal_type:
            current_page = self._find_page_by_title(
                target_title,
                site_pages,
                site_url=site_url,
            )

        # Build the generation request
        if proposal_type == "improve_seo_meta":
            result = self._generate_seo_meta_preview(proposal, current_page)
        elif proposal_type == "add_faq_section":
            result = self._generate_faq_preview(proposal, current_page)
        elif proposal_type == "add_howto_section":
            result = self._generate_howto_preview(proposal, current_page)
        elif proposal_type == "geo_optimize":
            result = self._generate_geo_preview(proposal, current_page)
        elif "satellite" in proposal_type:
            result = self._generate_satellite_preview(proposal, current_page, parent_pillar)
        else:
            result = self._generate_generic_preview(proposal, current_page)

        # Store in cache
        if len(_preview_cache) >= _MAX_CACHE_SIZE:
            # Remove oldest entry
            oldest_key = next(iter(_preview_cache))
            del _preview_cache[oldest_key]
        _preview_cache[cache_key] = result
        logger.info("Preview cached for proposal %s", proposal.get("id"))

        return result

    def _find_page_by_title(
        self,
        title: str,
        site_pages: list[dict] | None = None,
        site_url: str | None = None,
    ) -> dict | None:
        """Find a page by its title."""
        if not site_pages:
            site_pages = self.wp.fetch_all_content(site_url=site_url)

        title_lower = title.lower().strip()
        for page in site_pages:
            if page.get("title", "").lower().strip() == title_lower:
                return page
            # Also check slug
            if page.get("slug", "").lower().replace("-", " ") in title_lower:
                return page

        return None

    def _generate_seo_meta_preview(self, proposal: dict, current_page: dict | None) -> dict:
        """Generate SEO meta improvements preview."""
        current_yoast = {}
        current_content = ""

        if current_page:
            current_yoast = current_page.get("yoast", {})
            current_content = current_page.get("content", "")[:2000]

        payload = {
            "proposal_type": "improve_seo_meta",
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "current_meta": {
                "title": current_yoast.get("title", ""),
                "description": current_yoast.get("description", ""),
                "focus_keyphrase": current_yoast.get("focus_keyphrase", ""),
            },
            "content_excerpt": current_content,
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": "improve_seo_meta",
            "current_page": {
                "title": current_page.get("title") if current_page else None,
                "slug": current_page.get("slug") if current_page else None,
                "url": current_page.get("url") if current_page else None,
            },
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _generate_faq_preview(self, proposal: dict, current_page: dict | None) -> dict:
        """Generate FAQ section preview."""
        current_content = ""
        if current_page:
            current_content = current_page.get("content", "")[:3000]

        payload = {
            "proposal_type": "add_faq_section",
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "existing_faq_suggestions": proposal.get("faq_suggestions", ""),
            "content_excerpt": current_content,
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": "add_faq_section",
            "current_page": {
                "title": current_page.get("title") if current_page else None,
                "slug": current_page.get("slug") if current_page else None,
                "url": current_page.get("url") if current_page else None,
            },
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _generate_howto_preview(self, proposal: dict, current_page: dict | None) -> dict:
        """Generate HowTo section preview."""
        current_content = ""
        if current_page:
            current_content = current_page.get("content", "")[:3000]

        payload = {
            "proposal_type": "add_howto_section",
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "outline": proposal.get("outline", ""),
            "content_excerpt": current_content,
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": "add_howto_section",
            "current_page": {
                "title": current_page.get("title") if current_page else None,
                "slug": current_page.get("slug") if current_page else None,
            },
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _generate_geo_preview(self, proposal: dict, current_page: dict | None) -> dict:
        """Generate GEO optimization preview."""
        current_content = ""
        if current_page:
            current_content = current_page.get("content", "")[:4000]

        payload = {
            "proposal_type": "geo_optimize",
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "outline": proposal.get("outline", ""),
            "content_excerpt": current_content,
            "instructions": "Βελτιστοποίησε για AI search: clear answers, FAQ, definitions, structured summaries",
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": "geo_optimize",
            "current_page": {
                "title": current_page.get("title") if current_page else None,
                "slug": current_page.get("slug") if current_page else None,
            },
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _generate_satellite_preview(
        self, proposal: dict, current_page: dict | None, parent_pillar: str | None
    ) -> dict:
        """Generate satellite post preview."""
        payload = {
            "proposal_type": proposal.get("proposal_type"),
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "outline": proposal.get("outline", ""),
            "parent_pillar": parent_pillar,
            "suggested_schema": proposal.get("suggested_schema", ""),
            "is_new_content": current_page is None,
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": proposal.get("proposal_type"),
            "is_new": current_page is None,
            "parent_pillar": parent_pillar,
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _generate_generic_preview(self, proposal: dict, current_page: dict | None) -> dict:
        """Generate generic proposal preview."""
        current_content = ""
        if current_page:
            current_content = current_page.get("content", "")[:3000]

        payload = {
            "proposal_type": proposal.get("proposal_type"),
            "target_title": proposal.get("target_title", ""),
            "proposal_summary": proposal.get("summary", ""),
            "outline": proposal.get("outline", ""),
            "content_excerpt": current_content,
        }

        result = self.llm.generate_json(CONTENT_GENERATION_PROMPT, payload)

        return {
            "proposal_id": proposal.get("id"),
            "proposal_type": proposal.get("proposal_type"),
            "current_page": {
                "title": current_page.get("title") if current_page else None,
                "slug": current_page.get("slug") if current_page else None,
            },
            "changes": result,
            "generated_at": self._now_iso(),
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generated_content_dir(self) -> Path:
        """Return the configured output directory for generated HTML files."""
        return Path(settings.GENERATED_CONTENT_DIR)

    def generate_full_html(
        self, proposal: dict, site_pages: list[dict] | None = None, site_url: str | None = None
    ) -> dict:
        """
        Generate full HTML content for Elementor based on a proposal.

        Args:
            proposal: The proposal dict with type, title, summary, outline, etc.
            site_pages: Optional list of site pages (will fetch if not provided)
            site_url: The target site URL for filtering internal links

        Returns:
            Dict with generated HTML, metadata, and file path
        """
        proposal_type = proposal.get("proposal_type", "")
        target_title = proposal.get("target_title", "")
        site_url = site_url or proposal.get("site_url")

        # Fetch site pages for internal linking
        if site_pages is None:
            try:
                site_pages = self.wp.fetch_all_content(site_url=site_url)
                logger.info("Fetched %d site pages for internal linking from %s", len(site_pages), site_url)
            except Exception as e:
                logger.warning("Could not fetch site pages: %s", e)
                site_pages = []

        current_page = None
        current_content = ""
        if "update" in proposal_type or "improve" in proposal_type:
            current_page = self._find_page_by_title(target_title, site_pages)
            if current_page:
                current_content = current_page.get("content", "")

        # Separate internal links (same site) and potential external links (sister sites)
        internal_pages, sister_site_pages = self._categorize_pages_by_site(site_pages, site_url)

        # Format pages for linking
        internal_pages_for_linking = self._format_pages_for_linking(internal_pages, target_title)
        sister_pages_for_external = self._format_pages_for_linking(sister_site_pages, target_title)

        # Get custom instructions if provided
        custom_instructions = proposal.get("custom_instructions", "")

        payload = {
            "proposal_type": proposal_type,
            "target_title": target_title,
            "target_site": site_url,
            "proposal_summary": proposal.get("summary", ""),
            "outline": proposal.get("outline", ""),
            "parent_pillar": proposal.get("parent_pillar"),
            "suggested_schema": proposal.get("suggested_schema", ""),
            "faq_suggestions": proposal.get("faq_suggestions", ""),
            "seo_meta_suggestions": proposal.get("seo_meta_suggestions", ""),
            "existing_content": current_content[:5000] if current_content else "Δεν υπάρχει υπάρχον περιεχόμενο - δημιούργησε νέο",
            "is_new_page": current_page is None,
            "available_pages_for_internal_links": internal_pages_for_linking,
            "sister_site_pages_for_external_links": sister_pages_for_external[:10],
        }

        # Add custom instructions if provided
        if custom_instructions:
            payload["custom_instructions"] = f"ΕΠΙΠΛΕΟΝ ΟΔΗΓΙΕΣ ΑΠΟ ΤΟΝ ΧΡΗΣΤΗ: {custom_instructions}"
            logger.info("Custom instructions added: %s", custom_instructions[:100])

        logger.info("Generating full HTML for proposal %s: %s", proposal.get("id"), target_title)
        result = self.llm.generate_json(FULL_HTML_GENERATION_PROMPT, payload)

        html_content = result.get("html_content", "")
        saved_path = self._save_html_to_file(proposal, result)

        # Calculate SEO score
        seo_score = self.seo_scorer.calculate_score(result)
        logger.info("SEO Score for proposal %s: %d (%s)", proposal.get("id"), seo_score.total_score, seo_score.grade)

        return {
            "proposal_id": proposal.get("id"),
            "target_title": target_title,
            "proposal_type": proposal_type,
            "html_content": html_content,
            "meta_title": result.get("meta_title", ""),
            "meta_description": result.get("meta_description", ""),
            "focus_keyphrase": result.get("focus_keyphrase", ""),
            "word_count": result.get("word_count", 0),
            "keyword_count": result.get("keyword_count", 0),
            "sections": result.get("sections", []),
            "includes_faq": result.get("includes_faq", False),
            "internal_links": result.get("internal_links", []),
            "image_suggestions": result.get("image_suggestions", []),
            "file_path": saved_path,
            "generated_at": self._now_iso(),
            "current_page_url": current_page.get("url") if current_page else None,
            "seo_score": seo_score.to_dict(),
        }

    def _categorize_pages_by_site(
        self, all_pages: list[dict], target_site_url: str | None
    ) -> tuple[list[dict], list[dict]]:
        """
        Separate pages into internal (same site) and sister site pages.

        Args:
            all_pages: All fetched pages
            target_site_url: The URL of the target site (e.g., "https://e-therm.gr")

        Returns:
            Tuple of (internal_pages, sister_site_pages)
        """
        if not target_site_url:
            return all_pages, []

        # Extract domain from target site URL
        target_domain = self._extract_domain(target_site_url)
        internal_pages = []
        sister_pages = []

        for page in all_pages:
            page_url = page.get("url", "")
            page_domain = self._extract_domain(page_url)

            if page_domain == target_domain:
                internal_pages.append(page)
            elif page_domain:
                sister_pages.append(page)

        logger.info(
            "Categorized pages: %d internal (%s), %d sister sites",
            len(internal_pages), target_domain, len(sister_pages)
        )
        return internal_pages, sister_pages

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL (e.g., 'https://e-therm.gr/page' -> 'e-therm.gr')."""
        if not url:
            return ""
        url = url.lower().strip()
        # Remove protocol
        if "://" in url:
            url = url.split("://", 1)[1]
        # Remove path
        if "/" in url:
            url = url.split("/", 1)[0]
        # Remove www
        if url.startswith("www."):
            url = url[4:]
        return url

    def _format_pages_for_linking(
        self, site_pages: list[dict], exclude_title: str
    ) -> list[dict]:
        """
        Format site pages for internal linking suggestions.
        Returns a simplified list with title, url, and brief description.
        """
        formatted = []
        exclude_title_lower = exclude_title.lower().strip()

        for page in site_pages:
            title = page.get("title", "")
            if title.lower().strip() == exclude_title_lower:
                continue

            url = page.get("url", "")
            if not url:
                slug = page.get("slug", "")
                if slug:
                    url = f"/{slug}"

            content = page.get("content", "")
            description = content[:150].strip() + "..." if len(content) > 150 else content

            formatted.append({
                "title": title,
                "url": url,
                "description": description,
                "type": page.get("type", "page"),
            })

        return formatted[:30]

    def _save_html_to_file(self, proposal: dict, content: dict) -> str:
        """Save generated HTML content to a file."""
        output_dir = self._generated_content_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        target_title = proposal.get("target_title", "untitled")
        slug = self._slugify(target_title)
        proposal_id = proposal.get("id", 0)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        filename = f"{proposal_id}_{slug}_{timestamp}.html"
        filepath = output_dir / filename

        html_content = content.get("html_content", "")
        meta_title = content.get("meta_title", "")
        meta_description = content.get("meta_description", "")
        focus_keyphrase = content.get("focus_keyphrase", "")

        schemas_json = self._generate_schemas(proposal, content)

        internal_links = content.get("internal_links", [])
        image_suggestions = content.get("image_suggestions", [])
        internal_links_info = "\n    ".join([f"- {link.get('anchor', '')} -> {link.get('url', '')}" for link in internal_links[:5]])
        image_info = "\n    ".join([f"- {img.get('alt_text', '')}" for img in image_suggestions[:3]])

        full_html = f"""<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta_title}</title>
    <meta name="description" content="{meta_description}">
    <meta name="keywords" content="{focus_keyphrase}">
    <!--
    =================================================
    SEO METADATA (για χρήση στο Yoast/WordPress)
    =================================================
    Meta Title: {meta_title}
    Meta Description: {meta_description}
    Focus Keyphrase: {focus_keyphrase}

    SEO STATS:
    - Word Count: {content.get("word_count", 0)}
    - Keyword Count: {content.get("keyword_count", 0)}
    - Internal Links: {len(internal_links)}
    - Image Placeholders: {len(image_suggestions)}

    INTERNAL LINKS:
    {internal_links_info if internal_links_info else "    - Κανένας"}

    IMAGES (προσθέστε εικόνες με αυτά τα alt texts):
    {image_info if image_info else "    - Καμία πρόταση"}

    Generated: {datetime.now(timezone.utc).isoformat()}
    Proposal ID: {proposal.get("id")}
    =================================================
    -->
</head>
<body>
<!-- ΑΝΤΙΓΡΑΨΤΕ ΤΟ ΠΑΡΑΚΑΤΩ ΠΕΡΙΕΧΟΜΕΝΟ ΣΤΟ ELEMENTOR -->

{html_content}

<!-- ΤΕΛΟΣ ΠΕΡΙΕΧΟΜΕΝΟΥ -->

<!-- ============================================= -->
<!-- SCHEMA.ORG JSON-LD - Αντιγράψτε στο <head> του WordPress ή χρησιμοποιήστε plugin -->
<!-- Απαραίτητα για Google Search και AI Agents (ChatGPT, Perplexity, κλπ) -->
<!-- ============================================= -->

{schemas_json}

</body>
</html>"""

        filepath.write_text(full_html, encoding="utf-8")
        logger.info("Saved generated HTML to %s", filepath)

        return str(filepath)

    def _generate_schemas(self, proposal: dict, content: dict) -> str:
        """Generate Schema.org JSON-LD structured data with real site data."""
        schemas = []
        site_url = proposal.get("site_url")
        site_config = get_site_config(site_url)

        target_title = proposal.get("target_title", "")
        meta_title = content.get("meta_title", target_title)
        meta_description = content.get("meta_description", "")
        service_name = content.get("service_name", "")
        focus_keyphrase = content.get("focus_keyphrase", "")

        # Extract site info
        company_name = site_config.get("name", "")
        company_url = site_config.get("url", "")
        company_logo = site_config.get("logo", "")
        company_phone = site_config.get("telephone", "")
        company_desc = site_config.get("description", "")
        business_type = site_config.get("business_type", "LocalBusiness")
        address = site_config.get("address", {})
        geo = site_config.get("geo", {})

        # Article Schema
        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta_title,
            "description": meta_description,
            "author": {
                "@type": "Organization",
                "name": company_name,
                "url": company_url,
            },
            "publisher": {
                "@type": "Organization",
                "name": company_name,
                "logo": {
                    "@type": "ImageObject",
                    "url": company_logo,
                },
            },
            "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "dateModified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        schemas.append(article_schema)

        # FAQPage Schema
        faq_items = content.get("faq_items", [])
        if faq_items and len(faq_items) > 0:
            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("question", ""),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": item.get("answer", ""),
                        },
                    }
                    for item in faq_items
                ],
            }
            schemas.append(faq_schema)

        # HowTo Schema
        howto_steps = content.get("howto_steps", [])
        if howto_steps and len(howto_steps) > 0:
            howto_schema = {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": meta_title,
                "description": meta_description,
                "step": [
                    {
                        "@type": "HowToStep",
                        "position": i + 1,
                        "name": step.get("name", f"Βήμα {i+1}"),
                        "text": step.get("text", ""),
                    }
                    for i, step in enumerate(howto_steps)
                ],
            }
            schemas.append(howto_schema)

        # Service Schema
        service_schema = {
            "@context": "https://schema.org",
            "@type": "Service",
            "name": service_name or meta_title,
            "description": meta_description,
            "serviceType": focus_keyphrase,
            "provider": {
                "@type": business_type,
                "name": company_name,
                "telephone": company_phone,
                "url": company_url,
            },
            "areaServed": [
                {"@type": "AdministrativeArea", "name": area}
                for area in AREAS_SERVED[:20]
            ],
        }
        schemas.append(service_schema)

        # HVACBusiness / LocalBusiness Schema (full)
        business_schema = {
            "@context": "https://schema.org",
            "@type": business_type,
            "name": company_name,
            "url": company_url,
            "image": company_logo,
            "telephone": company_phone,
            "description": company_desc,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": address.get("streetAddress", ""),
                "addressLocality": address.get("addressLocality", ""),
                "addressRegion": address.get("addressRegion", "Αττική"),
                "postalCode": address.get("postalCode", ""),
                "addressCountry": address.get("addressCountry", "GR"),
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": geo.get("latitude", ""),
                "longitude": geo.get("longitude", ""),
            },
            "areaServed": [
                {"@type": "AdministrativeArea", "name": area}
                for area in AREAS_SERVED
            ],
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": company_phone,
                "contactType": "Customer Service",
                "areaServed": "GR",
                "availableLanguage": site_config.get("contact_languages", ["Greek"]),
            },
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": hours.get("dayOfWeek", []),
                    "opens": hours.get("opens", ""),
                    "closes": hours.get("closes", ""),
                }
                for hours in site_config.get("opening_hours", [])
            ],
            "priceRange": site_config.get("price_range", "€€"),
            "currenciesAccepted": site_config.get("currencies_accepted", "EUR"),
            "paymentAccepted": site_config.get("payment_accepted", ""),
        }

        # Add social links if available
        social_links = site_config.get("social_links", [])
        if social_links:
            business_schema["sameAs"] = social_links

        schemas.append(business_schema)

        # Format all schemas as script tags
        schema_scripts = []
        for schema in schemas:
            schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
            schema_scripts.append(f'<script type="application/ld+json">\n{schema_json}\n</script>')

        return "\n\n".join(schema_scripts)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text[:50]
