"""Socket.io event handlers for real-time game communication."""

import asyncio
import logging
from typing import Optional

import socketio

from core.game_manager import game_manager
from core.calypso import bot_service
from core.db import Player, Wallet, async_session

logger = logging.getLogger(__name__)

_sio: Optional[socketio.AsyncServer] = None


def init_socket(sio_instance: socketio.AsyncServer):
    global _sio
    _sio = sio_instance


def get_sio() -> socketio.AsyncServer:
    return _sio


async def _get_players_map() -> dict:
    async with async_session() as session:
        result = await session.execute(select(Player))
        players = {}
        for p in result.scalars().all():
            game_wins = p.game_wins if isinstance(p.game_wins, dict) else {}
            players[p.name] = {
                "name": p.name, "wins": p.wins, "losses": p.losses,
                "gameWins": game_wins, "selfie": p.selfie, "hasPin": bool(p.pin),
            }
        return players


def register_events(sio: socketio.AsyncServer):
    """Register Socket.IO event handlers."""

    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        player_name = game_manager.remove_online(sid)
        logger.info(f"Client disconnected: {sid} ({player_name})")
        await sio.emit("updateOnlineStatus", game_manager.get_online_status())

    @sio.event
    async def login(sid, player_name: str):
        game_manager.set_online(sid, player_name)
        await sio.emit("updateOnlineStatus", game_manager.get_online_status())

    @sio.event
    async def getOnlineUsers(sid):
        await sio.emit("onlineUsersResult", game_manager.get_online_status())

    @sio.event
    async def getPlayers(sid):
        players = await _get_players_map()
        await sio.emit("playersResult", players)

    @sio.event
    async def sendChallenge(sid, data: dict):
        challenger = data.get("challenger")
        opponent = data.get("opponent")
        game = data.get("game")
        logger.info(f"{challenger} challenged {opponent} to {game}")
        for socket_id, name in game_manager.online_users.items():
            if name == opponent:
                await sio.emit("receiveChallenge", {"challenger": challenger, "game": game}, to=socket_id)
                break

    @sio.event
    async def acceptChallenge(sid, data: dict):
        challenger = data.get("challenger")
        opponent = data.get("opponent")
        game = data.get("game")
        room_id = f"{game}_{challenger}_{opponent}_{int(asyncio.get_event_loop().time())}"
        for socket_id, name in game_manager.online_users.items():
            if name == challenger:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": opponent, "game": game, "role": "X"}, to=socket_id)
            elif name == opponent:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": challenger, "game": game, "role": "O"}, to=socket_id)

    @sio.event
    async def joinRoom(sid, room_id: str):
        await sio.enter_room(sid, room_id)
        logger.info(f"Socket {sid} joined room {room_id}")

    @sio.event
    async def makeMove(sid, data: dict):
        """Broadcast the move and trigger server-side chess AI when needed."""
        room_id = data.get("roomId")
        move = data.get("move")
        move_type = data.get("type")
        game_type = data.get("game", "unknown")

        if move_type == "reset":
            if game_type == "chess":
                game_manager.reset_chess(room_id)
            await sio.emit("gameReset", room=room_id)
            return

        # Route move to room — game logic is client-side
        await sio.emit("moveMade", {
            "move": move,
            "game": game_type,
            "fen": data.get("fen"),
            "nextState": data.get("nextState"),
        }, room=room_id)

        # Chess AI response via bot_service.
        if game_type == "chess" and ("solo" in room_id or "Calypso" in room_id or "Traka" in room_id):
            fen = data.get("fen")
            if fen:
                bot_name = "Calypso" if "Calypso" in room_id else "Traka"
                await bot_service.request_chess_move(bot_name, fen, lambda result: _handle_ai_response(room_id, result))

    async def _handle_ai_response(room_id: str, result: dict):
        if "error" in result:
            return
        try:
            import chess

            ai_move_str = f"{result['from']}{result['to']}"
            game_obj = game_manager.get_game(room_id)
            if game_obj and hasattr(game_obj, 'fen'):
                board = chess.Board(game_obj.fen)
                mv = chess.Move.from_uci(ai_move_str)
                if mv in board.legal_moves:
                    board.push(mv)
                    game_manager.update_chess_fen(room_id, board.fen())
                else:
                    return
            await sio.emit("moveMade", {"move": ai_move_str, "fen": board.fen()}, room=room_id)
        except Exception as e:
            logger.error(f"AI move error: {e}")

    @sio.event
    async def gameEnd(sid, data: dict):
        winner = data.get("winner")
        loser = data.get("losers")
        game = data.get("game")
        if not winner or not game:
            return
        async with async_session() as session:
            # Update winner stats
            result = await session.execute(select(Player).where(Player.name == winner))
            winner_player = result.scalar_one_or_none()
            if winner_player:
                game_wins = dict(winner_player.game_wins) if isinstance(winner_player.game_wins, dict) else {}
                game_wins[game] = game_wins.get(game, 0) + 1
                winner_player.wins += 1
                winner_player.game_wins = game_wins
            # Credit winner's wallet
            wallet_result = await session.execute(select(Wallet).where(Wallet.player_name == winner))
            winner_wallet = wallet_result.scalar_one_or_none()
            if winner_wallet is None:
                from core.db import Wallet as _WalletModel
                winner_wallet = _WalletModel(player_name=winner, balance=0)
                session.add(winner_wallet)
            winner_wallet.balance = (winner_wallet.balance or 0) + 10
            # Update loser stats
            if loser:
                result = await session.execute(select(Player).where(Player.name == loser))
                loser_player = result.scalar_one_or_none()
                if loser_player:
                    loser_player.losses += 1
            await session.commit()
            players = await _get_players_map()
            await sio.emit("updatePlayers", players)
