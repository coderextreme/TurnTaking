"""
Unit tests for Multi-Server Cluster and Distributed Game Master Failover.
"""

import unittest
from turnprog.models import Move, Player
from turnprog.cluster import ClusterCoordinator, NodeRole
from turnprog.client import PlayerClient


class TestMultiServerCluster(unittest.TestCase):
    def setUp(self):
        self.coordinator = ClusterCoordinator("test-cluster")
        self.nodes = self.coordinator.create_cluster(node_count=3)
        self.leader = self.coordinator.get_leader()

    def test_cluster_creation_and_initial_leader(self):
        self.assertEqual(len(self.nodes), 3)
        self.assertIsNotNone(self.leader)
        self.assertEqual(self.leader.role, NodeRole.LEADER)
        self.assertEqual(self.nodes[1].role, NodeRole.FOLLOWER)
        self.assertEqual(self.nodes[2].role, NodeRole.FOLLOWER)

    def test_state_replication_to_followers(self):
        # Register player on leader
        self.leader.game_master.register_player("p1", "Alice")
        self.leader.game_master.register_player("p2", "Bob")

        # Alice makes a move on leader
        client = PlayerClient("p1", "Alice", preferred_server_id=self.leader.node_id)
        move = client.prepare_move("score_points", points=30)
        ok, _ = self.coordinator.route_message_to_leader(move)
        self.assertTrue(ok)

        # Verify follower has received state update via replication log
        follower = self.nodes[1]
        self.assertIn("p1", follower.game_master.state.players)
        self.assertEqual(follower.game_master.state.players["p1"].score, 30)

    def test_leader_failover_preserves_progression(self):
        self.leader.game_master.register_player("p1", "Alice")
        self.leader.game_master.register_player("p2", "Bob")

        # Alice takes her turn
        c1 = PlayerClient("p1", "Alice")
        self.coordinator.route_message_to_leader(c1.prepare_move("turn_1", points=10))

        # Check progression state before crash
        self.assertEqual(self.leader.game_master.state.current_player_id(), "p2")

        # HARD CRASH current leader!
        crashed_id = self.leader.node_id
        new_leader_id = self.coordinator.kill_leader()
        self.assertIsNotNone(new_leader_id)
        self.assertNotEqual(crashed_id, new_leader_id)

        new_leader = self.coordinator.get_leader()
        self.assertEqual(new_leader.role, NodeRole.LEADER)

        # Progression state must be fully preserved on new leader!
        self.assertEqual(new_leader.game_master.state.current_player_id(), "p2")
        self.assertEqual(new_leader.game_master.state.players["p1"].score, 10)

        # Bob can immediately play his turn on new leader without reset
        c2 = PlayerClient("p2", "Bob")
        ok, _ = self.coordinator.route_message_to_leader(c2.prepare_move("turn_2", points=15))
        self.assertTrue(ok)
        self.assertEqual(new_leader.game_master.state.players["p2"].score, 15)


if __name__ == "__main__":
    unittest.main()
