import axios from "axios";
import Cookies from "js-cookie";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Typed API calls ───────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user: User }>("/auth/login", { email, password }),
  me: () => api.get<User>("/auth/me"),
  logout: () => api.post("/auth/logout"),
};

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
};

export const segmentsApi = {
  list: () => api.get<{ items: SegmentSummary[]; total: number }>("/segments/"),
  get: (id: number) => api.get<SegmentDetail>(`/segments/${id}`),
  timeline: (id: number) => api.get(`/segments/${id}/timeline`),
};

export const trendsApi = {
  list: (limit = 20) => api.get<{ items: TrendSummary[]; total: number }>(`/trends/?limit=${limit}`),
  emerging: () => api.get<{ items: TrendSummary[]; total: number }>("/trends/emerging"),
  get: (id: number) => api.get<TrendDetail>(`/trends/${id}`),
};

export const sentimentApi = {
  analyze: (text: string, language?: string) =>
    api.post<SentimentResult>("/sentiment/analyze", { text, language }),
  timeline: (platform?: string, hours = 24) =>
    api.get<{ points: TimePoint[] }>(`/sentiment/timeline?hours=${hours}${platform ? `&platform=${platform}` : ""}`),
};

export const simulationApi = {
  run: (policy_text: string, target_population?: string, question?: string, use_local_llm = false) =>
    api.post<SimulationResult>("/simulation/run", { policy_text, target_population, question, use_local_llm }),
};

export const ollamaApi = {
  status: () => api.get<OllamaStatus>("/ollama/status"),
  warm: () => api.post<{ status: string; model: string }>("/ollama/warm"),
  test: (prompt?: string) => api.post<OllamaTestResult>("/ollama/test", { prompt }),
};

export const personaApi = {
  regenerate: (segmentId: number) => api.post<PersonaRegenerateResult>(`/segments/${segmentId}/regenerate-persona`),
};

export const ingestApi = {
  status: () => api.get<ConnectorStatus[]>("/ingest/status"),
  stats: () => api.get<IngestionStats>("/ingest/stats"),
  trigger: () => api.post<{ status: string; task_id: string }>("/ingest/trigger"),
  modelStatus: () => api.get<ModelStatus[]>("/ingest/model-status"),
};

// ── Types (mirroring backend schemas) ────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface SentimentBreakdown {
  positive: number;
  neutral: number;
  negative: number;
}

export interface TimePoint {
  timestamp: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface PlatformStat {
  platform: string;
  display_name: string;
  post_count: number;
  color?: string;
}

export interface DashboardSummary {
  total_posts: number;
  posts_24h: number;
  active_segments: number;
  trending_topics: number;
  emerging_count: number;
  overall_sentiment: SentimentBreakdown;
  platform_breakdown: PlatformStat[];
  sentiment_timeline: TimePoint[];
  demo_mode: boolean;
}

export interface SegmentSummary {
  id: number;
  name: string;
  description?: string;
  dominant_language?: string;
  size_estimate?: number;
  confidence: number;
  evidence_count: number;
  sentiment_profile?: SentimentBreakdown;
  updated_at: string;
}

export interface Persona {
  id: number;
  summary?: string;
  interests?: string[];
  reaction?: Record<string, number>;
  influence_score?: number;
  confidence: number;
  generated_at: string;
}

export interface SegmentDetail extends SegmentSummary {
  geo_distribution?: Record<string, number>;
  topic_prefs?: Record<string, number>;
  activity_profile?: Record<string, number>;
  persona?: Persona;
}

export interface TrendSummary {
  id: number;
  name: string;
  trend_score: number;
  velocity: number;
  acceleration: number;
  is_emerging: boolean;
  platform_count: number;
  platforms?: string[];
  unique_users: number;
  measured_at: string;
}

export interface TrendDetail extends TrendSummary {
  volume_decay: number;
  engagement: number;
  community_spread: number;
  sentiment_shift: number;
  baseline_7d: number;
}

export interface SentimentResult {
  text: string;
  language: string;
  sentiment: string;
  sentiment_score: number;
  emotion?: string;
  emotion_score?: number;
  intensity?: number;
  sarcasm_flag?: boolean;
  sarcasm_conf?: number;
  epistemic_note: string;
}

export interface SegmentSimulationResponse {
  segment_id: number;
  segment_name: string;
  expected_sentiment: string;
  sentiment_distribution: SentimentBreakdown;
  intensity: number;
  support_ratio: number;
  likely_narratives: string[];
  confidence: number;
  evidence_count: number;
}

export interface ConnectorStatus {
  platform: string;
  mode: "mock" | "live";
  is_healthy: boolean;
  posts_ingested_total: number;
  last_ingested_at?: string;
  error?: string;
}

export interface PlatformIngestionStat {
  platform: string;
  display_name: string;
  total_posts: number;
  nlp_processed: number;
  nlp_coverage: number;
  color?: string;
}

export interface IngestionStats {
  total_posts: number;
  nlp_processed: number;
  nlp_coverage: number;
  per_platform: PlatformIngestionStat[];
  generated_at: string;
}

export interface NetworkNode {
  id: string;
  label: string;
  platform: string;
  post_count: number;
  topic_count: number;
  dominant_sentiment: string;
  community_id: number;
  pagerank: number;
  betweenness: number;
  is_bridge: boolean;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkCommunity {
  id: number;
  name: string;
  size: number;
  dominant_platform: string;
  avg_pagerank: number;
  platform_breakdown: Record<string, number>;
}

export interface NetworkInfluencer {
  rank: number;
  label: string;
  platform: string;
  pagerank: number;
  post_count: number;
  community_id: number;
  dominant_sentiment: string;
}

export interface NetworkBridge {
  label: string;
  platform: string;
  betweenness: number;
  community_id: number;
  post_count: number;
}

export interface NetworkStats {
  node_count: number;
  edge_count: number;
  community_count: number;
  avg_degree: number;
  density: number;
  bridge_count: number;
}

export interface NetworkGraph {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  communities: NetworkCommunity[];
  influencers: NetworkInfluencer[];
  bridges: NetworkBridge[];
  stats: NetworkStats;
  generated_at: string;
  is_synthetic?: boolean;
}

export const networkApi = {
  graph: (days = 7) => api.get<NetworkGraph>(`/network/graph?days=${days}`),
  influencers: (days = 7, top = 10) => api.get<{ items: NetworkInfluencer[]; stats: NetworkStats }>(`/network/influencers?days=${days}&top=${top}`),
  communities: (days = 7) => api.get<{ items: NetworkCommunity[]; stats: NetworkStats }>(`/network/communities?days=${days}`),
  bridges: (days = 7) => api.get<{ items: NetworkBridge[]; stats: NetworkStats }>(`/network/bridges?days=${days}`),
};

export interface ModelStatus {
  name: string;
  loaded: boolean;
  error?: string;
  use_real_nlp: boolean;
}

export interface OllamaStatus {
  available: boolean;
  base_url: string;
  configured_model: string;
  model_ready: boolean;
  available_models: string[];
}

export interface OllamaTestResult {
  prompt: string;
  response: string;
  model: string;
}

export interface PersonaRegenerateResult {
  segment_id: number;
  persona_summary: string;
  generated_by: string;
}

export interface SimulationResult {
  id: string;
  policy_text: string;
  overall_sentiment: SentimentBreakdown;
  overall_confidence: number;
  analogues_used: string[];
  topics_detected: string[];
  segment_responses: SegmentSimulationResponse[];
  influential_communities: string[];
  potential_spread: string;
  llm_brief?: string;
  disclaimer: string;
  generated_at: string;
  mode: string;
}
