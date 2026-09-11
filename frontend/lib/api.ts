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
  run: (policy_text: string, target_population?: string, question?: string) =>
    api.post<SimulationResult>("/simulation/run", { policy_text, target_population, question }),
};

export const ingestApi = {
  status: () => api.get<ConnectorStatus[]>("/ingest/status"),
  stats: () => api.get<IngestionStats>("/ingest/stats"),
  trigger: () => api.post<{ status: string; task_id: string }>("/ingest/trigger"),
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

export interface SimulationResult {
  id: string;
  policy_text: string;
  overall_sentiment: SentimentBreakdown;
  overall_confidence: number;
  analogues_used: string[];
  segment_responses: SegmentSimulationResponse[];
  influential_communities: string[];
  potential_spread: string;
  disclaimer: string;
  generated_at: string;
  mode: string;
}
