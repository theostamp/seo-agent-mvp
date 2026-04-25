# SEO Agent MVP v0.2 – Full Project Structure

## Overview

Ένα AI-powered SEO agent για WordPress sites που:
- Κάνει keyword discovery
- Αναλύει τη δομή του site (pillar/satellite model)
- Εξάγει style profile από το υπάρχον content
- Αναλύει Yoast SEO data
- Ελέγχει Schema.org markup και AI readiness
- Παράγει GEO-optimized proposals (Generative Engine Optimization)
- Δημιουργεί side-by-side previews για review

## Tech Stack

- **Backend**: FastAPI + LangGraph
- **Database**: PostgreSQL
- **UI**: Streamlit
- **LLM**: Gemini API (ή OpenAI)
- **Container**: Docker Compose
- **Platform**: WSL2 / Ubuntu

---

## 1. Δομή Φακέλων

```text
seo-agent-mvp/
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── logging_config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── workflow.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py
│   │   ├── wordpress_service.py
│   │   ├── keyword_service.py
│   │   ├── analysis_service.py
│   │   ├── proposal_service.py
│   │   ├── style_service.py
│   │   ├── topology_service.py
│   │   ├── yoast_service.py
│   │   ├── schema_analyzer.py
│   │   └── content_generator.py
│   └── utils/
│       ├── __init__.py
│       └── text.py
├── ui/
│   └── app.py
└── tests/
    ├── __init__.py
    └── test_health.py
```

---

## 2. Workflow Architecture

```
┌─────────────────┐
│ discover_keywords│
└────────┬────────┘
         │
┌────────▼────────┐
│read_site_content│  ← Fetches pages, posts, categories, Yoast data
└────────┬────────┘
         │
┌────────▼────────┐
│  extract_style  │  ← Analyzes tone, addressing, structure
└────────┬────────┘
         │
┌────────▼────────┐
│analyze_topology │  ← Identifies pillars, satellites, homepage
└────────┬────────┘
         │
┌────────▼────────┐
│  analyze_yoast  │  ← SEO issues, meta, focus keyphrases
└────────┬────────┘
         │
┌────────▼────────┐
│ analyze_schema  │  ← Schema.org coverage, AI readiness score
└────────┬────────┘
         │
┌────────▼────────┐
│  analyze_gaps   │  ← GEO-enhanced proposals with all context
└─────────────────┘
```

---

## 3. Services

### Core Services

| Service | Description |
|---------|-------------|
| `llm_service.py` | Gemini/OpenAI abstraction with retry logic |
| `wordpress_service.py` | WP REST API client with Yoast data extraction |
| `keyword_service.py` | AI keyword discovery |
| `analysis_service.py` | Gap analysis with GEO prompts |
| `proposal_service.py` | Database persistence |

### Analysis Services

| Service | Description |
|---------|-------------|
| `style_service.py` | Extracts style profile (tone, addressing, structure) |
| `topology_service.py` | Analyzes pillar/satellite content structure |
| `yoast_service.py` | Analyzes Yoast SEO data and issues |
| `schema_analyzer.py` | Schema.org analysis + AI readiness scoring |
| `content_generator.py` | Generates preview comparisons |

---

## 4. Proposal Types

### Content Architecture

| Type | Description |
|------|-------------|
| `create_satellite_post` | New supporting post for existing pillar |
| `update_satellite_post` | Improve existing satellite |
| `update_pillar_page` | Light improvements to pillar page |
| `link_existing_content` | Add internal links |
| `create_pillar_page` | New pillar (rare) |

### SEO & Schema

| Type | Description |
|------|-------------|
| `improve_seo_meta` | Fix Yoast meta (title, description, keyphrase) |
| `add_faq_section` | Add FAQ with FAQPage schema |
| `add_howto_section` | Add HowTo steps with schema |
| `improve_schema` | Fix/add structured data |
| `geo_optimize` | AI search optimization |

---

## 5. GEO Guidelines (Generative Engine Optimization)

Το σύστημα εφαρμόζει αυτές τις αρχές στα proposals:

1. **Clear Answers First** - Σαφείς απαντήσεις στην αρχή κάθε section
2. **FAQ Sections** - 3-5 FAQs ανά σελίδα με FAQPage schema
3. **Entity Definitions** - Ορισμοί τεχνικών όρων
4. **Structured Summaries** - TL;DR και key takeaways
5. **Conversational Tone** - Voice search friendly
6. **Authoritative Citations** - Αναφορές σε πρότυπα
7. **HowTo Structure** - Αριθμημένα βήματα με schema

---

## 6. Database Schema

### ContentProposal

```sql
CREATE TABLE content_proposals (
    id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER REFERENCES workflow_runs(id),
    proposal_type VARCHAR(50) NOT NULL,
    target_title VARCHAR(500) NOT NULL,
    parent_pillar VARCHAR(255),
    summary TEXT NOT NULL,
    outline TEXT,
    suggested_schema TEXT,
    faq_suggestions TEXT,
    schema_additions TEXT,
    seo_meta_suggestions TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'needs_review',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 7. API Endpoints

### Workflow

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflow/run` | Execute full analysis workflow |
| GET | `/health` | Health check |

