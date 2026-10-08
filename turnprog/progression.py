"""
Core Progression Engines based on John Carlson (1986):
'Designing Multi-player Games: Player Progression and Interface'.
"""

from __future__ import annotations
import abc
import time
from typing import Callable, Dict, List, Optional, Tuple
from .models import (
    Contest,
    ContestType,
    GameState,
    Move,
    Player,
    PlayerState,
    PowerPlay,
    PowerPlayType,
    ProgressionType,
)


class BaseProgression(abc.ABC):
    """Abstract base class for all player progression strategies."""

    def __init__(self, time_limit_sec: float = 15.0):
        self.time_limit_sec = time_limit_sec

    @abc.abstractmethod
    def get_eligible_players(self, state: GameState) -> List[str]:
        """Returns the list of player IDs currently eligible to make a move."""
        pass

    @abc.abstractmethod
    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        """
        Processes a player move, updates state, and advances turn/round according to progression rules.
        Returns (success, message).
        """
        pass

    def handle_player_timeout(self, state: GameState, player_id: str) -> None:
        """Default penalty for turn timeout: forfeit turn or lose points."""
        if player_id in state.players:
            state.players[player_id].score = max(0, state.players[player_id].score - 1)
        # Advance turn past timed out player
        self.advance_turn(state)

    def handle_player_quit(self, state: GameState, player_id: str) -> None:
        """
        Carlson (1986): When a player is removed from the ordering,
        the gap closes and the next player moves up one spot in the order.
        """
        if player_id in state.players:
            state.players[player_id].state = PlayerState.ELIMINATED

        if player_id in state.player_order:
            curr_idx = state.turn_index % max(1, len(state.player_order))
            idx = state.player_order.index(player_id)
            state.player_order.remove(player_id)

            # Adjust turn_index so current progression position isn't skipped
            if state.player_order:
                if idx < curr_idx:
                    state.turn_index = max(0, state.turn_index - 1)
                state.turn_index = state.turn_index % len(state.player_order)
            else:
                state.turn_index = 0

    def handle_player_join(self, state: GameState, player: Player) -> None:
        """Registers a new player into the game state and ordering."""
        state.players[player.player_id] = player
        if player.player_id not in state.player_order:
            state.player_order.append(player.player_id)

    @abc.abstractmethod
    def advance_turn(self, state: GameState) -> None:
        """Advances the internal progression pointer/round."""
        pass


# ============================================================================
# SEQUENTIAL PROGRESSIONS
# ============================================================================

class PredefinedProgression(BaseProgression):
    """
    Pre-defined Progression (Carlson 1986):
    - Fixed order established at the beginning.
    - Each player takes one move per turn.
    - Moves per round = active players.
    - Gap closes when a player loses or quits.
    - Lost turn causes a temporary 1-round skip.
    """

    def __init__(self, time_limit_sec: float = 15.0):
        super().__init__(time_limit_sec)

    def get_eligible_players(self, state: GameState) -> List[str]:
        curr = state.current_player_id()
        if not curr:
            return []
        player = state.players.get(curr)
        if player and player.state == PlayerState.ACTIVE:
            return [curr]
        return []

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        curr_id = state.current_player_id()
        if move.player_id != curr_id:
            return False, f"Not player {move.player_id}'s turn (current is {curr_id})"

        player = state.players[curr_id]
        move.round_number = state.round_number
        state.move_history.append(move)

        # Standard score increment or move execution
        points = move.payload.get("points", 1)
        player.score += points

        player.moves_left_in_turn -= 1
        if player.moves_left_in_turn <= 0:
            player.moves_left_in_turn = 1
            self.advance_turn(state)
            return True, f"Move accepted. Next player's turn."
        else:
            return True, f"Move accepted. {player.moves_left_in_turn} move(s) remaining this turn."

    def advance_turn(self, state: GameState) -> None:
        if not state.player_order:
            return

        old_index = state.turn_index
        state.turn_index = (state.turn_index + 1) % len(state.player_order)

        # Round completed if wrapped around
        if state.turn_index == 0 or state.turn_index <= old_index:
            state.round_number += 1

        # Check for skipped rounds
        curr_id = state.current_player_id()
        if curr_id and curr_id in state.players:
            p = state.players[curr_id]
            if p.skipped_rounds > 0:
                p.skipped_rounds -= 1
                # Skip to next player
                self.advance_turn(state)


