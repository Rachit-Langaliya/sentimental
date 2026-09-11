"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { sentimentApi, type SentimentResult, type TimePoint } from "@/lib/api";
import { fmtPct, sentimentColor } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

const EMOTION_COLORS: Record<string, string> = {
  joy: "#10B981",
  anger: "#EF4444",
  fear: "#F59E0B",
  sadness: "#6366F1",
  surprise: "#EC4899",
  disgust: "#84CC16",
  neutral: "#64748B",
};

export default function SentimentPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [timeline, setTimeline] = useState<TimePoint[]>([]);

  useEffect(() => {
    sentimentApi.timeline().then((r) => setTimeline(r.data.points)).catch(() => {});
  }, []);

  async function handleAnalyze() {
    if (!text.trim()) return;
    setAnalyzing(true);
    try {
      const { data } = await sentimentApi.analyze(text);
      setResult(data);
    } catch {
      setResult(null);
    } finally {
      setAnalyzing(false);
    }
  }

  const chartData = timeline.map((p) => ({
    time: format(new Date(p.timestamp), "HH:mm"),
    positive: +(p.positive * 100).toFixed(1),
    neutral: +(p.neutral * 100).toFixed(1),
    negative: +(p.negative * 100).toFixed(1),
  }));

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-ink">Sentiment Analysis</h1>
        <p className="text-sm text-ink-2 mt-0.5">Multilingual sentiment, emotion, and sarcasm detection</p>
      </div>

      {/* Live analysis */}
      <div className="bg-surface border border-bdr rounded-xl p-5 space-y-4">
        <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest">Analyse Text</p>
        <div className="flex gap-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            placeholder="Enter text in any language to analyze sentiment…"
            className="flex-1 bg-bg border border-bdr rounded-lg px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent/60 resize-none transition-colors"
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing || !text.trim()}
            className="px-4 self-end py-2.5 bg-accent hover:bg-accent/90 text-white rounded-lg flex items-center gap-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {analyzing ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Send className="w-4 h-4" />}
            Analyse
          </button>
        </div>

        {result && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-bdr">
            <div className="bg-bg border border-bdr rounded-lg p-3 text-center">
              <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-1">Sentiment</p>
              <p className={cn("text-sm font-bold uppercase", sentimentColor(result.sentiment))}>{result.sentiment}</p>
              <p className="text-[10px] text-ink-3 tabular-nums">{fmtPct(result.sentiment_score)}</p>
            </div>
            <div className="bg-bg border border-bdr rounded-lg p-3 text-center">
              <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-1">Emotion</p>
              <p className="text-sm font-bold text-ink capitalize">{result.emotion}</p>
              <p className="text-[10px] text-ink-3 tabular-nums">{fmtPct(result.emotion_score)}</p>
            </div>
            <div className="bg-bg border border-bdr rounded-lg p-3 text-center">
              <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-1">Language</p>
              <p className="text-sm font-bold text-ink uppercase">{result.language}</p>
            </div>
            <div className="bg-bg border border-bdr rounded-lg p-3 text-center">
              <p className="text-[10px] text-ink-3 uppercase tracking-wide mb-1">Sarcasm</p>
              <div className="flex items-center justify-center gap-1">
                <p className={cn("text-sm font-bold", result.sarcasm_flag ? "text-warning" : "text-ink")}>{result.sarcasm_flag ? "⚠ Likely" : "No"}</p>
              </div>
              <p className="text-[10px] text-ink-3">low confidence</p>
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="bg-surface border border-bdr rounded-xl p-5">
        <h2 className="text-sm font-semibold text-ink mb-4">Sentiment Timeline (24h)</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="sp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="sn" x1="0" y1="0" x2="0" y2="1">
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
              <Area type="monotone" dataKey="positive" stroke="#10B981" fill="url(#sp)" strokeWidth={1.5} dot={false} name="Positive" />
              <Area type="monotone" dataKey="negative" stroke="#EF4444" fill="url(#sn)" strokeWidth={1.5} dot={false} name="Negative" />
              <Area type="monotone" dataKey="neutral" stroke="#64748B" fill="none" strokeWidth={1} dot={false} name="Neutral" strokeDasharray="3 3" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-48 text-ink-3 text-sm gap-2">
            <MessageSquare className="w-5 h-5 opacity-30" />
            Loading timeline data…
          </div>
        )}
      </div>

      {/* Model info */}
      <div className="bg-surface border border-bdr rounded-xl p-4">
        <p className="text-xs font-semibold text-ink-2 uppercase tracking-widest mb-3">Active Models (Phase 1 — Mock)</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {[
            { label: "Sentiment", model: "twitter-xlm-roberta (Phase 3)", note: "50+ languages" },
            { label: "Emotion", model: "distilroberta-emotions (Phase 3)", note: "7 classes" },
            { label: "Sarcasm", model: "roberta-irony (Phase 3)", note: "⚠ Low confidence" },
          ].map(({ label, model, note }) => (
            <div key={label} className="bg-bg border border-bdr rounded-lg p-3">
              <p className="text-ink-3 uppercase tracking-wide text-[10px] mb-1">{label}</p>
              <p className="text-ink font-medium">{model}</p>
              <p className="text-ink-3 mt-0.5">{note}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
