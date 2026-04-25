# SEO Agent MVP

AI-powered SEO agent για WordPress sites με keyword discovery, content analysis και GEO optimization.

---

## Εγκατάσταση σε Windows (βήμα-βήμα)

### Βήμα 1: Εγκατάσταση WSL2

Άνοιξε **PowerShell ως Administrator** και τρέξε:

```powershell
wsl --install
```

Κάνε restart τον υπολογιστή. Μετά το restart, θα ανοίξει αυτόματα το Ubuntu και θα σου ζητήσει username/password.

### Βήμα 2: Εγκατάσταση Docker Desktop

1. Κατέβασε το [Docker Desktop για Windows](https://www.docker.com/products/docker-desktop/)
2. Εγκατέστησέ το και κάνε restart αν χρειαστεί
3. Άνοιξε το Docker Desktop
4. Πήγαινε στο **Settings > Resources > WSL Integration**
5. Ενεργοποίησε το "Enable integration with my default WSL distro"
6. Πάτα **Apply & Restart**

### Βήμα 3: Clone του repository

Άνοιξε το **Ubuntu terminal** (από το Start menu) και τρέξε:

```bash
# Δημιούργησε φάκελο projects
mkdir -p ~/projects
cd ~/projects

# Clone το repo
git clone https://github.com/theostamp/seo-agent-mvp.git
cd seo-agent-mvp
```

### Βήμα 4: Ρύθμιση credentials

```bash
# Αντίγραψε το example config
cp .env.example .env

# Άνοιξε για επεξεργασία
nano .env
```

Συμπλήρωσε τα παρακάτω:

```env
# Gemini API (δωρεάν από https://aistudio.google.com/apikey)
GEMINI_API_KEY=AIzaSy...

# WordPress credentials
WORDPRESS_BASE_URL=https://your-site.gr
WORDPRESS_USERNAME=your_username
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> **Tip:** Για WordPress App Password: WordPress Admin > Users > Profile > Application Passwords

Πάτα `Ctrl+X`, μετά `Y`, μετά `Enter` για αποθήκευση.

### Βήμα 5: Εκκίνηση

```bash
# Ξεκίνα την εφαρμογή
docker-compose up -d

# Περίμενε ~30 δευτερόλεπτα και έλεγξε
docker-compose ps
```

### Βήμα 6: Χρήση

Άνοιξε στον browser:

| URL | Περιγραφή |
|-----|-----------|
| http://localhost:8501 | **UI** - Κύρια εφαρμογή |
| http://localhost:8000/docs | **API Docs** - Swagger |

### Αντιμετώπιση προβλημάτων

```bash
# Δες τα logs
docker-compose logs -f api

# Restart όλων
docker-compose down && docker-compose up -d

# Καθαρισμός και rebuild
docker-compose down -v && docker-compose up -d --build
```

---

## Τι κάνει

1. **Keyword Discovery** - Ανακαλύπτει keywords με AI clustering
2. **Site Analysis** - Διαβάζει WordPress content μέσω REST API
3. **Style Extraction** - Αναλύει το ύφος του υπάρχοντος περιεχομένου
4. **Topology Analysis** - Εντοπίζει pillar/satellite δομή
5. **Yoast Integration** - Ελέγχει SEO issues και meta
6. **Schema Analysis** - Αναλύει Schema.org markup και AI readiness
7. **GEO Proposals** - Παράγει προτάσεις βελτιστοποιημένες για AI search
8. **Preview** - Side-by-side σύγκριση υπάρχοντος vs προτεινόμενου

**Human-in-the-loop:** Τίποτα δεν γίνεται publish χωρίς review.

## Περιβάλλον

- WSL2 + Ubuntu
- Docker Compose
- Python 3.11
- FastAPI + PostgreSQL + LangGraph

## Εκκίνηση

```bash
# 1. Αντίγραψε το .env
cp .env.example .env

# 2. Συμπλήρωσε τα credentials
#    - OPENAI_API_KEY
#    - WORDPRESS_BASE_URL
#    - WORDPRESS_USERNAME
#    - WORDPRESS_APP_PASSWORD

# 3. Τρέξε
make up

# 4. Swagger docs
# http://localhost:8000/docs
```

## Endpoints

| Method | Path | Περιγραφή |
|--------|------|-----------|
| GET | `/health` | Health check |
| GET | `/site/audit` | Γρήγορο audit WordPress content, topology, Yoast και schema |
| POST | `/workflow/run` | Εκτέλεση workflow |
| GET | `/proposals` | Λίστα proposals |
| GET | `/proposals/{id}` | Λεπτομέρειες proposal |
| PATCH | `/proposals/{id}/status` | Αλλαγή status (`needs_review`, `approved`, `rejected`) |
| POST | `/proposals/{id}/approve` | Έγκριση proposal |
| POST | `/proposals/{id}/reject` | Απόρριψη proposal |
| GET | `/proposals/{id}/preview` | AI preview αλλαγών |
| POST | `/proposals/{id}/generate-html` | Δημιουργία πλήρους HTML |

## Tests

```bash
make test
```

## Χρήσιμα env settings

| Variable | Default | Περιγραφή |
|----------|---------|-----------|
| `WORDPRESS_PER_PAGE` | `100` | Items ανά WordPress REST page |
| `WORDPRESS_MAX_PAGES` | `20` | Μέγιστες REST pages ανά content type |
| `GENERATED_CONTENT_DIR` | `generated_content` | Φάκελος για generated HTML |

## Παράδειγμα request

```bash
curl -X POST http://localhost:8000/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "category_name": "Επισκευή όψεων κτιρίων",
    "seed_keywords": ["επισκευή όψεων", "αποκατάσταση προσόψεων"],
    "location": "Αθήνα"
  }'
```

## Επόμενα βήματα

- [ ] Alembic migrations
- [x] WordPress pagination για όλες τις σελίδες
- [x] Approval/reject endpoints
- [ ] Content deduplication scoring