class VariableProgression(BaseProgression):
    """
    Variable Player Progression (Carlson 1986):
    - Sequential progression modified by Power Plays.
    - Power plays can:
        * Add moves to a player's turn
        * Take away moves from next turn
        * Reverse player order
        * Skip players in progression
        * Cancel or modify previous power plays
    """

    def __init__(self, time_limit_sec: float = 15.0):
        super().__init__(time_limit_sec)
        self.direction = 1  # 1 = forward, -1 = reverse

    def get_eligible_players(self, state: GameState) -> List[str]:
        curr = state.current_player_id()
        return [curr] if curr else []

    def apply_power_play(self, state: GameState, power_play: PowerPlay) -> Tuple[bool, str]:
        state.power_play_history.append(power_play)

        if power_play.play_type == PowerPlayType.ADD_MOVES:
            curr_id = power_play.player_id
            if curr_id in state.players:
                state.players[curr_id].moves_left_in_turn += power_play.magnitude
                power_play.applied = True
                return True, f"Player {curr_id} gained {power_play.magnitude} extra move(s)."

        elif power_play.play_type == PowerPlayType.TAKE_MOVES:
            target_id = power_play.target_player_id or self._peek_next_player(state)
            if target_id in state.players:
                target = state.players[target_id]
                target.moves_left_in_turn = max(0, target.moves_left_in_turn - power_play.magnitude)
                power_play.applied = True
                return True, f"Player {target_id} lost {power_play.magnitude} move(s)."

        elif power_play.play_type == PowerPlayType.REVERSE_ORDER:
            # Reverse order of player progression
            self.direction *= -1
            state.player_order.reverse()
            # Recalculate index of current player to maintain turn integrity
            if power_play.player_id in state.player_order:
                state.turn_index = state.player_order.index(power_play.player_id)
            power_play.applied = True
            return True, "Player order reversed."

        elif power_play.play_type == PowerPlayType.SKIP_PLAYER:
            target_id = power_play.target_player_id or self._peek_next_player(state)
            if target_id in state.players:
                state.players[target_id].skipped_rounds += power_play.magnitude
                power_play.applied = True
                return True, f"Player {target_id} skipped for {power_play.magnitude} round(s)."

        elif power_play.play_type == PowerPlayType.SWAP_ORDER:
            target_id = power_play.target_player_id
            curr_id = power_play.player_id
            if target_id and curr_id in state.player_order and target_id in state.player_order:
                i1, i2 = state.player_order.index(curr_id), state.player_order.index(target_id)
                state.player_order[i1], state.player_order[i2] = state.player_order[i2], state.player_order[i1]
                state.turn_index = state.player_order.index(curr_id)
                power_play.applied = True
                return True, f"Swapped positions between {curr_id} and {target_id}."

        elif power_play.play_type == PowerPlayType.CANCEL_POWER_PLAY:
            # Check previous power play in history
            applied_plays = [p for p in state.power_play_history[:-1] if p.applied]
            if applied_plays:
                last_play = applied_plays[-1]
                # Revert effect
                if last_play.play_type == PowerPlayType.REVERSE_ORDER:
                    self.direction *= -1
                    state.player_order.reverse()
                    if power_play.player_id in state.player_order:
                        state.turn_index = state.player_order.index(power_play.player_id)
                elif last_play.play_type == PowerPlayType.SKIP_PLAYER and last_play.target_player_id in state.players:
                    state.players[last_play.target_player_id].skipped_rounds = 0
                power_play.applied = True
                return True, f"Cancelled power play: {last_play.play_type.value}."

        return False, "Power play could not be applied."

    def _peek_next_player(self, state: GameState) -> Optional[str]:
        if not state.player_order:
            return None
        next_idx = (state.turn_index + 1) % len(state.player_order)
        return state.player_order[next_idx]

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        curr_id = state.current_player_id()
        if move.player_id != curr_id:
            return False, f"Not player {move.player_id}'s turn (current is {curr_id})"

        player = state.players[curr_id]
        move.round_number = state.round_number
        state.move_history.append(move)

        points = move.payload.get("points", 1)
        player.score += points

        player.moves_left_in_turn -= 1
        if player.moves_left_in_turn <= 0:
            player.moves_left_in_turn = 1
            self.advance_turn(state)
            return True, f"Move accepted. Next player's turn."
        else:
            return True, f"Move accepted. {player.moves_left_in_turn} moves remaining this turn."

    def advance_turn(self, state: GameState) -> None:
        if not state.player_order:
            return
        old_idx = state.turn_index
        state.turn_index = (state.turn_index + 1) % len(state.player_order)
        if state.turn_index <= old_idx:
            state.round_number += 1

        curr_id = state.current_player_id()
        if curr_id and curr_id in state.players:
            p = state.players[curr_id]
            if p.skipped_rounds > 0:
                p.skipped_rounds -= 1
                self.advance_turn(state)


