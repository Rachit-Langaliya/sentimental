"use client";

import { useEffect, useState } from "react";
import { Settings, Database, Cpu, Shield, Server, RefreshCw, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { ingestApi, ollamaApi, type ModelStatus, type OllamaStatus, type IngestionStats } from "@/lib/api";
import { cn } from "@/lib/utils";

function Section({ title, icon: Icon, children }: {
  title: string; icon: React.ElementType; children: React.ReactNode;
}) {
  return (
    <div className="bg-surface border border-bdr rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-bdr flex items-center gap-2.5">
        <Icon className="w-4 h-4 text-ink-3" />
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
      </div>
      <div className="divide-y divide-bdr">{children}</div>
    </div>
  );
}

function Row({ label, value, note, mono = false }: {
  label: string; value: React.ReactNode; note?: string; mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-3">
      <div>
        <p className="text-sm text-ink">{label}</p>
        {note && <p className="text-xs text-ink-3 mt-0.5">{note}</p>}
      </div>
      <div className={cn("text-sm font-medium text-ink-2 text-right", mono && "font-mono text-xs")}>{value}</div>
    </div>
  );
}

function StatusDot({ ok, loading }: { ok: boolean; loading?: boolean }) {
  if (loading) return <Loader2 className="w-3.5 h-3.5 text-ink-3 animate-spin" />;
  return ok
    ? <CheckCircle2 className="w-3.5 h-3.5 text-success" />
    : <XCircle className="w-3.5 h-3.5 text-danger" />;
}

function ModelRow({ model, loading }: { model: ModelStatus; loading: boolean }) {
  const labels: Record<string, string> = {
    "sentiment": "Sentiment (XLM-RoBERTa)",
    "emotion": "Emotion (DistilRoBERTa)",
    "irony": "Sarcasm (RoBERTa-irony)",
    "embedding": "Embeddings (MiniLM-L12)",
  };
  return (
    <div className="flex items-center justify-between px-5 py-3 gap-4">
      <div>
        <p className="text-sm text-ink">{labels[model.name] ?? model.name}</p>
        {model.error && <p className="text-xs text-danger mt-0.5">{model.error}</p>}
        {!model.use_real_nlp && (
          <p className="text-xs text-ink-3 mt-0.5">Rule-based fallback active (USE_REAL_NLP=false)</p>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-ink-3">
        <span>{model.loaded ? "loaded" : "idle"}</span>
        <StatusDot ok={model.loaded || !model.use_real_nlp} loading={loading} />
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [stats, setStats] = useState<IngestionStats | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchAll() {
    setLoading(true);
    const results = await Promise.allSettled([
      ingestApi.modelStatus(),
      ollamaApi.status(),
      ingestApi.stats(),
    ]);
    if (results[0].status === "fulfilled") setModels(results[0].value.data);
    if (results[1].status === "fulfilled") setOllama(results[1].value.data);
    if (results[2].status === "fulfilled") setStats(results[2].value.data);
    setLoading(false);
  }

  useEffect(() => { fetchAll(); }, []);

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Settings</h1>
          <p className="text-sm text-ink-2 mt-0.5">Platform configuration and live system status</p>
        </div>
        <button
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-bdr rounded-lg text-xs text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Data sources */}
      <Section title="Data Sources" icon={Database}>
        <Row label="Ingestion Mode" value="Demo (Synthetic)" note="Set USE_REAL_NLP=true for transformer models" />
        <Row label="Ingestion interval" value="Every 120 seconds" note="Celery beat scheduler" />
        <Row label="Active platforms" value="Twitter/X · Instagram · Facebook · YouTube · Reddit · News" />
        <Row label="Total posts indexed"
          value={stats ? stats.total_posts.toLocaleString("en-IN") : "—"}
          note={stats ? `${Math.round(stats.nlp_coverage * 100)}% NLP-processed` : undefined}
        />
        <Row label="Raw post TTL" value="30 days" note="Auto-deleted by Celery task (DPDP Act 2023)" />
      </Section>

      {/* NLP models */}
      <Section title="NLP Models" icon={Server}>
        {loading && models.length === 0 ? (
          <div className="px-5 py-4 flex items-center gap-2 text-sm text-ink-3">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading model status…
          </div>
        ) : models.length > 0 ? (
          models.map((m) => <ModelRow key={m.name} model={m} loading={loading} />)
        ) : (
          <>
            <Row label="Language detection" value="fasttext-langid" note="176 languages, ~0.2ms/call" />
            <Row label="Sentence embeddings" value="paraphrase-multilingual-MiniLM-L12-v2" note="384-dim, 50+ languages" />
            <Row label="Sentiment" value="twitter-xlm-roberta-base-sentiment" note="Multilingual, fine-tuned" />
            <Row label="Emotion" value="emotion-english-distilroberta-base" note="7 emotion classes" />
            <Row label="Sarcasm" value="twitter-roberta-base-irony" note="Binary irony detection" />
            <Row label="Topic modelling" value="BERTopic + HDBSCAN + UMAP" note="Online incremental fitting" />
          </>
        )}
      </Section>

      {/* Local LLM */}
      <Section title="Local LLM (Ollama)" icon={Cpu}>
        <div className="flex items-center justify-between px-5 py-3 gap-4">
          <div>
            <p className="text-sm text-ink">Ollama service</p>
            <p className="text-xs text-ink-3 mt-0.5">{ollama?.base_url ?? "http://localhost:11434"}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn("text-xs font-medium", ollama?.available ? "text-success" : "text-ink-3")}>
              {ollama === null ? "checking…" : ollama.available ? "running" : "offline"}
            </span>
            <StatusDot ok={ollama?.available ?? false} loading={ollama === null && loading} />
          </div>
        </div>
        <Row
          label="Configured model"
          value={
            <span className="flex items-center gap-2">
              <span className="font-mono text-xs">{ollama?.configured_model ?? "llama3.2:3b"}</span>
              {ollama && (
                <StatusDot ok={ollama.model_ready} />
              )}
            </span>
          }
          note={ollama?.model_ready ? "Model cached and ready" : "Run: make ollama → ollama pull llama3.2:3b"}
        />
        {ollama?.available_models && ollama.available_models.length > 0 && (
          <Row
            label="Available models"
            value={ollama.available_models.join(", ")}
            mono
          />
        )}
        <Row
          label="Capabilities"
          value="Persona generation · Narrative enrichment · Policy brief"
          note="All inference runs on-device — no external API calls"
        />
      </Section>

      {/* Privacy */}
      <Section title="Privacy & Compliance" icon={Shield}>
        <Row
          label="Author identifiers"
          value={<span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-success" />SHA-256 pseudonymised</span>}
          note="Daily rotating salt — original IDs irrecoverable"
        />
        <Row
          label="Policy query storage"
          value={<span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-success" />Hash only</span>}
          note="Raw policy text never persisted to database"
        />
        <Row
          label="Data retention"
          value={<span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-success" />30-day TTL enforced</span>}
          note="Celery beat deletes raw_posts where expires_at ≤ now"
        />
        <Row
          label="Compliance framework"
          value="DPDP Act 2023"
          note="Digital Personal Data Protection Act"
        />
        <Row
          label="Audit logging"
          value={<span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-success" />Enabled</span>}
          note="All API actions logged with hash identifiers only"
        />
      </Section>

      {/* Infrastructure */}
      <Section title="Infrastructure" icon={Server}>
        <Row label="Backend" value="FastAPI 0.115 + SQLAlchemy 2.0 (async)" />
        <Row label="Database" value="PostgreSQL 15 + pgvector" note="Vector similarity for embeddings" />
        <Row label="Task queue" value="Celery 5 + Redis 7" note="6 scheduled tasks via beat" />
        <Row label="Frontend" value="Next.js 14 App Router + TypeScript" />
        <Row label="NLP stack" value="sentence-transformers · BERTopic · HDBSCAN · UMAP" />
        <Row label="Local LLM" value="Ollama · llama3.2:3b" note="Runs fully offline" />
        <Row label="Platform version" value="1.0.0 (SIH 2026)" />
      </Section>
    </div>
  );
}
