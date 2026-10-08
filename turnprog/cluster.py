"""
Multi-server clustering, replicated state machine, and failover coordination.
Allows multiple Game Master nodes to synchronize player progression state,
elect leaders, and survive node crashes in distributed environments.
"""

from __future__ import annotations
import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import GameState, Message, MessageType
from .game_master import GameMaster

logger = logging.getLogger("turnprog.cluster")


class NodeRole(str, enum.Enum):
    LEADER = "leader"          # Authoritative Game Master executing progression
    FOLLOWER = "follower"      # Hot-standby replica applying state log
    CANDIDATE = "candidate"    # Participating in leader election
    OFFLINE = "offline"        # Node crashed or partitioned


@dataclass
class LogEntry:
    term: int
    index: int
    command_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class ServerNode:
    """
    A single server node within a multi-server Game Master cluster.
    """

    def __init__(self, node_id: str, address: str = "127.0.0.1", role: NodeRole = NodeRole.FOLLOWER):
        self.node_id = node_id
        self.address = address
        self.role = role
        self.current_term: int = 1
        self.voted_for: Optional[str] = None
        self.commit_index: int = 0
        self.log: List[LogEntry] = []
        self.last_leader_heartbeat: float = time.time()
        self.heartbeat_timeout_sec: float = 3.0

        # Local Game Master instance
        self.game_master = GameMaster(server_id=self.node_id)
        # When leader updates state, replicate into log
        self.game_master.add_replication_callback(self._on_local_state_change)

        # Peer server nodes in cluster
        self.peers: Dict[str, ServerNode] = {}

    def connect_peer(self, peer: ServerNode) -> None:
        if peer.node_id != self.node_id:
            self.peers[peer.node_id] = peer
            peer.peers[self.node_id] = self

    def _on_local_state_change(self, state: GameState) -> None:
        if self.role == NodeRole.LEADER:
            # Append to distributed log and replicate to peers
            entry = LogEntry(
                term=self.current_term,
                index=len(self.log) + 1,
                command_type="STATE_UPDATE",
                data=state.to_dict(),
            )
            self.log.append(entry)
            self.commit_index = entry.index
            self._replicate_to_followers(entry)

    def _replicate_to_followers(self, entry: LogEntry) -> None:
        for peer in self.peers.values():
            if peer.role != NodeRole.OFFLINE:
                peer.receive_append_entries(
                    leader_id=self.node_id,
                    term=self.current_term,
                    entry=entry,
                    commit_index=self.commit_index,
                )

    def receive_append_entries(self, leader_id: str, term: int, entry: LogEntry, commit_index: int) -> bool:
        if self.role == NodeRole.OFFLINE:
            return False

        if term >= self.current_term:
            self.current_term = term
            self.role = NodeRole.FOLLOWER
            self.last_leader_heartbeat = time.time()
            self.game_master.state.leader_server_id = leader_id

            # Apply state snapshot to follower Game Master
            if entry.command_type == "STATE_UPDATE":
                self.log.append(entry)
                self.commit_index = commit_index
                new_state = GameState.from_dict(entry.data)
                # Keep local follower synchronized
                self.game_master.state = new_state
            return True
        return False

    def receive_heartbeat(self, leader_id: str, term: int) -> bool:
        if self.role == NodeRole.OFFLINE:
            return False
        if term >= self.current_term:
            self.current_term = term
            self.role = NodeRole.FOLLOWER
            self.last_leader_heartbeat = time.time()
            self.game_master.state.leader_server_id = leader_id
            return True
        return False

    def check_leader_liveness(self) -> bool:
        """Called periodically by followers to detect leader failure."""
        if self.role == NodeRole.OFFLINE or self.role == NodeRole.LEADER:
            return False

        elapsed = time.time() - self.last_leader_heartbeat
        if elapsed > self.heartbeat_timeout_sec:
            logger.warning(f"Node {self.node_id} detected leader failure (timeout {elapsed:.1f}s). Triggering election.")
            self.start_election()
            return True
        return False

    def start_election(self) -> None:
        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        votes = 1  # Vote for self

        alive_peers = [p for p in self.peers.values() if p.role != NodeRole.OFFLINE]
        total_nodes = len(alive_peers) + 1

        for peer in alive_peers:
            if peer.request_vote(candidate_id=self.node_id, term=self.current_term, last_log_index=self.commit_index):
                votes += 1

        # Majority check
        if votes > total_nodes / 2:
            self.promote_to_leader()

    def request_vote(self, candidate_id: str, term: int, last_log_index: int) -> bool:
        if self.role == NodeRole.OFFLINE:
            return False
        if term > self.current_term and last_log_index >= self.commit_index:
            self.current_term = term
            self.voted_for = candidate_id
            self.role = NodeRole.FOLLOWER
            return True
        return False

    def promote_to_leader(self) -> None:
        logger.info(f"Node {self.node_id} successfully elected as LEADER for term {self.current_term}!")
        self.role = NodeRole.LEADER
        self.game_master.state.leader_server_id = self.node_id

        # Re-broadcast state sync to peers
        state_dict = self.game_master.state.to_dict()
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log) + 1,
            command_type="STATE_UPDATE",
            data=state_dict,
        )
        self.log.append(entry)
        self.commit_index = entry.index
        self._replicate_to_followers(entry)

    def crash_or_kill(self) -> None:
        """Simulates hard crash or network isolation of this server node."""
        logger.warning(f"Simulating kill of server node {self.node_id}")
        self.role = NodeRole.OFFLINE

    def recover(self) -> None:
        """Recovers this node back into follower status."""
        logger.info(f"Recovering server node {self.node_id}")
        self.role = NodeRole.FOLLOWER
        self.last_leader_heartbeat = time.time()


