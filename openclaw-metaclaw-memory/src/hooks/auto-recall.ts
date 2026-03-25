import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"

export function registerAutoRecall(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  if (!config.autoRecall) return

  api.on(
    "before_prompt_build",
    async (event: Record<string, unknown>, _ctx: Record<string, unknown>) => {
      try {
        // Extract the user prompt from the event
        const prompt = extractPrompt(event)
        if (!prompt) return {}

        const client = getClient()
        const result = await client.retrieve(prompt, config.scope)
        if (result.unit_count > 0 && result.rendered_prompt) {
          return { prependContext: result.rendered_prompt }
        }
      } catch (err) {
        api.logger.error("metaclaw-memory: auto-recall failed", err)
      }
      return {}
    },
  )
}

function extractPrompt(event: Record<string, unknown>): string | null {
  // Try event.prompt first
  if (typeof event.prompt === "string" && event.prompt.length > 0) {
    return event.prompt
  }
  // Try extracting from messages array
  const messages = event.messages as unknown[] | undefined
  if (Array.isArray(messages)) {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i] as Record<string, unknown> | undefined
      if (msg && msg.role === "user") {
        const content = msg.content
        if (typeof content === "string") return content
        if (Array.isArray(content)) {
          for (const block of content) {
            const b = block as Record<string, unknown>
            if (b.type === "text" && typeof b.text === "string") return b.text
          }
        }
      }
    }
  }
  return null
}
