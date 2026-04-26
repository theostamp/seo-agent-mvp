import re
from urllib.parse import urlparse

from app.prompts import HOMEPAGE_GENERATION_PROMPT


WORD_RE = re.compile(r"[\wά-ώΆ-Ώ]+", re.UNICODE)


class HomepageService:
    """Deterministic homepage checks for content volume, style, and linking."""

    MIN_WORDS = 120
    IDEAL_MAX_WORDS = 700
    HARD_MAX_WORDS = 1000
    MIN_INTERNAL_LINKS = 4
    MIN_PILLAR_LINKS = 3

    CTA_TERMS = (
        "επικοινων",
        "καλέστε",
        "ζητήστε",
        "ραντεβού",
        "προσφορά",
        "τηλέφων",
        "φόρμα",
    )

    def analyze(
        self,
        site_pages: list[dict],
        topology: dict | None = None,
        style_profile: dict | None = None,
    ) -> dict:
        homepage = self._find_homepage(site_pages, topology)
        if not homepage:
            return {
                "found": False,
                "score": 0,
                "issues": [
                    {
                        "severity": "high",
                        "type": "missing_homepage",
                        "message": "Δεν εντοπίστηκε αρχική σελίδα στο WordPress content.",
                    }
                ],
                "recommendations": ["Ορίστε/επιστρέψτε καθαρά την αρχική σελίδα από το WordPress REST API."],
            }

        content = homepage.get("content", "")
        words = self._words(content)
        internal_links = homepage.get("internal_links", [])
        linked_pillars = self._linked_pillars(homepage, topology or {})
        has_cta = self._has_cta(content)
        detected_addressing = self._detect_addressing(content)
        style_findings = self._style_findings(content, style_profile)

        issues = []
        recommendations = []

        if len(words) < self.MIN_WORDS:
            issues.append({
                "severity": "medium",
                "type": "homepage_too_short",
                "message": f"Η αρχική έχει μόνο {len(words)} λέξεις. Θέλει σύντομο αλλά επαρκές messaging.",
            })
            recommendations.append("Προσθέστε σύντομο hero value proposition, βασικές υπηρεσίες και trust signals.")
        elif len(words) > self.HARD_MAX_WORDS:
            issues.append({
                "severity": "high",
                "type": "homepage_too_long",
                "message": f"Η αρχική έχει {len(words)} λέξεις. Είναι υπερβολικά μεγάλη για homepage.",
            })
            recommendations.append("Μεταφέρετε αναλυτικό περιεχόμενο σε pillar/satellite pages και κρατήστε homepage 250-700 λέξεις.")
        elif len(words) > self.IDEAL_MAX_WORDS:
            issues.append({
                "severity": "medium",
                "type": "homepage_bulk_content",
                "message": f"Η αρχική έχει {len(words)} λέξεις. Καλύτερα να μείνει πιο συμπυκνωμένη.",
            })
            recommendations.append("Συμπτύξτε μεγάλα κείμενα σε περιλήψεις με links προς αναλυτικές υπηρεσίες.")

        if len(internal_links) < self.MIN_INTERNAL_LINKS:
            issues.append({
                "severity": "high",
                "type": "few_homepage_internal_links",
                "message": f"Η αρχική έχει {len(internal_links)} internal links. Χρειάζεται περισσότερη καθοδήγηση προς υπηρεσίες.",
            })
            recommendations.append("Προσθέστε 4-8 internal links από την αρχική προς βασικές υπηρεσίες/pillars.")

        target_pillar_links = min(self.MIN_PILLAR_LINKS, len((topology or {}).get("pillars", [])))
        if target_pillar_links and len(linked_pillars) < target_pillar_links:
            issues.append({
                "severity": "medium",
                "type": "few_pillar_links",
                "message": f"Η αρχική συνδέει {len(linked_pillars)}/{target_pillar_links} βασικά pillars.",
            })
            recommendations.append("Κάθε βασική ενότητα υπηρεσίας στην αρχική να οδηγεί σε αντίστοιχη pillar page.")

        if not has_cta:
            issues.append({
                "severity": "medium",
                "type": "missing_cta",
                "message": "Δεν εντοπίστηκε σαφές call-to-action στην αρχική.",
            })
            recommendations.append("Προσθέστε σαφές CTA κοντά στο hero και στο τέλος της αρχικής.")

        if detected_addressing == "mixed":
            issues.append({
                "severity": "low",
                "type": "mixed_addressing",
                "message": "Η αρχική φαίνεται να μπερδεύει ενικό και πληθυντικό ύφος.",
            })
            recommendations.append("Κρατήστε ενιαία προσφώνηση σε όλη την αρχική.")

        issues.extend(style_findings)
        if style_findings:
            recommendations.append("Εναρμονίστε το ύφος της αρχικής με το γενικό style profile του site.")

        if not recommendations:
            recommendations.append("Η αρχική είναι σε καλή βάση. Κρατήστε τη σύντομη και χρησιμοποιήστε τη ως κόμβο προς pillars.")

        return {
            "found": True,
            "score": self._score(issues),
            "homepage": {
                "title": homepage.get("title"),
                "slug": homepage.get("slug"),
                "url": homepage.get("url"),
            },
            "metrics": {
                "word_count": len(words),
                "content_length": len(content),
                "internal_links_count": len(internal_links),
                "linked_pillars_count": len(linked_pillars),
                "has_cta": has_cta,
                "detected_addressing": detected_addressing,
            },
            "linked_pillars": linked_pillars,
            "issues": issues,
            "recommendations": recommendations,
        }

    def build_guidance(
        self,
        site_pages: list[dict],
        topology: dict | None = None,
        style_profile: dict | None = None,
    ) -> dict:
        analysis = self.analyze(site_pages, topology, style_profile)
        pillars = (topology or {}).get("pillars", [])
        satellites = (topology or {}).get("satellites", [])
        orphans = (topology or {}).get("orphans", [])

        main_pillars = [
            {
                "title": pillar.get("title"),
                "slug": pillar.get("slug"),
                "url": pillar.get("url"),
            }
            for pillar in pillars[:8]
        ]

        return {
            "homepage_analysis": analysis,
            "architecture": self._architecture_guidance(analysis, main_pillars),
            "semantic": self._semantic_guidance(analysis, style_profile),
            "internal_link_plan": self._internal_link_plan(analysis, main_pillars),
            "content_allocation": self._content_allocation(analysis, main_pillars, satellites, orphans),
            "action_plan": self._action_plan(analysis, main_pillars),
        }

    def generate_ai_homepage_plan(
        self,
        site_pages: list[dict],
        topology: dict | None = None,
        style_profile: dict | None = None,
        custom_instructions: str | None = None,
        llm_service=None,
    ) -> dict:
        """
        Generate an AI-assisted homepage structure and copy plan.

        The deterministic guidance remains the source context and fallback. The LLM
        is only invoked here so regular audits stay fast and testable.
        """
        guidance = self.build_guidance(site_pages, topology, style_profile)
        payload = self._homepage_generation_payload(
            site_pages=site_pages,
            topology=topology,
            style_profile=style_profile,
            guidance=guidance,
            custom_instructions=custom_instructions,
        )

        if llm_service is None:
            from app.services.llm_service import LLMService
            llm_service = LLMService()

        ai_result = llm_service.generate_json(HOMEPAGE_GENERATION_PROMPT, payload)
        normalized = self._normalize_ai_homepage_plan(ai_result)
        if normalized:
            normalized["source"] = "ai"
            normalized["deterministic_guidance"] = guidance
            return normalized

        fallback = self._fallback_ai_homepage_plan(guidance)
        fallback["source"] = "fallback"
        fallback["deterministic_guidance"] = guidance
        return fallback

    def _homepage_generation_payload(
        self,
        site_pages: list[dict],
        topology: dict | None,
        style_profile: dict | None,
        guidance: dict,
        custom_instructions: str | None,
    ) -> dict:
        homepage = self._find_homepage(site_pages, topology)
        pillars = (topology or {}).get("pillars", [])
        satellites = (topology or {}).get("satellites", [])
        orphans = (topology or {}).get("orphans", [])

        return {
            "custom_instructions": (custom_instructions or "").strip(),
            "homepage_analysis": guidance.get("homepage_analysis", {}),
            "deterministic_guidance": {
                "architecture": guidance.get("architecture", {}),
                "semantic": guidance.get("semantic", {}),
                "internal_link_plan": guidance.get("internal_link_plan", {}),
                "content_allocation": guidance.get("content_allocation", {}),
                "action_plan": guidance.get("action_plan", {}),
            },
            "current_homepage": self._page_summary(homepage, include_excerpt=True) if homepage else None,
            "main_pillars": [self._page_summary(page) for page in pillars[:10]],
            "supporting_content_sample": [self._page_summary(page) for page in satellites[:10]],
            "orphan_content_sample": [self._page_summary(page) for page in orphans[:8]],
            "style_profile": style_profile or {},
        }

    def _normalize_ai_homepage_plan(self, result: dict | None) -> dict | None:
        if not isinstance(result, dict) or not result:
            return None

        required = (
            "homepage_strategy",
            "section_plan",
            "draft_copy",
            "internal_link_plan",
            "visual_guidance",
            "yoast_meta",
            "implementation_checklist",
        )
        if not any(key in result for key in required):
            return None

        draft_copy = result.get("draft_copy") if isinstance(result.get("draft_copy"), dict) else {}
        yoast_meta = result.get("yoast_meta") if isinstance(result.get("yoast_meta"), dict) else {}

        return {
            "homepage_strategy": result.get("homepage_strategy") if isinstance(result.get("homepage_strategy"), dict) else {},
            "section_plan": result.get("section_plan") if isinstance(result.get("section_plan"), list) else [],
            "draft_copy": {
                "hero_h1": draft_copy.get("hero_h1", ""),
                "hero_subtitle": draft_copy.get("hero_subtitle", ""),
                "primary_cta": draft_copy.get("primary_cta", ""),
                "service_blocks": draft_copy.get("service_blocks") if isinstance(draft_copy.get("service_blocks"), list) else [],
                "trust_section": draft_copy.get("trust_section", ""),
                "final_cta": draft_copy.get("final_cta", ""),
            },
            "internal_link_plan": result.get("internal_link_plan") if isinstance(result.get("internal_link_plan"), list) else [],
            "visual_guidance": result.get("visual_guidance") if isinstance(result.get("visual_guidance"), list) else [],
            "yoast_meta": {
                "meta_title": yoast_meta.get("meta_title", ""),
                "meta_description": yoast_meta.get("meta_description", ""),
                "focus_keyphrase": yoast_meta.get("focus_keyphrase", ""),
            },
            "implementation_checklist": (
                result.get("implementation_checklist")
                if isinstance(result.get("implementation_checklist"), list)
                else []
            ),
        }

    def _fallback_ai_homepage_plan(self, guidance: dict) -> dict:
        architecture = guidance.get("architecture", {})
        semantic = guidance.get("semantic", {})
        link_plan = guidance.get("internal_link_plan", {})
        pillars = architecture.get("pillar_targets", [])
        priority_links = link_plan.get("missing_priority_links", []) or pillars[:6]

        section_plan = []
        for section in architecture.get("recommended_sections", []):
            links = []
            if section.get("name") == "Βασικές υπηρεσίες":
                links = [
                    {
                        "label": pillar.get("title"),
                        "url": pillar.get("url"),
                    }
                    for pillar in priority_links[:6]
                ]
            section_plan.append({
                "order": section.get("order"),
                "section": section.get("name"),
                "heading": section.get("name"),
                "goal": section.get("purpose"),
                "content_notes": section.get("content_instruction"),
                "links": links,
                "visual_notes": self._visual_note_for_section(section.get("name")),
            })

        return {
            "homepage_strategy": {
                "primary_goal": "Να εξηγεί άμεσα την πρόταση αξίας και να οδηγεί τον χρήστη στις βασικές υπηρεσίες.",
                "positioning": "Επαγγελματική, αξιόπιστη τεχνική λύση με καθαρή διαδρομή επικοινωνίας.",
                "target_audience": "Επισκέπτες που αναζητούν τεχνική υπηρεσία και θέλουν γρήγορα να επιβεβαιώσουν αξιοπιστία.",
                "content_role": architecture.get("role", ""),
            },
            "section_plan": section_plan,
            "draft_copy": {
                "hero_h1": "Τεχνικές υπηρεσίες με άμεση ανταπόκριση και αξιόπιστη υποστήριξη",
                "hero_subtitle": semantic.get("core_message", ""),
                "primary_cta": "Ζητήστε προσφορά",
                "service_blocks": [
                    {
                        "title": pillar.get("title"),
                        "text": "Σύντομη παρουσίαση της υπηρεσίας με έμφαση στο πρόβλημα που λύνει και στο αποτέλεσμα για τον πελάτη.",
                        "link_url": pillar.get("url"),
                        "anchor_text": pillar.get("title"),
                    }
                    for pillar in priority_links[:6]
                ],
                "trust_section": "Προσθέστε 3-5 σύντομα σημεία εμπιστοσύνης: εμπειρία, τεχνική επάρκεια, συνέπεια, εξυπηρέτηση και σαφή επικοινωνία.",
                "final_cta": "Επικοινωνήστε μαζί μας για να αξιολογήσουμε τις ανάγκες σας και να προτείνουμε την κατάλληλη λύση.",
            },
            "internal_link_plan": [
                {
                    "target_title": pillar.get("title"),
                    "target_url": pillar.get("url"),
                    "anchor_text": pillar.get("title"),
                    "placement": "Ενότητα βασικών υπηρεσιών",
                    "reason": "Συνδέει την αρχική με βασικό pillar και ενισχύει την αρχιτεκτονική του site.",
                }
                for pillar in priority_links[:8]
            ],
            "visual_guidance": [
                {
                    "area": "Hero",
                    "recommendation": "Καθαρός τίτλος, σύντομο supporting text, ένα εμφανές CTA και δευτερεύον link προς τις υπηρεσίες.",
                    "reason": "Ο επισκέπτης πρέπει να καταλάβει την πρόταση αξίας χωρίς κύλιση.",
                },
                {
                    "area": "Βασικές υπηρεσίες",
                    "recommendation": "Χρησιμοποιήστε συμπαγές grid 4-8 υπηρεσιών με σύντομα κείμενα και ίδια οπτική βαρύτητα.",
                    "reason": "Η αρχική πρέπει να λειτουργεί ως κόμβος επιλογής υπηρεσίας.",
                },
            ],
            "yoast_meta": {
                "meta_title": "Τεχνικές Υπηρεσίες | Άμεση Υποστήριξη",
                "meta_description": "Δείτε βασικές τεχνικές υπηρεσίες, λύσεις και τρόπους επικοινωνίας για άμεση υποστήριξη από εξειδικευμένη ομάδα.",
                "focus_keyphrase": "τεχνικές υπηρεσίες",
            },
            "implementation_checklist": [
                "Κρατήστε ένα μόνο H1 στο hero.",
                "Περιορίστε το συνολικό κείμενο της αρχικής στις 250-700 λέξεις.",
                "Προσθέστε 4-8 links προς βασικές υπηρεσίες με περιγραφικά anchors.",
                "Βάλτε CTA στο hero και στο τέλος της σελίδας.",
                "Μεταφέρετε αναλυτικές τεχνικές εξηγήσεις σε pillars ή satellites.",
            ],
        }

    def _page_summary(self, page: dict | None, include_excerpt: bool = False) -> dict:
        if not page:
            return {}

        summary = {
            "title": page.get("title"),
            "slug": page.get("slug"),
            "url": page.get("url"),
            "post_type": page.get("post_type"),
            "word_count": len(self._words(page.get("content", ""))),
            "internal_links": page.get("internal_links", [])[:10],
        }
        if include_excerpt:
            content = page.get("content", "")
            summary["content_excerpt"] = content[:1200]
        return summary

    def _visual_note_for_section(self, section_name: str | None) -> str:
        notes = {
            "Hero": "Πάνω από το fold, με καθαρό H1, σύντομο κείμενο, κύριο CTA και ήρεμο οπτικό στοιχείο σχετικό με την υπηρεσία.",
            "Βασικές υπηρεσίες": "Grid ή λίστα υπηρεσιών με σταθερή δομή, σύντομες περιγραφές και εμφανή links προς pillars.",
            "Γιατί να μας επιλέξετε": "3-5 σύντομα σημεία εμπιστοσύνης με εικονίδια ή μικρούς αριθμούς, χωρίς μεγάλα paragraphs.",
            "Περιοχές ή εξυπηρέτηση": "Σύντομη οριζόντια ενότητα με local relevance και link όπου υπάρχει σχετική σελίδα.",
            "Τελικό CTA": "Απλή full-width ενότητα με μία πρόταση και ξεκάθαρο κουμπί/τηλέφωνο.",
        }
        return notes.get(section_name, "Κρατήστε σύντομη ενότητα με καθαρή ιεραρχία και μία συγκεκριμένη ενέργεια.")

    def _architecture_guidance(self, analysis: dict, pillars: list[dict]) -> dict:
        return {
            "role": "Η αρχική πρέπει να λειτουργεί ως κόμβος προσανατολισμού και εμπιστοσύνης, όχι ως αναλυτικό άρθρο.",
            "target_length": "250-700 λέξεις συνολικά, με σύντομες ενότητες και καθαρή διαδρομή προς τις υπηρεσίες.",
            "recommended_sections": [
                {
                    "order": 1,
                    "name": "Hero",
                    "purpose": "Να εξηγεί σε 1-2 προτάσεις ποιο πρόβλημα λύνει η επιχείρηση και σε ποια περιοχή.",
                    "content_instruction": "Κρατήστε έναν καθαρό τίτλο, σύντομο supporting text και ένα κύριο CTA.",
                },
                {
                    "order": 2,
                    "name": "Βασικές υπηρεσίες",
                    "purpose": "Να οδηγεί τον χρήστη στις σημαντικές pillar pages.",
                    "content_instruction": "Χρησιμοποιήστε 4-8 σύντομες κάρτες/γραμμές υπηρεσιών, καθεμία με link προς pillar.",
                },
                {
                    "order": 3,
                    "name": "Γιατί να μας επιλέξετε",
                    "purpose": "Να καλύπτει εμπιστοσύνη, εμπειρία, αμεσότητα και τεχνική επάρκεια.",
                    "content_instruction": "3-5 bullets, όχι μεγάλα paragraphs.",
                },
                {
                    "order": 4,
                    "name": "Περιοχές ή εξυπηρέτηση",
                    "purpose": "Να δίνει local relevance χωρίς keyword stuffing.",
                    "content_instruction": "Σύντομη αναφορά στις βασικές περιοχές και link προς σχετική σελίδα αν υπάρχει.",
                },
                {
                    "order": 5,
                    "name": "Τελικό CTA",
                    "purpose": "Να κλείνει με ξεκάθαρη επόμενη ενέργεια.",
                    "content_instruction": "Μία πρόταση και ένα κουμπί/τηλέφωνο/φόρμα.",
                },
            ],
            "pillar_targets": pillars,
        }

    def _semantic_guidance(self, analysis: dict, style_profile: dict | None) -> dict:
        metrics = analysis.get("metrics", {})
        addressing = (style_profile or {}).get("addressing") or metrics.get("detected_addressing", "εσείς")
        return {
            "core_message": "Η αρχική πρέπει να λέει άμεσα τι κάνετε, για ποιον, πού, και γιατί είστε αξιόπιστη επιλογή.",
            "tone": {
                "addressing": addressing,
                "instruction": "Κρατήστε ενιαία προσφώνηση σε όλο το homepage και αποφύγετε εναλλαγές ενικού/πληθυντικού.",
            },
            "meaning_rules": [
                "Κάθε ενότητα να απαντά σε μία ερώτηση του επισκέπτη.",
                "Μην αναλύετε τεχνικές λεπτομέρειες στην αρχική. Δώστε περίληψη και link προς την αντίστοιχη υπηρεσία.",
                "Χρησιμοποιήστε συγκεκριμένες λέξεις για υπηρεσίες και αποτελέσματα, όχι γενικόλογες διατυπώσεις.",
                "Βάλτε CTA μετά το hero και στο τέλος, όχι μόνο στο footer.",
            ],
            "avoid": [
                "Μεγάλα blocks κειμένου",
                "Πολλά ασύνδετα keywords",
                "FAQ/HowTo bulk περιεχόμενο στην αρχική",
                "Links χωρίς περιγραφικό anchor text",
            ],
        }

    def _internal_link_plan(self, analysis: dict, pillars: list[dict]) -> dict:
        linked_slugs = {pillar.get("slug") for pillar in analysis.get("linked_pillars", [])}
        missing = [pillar for pillar in pillars if pillar.get("slug") not in linked_slugs]

        return {
            "target": "4-8 internal links από την αρχική, κυρίως προς βασικές υπηρεσίες/pillars.",
            "already_linked": analysis.get("linked_pillars", []),
            "missing_priority_links": missing[:8],
            "anchor_text_rule": "Το anchor text να περιγράφει την υπηρεσία, π.χ. 'συντήρηση λέβητα φυσικού αερίου', όχι 'δείτε εδώ'.",
        }

    def _content_allocation(
        self,
        analysis: dict,
        pillars: list[dict],
        satellites: list[dict],
        orphans: list[dict],
    ) -> dict:
        metrics = analysis.get("metrics", {})
        move_details = metrics.get("word_count", 0) > self.IDEAL_MAX_WORDS

        return {
            "keep_on_homepage": [
                "Σύντομο value proposition",
                "Λίστα βασικών υπηρεσιών με links",
                "Trust signals και σύντομη απόδειξη εμπειρίας",
                "CTA για επικοινωνία",
            ],
            "move_to_pillar_pages": [
                pillar.get("title")
                for pillar in pillars[:8]
            ] if move_details else [],
            "support_with_satellites": [
                satellite.get("title")
                for satellite in satellites[:5]
            ],
            "review_orphans_for_linking": [
                orphan.get("title")
                for orphan in orphans[:5]
            ],
        }

    def _action_plan(self, analysis: dict, pillars: list[dict]) -> list[dict]:
        issues = {issue.get("type") for issue in analysis.get("issues", [])}
        actions = []

        if "homepage_too_long" in issues or "homepage_bulk_content" in issues:
            actions.append({
                "priority": "high",
                "area": "Μήκος περιεχομένου",
                "instruction": "Κόψτε αναλυτικές παραγράφους και μεταφέρετέ τις στις αντίστοιχες pillar pages.",
                "reason": "Η αρχική πρέπει να καθοδηγεί, όχι να αντικαθιστά τις σελίδες υπηρεσιών.",
            })

        if "homepage_too_short" in issues:
            actions.append({
                "priority": "medium",
                "area": "Περιεχόμενο",
                "instruction": "Προσθέστε hero, υπηρεσίες, trust signals και CTA χωρίς να ξεπεράσετε τις 700 λέξεις.",
                "reason": "Η αρχική χρειάζεται αρκετό context για χρήστη και SEO.",
            })

        if "few_homepage_internal_links" in issues or "few_pillar_links" in issues:
            actions.append({
                "priority": "high",
                "area": "Αρχιτεκτονική συνδέσμων",
                "instruction": "Προσθέστε links από την αρχική προς τις βασικές υπηρεσίες.",
                "reason": "Τα homepage links καθορίζουν την ιεραρχία και βοηθούν χρήστες και crawlers.",
            })

        if "missing_cta" in issues:
            actions.append({
                "priority": "medium",
                "area": "Conversion",
                "instruction": "Προσθέστε σαφές CTA στο hero και στο τέλος της σελίδας.",
                "reason": "Ο χρήστης πρέπει να ξέρει ποια είναι η επόμενη ενέργεια.",
            })

        if not actions:
            actions.append({
                "priority": "low",
                "area": "Συντήρηση",
                "instruction": "Κρατήστε την αρχική σύντομη και ενημερώστε τα links όταν αλλάζει η δομή υπηρεσιών.",
                "reason": "Η αρχική πρέπει να παραμένει καθαρός κόμβος πλοήγησης.",
            })

        return actions

    def _find_homepage(self, site_pages: list[dict], topology: dict | None) -> dict | None:
        homepage_slug = (topology or {}).get("homepage", {}).get("slug")
        if homepage_slug is not None:
            for page in site_pages:
                if page.get("slug") == homepage_slug:
                    return page

        for page in site_pages:
            if page.get("is_front_page"):
                return page

        for page in site_pages:
            if page.get("slug") in ("", "home", "αρχικη", "αρχική"):
                return page

        return None

    def _linked_pillars(self, homepage: dict, topology: dict) -> list[dict]:
        links = set(homepage.get("internal_links", []))
        linked = []

        for pillar in topology.get("pillars", []):
            slug = pillar.get("slug", "")
            url_path = urlparse(pillar.get("url", "")).path.rstrip("/")
            if any(
                candidate and (
                    candidate in links
                    or f"/{candidate}" in links
                    or any(candidate in link for link in links)
                )
                for candidate in (slug, url_path)
            ):
                linked.append({
                    "title": pillar.get("title"),
                    "slug": slug,
                    "url": pillar.get("url"),
                })

        return linked

    def _has_cta(self, content: str) -> bool:
        text = content.lower()
        return any(term in text for term in self.CTA_TERMS)

    def _detect_addressing(self, content: str) -> str:
        text = f" {content.lower()} "
        singular_hits = sum(text.count(term) for term in (" εσύ ", " σου ", " σε βοηθάμε "))
        plural_hits = sum(text.count(term) for term in (" εσείς ", " σας ", " επικοινωνήστε "))

        if singular_hits and plural_hits:
            return "mixed"
        if plural_hits:
            return "εσείς"
        if singular_hits:
            return "εσύ"
        return "unknown"

    def _style_findings(self, content: str, style_profile: dict | None) -> list[dict]:
        if not style_profile:
            return []

        findings = []
        addressing = style_profile.get("addressing")
        text = content.lower()

        if addressing == "εσείς" and any(term in text for term in (" εσύ ", " σου ", " σε βοηθάμε ")):
            findings.append({
                "severity": "low",
                "type": "addressing_mismatch",
                "message": "Το site προτιμά πληθυντικό, αλλά η αρχική φαίνεται να έχει σημεία σε ενικό.",
            })

        if addressing == "εσύ" and any(term in text for term in (" σας ", " εσάς ", " επικοινωνήστε ")):
            findings.append({
                "severity": "low",
                "type": "addressing_mismatch",
                "message": "Το site προτιμά ενικό, αλλά η αρχική φαίνεται να έχει σημεία σε πληθυντικό.",
            })

        return findings

    def _score(self, issues: list[dict]) -> int:
        penalty = 0
        for issue in issues:
            severity = issue.get("severity")
            if severity == "high":
                penalty += 25
            elif severity == "medium":
                penalty += 15
            else:
                penalty += 7
        return max(0, 100 - penalty)

    def _words(self, content: str) -> list[str]:
        return [word for word in WORD_RE.findall(content) if len(word) > 1]
