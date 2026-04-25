.PHONY: up down logs test shell clean

up:
	docker-compose up --build

up-d:
	docker-compose up --build -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	docker-compose run --rm api sh -c "pip install --no-cache-dir -r requirements.txt && pytest -v"

shell:
	docker-compose exec api sh

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
