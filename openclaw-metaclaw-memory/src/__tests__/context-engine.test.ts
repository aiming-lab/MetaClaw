import { describe, it, expect, vi } from "vitest";
import { createMetaClawContextEngine } from "../context-engine.js";

function makeLogger() {
  return { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
}

const cfg = { scope: "default" } as any;

describe("createMetaClawContextEngine", () => {
  describe("assemble", () => {
    it("returns systemPromptAddition when sidecar has memories", async () => {
      const mockClient = {
        retrieve: vi.fn().mockResolvedValue({
          unit_count: 2,
          rendered_prompt: "Memory 1: ...\nMemory 2: ...",
        }),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      const result = await engine.assemble({
        sessionId: "test-session",
        messages: [{ role: "user", content: "What is MetaClaw?" }],
      });

      expect(result.systemPromptAddition).toBe("Memory 1: ...\nMemory 2: ...");
      expect(result.estimatedTokens).toBeGreaterThan(0);
      expect(result.messages).toHaveLength(1);
      expect(mockClient.retrieve).toHaveBeenCalledWith("What is MetaClaw?", "default");
    });

    it("returns empty when no user message found", async () => {
      const mockClient = { retrieve: vi.fn() };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      const result = await engine.assemble({
        sessionId: "test-session",
        messages: [{ role: "system", content: "You are helpful" }],
      });

      expect(result.systemPromptAddition).toBeUndefined();
      expect(result.estimatedTokens).toBe(0);
      expect(mockClient.retrieve).not.toHaveBeenCalled();
    });

    it("returns empty when sidecar has no memories", async () => {
      const mockClient = {
        retrieve: vi.fn().mockResolvedValue({ unit_count: 0, rendered_prompt: null }),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      const result = await engine.assemble({
        sessionId: "test",
        messages: [{ role: "user", content: "hello" }],
      });

      expect(result.systemPromptAddition).toBeUndefined();
      expect(result.estimatedTokens).toBe(0);
    });

    it("gracefully handles retrieve errors", async () => {
      const mockClient = {
        retrieve: vi.fn().mockRejectedValue(new Error("sidecar down")),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      const result = await engine.assemble({
        sessionId: "test",
        messages: [{ role: "user", content: "hello" }],
      });

      expect(result.systemPromptAddition).toBeUndefined();
      expect(result.estimatedTokens).toBe(0);
      expect(result.messages).toHaveLength(1);
      expect(logger.warn).toHaveBeenCalled();
    });

    it("extracts prompt from array content blocks", async () => {
      const mockClient = {
        retrieve: vi.fn().mockResolvedValue({ unit_count: 1, rendered_prompt: "mem" }),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      await engine.assemble({
        sessionId: "test",
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: "Hello " },
              { type: "text", text: "World" },
            ],
          },
        ],
      });

      expect(mockClient.retrieve).toHaveBeenCalledWith("Hello \nWorld", "default");
    });

    it("returns empty when user content is empty/whitespace string", async () => {
      const mockClient = { retrieve: vi.fn() };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);
      const result = await engine.assemble({
        sessionId: "t",
        messages: [{ role: "user", content: "   " }],
      });

      expect(result.systemPromptAddition).toBeUndefined();
      expect(mockClient.retrieve).not.toHaveBeenCalled();
    });
  });

  describe("bootstrap", () => {
    it("succeeds when sidecar is healthy", async () => {
      const mockClient = { health: vi.fn().mockResolvedValue({ ok: true }) };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);

      await expect(engine.bootstrap()).resolves.toBeUndefined();
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("bootstrap ok"));
    });

    it("throws when sidecar is unhealthy", async () => {
      const mockClient = {
        health: vi.fn().mockRejectedValue(new Error("connection refused")),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);

      await expect(engine.bootstrap()).rejects.toThrow("bootstrap failed");
      expect(logger.error).toHaveBeenCalled();
    });
  });

  describe("compact", () => {
    it("consolidates memory and returns ok", async () => {
      const mockClient = { consolidate: vi.fn().mockResolvedValue({ ok: true }) };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);

      const result = await engine.compact!("session-123");
      expect(result.ok).toBe(true);
      expect(result.compacted).toBe(true);
      expect(mockClient.consolidate).toHaveBeenCalledWith("default");
    });

    it("returns failure on consolidate error", async () => {
      const mockClient = {
        consolidate: vi.fn().mockRejectedValue(new Error("timeout")),
      };
      const logger = makeLogger();
      const engine = createMetaClawContextEngine(() => mockClient as any, cfg, logger);

      const result = await engine.compact!("session-123");
      expect(result.ok).toBe(false);
      expect(result.compacted).toBe(false);
      expect(result.reason).toContain("timeout");
    });
  });

  describe("no-op lifecycle methods", () => {
    const mockClient = {} as any;
    const logger = makeLogger();
    const engine = createMetaClawContextEngine(() => mockClient, cfg, logger);

    it("ingest is a no-op", async () => {
      await expect(engine.ingest!([{ role: "user", content: "hi" }])).resolves.toBeUndefined();
    });

    it("ingestBatch is a no-op", async () => {
      await expect(engine.ingestBatch!([[{ role: "user", content: "hi" }]])).resolves.toBeUndefined();
    });

    it("afterTurn is a no-op", async () => {
      await expect(engine.afterTurn!({ ok: true })).resolves.toBeUndefined();
    });

    it("dispose is a no-op", async () => {
      await expect(engine.dispose()).resolves.toBeUndefined();
    });
  });
});