### Proposals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/proposals` | List all proposals |
| GET | `/proposals/{id}` | Get single proposal |
| GET | `/proposals/{id}/preview` | Generate side-by-side preview |

---

## 8. UI Features

### Tab 1: Νέα Ανάλυση
- Input: category, seed keywords, location
- Output: keywords, clusters, proposals
- Metrics: Yoast issues, AI readiness, topology

### Tab 2: Proposals
- Filter by status
- Preview button per proposal
- Priority indicators
- Parent pillar info

### Tab 3: Preview
- Side-by-side comparison
- Current vs Proposed meta
- FAQ suggestions preview
- Schema recommendations
- Character counts

---

## 9. Environment Variables

```env
# App
APP_NAME=seo-agent-mvp
APP_ENV=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/seo_agent

# LLM Provider (gemini or openai)
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-flash-latest

# Alternative: OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# WordPress
WORDPRESS_BASE_URL=https://yoursite.com
WORDPRESS_USERNAME=your_username
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
WORDPRESS_TIMEOUT=30
```

---

## 10. Docker Compose

```yaml
services:
  api:
    image: python:3.11-slim
    container_name: seo-agent-api
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir -r requirements.txt &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes:
      - ./:/app
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  ui:
    image: python:3.11-slim
    container_name: seo-agent-ui
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir streamlit requests &&
             streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0"
    volumes:
      - ./:/app
    ports:
      - "8501:8501"
    depends_on:
      - api

  db:
    image: postgres:16
    container_name: seo-agent-db
    environment:
      POSTGRES_DB: seo_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

---

## 11. Quick Start

```bash
# 1. Clone & setup
cd ~/projects/seo-agent-mvp
cp .env.example .env
# Edit .env with your credentials

# 2. Start services
docker-compose up -d

# 3. Access
# API docs: http://localhost:8000/docs
# UI: http://localhost:8501

# 4. Run analysis
# Use the UI or POST to /workflow/run
```

---

## 12. Example Request

```json
POST /workflow/run
{
  "category_name": "Επισκευή μπαλκονιών",
  "seed_keywords": [
    "επισκευή μπαλκονιών",
    "στεγανοποίηση μπαλκονιού",
    "επισκευή πλακιδίων"
  ],
  "location": "Αθήνα",
  "style_config": {
    "tone": "professional",
    "addressing": "εσείς"
  }
}
```

---

## 13. Example Response

```json
{
  "workflow_run_id": 7,
  "category_name": "Επισκευή μπαλκονιών",
  "discovered_keywords": ["επισκευή μπαλκονιού κόστος", "..."],
  "clusters_count": 4,
  "site_pages_found": 36,
  "style_profile": {
    "tone": "professional",
    "addressing": "εσείς",
    "technical_level": "medium"
  },
  "topology": {
    "homepage_title": "Αρχική",
    "pillars_count": 11,
    "satellites_count": 9,
    "orphans_count": 15
  },
  "yoast_summary": {
    "total_issues": 71,
    "high_priority_issues": 46,
    "missing_focus_keyphrase": 12
  },
  "schema_summary": {
    "ai_readiness_score": 45.2,
    "has_faq_schema": false,
    "has_howto_schema": false
  },
  "proposals": [
    {
      "id": 17,
      "proposal_type": "add_faq_section",
      "target_title": "Επισκευή Μπαλκονιών",
      "parent_pillar": "ypiresies",
      "priority": "high",
      "faq_suggestions": "[...]",
      "suggested_schema": "FAQPage"
    }
  ],
  "status": "needs_review"
}
```

---

## 14. Future Improvements

### Phase 2
- [ ] Alembic migrations
- [ ] Approval workflow (approve/reject/revise)
- [ ] Auto-publish approved content to WordPress
- [ ] Batch processing multiple categories

### Phase 3
- [ ] Competitor analysis
- [ ] SERP tracking
- [ ] Content performance monitoring
- [ ] A/B testing for proposals

### Phase 4
- [ ] Multi-site support
- [ ] Team collaboration
- [ ] Custom prompt templates
- [ ] Plugin marketplace

---

## 15. Architecture Notes

**Γιατί αυτή η αρχιτεκτονική:**

1. **Backend-first**: Καθαρό API, εύκολο να επεκταθεί
2. **Human-in-the-loop**: Τίποτα δεν γίνεται publish χωρίς review
3. **Modular services**: Κάθε service κάνει ένα πράγμα καλά
4. **LLM-agnostic**: Εύκολη αλλαγή provider (Gemini ↔ OpenAI)
5. **Content topology aware**: Σέβεται τη δομή pillar/satellite
6. **GEO-ready**: Optimized για AI search engines

---

*Last updated: 2026-04-23*
*Version: 0.2*
