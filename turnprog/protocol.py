"""
Wire protocol and network envelope for multi-client multi-server messaging.
"""

from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .models import Message, MessageType


@dataclass
class Envelope:
    """Network envelope wrapper containing routing metadata and wire framing."""
    version: str = "1.0"
    cluster_id: str = "default-cluster"
    server_id: str = ""
    client_id: str = ""
    message: Message = field(default_factory=lambda: Message(MessageType.HEARTBEAT, "anonymous"))
    server_time: float = field(default_factory=time.time)

    def serialize(self) -> bytes:
        payload = {
            "version": self.version,
            "cluster_id": self.cluster_id,
            "server_id": self.server_id,
            "client_id": self.client_id,
            "message": self.message.to_dict(),
            "server_time": self.server_time,
        }
        # Delimited by newline for line-based streaming framed protocol
        return json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"

    @classmethod
    def deserialize(cls, data: bytes) -> Envelope:
        obj = json.loads(data.decode("utf-8").strip())
        msg = Message.from_dict(obj["message"])
        return cls(
            version=obj.get("version", "1.0"),
            cluster_id=obj.get("cluster_id", "default-cluster"),
            server_id=obj.get("server_id", ""),
            client_id=obj.get("client_id", ""),
            message=msg,
            server_time=obj.get("server_time", time.time()),
        )


class WireProtocol:
    """Helper utilities for standard protocol messages."""

    @staticmethod
    def prompt_turn(current_player_id: str, timeout_sec: float, round_num: int, moves_allowed: int = 1) -> Message:
        return Message(
            msg_type=MessageType.PROMPT_TURN,
            sender_id="game_master",
            target_id=current_player_id,
            payload={
                "current_player_id": current_player_id,
                "timeout_sec": timeout_sec,
                "round_number": round_num,
                "moves_allowed": moves_allowed,
            },
        )

    @staticmethod
    def contest_prompt(contest_id: str, contest_type: str, time_limit: Optional[float], max_moves: Optional[int], description: str) -> Message:
        return Message(
            msg_type=MessageType.CONTEST_START,
            sender_id="game_master",
            payload={
                "contest_id": contest_id,
                "contest_type": contest_type,
                "time_limit": time_limit,
                "max_moves": max_moves,
                "description": description,
            },
        )

    @staticmethod
    def state_sync(state_dict: Dict[str, Any], server_id: str) -> Message:
        return Message(
            msg_type=MessageType.STATE_SYNC,
            sender_id=server_id,
            payload=state_dict,
        )

    @staticmethod
    def ack(sender_id: str, correlation_id: str, status: str = "ok", details: Optional[Dict[str, Any]] = None) -> Message:
        return Message(
            msg_type=MessageType.ACK,
            sender_id=sender_id,
            correlation_id=correlation_id,
            payload={"status": status, "details": details or {}},
        )

    @staticmethod
    def error(sender_id: str, message: str, correlation_id: Optional[str] = None) -> Message:
        return Message(
            msg_type=MessageType.ERROR,
            sender_id=sender_id,
            correlation_id=correlation_id or str(uuid.uuid4())[:8],
            payload={"error": message},
        )
