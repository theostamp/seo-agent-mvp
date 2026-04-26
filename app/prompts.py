STYLE_EXTRACTION_PROMPT = """
Είσαι content analyst. Ανάλυσε τα παρακάτω δείγματα περιεχομένου από ένα site και εξήγαγε το style profile.

Εξέτασε:
1. Τόνος επικοινωνίας (formal/professional/friendly/casual)
2. Προσφώνηση (εσείς/εσύ/απρόσωπο)
3. Μήκος παραγράφων (σύντομες/μεσαίες/μακριές)
4. Χρήση τεχνικής ορολογίας (υψηλή/μέτρια/χαμηλή)
5. Δομή περιεχομένου (bullets/παράγραφοι/μικτή)
6. Στυλ τίτλων (ερωτηματικοί/δηλωτικοί/how-to)
7. Call-to-action στυλ (άμεσο/έμμεσο/καθόλου)

Επίστρεψε ΜΟΝΟ JSON:
{
  "tone": "formal|professional|friendly|casual",
  "addressing": "εσείς|εσύ|απρόσωπο",
  "paragraph_length": "short|medium|long",
  "technical_level": "high|medium|low",
  "structure": "bullets|paragraphs|mixed",
  "title_style": "question|statement|how-to",
  "cta_style": "direct|indirect|none",
  "sample_phrases": ["χαρακτηριστική φράση 1", "χαρακτηριστική φράση 2"],
  "avoid_patterns": ["pattern να αποφευχθεί"],
  "summary": "Σύντομη περιγραφή του στυλ σε 1-2 προτάσεις"
}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
""".strip()


TOPOLOGY_ANALYSIS_PROMPT = """
Είσαι content architect. Ανάλυσε τη δομή ενός site με pillar-satellite μοντέλο.

Θα σου δοθούν:
- pillars: κύριες σελίδες υπηρεσιών
- satellites: υποστηρικτικά posts
- orphans: περιεχόμενο χωρίς συνδέσεις
- pillar_satellite_map: τρέχουσες συνδέσεις

Αποστολή:
1. Πρότεινε βελτιωμένες αντιστοιχίσεις pillar→satellite
2. Εντόπισε κενά στην κάλυψη (pillars χωρίς αρκετά satellites)
3. Πρότεινε ποια orphans θα μπορούσαν να γίνουν satellites

Επίστρεψε ΜΟΝΟ JSON:
{
  "suggested_mappings": {
    "pillar_slug": ["satellite_slug1", "satellite_slug2"]
  },
  "coverage_gaps": [
    {
      "pillar_slug": "slug",
      "pillar_title": "τίτλος",
      "current_satellites": 1,
      "suggested_minimum": 3,
      "missing_topics": ["θέμα1", "θέμα2"]
    }
  ],
  "orphan_suggestions": [
    {
      "orphan_slug": "slug",
      "suggested_pillar": "pillar_slug",
      "reason": "γιατί ταιριάζει"
    }
  ],
  "insights": ["παρατήρηση 1", "παρατήρηση 2"]
}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
""".strip()


KEYWORD_DISCOVERY_PROMPT = """
Είσαι SEO strategist για ελληνικό τεχνικό / επαγγελματικό site στον κλάδο κατασκευών και ανακαινίσεων.

Σκοπός:
- Πάρε μία κύρια κατηγορία θέματος
- Πάρε seed keywords
- Πρότεινε σχετικές λέξεις-κλειδιά και clusters
- Δώσε μόνο σχετικούς όρους για υπηρεσίες, προβλήματα, intent και πιθανές landing pages
- Προτίμησε ελληνική γλώσσα
- Απέφυγε άσχετους ή υπερβολικά γενικούς όρους
- Σκέψου τοπικά keywords αν δοθεί location

Επίστρεψε ΜΟΝΟ JSON με μορφή:
{
  "keywords": ["keyword1", "keyword2", ...],
  "clusters": [
    {
      "name": "Όνομα cluster",
      "intent": "commercial|informational|local|transactional",
      "keywords": ["keyword1", "keyword2"]
    }
  ]
}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
""".strip()


