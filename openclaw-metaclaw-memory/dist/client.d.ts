import type { HealthResponse, RetrieveResponse, IngestResponse, BufferTurnResponse, FlushSessionResponse, SearchResult, StoreResponse, StatsResponse, ConsolidateResponse, UpgradeStatusResponse } from "./types.js";
export declare class SidecarClient {
    private baseUrl;
    constructor(baseUrl: string);
    private request;
    health(): Promise<HealthResponse>;
    retrieve(taskDescription: string, scopeId?: string): Promise<RetrieveResponse>;
    ingest(sessionId: string, turns: Array<{
        prompt_text: string;
        response_text: string;
    }>, scopeId?: string): Promise<IngestResponse>;
    bufferTurn(sessionId: string, turn: {
        prompt_text: string;
        response_text: string;
    }, scopeId?: string): Promise<BufferTurnResponse>;
    flushSession(sessionId: string, scopeId?: string, final?: boolean): Promise<FlushSessionResponse>;
    search(query: string, scopeId?: string, limit?: number): Promise<SearchResult[]>;
    store(content: string, memoryType: string, scopeId?: string, tags?: string[], importance?: number): Promise<StoreResponse>;
    forget(memoryId: string): Promise<{
        ok: boolean;
    }>;
    stats(): Promise<StatsResponse>;
    consolidate(scopeId?: string): Promise<ConsolidateResponse>;
    upgradeStatus(): Promise<UpgradeStatusResponse>;
    upgradeTrigger(): Promise<{
        ok: boolean;
    }>;
}
