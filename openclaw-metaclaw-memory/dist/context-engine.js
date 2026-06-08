function extractUserPrompt(messages) {
    for (let i = messages.length - 1; i >= 0; i--) {
        const msg = messages[i];
        if (!msg || msg.role !== "user")
            continue;
        const content = msg.content;
        if (typeof content === "string") {
            const trimmed = content.trim();
            return trimmed.length > 0 ? trimmed : null;
        }
        if (Array.isArray(content)) {
            const parts = [];
            for (const block of content) {
                if (block && typeof block === "object") {
                    const b = block;
                    if (typeof b.text === "string") {
                        parts.push(b.text);
                    }
                    else if (b.type === "text" && typeof b.content === "string") {
                        parts.push(b.content);
                    }
                }
                else if (typeof block === "string") {
                    parts.push(block);
                }
            }
            const joined = parts.join("\n").trim();
            return joined.length > 0 ? joined : null;
        }
    }
    return null;
}
export function createMetaClawContextEngine(getClient, cfg, logger) {
    return {
        async bootstrap() {
            const client = getClient();
            try {
                await client.health();
                logger.info("metaclaw-memory: context-engine bootstrap ok (sidecar healthy)");
            }
            catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                logger.error(`metaclaw-memory: context-engine bootstrap failed: ${msg}`);
                throw new Error(`metaclaw-memory context-engine bootstrap failed: ${msg}`);
            }
        },
        async ingest(_messages) {
            // No-op: turn ingestion is handled by auto-capture hook + sidecar scheduler.
        },
        async ingestBatch(_messages) {
            // No-op: same as ingest — sidecar scheduler handles batching.
        },
        async afterTurn(_result) {
            // No-op: consolidation handled by sidecar scheduler.
        },
        async assemble(query) {
            const prompt = extractUserPrompt(query.messages);
            if (!prompt) {
                return { messages: query.messages, estimatedTokens: 0 };
            }
            try {
                const result = await getClient().retrieve(prompt, cfg.scope);
                if (result.unit_count > 0 && result.rendered_prompt) {
                    return {
                        messages: query.messages,
                        estimatedTokens: Math.ceil(result.rendered_prompt.length / 4),
                        systemPromptAddition: result.rendered_prompt,
                    };
                }
                return { messages: query.messages, estimatedTokens: 0 };
            }
            catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                logger.warn(`metaclaw-memory: assemble retrieve failed: ${msg}`);
                return { messages: query.messages, estimatedTokens: 0 };
            }
        },
        async compact(_sessionId) {
            try {
                await getClient().consolidate(cfg.scope);
                return { ok: true, compacted: true };
            }
            catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                logger.warn(`metaclaw-memory: compact consolidate failed: ${msg}`);
                return { ok: false, compacted: false, reason: msg };
            }
        },
        async dispose() {
            // No-op: sidecar lifecycle managed by SidecarManager via registerService.
        },
    };
}
//# sourceMappingURL=context-engine.js.map