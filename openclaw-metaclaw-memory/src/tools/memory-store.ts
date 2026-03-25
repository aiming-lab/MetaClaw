import { Type } from "@sinclair/typebox"
import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"

const MEMORY_TYPES = [
  "episodic",
  "semantic",
  "preference",
  "project_state",
  "working_summary",
  "procedural_observation",
] as const

function stringEnum<T extends readonly string[]>(values: T) {
  return Type.Unsafe<T[number]>({
    type: "string",
    enum: values as unknown as string[],
  })
}

export function registerMemoryStoreTool(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  api.registerTool(
    {
      name: "metaclaw_memory_store",
      label: "Memory Store",
      description: "Store a new memory explicitly",
      parameters: Type.Object({
        content: Type.String({ description: "Memory content to store" }),
        memory_type: Type.Optional(
          stringEnum(MEMORY_TYPES),
        ),
        tags: Type.Optional(
          Type.Array(Type.String(), { description: "Tags for categorization" }),
        ),
        importance: Type.Optional(
          Type.Number({ description: "Importance score (0.0 to 1.0)" }),
        ),
      }),
      async execute(
        _toolCallId: string,
        params: {
          content: string
          memory_type?: string
          tags?: string[]
          importance?: number
        },
      ) {
        const client = getClient()
        const result = await client.store(
          params.content,
          params.memory_type ?? "semantic",
          config.scope,
          params.tags,
          params.importance,
        )
        return {
          content: [{ type: "text", text: `Stored memory with id: ${result.memory_id}` }],
        }
      },
    },
    { name: "metaclaw_memory_store" },
  )
}