GAP_ANALYSIS_PROMPT_TEMPLATE = """
Είσαι content strategist για ελληνικό site στον κλάδο κατασκευών.

Θα σου δοθούν:
1. Keyword clusters που ανακαλύφθηκαν
2. Content topology του site (pillars, satellites, homepage)
3. Style profile του site

{style_instructions}

{topology_instructions}

ΚΑΝΟΝΕΣ CONTENT ARCHITECTURE:
1. ΠΟΤΕ μην προτείνεις bulk content στο homepage - μόνο μικρές βελτιώσεις στο messaging
2. Τα pillars είναι κύριες σελίδες υπηρεσιών - βελτίωση χωρίς αλλαγή δομής
3. Τα satellites είναι υποστηρικτικά posts - εδώ προσθέτουμε νέο περιεχόμενο
4. Κάθε pillar πρέπει να έχει 3-5 satellites για καλό SEO
5. Προτίμησε create_satellite_post αντί για update_pillar_page

ΚΑΝΟΝΕΣ ΓΙΑ HOMEPAGE / ΑΡΧΙΚΗ ΣΕΛΙΔΑ:
1. Η αρχική λειτουργεί ως κόμβος πλοήγησης, όχι ως αναλυτικό άρθρο
2. Ιδανικό μήκος: 250-700 λέξεις, με σύντομες ενότητες
3. Πρότεινε 4-8 internal links από την αρχική προς βασικά pillars/υπηρεσίες
4. Αν λείπει CTA, πρότεινε σύντομο CTA σε hero και στο τέλος
5. Για homepage proposals χρησιμοποίησε update_pillar_page ή link_existing_content, όχι create_satellite_post
6. Μην προτείνεις FAQ/HowTo bulk sections στην αρχική εκτός αν υπάρχει ήδη αντίστοιχη δομή

ΤΥΠΟΙ ΠΡΟΤΑΣΕΩΝ (κατά σειρά προτεραιότητας):
- create_satellite_post: νέο δορυφορικό post για υπάρχον pillar (ΠΡΟΤΙΜΗΣΕ ΑΥΤΟ)
- update_satellite_post: βελτίωση υπάρχοντος satellite
- update_pillar_page: ελαφριά βελτίωση pillar (keywords, meta, μικρές προσθήκες)
- link_existing_content: προσθήκη internal links μεταξύ υπαρχόντων
- create_pillar_page: νέο pillar μόνο αν δεν υπάρχει σχετική κατηγορία
- no_action: επαρκής κάλυψη

Για κάθε πρόταση δώσε:
- proposal_type: ένας από τους παραπάνω τύπους
- target_title: τίτλος (υπάρχων ή προτεινόμενος)
- parent_pillar: slug του pillar που ανήκει (για satellites)
- summary: τι πρέπει να γίνει
- outline: λίστα ενοτήτων
- suggested_schema: Schema.org types
- priority: high/medium/low

Επίστρεψε ΜΟΝΟ JSON:
{{
  "proposals": [
    {{
      "proposal_type": "create_satellite_post|update_satellite_post|update_pillar_page|link_existing_content|create_pillar_page|no_action",
      "target_title": "Τίτλος",
      "parent_pillar": "pillar-slug ή null",
      "summary": "Περιγραφή",
      "outline": ["Ενότητα 1", "Ενότητα 2"],
      "suggested_schema": ["Article", "FAQPage"],
      "priority": "high|medium|low"
    }}
  ]
}}

Μην προσθέσεις κανένα επιπλέον κείμενο πριν ή μετά το JSON.
"""


def build_gap_analysis_prompt(
    style_profile: dict | None = None,
    topology: dict | None = None,
) -> str:
    """Build the gap analysis prompt with style and topology instructions."""

    # Style instructions
    if style_profile:
        style_instructions = f"""
STYLE PROFILE ΤΟΥ SITE (ακολούθησε αυτό το ύφος):
- Τόνος: {style_profile.get('tone', 'professional')}
- Προσφώνηση: {style_profile.get('addressing', 'εσείς')}
- Μήκος παραγράφων: {style_profile.get('paragraph_length', 'medium')}
- Τεχνική ορολογία: {style_profile.get('technical_level', 'medium')}
- Δομή: {style_profile.get('structure', 'mixed')}
- Στυλ τίτλων: {style_profile.get('title_style', 'statement')}
- CTA στυλ: {style_profile.get('cta_style', 'indirect')}
- Χαρακτηριστικές φράσεις: {', '.join(style_profile.get('sample_phrases', []))}
- Αποφυγή: {', '.join(style_profile.get('avoid_patterns', []))}
- Σύνοψη στυλ: {style_profile.get('summary', '')}
"""
    else:
        style_instructions = "Χρησιμοποίησε επαγγελματικό ύφος με προσφώνηση στον πληθυντικό (εσείς)."

    # Topology instructions
    if topology:
        pillars_info = "\n".join([
            f"  - {p.get('title', 'N/A')} (slug: {p.get('slug', 'N/A')}, satellites: {len(topology.get('pillar_satellite_map', {}).get(p.get('slug'), []))})"
            for p in topology.get('pillars', [])[:10]
        ]) or "  Δεν βρέθηκαν pillars"

        homepage = topology.get('homepage')
        homepage_info = f"{homepage.get('title', 'N/A')} (slug: {homepage.get('slug', 'N/A')})" if homepage else "Δεν εντοπίστηκε"

        coverage_gaps = topology.get('coverage_gaps', [])
        gaps_info = "\n".join([
            f"  - {g.get('pillar_title', 'N/A')}: έχει {g.get('current_satellites', 0)}, χρειάζεται {g.get('suggested_minimum', 3)}+"
            for g in coverage_gaps[:5]
        ]) or "  Δεν εντοπίστηκαν κενά"

        topology_instructions = f"""
CONTENT TOPOLOGY ΤΟΥ SITE:

Homepage (ΜΗΝ ΠΡΟΣΘΕΣΕΙΣ BULK CONTENT):
  {homepage_info}

Pillar Pages (κύριες σελίδες υπηρεσιών):
{pillars_info}

Coverage Gaps (pillars που χρειάζονται περισσότερα satellites):
{gaps_info}

Orphan Content: {len(topology.get('orphans', []))} posts χωρίς σύνδεση
"""
    else:
        topology_instructions = "Δεν υπάρχει topology analysis - χρησιμοποίησε γενικές αρχές SEO."

    return GAP_ANALYSIS_PROMPT_TEMPLATE.format(
        style_instructions=style_instructions,
        topology_instructions=topology_instructions,
    ).strip()


