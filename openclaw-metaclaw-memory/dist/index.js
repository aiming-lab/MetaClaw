import { parseConfig } from "./types.js";
import { SidecarManager } from "./sidecar.js";
import { SidecarClient } from "./client.js";
import { registerAutoRecall } from "./hooks/auto-recall.js";
import { registerAutoCapture } from "./hooks/auto-capture.js";
import { registerMemorySearchTool } from "./tools/memory-search.js";
import { registerMemoryStoreTool } from "./tools/memory-store.js";
import { registerMemoryForgetTool } from "./tools/memory-forget.js";
import { registerMemoryStatusTool } from "./tools/memory-status.js";
import { registerCli } from "./commands/cli.js";
import { registerSlashCommands } from "./commands/slash.js";
import { configSchema } from "./config-schema.js";
export default {
    id: "metaclaw-memory",
    name: "MetaClaw Memory",
    description: "Self-evolving local-first memory with hybrid retrieval, 6 structured types, and adaptive policy — no cloud required.",
    kind: "memory",
    configSchema,
    register(api) {
        const cfg = parseConfig(api.pluginConfig ?? {});
        let sidecar = null;
        let client = null;
        // Register sidecar as a managed service
        api.registerService({
            id: "metaclaw-memory",
            start: async () => {
                sidecar = new SidecarManager(cfg);
                client = new SidecarClient(`http://127.0.0.1:${cfg.sidecarPort}`);
                await sidecar.start();
                await sidecar.waitForReady();
                api.logger.info("metaclaw-memory: sidecar started");
            },
            stop: () => {
                if (sidecar) {
                    sidecar.stop();
                    api.logger.info("metaclaw-memory: sidecar stopped");
                }
            },
        });
        // Lazy client getter — tools/hooks call this after service.start()
        const getClient = () => {
            if (!client) {
                client = new SidecarClient(`http://127.0.0.1:${cfg.sidecarPort}`);
            }
            return client;
        };
        // Hooks
        registerAutoRecall(api, getClient, cfg);
        registerAutoCapture(api, getClient, cfg);
        // AI tools
        registerMemorySearchTool(api, getClient, cfg);
        registerMemoryStoreTool(api, getClient, cfg);
        registerMemoryForgetTool(api, getClient, cfg);
        registerMemoryStatusTool(api, getClient, cfg);
        // Slash commands (/remember, /recall, /memory-status)
        registerSlashCommands(api, getClient, cfg);
        // CLI commands (openclaw metaclaw setup/status/search/wipe/upgrade)
        registerCli(api, getClient, cfg);
    },
};
//# sourceMappingURL=index.js.map