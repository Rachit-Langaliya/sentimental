"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { TrendingUp, Users, MessageSquare, Zap, AlertTriangle, Radio, WifiOff, RefreshCw, Clock, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { dashboardApi, trendsApi, ingestApi, type DashboardSummary, type TrendSummary, type ConnectorStatus } from "@/lib/api";
import { fmtNumber, fmtPct } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { format, formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

function KpiCard({ label, value, sub, icon: Icon, accent = false }: {
  label: string; value: string; sub?: string; icon: React.ElementType; accent?: boolean;
}) {
  return (
    <div className="bg-surface border border-bdr rounded-xl p-5 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${accent ? "bg-accent/15 border border-accent/25" : "bg-surface-2 border border-bdr"}`}>
        <Icon className={`w-5 h-5 ${accent ? "text-accent" : "text-ink-2"}`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-ink tabular-nums">{value}</p>
        <p className="text-xs font-semibold text-ink-2 uppercase tracking-wider mt-0.5">{label}</p>
        {sub && <p className="text-xs text-ink-3 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function SentimentBar({ positive, neutral, negative }: { positive: number; neutral: number; negative: number }) {
  return (
    <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
      <div className="bg-success rounded-l-full" style={{ width: fmtPct(positive) }} title={`Positive ${fmtPct(positive)}`} />
      <div className="bg-ink-3" style={{ width: fmtPct(neutral) }} title={`Neutral ${fmtPct(neutral)}`} />
      <div className="bg-danger rounded-r-full" style={{ width: fmtPct(negative) }} title={`Negative ${fmtPct(negative)}`} />
    </div>
  );
}

function ConnectorStatusPanel() {
  const [statuses, setStatuses] = useState<ConnectorStatus[]>([]);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    ingestApi.status().then((r) => setStatuses(r.data)).catch(() => {});
  }, []);

  async function handleTrigger() {
    setTriggering(true);
    try {
      await ingestApi.trigger();
      toast.success("Ingestion cycle queued");
    } catch {
      toast.error("Failed to trigger ingestion");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div className="bg-surface border border-bdr rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-ink">Connector Status</h2>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-accent/15 border border-accent/30 text-accent rounded-lg hover:bg-accent/25 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", triggering && "animate-spin")} />
          {triggering ? "Queuing…" : "Trigger Ingest"}
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2">
        {statuses.length > 0 ? statuses.map((s) => (
          <div key={s.platform} className="bg-bg border border-bdr rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              {s.is_healthy
                ? <Radio className="w-3 h-3 text-success" />
                : <WifiOff className="w-3 h-3 text-danger" />}
              <span className="text-xs font-semibold text-ink capitalize">{s.platform}</span>
            </div>
            <p className="text-[10px] text-ink-3 uppercase tracking-wide">{s.mode}</p>
            <p className="text-xs font-bold text-ink-2 tabular-nums mt-0.5">
              {fmtNumber(s.posts_ingested_total)} new
            </p>
          </div>
        )) : (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-bg border border-bdr rounded-lg p-3 animate-pulse h-16" />
          ))
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<TrendSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [s, t] = await Promise.all([dashboardApi.summary(), trendsApi.list(7)]);
      setSummary(s.data);
      setTrends(t.data.items);
      setLastUpdated(new Date());
    } catch {
      // noop
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(() => load(true), 60_000);
    return () => clearInterval(interval);
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const timelineData = summary?.sentiment_timeline.map((p) => ({
    time: format(new Date(p.timestamp), "HH:mm"),
    positive: +(p.positive * 100).toFixed(1),
    neutral: +(p.neutral * 100).toFixed(1),
    negative: +(p.negative * 100).toFixed(1),
  })) ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Demo banner */}
      {summary?.demo_mode && (
        <div className="flex items-center gap-3 bg-accent/10 border border-accent/30 rounded-xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-accent flex-shrink-0" />
          <p className="text-sm text-accent font-medium">
            Demo Mode — displaying synthetic data for demonstration purposes.
            <span className="text-ink-2 font-normal"> Real platform connectors available in production deployment.</span>
          </p>
        </div>
      )}

      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Intelligence Overview</h1>
          <p className="text-sm text-ink-2 mt-0.5">Real-time public discourse monitoring across {summary?.platform_breakdown.length ?? 0} platforms</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <div className="flex items-center gap-1.5 text-xs text-ink-3">
              <Clock className="w-3 h-3" />
              <span>Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}</span>
            </div>
          )}
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            title="Refresh data"
            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-bdr rounded-lg text-xs text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Quick Insights row — top emerging trend + overall sentiment direction */}
      {trends.length > 0 && (() => {
        const emerging = trends.filter(t => t.is_emerging);
        const top = emerging[0] ?? trends[0];
        const sentPositive = (summary?.overall_sentiment.positive ?? 0) > 0.35;
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex items-center gap-3 bg-accent/8 border border-accent/25 rounded-xl px-4 py-3">
              <TrendingUp className="w-4 h-4 text-accent flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-ink-3 font-medium uppercase tracking-wider">Top Emerging Topic</p>
                <p className="text-sm font-semibold text-ink truncate mt-0.5">{top.name}</p>
                <p className="text-[10px] text-ink-3 mt-0.5">
                  {fmtNumber(top.unique_users)} users · {top.platform_count} platforms · score {top.trend_score.toFixed(2)}
                </p>
              </div>
            </div>
            <div className={cn(
              "flex items-center gap-3 rounded-xl px-4 py-3 border",
              sentPositive
                ? "bg-success/8 border-success/25"
                : "bg-danger/8 border-danger/25"
            )}>
              {sentPositive
                ? <ArrowUpRight className="w-4 h-4 text-success flex-shrink-0" />
                : <ArrowDownRight className="w-4 h-4 text-danger flex-shrink-0" />}
              <div>
                <p className="text-xs text-ink-3 font-medium uppercase tracking-wider">Overall Discourse Tone</p>
                <p className={cn("text-sm font-semibold mt-0.5", sentPositive ? "text-success" : "text-danger")}>
                  {sentPositive ? "Predominantly Positive" : "Predominantly Negative"}
                </p>
                <p className="text-[10px] text-ink-3 mt-0.5">
                  {fmtPct(summary?.overall_sentiment.positive ?? 0)} positive · {fmtPct(summary?.overall_sentiment.negative ?? 0)} negative
                </p>
              </div>
            </div>
          </div>
        );
      })()}

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Total Posts" value={fmtNumber(summary?.total_posts ?? 0)} sub={`+${fmtNumber(summary?.posts_24h ?? 0)} last 24h`} icon={MessageSquare} />
        <KpiCard label="Active Segments" value={String(summary?.active_segments ?? 0)} sub="Demographic clusters" icon={Users} />
        <KpiCard label="Trending Topics" value={String(summary?.trending_topics ?? 0)} sub={`${summary?.emerging_count ?? 0} emerging`} icon={TrendingUp} accent />
        <KpiCard label="Overall Sentiment"
          value={summary ? `${fmtPct(summary.overall_sentiment.positive)} +` : "—"}
          sub={`${fmtPct(summary?.overall_sentiment.negative ?? 0)} negative`}
          icon={Zap} />
      </div>

      {/* Sentiment breakdown */}
      {summary && (
        <div className="bg-surface border border-bdr rounded-xl p-5">
          <h2 className="text-sm font-semibold text-ink mb-3">Overall Sentiment Distribution</h2>
          <SentimentBar {...summary.overall_sentiment} />
          <div className="flex gap-5 mt-3">
            {[
              { label: "Positive", value: summary.overall_sentiment.positive, color: "bg-success" },
              { label: "Neutral", value: summary.overall_sentiment.neutral, color: "bg-ink-3" },
              { label: "Negative", value: summary.overall_sentiment.negative, color: "bg-danger" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${color}`} />
                <span className="text-xs text-ink-2">{label}</span>
                <span className="text-xs font-semibold text-ink tabular-nums">{fmtPct(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Sentiment timeline */}
        <div className="xl:col-span-2 bg-surface border border-bdr rounded-xl p-5">
          <h2 className="text-sm font-semibold text-ink mb-4">Sentiment Timeline (24h)</h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={timelineData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="pos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="neg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fill: "#64748B", fontSize: 10 }} tickLine={false} axisLine={false} interval={5} />
              <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip
                contentStyle={{ background: "#1C2D44", border: "1px solid #263450", borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: "#94A3B8" }}
              />
              <Area type="monotone" dataKey="positive" stroke="#10B981" fill="url(#pos)" strokeWidth={1.5} dot={false} name="Positive" />
              <Area type="monotone" dataKey="negative" stroke="#EF4444" fill="url(#neg)" strokeWidth={1.5} dot={false} name="Negative" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Platform breakdown */}
        <div className="bg-surface border border-bdr rounded-xl p-5">
          <h2 className="text-sm font-semibold text-ink mb-4">Platform Activity</h2>
          <div className="space-y-2.5">
            {(summary?.platform_breakdown ?? []).sort((a, b) => b.post_count - a.post_count).map((p) => (
              <div key={p.platform}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-ink-2">{p.display_name}</span>
                  <span className="text-xs font-semibold text-ink tabular-nums">{fmtNumber(p.post_count)}</span>
                </div>
                <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${summary && summary.total_posts > 0 ? Math.min(100, (p.post_count / summary.total_posts) * 100) : 0}%`,
                      background: p.color ?? "#D97706",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top trends */}
      <div className="bg-surface border border-bdr rounded-xl p-5">
        <h2 className="text-sm font-semibold text-ink mb-4">Top Trending Topics</h2>
        <div className="space-y-2">
          {trends.map((t, i) => (
            <div key={t.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-surface-2 transition-colors">
              <span className="text-xs font-mono text-ink-3 w-5 flex-shrink-0">{String(i + 1).padStart(2, "0")}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink truncate">{t.name}</p>
                <p className="text-xs text-ink-3">{fmtNumber(t.unique_users)} users · {t.platform_count} platforms</p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                {t.is_emerging && (
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/20 text-accent">↑ Emerging</span>
                )}
                <div className="text-right">
                  <p className="text-sm font-bold text-ink tabular-nums">{t.trend_score.toFixed(2)}</p>
                  <p className="text-[10px] text-ink-3">score</p>
                </div>
              </div>
            </div>
          ))}
          {trends.length === 0 && (
            <p className="text-sm text-ink-3 py-4 text-center">No trend data yet. Start ingestion to populate.</p>
          )}
        </div>
      </div>

      {/* Connector status */}
      <ConnectorStatusPanel />
    </div>
  );
}
