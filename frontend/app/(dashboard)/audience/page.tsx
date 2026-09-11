"use client";

import { useEffect, useState } from "react";
import { Users, ChevronRight, Activity } from "lucide-react";
import { segmentsApi, type SegmentSummary, type SegmentDetail } from "@/lib/api";
import { fmtNumber, fmtPct, confidenceBadge, confidenceColor } from "@/lib/utils";
import { cn } from "@/lib/utils";

function EpistemicBadge({ label }: { label: "Observed" | "Inferred" | "Modeled" }) {
  const colors = {
    Observed: "bg-success/15 text-success border-success/30",
    Inferred: "bg-accent/15 text-accent border-accent/30",
    Modeled: "bg-ink-3/20 text-ink-2 border-bdr",
  };
  return (
    <span className={cn("text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border", colors[label])}>
      {label}
    </span>
  );
}

function SegmentCard({ segment, onClick, active }: {
  segment: SegmentSummary; onClick: () => void; active: boolean;
}) {
  const sent = segment.sentiment_profile as any;
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-4 rounded-xl border transition-all",
        active
          ? "bg-accent/10 border-accent/40"
          : "bg-surface border-bdr hover:bg-surface-2"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-semibold text-ink leading-tight">{segment.name}</p>
        <ChevronRight className={cn("w-4 h-4 flex-shrink-0 mt-0.5 transition-transform", active && "rotate-90")} style={{ color: active ? "#D97706" : "#64748B" }} />
      </div>
      <p className="text-xs text-ink-3 mb-3 line-clamp-2">{segment.description}</p>
      <div className="flex items-center justify-between text-xs">
        <div>
          <span className="text-ink-2">{fmtNumber(segment.size_estimate ?? 0)}</span>
          <span className="text-ink-3"> users · </span>
          <span className="text-ink-2">{segment.dominant_language}</span>
        </div>
        <span className={cn("font-semibold", confidenceColor(segment.confidence))}>
          {confidenceBadge(segment.confidence)} conf.
        </span>
      </div>
      {sent && (
        <div className="mt-2 flex h-1.5 rounded-full overflow-hidden gap-0.5">
          <div className="bg-success rounded-l-full" style={{ width: fmtPct(sent.positive || 0) }} />
          <div className="bg-ink-3" style={{ width: fmtPct(sent.neutral || 0) }} />
          <div className="bg-danger rounded-r-full" style={{ width: fmtPct(sent.negative || 0) }} />
        </div>
      )}
    </button>
  );
}

