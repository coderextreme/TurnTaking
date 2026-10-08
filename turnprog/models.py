"""
Data models and core definitions for turn progression in multi-client multi-server games.
"""

from __future__ import annotations
import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


class ProgressionType(str, enum.Enum):
    PREDEFINED = "predefined"          # Fixed cyclical order, gap closure on drop
    VARIABLE = "variable"              # Order altered dynamically by Power Plays
    ROUND_ORDER = "round_order"        # Order recalculated between rounds (score/rank/autocratic)
    SNATCH = "snatch"                  # Simultaneous: exactly 1 move per player per contest (first/last wins)
    LIMITED = "limited"                # Simultaneous: up to N moves within time/action budget (e.g. auction/betting)
    CONTINUOUS = "continuous"          # Simultaneous: unlimited moves, dynamic join/leave, goal races
    HYBRID = "hybrid"                  # Combined sequential + simultaneous contest interrupts


class PowerPlayType(str, enum.Enum):
    ADD_MOVES = "add_moves"            # Grant extra moves to a player's turn
    TAKE_MOVES = "take_moves"          # Deduct moves from a player's turn
    REVERSE_ORDER = "reverse_order"    # Invert the progression sequence
    SKIP_PLAYER = "skip_player"        # Skip the next player (or target player)
    CANCEL_POWER_PLAY = "cancel_power_play"  # Nullify a preceding power play
    SWAP_ORDER = "swap_order"          # Swap position of two players in progression


class ContestType(str, enum.Enum):
    SNATCH = "snatch"
    LIMITED = "limited"
    CONTINUOUS = "continuous"


