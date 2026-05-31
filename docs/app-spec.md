# Play Spec

## Purpose
- Lightweight multiplayer game hub for family play.

## Scope
- In scope: game selection, player state, leaderboard, tasks.
- Out of scope: enterprise-style dashboards.

## Business Value
- Primary ROI: family engagement and repeat use.
- Secondary ROI: simple shared play platform.
- Success metrics: session length, repeat plays, low friction.

## UX Standard
- Browser title: `Play`
- Header: `silrod | Play`
- Favicon: `https://home.silrod.org/static/silrod_logo.svg`
- Layout: shared silrod shell via `silrod-ui` macros
- Theme: `silrod.css` + `silrod-components.css`
- Navigation: shared shell_header/shell_footer from silrod-ui

## Information Architecture
- Routes:
  - `/` — Game dashboard
  - `/leaderboard` — Player rankings by wins and wallet balance
  - `/tasks` — Task management and approval for kids
  - `/games/chess` — Chess vs AI (Calypso)
  - `/games/tictactoe` — Tic-tac-toe local 2-player
  - `/games/connectfour` — Connect Four vs AI
  - `/games/rockpaperscissors` — RPS vs bot
  - `/games/snake` — Snake high score
  - `/games/hangman` — Hangman word game
  - `/games/checkers` — Checkers vs AI
  - `/games/simonsays` — Simon Says memory game
  - `/games/wordsearch` — Word search race vs AI
- API prefix: `/api/`

## Data Model
- Main entities: Player, Wallet, Task, Transaction, PlayerCollection, Achievement
- Storage: PostgreSQL via SQLAlchemy async

## Design System Rules
- Directory layout: Standard silrod app structure (`web/`, `core/`, `services/`)
- Template layout: Uses `base.html` extending silrod-ui shell macros
- Static assets: `web/static/` + served from `silrod-ui`
- Shared shell: `shell_header(shell_label='Play')` and `shell_footer(shell_footer_label='Play')`

## Simplify / Improve ROI
- Keep the entry dashboard minimal.
- Hide game-specific clutter until needed.
- Make replay and switching games immediate.
