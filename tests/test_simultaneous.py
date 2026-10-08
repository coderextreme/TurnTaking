"""
Unit tests for Simultaneous Player Progression methods (Carlson 1986).
- Snatch Progression (1 move per contest, first/last to move wins)
- Limited Progression (up to N moves per contest, budget/time limited)
- Continuous Progression (unlimited moves, dynamic join/leave, goal race)
"""

import unittest
import time
from turnprog.models import (
    GameState,
    Move,
    Player,
    PlayerState,
    ContestType,
)
from turnprog.progression import (
    SnatchProgression,
    LimitedProgression,
    ContinuousProgression,
)


class TestSnatchProgression(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.engine = SnatchProgression(time_limit_sec=5.0, first_to_move_wins=True)
        for pid in ["p1", "p2", "p3"]:
            self.engine.handle_player_join(self.state, Player(player_id=pid, name=pid))

    def test_snatch_first_to_move_wins(self):
        contest = self.engine.create_contest(self.state, "Buzzer Snatch")
        self.assertFalse(contest.resolved)

        # p2 snatches first
        ok, msg = self.engine.process_move(self.state, Move(player_id="p2", action="buzz", payload={"points": 5}))
        self.assertTrue(ok)
        self.assertTrue(contest.resolved)
        self.assertEqual(contest.winner_player_id, "p2")
        self.assertEqual(self.state.players["p2"].score, 5)

        # Second player p1 attempts to snatch after contest resolution
        ok2, msg2 = self.engine.process_move(self.state, Move(player_id="p1", action="buzz"))
        self.assertFalse(ok2)
        self.assertIn("No active contest", msg2)

    def test_snatch_single_move_per_player_enforced(self):
        engine_require_all = SnatchProgression(first_to_move_wins=False, require_all=True)
        contest = engine_require_all.create_contest(self.state, "Wait all snatch")

        ok1, _ = engine_require_all.process_move(self.state, Move(player_id="p1", action="act"))
        self.assertTrue(ok1)

        # p1 attempts a second move in the same contest
        ok2, msg2 = engine_require_all.process_move(self.state, Move(player_id="p1", action="act"))
        self.assertFalse(ok2)
        self.assertIn("already made their 1 snatch move", msg2)


class TestLimitedProgression(unittest.TestCase):
    def test_limited_move_budget(self):
        state = GameState()
        engine = LimitedProgression(max_moves_per_player=2)
        for pid in ["p1", "p2"]:
            engine.handle_player_join(state, Player(player_id=pid, name=pid))

        contest = engine.create_contest(state, "Auction Bidding")

        # p1 moves twice (reaches max)
        self.assertTrue(engine.process_move(state, Move(player_id="p1", payload={"points": 2}))[0])
        self.assertTrue(engine.process_move(state, Move(player_id="p1", payload={"points": 3}))[0])

        # p1 attempts third move: should be rejected
        ok, msg = engine.process_move(state, Move(player_id="p1", payload={"points": 4}))
        self.assertFalse(ok)
        self.assertIn("exceeded move limit", msg)

        # p2 moves twice to finish contest
        self.assertTrue(engine.process_move(state, Move(player_id="p2", payload={"points": 1}))[0])
        self.assertTrue(engine.process_move(state, Move(player_id="p2", payload={"points": 1}))[0])

        self.assertTrue(contest.resolved)
        # Winner should be p1 (5 total points vs 2 points)
        self.assertEqual(contest.winner_player_id, "p1")


class TestContinuousProgression(unittest.TestCase):
    def test_continuous_goal_race(self):
        state = GameState()
        engine = ContinuousProgression(target_goal_score=10)
        for pid in ["p1", "p2"]:
            engine.handle_player_join(state, Player(player_id=pid, name=pid))

        contest = engine.create_contest(state, "Fast Race")

        # p1 makes rapid moves to reach 10 points
        for _ in range(5):
            engine.process_move(state, Move(player_id="p1", payload={"points": 2}))

        self.assertEqual(state.players["p1"].score, 10)
        self.assertIn("p1", contest.winning_order)

        # Dynamic join mid-race (Carlson 1986: players join anytime in continuous)
        p3 = Player(player_id="p3", name="Charlie")
        engine.handle_player_join(state, p3)
        self.assertIn("p3", state.players)


if __name__ == "__main__":
    unittest.main()
