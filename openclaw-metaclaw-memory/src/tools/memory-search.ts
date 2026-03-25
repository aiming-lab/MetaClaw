import { Type } from "@sinclair/typebox"
import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"

export function registerMemorySearchTool(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  api.registerTool(
    {
      name: "metaclaw_memory_search",
      label: "Memory Search",
      description: "Search long-term memories by keyword or semantic query",
      parameters: Type.Object({
        query: Type.String({ description: "Search query" }),
        limit: Type.Optional(
          Type.Number({ description: "Max results to return", default: 10 }),
        ),
      }),
      async execute(
        _toolCallId: string,
        params: { query: string; limit?: number },
      ) {
        const client = getClient()
        const results = await client.search(params.query, config.scope, params.limit)

        if (results.length === 0) {
          return { content: [{ type: "text", text: "No memories found matching the query." }] }
        }

        const formatted = results
          .map(
            (r, i) =>
              [
                `[${i + 1}] ${r.unit.summary || r.unit.content.slice(0, 120)}`,
                `    id: ${r.unit.memory_id} | type: ${r.unit.memory_type} | score: ${r.score.toFixed(3)}`,
                `    tags: ${r.unit.tags.join(", ") || "none"}`,
                r.reason ? `    reason: ${r.reason}` : null,
              ]
                .filter(Boolean)
                .join("\n"),
          )
          .join("\n\n")

        return { content: [{ type: "text", text: formatted }] }
      },
    },
    { name: "metaclaw_memory_search" },
  )
}
