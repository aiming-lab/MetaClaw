/**
 * Plugin configuration — mirrors configSchema in openclaw.plugin.json.
 */
export interface PluginConfig {
    autoRecall: boolean;
    autoCapture: boolean;
    sidecarPort: number;
    scope: string;
    retrievalMode: "keyword" | "embedding" | "hybrid";
    maxInjectedTokens: number;
    maxInjectedUnits: number;
    memoryDir: string;
    autoUpgradeEnabled: boolean;
    pythonPath: string;
    debug: boolean;
}
export declare const defaultConfig: PluginConfig;
export declare function parseConfig(raw: Record<string, unknown>): PluginConfig;
export interface MemoryUnit {
    memory_id: string;
    scope_id: string;
    memory_type: "episodic" | "semantic" | "preference" | "project_state" | "working_summary" | "procedural_observation";
    content: string;
    summary: string;
    importance: number;
    confidence: number;
    access_count: number;
    status: string;
    tags: string[];
    created_at: string;
    updated_at: string;
}
export interface SearchResult {
    unit: MemoryUnit;
    score: number;
    matched_terms: string[];
    reason: string;
}
export interface RetrieveResponse {
    rendered_prompt: string;
    unit_count: number;
}
export interface IngestResponse {
    added: number;
}
export interface StoreResponse {
    memory_id: string;
}
export interface HealthResponse {
    status: string;
    memories: number;
    scope: string;
}
export interface StatsResponse {
    [key: string]: string | number;
}
export interface ConsolidateResponse {
    superseded: number;
    decayed: number;
    reinforced: number;
}
export interface UpgradeStatusResponse {
    state: string;
    last_cycle: string | null;
}
