"""
Game Master engine implementing the generic Game Master loop from Carlson (1986).
Coordinates progression engines, player message buffers, timers, and broadcast output.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    BufferState,
    Contest,
    GameState,
    Message,
    MessageType,
    Move,
    Player,
    PlayerState,
    PowerPlay,
    ProgressionType,
)
from .buffers import MessageFramingBuffer
from .protocol import WireProtocol
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

logger = logging.getLogger("turnprog.game_master")


class GameMaster:
    """
    Authoritative Game Master coordinating player progression,
    three-state message framing buffers, and game lifecycle.
    """

    def __init__(
        self,
        server_id: str = "master-node-01",
        progression_engine: Optional[BaseProgression] = None,
        turn_timeout_sec: float = 15.0,
        cluster_id: str = "default-cluster",
    ):
        self.server_id = server_id
        self.cluster_id = cluster_id
        self.turn_timeout_sec = turn_timeout_sec
        self.state = GameState(leader_server_id=server_id)

        # Progression engine
        self.progression: BaseProgression = progression_engine or PredefinedProgression(turn_timeout_sec)
        self._update_progression_type_metadata()

        # Three-state player buffers (Carlson 1986)
        self.player_buffers: Dict[str, MessageFramingBuffer] = {}

        # Broadcast output listeners (e.g. websockets, sockets, event busses)
        self._output_listeners: List[Callable[[Message], Any]] = []

        # Replication callbacks for multi-server synchronization
        self._replication_callbacks: List[Callable[[GameState], Any]] = []

        # Turn timer tracking
        self.turn_start_timestamp: float = time.time()
        self.is_running: bool = False
        self._lock = asyncio.Lock()

    def _update_progression_type_metadata(self) -> None:
        if isinstance(self.progression, PredefinedProgression):
            self.state.progression_type = ProgressionType.PREDEFINED
        elif isinstance(self.progression, VariableProgression):
            self.state.progression_type = ProgressionType.VARIABLE
        elif isinstance(self.progression, RoundOrderProgression):
            self.state.progression_type = ProgressionType.ROUND_ORDER
        elif isinstance(self.progression, SnatchProgression):
            self.state.progression_type = ProgressionType.SNATCH
        elif isinstance(self.progression, LimitedProgression):
            self.state.progression_type = ProgressionType.LIMITED
        elif isinstance(self.progression, ContinuousProgression):
            self.state.progression_type = ProgressionType.CONTINUOUS
        elif isinstance(self.progression, HybridProgression):
            self.state.progression_type = ProgressionType.HYBRID

    def set_progression_engine(self, engine: BaseProgression) -> None:
        """Dynamically switch progression model (e.g. during game phases or demonstration)."""
        self.progression = engine
        self._update_progression_type_metadata()
        self.notify_state_change()

    def add_output_listener(self, listener: Callable[[Message], Any]) -> None:
        self._output_listeners.append(listener)

    def add_replication_callback(self, callback: Callable[[GameState], Any]) -> None:
        self._replication_callbacks.append(callback)

    def register_player(self, player_id: str, name: str, endpoint: str = "") -> Player:
        """
        Registers a player. Creates their 3-state message buffer
        and updates progression order.
        """
        player = Player(
            player_id=player_id,
            name=name,
            endpoint=endpoint,
            state=PlayerState.ACTIVE,
            connected_server_id=self.server_id,
        )
        self.state.players[player_id] = player
        if player_id not in self.state.player_order:
            self.state.player_order.append(player_id)

        self.player_buffers[player_id] = MessageFramingBuffer(player_id)
        self.progression.handle_player_join(self.state, player)

        logger.info(f"Player registered: {player_id} ({name}) on {self.server_id}")
        self.notify_state_change()
        return player

    def terminate_player(self, player_id: str, reason: str = "quit") -> None:
        """
        Handles player termination (Carlson 1986):
        - Quitting / Losing / I/O failure
        - Buffer flushing
        - Gap closure in progression order
        """
        if player_id not in self.state.players:
            return

        logger.info(f"Terminating player {player_id} due to {reason}")

        # Flush buffers upon termination
        if player_id in self.player_buffers:
            self.player_buffers[player_id].flush_and_reset()

        # Engine handles gap closure
        self.progression.handle_player_quit(self.state, player_id)

        # Broadcast notice
        msg = Message(
            msg_type=MessageType.CLIENT_LEAVE,
            sender_id="game_master",
            payload={"player_id": player_id, "reason": reason},
        )
        self.broadcast(msg)
        self.notify_state_change()

    def receive_player_bytes(self, player_id: str, raw_chunk: bytes) -> List[Message]:
        """
        Receives raw network stream bytes from a player,
        transitions the 3-state buffer (READY -> PARTIAL -> COMPLETE),
        and returns any newly completed messages.
        """
        if player_id not in self.player_buffers:
            self.player_buffers[player_id] = MessageFramingBuffer(player_id)

        buffer = self.player_buffers[player_id]
        completed = buffer.feed_bytes(raw_chunk)
        return completed

    # =========================================================================
    # CARSON'S 8-STEP GENERIC GAME MASTER LOOP STEP IMPLEMENTATIONS
    # =========================================================================

    def step1_decide_next_players(self) -> List[str]:
        """Step 1: Decide which player(s) are next."""
        return self.progression.get_eligible_players(self.state)

    def step2_prompt_players(self, eligible_players: List[str]) -> None:
        """Step 2: Prompt the player(s) if necessary."""
        if not eligible_players:
            return

        if self.state.active_contest and not self.state.active_contest.resolved:
            contest = self.state.active_contest
            prompt = WireProtocol.contest_prompt(
                contest_id=contest.contest_id,
                contest_type=contest.contest_type.value,
                time_limit=contest.time_limit_sec,
                max_moves=contest.max_moves_per_player,
                description=contest.description,
            )
            self.broadcast(prompt)
        else:
            for pid in eligible_players:
                p = self.state.players.get(pid)
                moves_left = p.moves_left_in_turn if p else 1
                msg = WireProtocol.prompt_turn(
                    current_player_id=pid,
                    timeout_sec=self.turn_timeout_sec,
                    round_num=self.state.round_number,
                    moves_allowed=moves_left,
                )
                self.send_to_player(pid, msg)

    def step4_get_player_input(self, player_id: str) -> Optional[Message]:
        """
        Step 4: Get player's input from buffer.
        Carlson 1986: Checks if message is complete.
        """
        buffer = self.player_buffers.get(player_id)
        if not buffer:
            return None
        return buffer.pop_message()

    def step5_process_input(self, message: Message) -> Tuple[bool, str]:
        """Step 5: Process the input according to message type."""
        pid = message.sender_id

        if message.msg_type == MessageType.SUBMIT_MOVE:
            move = Move(
                player_id=pid,
                action=message.payload.get("action", "move"),
                payload=message.payload.get("details", {}),
            )
            success, note = self.progression.process_move(self.state, move)
            if success:
                self.turn_start_timestamp = time.time()
                self.notify_state_change()
            return success, note

        elif message.msg_type == MessageType.SUBMIT_POWER_PLAY:
            if isinstance(self.progression, VariableProgression):
                pp = PowerPlay(
                    player_id=pid,
                    play_type=message.payload.get("play_type"),
                    target_player_id=message.payload.get("target_player_id"),
                    magnitude=message.payload.get("magnitude", 1),
                )
                success, note = self.progression.apply_power_play(self.state, pp)
                if success:
                    self.notify_state_change()
                return success, note
            return False, "Power plays only active in Variable Progression mode."

        elif message.msg_type == MessageType.CONTEST_ACTION:
            move = Move(
                player_id=pid,
                action=message.payload.get("action", "snatch"),
                payload=message.payload.get("details", {}),
            )
            success, note = self.progression.process_move(self.state, move)
            if success:
                self.notify_state_change()
            return success, note

        elif message.msg_type == MessageType.HEARTBEAT:
            if pid in self.state.players:
                self.state.players[pid].last_heartbeat = time.time()
            return True, "Heartbeat acknowledged"

        return False, f"Unhandled message type: {message.msg_type}"

    def step7_output_to_players(self, result_msg: Message) -> None:
        """Step 7: Output to all players."""
        self.broadcast(result_msg)

    # Output dispatch helpers
    def send_to_player(self, player_id: str, msg: Message) -> None:
        msg.target_id = player_id
        if player_id in self.player_buffers:
            self.player_buffers[player_id].enqueue_outbound(msg)
        for listener in self._output_listeners:
            try:
                listener(msg)
            except Exception as e:
                logger.error(f"Error in output listener: {e}")

    def broadcast(self, msg: Message) -> None:
        for pid in self.state.players:
            if pid in self.player_buffers:
                self.player_buffers[pid].enqueue_outbound(msg)
        for listener in self._output_listeners:
            try:
                listener(msg)
            except Exception as e:
                logger.error(f"Error in output listener: {e}")

    def notify_state_change(self) -> None:
        """Increments state version and triggers cluster replication."""
        self.state.state_version += 1
        self.state.updated_at = time.time()
        for callback in self._replication_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"Error in replication callback: {e}")

    def check_turn_timeout(self) -> bool:
        """Checks if current player has exceeded turn time limit."""
        if not self.turn_timeout_sec:
            return False

        curr_id = self.state.current_player_id()
        if not curr_id:
            return False

        elapsed = time.time() - self.turn_start_timestamp
        if elapsed > self.turn_timeout_sec:
            logger.warning(f"Player {curr_id} turn timed out ({elapsed:.1f}s > {self.turn_timeout_sec}s)")
            self.progression.handle_player_timeout(self.state, curr_id)
            self.turn_start_timestamp = time.time()
            self.broadcast(Message(
                msg_type=MessageType.ERROR,
                sender_id="game_master",
                payload={"error": f"Player {curr_id} timed out. Turn skipped."},
            ))
            self.notify_state_change()
            return True
        return False
