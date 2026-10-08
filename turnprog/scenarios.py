"""
Ready-to-run scenarios showcasing all progression methods from Carlson (1986)
and multi-server fault tolerance.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List

from .models import (
    PowerPlayType,
    ProgressionType,
)
from .progression import (
    PredefinedProgression,
    VariableProgression,
    RoundOrderProgression,
    SnatchProgression,
    LimitedProgression,
    ContinuousProgression,
    HybridProgression,
)
from .game_master import GameMaster
from .cluster import ClusterCoordinator, NodeRole
from .client import PlayerClient


def run_predefined_scenario() -> Dict[str, Any]:
    """Demonstrates Pre-defined Sequential progression with gap closure."""
    gm = GameMaster(server_id="srv-master")
    gm.set_progression_engine(PredefinedProgression())

    p_alice = gm.register_player("p1", "Alice")
    p_bob = gm.register_player("p2", "Bob")
    p_carol = gm.register_player("p3", "Carol")
    p_dave = gm.register_player("p4", "Dave")

    log = []
    log.append(f"Initial order: {list(gm.state.player_order)}")

    # Round 1: Alice moves
    c_alice = PlayerClient("p1", "Alice")
    move1 = c_alice.prepare_move("play_card", points=10)
    gm.step5_process_input(move1)
    log.append(f"Alice moved. Next player: {gm.state.current_player_id()} (Round {gm.state.round_number})")

    # Bob moves
    c_bob = PlayerClient("p2", "Bob")
    move2 = c_bob.prepare_move("play_card", points=15)
    gm.step5_process_input(move2)
    log.append(f"Bob moved. Next player: {gm.state.current_player_id()}")

    # Dave quits before his turn; Carlson: gap closes immediately
    log.append("Dave abruptly disconnects / quits game.")
    gm.terminate_player("p4", reason="client_quit")
    log.append(f"Order after Dave quit (gap closed): {list(gm.state.player_order)}")
    log.append(f"Next player is now: {gm.state.current_player_id()}")

    # Carol moves
    c_carol = PlayerClient("p3", "Carol")
    move3 = c_carol.prepare_move("play_card", points=20)
    gm.step5_process_input(move3)
    log.append(f"Carol moved. Next player wraps to: {gm.state.current_player_id()} (Round {gm.state.round_number})")

    return {
        "scenario": "Predefined Sequential Progression",
        "description": "Cyclical turn-taking with seamless gap closure upon player quit.",
        "final_state": gm.state.to_dict(),
        "log": log,
    }


def run_variable_scenario() -> Dict[str, Any]:
    """Demonstrates Variable Progression with Power Plays (Reverse, Skip, Add moves, Cancel)."""
    gm = GameMaster(server_id="srv-master")
    engine = VariableProgression()
    gm.set_progression_engine(engine)

    gm.register_player("p1", "Alice")
    gm.register_player("p2", "Bob")
    gm.register_player("p3", "Carol")
    gm.register_player("p4", "Dave")

    log = []
    log.append(f"Initial order: {list(gm.state.player_order)}")

    c_alice = PlayerClient("p1", "Alice")
    c_bob = PlayerClient("p2", "Bob")
    c_carol = PlayerClient("p3", "Carol")

    # Alice plays REVERSE_ORDER power play
    pp_rev = c_alice.prepare_power_play(PowerPlayType.REVERSE_ORDER)
    gm.step5_process_input(pp_rev)
    log.append(f"Alice executed REVERSE_ORDER! New order: {list(gm.state.player_order)}")

    # Alice moves
    m_alice = c_alice.prepare_move("strike", points=5)
    gm.step5_process_input(m_alice)
    log.append(f"Alice finished turn. Next player in reversed order: {gm.state.current_player_id()}")

    # Dave is next due to reverse! Dave plays SKIP_PLAYER targeting Bob
    c_dave = PlayerClient("p4", "Dave")
    pp_skip = c_dave.prepare_power_play(PowerPlayType.SKIP_PLAYER, target_player_id="p2")
    gm.step5_process_input(pp_skip)
    m_dave = c_dave.prepare_move("strike", points=7)
    gm.step5_process_input(m_dave)
    log.append(f"Dave moved and skipped Bob! Next player: {gm.state.current_player_id()}")

    # Carol plays ADD_MOVES
    pp_add = c_carol.prepare_power_play(PowerPlayType.ADD_MOVES, magnitude=1)
    gm.step5_process_input(pp_add)
    log.append(f"Carol used ADD_MOVES! Moves left: {gm.state.players['p3'].moves_left_in_turn}")

    m_c1 = c_carol.prepare_move("strike_1", points=4)
    gm.step5_process_input(m_c1)
    log.append(f"Carol move 1 done. Still Carol's turn: {gm.state.current_player_id() == 'p3'}")

    m_c2 = c_carol.prepare_move("strike_2", points=6)
    gm.step5_process_input(m_c2)
    log.append(f"Carol move 2 done. Next player: {gm.state.current_player_id()} (Bob skipped!)")

    return {
        "scenario": "Variable Progression (Power Plays)",
        "description": "Dynamic turn order manipulation through stacked power plays.",
        "final_state": gm.state.to_dict(),
        "log": log,
    }


def run_round_order_scenario() -> Dict[str, Any]:
    """Demonstrates Round-Order Progression (Score-based re-ordering each round)."""
    gm = GameMaster(server_id="srv-master")
    engine = RoundOrderProgression(mode="score_desc")
    gm.set_progression_engine(engine)

    gm.register_player("p1", "Alice")
    gm.register_player("p2", "Bob")
    gm.register_player("p3", "Carol")

    log = []
    log.append(f"Round 1 initial order: {list(gm.state.player_order)}")

    # Alice scores 2
    m1 = PlayerClient("p1", "Alice").prepare_move("roll", points=2)
    gm.step5_process_input(m1)
    # Bob scores 10
    m2 = PlayerClient("p2", "Bob").prepare_move("roll", points=10)
    gm.step5_process_input(m2)
    # Carol scores 6
    m3 = PlayerClient("p3", "Carol").prepare_move("roll", points=6)
    gm.step5_process_input(m3)

    log.append(f"Round 1 completed. Scores: Alice={gm.state.players['p1'].score}, Bob={gm.state.players['p2'].score}, Carol={gm.state.players['p3'].score}")
    log.append(f"Round 2 new order (sorted by highest score): {list(gm.state.player_order)}")
    log.append(f"First player in Round 2: {gm.state.current_player_id()}")

    return {
        "scenario": "Round-Order Progression",
        "description": "Turn order dynamically recalculated each round based on competitive scores.",
        "final_state": gm.state.to_dict(),
        "log": log,
    }


def run_snatch_scenario() -> Dict[str, Any]:
    """Demonstrates Snatch Progression (Simultaneous 1-move contest, first-to-act wins)."""
    gm = GameMaster(server_id="srv-master")
    engine = SnatchProgression(time_limit_sec=5.0, first_to_move_wins=True)
    gm.set_progression_engine(engine)

    gm.register_player("p1", "Alice")
    gm.register_player("p2", "Bob")
    gm.register_player("p3", "Carol")

    contest = engine.create_contest(gm.state, "Bonus Point Snatch! (Cribbage / Buzzer style)")
    log = []
    log.append(f"Snatch contest started: {contest.description}")

    # Bob reacts at t=0.12s
    c_bob = PlayerClient("p2", "Bob")
    act_bob = c_bob.prepare_snatch_action(contest.contest_id, reaction_time_ms=120)
    ok_b, msg_b = gm.step5_process_input(act_bob)
    log.append(f"Bob submitted snatch: {msg_b}")

    # Alice reacts at t=0.18s
    c_alice = PlayerClient("p1", "Alice")
    act_alice = c_alice.prepare_snatch_action(contest.contest_id, reaction_time_ms=180)
    ok_a, msg_a = gm.step5_process_input(act_alice)
    log.append(f"Alice submitted snatch: {msg_a}")

    log.append(f"Contest resolved: {contest.resolved}")
    log.append(f"Contest winner: {contest.winner_player_id} (Bob)")
    log.append(f"Winning order: {contest.winning_order}")

    return {
        "scenario": "Snatch Progression (Simultaneous)",
        "description": "High-speed contest where players race to claim unclaimed points.",
        "final_state": gm.state.to_dict(),
        "log": log,
    }


def run_cluster_failover_scenario() -> Dict[str, Any]:
    """Demonstrates Multi-Server Cluster Leader Election and Failover."""
    coordinator = ClusterCoordinator("cluster-production")
    nodes = coordinator.create_cluster(node_count=3)
    leader = coordinator.get_leader()

    log = []
    log.append(f"Cluster active with 3 nodes: {[n.node_id for n in nodes]}")
    log.append(f"Active Primary Leader: {leader.node_id if leader else 'None'}")

    # Register players via active leader
    p1 = leader.game_master.register_player("p1", "Alice")
    p2 = leader.game_master.register_player("p2", "Bob")
    log.append(f"Players registered on cluster: {list(leader.game_master.state.players.keys())}")

    # Alice makes a move on leader
    c_alice = PlayerClient("p1", "Alice", preferred_server_id=leader.node_id)
    m1 = c_alice.prepare_move("mine_gold", points=25)
    leader.game_master.step5_process_input(m1)
    log.append(f"Alice scored 25 on {leader.node_id}. State replicated across cluster log.")

    # Check follower replication
    follower = nodes[1]
    log.append(f"Follower {follower.node_id} synchronized state commit index: {follower.commit_index}")
    log.append(f"Follower sees Alice score: {follower.game_master.state.players['p1'].score}")

    # KILL THE ACTIVE LEADER!
    log.append(f"Simulating HARD CRASH of Primary Leader {leader.node_id}...")
    new_leader_id = coordinator.kill_leader()
    log.append(f"Failover election complete! New Leader elected: {new_leader_id}")

    # Now Bob submits move to the NEW leader
    new_leader = coordinator.get_leader()
    c_bob = PlayerClient("p2", "Bob", preferred_server_id=new_leader.node_id)
    m2 = c_bob.prepare_move("mine_gold", points=40)
    new_leader.game_master.step5_process_input(m2)

    log.append(f"Bob scored 40 on newly elected Leader {new_leader.node_id} without state loss!")
    log.append(f"Final scores on new leader: Alice={new_leader.game_master.state.players['p1'].score}, Bob={new_leader.game_master.state.players['p2'].score}")

    return {
        "scenario": "Multi-Server Leader Failover",
        "description": "Raft-style leader election & replicated state machine preserving game turn progression across node crashes.",
        "final_state": new_leader.game_master.state.to_dict(),
        "log": log,
    }
