"""
Player client SDK for multi-client game participation.
Handles connection to cluster, local turn state, message buffering,
move submission, power plays, and snatch contest actions.
"""

from __future__ import annotations
import collections
import logging
import time
import uuid
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from .models import (
    GameState,
    Message,
    MessageType,
    Move,
    Player,
    PlayerState,
    PowerPlay,
    PowerPlayType,
)
from .protocol import WireProtocol

logger = logging.getLogger("turnprog.client")


class PlayerClient:
    """
    Client representing a player in a multi-client multi-server game.
    """

    def __init__(
        self,
        player_id: str,
        name: str,
        preferred_server_id: str = "srv-1",
    ):
        self.player_id = player_id
        self.name = name
        self.connected_server_id = preferred_server_id
        self.inbox: Deque[Message] = collections.deque()
        self.outbox: Deque[Message] = collections.deque()
        self.is_my_turn: bool = False
        self.current_round: int = 1
        self.current_score: int = 0
        self.active_contest_id: Optional[str] = None
        self.last_sync_timestamp: float = time.time()
        self.event_callbacks: List[Callable[[Message], Any]] = []

    def on_message_received(self, callback: Callable[[Message], Any]) -> None:
        self.event_callbacks.append(callback)

    def receive_message(self, message: Message) -> None:
        """Processes an incoming message from the Game Master server."""
        self.inbox.append(message)

        if message.msg_type == MessageType.PROMPT_TURN:
            target = message.payload.get("current_player_id")
            if target == self.player_id:
                self.is_my_turn = True
            self.current_round = message.payload.get("round_number", self.current_round)

        elif message.msg_type == MessageType.CONTEST_START:
            self.active_contest_id = message.payload.get("contest_id")

        elif message.msg_type == MessageType.CONTEST_END:
            self.active_contest_id = None

        elif message.msg_type == MessageType.STATE_SYNC:
            state_data = message.payload
            if "players" in state_data and self.player_id in state_data["players"]:
                p_info = state_data["players"][self.player_id]
                self.current_score = p_info.get("score", self.current_score)
            self.last_sync_timestamp = time.time()

        for cb in self.event_callbacks:
            try:
                cb(message)
            except Exception as e:
                logger.error(f"Client {self.player_id} callback error: {e}")

    def prepare_move(self, action: str = "standard_action", points: int = 1, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Creates a Move message ready for network transmission."""
        msg = Message(
            msg_type=MessageType.SUBMIT_MOVE,
            sender_id=self.player_id,
            target_id=self.connected_server_id,
            payload={
                "action": action,
                "details": {
                    "points": points,
                    **(metadata or {}),
                },
            },
        )
        self.outbox.append(msg)
        self.is_my_turn = False
        return msg

    def prepare_power_play(
        self,
        play_type: PowerPlayType,
        target_player_id: Optional[str] = None,
        magnitude: int = 1,
    ) -> Message:
        """Prepares a variable progression Power Play."""
        msg = Message(
            msg_type=MessageType.SUBMIT_POWER_PLAY,
            sender_id=self.player_id,
            target_id=self.connected_server_id,
            payload={
                "play_type": play_type,
                "target_player_id": target_player_id,
                "magnitude": magnitude,
            },
        )
        self.outbox.append(msg)
        return msg

    def prepare_snatch_action(self, contest_id: Optional[str] = None, reaction_time_ms: int = 150) -> Message:
        """Prepares a simultaneous snatch buzz-in action."""
        cid = contest_id or self.active_contest_id or "contest"
        msg = Message(
            msg_type=MessageType.CONTEST_ACTION,
            sender_id=self.player_id,
            target_id=self.connected_server_id,
            payload={
                "contest_id": cid,
                "action": "snatch_claim",
                "details": {
                    "reaction_time_ms": reaction_time_ms,
                    "points": 5,
                },
            },
        )
        self.outbox.append(msg)
        return msg

    def send_heartbeat(self) -> Message:
        msg = Message(
            msg_type=MessageType.HEARTBEAT,
            sender_id=self.player_id,
            target_id=self.connected_server_id,
        )
        self.outbox.append(msg)
        return msg

    def flush_outbox(self) -> List[Message]:
        msgs = list(self.outbox)
        self.outbox.clear()
        return msgs
