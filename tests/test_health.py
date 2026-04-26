from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ContentProposal, WorkflowRun
from app.services.analysis_service import AnalysisService
from app.services.deduplication_service import DeduplicationService
from app.services.homepage_service import HomepageService
from app.services.wordpress_service import WordPressService


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "seo-agent-mvp"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_proposal(db_session) -> ContentProposal:
    workflow_run = WorkflowRun(category_name="Test category", status="needs_review")
    db_session.add(workflow_run)
    db_session.commit()
    db_session.refresh(workflow_run)

    proposal = ContentProposal(
        workflow_run_id=workflow_run.id,
        proposal_type="create_new_page",
        target_title="Test proposal",
        summary="Test summary",
        outline="Test outline",
        suggested_schema="Article",
        status="needs_review",
    )
    db_session.add(proposal)
    db_session.commit()
    db_session.refresh(proposal)
    return proposal


def test_proposal_status_can_be_updated(db_session):
    proposal = create_proposal(db_session)

    response = client.patch(
        f"/proposals/{proposal.id}/status",
        json={"status": "approved"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == proposal.id
    assert data["status"] == "approved"


def test_proposal_status_filter_rejects_invalid_status(db_session):
    response = client.get("/proposals", params={"status": "published"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid proposal status"


def test_wordpress_fetch_pages_uses_total_pages_header(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, page: int) -> None:
            self.page = page
            self.headers = {"X-WP-TotalPages": "3"}

        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "id": self.page,
                    "title": {"rendered": f"Page {self.page}"},
                    "content": {"rendered": ""},
                    "excerpt": {"rendered": ""},
                    "slug": f"page-{self.page}",
                    "link": f"https://example.test/page-{self.page}",
                }
            ]

    def fake_get(url, params, auth, timeout):
        calls.append(params["page"])
        return FakeResponse(params["page"])

    monkeypatch.setattr("app.services.wordpress_service.requests.get", fake_get)

    service = WordPressService(base_url="https://example.test")
    pages = service.fetch_pages(per_page=1, max_pages=10)

    assert calls == [1, 2, 3]
    assert [page["slug"] for page in pages] == ["page-1", "page-2", "page-3"]


def test_site_audit_returns_deterministic_summary(monkeypatch):
    pages = [
        {
            "title": "Home",
            "slug": "home",
            "url": "https://example.test",
            "post_type": "page",
            "content": "Επικοινωνήστε μαζί μας για υπηρεσίες θέρμανσης.",
            "internal_links": ["/services"],
            "yoast": {"available": True, "schema_types": ["WebSite"]},
        },
        {
            "title": "Guide",
            "slug": "guide",
            "url": "https://example.test/guide",
            "post_type": "post",
            "yoast": {"available": False, "schema_types": []},
        },
    ]

    class FakeWordPressService:
        def __init__(self, base_url=None) -> None:
            self.base_url = base_url or "https://example.test"

        def fetch_all_content(self):
            return pages

        def fetch_categories(self):
            return {}

    class FakeTopologyService:
        def analyze_topology(self, site_pages, categories):
            return {
                "homepage": {"title": "Home", "slug": "home"},
                "pillars": [site_pages[0]],
                "satellites": [],
                "orphans": [site_pages[1]],
            }

    class FakeYoastService:
        def analyze_seo_data(self, site_pages):
            return {
                "pages_with_yoast": 1,
                "pages_without_yoast": 1,
                "total_issues": 2,
                "issue_summary": {"by_type": {"missing_meta_description": 1}},
                "pages_analysis": [
                    {
                        "slug": "guide",
                        "title": "Guide",
                        "issues_count": 2,
                        "issues": [{"severity": "high"}],
                    }
                ],
            }

        def get_optimization_priorities(self, analysis):
            return [{"slug": "guide", "issues_count": 2}]

    class FakeSchemaAnalyzer:
        def analyze_schemas(self, site_pages):
            return {
                "pages_with_schema": 1,
                "schema_coverage_percent": 50.0,
                "ai_readiness_score": 25.0,
                "schema_types_found": {"WebSite": 1},
                "improvement_suggestions": [{"type": "add_schema", "schema": "FAQPage"}],
            }

    monkeypatch.setattr("app.api.routes.WordPressService", FakeWordPressService)
    monkeypatch.setattr("app.api.routes.TopologyService", FakeTopologyService)
    monkeypatch.setattr("app.api.routes.YoastService", FakeYoastService)
    monkeypatch.setattr("app.api.routes.SchemaAnalyzer", FakeSchemaAnalyzer)

    response = client.get("/site/audit", params={"site_url": "https://example.test"})

    assert response.status_code == 200
    data = response.json()
    assert data["site_pages_found"] == 2
    assert data["post_type_counts"] == {"page": 1, "post": 1}
    assert data["topology"]["orphans_count"] == 1
    assert data["homepage"]["found"] is True
    assert data["yoast"]["total_issues"] == 2
    assert data["schema"]["ai_readiness_score"] == 25.0


def test_gap_analysis_returns_fallback_proposals_when_llm_is_empty():
    class EmptyLLM:
        def generate_json(self, prompt, payload):
            return {}

    service = AnalysisService.__new__(AnalysisService)
    service.llm_service = EmptyLLM()
    service.deduplication_service = DeduplicationService()

    result = service.gap_analysis(
        category_name="Επισκευή μπαλκονιών",
        clusters=[
            {
                "name": "Στεγάνωση μπαλκονιού",
                "keywords": ["στεγάνωση μπαλκονιού"],
            }
        ],
        site_pages=[],
        yoast_analysis={
            "pages_analysis": [
                {
                    "title": "Παλιά σελίδα",
                    "slug": "palia-selida",
                    "issues_count": 1,
                    "issues": [{"type": "missing_meta_description"}],
                    "schema_types": [],
                }
            ]
        },
        schema_analysis={
            "improvement_suggestions": [
                {
                    "schema": "FAQPage",
                    "priority": "high",
                    "reason": "Χρειάζεται FAQ section",
                }
            ]
        },
    )

    proposals = result["proposals"]
    assert len(proposals) == 2
    assert proposals[0]["proposal_type"] == "improve_seo_meta"
    assert proposals[1]["proposal_type"] == "add_faq_section"


def test_gap_analysis_marks_high_duplicate_create_proposals():
    class DuplicateLLM:
        def generate_json(self, prompt, payload):
            return {
                "proposals": [
                    {
                        "proposal_type": "create_satellite_post",
                        "target_title": "Στεγάνωση μπαλκονιού",
                        "summary": "Νέο άρθρο για στεγάνωση μπαλκονιού",
                        "outline": ["Στεγάνωση μπαλκονιού", "Κόστος"],
                        "suggested_schema": ["Article"],
                        "priority": "high",
                    }
                ]
            }

    service = AnalysisService.__new__(AnalysisService)
    service.llm_service = DuplicateLLM()
    service.deduplication_service = DeduplicationService()

    result = service.gap_analysis(
        category_name="Στεγάνωση",
        clusters=[],
        site_pages=[
            {
                "title": "Στεγάνωση μπαλκονιού",
                "slug": "steganosi-mpalkoniou",
                "url": "https://example.test/steganosi-mpalkoniou",
                "post_type": "post",
                "excerpt": "Στεγάνωση μπαλκονιού και κόστος εργασιών.",
                "content": "Στεγάνωση μπαλκονιού με αναλυτική διαδικασία και τιμές.",
                "yoast": {},
            }
        ],
    )

    proposal = result["proposals"][0]
    assert proposal["duplicate_check"]["risk"] == "high"
    assert proposal["priority"] == "low"
    assert "Πιθανό duplicate" in proposal["summary"]


def test_wordpress_fetch_all_content_uses_cache(monkeypatch):
    WordPressService.clear_cache()
    calls = {"pages": 0, "posts": 0}

    service = WordPressService(base_url="https://example.test")

    def fake_fetch_pages():
        calls["pages"] += 1
        return [{"title": "Page", "slug": "page"}]

    def fake_fetch_posts():
        calls["posts"] += 1
        return [{"title": "Post", "slug": "post"}]

    monkeypatch.setattr(service, "fetch_pages", fake_fetch_pages)
    monkeypatch.setattr(service, "fetch_posts", fake_fetch_posts)

    first = service.fetch_all_content()
    second = service.fetch_all_content()

    assert first == second
    assert calls == {"pages": 1, "posts": 1}


def test_clear_site_cache_endpoint():
    response = client.post("/site/cache/clear", params={"site_url": "https://example.test"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_homepage_service_flags_bulk_content_and_weak_links():
    long_content = " ".join(["υπηρεσία"] * 1100)
    pages = [
        {
            "title": "Αρχική",
            "slug": "home",
            "url": "https://example.test",
            "post_type": "page",
            "is_front_page": True,
            "content": long_content,
            "internal_links": ["/service-a"],
        }
    ]
    topology = {
        "homepage": {"slug": "home"},
        "pillars": [
            {"title": "Service A", "slug": "service-a", "url": "https://example.test/service-a"},
            {"title": "Service B", "slug": "service-b", "url": "https://example.test/service-b"},
            {"title": "Service C", "slug": "service-c", "url": "https://example.test/service-c"},
        ],
    }

    analysis = HomepageService().analyze(pages, topology)
    issue_types = {issue["type"] for issue in analysis["issues"]}

    assert analysis["found"] is True
    assert analysis["metrics"]["word_count"] == 1100
    assert "homepage_too_long" in issue_types
    assert "few_homepage_internal_links" in issue_types
    assert "few_pillar_links" in issue_types


def test_homepage_service_builds_structured_guidance():
    pages = [
        {
            "title": "Αρχική",
            "slug": "home",
            "url": "https://example.test",
            "post_type": "page",
            "is_front_page": True,
            "content": "Επικοινωνήστε μαζί μας για άμεση τεχνική υποστήριξη.",
            "internal_links": [],
        }
    ]
    topology = {
        "homepage": {"slug": "home"},
        "pillars": [
            {"title": "Συντήρηση λέβητα", "slug": "syntirisi-levita", "url": "https://example.test/syntirisi-levita"},
        ],
        "satellites": [],
        "orphans": [],
    }

    guidance = HomepageService().build_guidance(pages, topology)

    assert guidance["homepage_analysis"]["found"] is True
    assert guidance["architecture"]["recommended_sections"]
    assert guidance["semantic"]["meaning_rules"]
    assert guidance["internal_link_plan"]["missing_priority_links"][0]["slug"] == "syntirisi-levita"
    assert guidance["action_plan"]


def test_homepage_guidance_endpoint_returns_plan(monkeypatch):
    pages = [
        {
            "title": "Home",
            "slug": "home",
            "url": "https://example.test",
            "post_type": "page",
            "is_front_page": True,
            "content": "Επικοινωνήστε μαζί μας για υπηρεσίες θέρμανσης.",
            "internal_links": [],
            "yoast": {"available": True, "schema_types": ["WebSite"]},
        }
    ]

    class FakeWordPressService:
        def __init__(self, base_url=None) -> None:
            self.base_url = base_url or "https://example.test"

        def fetch_all_content(self):
            return pages

        def fetch_categories(self):
            return {}

    class FakeTopologyService:
        def analyze_topology(self, site_pages, categories):
            return {
                "homepage": {"title": "Home", "slug": "home"},
                "pillars": [
                    {
                        "title": "Service",
                        "slug": "service",
                        "url": "https://example.test/service",
                    }
                ],
                "satellites": [],
                "orphans": [],
            }

    monkeypatch.setattr("app.api.routes.WordPressService", FakeWordPressService)
    monkeypatch.setattr("app.api.routes.TopologyService", FakeTopologyService)

    response = client.get("/site/homepage-guidance", params={"site_url": "https://example.test"})

    assert response.status_code == 200
    data = response.json()
    assert data["site_pages_found"] == 1
    assert data["guidance"]["homepage_analysis"]["found"] is True
    assert data["guidance"]["architecture"]["recommended_sections"]
    assert data["guidance"]["action_plan"]
