"""
TurnProg: Python library for Player Progression in Multi-Client Multi-Server environments.
Based on the foundational game architecture paper by John Carlson (1986):
"Designing Multi-player Games: Player Progression and Interface".
"""

__version__ = "1.0.0"

from .models import (
    Player,
    PlayerState,
    Move,
    PowerPlay,
    PowerPlayType,
    Contest,
    ContestType,
    ProgressionType,
    GameState,
    Message,
    MessageType,
    BufferState,
)
from .buffers import MessageFramingBuffer
from .protocol import WireProtocol, Envelope
from .progression import (
    BaseProgression,
    PredefinedProgression,
    VariableProgression,
    RoundOrderProgression,
    SnatchProgression,
    LimitedProgression,
    ContinuousProgression,
    HybridProgression,
)
from .game_master import GameMaster
from .cluster import ServerNode, ClusterCoordinator, NodeRole
from .client import PlayerClient

__all__ = [
    "Player",
    "PlayerState",
    "Move",
    "PowerPlay",
    "PowerPlayType",
    "Contest",
    "ContestType",
    "ProgressionType",
    "GameState",
    "Message",
    "MessageType",
    "BufferState",
    "MessageFramingBuffer",
    "WireProtocol",
    "Envelope",
    "BaseProgression",
    "PredefinedProgression",
    "VariableProgression",
    "RoundOrderProgression",
    "SnatchProgression",
    "LimitedProgression",
    "ContinuousProgression",
    "HybridProgression",
    "GameMaster",
    "ServerNode",
    "ClusterCoordinator",
    "NodeRole",
    "PlayerClient",
]
