"use client";

import { Settings, Database, Cpu, Shield, Server } from "lucide-react";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-bdr rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-bdr">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
      </div>
      <div className="p-5 space-y-3">{children}</div>
    </div>
  );
}

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm text-ink">{label}</p>
        {note && <p className="text-xs text-ink-3">{note}</p>}
      </div>
      <p className="text-sm font-medium text-ink-2 text-right">{value}</p>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-ink">Settings</h1>
        <p className="text-sm text-ink-2 mt-0.5">Platform configuration and model information</p>
      </div>

      <Section title="Data Sources">
        <Row label="Mode" value="Demo (Synthetic)" note="Real connectors require API credentials" />
        <Row label="Ingestion interval" value="Every 120 seconds" />
        <Row label="Active platforms" value="Twitter/X, Instagram, Facebook, YouTube, Reddit, Telegram" />
        <Row label="Raw post TTL" value="30 days (DPDP Act 2023)" note="Posts deleted automatically after 30 days" />
      </Section>

      <Section title="NLP Models (Planned — Phase 3)">
        <Row label="Language detection" value="fasttext-langid" note="176 languages, ~0.2ms" />
        <Row label="Sentence embeddings" value="paraphrase-multilingual-MiniLM-L12-v2" note="384-dim, 50+ languages" />
        <Row label="Sentiment" value="twitter-xlm-roberta-base-sentiment" note="Multilingual" />
        <Row label="Emotion" value="emotion-english-distilroberta-base" note="7 classes" />
        <Row label="Topic modeling" value="BERTopic (online/incremental)" />
        <Row label="Clustering" value="HDBSCAN" />
      </Section>

      <Section title="Privacy & Compliance">
        <Row label="Author identifiers" value="SHA-256 pseudonymised" note="Daily rotating salt" />
        <Row label="Policy query storage" value="Hash only — never raw text" />
        <Row label="Compliance" value="DPDP Act 2023" />
        <Row label="Audit log" value="Enabled (all API actions)" />
      </Section>

      <Section title="Infrastructure">
        <Row label="Backend" value="FastAPI + SQLAlchemy (async)" />
        <Row label="Database" value="PostgreSQL 15 + pgvector" />
        <Row label="Task queue" value="Celery + Redis" />
        <Row label="Frontend" value="Next.js 14 App Router" />
        <Row label="Local inference (Phase 9)" value="Ollama + Llama 3.2 3B" note="Runs entirely offline" />
      </Section>
    </div>
  );
}
