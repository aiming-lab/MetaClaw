import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"

/**
 * Register slash commands that execute without invoking the AI agent.
 * These are auto-reply commands: /remember, /recall, /memory-status
 */
export function registerSlashCommands(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  // /remember <text> — manually store a memory
  api.registerCommand({
    name: "remember",
    description: "Save information to long-term memory",
    acceptsArgs: true,
    requireAuth: false,
    handler: async (ctx: { args?: string }) => {
      if (!ctx.args || ctx.args.trim().length === 0) {
        return { text: "Usage: /remember <text to remember>" }
      }
      try {
        const client = getClient()
        const result = await client.store(ctx.args.trim(), "semantic", config.scope)
        return { text: `Remembered (id: ${result.memory_id})` }
      } catch {
        return { text: "Failed to store memory. Is the sidecar running?" }
      }
    },
  })

  // /recall <query> — search memories
  api.registerCommand({
    name: "recall",
    description: "Search long-term memories",
    acceptsArgs: true,
    requireAuth: false,
    handler: async (ctx: { args?: string }) => {
      if (!ctx.args || ctx.args.trim().length === 0) {
        return { text: "Usage: /recall <search query>" }
      }
      try {
        const client = getClient()
        const results = await client.search(ctx.args.trim(), config.scope)

        if (results.length === 0) {
          return { text: "No memories found." }
        }

        const lines = results.map(
          (r, i) =>
            `[${i + 1}] ${r.unit.summary || r.unit.content.slice(0, 120)} (score: ${r.score.toFixed(3)})`,
        )
        return { text: lines.join("\n") }
      } catch {
        return { text: "Search failed. Is the sidecar running?" }
      }
    },
  })

  // /memory-status — quick health check
  api.registerCommand({
    name: "memory-status",
    description: "Show MetaClaw memory system status",
    acceptsArgs: false,
    requireAuth: false,
    handler: async () => {
      try {
        const client = getClient()
        const health = await client.health()
        return {
          text: `Status: ${health.status} | Memories: ${health.memories} | Scope: ${health.scope}`,
        }
      } catch {
        return { text: "Sidecar not reachable. Run: openclaw metaclaw setup" }
      }
    },
  })
}
