# Play App Spec

## Purpose
Lightweight multiplayer game hub for family play with PIN-based authentication.

## Business Value
- Primary ROI: family engagement and repeat use
- Secondary ROI: task completion through gamification
- Success metrics: session_length, repeat_plays, task_completion_rate

## Tech Stack
- **Stack**: FastAPI + PostgreSQL + Jinja2/HTMX + Socket.IO
- **Port**: 3001
- **Container**: play-app
- **Host**: BOSGAME (192.168.5.98) - MOVED from NUC
- **Database**: PostgreSQL (shared postgres container)

## Directory Structure
```
/home/silvio/apps/play-app/
├── main.py              # FastAPI app entry point
├── config.py            # Settings
├── database.py          # DB models
├── auth.py              # PIN auth + middleware
├── web/
│   ├── main.py        # API routes
│   ├── templates/     # Jinja2 templates
│   └── static/        # Static assets
└── docs/
    └── app-spec.md
```

## API Endpoints

### Value Metrics
| Endpoint | Method | Auth | Description |
|---------|--------|------|-------------|
| `/api/v1/status` | GET | No | Value metrics (sessions, tasks, engagement) |
| `/health` | GET | No | Health check |

### Status Response (`/api/v1/status`)
```json
{
  "task_completion_rate": 1.0,
  "total_tasks": 1,
  "approved_tasks": 1,
  "week_tasks_created": 1,
  "points_by_child": {"Emma": 5.0},
  "active_players": 3,
  "timestamp": "2026-06-01T..."
}
```

## Authentication
- **Method:** 4-digit PIN per player (Emma, Mateo, Dad)
- **First login:** player selects name, enters 4-digit PIN → PIN is hashed with bcrypt and stored
- **Subsequent logins:** player selects name, enters PIN → verified against stored hash
- **Session:** HttpOnly cookie (`play_session`), SameSite=lax, 30-day TTL
- **Rate limiting:** 5 failed attempts per player+IP → 5-minute lockout
- **Protected routes:** all except `/login`, `/health`, `/ready`, `/static/*`

## Key Routes
| Route | Description |
|-------|-------------|
| `/login` | PIN entry form |
| `/` | Game dashboard (protected) |
| `/leaderboard` | Player rankings |
| `/tasks` | Task management |
| `/wallet/{player}` | Wallet balance |

## Games Available
- Chess vs AI
- Tic-Tac-Toe local 2P
- Connect Four vs AI
- Rock Paper Scissors
- Snake
- Hangman
- Checkers vs AI
- Simon Says
- Word Search

## Data Model
- **Player:** name, pin_hash, wins, losses, game_wins (JSON)
- **Wallet:** player_name, balance
- **Task:** child_name, description, points, is_completed, is_approved, is_paid
- **Transaction:** player_name, amount, description, kind

## Environment Variables
| Variable | Description |
|----------|-------------|
| `SILROD_APP_NAME` | App identifier |
| `POSTGRES_HOST` | PostgreSQL host |
| `POSTGRES_PORT` | PostgreSQL port |
| `POSTGRES_USER` | PostgreSQL user |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | Database name |
| `PYTHONPATH` | Include /app and /app/silrod_core |

## Deployment
```bash
# Via compose
cd /home/silvio/bosgame-compose
docker compose -f compose.infra.yml -f compose.apps.yml up -d play-app

# Manual rebuild
cd /home/silvio/apps/play-app
docker build --no-cache -t play-app:local .
```

## Health Monitoring
- Watchdog monitors: `http://play-app:3001/`
- Value metric: `http://play-app:3001/api/v1/status`

## Recent Changes
- 2026-06-01: Moved from NUC to BOSGAME (same host as other apps)
- Added /api/v1/status endpoint for value metrics
- Auth redirect fixed (excluded `/api/v1/status` from auth middleware)
## Architect's Deep Review (2026-06-03)

### Expert Game Design Analysis
Needs a **Unified Infrastructure** for game state persistence and standard controller mapping.

### Recommendations
1. **Save-Game Brain Sync**: Store game states and high scores as "Memories" in the Brain app via direct API.
2. **Standard Controller Layer**: Implement a unified mapping for Bluetooth/WebHID controllers to ensure consistent UX across all internal games.
3. **Integrated Hub UI**: Transition to a lean "Game Shell" that manages the lifecycle (start/suspend/resume) of child game processes.