class RoundOrderProgression(BaseProgression):
    """
    Round-Order Progression (Carlson 1986):
    - Player order changes after every round.
    - Ordering modes:
        1. 'best_first': Winner of previous round goes first, followed by previous order
        2. 'score_desc': Sorted descending by cumulative game score
        3. 'score_asc': Sorted ascending (e.g. lowest score goes first, like golf honors)
        4. 'autocratic': Game Master custom rule/order decided every round
    """

    def __init__(self, mode: str = "best_first", autocratic_fn: Optional[Callable[[GameState], List[str]]] = None):
        super().__init__()
        self.mode = mode
        self.autocratic_fn = autocratic_fn
        self._round_moves_count = 0

    def get_eligible_players(self, state: GameState) -> List[str]:
        curr = state.current_player_id()
        return [curr] if curr else []

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        curr_id = state.current_player_id()
        if move.player_id != curr_id:
            return False, f"Not player {move.player_id}'s turn."

        player = state.players[curr_id]
        move.round_number = state.round_number
        state.move_history.append(move)

        player.score += move.payload.get("points", 1)
        self._round_moves_count += 1
        self.advance_turn(state)
        return True, "Move processed."

    def advance_turn(self, state: GameState) -> None:
        if not state.player_order:
            return
        state.turn_index += 1

        # Check if the round finished (every active player took a turn)
        active_count = len([p for p in state.player_order if state.players[p].state == PlayerState.ACTIVE])
        if state.turn_index >= active_count:
            # Round boundary reached! Recalculate order for next round
            self._recalculate_round_order(state)
            state.round_number += 1
            state.turn_index = 0
            self._round_moves_count = 0

    def _recalculate_round_order(self, state: GameState) -> None:
        active_players = [p for p in state.player_order if p in state.players and state.players[p].state == PlayerState.ACTIVE]
        if not active_players:
            return

        if self.mode == "score_desc":
            active_players.sort(key=lambda pid: state.players[pid].score, reverse=True)
            state.player_order = active_players
        elif self.mode == "score_asc":
            active_players.sort(key=lambda pid: state.players[pid].score)
            state.player_order = active_players
        elif self.mode == "best_first":
            # Highest scorer in the round moves to index 0, rest keep cyclical order
            best_player = max(active_players, key=lambda pid: state.players[pid].score)
            idx = active_players.index(best_player)
            state.player_order = active_players[idx:] + active_players[:idx]
        elif self.mode == "autocratic" and self.autocratic_fn:
            state.player_order = self.autocratic_fn(state)


# ============================================================================
# SIMULTANEOUS PROGRESSIONS
# ============================================================================

class SnatchProgression(BaseProgression):
    """
    Snatch Progression (Carlson 1986):
    - Simultaneous: Exactly 1 move per player per contest.
    - Used to claim unclaimed points, buzz-in, challenge a move, or slapjack.
    - Winner is first (or last) to make a move.
    - Time limit imposed.
    - Optional: require all players to act (e.g. Pass or Snatch).
    """

    def __init__(self, time_limit_sec: float = 8.0, first_to_move_wins: bool = True, require_all: bool = False):
        super().__init__(time_limit_sec)
        self.first_to_move_wins = first_to_move_wins
        self.require_all = require_all

    def create_contest(self, state: GameState, description: str = "Snatch contest") -> Contest:
        eligible = [pid for pid, p in state.players.items() if p.state == PlayerState.ACTIVE]
        contest = Contest(
            contest_type=ContestType.SNATCH,
            description=description,
            eligible_player_ids=eligible,
            max_moves_per_player=1,
            time_limit_sec=self.time_limit_sec,
            require_all_players_to_act=self.require_all,
            start_time=time.time(),
        )
        state.active_contest = contest
        return contest

    def get_eligible_players(self, state: GameState) -> List[str]:
        if not state.active_contest or state.active_contest.resolved:
            return []
        contest = state.active_contest
        # Eligible = anyone in contest who has not yet made their 1 move
        return [
            pid for pid in contest.eligible_player_ids
            if len(contest.moves_by_player.get(pid, [])) < 1
        ]

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        contest = state.active_contest
        if not contest or contest.resolved:
            return False, "No active contest to snatch."

        if move.player_id not in contest.eligible_player_ids:
            return False, f"Player {move.player_id} is not eligible for this snatch contest."

        player_moves = contest.moves_by_player.setdefault(move.player_id, [])
        if len(player_moves) >= 1:
            return False, f"Player {move.player_id} already made their 1 snatch move."

        move.contest_id = contest.contest_id
        move.server_timestamp = time.time()
        player_moves.append(move)
        state.move_history.append(move)

        if self.first_to_move_wins and not contest.winner_player_id:
            contest.winner_player_id = move.player_id
            contest.winning_order.append(move.player_id)
            state.players[move.player_id].score += move.payload.get("points", 5)

        # Check resolution
        eligible_count = len(contest.eligible_player_ids)
        moved_count = len(contest.moves_by_player)

        if not self.require_all and self.first_to_move_wins:
            # Immediate resolution on first snatch
            self.resolve_contest(state)
            return True, f"Snatch won by player {move.player_id}!"
        elif moved_count >= eligible_count:
            # All players moved
            self.resolve_contest(state)
            return True, f"All players acted. Contest resolved."

        return True, f"Snatch move registered for {move.player_id}."

    def resolve_contest(self, state: GameState) -> None:
        contest = state.active_contest
        if not contest or contest.resolved:
            return

        contest.resolved = True
        contest.end_time = time.time()

        # Gather moves sorted by server timestamp
        all_contest_moves: List[Move] = []
        for moves in contest.moves_by_player.values():
            all_contest_moves.extend(moves)
        all_contest_moves.sort(key=lambda m: m.server_timestamp)

        if all_contest_moves:
            if self.first_to_move_wins:
                contest.winner_player_id = all_contest_moves[0].player_id
                contest.winning_order = [m.player_id for m in all_contest_moves]
            else:
                contest.winner_player_id = all_contest_moves[-1].player_id
                contest.winning_order = [m.player_id for m in reversed(all_contest_moves)]

        # Those who did not move form losing order
        contest.losing_order = [
            pid for pid in contest.eligible_player_ids
            if pid not in contest.moves_by_player
        ]

    def advance_turn(self, state: GameState) -> None:
        if state.active_contest and not state.active_contest.resolved:
            self.resolve_contest(state)


