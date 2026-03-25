/**
 * Plugin configuration — mirrors configSchema in openclaw.plugin.json.
 */
export interface PluginConfig {
  autoRecall: boolean
  autoCapture: boolean
  sidecarPort: number
  scope: string
  retrievalMode: "keyword" | "embedding" | "hybrid"
  maxInjectedTokens: number
  maxInjectedUnits: number
  memoryDir: string
  autoUpgradeEnabled: boolean
  pythonPath: string
  debug: boolean
}

export const defaultConfig: PluginConfig = {
  autoRecall: true,
  autoCapture: true,
  sidecarPort: 19823,
  scope: "default",
  retrievalMode: "hybrid",
  maxInjectedTokens: 800,
  maxInjectedUnits: 6,
  memoryDir: "~/.metaclaw/memory",
  autoUpgradeEnabled: false,
  pythonPath: "python3",
  debug: false,
}

export function parseConfig(raw: Record<string, unknown>): PluginConfig {
  return {
    autoRecall: (raw.autoRecall as boolean) ?? defaultConfig.autoRecall,
    autoCapture: (raw.autoCapture as boolean) ?? defaultConfig.autoCapture,
    sidecarPort: (raw.sidecarPort as number) ?? defaultConfig.sidecarPort,
    scope: (raw.scope as string) ?? defaultConfig.scope,
    retrievalMode: (raw.retrievalMode as PluginConfig["retrievalMode"]) ?? defaultConfig.retrievalMode,
    maxInjectedTokens: (raw.maxInjectedTokens as number) ?? defaultConfig.maxInjectedTokens,
    maxInjectedUnits: (raw.maxInjectedUnits as number) ?? defaultConfig.maxInjectedUnits,
    memoryDir: (raw.memoryDir as string) ?? defaultConfig.memoryDir,
    autoUpgradeEnabled: (raw.autoUpgradeEnabled as boolean) ?? defaultConfig.autoUpgradeEnabled,
    pythonPath: (raw.pythonPath as string) ?? defaultConfig.pythonPath,
    debug: (raw.debug as boolean) ?? defaultConfig.debug,
  }
}

// ---------- Sidecar response types ----------

export interface MemoryUnit {
  memory_id: string
  scope_id: string
  memory_type: "episodic" | "semantic" | "preference" | "project_state" | "working_summary" | "procedural_observation"
  content: string
  summary: string
  importance: number
  confidence: number
  access_count: number
  status: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface SearchResult {
  unit: MemoryUnit
  score: number
  matched_terms: string[]
  reason: string
}

export interface RetrieveResponse {
  rendered_prompt: string
  unit_count: number
}

export interface IngestResponse {
  added: number
}

export interface StoreResponse {
  memory_id: string
}

export interface HealthResponse {
  status: string
  memories: number
  scope: string
}

export interface StatsResponse {
  [key: string]: string | number
}

export interface ConsolidateResponse {
  superseded: number
  decayed: number
  reinforced: number
}

export interface UpgradeStatusResponse {
  state: string
  last_cycle: string | null
}
