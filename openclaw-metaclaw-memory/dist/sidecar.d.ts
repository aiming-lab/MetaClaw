import type { PluginConfig } from "./types.js";
export declare class SidecarManager {
    private config;
    private process;
    constructor(config: PluginConfig);
    /**
     * Resolve the Python interpreter to use.
     * Prefers the venv created by `openclaw metaclaw setup`, falls back to config.
     */
    private resolvePython;
    start(): Promise<void>;
    waitForReady(timeoutMs?: number): Promise<void>;
    stop(): Promise<void>;
    isRunning(): boolean;
}