class LimitedProgression(BaseProgression):
    """
    Limited Progression (Carlson 1986):
    - Simultaneous: Players can take several moves up to a limit or budget
      within a reasonable amount of time.
    - Examples: Auctions (bidding increments), casino betting (craps/roulette),
      stamina-pool combat rounds.
    """

    def __init__(self, max_moves_per_player: int = 5, time_limit_sec: float = 20.0):
        super().__init__(time_limit_sec)
        self.max_moves_per_player = max_moves_per_player

    def create_contest(self, state: GameState, description: str = "Auction / Limited Contest") -> Contest:
        eligible = [pid for pid, p in state.players.items() if p.state == PlayerState.ACTIVE]
        contest = Contest(
            contest_type=ContestType.LIMITED,
            description=description,
            eligible_player_ids=eligible,
            max_moves_per_player=self.max_moves_per_player,
            time_limit_sec=self.time_limit_sec,
            start_time=time.time(),
        )
        state.active_contest = contest
        return contest

    def get_eligible_players(self, state: GameState) -> List[str]:
        if not state.active_contest or state.active_contest.resolved:
            return []
        contest = state.active_contest
        return [
            pid for pid in contest.eligible_player_ids
            if len(contest.moves_by_player.get(pid, [])) < self.max_moves_per_player
        ]

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        contest = state.active_contest
        if not contest or contest.resolved:
            return False, "No active limited contest."

        player_moves = contest.moves_by_player.setdefault(move.player_id, [])
        if len(player_moves) >= self.max_moves_per_player:
            return False, f"Player {move.player_id} has exceeded move limit ({self.max_moves_per_player})."

        move.contest_id = contest.contest_id
        player_moves.append(move)
        state.move_history.append(move)

        points = move.payload.get("points", 1)
        state.players[move.player_id].score += points

        # Check if everyone used all allowed moves
        all_done = all(
            len(contest.moves_by_player.get(pid, [])) >= self.max_moves_per_player
            for pid in contest.eligible_player_ids
        )
        if all_done:
            self.resolve_contest(state)
            return True, "All players reached move limit. Contest resolved."

        return True, f"Move accepted for {move.player_id} ({len(player_moves)}/{self.max_moves_per_player})."

    def resolve_contest(self, state: GameState) -> None:
        contest = state.active_contest
        if not contest or contest.resolved:
            return
        contest.resolved = True
        contest.end_time = time.time()
        # Rank by total contest points/moves
        sorted_pids = sorted(
            contest.eligible_player_ids,
            key=lambda pid: sum(m.payload.get("points", 1) for m in contest.moves_by_player.get(pid, [])),
            reverse=True,
        )
        contest.winning_order = sorted_pids
        contest.winner_player_id = sorted_pids[0] if sorted_pids else None

    def advance_turn(self, state: GameState) -> None:
        self.resolve_contest(state)


