export function registerAutoRecall(api, getClient, config) {
    if (!config.autoRecall)
        return;
    api.on("before_prompt_build", async (event, _ctx) => {
        try {
            // Extract the user prompt from the event
            const prompt = extractPrompt(event);
            if (!prompt)
                return {};
            const client = getClient();
            const result = await client.retrieve(prompt, config.scope);
            if (result.unit_count > 0 && result.rendered_prompt) {
                return { prependContext: result.rendered_prompt };
            }
        }
        catch (err) {
            api.logger.error("metaclaw-memory: auto-recall failed", err);
        }
        return {};
    });
}
function extractPrompt(event) {
    // Try event.prompt first
    if (typeof event.prompt === "string" && event.prompt.length > 0) {
        return event.prompt;
    }
    // Try extracting from messages array
    const messages = event.messages;
    if (Array.isArray(messages)) {
        for (let i = messages.length - 1; i >= 0; i--) {
            const msg = messages[i];
            if (msg && msg.role === "user") {
                const content = msg.content;
                if (typeof content === "string")
                    return content;
                if (Array.isArray(content)) {
                    for (const block of content) {
                        const b = block;
                        if (b.type === "text" && typeof b.text === "string")
                            return b.text;
                    }
                }
            }
        }
    }
    return null;
}
//# sourceMappingURL=auto-recall.js.map