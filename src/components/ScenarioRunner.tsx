import React, { useState } from 'react';
import { Play, CheckCircle2, Cpu, ArrowRight, RefreshCw, Layers, ShieldCheck, Terminal } from 'lucide-react';
import { ScenarioResult } from '../types';

export const ScenarioRunner: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<string>('predefined');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const scenarios = [
    {
      id: 'predefined',
      title: '1. Predefined Sequential Progression',
      category: 'Sequential',
      desc: 'Fixed cyclical player order. Alice moves, Bob moves, Dave quits abruptly. Verifies immediate gap closure and next player promotion without turn loss.',
    },
    {
      id: 'variable',
      title: '2. Variable Progression with Power Plays',
      category: 'Sequential',
      desc: 'Dynamic order modification via power plays: REVERSE_ORDER, SKIP_PLAYER, and ADD_MOVES. Demonstrates Carlson stacking and modification rules.',
    },
    {
      id: 'round_order',
      title: '3. Round-Order Progression',
      category: 'Sequential',
      desc: 'Turn order recalculated after every round based on performance/scores (like golf honors or draft order). Demonstrates score-descending re-ordering.',
    },
    {
      id: 'snatch',
      title: '4. Snatch Progression (Simultaneous)',
      category: 'Simultaneous',
      desc: 'Simultaneous 1-move contest where multiple clients race to claim unclaimed points. Master orders by millisecond-precision arrival timestamp.',
    },
    {
      id: 'cluster_failover',
      title: '5. Multi-Server Cluster Failover',
      category: 'Distributed System',
      desc: '3-node server cluster with Raft log replication. Primary Leader crashes; standby node detects timeout, wins election, and resumes turns seamlessly.',
    },
  ];

  const handleRun = async (scId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/scenarios/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scId }),
      });
      if (!resp.ok) {
        throw new Error(`Execution error: ${resp.statusText}`);
      }
      const data = await resp.json();
      setResult(data);
      setSelectedScenario(scId);
    } catch (err: any) {
      setError(err.message || 'Failed to execute Python scenario');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro Header */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <h2 className="text-base font-semibold text-white">Automated Python Scenario Testbed</h2>
        </div>
        <p className="text-xs text-slate-400">
          Executes the Python library algorithms live on the backend server (`turnprog/scenarios.py`) and returns complete event sequences and state trees.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Scenario Selection Cards */}
        <div className="lg:col-span-5 space-y-3">
          {scenarios.map((sc) => {
            const isSelected = selectedScenario === sc.id;
            return (
              <div
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-900/40 border-slate-800 hover:bg-slate-900/70'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-white">{sc.title}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-slate-800 text-slate-300 border border-slate-700">
                    {sc.category}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{sc.desc}</p>
                <div className="mt-3 flex items-center justify-between">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRun(sc.id);
                    }}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
                  >
                    {loading && selectedScenario === sc.id ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5 fill-white" />
                    )}
                    <span>Run Python Scenario</span>
                  </button>
                  {result && selectedScenario === sc.id && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Executed
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Results & Execution Log */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 h-full flex flex-col">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Scenario Output & Audit Log</h3>
              </div>
              {result && (
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  State Version: #{result.final_state.state_version}
                </span>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300">
                {error}
              </div>
            )}

            {!result && !loading && !error && (
              <div className="flex-1 flex flex-col items-center justify-center py-16 text-center text-slate-500">
                <Cpu className="w-10 h-10 mb-2 opacity-40" />
                <p className="text-xs">Select a scenario on the left and click &ldquo;Run Python Scenario&rdquo;.</p>
              </div>
            )}

            {loading && (
              <div className="flex-1 flex flex-col items-center justify-center py-16 text-center text-slate-400">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-400 mb-2" />
                <p className="text-xs">Running Python execution via `cli_runner.py`...</p>
              </div>
            )}

            {result && !loading && (
              <div className="space-y-4 flex-1">
                <div>
                  <h4 className="text-xs font-semibold text-white">{result.scenario}</h4>
                  <p className="text-xs text-slate-400">{result.description}</p>
                </div>

                {/* Event execution steps */}
                <div>
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Execution Steps:
                  </div>
                  <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 font-mono text-[11px] space-y-1.5 max-h-60 overflow-y-auto text-slate-300">
                    {result.log.map((step, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-slate-600 select-none">{idx + 1}.</span>
                        <span className={step.includes('POWER') || step.includes('REVERSE') ? 'text-purple-300' : step.includes('CRASH') ? 'text-rose-300' : step.includes('GAP') ? 'text-amber-300' : 'text-slate-200'}>
                          {step}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Final State Snapshot */}
                <div>
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Final Game State Snapshot:
                  </div>
                  <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 text-[11px] font-mono max-h-48 overflow-y-auto text-emerald-400">
                    <pre>{JSON.stringify(result.final_state, null, 2)}</pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
