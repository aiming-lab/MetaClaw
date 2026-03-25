import { Type } from "@sinclair/typebox";
export function registerMemoryStatusTool(api, getClient, config) {
    api.registerTool({
        name: "metaclaw_memory_status",
        label: "Memory Status",
        description: "Get memory system health and statistics",
        parameters: Type.Object({}),
        async execute() {
            const client = getClient();
            const [health, stats] = await Promise.all([
                client.health(),
                client.stats(),
            ]);
            const lines = [
                `Status: ${health.status}`,
                `Memories: ${health.memories}`,
                `Scope: ${health.scope}`,
                "",
                "Stats:",
                ...Object.entries(stats).map(([k, v]) => `  ${k}: ${v}`),
            ];
            return {
                content: [{ type: "text", text: lines.join("\n") }],
            };
        },
    }, { name: "metaclaw_memory_status" });
}
//# sourceMappingURL=memory-status.js.map