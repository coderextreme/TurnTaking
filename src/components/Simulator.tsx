import React, { useState, useEffect } from 'react';
import { 
  Server, 
  Play, 
  RotateCcw, 
  Skull, 
  Zap, 
  Users, 
  Award, 
  Timer, 
  ShieldAlert, 
  Sparkles,
  ArrowRight,
  UserX,
  FastForward,
  Radio,
  Layers,
  Inbox
} from 'lucide-react';
import { GameState, Player, Move, PowerPlay, Contest } from '../types';

interface ServerNodeVisual {
  id: string;
  name: string;
  address: string;
  role: 'leader' | 'follower' | 'offline';
  commitIndex: number;
  lastHeartbeat: number;
}

export const Simulator: React.FC = () => {
  // Progression Mode
  const [progressionMode, setProgressionMode] = useState<
    'predefined' | 'variable' | 'round_order' | 'snatch' | 'limited' | 'continuous'
  >('predefined');

  // Server cluster state
  const [nodes, setNodes] = useState<ServerNodeVisual[]>([
    { id: 'srv-1', name: 'Master Gateway 1', address: '10.0.0.1:9001', role: 'leader', commitIndex: 6, lastHeartbeat: Date.now() },
    { id: 'srv-2', name: 'Replica Node 2', address: '10.0.0.2:9002', role: 'follower', commitIndex: 6, lastHeartbeat: Date.now() },
    { id: 'srv-3', name: 'Replica Node 3', address: '10.0.0.3:9003', role: 'follower', commitIndex: 6, lastHeartbeat: Date.now() },
  ]);

  // Players
  const [players, setPlayers] = useState<Record<string, Player>>({
    p1: { player_id: 'p1', name: 'Alice', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-1', state: 'active' },
    p2: { player_id: 'p2', name: 'Bob', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-2', state: 'active' },
    p3: { player_id: 'p3', name: 'Carol', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-3', state: 'active' },
    p4: { player_id: 'p4', name: 'Dave', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-1', state: 'active' },
  });

  const [playerOrder, setPlayerOrder] = useState<string[]>(['p1', 'p2', 'p3', 'p4']);
  const [turnIndex, setTurnIndex] = useState<number>(0);
  const [roundNumber, setRoundNumber] = useState<number>(1);
  const [direction, setDirection] = useState<number>(1); // 1 = forward, -1 = reverse
  const [activeContest, setActiveContest] = useState<Contest | null>(null);

  // 3-State Buffer Simulation
  const [bufferState, setBufferState] = useState<'ready_for_message' | 'partial_message' | 'complete_message'>('ready_for_message');
  const [bufferStream, setBufferStream] = useState<string>('');

  // Logs
  const [logs, setLogs] = useState<string[]>([
    'System initialized with 3 server nodes (1 Leader, 2 Followers).',
    'Predefined progression mode active with 4 players in cyclical order [Alice, Bob, Carol, Dave].',
    "Alice's turn to move (Round 1)."
  ]);

  const addLog = (msg: string) => {
    setLogs((prev) => [msg, ...prev.slice(0, 49)]);
  };

  const leaderNode = nodes.find((n) => n.role === 'leader');
  const currentEligibleId = activeContest ? null : playerOrder[turnIndex % Math.max(1, playerOrder.length)];
  const currentPlayer = currentEligibleId ? players[currentEligibleId] : null;

  // Heartbeat ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setNodes((prev) =>
        prev.map((n) => (n.role !== 'offline' ? { ...n, lastHeartbeat: Date.now() } : n))
      );
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  // 1. Submit Standard Move
  const handleMakeMove = (points: number = 5) => {
    if (!currentEligibleId || !currentPlayer) return;

    const pid = currentEligibleId;
    const newScore = currentPlayer.score + points;
    const movesLeft = currentPlayer.moves_left_in_turn - 1;

    setPlayers((prev) => ({
      ...prev,
      [pid]: {
        ...prev[pid],
        score: newScore,
        moves_left_in_turn: movesLeft <= 0 ? 1 : movesLeft,
      },
    }));

    // Update server commit index
    setNodes((prev) =>
      prev.map((n) => (n.role !== 'offline' ? { ...n, commitIndex: n.commitIndex + 1 } : n))
    );

    if (movesLeft > 0) {
      addLog(`Move accepted: ${currentPlayer.name} scored +${points} pts (${movesLeft} moves remaining this turn).`);
      return;
    }

    // Advance turn
    if (progressionMode === 'round_order') {
      const nextIdx = turnIndex + 1;
      if (nextIdx >= playerOrder.length) {
        // Recalculate round order based on highest score!
        const sortedOrder = [...playerOrder].sort(
          (a, b) => (players[b]?.score || 0) - (players[a]?.score || 0)
        );
        setPlayerOrder(sortedOrder);
        setTurnIndex(0);
        setRoundNumber((r) => r + 1);
        addLog(`Round completed! Round-order recalculated by highest score: [${sortedOrder.map((id) => players[id]?.name).join(', ')}].`);
      } else {
        setTurnIndex(nextIdx);
        addLog(`${currentPlayer.name} finished turn (+${points} pts). Next: ${players[playerOrder[nextIdx]]?.name}.`);
      }
    } else {
      let nextIdx = (turnIndex + 1) % playerOrder.length;
      let nextRound = roundNumber;
      if (nextIdx === 0) {
        nextRound += 1;
        setRoundNumber(nextRound);
      }
      setTurnIndex(nextIdx);

      // Check if next player is skipped
      const nextPid = playerOrder[nextIdx];
      if (players[nextPid]?.skipped_rounds > 0) {
        setPlayers((prev) => ({
          ...prev,
          [nextPid]: { ...prev[nextPid], skipped_rounds: prev[nextPid].skipped_rounds - 1 },
        }));
        nextIdx = (nextIdx + 1) % playerOrder.length;
        setTurnIndex(nextIdx);
        addLog(`${currentPlayer.name} finished turn (+${points} pts). ${players[nextPid]?.name} was skipped! Next is ${players[playerOrder[nextIdx]]?.name}.`);
      } else {
        addLog(`${currentPlayer.name} finished turn (+${points} pts). Next player: ${players[nextPid]?.name} (Round ${nextRound}).`);
      }
    }
  };

  // 2. Power Plays
  const handlePowerPlay = (type: 'reverse' | 'skip' | 'add_moves' | 'cancel') => {
    if (!currentPlayer) return;

    if (type === 'reverse') {
      const reversed = [...playerOrder].reverse();
      const newIdx = reversed.indexOf(currentEligibleId!);
      setPlayerOrder(reversed);
      setTurnIndex(newIdx >= 0 ? newIdx : 0);
      setDirection((d) => d * -1);
      addLog(`⚡ POWER PLAY: ${currentPlayer.name} played REVERSE ORDER! Sequence is now inverted: [${reversed.map((id) => players[id]?.name).join(', ')}].`);
    } else if (type === 'skip') {
      const nextIdx = (turnIndex + 1) % playerOrder.length;
      const targetPid = playerOrder[nextIdx];
      setPlayers((prev) => ({
        ...prev,
        [targetPid]: { ...prev[targetPid], skipped_rounds: 1 },
      }));
      addLog(`⚡ POWER PLAY: ${currentPlayer.name} played SKIP PLAYER targeting ${players[targetPid]?.name}!`);
    } else if (type === 'add_moves') {
      setPlayers((prev) => ({
        ...prev,
        [currentEligibleId!]: { ...prev[currentEligibleId!], moves_left_in_turn: prev[currentEligibleId!].moves_left_in_turn + 1 },
      }));
      addLog(`⚡ POWER PLAY: ${currentPlayer.name} gained +1 extra move this turn.`);
    } else if (type === 'cancel') {
      addLog(`⚡ POWER PLAY: ${currentPlayer.name} cancelled previous power play effect.`);
    }

    setNodes((prev) =>
      prev.map((n) => (n.role !== 'offline' ? { ...n, commitIndex: n.commitIndex + 1 } : n))
    );
  };

  // 3. Gap Closure (Carlson 1986): Player quits or disconnects
  const handleDropPlayer = (pid: string) => {
    const pName = players[pid]?.name || pid;
    const newOrder = playerOrder.filter((id) => id !== pid);
    setPlayerOrder(newOrder);

    // Adjust turn index
    const currIdx = turnIndex % Math.max(1, playerOrder.length);
    const dropIdx = playerOrder.indexOf(pid);
    if (dropIdx < currIdx) {
      setTurnIndex(Math.max(0, turnIndex - 1));
    } else if (turnIndex >= newOrder.length) {
      setTurnIndex(0);
    }

    setPlayers((prev) => ({
      ...prev,
      [pid]: { ...prev[pid], state: 'eliminated' },
    }));

    addLog(`🚫 GAP CLOSURE (Carlson 1986): Player ${pName} dropped out. Gap closed immediately! New order: [${newOrder.map((id) => players[id]?.name).join(', ')}].`);
  };

  // 4. Snatch Contest (Simultaneous)
  const handleStartSnatchContest = () => {
    const contest: Contest = {
      contest_id: `c-${Date.now().toString().slice(-4)}`,
      contest_type: 'snatch',
      description: 'Cribbage / Buzzer Snatch Contest (First to move wins +10 pts)',
      eligible_player_ids: playerOrder,
      moves_by_player: {},
      max_moves_per_player: 1,
      time_limit_sec: 5.0,
      require_all_players_to_act: false,
      start_time: Date.now(),
      resolved: false,
      winning_order: [],
      losing_order: [],
    };
    setActiveContest(contest);
    addLog(`🔔 SNATCH CONTEST STARTED: All players race to claim unclaimed points! Exactly 1 move per player.`);
  };

  const handleSnatchBuzz = (pid: string) => {
    if (!activeContest || activeContest.resolved) return;

    const pName = players[pid]?.name || pid;
    const updatedContest: Contest = {
      ...activeContest,
      resolved: true,
      winner_player_id: pid,
      winning_order: [pid],
      losing_order: playerOrder.filter((id) => id !== pid),
      end_time: Date.now(),
    };
    setActiveContest(updatedContest);

    // Award winner
    setPlayers((prev) => ({
      ...prev,
      [pid]: { ...prev[pid], score: prev[pid].score + 10 },
    }));

    setNodes((prev) =>
      prev.map((n) => (n.role !== 'offline' ? { ...n, commitIndex: n.commitIndex + 1 } : n))
    );

    addLog(`🏆 SNATCH WON: ${pName} buzzed in first! Awarded +10 points. Contest resolved.`);
  };

  // 5. Multi-Server Failover: Kill active Leader node
  const handleKillLeader = () => {
    if (!leaderNode) return;
    const oldLeaderId = leaderNode.id;

    // Set old leader offline
    const updatedNodes = nodes.map((n) =>
      n.id === oldLeaderId ? { ...n, role: 'offline' as const } : n
    );

    // Pick first available follower as new leader
    const candidate = updatedNodes.find((n) => n.role === 'follower');
    if (candidate) {
      const finalized = updatedNodes.map((n) =>
        n.id === candidate.id ? { ...n, role: 'leader' as const, commitIndex: n.commitIndex + 1 } : n
      );
      setNodes(finalized);
      addLog(`💥 HARD CRASH: Primary Leader ${oldLeaderId} killed!`);
      addLog(`🗳️ RAFT ELECTION: Standby ${candidate.name} (${candidate.id}) elected as new LEADER. Replicated state & turn order preserved intact!`);
    } else {
      setNodes(updatedNodes);
      addLog(`💥 All nodes offline! Cluster partition.`);
    }
  };

  const handleRecoverNode = (nodeId: string) => {
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId
          ? {
              ...n,
              role: prev.some((x) => x.role === 'leader') ? 'follower' : 'leader',
              commitIndex: Math.max(...prev.map((x) => x.commitIndex)),
            }
          : n
      )
    );
    addLog(`🟢 Server Node ${nodeId} recovered and re-joined the cluster as hot-standby follower.`);
  };

  // 6. Reset simulation
  const handleReset = () => {
    setNodes([
      { id: 'srv-1', name: 'Master Gateway 1', address: '10.0.0.1:9001', role: 'leader', commitIndex: 1, lastHeartbeat: Date.now() },
      { id: 'srv-2', name: 'Replica Node 2', address: '10.0.0.2:9002', role: 'follower', commitIndex: 1, lastHeartbeat: Date.now() },
      { id: 'srv-3', name: 'Replica Node 3', address: '10.0.0.3:9003', role: 'follower', commitIndex: 1, lastHeartbeat: Date.now() },
    ]);
    setPlayers({
      p1: { player_id: 'p1', name: 'Alice', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-1', state: 'active' },
      p2: { player_id: 'p2', name: 'Bob', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-2', state: 'active' },
      p3: { player_id: 'p3', name: 'Carol', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-3', state: 'active' },
      p4: { player_id: 'p4', name: 'Dave', score: 0, moves_left_in_turn: 1, skipped_rounds: 0, connected_server_id: 'srv-1', state: 'active' },
    });
    setPlayerOrder(['p1', 'p2', 'p3', 'p4']);
    setTurnIndex(0);
    setRoundNumber(1);
    setDirection(1);
    setActiveContest(null);
    setBufferState('ready_for_message');
    setBufferStream('');
    addLog('Simulation reset to initial state.');
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Mode Selector & High-level Controls */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-semibold text-white">Progression Strategy Selector</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Carlson (1986)
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Switch between Sequential and Simultaneous methods to test turn scheduling and state replication.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'predefined', label: 'Pre-defined', sub: 'Sequential' },
              { id: 'variable', label: 'Variable (Power Plays)', sub: 'Sequential' },
              { id: 'round_order', label: 'Round-Order', sub: 'Sequential' },
              { id: 'snatch', label: 'Snatch Contest', sub: 'Simultaneous' },
              { id: 'limited', label: 'Limited Auction', sub: 'Simultaneous' },
              { id: 'continuous', label: 'Continuous Race', sub: 'Simultaneous' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  setProgressionMode(m.id as any);
                  setActiveContest(null);
                  addLog(`Switched progression engine to: ${m.label} (${m.sub}).`);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all text-left ${
                  progressionMode === m.id
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-slate-700/60'
                }`}
              >
                <div>{m.label}</div>
                <div className="text-[10px] opacity-70">{m.sub}</div>
              </button>
            ))}

            <button
              onClick={handleReset}
              className="p-2 rounded-xl bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-700/60 transition-colors ml-auto"
              title="Reset Simulation"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Multi-Server Cluster Topology & Players State */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Server Cluster & Failover Controls */}
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Multi-Server Cluster</h3>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                {nodes.filter((n) => n.role !== 'offline').length}/3 Online
              </span>
            </div>

            {/* Server Nodes Cards */}
            <div className="space-y-2.5">
              {nodes.map((node) => (
                <div
                  key={node.id}
                  className={`p-3 rounded-xl border transition-all ${
                    node.role === 'leader'
                      ? 'bg-indigo-950/40 border-indigo-500/50 shadow-sm shadow-indigo-500/10'
                      : node.role === 'follower'
                      ? 'bg-slate-950/60 border-slate-800'
                      : 'bg-red-950/20 border-red-900/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          node.role === 'leader'
                            ? 'bg-emerald-400 animate-pulse'
                            : node.role === 'follower'
                            ? 'bg-indigo-400'
                            : 'bg-red-500'
                        }`}
                      />
                      <span className="text-xs font-semibold text-white">{node.name}</span>
                      <span className="text-[10px] text-slate-400 font-mono">({node.id})</span>
                    </div>

                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                        node.role === 'leader'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : node.role === 'follower'
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          : 'bg-red-500/20 text-red-300 border border-red-500/30'
                      }`}
                    >
                      {node.role}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                    <div>
                      <span className="text-slate-500">Address: </span>
                      <span className="font-mono text-slate-300">{node.address}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Commit Log: </span>
                      <span className="font-mono text-emerald-400 font-semibold">#{node.commitIndex}</span>
                    </div>
                  </div>

                  {node.role === 'offline' && (
                    <button
                      onClick={() => handleRecoverNode(node.id)}
                      className="mt-2 w-full text-xs py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                    >
                      Recover Node
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Leader Hard-Crash Action Button */}
            <div className="mt-4 pt-3 border-t border-slate-800">
              <button
                onClick={handleKillLeader}
                disabled={!leaderNode}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 transition-all disabled:opacity-50"
              >
                <Skull className="w-3.5 h-3.5 text-rose-400" />
                <span>Simulate Hard Crash of Active Leader</span>
              </button>
              <p className="text-[10px] text-slate-400 text-center mt-1.5">
                Tests automatic Raft-style election & state preservation across node failures.
              </p>
            </div>
          </div>

          {/* 3-State Message Buffer Inspector (Carlson 1986) */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Inbox className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-white">3-State Framing Buffer</h3>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Carlson (1986) I/O</span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Handles packet fragmentation: Ready &rarr; Partial &rarr; Complete.
            </p>

            {/* Visual State Indicators */}
            <div className="grid grid-cols-3 gap-1.5 mb-3">
              {[
                { id: 'ready_for_message', label: 'Ready', desc: 'Idle buffer' },
                { id: 'partial_message', label: 'Partial', desc: 'Accumulating' },
                { id: 'complete_message', label: 'Complete', desc: 'Framed' },
              ].map((s) => (
                <div
                  key={s.id}
                  className={`p-2 rounded-lg text-center border transition-all ${
                    bufferState === s.id
                      ? 'bg-amber-500/20 border-amber-500/50 text-amber-200 font-semibold'
                      : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
                  }`}
                >
                  <div className="text-xs">{s.label}</div>
                  <div className="text-[9px] opacity-70">{s.desc}</div>
                </div>
              ))}
            </div>

            {/* Test chunk fragmentation */}
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setBufferStream('{"msg_type":"submit_move"');
                  setBufferState('partial_message');
                  addLog('Buffer: Ingested incomplete TCP packet (15 bytes). Buffer state transitioned to PARTIAL_MESSAGE.');
                }}
                className="flex-1 text-[11px] py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
              >
                Feed Partial Chunk
              </button>
              <button
                onClick={() => {
                  setBufferStream('{"msg_type":"submit_move","sender_id":"p1"}\\n');
                  setBufferState('complete_message');
                  addLog('Buffer: Delimiter received. Message framed and queued! Buffer state transitioned to COMPLETE_MESSAGE.');
                }}
                className="flex-1 text-[11px] py-1.5 px-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30"
              >
                Feed Full Frame
              </button>
            </div>

            {bufferStream && (
              <div className="mt-2 p-2 rounded bg-slate-950 border border-slate-800 font-mono text-[10px] text-amber-300 break-all">
                {bufferStream}
              </div>
            )}
          </div>
        </div>

        {/* Center & Right Column: Progression Track & Interactive Player Actions */}
        <div className="lg:col-span-2 space-y-4">
          {/* Active Status Header */}
          <div className="bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 animate-pulse" />
                  <span>Progression State &bull; Round {roundNumber}</span>
                </div>
                <div className="text-lg font-bold text-white mt-1 flex items-center gap-2">
                  {activeContest ? (
                    <span className="text-amber-400">⚡ Simultaneous Snatch Contest Active!</span>
                  ) : currentPlayer ? (
                    <span>Current Turn: <span className="text-indigo-400">{currentPlayer.name}</span></span>
                  ) : (
                    <span>No active players</span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Direction: {direction === 1 ? 'Forward (A → B → C → D)' : 'Reversed (D → C → B → A)'} &bull; Active Node: {leaderNode?.name || 'Partitioned'}
                </p>
              </div>

              {/* Turn Action Buttons */}
              <div className="flex flex-wrap items-center gap-2">
                {!activeContest && (
                  <>
                    <button
                      onClick={() => handleMakeMove(10)}
                      disabled={!currentPlayer}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
                    >
                      <Play className="w-3.5 h-3.5 fill-white" />
                      <span>Take Turn (+10 pts)</span>
                    </button>

                    {progressionMode === 'variable' && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handlePowerPlay('reverse')}
                          className="px-2.5 py-2 rounded-xl text-xs font-semibold bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 transition-colors"
                          title="Reverse player order"
                        >
                          Reverse
                        </button>
                        <button
                          onClick={() => handlePowerPlay('skip')}
                          className="px-2.5 py-2 rounded-xl text-xs font-semibold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 transition-colors"
                          title="Skip next player"
                        >
                          Skip
                        </button>
                        <button
                          onClick={() => handlePowerPlay('add_moves')}
                          className="px-2.5 py-2 rounded-xl text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 transition-colors"
                          title="Add extra move to current turn"
                        >
                          +Move
                        </button>
                      </div>
                    )}
                  </>
                )}

                {activeContest && !activeContest.resolved && (
                  <span className="text-xs text-amber-300 animate-pulse font-medium">
                    Waiting for players to buzz in...
                  </span>
                )}

                {/* Snatch trigger */}
                <button
                  onClick={handleStartSnatchContest}
                  className="px-3 py-2 rounded-xl text-xs font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 transition-colors"
                  title="Trigger simultaneous snatch competition"
                >
                  Trigger Snatch Contest
                </button>
              </div>
            </div>

            {/* Sequence Order Visualizer */}
            <div className="mt-4 pt-4 border-t border-slate-800">
              <div className="text-[11px] text-slate-400 font-medium mb-2 flex items-center justify-between">
                <span>Player Progression Queue (Gap closes automatically on quit):</span>
                <span className="font-mono text-indigo-300">{playerOrder.length} Active Players</span>
              </div>
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {playerOrder.map((pid, idx) => {
                  const p = players[pid];
                  const isCurrent = pid === currentEligibleId;
                  return (
                    <React.Fragment key={pid}>
                      <div
                        className={`flex-shrink-0 px-3 py-2 rounded-xl border transition-all ${
                          isCurrent
                            ? 'bg-indigo-600 text-white border-indigo-400 shadow-md shadow-indigo-600/30 scale-105'
                            : 'bg-slate-900/80 text-slate-300 border-slate-800'
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-xs">{p?.name}</span>
                          {p?.skipped_rounds > 0 && (
                            <span className="text-[9px] bg-rose-500/30 text-rose-300 px-1 rounded">
                              Skipped
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] opacity-75 mt-0.5">
                          {p?.score} pts &bull; {p?.connected_server_id}
                        </div>
                      </div>
                      {idx < playerOrder.length - 1 && (
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Active Contest Banner if running */}
          {activeContest && (
            <div className="bg-amber-950/30 border border-amber-500/40 rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400 animate-bounce" />
                  <h4 className="text-sm font-semibold text-amber-200">
                    {activeContest.description}
                  </h4>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                  {activeContest.resolved ? 'RESOLVED' : 'ACTIVE CONTEST'}
                </span>
              </div>

              <p className="text-xs text-amber-200/80 mb-3">
                Carlson (1986): Snatch progression allows exactly 1 move per player per contest. Click buzz-in below:
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {activeContest.eligible_player_ids.map((pid) => (
                  <button
                    key={pid}
                    onClick={() => handleSnatchBuzz(pid)}
                    disabled={activeContest.resolved}
                    className="p-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 border border-amber-500/40 text-xs font-semibold flex items-center justify-center gap-1 transition-all disabled:opacity-40"
                  >
                    <span>Buzz {players[pid]?.name}</span>
                    <Zap className="w-3 h-3 text-amber-400" />
                  </button>
                ))}
              </div>

              {activeContest.resolved && (
                <div className="mt-3 pt-2 border-t border-amber-500/20 text-xs text-emerald-300 font-semibold flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-emerald-400" />
                  <span>Winner: {players[activeContest.winner_player_id || '']?.name}! Received +10 points.</span>
                </div>
              )}
            </div>
          )}

          {/* Player Cards Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Connected Player Clients</h3>
              </div>
              <span className="text-xs text-slate-400">Click &ldquo;Quit&rdquo; to test Gap Closure</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.values(players).map((p) => {
                const isCurrent = p.player_id === currentEligibleId;
                const isEliminated = p.state === 'eliminated';
                return (
                  <div
                    key={p.player_id}
                    className={`p-3 rounded-xl border transition-all ${
                      isEliminated
                        ? 'bg-slate-950/40 border-slate-800/50 opacity-40'
                        : isCurrent
                        ? 'bg-indigo-950/40 border-indigo-500/60'
                        : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                            isCurrent
                              ? 'bg-indigo-600 text-white'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {p.name[0]}
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                            <span>{p.name}</span>
                            <span className="text-[10px] text-slate-500 font-mono">({p.player_id})</span>
                          </div>
                          <div className="text-[10px] text-slate-400">
                            Edge Proxy: <span className="font-mono text-indigo-300">{p.connected_server_id}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-bold text-emerald-400 font-mono">
                          {p.score} pts
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {p.moves_left_in_turn} move left
                        </div>
                      </div>
                    </div>

                    {!isEliminated && (
                      <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">
                          Status: <span className="text-emerald-400 capitalize">{p.state}</span>
                        </span>
                        <button
                          onClick={() => handleDropPlayer(p.player_id)}
                          className="text-[10px] text-rose-400 hover:text-rose-300 flex items-center gap-1 hover:underline"
                        >
                          <UserX className="w-3 h-3" />
                          <span>Simulate Disconnect / Quit</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-time Activity Log */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Distributed Progression Event Log
              </h3>
              <span className="text-[10px] text-slate-500 font-mono">Real-time trace</span>
            </div>
            <div className="bg-slate-950 rounded-xl p-3 border border-slate-800/80 font-mono text-[11px] h-40 overflow-y-auto space-y-1 text-slate-300">
              {logs.map((log, i) => (
                <div key={i} className="leading-relaxed">
                  <span className="text-slate-600 select-none mr-2">
                    [{new Date().toLocaleTimeString()}]
                  </span>
                  <span className={log.includes('⚡') || log.includes('POWER') ? 'text-purple-300' : log.includes('💥') || log.includes('CRASH') ? 'text-rose-300' : log.includes('🏆') ? 'text-emerald-300' : 'text-slate-300'}>
                    {log}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
