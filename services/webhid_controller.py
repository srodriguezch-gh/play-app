import json
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/webhid")

# Simple bearer token auth using existing AuthMiddleware token logic (placeholder)
security = HTTPBearer(auto_error=False)

def get_current_player(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # In a real setup, verify JWT token and extract player name
    # Here we assume token string is the player name for simplicity
    return credentials.credentials

class SavePayload(BaseModel):
    game: str
    state: dict

@router.post("/save")
async def save_game(payload: SavePayload, request: Request, player: str = Depends(get_current_player)):
    """Receive a JSON snapshot of the current game state and forward to brain‑app."""
    # Forward to brain‑app sync service (will be imported in play‑app runtime)
    from services.brain_sync import save_game_state
    await save_game_state(player, payload.game, payload.state)
    return {"status": "saved"}

@router.get("/load/{game}")
async def load_game(game: str, request: Request, player: str = Depends(get_current_player)):
    """Retrieve the latest saved state for a given game and player."""
    from services.brain_sync import load_game_state
    state = await load_game_state(player, game)
    if state is None:
        raise HTTPException(status_code=404, detail="No saved state")
    return {"game": game, "state": state}

@router.post("/listen")
async def listen_events(request: Request, player: str = Depends(get_current_player)):
    """Placeholder endpoint for a future WebSocket stream of raw HID events."""
    return {"status": "ok"}
