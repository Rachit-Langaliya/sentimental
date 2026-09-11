"use client";

import { Network, GitFork, Users, Share2 } from "lucide-react";

export default function NetworkPage() {
  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-ink">Network Analysis</h1>
        <p className="text-sm text-ink-2 mt-0.5">Influence propagation, community detection, and bridge actors</p>
      </div>

      {/* Phase placeholder */}
      <div className="bg-surface border border-bdr rounded-xl p-8 flex flex-col items-center text-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center">
          <Network className="w-8 h-8 text-accent" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-ink">Coming in Phase 7</h2>
          <p className="text-sm text-ink-2 mt-1 max-w-md">
            Interactive network graph with Sigma.js showing influence propagation, Louvain community detection, PageRank-ranked influencers, and cross-community bridge actors.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-4 w-full max-w-md mt-2">
          {[
            { icon: Users, label: "Community Detection", note: "Louvain algorithm" },
            { icon: Share2, label: "Influence Ranking", note: "PageRank + betweenness" },
            { icon: GitFork, label: "Bridge Actors", note: "Cross-community links" },
          ].map(({ icon: Icon, label, note }) => (
            <div key={label} className="bg-bg border border-bdr rounded-xl p-4 text-center">
              <Icon className="w-5 h-5 text-ink-3 mx-auto mb-2" />
              <p className="text-xs font-semibold text-ink">{label}</p>
              <p className="text-[10px] text-ink-3 mt-0.5">{note}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture preview */}
      <div className="bg-surface border border-bdr rounded-xl p-5">
        <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">Planned Architecture</p>
        <div className="space-y-2 text-xs">
          {[
            "NetworkX for graph computation (PageRank, betweenness centrality)",
            "PostgreSQL graph storage — co-mention and repost edges",
            "Sigma.js WebGL rendering — handles 100K+ node graphs interactively",
            "Community detection via python-louvain (Louvain modularity)",
            "Narrative diffusion timeline per community cluster",
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-bg border border-bdr rounded-lg">
              <span className="text-accent font-mono flex-shrink-0">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-ink-2">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
