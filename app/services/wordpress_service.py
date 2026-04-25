import logging
import re
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings
from app.utils.text import strip_html

logger = logging.getLogger(__name__)


class WordPressService:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.WORDPRESS_BASE_URL).rstrip("/")
        self.timeout = settings.WORDPRESS_TIMEOUT
        self.per_page = min(max(settings.WORDPRESS_PER_PAGE, 1), 100)
        self.max_pages = max(settings.WORDPRESS_MAX_PAGES, 1)
        self.auth = HTTPBasicAuth(
            settings.WORDPRESS_USERNAME,
            settings.WORDPRESS_APP_PASSWORD,
        )

    def _get_response(self, endpoint: str, params: dict | None = None) -> requests.Response | None:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error("WordPress API error: %s", e)
            return None

    def _get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        response = self._get_response(endpoint, params)
        if response is None:
            return []

        try:
            data = response.json()
        except ValueError:
            logger.error("Invalid JSON from WordPress endpoint: %s", endpoint)
            return []

        return data if isinstance(data, list) else []

    def _fetch_collection(
        self,
        endpoint: str,
        post_type: str,
        per_page: int | None = None,
        max_pages: int | None = None,
    ) -> list[dict]:
        items: list[dict] = []
        page = 1
        per_page = min(max(per_page or self.per_page, 1), 100)
        max_pages = max(max_pages or self.max_pages, 1)

        while page <= max_pages:
            response = self._get_response(
                endpoint,
                params={"per_page": per_page, "page": page, "status": "publish"},
            )
            if response is None:
                break

            try:
                raw = response.json()
            except ValueError:
                logger.error("Invalid JSON from WordPress endpoint: %s page %d", endpoint, page)
                break
            if not isinstance(raw, list):
                logger.warning("Unexpected WordPress response for %s page %d", endpoint, page)
                break

            if not raw:
                break

            for item in raw:
                items.append(self._parse_wp_item(item, post_type))

            total_pages_header = response.headers.get("X-WP-TotalPages")
            total_pages = int(total_pages_header) if total_pages_header and total_pages_header.isdigit() else None
            if (total_pages and page >= total_pages) or len(raw) < per_page:
                break

            page += 1

        if page > max_pages:
            logger.warning(
                "Stopped fetching %s at configured WORDPRESS_MAX_PAGES=%d",
                endpoint,
                max_pages,
            )

        return items

    def fetch_pages(self, per_page: int | None = None, max_pages: int | None = None) -> list[dict]:
        all_pages = self._fetch_collection(
            "/wp-json/wp/v2/pages",
            "page",
            per_page=per_page,
            max_pages=max_pages,
        )
        logger.info("Fetched %d pages from WordPress", len(all_pages))
        return all_pages

    def fetch_posts(self, per_page: int | None = None, max_pages: int | None = None) -> list[dict]:
        all_posts = self._fetch_collection(
            "/wp-json/wp/v2/posts",
            "post",
            per_page=per_page,
            max_pages=max_pages,
        )
        logger.info("Fetched %d posts from WordPress", len(all_posts))
        return all_posts

    def fetch_all_content(self, site_url: str | None = None) -> list[dict]:
        """
        Fetch all pages and posts from WordPress.

        Args:
            site_url: Optional site URL to fetch from. If provided, creates
                      a temporary service instance for that site.
        """
        if site_url and site_url.rstrip("/") != self.base_url:
            # Create a temporary instance for the specified site
            temp_service = WordPressService(base_url=site_url)
            return temp_service.fetch_all_content()

        pages = self.fetch_pages()
        posts = self.fetch_posts()
        return pages + posts

    def fetch_categories(self) -> dict[int, str]:
        """Fetch all categories and return id->name mapping."""
        categories = {}
        page = 1

        while page <= self.max_pages:
            raw = self._get(
                "/wp-json/wp/v2/categories",
                params={"per_page": 100, "page": page},
            )
            if not raw:
                break

            for cat in raw:
                categories[cat.get("id")] = cat.get("name", "")

            if len(raw) < 100:
                break
            page += 1

        logger.info("Fetched %d categories from WordPress", len(categories))
        return categories

    def _parse_wp_item(self, item: dict, post_type: str) -> dict:
        content_html = item.get("content", {}).get("rendered", "")
        internal_links = self._extract_internal_links(content_html)

        # Extract Yoast SEO data
        yoast_data = self._extract_yoast_data(item)

        return {
            "wp_id": item.get("id"),
            "title": strip_html(item.get("title", {}).get("rendered", "")),
            "excerpt": strip_html(item.get("excerpt", {}).get("rendered", "")),
            "content": strip_html(content_html),
            "slug": item.get("slug", ""),
            "url": item.get("link", ""),
            "post_type": post_type,
            "categories": item.get("categories", []),
            "internal_links": internal_links,
            "is_front_page": item.get("slug") in ("home", "αρχικη", "αρχική")
                or item.get("link", "").rstrip("/") == self.base_url.rstrip("/"),
            # Yoast SEO data
            "yoast": yoast_data,
        }

    def _extract_yoast_data(self, item: dict) -> dict:
        """Extract Yoast SEO data from WordPress REST API response."""
        yoast_head = item.get("yoast_head_json", {})

        if not yoast_head:
            return {"available": False}

        # Extract schema graph
        schema_graph = []
        schema_data = yoast_head.get("schema", {})
        if schema_data:
            schema_graph = schema_data.get("@graph", [])

        return {
            "available": True,
            "title": yoast_head.get("title", ""),
            "description": yoast_head.get("description", ""),
            "og_title": yoast_head.get("og_title", ""),
            "og_description": yoast_head.get("og_description", ""),
            "focus_keyphrase": yoast_head.get("focuskw", ""),
            "canonical": yoast_head.get("canonical", ""),
            "robots": yoast_head.get("robots", {}),
            "schema_types": self._flatten_schema_types(schema_graph),
            "schema_graph": schema_graph,
            "twitter_card": yoast_head.get("twitter_card", ""),
            "article_modified_time": yoast_head.get("article_modified_time", ""),
        }

    def _flatten_schema_types(self, schema_graph: list[dict]) -> list[str]:
        """Extract and flatten schema types from schema graph."""
        types = []
        for item in schema_graph:
            schema_type = item.get("@type")
            if not schema_type:
                continue
            if isinstance(schema_type, list):
                types.extend(schema_type)
            else:
                types.append(schema_type)
        return types

    def _extract_internal_links(self, html_content: str) -> list[str]:
        """Extract internal links from HTML content."""
        if not html_content:
            return []

        base_domain = urlparse(self.base_url).netloc
        link_pattern = r'href=["\']([^"\']+)["\']'
        all_links = re.findall(link_pattern, html_content)

        internal_links = []
        for link in all_links:
            try:
                parsed = urlparse(link)
                # Internal if same domain or relative path
                if parsed.netloc == base_domain or (not parsed.netloc and parsed.path):
                    # Normalize the link
                    path = parsed.path.rstrip("/")
                    if path and path != "#" and not path.startswith("#"):
                        internal_links.append(path)
            except Exception:
                continue

        return list(set(internal_links))
