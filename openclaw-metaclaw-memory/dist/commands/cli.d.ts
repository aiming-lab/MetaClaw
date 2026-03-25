import type { SidecarClient } from "../client.js";
import type { PluginConfig } from "../types.js";
/**
 * Register CLI commands under `openclaw metaclaw <subcommand>`.
 */
export declare function registerCli(api: any, getClient: () => SidecarClient, config: PluginConfig): void;