class ContinuousProgression(BaseProgression):
    """
    Continuous Progression (Carlson 1986):
    - Simultaneous: Players take as many moves as they need/want.
    - Players may drop out or join whenever they want.
    - Definite goal: When a player reaches the goal, contest is over for that person.
    - Order reaching goal = winning order; failures = losing order.
    """

    def __init__(self, target_goal_score: int = 25, time_limit_sec: Optional[float] = 60.0):
        super().__init__(time_limit_sec or 60.0)
        self.target_goal_score = target_goal_score

    def create_contest(self, state: GameState, description: str = "Continuous Race") -> Contest:
        eligible = [pid for pid, p in state.players.items() if p.state == PlayerState.ACTIVE]
        contest = Contest(
            contest_type=ContestType.CONTINUOUS,
            description=description,
            eligible_player_ids=eligible,
            max_moves_per_player=None,  # unlimited
            time_limit_sec=self.time_limit_sec,
            start_time=time.time(),
        )
        state.active_contest = contest
        return contest

    def get_eligible_players(self, state: GameState) -> List[str]:
        if not state.active_contest or state.active_contest.resolved:
            return []
        contest = state.active_contest
        # Eligible players are active and haven't already crossed finish line
        return [
            pid for pid, p in state.players.items()
            if p.state == PlayerState.ACTIVE and pid not in contest.winning_order
        ]

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        contest = state.active_contest
        if not contest or contest.resolved:
            return False, "No active continuous contest."

        player = state.players.get(move.player_id)
        if not player or player.state != PlayerState.ACTIVE:
            return False, f"Player {move.player_id} is not active."

        if move.player_id in contest.winning_order:
            return False, f"Player {move.player_id} has already finished the contest."

        move.contest_id = contest.contest_id
        contest.moves_by_player.setdefault(move.player_id, []).append(move)
        state.move_history.append(move)

        points = move.payload.get("points", 1)
        player.score += points

        # Goal reached check
        if player.score >= self.target_goal_score:
            contest.winning_order.append(player.player_id)
            if not contest.winner_player_id:
                contest.winner_player_id = player.player_id

            # If all or majority finished, conclude
            if len(contest.winning_order) >= len(state.players):
                self.resolve_contest(state)
                return True, f"Player {player.player_id} completed goal! All players finished."
            return True, f"Goal achieved by {player.player_id}! Finish position: #{len(contest.winning_order)}."

        return True, f"Continuous move recorded for {player.player_id}. Score: {player.score}/{self.target_goal_score}."

    def resolve_contest(self, state: GameState) -> None:
        contest = state.active_contest
        if not contest or contest.resolved:
            return
        contest.resolved = True
        contest.end_time = time.time()
        contest.losing_order = [
            pid for pid in state.players
            if pid not in contest.winning_order and state.players[pid].state == PlayerState.ACTIVE
        ]

    def advance_turn(self, state: GameState) -> None:
        self.resolve_contest(state)


class HybridProgression(BaseProgression):
    """
    Hybrid Progression (Carlson 1986):
    - Blends sequential progression with simultaneous contest interrupts
      (e.g., Cribbage where play is sequential, but unclaimed points trigger snatch races).
    """

    def __init__(self, sequential_engine: BaseProgression, snatch_engine: SnatchProgression):
        super().__init__()
        self.sequential_engine = sequential_engine
        self.snatch_engine = snatch_engine
        self.in_interrupt_contest = False

    def trigger_snatch_interrupt(self, state: GameState, description: str = "Unclaimed points race!") -> Contest:
        self.in_interrupt_contest = True
        return self.snatch_engine.create_contest(state, description)

    def get_eligible_players(self, state: GameState) -> List[str]:
        if self.in_interrupt_contest and state.active_contest and not state.active_contest.resolved:
            return self.snatch_engine.get_eligible_players(state)
        return self.sequential_engine.get_eligible_players(state)

    def process_move(self, state: GameState, move: Move) -> Tuple[bool, str]:
        if self.in_interrupt_contest and state.active_contest and not state.active_contest.resolved:
            ok, msg = self.snatch_engine.process_move(state, move)
            if state.active_contest.resolved:
                self.in_interrupt_contest = False
            return ok, msg
        return self.sequential_engine.process_move(state, move)

    def advance_turn(self, state: GameState) -> None:
        if self.in_interrupt_contest:
            self.snatch_engine.advance_turn(state)
            self.in_interrupt_contest = False
        else:
            self.sequential_engine.advance_turn(state)
