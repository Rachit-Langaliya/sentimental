"use client";

import { useState } from "react";
import { FlaskConical, Loader2, AlertTriangle, ChevronDown, ChevronUp, Shield } from "lucide-react";
import { simulationApi, type SimulationResult, type SegmentSimulationResponse } from "@/lib/api";
import { fmtPct, sentimentColor, confidenceColor, confidenceBadge } from "@/lib/utils";
import { cn } from "@/lib/utils";

const EXAMPLES = [
  "Proposed increase in fuel tax by 8%",
  "Mandatory digital KYC for all bank accounts",
  "New national education policy changes for Class 10 board exams",
  "Expansion of PM-KISAN direct benefit transfer",
];

function SentimentBar({ positive, neutral, negative, size = "sm" }: {
  positive: number; neutral: number; negative: number; size?: "sm" | "md";
}) {
  const h = size === "md" ? "h-2.5" : "h-1.5";
  return (
    <div className={`flex ${h} rounded-full overflow-hidden gap-0.5`}>
      <div className="bg-success rounded-l-full" style={{ width: fmtPct(positive) }} />
      <div className="bg-ink-3" style={{ width: fmtPct(neutral) }} />
      <div className="bg-danger rounded-r-full" style={{ width: fmtPct(negative) }} />
    </div>
  );
}

function SegmentCard({ resp }: { resp: SegmentSimulationResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-bg border border-bdr rounded-xl overflow-hidden">
      <button className="w-full flex items-center gap-4 p-4 hover:bg-surface-2 transition-colors" onClick={() => setOpen(!open)}>
        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-ink">{resp.segment_name}</p>
          <div className="mt-1.5">
            <SentimentBar {...resp.sentiment_distribution} />
          </div>
        </div>
        <div className="text-right flex-shrink-0 space-y-1">
          <div className={cn("text-xs font-bold uppercase", sentimentColor(resp.expected_sentiment))}>{resp.expected_sentiment}</div>
          <div className={cn("text-xs", confidenceColor(resp.confidence))}>{confidenceBadge(resp.confidence)} conf.</div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-ink-3 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-ink-3 flex-shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-bdr pt-3">
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Positive", v: resp.sentiment_distribution.positive, c: "text-success" },
              { label: "Neutral", v: resp.sentiment_distribution.neutral, c: "text-ink-2" },
              { label: "Negative", v: resp.sentiment_distribution.negative, c: "text-danger" },
            ].map(({ label, v, c }) => (
              <div key={label} className="bg-surface rounded-lg p-2.5 text-center">
                <p className={cn("text-sm font-bold tabular-nums", c)}>{fmtPct(v)}</p>
                <p className="text-[10px] text-ink-3">{label}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-surface rounded-lg p-2.5">
              <p className="text-ink-3 mb-0.5">Reaction Intensity</p>
              <p className="text-sm font-bold text-ink tabular-nums">{fmtPct(resp.intensity)}</p>
            </div>
            <div className="bg-surface rounded-lg p-2.5">
              <p className="text-ink-3 mb-0.5">Support Ratio</p>
              <p className="text-sm font-bold text-ink tabular-nums">{fmtPct(resp.support_ratio)}</p>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-ink-3 uppercase tracking-widest mb-2">Likely Narratives</p>
            <div className="flex flex-wrap gap-1.5">
              {resp.likely_narratives.map((n) => (
                <span key={n} className="text-xs px-2 py-0.5 bg-surface border border-bdr rounded-full text-ink-2">{n}</span>
              ))}
            </div>
          </div>
          <p className="text-[10px] text-ink-3">Evidence: {resp.evidence_count.toLocaleString()} posts</p>
        </div>
      )}
    </div>
  );
}

