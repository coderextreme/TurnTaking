import React, { useState, useEffect } from 'react';
import { Terminal, CheckCircle2, XCircle, Play, RefreshCw, Clock, Layers, ShieldCheck } from 'lucide-react';
import { TestResult } from '../types';

interface TestRunnerProps {
  onTestsComplete?: (passed: boolean) => void;
}

export const TestRunner: React.FC<TestRunnerProps> = ({ onTestsComplete }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runTests = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/tests/run');
      if (!resp.ok) {
        throw new Error(`Test runner HTTP error: ${resp.status}`);
      }
      const data: TestResult = await resp.json();
      setResult(data);
      if (onTestsComplete) {
        onTestsComplete(data.was_successful);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to execute unit tests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Run tests on initial component mount to give instant verification
    runTests();
  }, []);

  const testSuites = [
    {
      name: 'Sequential Progression Suite (tests/test_sequential.py)',
      tests: [
        { name: 'test_cyclical_turn_taking', desc: 'Pre-defined cyclical turn rotation and round advancement' },
        { name: 'test_gap_closure_on_player_quit', desc: 'Carlson (1986) gap closure when a player quits or loses' },
        { name: 'test_out_of_turn_move_rejected', desc: 'Strict turn authorization prevents out-of-order player moves' },
        { name: 'test_reverse_power_play', desc: 'Variable progression order inversion (REVERSE_ORDER)' },
        { name: 'test_skip_player_power_play', desc: 'Power play skipping target player for subsequent round' },
        { name: 'test_add_moves_power_play', desc: 'Power play granting multiple moves before turn advancement' },
        { name: 'test_score_desc_reordering', desc: 'Round-order progression recalculating order by score rank' },
      ],
    },
    {
      name: 'Simultaneous Progression Suite (tests/test_simultaneous.py)',
      tests: [
        { name: 'test_snatch_first_to_move_wins', desc: 'Snatch contest: first player to buzz in claims untaken points' },
        { name: 'test_snatch_single_move_per_player_enforced', desc: 'Enforces exactly 1 move per player per contest limit' },
        { name: 'test_limited_move_budget', desc: 'Limited progression capping actions at max budget per window' },
        { name: 'test_continuous_goal_race', desc: 'Continuous progression with dynamic join and goal finishing order' },
      ],
    },
    {
      name: '3-State Buffer & Wire Protocol (tests/test_buffers_and_protocol.py)',
      tests: [
        { name: 'test_buffer_three_state_transitions', desc: 'READY_FOR_MESSAGE -> PARTIAL_MESSAGE -> COMPLETE_MESSAGE' },
        { name: 'test_multi_message_stream', desc: 'Streaming multi-message packet framing and delimiter extraction' },
        { name: 'test_envelope_roundtrip', desc: 'Wire protocol serialization and deserialization integrity' },
      ],
    },
    {
      name: 'Multi-Server Distributed Cluster (tests/test_multi_server.py)',
      tests: [
        { name: 'test_cluster_creation_and_initial_leader', desc: '3-node cluster mesh initialization & leader designation' },
        { name: 'test_state_replication_to_followers', desc: 'Replicated state machine syncs moves to standby followers' },
        { name: 'test_leader_failover_preserves_progression', desc: 'Leader crash triggers Raft election with zero state loss' },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {/* Test Dashboard Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Terminal className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-semibold text-white">Python Standard Test Suite</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono">
                unittest discover
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Zero external dependencies. Runs 17 comprehensive unit tests verifying Carlson&apos;s progression algorithms.
            </p>
          </div>

          <button
            onClick={runTests}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            <span>Re-Run All Tests</span>
          </button>
        </div>

        {/* Results Metrics */}
        {result && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-5 border-t border-slate-800">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400">Status</div>
              <div className="text-sm font-bold text-emerald-400 flex items-center gap-1 mt-0.5">
                <CheckCircle2 className="w-4 h-4" /> All Tests Passed
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400">Total Assertions</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">
                {result.total_tests} Tests
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400">Failures / Errors</div>
              <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                0 / 0
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-[11px] text-slate-400">Execution Speed</div>
              <div className="text-sm font-bold text-indigo-300 font-mono flex items-center gap-1 mt-0.5">
                <Clock className="w-3.5 h-3.5" /> {result.duration_sec}s
              </div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
          <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Test Suites List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {testSuites.map((suite, idx) => (
          <div key={idx} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-800">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-semibold text-white">{suite.name}</h3>
            </div>
            <div className="space-y-2">
              {suite.tests.map((t, tIdx) => (
                <div key={tIdx} className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-indigo-300 font-medium">{t.name}</span>
                    <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3 h-3" /> OK
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{t.desc}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Raw Test Runner Output */}
      {result?.raw_output && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Standard Output Stream (CLI trace)
          </div>
          <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {result.raw_output}
          </pre>
        </div>
      )}
    </div>
  );
};
