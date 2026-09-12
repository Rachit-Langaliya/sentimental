"use client";

import { useEffect, useState } from "react";
import { Users, ChevronRight, RefreshCw, Globe, BarChart2, Clock, Cpu, Loader2, Sparkles } from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, Tooltip,
} from "recharts";
import { segmentsApi, personaApi, type SegmentSummary, type SegmentDetail } from "@/lib/api";
import { fmtNumber, fmtPct, sentimentColor } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { toast } from "sonner";

// ── Confidence bar ─────────────────────────────────────────────────────────────
function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "bg-success" : pct >= 40 ? "bg-warning" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] tabular-nums text-ink-3">{pct}%</span>
    </div>
  );
}

// ── Segment row ────────────────────────────────────────────────────────────────
function SegmentRow({ seg, active, onClick }: { seg: SegmentSummary; active: boolean; onClick: () => void }) {
  const sp = seg.sentiment_profile;
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left px-4 py-3.5 border-b border-bdr transition-colors",
        active ? "bg-accent/8 border-l-2 border-l-accent" : "hover:bg-surface-2"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-accent/15 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Users className="w-4 h-4 text-accent" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink leading-snug mb-1 line-clamp-2">{seg.name}</p>
          <div className="flex items-center gap-3 flex-wrap">
            {seg.dominant_language && (
              <span className="flex items-center gap-1 text-[10px] text-ink-3">
                <Globe className="w-3 h-3" />{seg.dominant_language}
              </span>
            )}
            {seg.size_estimate != null && (
              <span className="text-[10px] text-ink-3">{fmtNumber(seg.size_estimate)} authors</span>
            )}
            <span className="text-[10px] text-ink-3">{fmtNumber(seg.evidence_count)} posts</span>
          </div>
          {sp && (
            <div className="flex gap-2 mt-2">
              <span className="text-[10px] text-success">{fmtPct(sp.positive)} pos</span>
              <span className="text-[10px] text-ink-3">{fmtPct(sp.neutral)} neu</span>
              <span className="text-[10px] text-danger">{fmtPct(sp.negative)} neg</span>
            </div>
          )}
        </div>
        <ChevronRight className={cn("w-4 h-4 flex-shrink-0 mt-1 transition-transform", active ? "rotate-90 text-accent" : "text-ink-3")} />
      </div>
    </button>
  );
}