export default function SimulationPage() {
  const [policyText, setPolicyText] = useState("");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleRun() {
    if (!policyText.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await simulationApi.run(policyText);
      setResult(data);
    } catch {
      setError("Simulation failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-ink">Policy Simulation</h1>
        <p className="text-sm text-ink-2 mt-0.5">Scenario synthesis based on historical public response patterns</p>
      </div>

      {/* Privacy notice */}
      <div className="flex items-start gap-3 bg-surface border border-bdr rounded-xl p-4">
        <Shield className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
        <div className="text-xs text-ink-2 space-y-1">
          <p className="font-semibold text-ink">Privacy-preserving analysis</p>
          <p>Policy queries are hashed before audit logging — raw text is never stored on the server. For maximum privacy, use <span className="text-accent font-semibold">Local Mode</span> (available in Phase 9) to run analysis entirely offline.</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-surface border border-bdr rounded-xl p-5 space-y-4">
        <div>
          <label className="block text-xs font-semibold text-ink-2 uppercase tracking-widest mb-2">
            Policy or Event Description
          </label>
          <textarea
            value={policyText}
            onChange={(e) => setPolicyText(e.target.value)}
            rows={3}
            placeholder="Describe the policy, announcement, or event to simulate public response for…"
            className="w-full bg-bg border border-bdr rounded-lg px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent/60 transition-colors resize-none"
          />
        </div>

        <div>
          <p className="text-xs text-ink-3 mb-2">Example queries:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => setPolicyText(ex)}
                className="text-xs px-3 py-1.5 bg-surface-2 border border-bdr rounded-full text-ink-2 hover:text-ink hover:border-accent/40 transition-colors">
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading || !policyText.trim()}
          className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/90 text-white font-semibold text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
          {loading ? "Analysing…" : "Run Simulation"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 border border-danger/30 rounded-xl p-4">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-5">
          {/* Disclaimer */}
          <div className="flex items-start gap-3 bg-accent/8 border border-accent/25 rounded-xl p-4">
            <AlertTriangle className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
            <p className="text-xs text-ink-2 leading-relaxed">{result.disclaimer}</p>
          </div>

          {/* Overall */}
          <div className="bg-surface border border-bdr rounded-xl p-5">
            <h2 className="text-sm font-semibold text-ink mb-4">Overall Predicted Response</h2>
            <SentimentBar {...result.overall_sentiment} size="md" />
            <div className="flex gap-5 mt-2 text-xs">
              {["positive", "neutral", "negative"].map((k) => (
                <span key={k} className="text-ink-2">
                  <span className="font-bold text-ink">{fmtPct((result.overall_sentiment as any)[k])}</span> {k}
                </span>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
              <div className="bg-bg border border-bdr rounded-lg p-3">
                <p className="text-ink-3 mb-1">Overall Confidence</p>
                <p className={cn("text-base font-bold tabular-nums", confidenceColor(result.overall_confidence))}>{fmtPct(result.overall_confidence)}</p>
              </div>
              <div className="bg-bg border border-bdr rounded-lg p-3">
                <p className="text-ink-3 mb-1">Expected Spread</p>
                <p className="text-base font-bold text-ink capitalize">{result.potential_spread}</p>
              </div>
              <div className="bg-bg border border-bdr rounded-lg p-3">
                <p className="text-ink-3 mb-1">Historical Analogues</p>
                <p className="text-base font-bold text-ink">{result.analogues_used.length}</p>
              </div>
            </div>
          </div>

          {/* Segment responses */}
          <div>
            <h2 className="text-sm font-semibold text-ink mb-3">Segment-Level Predicted Responses</h2>
            <div className="space-y-2">
              {result.segment_responses.map((r) => (
                <SegmentCard key={r.segment_id} resp={r} />
              ))}
            </div>
          </div>

          {/* Influential communities */}
          <div className="bg-surface border border-bdr rounded-xl p-5">
            <h2 className="text-sm font-semibold text-ink mb-3">Influential Communities Expected to Amplify</h2>
            <div className="flex flex-wrap gap-2">
              {result.influential_communities.map((c) => (
                <span key={c} className="px-3 py-1.5 text-xs font-medium bg-surface-2 border border-bdr rounded-full text-ink-2 capitalize">{c}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