# Backwards compatibility
GAP_ANALYSIS_PROMPT = build_gap_analysis_prompt(None, None)


# ============================================================================
# GEO (Generative Engine Optimization) - AI Search Optimization
# ============================================================================

GEO_CONTENT_GUIDELINES = """
ΟΔΗΓΙΕΣ GEO (Generative Engine Optimization) - Βελτιστοποίηση για AI Search:

1. CLEAR ANSWERS FIRST (Καθαρές απαντήσεις στην αρχή):
   - Ξεκίνα κάθε section με μια σαφή, περιεκτική απάντηση (2-3 προτάσεις)
   - Αυτό βοηθά τα AI να εξάγουν απαντήσεις για featured snippets
   - Παράδειγμα: "Η επισκευή μπαλκονιού κοστίζει 50-150€/τμ. Η τιμή εξαρτάται από..."

2. FAQ SECTIONS (Ενότητες Ερωτήσεων-Απαντήσεων):
   - Κάθε σελίδα πρέπει να έχει 3-5 FAQs
   - Χρησιμοποίησε πραγματικές ερωτήσεις που θα έκανε ο χρήστης
   - Μορφή: "Ερώτηση: ... Απάντηση: ..."
   - Υποστήριξε με FAQPage Schema

3. ENTITY DEFINITIONS (Ορισμοί Οντοτήτων):
   - Όρισε σαφώς τεχνικούς όρους την πρώτη φορά που εμφανίζονται
   - Παράδειγμα: "Η μόνωση XPS (εξηλασμένη πολυστερίνη) είναι..."
   - Βοηθά τα AI να κατανοήσουν το context

4. STRUCTURED SUMMARIES (Δομημένες Περιλήψεις):
   - Πρόσθεσε TL;DR στην αρχή μακροσκελών άρθρων
   - Χρησιμοποίησε bullet points για key takeaways
   - Τελείωσε με "Συμπέρασμα" section

5. CONVERSATIONAL TONE (Συνομιλιακό Ύφος):
   - Γράψε όπως θα απαντούσες σε έναν πελάτη
   - Χρησιμοποίησε ερωτήσεις ρητορικές: "Αναρωτιέστε πόσο κοστίζει;"
   - Αυτό ταιριάζει με voice search και AI assistants

6. AUTHORITATIVE CITATIONS (Αξιόπιστες Αναφορές):
   - Αναφέρου σε πρότυπα (π.χ. ΕΛΟΤ, ΕΝ)
   - Χρησιμοποίησε στατιστικά με πηγές
   - Αυτό αυξάνει την αξιοπιστία για AI

7. HOWTO STRUCTURE (Δομή Οδηγιών):
   - Αριθμημένα βήματα για διαδικασίες
   - Κάθε βήμα με σαφή τίτλο και περιγραφή
   - Υποστήριξε με HowTo Schema
"""

YOAST_ANALYSIS_PROMPT = """
Ανάλυσε τα Yoast SEO δεδομένα και πρότεινε βελτιώσεις.

Θα σου δοθούν:
- Τρέχουσες Yoast ρυθμίσεις (focus keyphrase, meta title/description)
- SEO issues που εντοπίστηκαν
- Υπάρχοντα schemas

Για κάθε σελίδα με issues, πρότεινε:
1. Βελτιωμένο meta title (30-60 χαρακτήρες)
2. Βελτιωμένο meta description (120-160 χαρακτήρες)
3. Focus keyphrase αν λείπει
4. Πώς να ενσωματωθεί το keyphrase στο περιεχόμενο

Επίστρεψε ΜΟΝΟ JSON:
{
  "seo_improvements": [
    {
      "slug": "page-slug",
      "current_title": "...",
      "suggested_title": "...",
      "current_description": "...",
      "suggested_description": "...",
      "focus_keyphrase": "...",
      "content_suggestions": ["προσθήκη keyphrase στο H1", "..."]
    }
  ]
}
""".strip()

