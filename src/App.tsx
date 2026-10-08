/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Header } from './components/Header';
import { Simulator } from './components/Simulator';
import { ScenarioRunner } from './components/ScenarioRunner';
import { TestRunner } from './components/TestRunner';
import { CodeExplorer } from './components/CodeExplorer';
import { PaperReference } from './components/PaperReference';

export default function App() {
  const [activeTab, setActiveTab] = useState<'simulator' | 'scenarios' | 'tests' | 'code' | 'paper'>('simulator');
  const [testsPassed, setTestsPassed] = useState<boolean | null>(true);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        testsPassed={testsPassed}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'simulator' && <Simulator />}
        {activeTab === 'scenarios' && <ScenarioRunner />}
        {activeTab === 'tests' && <TestRunner onTestsComplete={(passed) => setTestsPassed(passed)} />}
        {activeTab === 'code' && <CodeExplorer />}
        {activeTab === 'paper' && <PaperReference />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>
            Based on <span className="text-slate-400 font-medium">&ldquo;Designing Multi-player Games: Player Progression and Interface&rdquo;</span> by John Carlson (August 20, 1986).
          </p>
          <div className="flex items-center gap-4 text-slate-400">
            <span>Pure Python 3.10+ Standard Library</span>
            <span>&bull;</span>
            <a
              href="https://coderextreme.net/TurnTaking.html"
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 hover:text-indigo-300 underline"
            >
              Original 1986 Paper
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