class PlayerState(str, enum.Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    SKIPPED = "skipped"
    DISCONNECTED = "disconnected"
    ELIMINATED = "eliminated"
    WON = "won"


class BufferState(str, enum.Enum):
    """Three-state message buffer as formulated in Carlson (1986)."""
    READY_FOR_MESSAGE = "ready_for_message"  # Idle, waiting for new packet
    PARTIAL_MESSAGE = "partial_message"      # Incomplete data stream, accumulating
    COMPLETE_MESSAGE = "complete_message"    # Full frame ready for processing


class MessageType(str, enum.Enum):
    # Handshake & Lifecycle
    CLIENT_JOIN = "client_join"
    CLIENT_LEAVE = "client_leave"
    HEARTBEAT = "heartbeat"
    ACK = "ack"
    ERROR = "error"

    # Game Master Flow
    PROMPT_TURN = "prompt_turn"
    SUBMIT_MOVE = "submit_move"
    SUBMIT_POWER_PLAY = "submit_power_play"
    MOVE_CONFIRMED = "move_confirmed"

    # Simultaneous Contests
    CONTEST_START = "contest_start"
    CONTEST_ACTION = "contest_action"
    CONTEST_END = "contest_end"

    # Multi-Server Replication
    STATE_SYNC = "state_sync"
    LEADER_HEARTBEAT = "leader_heartbeat"
    FAILOVER_ALERT = "failover_alert"


@dataclass
class Player:
    player_id: str
    name: str
    endpoint: str = ""
    state: PlayerState = PlayerState.ACTIVE
    score: int = 0
    moves_left_in_turn: int = 1
    skipped_rounds: int = 0
    connected_server_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "state": self.state.value,
            "score": self.score,
            "moves_left_in_turn": self.moves_left_in_turn,
            "skipped_rounds": self.skipped_rounds,
            "connected_server_id": self.connected_server_id,
            "metadata": self.metadata,
            "last_heartbeat": self.last_heartbeat,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Player:
        p = cls(
            player_id=data["player_id"],
            name=data["name"],
            endpoint=data.get("endpoint", ""),
            state=PlayerState(data.get("state", PlayerState.ACTIVE.value)),
            score=data.get("score", 0),
            moves_left_in_turn=data.get("moves_left_in_turn", 1),
            skipped_rounds=data.get("skipped_rounds", 0),
            connected_server_id=data.get("connected_server_id", ""),
            metadata=data.get("metadata", {}),
            last_heartbeat=data.get("last_heartbeat", time.time()),
        )
        return p


@dataclass
class Move:
    move_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    player_id: str = ""
    action: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    round_number: int = 1
    contest_id: Optional[str] = None
    server_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "move_id": self.move_id,
            "player_id": self.player_id,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "round_number": self.round_number,
            "contest_id": self.contest_id,
            "server_timestamp": self.server_timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Move:
        return cls(
            move_id=data.get("move_id", str(uuid.uuid4())[:8]),
            player_id=data.get("player_id", ""),
            action=data.get("action", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            round_number=data.get("round_number", 1),
            contest_id=data.get("contest_id"),
            server_timestamp=data.get("server_timestamp", time.time()),
        )


@dataclass
class PowerPlay:
    power_play_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    player_id: str = ""
    play_type: PowerPlayType = PowerPlayType.SKIP_PLAYER
    target_player_id: Optional[str] = None
    magnitude: int = 1  # e.g., number of extra moves or skip rounds
    applied: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power_play_id": self.power_play_id,
            "player_id": self.player_id,
            "play_type": self.play_type.value,
            "target_player_id": self.target_player_id,
            "magnitude": self.magnitude,
            "applied": self.applied,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PowerPlay:
        return cls(
            power_play_id=data.get("power_play_id", str(uuid.uuid4())[:8]),
            player_id=data.get("player_id", ""),
            play_type=PowerPlayType(data.get("play_type", PowerPlayType.SKIP_PLAYER.value)),
            target_player_id=data.get("target_player_id"),
            magnitude=data.get("magnitude", 1),
            applied=data.get("applied", False),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class Contest:
    """A contest unit representing a simultaneous progression segment."""
    contest_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    contest_type: ContestType = ContestType.SNATCH
    description: str = ""
    eligible_player_ids: List[str] = field(default_factory=list)
    moves_by_player: Dict[str, List[Move]] = field(default_factory=dict)
    max_moves_per_player: Optional[int] = 1   # None = unlimited (continuous), 1 = snatch, N = limited
    time_limit_sec: Optional[float] = 10.0
    require_all_players_to_act: bool = False  # e.g. snatch pass requirement
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    resolved: bool = False
    winner_player_id: Optional[str] = None
    winning_order: List[str] = field(default_factory=list)
    losing_order: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contest_id": self.contest_id,
            "contest_type": self.contest_type.value,
            "description": self.description,
            "eligible_player_ids": self.eligible_player_ids,
            "moves_by_player": {
                pid: [m.to_dict() for m in moves]
                for pid, moves in self.moves_by_player.items()
            },
            "max_moves_per_player": self.max_moves_per_player,
            "time_limit_sec": self.time_limit_sec,
            "require_all_players_to_act": self.require_all_players_to_act,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "resolved": self.resolved,
            "winner_player_id": self.winner_player_id,
            "winning_order": self.winning_order,
            "losing_order": self.losing_order,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Contest:
        c = cls(
            contest_id=data.get("contest_id", str(uuid.uuid4())[:8]),
            contest_type=ContestType(data.get("contest_type", ContestType.SNATCH.value)),
            description=data.get("description", ""),
            eligible_player_ids=data.get("eligible_player_ids", []),
            max_moves_per_player=data.get("max_moves_per_player", 1),
            time_limit_sec=data.get("time_limit_sec", 10.0),
            require_all_players_to_act=data.get("require_all_players_to_act", False),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            resolved=data.get("resolved", False),
            winner_player_id=data.get("winner_player_id"),
            winning_order=data.get("winning_order", []),
            losing_order=data.get("losing_order", []),
            metadata=data.get("metadata", {}),
        )
        moves_data = data.get("moves_by_player", {})
        for pid, mlist in moves_data.items():
            c.moves_by_player[pid] = [Move.from_dict(m) for m in mlist]
        return c


@dataclass
class GameState:
    game_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    progression_type: ProgressionType = ProgressionType.PREDEFINED
    round_number: int = 1
    turn_index: int = 0
    player_order: List[str] = field(default_factory=list)
    players: Dict[str, Player] = field(default_factory=dict)
    active_contest: Optional[Contest] = None
    move_history: List[Move] = field(default_factory=list)
    power_play_history: List[PowerPlay] = field(default_factory=list)
    game_over: bool = False
    state_version: int = 0
    leader_server_id: str = ""
    updated_at: float = field(default_factory=time.time)

    def current_player_id(self) -> Optional[str]:
        if not self.player_order:
            return None
        valid_order = [p for p in self.player_order if p in self.players and self.players[p].state == PlayerState.ACTIVE]
        if not valid_order:
            return None
        idx = self.turn_index % len(valid_order)
        return valid_order[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "progression_type": self.progression_type.value,
            "round_number": self.round_number,
            "turn_index": self.turn_index,
            "player_order": self.player_order,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "active_contest": self.active_contest.to_dict() if self.active_contest else None,
            "move_history": [m.to_dict() for m in self.move_history[-50:]],  # keep recent
            "power_play_history": [pp.to_dict() for pp in self.power_play_history[-20:]],
            "game_over": self.game_over,
            "state_version": self.state_version,
            "leader_server_id": self.leader_server_id,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GameState:
        gs = cls(
            game_id=data.get("game_id", str(uuid.uuid4())[:8]),
            progression_type=ProgressionType(data.get("progression_type", ProgressionType.PREDEFINED.value)),
            round_number=data.get("round_number", 1),
            turn_index=data.get("turn_index", 0),
            player_order=data.get("player_order", []),
            game_over=data.get("game_over", False),
            state_version=data.get("state_version", 0),
            leader_server_id=data.get("leader_server_id", ""),
            updated_at=data.get("updated_at", time.time()),
        )
        for pid, pdata in data.get("players", {}).items():
            gs.players[pid] = Player.from_dict(pdata)
        if data.get("active_contest"):
            gs.active_contest = Contest.from_dict(data["active_contest"])
        for mdata in data.get("move_history", []):
            gs.move_history.append(Move.from_dict(mdata))
        for pdata in data.get("power_play_history", []):
            gs.power_play_history.append(PowerPlay.from_dict(pdata))
        return gs


@dataclass
class Message:
    msg_type: MessageType
    sender_id: str
    target_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    sequence_num: int = 0
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_type": self.msg_type.value,
            "sender_id": self.sender_id,
            "target_id": self.target_id,
            "payload": self.payload,
            "sequence_num": self.sequence_num,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        return cls(
            msg_type=MessageType(data["msg_type"]),
            sender_id=data["sender_id"],
            target_id=data.get("target_id"),
            payload=data.get("payload", {}),
            sequence_num=data.get("sequence_num", 0),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())[:8]),
        )
