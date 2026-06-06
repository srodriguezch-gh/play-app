"""Socket.io event handlers for real-time game communication."""

import asyncio
import logging
import uuid
from typing import Optional

import socketio

from core.db import Player, Session, Wallet, async_session
from core.game_manager import game_manager
from sqlalchemy import select

logger = logging.getLogger(__name__)

_sio: Optional[socketio.AsyncServer] = None

COOKIE_NAME = "play_session"


def _extract_player_from_environ(environ: dict) -> str | None:
    """Parse play_session cookie from WSGI environ and look up player name."""
    cookie_header = environ.get("HTTP_COOKIE", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{COOKIE_NAME}="):
            token = part[len(COOKIE_NAME) + 1:].strip()
            return _get_player_from_token_sync(token)
    return None


def _get_player_from_token_sync(token: str) -> str | None:
    """Blocking sync lookup for use in socketio connect handler."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_get_player_async(token))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Session lookup error: {e}")
        return None


async def _get_player_async(token: str) -> str | None:
    async with async_session() as session:
        result = await session.execute(select(Session).where(Session.token == token))
        sess = result.scalars().one_or_none()
        return sess.player_name if sess else None


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
        player = _extract_player_from_environ(environ)
        if player:
            game_manager.set_online(sid, player)
            logger.info(f"Client connected: {sid} as {player}")
        else:
            logger.warning(f"Client connected without valid session: {sid}")

    @sio.event
    async def disconnect(sid):
        player_name = game_manager.remove_online(sid)
        logger.info(f"Client disconnected: {sid} ({player_name})")
        await sio.emit("updateOnlineStatus", game_manager.get_online_status())

    @sio.event
    async def login(sid, player_name: str):
        authenticated = _extract_player_from_environ(
            _sio.get_context(sid).environ if hasattr(_sio, "get_context") else {}
        )
        if authenticated != player_name:
            logger.warning(f"Unauthorized login attempt: {player_name} != {authenticated}")
            return
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
        found = False
        for socket_id, name in game_manager.online_users.items():
            if name == opponent:
                await sio.emit("receiveChallenge", {"challenger": challenger, "game": game}, to=socket_id)
                found = True
                break
        if not found:
            logger.info(f"Challenge failed: {opponent} is not online")

    @sio.event
    async def acceptChallenge(sid, data: dict):
        challenger = data.get("challenger")
        opponent = data.get("opponent")
        game = data.get("game")

        caller = game_manager.online_users.get(sid)
        if caller != opponent:
            logger.warning(f"acceptChallenge rejected: {caller} attempted to accept challenge for {opponent}")
            return
        room_id = f"{game}_{challenger}_{opponent}_{uuid.uuid4().hex[:12]}"
        for socket_id, name in game_manager.online_users.items():
            if name == challenger:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": opponent, "game": game, "role": "X"}, to=socket_id)
            elif name == opponent:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": challenger, "game": game, "role": "O"}, to=socket_id)

    @sio.event
    async def joinRoom(sid, room_id: str):
        await sio.enter_room(sid, room_id)
        player = game_manager.online_users.get(sid)
        if player:
            game_obj = game_manager.get_game(room_id)
            if game_obj is not None:
                if not hasattr(game_obj, "_players") or game_obj._players is None:
                    game_obj._players = []
                if player not in game_obj._players:
                    game_obj._players.append(player)
        logger.info(f"Socket {sid} ({player}) joined room {room_id}")

    @sio.event
    async def makeMove(sid, data: dict):
        """Apply the move server-side, broadcast the new state, and trigger AI when needed."""
        room_id = data.get("roomId")
        move = data.get("move")
        move_type = data.get("type")
        game_type = data.get("game", "unknown")

        if move_type == "reset":
            if game_type == "chess":
                game_manager.reset_chess(room_id)
            elif game_type == "tictactoe":
                game_obj = game_manager.get_or_create_tictactoe(room_id)
                game_obj.tictactoe.reset()
            elif game_type == "connectfour":
                game_obj = game_manager.get_or_create_connectfour(room_id)
                game_obj.connectfour.reset()
            await sio.emit("gameReset", room=room_id)
            return

        response = {"move": move, "game": game_type}
        if game_type == "chess":
            chess_move = move
            if chess_move:
                game_obj = game_manager.get_or_create_chess(room_id)
                success = game_obj.chess.move(chess_move)
                if success:
                    response["fen"] = game_obj.chess.to_fen()
                    response["legal"] = game_obj.chess.get_legal_moves()
                    response["game_over"] = game_obj.chess.is_game_over()
                    response["winner"] = game_obj.chess.get_winner()
                else:
                    response["error"] = "Illegal move"
        elif game_type == "tictactoe":
            cell = move
            if cell is not None:
                game_obj = game_manager.get_or_create_tictactoe(room_id)
                success = game_obj.tictactoe.move(int(cell), data.get("symbol"))
                if success:
                    response["board"] = game_obj.tictactoe.get_board()
                    response["game_over"] = game_obj.tictactoe.is_game_over()
                    response["winner"] = game_obj.tictactoe.get_winner()
                else:
                    response["error"] = "Illegal move"
        elif game_type == "connectfour":
            col = move
            if col is not None:
                game_obj = game_manager.get_or_create_connectfour(room_id)
                success = game_obj.connectfour.move(int(col), data.get("symbol"))
                if success:
                    response["board"] = game_obj.connectfour.get_board()
                    response["game_over"] = game_obj.connectfour.is_game_over()
                    response["winner"] = game_obj.connectfour.get_winner()
                else:
                    response["error"] = "Illegal move"

        await sio.emit("moveMade", response, room=room_id)

        if game_type == "chess" and ("solo" in room_id or "Calypso" in room_id or "Traka" in room_id):
            fen = response.get("fen")
            if fen:
                bot_name = "Calypso" if "Calypso" in room_id else "Traka"
                from core.calypso import bot_service
                bot_service.request_chess_move(bot_name, fen, lambda result, rid=room_id: _safe_handle_ai_response(rid, result))

    def _safe_handle_ai_response(room_id: str, result: dict):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_handle_ai_response(room_id, result))
        except RuntimeError:
            asyncio.run(_handle_ai_response_async(room_id, result))
        except Exception as e:
            logger.error(f"AI response handler error: {e}")

    async def _handle_ai_response(room_id: str, result: dict):
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
                    await sio.emit("moveMade", {"move": ai_move_str, "fen": board.fen()}, room=room_id)
        except Exception as e:
            logger.error(f"AI move error: {e}")

    async def _handle_ai_response_async(room_id: str, result: dict):
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
                    await sio.emit("moveMade", {"move": ai_move_str, "fen": board.fen()}, room=room_id)
        except Exception as e:
            logger.error(f"AI move error: {e}")

    @sio.event
    async def gameEnd(sid, data: dict):
        winner = data.get("winner")
        loser = data.get("loser")
        game = data.get("game")
        room_id = data.get("roomId")

        if not winner or not game or str(winner).lower() == "draw":
            return

        caller = game_manager.online_users.get(sid)
        if caller and caller != winner:
            logger.warning(f"gameEnd rejected: caller {caller} claimed winner {winner} in room {room_id}")
            return

        if room_id:
            game_obj = game_manager.get_game(room_id)
            if game_obj:
                players_in_room = getattr(game_obj, "_players", None)
                if players_in_room is not None and winner not in players_in_room:
                    logger.warning(f"gameEnd rejected: {winner} not tracked in room {room_id}")
                    return

        async with async_session() as session:
            result = await session.execute(select(Player).where(Player.name == winner))
            winner_player = result.scalars().one_or_none()
            if not winner_player:
                return

            game_wins = dict(winner_player.game_wins) if isinstance(winner_player.game_wins, dict) else {}
            game_wins[game] = game_wins.get(game, 0) + 1
            winner_player.wins += 1
            winner_player.game_wins = game_wins

            wallet_result = await session.execute(select(Wallet).where(Wallet.player_name == winner))
            winner_wallet = wallet_result.scalars().one_or_none()
            if winner_wallet is None:
                winner_wallet = Wallet(player_name=winner, balance=0)
                session.add(winner_wallet)
            winner_wallet.balance = (winner_wallet.balance or 0) + 10

            if loser:
                result = await session.execute(select(Player).where(Player.name == loser))
                loser_player = result.scalars().one_or_none()
                if loser_player:
                    loser_player.losses += 1

            await session.commit()
            players = await _get_players_map()
            await sio.emit("updatePlayers", players)

        # Brain sync: save game result
        from services.brain_sync import save_game_result
        await save_game_result(winner, game or "unknown", winner, loser or "unknown", room_id or "")
