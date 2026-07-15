const API_BASE = (() => {
  const fromEnv = process.env.NEXT_PUBLIC_AI_OS_API_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (process.env.NODE_ENV === "production") {
    return "https://api.sedr.ca";
  }
  return "http://127.0.0.1:8741";
})();

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(`API ${res.status}: ${path}`, res.status, body);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/v1/health"),

  dashboard: () => request<DashboardData>("/api/v1/dashboard"),

  knowledge: {
    status: () => request<KnowledgeHealth>("/api/v1/knowledge/status"),
    sources: () => request<SourceRecord[]>("/api/v1/knowledge/sources"),
    documents: () => request<KnowledgeDocument[]>("/api/v1/knowledge/documents"),
    document: (id: string) =>
      request<{ document: unknown; chunks: unknown[] }>(
        `/api/v1/knowledge/documents/${id}`,
      ),
    search: (query: string, mode = "hybrid", topK = 10) =>
      request<SearchHit[]>("/api/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ query, mode, top_k: topK }),
      }),
    retrieve: (query: string) =>
      request<unknown>("/api/v1/knowledge/retrieve", {
        method: "POST",
        body: JSON.stringify({ query }),
      }),
    reindex: () =>
      request<{ status: string }>("/api/v1/knowledge/reindex", { method: "POST" }),
  },

  memory: {
    list: (memoryType?: string) =>
      request<MemoryRecord[]>(
        `/api/v1/memory${memoryType ? `?memory_type=${memoryType}` : ""}`,
      ),
    search: (query: string, limit = 20) =>
      request<MemoryRecord[]>("/api/v1/memory/search", {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      }),
    get: (id: string) => request<MemoryRecord>(`/api/v1/memory/${id}`),
    insights: () => request<MemoryInsights>("/api/v1/memory/insights/summary"),
    timeline: (query = "") =>
      request<TimelineEvent[]>(
        `/api/v1/memory/timeline/events?query=${encodeURIComponent(query)}`,
      ),
  },

  decisions: {
    list: () => request<DecisionResult[]>("/api/v1/decisions"),
    get: (id: string) => request<DecisionResult>(`/api/v1/decisions/${id}`),
    create: (body: unknown) =>
      request<DecisionResult>("/api/v1/decisions", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },

  workflows: {
    list: () => request<Workflow[]>("/api/v1/workflows"),
    get: (id: string) => request<Workflow>(`/api/v1/workflows/${id}`),
    run: (id: string, inputs: Record<string, unknown> = {}) =>
      request<ExecutionResult>(`/api/v1/workflows/${id}/run`, {
        method: "POST",
        body: JSON.stringify({ inputs }),
      }),
  },

  agents: {
    list: () => request<Agent[]>("/api/v1/agents"),
  },

  tasks: {
    list: () => request<AgentTask[]>("/api/v1/tasks"),
    get: (id: string) =>
      request<{ task: AgentTask; logs: LogEntry[] }>(`/api/v1/tasks/${id}`),
  },

  automations: {
    list: () => request<Automation[]>("/api/v1/automations"),
    history: (limit = 20) =>
      request<ExecutionRecord[]>(`/api/v1/automations/history?limit=${limit}`),
    run: (id: string) =>
      request<ExecutionRecord>(`/api/v1/automations/${id}/run`, {
        method: "POST",
      }),
    enable: (id: string) =>
      request<Automation>(`/api/v1/automations/${id}/enable`, { method: "POST" }),
    disable: (id: string) =>
      request<Automation>(`/api/v1/automations/${id}/disable`, { method: "POST" }),
  },

  providers: {
    list: () => request<ProviderSummary[]>("/api/v1/providers"),
    health: () => request<ProviderHealth[]>("/api/v1/providers/health"),
    capabilities: (id: string) =>
      request<unknown[]>(`/api/v1/providers/${id}/capabilities`),
  },

  models: {
    list: () => request<ModelProfile[]>("/api/v1/models"),
    routing: () => request<RoutingSettings>("/api/v1/models/routing"),
    route: (task: string) =>
      request<ModelRoute>("/api/v1/models/route", {
        method: "POST",
        body: JSON.stringify({ task }),
      }),
  },

  settings: {
    all: () => request<Record<string, unknown>>("/api/v1/settings"),
    paths: () => request<ConfigPath[]>("/api/v1/settings/paths"),
    version: () => request<{ name: string; version: string }>("/api/v1/settings/version"),
    doctor: () =>
      request<unknown>("/api/v1/settings/doctor", { method: "POST" }),
  },

  search: {
    global: (q: string) =>
      request<GlobalSearchResult>(`/api/v1/search?q=${encodeURIComponent(q)}`),
  },

  imports: {
    presets: () => request<ImportPreset[]>("/api/v1/imports/presets"),
    validate: (presetId: string, sourcePath: string) =>
      request<ImportValidation>("/api/v1/imports/validate", {
        method: "POST",
        body: JSON.stringify({ preset_id: presetId, source_path: sourcePath }),
      }),
    run: (presetId: string, sourcePath: string) =>
      request<ImportProgress>("/api/v1/imports/run", {
        method: "POST",
        body: JSON.stringify({ preset_id: presetId, source_path: sourcePath }),
      }),
    /** Upload via same-origin Next.js proxy (server holds AI_OS_API_KEY). */
    upload: async (
      files: File[],
      presetId: string,
      tags = "",
    ): Promise<UploadProgress> => {
      const form = new FormData();
      form.append("preset_id", presetId);
      if (tags) form.append("tags", tags);
      for (const file of files) {
        form.append("files", file);
      }
      const res = await fetch("/api/imports/upload", {
        method: "POST",
        body: form,
        cache: "no-store",
      });
      if (!res.ok) {
        let body: unknown;
        try {
          body = await res.json();
        } catch {
          body = await res.text();
        }
        throw new ApiError(`API ${res.status}: /api/imports/upload`, res.status, body);
      }
      return res.json() as Promise<UploadProgress>;
    },
  },
};

