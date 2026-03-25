export class SidecarClient {
    baseUrl;
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    async request(path, body) {
        const url = `${this.baseUrl}${path}`;
        const options = {
            method: body ? "POST" : "GET",
            headers: { "Content-Type": "application/json" },
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        const res = await fetch(url, options);
        if (!res.ok) {
            const text = await res.text().catch(() => "unknown error");
            throw new Error(`Sidecar ${path} failed (${res.status}): ${text}`);
        }
        return res.json();
    }
    async health() {
        return this.request("/health");
    }
    async retrieve(taskDescription, scopeId) {
        return this.request("/retrieve", {
            task_description: taskDescription,
            ...(scopeId && { scope_id: scopeId }),
        });
    }
    async ingest(sessionId, turns, scopeId) {
        return this.request("/ingest", {
            session_id: sessionId,
            turns,
            ...(scopeId && { scope_id: scopeId }),
        });
    }
    async search(query, scopeId, limit) {
        const resp = await this.request("/search", {
            query,
            ...(scopeId && { scope_id: scopeId }),
            ...(limit !== undefined && { limit }),
        });
        return resp.results;
    }
    async store(content, memoryType, scopeId, tags, importance) {
        return this.request("/store", {
            content,
            memory_type: memoryType,
            ...(scopeId && { scope_id: scopeId }),
            ...(tags && { tags }),
            ...(importance !== undefined && { importance }),
        });
    }
    async forget(memoryId) {
        return this.request("/forget", { memory_id: memoryId });
    }
    async stats() {
        return this.request("/stats");
    }
    async consolidate(scopeId) {
        return this.request("/consolidate", {
            ...(scopeId && { scope_id: scopeId }),
        });
    }
    async upgradeStatus() {
        return this.request("/upgrade/status");
    }
    async upgradeTrigger() {
        return this.request("/upgrade/trigger", {});
    }
}
//# sourceMappingURL=client.js.map