SCHEMA_IMPROVEMENT_PROMPT = """
Ανάλυσε τα υπάρχοντα Schema.org markups και πρότεινε βελτιώσεις για AI search optimization.

Θα σου δοθούν:
- Υπάρχοντα schemas ανά σελίδα
- AI readiness score
- Missing schemas

Πρότεινε:
1. Ποια schemas να προστεθούν (προτεραιότητα σε FAQPage, HowTo)
2. FAQ ερωτήσεις για κάθε σελίδα (3-5 ανά σελίδα)
3. HowTo βήματα όπου ταιριάζει
4. Βελτιώσεις σε υπάρχοντα schemas

Επίστρεψε ΜΟΝΟ JSON:
{
  "schema_proposals": [
    {
      "slug": "page-slug",
      "add_schemas": ["FAQPage", "HowTo"],
      "faq_suggestions": [
        {"question": "...", "answer_hint": "..."}
      ],
      "howto_steps": [
        {"name": "Βήμα 1", "description": "..."}
      ],
      "schema_fixes": ["προσθήκη author στο Article"]
    }
  ],
  "global_recommendations": ["..."]
}
""".strip()


def build_geo_enhanced_prompt(
    style_profile: dict | None = None,
    topology: dict | None = None,
    yoast_analysis: dict | None = None,
    schema_analysis: dict | None = None,
) -> str:
    """Build the full gap analysis prompt with GEO, Yoast, and Schema insights."""

    # Start with base prompt
    base_prompt = build_gap_analysis_prompt(style_profile, topology)

    # Add GEO guidelines
    geo_section = f"""

{GEO_CONTENT_GUIDELINES}
"""

    # Add Yoast insights if available
    yoast_section = ""
    if yoast_analysis:
        high_priority = yoast_analysis.get("issue_summary", {}).get("by_severity", {}).get("high", 0)
        total_issues = yoast_analysis.get("total_issues", 0)
        yoast_section = f"""

YOAST SEO ANALYSIS:
- Συνολικά issues: {total_issues}
- High priority: {high_priority}
- Pages χωρίς focus keyphrase: {yoast_analysis.get('issue_summary', {}).get('by_type', {}).get('missing_focus_keyphrase', 0)}
- Pages χωρίς meta description: {yoast_analysis.get('issue_summary', {}).get('by_type', {}).get('missing_meta_description', 0)}

ΣΗΜΑΝΤΙΚΟ: Για proposals τύπου update, συμπερίλαβε και SEO meta βελτιώσεις.
"""

    # Add Schema insights if available
    schema_section = ""
    if schema_analysis:
        ai_score = schema_analysis.get("ai_readiness_score", 0)
        schema_section = f"""

SCHEMA & AI READINESS:
- AI Readiness Score: {ai_score}%
- Pages με schema: {schema_analysis.get('pages_with_schema', 0)}/{schema_analysis.get('total_pages', 0)}
- FAQPage coverage: {"Χαμηλή" if ai_score < 50 else "Μέτρια" if ai_score < 75 else "Καλή"}

ΠΡΟΤΕΡΑΙΟΤΗΤΕΣ SCHEMA:
1. Πρόσθεσε FAQPage σε ΚΑΘΕ σελίδα υπηρεσίας (3-5 FAQs)
2. Πρόσθεσε HowTo σε οδηγούς και διαδικασίες
3. Βελτίωσε υπάρχοντα schemas με missing properties

Για κάθε proposal, συμπερίλαβε:
- suggested_schema: ["FAQPage", "HowTo", ...]
- faq_suggestions: ["{{"question": "...", "answer": "..."}}"] αν είναι relevant
"""

    # Add new proposal types
    new_types_section = """

ΕΠΙΠΛΕΟΝ ΤΥΠΟΙ ΠΡΟΤΑΣΕΩΝ:
- improve_seo_meta: βελτίωση Yoast meta (title, description, keyphrase)
- add_faq_section: προσθήκη FAQ section με schema
- add_howto_section: προσθήκη HowTo section με schema
- improve_schema: βελτίωση/προσθήκη structured data
- geo_optimize: βελτιστοποίηση για AI search (summaries, definitions, structure)

Για schema/FAQ proposals, συμπερίλαβε:
- faq_suggestions: λίστα με προτεινόμενα Q&A
- schema_additions: ποια schemas να προστεθούν
"""

    return base_prompt + geo_section + yoast_section + schema_section + new_types_section
