import type {
  HealthResponse,
  RetrieveResponse,
  IngestResponse,
  SearchResult,
  StoreResponse,
  StatsResponse,
  ConsolidateResponse,
  UpgradeStatusResponse,
} from "./types.js"

export class SidecarClient {
  constructor(private baseUrl: string) {}

  private async request<T>(path: string, body?: Record<string, unknown>): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const options: RequestInit = {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json" },
    }
    if (body) {
      options.body = JSON.stringify(body)
    }

    const res = await fetch(url, options)
    if (!res.ok) {
      const text = await res.text().catch(() => "unknown error")
      throw new Error(`Sidecar ${path} failed (${res.status}): ${text}`)
    }
    return res.json() as Promise<T>
  }

  async health(): Promise<HealthResponse> {
    return this.request("/health")
  }

  async retrieve(taskDescription: string, scopeId?: string): Promise<RetrieveResponse> {
    return this.request("/retrieve", {
      task_description: taskDescription,
      ...(scopeId && { scope_id: scopeId }),
    })
  }

  async ingest(
    sessionId: string,
    turns: Array<{ prompt_text: string; response_text: string }>,
    scopeId?: string,
  ): Promise<IngestResponse> {
    return this.request("/ingest", {
      session_id: sessionId,
      turns,
      ...(scopeId && { scope_id: scopeId }),
    })
  }

  async search(query: string, scopeId?: string, limit?: number): Promise<SearchResult[]> {
    const resp = await this.request<{ results: SearchResult[] }>("/search", {
      query,
      ...(scopeId && { scope_id: scopeId }),
      ...(limit !== undefined && { limit }),
    })
    return resp.results
  }

  async store(
    content: string,
    memoryType: string,
    scopeId?: string,
    tags?: string[],
    importance?: number,
  ): Promise<StoreResponse> {
    return this.request("/store", {
      content,
      memory_type: memoryType,
      ...(scopeId && { scope_id: scopeId }),
      ...(tags && { tags }),
      ...(importance !== undefined && { importance }),
    })
  }

  async forget(memoryId: string): Promise<{ ok: boolean }> {
    return this.request("/forget", { memory_id: memoryId })
  }

  async stats(): Promise<StatsResponse> {
    return this.request("/stats")
  }

  async consolidate(scopeId?: string): Promise<ConsolidateResponse> {
    return this.request("/consolidate", {
      ...(scopeId && { scope_id: scopeId }),
    })
  }

  async upgradeStatus(): Promise<UpgradeStatusResponse> {
    return this.request("/upgrade/status")
  }

  async upgradeTrigger(): Promise<{ ok: boolean }> {
    return this.request("/upgrade/trigger", {})
  }
}
