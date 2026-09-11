"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Zap, BarChart2 } from "lucide-react";
import { trendsApi, type TrendSummary, type TrendDetail } from "@/lib/api";
import { fmtNumber, fmtPct, sentimentColor } from "@/lib/utils";
import { cn } from "@/lib/utils";

function VelocityBadge({ v }: { v: number }) {
  const up = v > 0;
  return (
    <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded", up ? "bg-success/15 text-success" : "bg-danger/15 text-danger")}>
      {up ? "↑" : "↓"} {Math.abs(v).toFixed(2)}/h
    </span>
  );
}

function TrendRow({ trend, active, onClick }: { trend: TrendSummary; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left px-4 py-3.5 border-b border-bdr transition-colors flex items-center gap-4",
        active ? "bg-accent/8 border-l-2 border-l-accent" : "hover:bg-surface-2"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-sm font-semibold text-ink truncate">{trend.name}</p>
          {trend.is_emerging && (
            <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-accent/20 text-accent rounded flex-shrink-0">Emerging</span>
          )}
        </div>
        <div className="flex flex-wrap gap-1">
          {(trend.platforms ?? []).slice(0, 3).map((p: string) => (
            <span key={p} className="text-[10px] text-ink-3">{p}</span>
          ))}
        </div>
      </div>
      <div className="text-right flex-shrink-0 space-y-1">
        <p className="text-sm font-bold text-ink tabular-nums">{trend.trend_score.toFixed(2)}</p>
        <VelocityBadge v={trend.velocity} />
      </div>
    </button>
  );
}

function TrendDetailPanel({ detail }: { detail: TrendDetail }) {
  const metrics = [
    { label: "Trend Score", value: detail.trend_score.toFixed(3) },
    { label: "Velocity", value: `${detail.velocity > 0 ? "+" : ""}${detail.velocity.toFixed(2)}/h` },
    { label: "Acceleration", value: `${detail.acceleration > 0 ? "+" : ""}${detail.acceleration.toFixed(3)}` },
    { label: "Volume (decay)", value: detail.volume_decay.toFixed(0) },
    { label: "Unique Users", value: fmtNumber(detail.unique_users) },
    { label: "Platforms", value: String(detail.platform_count) },
    { label: "Engagement", value: fmtPct(detail.engagement) },
    { label: "Community Spread", value: fmtPct(detail.community_spread) },
  ];

  return (
    <div className="p-5 space-y-5">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-base font-bold text-ink">{detail.name}</h2>
          {detail.is_emerging && (
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 bg-accent/20 text-accent rounded">Emerging</span>
          )}
        </div>
        <p className="text-xs text-ink-3">First seen: {new Date(detail.measured_at).toLocaleDateString("en-IN")}</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {metrics.map(({ label, value }) => (
          <div key={label} className="bg-bg border border-bdr rounded-lg p-3">
            <p className="text-[10px] text-ink-3 mb-0.5 uppercase tracking-wide">{label}</p>
            <p className="text-sm font-bold text-ink tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {detail.sentiment_shift !== undefined && detail.baseline_7d !== undefined && (
        <div className="bg-bg border border-bdr rounded-xl p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">Sentiment Context</p>
          <div className="flex items-center gap-4 text-xs">
            <div>
              <p className="text-ink-3 mb-0.5">Sentiment Shift</p>
              <p className={cn("font-bold tabular-nums", detail.sentiment_shift > 0 ? "text-success" : detail.sentiment_shift < 0 ? "text-danger" : "text-ink")}>
                {detail.sentiment_shift > 0 ? "+" : ""}{(detail.sentiment_shift * 100).toFixed(1)}pp
              </p>
            </div>
            <div>
              <p className="text-ink-3 mb-0.5">7-Day Baseline</p>
              <p className="font-bold text-ink tabular-nums">{detail.baseline_7d.toFixed(0)} posts/day</p>
            </div>
          </div>
        </div>
      )}

      {detail.platforms && detail.platforms.length > 0 && (
        <div className="bg-bg border border-bdr rounded-xl p-4">
          <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-2">Active Platforms</p>
          <div className="flex flex-wrap gap-2">
            {detail.platforms.map((p: string) => (
              <span key={p} className="text-xs px-2.5 py-1 bg-surface border border-bdr rounded-full text-ink-2">{p}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TrendsPage() {
  const [trends, setTrends] = useState<TrendSummary[]>([]);
  const [emerging, setEmerging] = useState<TrendSummary[]>([]);
  const [selected, setSelected] = useState<TrendDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [tab, setTab] = useState<"all" | "emerging">("all");

  useEffect(() => {
    Promise.all([trendsApi.list(20), trendsApi.emerging()]).then(([a, e]) => {
      setTrends(a.data.items);
      setEmerging(e.data.items);
      setLoading(false);
      if (a.data.items.length > 0) loadDetail(a.data.items[0].id);
    }).catch(() => setLoading(false));
  }, []);

  function loadDetail(id: number) {
    setDetailLoading(true);
    trendsApi.get(id).then((r) => {
      setSelected(r.data);
      setDetailLoading(false);
    }).catch(() => setDetailLoading(false));
  }

  const displayed = tab === "emerging" ? emerging : trends;

  return (
    <div className="p-6 flex flex-col h-full">
      <div className="mb-5">
        <h1 className="text-xl font-bold text-ink">Trend Intelligence</h1>
        <p className="text-sm text-ink-2 mt-0.5">Real-time topic velocity, acceleration, and community spread</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex gap-5 flex-1 min-h-0">
          {/* Left: trend list */}
          <div className="w-80 flex-shrink-0 bg-surface border border-bdr rounded-xl overflow-hidden flex flex-col">
            {/* Tabs */}
            <div className="flex border-b border-bdr">
              {(["all", "emerging"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className={cn("flex-1 px-4 py-3 text-xs font-semibold capitalize transition-colors",
                    tab === t ? "text-accent border-b-2 border-accent" : "text-ink-3 hover:text-ink"
                  )}>
                  {t === "all" ? `All (${trends.length})` : `Emerging (${emerging.length})`}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto">
              {displayed.map((t) => (
                <TrendRow key={t.id} trend={t} active={selected?.id === t.id} onClick={() => loadDetail(t.id)} />
              ))}
              {displayed.length === 0 && (
                <div className="text-center py-12 text-ink-3 text-sm">
                  <TrendingUp className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  No trends yet
                </div>
              )}
            </div>
          </div>

          {/* Right: detail */}
          <div className="flex-1 bg-surface border border-bdr rounded-xl overflow-y-auto">
            {detailLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            ) : selected ? (
              <TrendDetailPanel detail={selected} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-ink-3 gap-2">
                <BarChart2 className="w-8 h-8 opacity-30" />
                <p className="text-sm">Select a trend to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