function PersonaPanel({ detail }: { detail: SegmentDetail }) {
  const persona = detail.persona;
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-bold text-ink">{detail.name}</h2>
        <p className="text-xs text-ink-3 mt-0.5">{fmtNumber(detail.size_estimate ?? 0)} estimated users · {detail.evidence_count.toLocaleString()} evidence posts</p>
      </div>

      {/* Epistemic labels */}
      <div className="flex gap-2 flex-wrap">
        <EpistemicBadge label="Observed" />
        <EpistemicBadge label="Inferred" />
        <EpistemicBadge label="Modeled" />
        <span className="text-[10px] text-ink-3 ml-1 self-center">All attributes labeled by source</span>
      </div>

      {/* Sentiment profile */}
      {detail.sentiment_profile && (
        <div className="bg-bg rounded-xl border border-bdr p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">
            Sentiment Profile <EpistemicBadge label="Observed" />
          </p>
          <div className="flex h-2.5 rounded-full overflow-hidden gap-0.5 mb-2">
            <div className="bg-success rounded-l-full" style={{ width: fmtPct((detail.sentiment_profile as any).positive || 0) }} />
            <div className="bg-ink-3" style={{ width: fmtPct((detail.sentiment_profile as any).neutral || 0) }} />
            <div className="bg-danger rounded-r-full" style={{ width: fmtPct((detail.sentiment_profile as any).negative || 0) }} />
          </div>
          <div className="flex gap-4 text-xs">
            {["positive", "neutral", "negative"].map((k) => (
              <span key={k} className="text-ink-2">
                <span className="font-semibold text-ink">{fmtPct((detail.sentiment_profile as any)[k] || 0)}</span> {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Persona summary */}
      {persona?.summary && (
        <div className="bg-bg rounded-xl border border-bdr p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">AI-Generated Summary</p>
            <EpistemicBadge label="Modeled" />
          </div>
          <p className="text-sm text-ink-2 leading-relaxed">{persona.summary}</p>
          <div className="mt-3 flex items-center gap-3 text-xs text-ink-3">
            <span>Confidence: <span className={cn("font-semibold", confidenceColor(persona.confidence))}>{fmtPct(persona.confidence)}</span></span>
            <span>Evidence: <span className="text-ink-2 font-semibold">{detail.evidence_count.toLocaleString()} posts</span></span>
          </div>
        </div>
      )}

      {/* Interests */}
      {persona?.interests && persona.interests.length > 0 && (
        <div className="bg-bg rounded-xl border border-bdr p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">Interests</p>
            <EpistemicBadge label="Inferred" />
          </div>
          <div className="flex flex-wrap gap-2">
            {persona.interests.map((interest) => (
              <span key={interest} className="text-xs px-2.5 py-1 bg-surface-2 border border-bdr rounded-full text-ink-2">
                {interest}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reaction profile */}
      {persona?.reaction && (
        <div className="bg-bg rounded-xl border border-bdr p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">Reaction Intensity by Topic</p>
            <EpistemicBadge label="Inferred" />
          </div>
          <div className="space-y-2">
            {Object.entries(persona.reaction).map(([topic, score]) => (
              <div key={topic}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-ink-2 capitalize">{topic.replace(/_/g, " ")}</span>
                  <span className="text-xs font-semibold text-ink tabular-nums">{((score as number) * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full" style={{ width: `${(score as number) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Geo distribution */}
      {detail.geo_distribution && (
        <div className="bg-bg rounded-xl border border-bdr p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">Geographic Distribution</p>
            <EpistemicBadge label="Observed" />
          </div>
          <div className="space-y-1.5">
            {Object.entries(detail.geo_distribution).map(([state, pct]) => (
              <div key={state} className="flex justify-between text-xs">
                <span className="text-ink-2">{state}</span>
                <span className="font-semibold text-ink tabular-nums">{pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AudiencePage() {
  const [segments, setSegments] = useState<SegmentSummary[]>([]);
  const [selected, setSelected] = useState<SegmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    segmentsApi.list().then((r) => {
      setSegments(r.data.items);
      setLoading(false);
      if (r.data.items.length > 0) loadDetail(r.data.items[0].id);
    }).catch(() => setLoading(false));
  }, []);

  function loadDetail(id: number) {
    setDetailLoading(true);
    segmentsApi.get(id).then((r) => {
      setSelected(r.data);
      setDetailLoading(false);
    }).catch(() => setDetailLoading(false));
  }

  return (
    <div className="p-6 flex flex-col h-full">
      <div className="mb-5">
        <h1 className="text-xl font-bold text-ink">Audience Intelligence</h1>
        <p className="text-sm text-ink-2 mt-0.5">Demographic segment profiles with AI-generated persona summaries</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex gap-5 flex-1 min-h-0">
          {/* Segments list */}
          <div className="w-72 flex-shrink-0 space-y-2 overflow-y-auto">
            <p className="text-[10px] font-bold text-ink-3 uppercase tracking-widest px-1">{segments.length} segments</p>
            {segments.map((s) => (
              <SegmentCard key={s.id} segment={s} active={selected?.id === s.id} onClick={() => loadDetail(s.id)} />
            ))}
            {segments.length === 0 && (
              <div className="text-center py-12 text-ink-3 text-sm">
                <Users className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No segments yet. Data ingestion will populate segments.
              </div>
            )}
          </div>

          {/* Detail panel */}
          <div className="flex-1 bg-surface border border-bdr rounded-xl p-5 overflow-y-auto">
            {detailLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            ) : selected ? (
              <PersonaPanel detail={selected} />
            ) : (
              <div className="flex items-center justify-center h-full text-ink-3 text-sm">
                Select a segment to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
