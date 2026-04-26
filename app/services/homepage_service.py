import re
from urllib.parse import urlparse


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