// Types (subset — API returns full pydantic shapes)
export interface DashboardData {
  status: string;
  counts: Record<string, number>;
  health: KnowledgeHealth;
  provider_health: ProviderHealth[];
  model_route: ModelRoute;
  routing_settings: RoutingSettings;
  recent_decisions: DecisionResult[];
  recent_memories: MemoryRecord[];
  recent_knowledge: SearchHit[];
  recent_activity: ExecutionRecord[];
  recent_tasks: AgentTask[];
  workflows: Workflow[];
  automations: Automation[];
}

export interface KnowledgeHealth {
  healthy: boolean;
  document_count: number;
  chunk_count: number;
  source_count: number;
  storage_bytes: number;
  ollama_available: boolean;
  embedding_model: string;
  warnings?: string[];
  recommendations?: string[];
}

export interface SourceRecord {
  source_id: string;
  original_uri: string;
  status: string;
  title?: string;
}

export interface KnowledgeDocument {
  doc_id: string;
  title: string;
  source_uri?: string;
}

export interface SearchHit {
  score: number;
  doc_id: string;
  chunk_id: string;
  title: string;
  section?: string;
  excerpt: string;
}

export interface MemoryRecord {
  memory_id: string;
  memory_type: string;
  status: string;
  title?: string;
  summary?: string;
  created_at: string;
}

export interface MemoryInsights {
  duplicates: string[][];
  clusters: Record<string, string[]>;
  contradictions: unknown[];
  promotions: unknown[];
  graph: Record<string, string[]>;
}

export interface TimelineEvent {
  occurred_at: string;
  event_type: string;
  title: string;
}

export interface DecisionResult {
  decision_id: string;
  request: { question: string; strategy: string };
  confidence: number;
  status: string;
  created_at: string;
  recommendation?: { title: string; rationale: string };
  options?: unknown[];
  evidence?: unknown[];
  risks?: unknown[];
  tradeoffs?: unknown[];
  reasoning_trace?: unknown[];
}

export interface Workflow {
  workflow_id: string;
  name: string;
  description?: string;
  steps?: unknown[];
}

export interface Agent {
  agent_id: string;
  name: string;
  description?: string;
  tools: string[];
}

export interface AgentTask {
  task_id: string;
  workflow_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface ExecutionResult {
  task_id: string;
  status: string;
  steps_completed: number;
  duration_ms: number;
  error?: string;
}

export interface Automation {
  automation_id: string;
  name: string;
  description?: string;
  status: string;
  workflow_id: string;
  schedule?: unknown;
}

export interface ExecutionRecord {
  execution_id: string;
  automation_id: string;
  status: string;
  started_at?: string;
  duration_ms?: number;
}

export interface ProviderSummary {
  provider_id: string;
  name: string;
  enabled: boolean;
  credentials_present: boolean;
}

export interface ProviderHealth {
  provider_id: string;
  status: string;
  message: string;
  latency_ms?: number;
}

export interface ModelProfile {
  provider_id: string;
  model_id: string;
  context_length: number;
  is_local: boolean;
}

export interface RoutingSettings {
  default_provider: string;
  fallback_chain: string;
  prefer_local: boolean;
}

export interface ModelRoute {
  provider_id: string;
  model_id: string;
  score: number;
  fallback_chain: string[];
}

export interface ConfigPath {
  key: string;
  path: string;
  exists: boolean;
}

export interface GlobalSearchResult {
  query: string;
  knowledge: SearchHit[];
  memories: MemoryRecord[];
  decisions: DecisionResult[];
  workflows: Workflow[];
  automations: Automation[];
}

export interface ImportPreset {
  id: string;
  name: string;
  description: string;
  suggested_path: string;
  source_type: string;
}

export interface ImportValidation {
  ready: boolean;
  total_files: number;
  new_files: number;
  estimated_minutes: number;
  errors: string[];
}

export interface ImportProgress {
  total: number;
  processed: number;
  ingested: number;
  skipped: number;
  failed: number;
  errors: string[];
}

export interface UploadProgress extends ImportProgress {
  saved_files: number;
  rejected?: string[];
  document_count?: number;
  chunk_count?: number;
  duplicate_files?: number;
}
