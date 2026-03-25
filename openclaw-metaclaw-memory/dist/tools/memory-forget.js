import { Type } from "@sinclair/typebox";
export function registerMemoryForgetTool(api, getClient, config) {
    api.registerTool({
        name: "metaclaw_memory_forget",
        label: "Memory Forget",
        description: "Archive a specific memory by its ID",
        parameters: Type.Object({
            memory_id: Type.String({ description: "The memory ID to archive" }),
        }),
        async execute(_toolCallId, params) {
            const client = getClient();
            await client.forget(params.memory_id);
            return {
                content: [{ type: "text", text: `Memory ${params.memory_id} archived.` }],
            };
        },
    }, { name: "metaclaw_memory_forget" });
}
//# sourceMappingURL=memory-forget.js.map