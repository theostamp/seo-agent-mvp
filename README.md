# SEO Agent MVP

Backend SEO / content recommendation engine για WordPress site (oikonrg.gr).

## Τι κάνει

1. Δέχεται κατηγορία θέματος και seed keywords
2. Κάνει keyword/topic discovery με LLM
3. Διαβάζει το περιεχόμενο του WordPress site μέσω REST API
4. Κάνει gap analysis μεταξύ keywords και υπάρχοντος content
5. Παράγει proposals (update/create page/category)
6. Σταματά στο human review stage

**Δεν κάνει:** publish, write-back στο WordPress, Elementor integration.

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
- [ ] WordPress pagination για όλες τις σελίδες
- [x] Approval/reject endpoints
- [ ] Content deduplication scoring
