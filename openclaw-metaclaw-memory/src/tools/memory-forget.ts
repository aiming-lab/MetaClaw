import { Type } from "@sinclair/typebox"
import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"

export function registerMemoryForgetTool(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  api.registerTool(
    {
      name: "metaclaw_memory_forget",
      label: "Memory Forget",
      description: "Archive a specific memory by its ID",
      parameters: Type.Object({
        memory_id: Type.String({ description: "The memory ID to archive" }),
      }),
      async execute(
        _toolCallId: string,
        params: { memory_id: string },
      ) {
        const client = getClient()
        await client.forget(params.memory_id)
        return {
          content: [{ type: "text", text: `Memory ${params.memory_id} archived.` }],
        }
      },
    },
    { name: "metaclaw_memory_forget" },
  )
}
