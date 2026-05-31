# Play Spec

## Purpose
- Lightweight multiplayer game hub for family play with PIN-based authentication.
- Solves family engagement with games, task tracking, and wallet rewards.

## Scope
- In scope: PIN authentication, game selection, player state, leaderboard, tasks, wallet.
- Out of scope: enterprise-style dashboards, external authentication.

## Business Value
- Primary ROI: family engagement and repeat use.
- Secondary ROI: simple shared play platform with gamification.
- Success metrics: session length, repeat plays, task completion rate, low friction.

## UX Standard
- Browser title: `Play`
- Header: `silrod | Play`
- Favicon: `https://home.silrod.org/static/silrod_logo.svg`
- Layout: shared silrod shell via `silrod-ui` macros
- Theme: `silrod.css` + `silrod-components.css`
- Navigation: shared `shell_header`/`shell_footer` from silrod-ui
- Footer: dark (`bg-slate-800`) with "Silvio Rodriguez © 2026"

## Authentication
- **Method:** 4-digit PIN per player (Emma, Mateo, Dad)
- **First login:** player selects name, enters 4-digit PIN → PIN is hashed with bcrypt and stored
- **Subsequent logins:** player selects name, enters PIN → verified against stored hash
- **Session:** HttpOnly cookie (`play_session`), SameSite=lax, 30-day TTL
- **Rate limiting:** 5 failed attempts per player+IP → 5-minute lockout
- **Logout:** POST `/logout` clears the session cookie
- **Protected routes:** all except `/login`, `/health`, `/ready`, `/static/*`

## Information Architecture
- Routes:
  - `GET /login` — player + PIN entry form
  - `POST /login` — authenticate, set session cookie
  - `POST /logout` — clear session
  - `GET /` — game dashboard (protected)
  - `GET /leaderboard` — player rankings (protected)
  - `GET /tasks` — task management (protected)
  - `GET /games/chess` — Chess vs AI (Calypso) (protected)
  - `GET /games/tictactoe` — Tic-Tac-Toe local 2P (protected)
  - `GET /games/connectfour` — Connect Four vs AI (protected)
  - `GET /games/rockpaperscissors` — RPS vs bot (protected)
  - `GET /games/snake` — Snake high score (protected)
  - `GET /games/hangman` — Hangman word game (protected)
  - `GET /games/checkers` — Checkers vs AI (protected)
  - `GET /games/simonsays` — Simon Says memory game (protected)
  - `GET /games/wordsearch` — Word search race vs AI (protected)
- API prefix: `/api/`
  - `GET /api/players` — all players with stats and wallet balance
  - `GET /api/tasks/{child}` — tasks for a player
  - `POST /api/tasks` — create task
  - `PATCH /api/tasks/{id}` — update task (complete, recurring increment)
  - `POST /api/tasks/{id}/approve` — approve with PIN verification
  - `DELETE /api/tasks/{id}` — delete task
  - `POST /api/tasks/{id}/approve` — approve + credit wallet
  - `GET /api/transactions/{child}` — transaction history
  - `POST /api/transactions` — manual transaction
  - `POST /api/payout/{child}` — mark approved tasks as paid
  - `GET /api/wallet/{name}` — wallet balance
  - `GET /api/session` — current logged-in player
  - `GET /api/games/chess/move`, `/api/games/tictactoe/move`, etc. — game APIs

## Data Model
- **Player:** name (PK), pin (bcrypt hash), wins, losses, game_wins (JSON), selfie (bool), created_at
- **Wallet:** player_name (PK), balance (Numeric), updated_at
- **Task:** id (PK), child_name, task_description, points, is_completed, is_approved, is_paid, is_recurring, series_total, series_count, last_increment_at, created_at
- **Transaction:** id (PK), child_name, amount, description, kind, created_at
- **PlayerCollection:** id (PK), player_name, game_id, collection_data (JSON), updated_at
- **Achievement:** id (PK), platform, game_id, achievement_id, title, achieved (bool), timestamp
- Storage: PostgreSQL via SQLAlchemy async

## Design System Rules
- Directory layout: Standard silrod app structure (`web/`, `core/`, `services/`)
- Template layout: Uses `base.html` extending silrod-ui shell macros
- Static assets: `web/static/` + served from `silrod-ui`
- Shared shell: `shell_header(shell_label='Play')` and `shell_footer(shell_footer_label='Play')`
- Auth: via `web/middleware/auth.py` (AuthMiddleware), routes in `web/routes/auth.py`
- PIN auth: bcrypt hashing, rate limiting, session cookie

## Tech Stack
- FastAPI + Uvicorn + Python 3.12
- Socket.IO for real-time game events
- PostgreSQL via SQLAlchemy async (asyncpg driver)
- Jinja2 templates + HTMX
- python-chess for server-side chess validation
- silrod-ui for shared shell/CSS/JS
- silrod-core for logging and shared utilities

## Simplify / Improve ROI
- Keep the entry dashboard minimal.
- Hide game-specific clutter until needed.
- Make replay and switching games immediate.
- Wallet balance visible at a glance on dashboard.
- Task approval requires PIN — no separate admin needed.
