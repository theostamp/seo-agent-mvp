import logging
from collections import defaultdict

from app.prompts import TOPOLOGY_ANALYSIS_PROMPT
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class TopologyService:
    """Analyzes site content structure to identify pillars, satellites, and relationships."""

    def __init__(self) -> None:
        self.llm = LLMService()

    def analyze_topology(
        self,
        site_pages: list[dict],
        categories: dict[int, str] | None = None,
    ) -> dict:
        """
        Analyze site content topology.

        Returns:
            {
                "homepage": {...},
                "pillars": [...],
                "satellites": [...],
                "orphans": [...],
                "pillar_satellite_map": {"pillar_slug": ["satellite_slug", ...]},
                "coverage_gaps": [...],
            }
        """
        if not site_pages:
            return self._empty_topology()

        # Step 1: Identify homepage
        homepage = self._find_homepage(site_pages)

        # Step 2: Build link graph
        link_graph = self._build_link_graph(site_pages)

        # Step 3: Classify content using heuristics + LLM
        classification = self._classify_content(site_pages, link_graph, categories)

        # Step 4: Map pillars to satellites
        pillar_satellite_map = self._map_pillars_to_satellites(
            classification["pillars"],
            classification["satellites"],
            link_graph,
            site_pages,
        )

        topology = {
            "homepage": homepage,
            "pillars": classification["pillars"],
            "satellites": classification["satellites"],
            "orphans": classification["orphans"],
            "pillar_satellite_map": pillar_satellite_map,
            "link_graph": link_graph,
        }

        logger.info(
            "Topology analysis complete: pillars=%d, satellites=%d, orphans=%d",
            len(classification["pillars"]),
            len(classification["satellites"]),
            len(classification["orphans"]),
        )

        return topology

    def _find_homepage(self, site_pages: list[dict]) -> dict | None:
        """Find the homepage/front page."""
        for page in site_pages:
            if page.get("is_front_page"):
                return {
                    "wp_id": page["wp_id"],
                    "title": page["title"],
                    "slug": page["slug"],
                    "url": page["url"],
                }
        # Fallback: look for common homepage slugs
        for page in site_pages:
            if page.get("slug") in ("home", "αρχικη", "αρχική", ""):
                return {
                    "wp_id": page["wp_id"],
                    "title": page["title"],
                    "slug": page["slug"],
                    "url": page["url"],
                }
        return None

    def _build_link_graph(self, site_pages: list[dict]) -> dict:
        """
        Build bidirectional link graph.

        Returns:
            {
                "outgoing": {"slug": ["linked_slug", ...]},
                "incoming": {"slug": ["linking_slug", ...]},
            }
        """
        outgoing = defaultdict(list)
        incoming = defaultdict(list)

        # Create slug lookup
        slug_lookup = {p["slug"]: p for p in site_pages}
        url_to_slug = {}
        for p in site_pages:
            url_to_slug[p["url"].rstrip("/")] = p["slug"]
            # Also map by path
            from urllib.parse import urlparse
            path = urlparse(p["url"]).path.rstrip("/")
            if path:
                url_to_slug[path] = p["slug"]

        for page in site_pages:
            source_slug = page["slug"]
            for link in page.get("internal_links", []):
                # Try to resolve link to a slug
                target_slug = None
                link_clean = link.rstrip("/")

                if link_clean in url_to_slug:
                    target_slug = url_to_slug[link_clean]
                elif link_clean.lstrip("/") in slug_lookup:
                    target_slug = link_clean.lstrip("/")

                if target_slug and target_slug != source_slug:
                    outgoing[source_slug].append(target_slug)
                    incoming[target_slug].append(source_slug)

        return {
            "outgoing": dict(outgoing),
            "incoming": dict(incoming),
        }

    def _classify_content(
        self,
        site_pages: list[dict],
        link_graph: dict,
        categories: dict[int, str] | None,
    ) -> dict:
        """Classify pages as pillars, satellites, or orphans."""
        pillars = []
        satellites = []
        orphans = []

        incoming = link_graph.get("incoming", {})
        outgoing = link_graph.get("outgoing", {})

        for page in site_pages:
            slug = page["slug"]

            # Skip homepage
            if page.get("is_front_page"):
                continue

            # Heuristics for classification
            incoming_count = len(incoming.get(slug, []))
            outgoing_count = len(outgoing.get(slug, []))
            content_length = len(page.get("content", ""))
            is_page = page.get("post_type") == "page"

            # Pillar indicators:
            # - Is a page (not post)
            # - OR has many incoming links
            # - OR has substantial content
            # - OR is linked from homepage
            is_pillar = False

            if is_page and content_length > 1000:
                is_pillar = True
            elif incoming_count >= 3:
                is_pillar = True
            elif is_page and outgoing_count >= 2:
                is_pillar = True

            page_info = {
                "wp_id": page["wp_id"],
                "title": page["title"],
                "slug": slug,
                "url": page["url"],
                "post_type": page.get("post_type"),
                "content_length": content_length,
                "incoming_links": incoming_count,
                "outgoing_links": outgoing_count,
                "categories": [
                    categories.get(cat_id, f"cat_{cat_id}")
                    for cat_id in page.get("categories", [])
                ] if categories else page.get("categories", []),
            }

            if is_pillar:
                pillars.append(page_info)
            elif incoming_count > 0 or outgoing_count > 0:
                satellites.append(page_info)
            else:
                orphans.append(page_info)

        return {
            "pillars": pillars,
            "satellites": satellites,
            "orphans": orphans,
        }

    def _map_pillars_to_satellites(
        self,
        pillars: list[dict],
        satellites: list[dict],
        link_graph: dict,
        site_pages: list[dict],
    ) -> dict[str, list[str]]:
        """Map each pillar to its satellite posts."""
        pillar_slugs = {p["slug"] for p in pillars}
        satellite_slugs = {s["slug"] for s in satellites}

        incoming = link_graph.get("incoming", {})
        outgoing = link_graph.get("outgoing", {})

        pillar_map = {slug: [] for slug in pillar_slugs}

        for satellite in satellites:
            sat_slug = satellite["slug"]

            # Check which pillars link to this satellite
            linked_from = incoming.get(sat_slug, [])
            for linker in linked_from:
                if linker in pillar_slugs:
                    pillar_map[linker].append(sat_slug)
                    break
            else:
                # Check which pillars this satellite links to
                links_to = outgoing.get(sat_slug, [])
                for linked in links_to:
                    if linked in pillar_slugs:
                        pillar_map[linked].append(sat_slug)
                        break

        return pillar_map

    def _empty_topology(self) -> dict:
        return {
            "homepage": None,
            "pillars": [],
            "satellites": [],
            "orphans": [],
            "pillar_satellite_map": {},
            "link_graph": {"outgoing": {}, "incoming": {}},
        }

    def enrich_with_llm(self, topology: dict, site_pages: list[dict]) -> dict:
        """Use LLM to validate and enrich topology analysis."""
        if not topology.get("pillars"):
            return topology

        # Prepare compact data for LLM
        compact_data = {
            "pillars": [
                {"title": p["title"], "slug": p["slug"]}
                for p in topology["pillars"][:10]
            ],
            "satellites": [
                {"title": s["title"], "slug": s["slug"], "categories": s.get("categories", [])}
                for s in topology["satellites"][:20]
            ],
            "orphans": [
                {"title": o["title"], "slug": o["slug"]}
                for o in topology["orphans"][:10]
            ],
            "pillar_satellite_map": {
                k: v[:5] for k, v in list(topology["pillar_satellite_map"].items())[:5]
            },
        }

        result = self.llm.generate_json(TOPOLOGY_ANALYSIS_PROMPT, compact_data)

        if result and "suggested_mappings" in result:
            # Merge LLM suggestions
            for pillar_slug, satellites in result.get("suggested_mappings", {}).items():
                if pillar_slug in topology["pillar_satellite_map"]:
                    existing = set(topology["pillar_satellite_map"][pillar_slug])
                    existing.update(satellites)
                    topology["pillar_satellite_map"][pillar_slug] = list(existing)

            topology["llm_insights"] = result.get("insights", [])
            topology["coverage_gaps"] = result.get("coverage_gaps", [])

        return topology
