import React from 'react';
import { BookOpen, ExternalLink, GitBranch, ArrowRight, CheckCircle2, ShieldAlert, Cpu, Layers } from 'lucide-react';

export const PaperReference: React.FC = () => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="w-5 h-5 text-indigo-400" />
              <h2 className="text-xl font-bold text-white">
                Designing Multi-player Games: Player Progression and Interface
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              By <span className="text-slate-200 font-semibold">John Carlson</span> &bull; August 20, 1986
            </p>
          </div>

          <a
            href="https://coderextreme.net/TurnTaking.html"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all self-start md:self-auto"
          >
            <span>View Original Paper</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-800 text-xs text-slate-300 leading-relaxed">
          <p className="italic bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 text-slate-400">
            &ldquo;This paper discusses methods of player progression and sketches out algorithms for machine implementation. It also discusses how a game master communicates with the players depending on which method of player progression is used... Making a general master requires formal definition of player progression, the order in which players take their turns during one part of the game.&rdquo;
          </p>
        </div>
      </div>

      {/* Two Pillars: Sequential vs Simultaneous */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pillar 1: Sequential */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-bold text-white">Sequential Player Progression</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Restricted to one player at a time in a deterministic order. Each player has the power to halt progression by withholding an action until timeout.
          </p>

          <div className="space-y-3">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-indigo-300">1. Pre-defined Progression</div>
              <p className="text-xs text-slate-400 mt-1">
                Fixed order established at the start. 1 move per turn. When a player quits or loses, <span className="text-slate-200 font-semibold">the gap closes immediately</span> and remaining players shift forward.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-purple-300">2. Variable Progression (Power Plays)</div>
              <p className="text-xs text-slate-400 mt-1">
                Player order modified dynamically through in-game power plays:
                <span className="block mt-1 text-slate-300 font-mono text-[11px]">
                  &bull; ADD_MOVES, TAKE_MOVES<br />
                  &bull; REVERSE_ORDER, SKIP_PLAYER<br />
                  &bull; CANCEL_POWER_PLAY, SWAP_ORDER
                </span>
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-emerald-300">3. Round-Order Progression</div>
              <p className="text-xs text-slate-400 mt-1">
                Order recalculated after each round (like golf honors or sports drafts): sorted by previous round score, cumulative score, or autocratic decision.
              </p>
            </div>
          </div>
        </div>

        {/* Pillar 2: Simultaneous */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-bold text-white">Simultaneous Player Progression</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Players make moves concurrently in an undefined order within discrete competition units called <span className="text-slate-200 font-semibold">Contests</span>.
          </p>

          <div className="space-y-3">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-amber-300">1. Snatch Progression</div>
              <p className="text-xs text-slate-400 mt-1">
                Allows <span className="text-slate-200 font-semibold">exactly 1 move per player per contest</span>. Used in trivia buzzers, slapping, or claiming unclaimed points in Cribbage. First or last to move wins.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-blue-300">2. Limited Progression</div>
              <p className="text-xs text-slate-400 mt-1">
                Players can take several moves up to a fixed budget or time window. Examples include auctions, wagering rounds in casino games, or action-point pools.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold text-rose-300">3. Continuous Progression</div>
              <p className="text-xs text-slate-400 mt-1">
                Unlimited moves within physical/network limits. Players join or drop out dynamically. Reaching target milestones generates winning and losing orders.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* The 8-Step Game Master Algorithm & 3-State Buffers */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
        <h3 className="text-base font-bold text-white">
          The Generic Game Master Algorithm (Section 3 of Paper)
        </h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          The paper formalizes the core loop executed by the authoritative Game Master:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 1</span>
            <div className="text-slate-300 mt-1">Decide which player(s) are next</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 2</span>
            <div className="text-slate-300 mt-1">Prompt player(s) if necessary</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 3</span>
            <div className="text-slate-300 mt-1">Order players / queue arrival signals</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 4</span>
            <div className="text-slate-300 mt-1">Get player input from 3-state buffer</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 5</span>
            <div className="text-slate-300 mt-1">Process input & execute move</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 6</span>
            <div className="text-slate-300 mt-1">Prompt for more input if incomplete</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 7</span>
            <div className="text-slate-300 mt-1">Output state updates to all players</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-indigo-400 font-bold">Step 8</span>
            <div className="text-slate-300 mt-1">Loop back to Step 1</div>
          </div>
        </div>

        {/* Distributed Extension */}
        <div className="mt-4 pt-4 border-t border-slate-800">
          <h4 className="text-sm font-semibold text-white mb-2">
            Multi-Server Architecture Extension in TurnProg
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            In 1986, Carlson envisioned a single machine or BSD Unix `select(2)` multiplexer. TurnProg elevates this to a modern <span className="text-emerald-400 font-semibold">replicated multi-server cluster</span>:
          </p>
          <ul className="mt-2 space-y-1.5 text-xs text-slate-400 list-disc list-inside">
            <li><strong className="text-slate-200">Replicated State Machine:</strong> All game moves and power plays are appended to an ordered distributed log replicated to standby servers.</li>
            <li><strong className="text-slate-200">Raft-Style Leader Election:</strong> If the primary Game Master node fails or partitions, follower nodes trigger an election within 3 seconds and preserve turn progression without state loss.</li>
            <li><strong className="text-slate-200">Edge Client Routing:</strong> Clients connect to local edge proxies that route messages transparently to whichever node is currently leader.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
