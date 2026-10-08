# TurnProg: Multi-Client Multi-Server Player Progression Library

A robust, pure-Python distributed progression and game master engine implementing the taxonomy and algorithms described in John Carlson's foundational 1986 paper:
**["Designing Multi-player Games: Player Progression and Interface"](https://coderextreme.net/TurnTaking.html)** (August 20, 1986).

---

## 🌟 Theoretical Foundations (Carlson 1986)

In distributed multiplayer game architectures, **player progression** defines how players take turns, contend for points, and progress through rounds. TurnProg translates Carlson's mathematical and protocol models into a modern, distributed, multi-client multi-server engine.

### 1. Sequential Player Progression
Play is restricted to one player (or team) at a time:
- **Pre-defined Progression**: Static cyclical ordering established at game start. Moves per round equals number of active players. When a player quits, resigns, or drops out, the gap closes immediately and subsequent players shift forward.
- **Variable Progression & Power Plays**: Dynamic order manipulation via in-game power plays:
  - `ADD_MOVES`: Grants extra moves in the current turn.
  - `TAKE_MOVES`: Deducts moves from the target player's turn.
  - `REVERSE_ORDER`: Inverts progression sequencing (e.g., Uno reverse).
  - `SKIP_PLAYER`: Temporarily skips players in the cycle.
  - `CANCEL_POWER_PLAY`: Stacking power play that negates or alters the preceding play.
  - `SWAP_ORDER`: Swaps positions between two players.
- **Round-Order Progression**: Sequence recalculated at round boundaries (e.g., golf honors, draft mechanics):
  - `best_first`: Winner of previous round leads off.
  - `score_desc` / `score_asc`: Cumulative score-ranked progression.
  - `autocratic`: Game Master algorithmically selects round sequence.

### 2. Simultaneous Player Progression
Multiple players act simultaneously within discrete competition units called **Contests**:
- **Snatch Progression**: Exactly **1 move per player per contest**. Used for reaction contests (buzzers, claiming untaken points in Cribbage, challenges, slapjack). Can be first-to-act wins or last-to-act wins, with optional pass requirements.
- **Limited Progression**: Players take up to $N$ moves within an action or time budget (e.g., auctions, betting rounds in craps/roulette).
- **Continuous Progression**: Unlimited moves within physical/network limits. Players can join or drop out dynamically. Reaching target goals generates ordered winning and losing sequences.
- **Hybrid Progression**: Main sequential loop punctuated by simultaneous snatch interrupts.

### 3. Game Master 8-Step Algorithm
1. Decide which player(s) are next
2. Prompt player(s) if necessary
3. Order players (or queue simultaneous signals by arrival timestamp)
4. Receive player input from buffer
5. Process input and update state
6. Request more input if incomplete
7. Broadcast state updates to all players
8. Repeat cycle

### 4. Three-State Input Framing Buffer
To handle network packet fragmentation and streaming I/O safely:
- `READY_FOR_MESSAGE`: Idle, awaiting new frame.
- `PARTIAL_MESSAGE`: Chunk received, buffering incomplete segment.
- `COMPLETE_MESSAGE`: Message parsed and queued for Game Master consumption.

### 5. Multi-Server Clustering & Distributed Failover
- Replicated State Machine with Raft-style log replication and commit index.
- Primary Leader node executes the authoritative Game Master progression loop.
- Hot standby replica nodes sync state logs.
- Automatic failover and leader election upon leader node crash or network partition—preserving progression state, scores, and turn indices.

---

## 🚀 Quickstart

### Installation
```bash
pip install -e .
```

### Running Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Example: Pre-defined Sequential Progression
```python
from turnprog import GameMaster, PredefinedProgression, PlayerClient

gm = GameMaster(server_id="srv-1")
gm.set_progression_engine(PredefinedProgression())

# Register players
gm.register_player("p1", "Alice")
gm.register_player("p2", "Bob")
gm.register_player("p3", "Carol")

# Alice submits her move
client_a = PlayerClient("p1", "Alice")
move_msg = client_a.prepare_move(action="play_card", points=10)
success, note = gm.step5_process_input(move_msg)

print("Next player:", gm.state.current_player_id()) # -> 'p2' (Bob)
```

### Example: Variable Progression with Power Plays
```python
from turnprog import GameMaster, VariableProgression, PlayerClient, PowerPlayType

gm = GameMaster()
gm.set_progression_engine(VariableProgression())
gm.register_player("p1", "Alice")
gm.register_player("p2", "Bob")
gm.register_player("p3", "Carol")

client_a = PlayerClient("p1", "Alice")
# Alice reverses turn order!
rev = client_a.prepare_power_play(PowerPlayType.REVERSE_ORDER)
gm.step5_process_input(rev)

client_a.prepare_move("strike")
gm.step5_process_input(client_a.flush_outbox()[0])

print("Reversed next player:", gm.state.current_player_id()) # -> 'p3' (Carol)
```

### Example: Multi-Server Cluster Failover
```python
from turnprog import ClusterCoordinator, PlayerClient

coordinator = ClusterCoordinator("prod-cluster")
nodes = coordinator.create_cluster(node_count=3)
leader = coordinator.get_leader()

# Alice moves on active leader
leader.game_master.register_player("p1", "Alice")
leader.game_master.register_player("p2", "Bob")

# Simulate sudden leader crash
new_leader_id = coordinator.kill_leader()
print("Elected new leader:", new_leader_id)

# Bob immediately moves on new leader with zero state loss
new_leader = coordinator.get_leader()
bob = PlayerClient("p2", "Bob")
coordinator.route_message_to_leader(bob.prepare_move("action", points=20))
```
