# Play App Codemap

## Overview
Lightweight multiplayer game hub for family play with PIN-based authentication. FastAPI + PostgreSQL + Jinja2/HTMX.

## Directory Structure

```
play-app/
├── main.py              # FastAPI entry point
├── config.py            # Settings
├── database.py          # SQLAlchemy async setup
├── auth.py              # PIN auth + middleware
├── db_init.py           # Database initialization
├── silrod_core/         # Shared core (if present)
├── core/                # Core business logic
│   ├── __init__.py
│   ├── models.py        # SQLAlchemy models
│   └── schemas.py       # Pydantic schemas
├── services/             # Business services
│   ├── __init__.py
│   ├── game_service.py
│   ├── wallet_service.py
│   └── task_service.py
├── web/                  # Web layer
│   ├── __init__.py
│   ├── main.py          # Web routes
│   ├── auth.py          # Auth routes
│   ├── games.py         # Game routes
│   ├── tasks.py         # Task routes
│   ├── wallet.py        # Wallet routes
│   └── templates/       # Jinja2 templates
├── docs/
│   └── app-spec.md
├── tests/
└── Dockerfile
```

## Key Entry Points

- `main.py:app` - FastAPI application instance
- `web/main.py` - Web route registration

## Dependencies
- FastAPI + Uvicorn
- SQLAlchemy async (asyncpg)
- Jinja2 + HTMX
- python-chess
- silrod-core