// ── Detail panel ───────────────────────────────────────────────────────────────
function DetailPanel({ detail, onPersonaRegenerated }: {
  detail: SegmentDetail;
  onPersonaRegenerated: (id: number, summary: string) => void;
}) {
  const [timeline, setTimeline] = useState<{ date: string; positive: number; neutral: number; negative: number }[]>([]);
  const [regenerating, setRegenerating] = useState(false);
  const [localPersonaSummary, setLocalPersonaSummary] = useState<string | null>(null);

  useEffect(() => {
    segmentsApi.timeline(detail.id).then((r: any) => setTimeline(r.data.points)).catch(() => {});
    setLocalPersonaSummary(null);
  }, [detail.id]);

  async function handleRegeneratePersona() {
    setRegenerating(true);
    try {
      const { data } = await personaApi.regenerate(detail.id);
      setLocalPersonaSummary(data.persona_summary);
      onPersonaRegenerated(detail.id, data.persona_summary);
      toast.success("Persona regenerated with local LLM");
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? "Failed — check Ollama is running";
      toast.error(msg);
    } finally {
      setRegenerating(false);
    }
  }

  const sp = detail.sentiment_profile || { positive: 0, neutral: 0, negative: 0 };
  const tp = detail.topic_prefs || {};
  const ap = detail.activity_profile || {};

  const radarData = Object.entries(tp).slice(0, 6).map(([name, value]) => ({
    subject: name.replace(" & ", " & ").replace("Electric Vehicles", "EVs"),
    value: Math.round((value as number) * 100),
  }));

  const chartData = timeline.map((p) => ({
    date: format(new Date(p.date), "dd MMM"),
    Positive: +(p.positive * 100).toFixed(1),
    Neutral: +(p.neutral * 100).toFixed(1),
    Negative: +(p.negative * 100).toFixed(1),
  }));

  const activityBands = Object.entries(ap)
    .filter(([k]) => k !== "peak_band")
    .map(([k, v]) => ({ period: k, pct: Math.round((v as number) * 100) }));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-base font-bold text-ink leading-snug">{detail.name}</h2>
        {detail.description && (
          <p className="text-xs text-ink-2 mt-1.5 leading-relaxed">{detail.description}</p>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Authors", value: fmtNumber(detail.size_estimate ?? 0) },
          { label: "Posts", value: fmtNumber(detail.evidence_count) },
          { label: "Language", value: detail.dominant_language ?? "—" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-bg border border-bdr rounded-lg p-3 text-center">
            <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-0.5">{label}</p>
            <p className="text-sm font-bold text-ink">{value}</p>
          </div>
        ))}
      </div>

      {/* Confidence */}
      <div className="bg-bg border border-bdr rounded-lg p-3">
        <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-1.5">Model Confidence</p>
        <ConfBar value={detail.confidence} />
      </div>

      {/* Sentiment breakdown */}
      <div className="bg-surface border border-bdr rounded-xl p-4">
        <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">Sentiment Profile</p>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Positive", value: sp.positive, cls: "text-success" },
            { label: "Neutral", value: sp.neutral, cls: "text-ink-2" },
            { label: "Negative", value: sp.negative, cls: "text-danger" },
          ].map(({ label, value, cls }) => (
            <div key={label} className="text-center">
              <p className={cn("text-lg font-bold tabular-nums", cls)}>{fmtPct(value as number)}</p>
              <p className="text-[10px] text-ink-3">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Topic radar */}
      {radarData.length > 0 && (
        <div className="bg-surface border border-bdr rounded-xl p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">Topic Interests</p>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
              <PolarGrid stroke="#263450" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748B", fontSize: 10 }} />
              <Radar dataKey="value" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.25} strokeWidth={1.5} dot={false} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Activity profile */}
      {activityBands.length > 0 && (
        <div className="bg-surface border border-bdr rounded-xl p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />Activity Pattern
          </p>
          <div className="space-y-2">
            {activityBands.map(({ period, pct }) => (
              <div key={period} className="flex items-center gap-3">
                <span className="text-[11px] text-ink-3 capitalize w-20">{period}</span>
                <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
                  <div className="h-full bg-accent/60 rounded-full" style={{ width: `${Math.min(pct * 3, 100)}%` }} />
                </div>
                <span className="text-[10px] tabular-nums text-ink-3 w-8 text-right">{pct}%</span>
              </div>
            ))}
          </div>
          {ap.peak_band && (
            <p className="text-[10px] text-ink-3 mt-2">Peak: <span className="text-ink capitalize">{ap.peak_band as string}</span></p>
          )}
        </div>
      )}

      {/* 7-day sentiment timeline */}
      {chartData.length > 0 && (
        <div className="bg-surface border border-bdr rounded-xl p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">7-Day Sentiment</p>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: "#64748B", fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip
                contentStyle={{ background: "#1C2D44", border: "1px solid #263450", borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: "#94A3B8" }}
              />
              <Area type="monotone" dataKey="Positive" stroke="#10B981" fill="url(#gp)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="Negative" stroke="#EF4444" fill="url(#gn)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Persona summary */}
      {detail.persona && (
        <div className="bg-surface border border-bdr rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">Persona</p>
            <button
              onClick={handleRegeneratePersona}
              disabled={regenerating}
              title="Regenerate persona summary using local LLM (requires Ollama)"
              className="flex items-center gap-1.5 text-[10px] font-semibold px-2.5 py-1 bg-surface-2 border border-bdr rounded-full text-ink-3 hover:text-accent hover:border-accent/40 transition-colors disabled:opacity-50"
            >
              {regenerating
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <Cpu className="w-3 h-3" />}
              {regenerating ? "Generating…" : "Regenerate with LLM"}
            </button>
          </div>
          {localPersonaSummary && (
            <div className="flex items-start gap-2 bg-success/8 border border-success/25 rounded-lg px-3 py-2">
              <Sparkles className="w-3 h-3 text-success flex-shrink-0 mt-0.5" />
              <p className="text-xs text-success font-medium">Updated by local LLM</p>
            </div>
          )}
          <p className="text-sm text-ink leading-relaxed">{localPersonaSummary ?? detail.persona.summary}</p>
          {detail.persona.interests && detail.persona.interests.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {detail.persona.interests.map((i: string) => (
                <span key={i} className="text-[10px] px-2 py-0.5 bg-accent/10 text-accent rounded-full">{i}</span>
              ))}
            </div>
          )}
          {detail.persona.reaction && (
            <div className="grid grid-cols-3 gap-2 pt-1">
              {Object.entries(detail.persona.reaction).map(([k, v]) => (
                <div key={k} className="text-center">
                  <p className="text-sm font-bold tabular-nums text-ink">{fmtPct(v as number)}</p>
                  <p className="text-[9px] text-ink-3 capitalize">{k.replace(/_/g, " ")}</p>
                </div>
              ))}
            </div>
          )}
          <p className="text-[10px] text-ink-3">
            Influence score: {fmtPct(detail.persona.influence_score ?? 0)} · Confidence: {fmtPct(detail.persona.confidence)}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────
function EmptyState({ onTrigger, loading }: { onTrigger: () => void; loading: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center">
        <Users className="w-8 h-8 text-accent/50" />
      </div>
      <div>
        <p className="text-sm font-semibold text-ink">No segments yet</p>
        <p className="text-xs text-ink-3 mt-1 max-w-64">
          Segments are built from ingested post data. Trigger an ingestion cycle first, then run segmentation.
        </p>
      </div>
      <button
        onClick={onTrigger}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
      >
        {loading ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <RefreshCw className="w-4 h-4" />}
        Run Segmentation
      </button>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function SegmentsPage() {
  const [segments, setSegments] = useState<SegmentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<SegmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  async function loadSegments() {
    try {
      const { data } = await segmentsApi.list();
      setSegments(data.items);
      setTotal(data.total);
    } catch {
      setSegments([]);
    } finally {
      setLoading(false);
    }
  }

  async function selectSegment(id: number) {
    try {
      const { data } = await segmentsApi.get(id);
      setSelected(data);
    } catch {}
  }

  async function triggerSegmentation() {
    setTriggering(true);
    try {
      await fetch("/api/v1/segments/trigger-segmentation", { method: "POST" });
      setTimeout(() => { loadSegments(); setTriggering(false); }, 2000);
    } catch { setTriggering(false); }
  }

  useEffect(() => { loadSegments(); }, []);

  return (
    <div className="flex h-full">
      {/* Sidebar list */}
      <div className="w-80 flex-shrink-0 border-r border-bdr flex flex-col bg-surface">
        <div className="px-4 py-4 border-b border-bdr flex items-center justify-between">
          <div>
            <h1 className="text-base font-bold text-ink">Audience Segments</h1>
            <p className="text-[11px] text-ink-3 mt-0.5">{total} demographic clusters</p>
          </div>
          <button
            onClick={triggerSegmentation}
            disabled={triggering}
            title="Re-run segmentation"
            className="p-1.5 rounded-lg hover:bg-surface-2 text-ink-3 hover:text-ink transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-4 h-4", triggering && "animate-spin")} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 bg-bg rounded-xl animate-pulse" />
              ))}
            </div>
          ) : segments.length === 0 ? (
            <EmptyState onTrigger={triggerSegmentation} loading={triggering} />
          ) : (
            segments.map((s) => (
              <SegmentRow
                key={s.id}
                seg={s}
                active={selected?.id === s.id}
                onClick={() => selectSegment(s.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <DetailPanel
            detail={selected}
            onPersonaRegenerated={(_id, _summary) => {
              // local state update handled inside DetailPanel
            }}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
            <BarChart2 className="w-10 h-10 text-ink-3 opacity-30" />
            <p className="text-sm text-ink-3">Select a segment to view details</p>
          </div>
        )}
      </div>
    </div>
  );
}
