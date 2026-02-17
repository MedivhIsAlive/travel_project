# Travel Planner API

Manage travel projects and collect places from the [Art Institute of Chicago API](https://api.artic.edu/docs/).

## Setup

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000/api/
Docs: http://localhost:8000/api/docs/

## Run Tests

```bash
docker compose exec web python manage.py test
```

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/projects/` | List projects |
| POST | `/api/projects/` | Create project (optionally with places) |
| GET | `/api/projects/{id}/` | Get project |
| PATCH | `/api/projects/{id}/` | Update project |
| DELETE | `/api/projects/{id}/` | Delete project |
| GET | `/api/projects/{id}/places/` | List places |
| POST | `/api/projects/{id}/places/` | Add place |
| GET | `/api/projects/{id}/places/{external_id}/` | Get place |
| PATCH | `/api/projects/{id}/places/{external_id}/` | Update place |

## Example Requests

Create project with places:
```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Chicago Trip", "places": [{"external_id": "129884"}, {"external_id": "27992"}]}'
```

Mark place as visited:
```bash
curl -X PATCH http://localhost:8000/api/projects/1/places/129884/ \
  -H "Content-Type: application/json" \
  -d '{"visited": true, "notes": "Beautiful painting"}'
```
