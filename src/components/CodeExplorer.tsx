import React, { useState, useEffect } from 'react';
import { FileCode, Folder, Copy, Check, Download, FileText, ChevronRight, Terminal } from 'lucide-react';
import { FileTreeNode } from '../types';

export const CodeExplorer: React.FC = () => {
  const [tree, setTree] = useState<FileTreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string>('turnprog/progression.py');
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    fetch('/api/code/tree')
      .then((r) => r.json())
      .then((data) => setTree(data))
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    if (!selectedPath) return;
    setLoading(true);
    fetch(`/api/code/file?path=${encodeURIComponent(selectedPath)}`)
      .then((r) => r.json())
      .then((data) => setContent(data.content || ''))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [selectedPath]);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderTree = (nodes: FileTreeNode[], depth: number = 0) => {
    return nodes.map((node) => {
      const isSelected = selectedPath === node.path;
      if (node.type === 'directory') {
        return (
          <div key={node.path} className="space-y-0.5">
            <div
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 font-semibold select-none"
              style={{ paddingLeft: `${depth * 12 + 8}px` }}
            >
              <Folder className="w-3.5 h-3.5 text-indigo-400" />
              <span>{node.name}</span>
            </div>
            {node.children && renderTree(node.children, depth + 1)}
          </div>
        );
      }
      return (
        <button
          key={node.path}
          onClick={() => setSelectedPath(node.path)}
          className={`w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-mono text-left transition-all ${
            isSelected
              ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 font-semibold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {node.name.endsWith('.py') ? (
            <FileCode className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
          ) : (
            <FileText className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
      );
    });
  };

  return (
    <div className="space-y-6">
      {/* Intro Header */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileCode className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">Python Library Code Inspector</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
              Pure Python 3.10+
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Inspect the modules, classes, and tests implementing Carlson (1986).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy File'}</span>
          </button>
          <a
            href="/api/export/zip"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .zip</span>
          </a>
        </div>
      </div>

      {/* Editor & File Tree Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Tree */}
        <div className="lg:col-span-4 bg-slate-900/60 border border-slate-800 rounded-2xl p-3">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-2">
            Repository File Tree
          </div>
          <div className="space-y-0.5 max-h-[600px] overflow-y-auto">
            {renderTree(tree)}
          </div>
        </div>

        {/* Right: Code Viewer */}
        <div className="lg:col-span-8 bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden flex flex-col">
          {/* File bar */}
          <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
              <FileCode className="w-4 h-4 text-amber-400" />
              <span>{selectedPath}</span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">
              {content ? `${content.split('\n').length} lines` : ''}
            </span>
          </div>

          {/* Code content */}
          <div className="p-4 bg-slate-950 flex-1 overflow-x-auto max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="py-20 text-center text-xs text-slate-500">Loading file...</div>
            ) : (
              <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre">
                {content}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
