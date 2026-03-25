import type { SidecarClient } from "../client.js"
import type { PluginConfig } from "../types.js"
import { randomUUID } from "node:crypto"

export function registerAutoCapture(
  api: any,
  getClient: () => SidecarClient,
  config: PluginConfig,
): void {
  if (!config.autoCapture) return

  api.on(
    "agent_end",
    async (event: Record<string, unknown>, _ctx: Record<string, unknown>) => {
      try {
        if (!event.success) return
        const messages = event.messages as unknown[] | undefined
        if (!Array.isArray(messages) || messages.length === 0) return

        const turns = extractTurns(messages)
        if (turns.length === 0) return

        const sessionId = (event.sessionId as string) || randomUUID()
        const client = getClient()
        const result = await client.ingest(sessionId, turns, config.scope)
        if (result.added > 0) {
          api.logger.info(
            `metaclaw-memory: captured ${result.added} memories from session ${sessionId}`,
          )
        }
      } catch (err) {
        api.logger.error("metaclaw-memory: auto-capture failed", err)
      }
    },
  )
}

interface Turn {
  prompt_text: string
  response_text: string
}

function extractTurns(messages: unknown[]): Turn[] {
  const turns: Turn[] = []
  let pendingPrompt: string | null = null

  for (const msg of messages) {
    if (!msg || typeof msg !== "object") continue
    const m = msg as Record<string, unknown>
    const text = extractText(m.content)
    if (!text) continue

    if (m.role === "user") {
      pendingPrompt = text
    } else if (m.role === "assistant" && pendingPrompt) {
      turns.push({ prompt_text: pendingPrompt, response_text: text })
      pendingPrompt = null
    }
  }
  return turns
}

function extractText(content: unknown): string | null {
  if (typeof content === "string") return content
  if (Array.isArray(content)) {
    const parts: string[] = []
    for (const block of content) {
      if (!block || typeof block !== "object") continue
      const b = block as Record<string, unknown>
      if (b.type === "text" && typeof b.text === "string") {
        parts.push(b.text)
      }
    }
    return parts.length > 0 ? parts.join("\n") : null
  }
  return null
}
