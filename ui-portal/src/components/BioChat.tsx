"use client";

import { useState } from "react";

export default function BioChat() {
  const [input, setInput] = useState("");

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    // In actual implementation, send `input` payload to `/intelligence` FastMCP
    setInput("");
  };

  return (
    <aside className="w-80 h-full bg-surface-container-low border-l border-outline-variant/15 flex flex-col shrink-0">
      <div className="p-6 border-b border-outline-variant/10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
            Intelligence
          </span>
          <span className="text-[10px] font-mono text-tertiary bg-tertiary/10 px-1.5 rounded">
            MCP ONLINE
          </span>
        </div>
        <h3 className="text-xl font-headline font-bold text-on-surface mb-1">
          Bio-Chat Assistant
        </h3>
        <p className="text-xs text-on-surface-variant leading-relaxed opacity-80">
          Query the knowledge graph and RAG context via FastMCP.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 space-y-4">
        {/* Sample Message from Assistant */}
        <div className="bg-surface-container-lowest p-3 rounded-md border border-outline-variant/10">
          <p className="text-[11px] leading-relaxed text-on-surface-variant mb-2">
            I found evidence linking <span className="text-primary font-mono">CYP3A4</span> to drug metabolism pathways in liver.
          </p>
          <span className="text-[9px] text-tertiary font-mono">Source: UniProt & Reactome</span>
        </div>
      </div>

      <div className="p-6 bg-surface-container-lowest border-t border-outline-variant/10">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-10 h-10 rounded bg-secondary-container flex items-center justify-center">
            <span className="material-symbols-outlined text-secondary">science</span>
          </div>
          <div>
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-tighter">
              Analysis Engine
            </p>
            <p className="text-xs font-semibold text-secondary">Awaiting Query</p>
          </div>
        </div>
        <form onSubmit={handleSend} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Bio-Chat..."
            className="w-full bg-surface-container-high border-none rounded-md py-2.5 px-3 text-xs text-on-surface placeholder:text-outline focus:ring-1 focus:ring-primary outline-none"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-primary p-1 hover:bg-primary/10 rounded-full transition-colors flex items-center justify-center"
          >
            <span className="material-symbols-outlined text-sm">send</span>
          </button>
        </form>
      </div>
    </aside>
  );
}