class ClusterCoordinator:
    """
    Coordinates a multi-server cluster, routing client requests
    to the active leader while managing failover and edge proxies.
    """

    def __init__(self, cluster_id: str = "cluster-omega"):
        self.cluster_id = cluster_id
        self.nodes: Dict[str, ServerNode] = {}
        self.event_log: List[Dict[str, Any]] = []

    def create_cluster(self, node_count: int = 3, address_prefix: str = "srv") -> List[ServerNode]:
        created: List[ServerNode] = []
        for i in range(1, node_count + 1):
            nid = f"{address_prefix}-{i}"
            role = NodeRole.LEADER if i == 1 else NodeRole.FOLLOWER
            node = ServerNode(node_id=nid, address=f"10.0.0.{i}:900{i}", role=role)
            self.nodes[nid] = node
            created.append(node)

        # Full mesh connection between peers
        for n1 in created:
            for n2 in created:
                if n1.node_id != n2.node_id:
                    n1.connect_peer(n2)

        self._log_event("CLUSTER_INIT", f"Created cluster with {node_count} nodes. Leader: {created[0].node_id}")
        return created

    def get_leader(self) -> Optional[ServerNode]:
        for node in self.nodes.values():
            if node.role == NodeRole.LEADER:
                return node
        return None

    def route_message_to_leader(self, message: Message) -> Tuple[bool, str]:
        """Routes player messages to the active leader node."""
        leader = self.get_leader()
        if not leader:
            # Trigger election among alive nodes
            self.trigger_election_check()
            leader = self.get_leader()
            if not leader:
                return False, "Cluster has no active leader (split-brain or all nodes offline)"

        return leader.game_master.step5_process_input(message)

    def trigger_election_check(self) -> Optional[str]:
        for node in self.nodes.values():
            if node.role == NodeRole.FOLLOWER:
                node.last_leader_heartbeat = 0.0  # Force timeout
                if node.check_leader_liveness():
                    self._log_event("ELECTION", f"New leader elected: {node.node_id}")
                    return node.node_id
        return None

    def kill_leader(self) -> Optional[str]:
        """Simulates crash of current leader and triggers immediate election."""
        leader = self.get_leader()
        if not leader:
            return None
        old_id = leader.node_id
        leader.crash_or_kill()
        self._log_event("NODE_KILL", f"Leader {old_id} crashed. Failover initiating...")

        # Remaining nodes elect new leader
        new_leader_id = self.trigger_election_check()
        return new_leader_id

    def _log_event(self, event_type: str, details: str) -> None:
        self.event_log.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details,
        })
