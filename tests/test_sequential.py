"""
Unit tests for Sequential Player Progression methods (Carlson 1986).
- Predefined Progression & Gap Closure
- Variable Progression & Power Plays (Add, Take, Reverse, Skip, Cancel)
- Round-Order Progression (Score Desc, Best First)
"""

import unittest
from turnprog.models import (
    GameState,
    Move,
    Player,
    PlayerState,
    PowerPlay,
    PowerPlayType,
    ProgressionType,
)
from turnprog.progression import (
    PredefinedProgression,
    VariableProgression,
    RoundOrderProgression,
)


class TestPredefinedProgression(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.engine = PredefinedProgression()
        for pid, name in [("p1", "Alice"), ("p2", "Bob"), ("p3", "Carol")]:
            player = Player(player_id=pid, name=name)
            self.engine.handle_player_join(self.state, player)

    def test_cyclical_turn_taking(self):
        self.assertEqual(self.state.current_player_id(), "p1")
        self.assertEqual(self.state.round_number, 1)

        # Move for Alice
        ok, _ = self.engine.process_move(self.state, Move(player_id="p1", action="draw"))
        self.assertTrue(ok)
        self.assertEqual(self.state.current_player_id(), "p2")

        # Move for Bob
        ok, _ = self.engine.process_move(self.state, Move(player_id="p2", action="draw"))
        self.assertTrue(ok)
        self.assertEqual(self.state.current_player_id(), "p3")

        # Move for Carol wraps round
        ok, _ = self.engine.process_move(self.state, Move(player_id="p3", action="draw"))
        self.assertTrue(ok)
        self.assertEqual(self.state.current_player_id(), "p1")
        self.assertEqual(self.state.round_number, 2)

    def test_out_of_turn_move_rejected(self):
        # Alice is current; Bob attempts to move
        ok, msg = self.engine.process_move(self.state, Move(player_id="p2", action="cheat"))
        self.assertFalse(ok)
        self.assertIn("Not player p2's turn", msg)

    def test_gap_closure_on_player_quit(self):
        # Current is Alice
        self.assertEqual(self.state.current_player_id(), "p1")
        # Bob quits
        self.engine.handle_player_quit(self.state, "p2")
        self.assertNotIn("p2", self.state.player_order)

        # Alice moves; next should be Carol immediately because gap closed!
        self.engine.process_move(self.state, Move(player_id="p1", action="draw"))
        self.assertEqual(self.state.current_player_id(), "p3")


class TestVariableProgression(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.engine = VariableProgression()
        for pid in ["p1", "p2", "p3", "p4"]:
            self.engine.handle_player_join(self.state, Player(player_id=pid, name=pid))

    def test_reverse_power_play(self):
        # Normal order: p1, p2, p3, p4
        self.assertEqual(self.state.current_player_id(), "p1")

        # p1 plays REVERSE_ORDER
        pp = PowerPlay(player_id="p1", play_type=PowerPlayType.REVERSE_ORDER)
        ok, _ = self.engine.apply_power_play(self.state, pp)
        self.assertTrue(ok)

        # After p1 completes turn, next in reversed order should be p4
        self.engine.process_move(self.state, Move(player_id="p1", action="strike"))
        self.assertEqual(self.state.current_player_id(), "p4")

    def test_skip_player_power_play(self):
        # p1 plays SKIP_PLAYER targeting p2
        pp = PowerPlay(player_id="p1", play_type=PowerPlayType.SKIP_PLAYER, target_player_id="p2")
        self.engine.apply_power_play(self.state, pp)

        # p1 moves
        self.engine.process_move(self.state, Move(player_id="p1", action="strike"))
        # p2 should be skipped; p3 gets turn
        self.assertEqual(self.state.current_player_id(), "p3")

    def test_add_moves_power_play(self):
        # p1 gains +2 moves
        pp = PowerPlay(player_id="p1", play_type=PowerPlayType.ADD_MOVES, magnitude=2)
        self.engine.apply_power_play(self.state, pp)
        self.assertEqual(self.state.players["p1"].moves_left_in_turn, 3)

        # Move 1: still p1
        self.engine.process_move(self.state, Move(player_id="p1", action="strike"))
        self.assertEqual(self.state.current_player_id(), "p1")
        # Move 2: still p1
        self.engine.process_move(self.state, Move(player_id="p1", action="strike"))
        self.assertEqual(self.state.current_player_id(), "p1")
        # Move 3: advances to p2
        self.engine.process_move(self.state, Move(player_id="p1", action="strike"))
        self.assertEqual(self.state.current_player_id(), "p2")


class TestRoundOrderProgression(unittest.TestCase):
    def test_score_desc_reordering(self):
        state = GameState()
        engine = RoundOrderProgression(mode="score_desc")
        for pid in ["p1", "p2", "p3"]:
            engine.handle_player_join(state, Player(player_id=pid, name=pid))

        # p1 scores 5
        engine.process_move(state, Move(player_id="p1", payload={"points": 5}))
        # p2 scores 20
        engine.process_move(state, Move(player_id="p2", payload={"points": 20}))
        # p3 scores 12
        engine.process_move(state, Move(player_id="p3", payload={"points": 12}))

        # Round boundary reached! Next round order should be: p2 (20), p3 (12), p1 (5)
        self.assertEqual(state.round_number, 2)
        self.assertEqual(state.player_order, ["p2", "p3", "p1"])
        self.assertEqual(state.current_player_id(), "p2")


if __name__ == "__main__":
    unittest.main()
