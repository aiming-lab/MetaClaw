import type { SidecarClient } from "./client.js";
import type { PluginConfig } from "./types.js";
interface AssembleQuery {
    sessionId: string;
    messages: Array<Record<string, unknown>>;
    systemPrompt?: string;
}
interface AssembleResult {
    messages: Array<Record<string, unknown>>;
    estimatedTokens: number;
    systemPromptAddition?: string;
}
interface CompactResult {
    ok: boolean;
    compacted: boolean;
    reason?: string;
}
interface ContextEngine {
    bootstrap(): Promise<void>;
    ingest?(messages: Array<Record<string, unknown>>): Promise<void>;
    ingestBatch?(messages: Array<Array<Record<string, unknown>>>): Promise<void>;
    afterTurn?(result: Record<string, unknown>): Promise<void>;
    assemble(query: AssembleQuery): Promise<AssembleResult>;
    compact?(sessionId: string): Promise<CompactResult>;
    dispose(): Promise<void>;
}
interface Logger {
    info(message: string, ...args: unknown[]): void;
    warn(message: string, ...args: unknown[]): void;
    error(message: string, ...args: unknown[]): void;
    debug?(message: string, ...args: unknown[]): void;
}
export declare function createMetaClawContextEngine(getClient: () => SidecarClient, cfg: PluginConfig, logger: Logger): ContextEngine;
export {};
