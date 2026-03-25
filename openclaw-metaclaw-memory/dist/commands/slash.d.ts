import type { SidecarClient } from "../client.js";
import type { PluginConfig } from "../types.js";
/**
 * Register slash commands that execute without invoking the AI agent.
 * These are auto-reply commands: /remember, /recall, /memory-status
 */
export declare function registerSlashCommands(api: any, getClient: () => SidecarClient, config: PluginConfig): void;
