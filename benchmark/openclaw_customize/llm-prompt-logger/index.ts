import * as fs from "node:fs";
import * as path from "node:path";
import type { OpenClawPluginApi } from "~/openclaw/src/plugins/types.js";

const DEFAULT_LOG_DIR = "/home/xkaiwen/workspace/log_cache/llm_prompts";

type PendingInput = {
  timestamp: string;
  runId: string;
  sessionId: string;
  provider: string;
  model: string;
  imagesCount: number;
  agentId?: string;
  sessionKey?: string;
  workspaceDir?: string;
  systemPrompt?: string;
  prompt: string;
  historyMessages: unknown[];
};

export default function register(api: OpenClawPluginApi) {
  const config = api.pluginConfig as {
    logDir?: string;
    enableLlmInput?: boolean;
    enableLlmOutput?: boolean;
    enableAgentEnd?: boolean;
  } | undefined;
  const logDir = config?.logDir || DEFAULT_LOG_DIR;
  const enableLlmInput = config?.enableLlmInput !== false;
  const enableLlmOutput = config?.enableLlmOutput !== false;
  const enableAgentEnd = config?.enableAgentEnd !== false;

  // Buffer llm_input data keyed by runId, so llm_output can merge into it
  const pendingInputs = new Map<string, PendingInput>();

  function ensureDir(dir: string): boolean {
    try {
      fs.mkdirSync(dir, { recursive: true });
      return true;
    } catch {
      return false;
    }
  }

  function writeJson(filePath: string, data: unknown): void {
    try {
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
    } catch {
      // silently ignore
    }
  }

  function makeTimestamp(): string {
    return new Date().toISOString().replace(/[:.]/g, "-");
  }

  // ── llm_input: capture request data ──
  api.on("llm_input", (event, ctx) => {
    if (!enableLlmInput) return;

    const inputData: PendingInput = {
      timestamp: new Date().toISOString(),
      runId: event.runId,
      sessionId: event.sessionId,
      provider: event.provider,
      model: event.model,
      imagesCount: event.imagesCount,
      agentId: ctx.agentId,
      sessionKey: ctx.sessionKey,
      workspaceDir: ctx.workspaceDir,
      systemPrompt: event.systemPrompt,
      prompt: event.prompt,
      historyMessages: event.historyMessages,
    };

    // Always buffer for llm_output to merge
    pendingInputs.set(event.runId, inputData);

    if (!enableLlmInput) return;

    // Write input-only file immediately (in case llm_output never fires)
    const sessionId = event.sessionId || ctx.sessionId || "unknown-session";
    const sessionDir = path.join(logDir, sessionId);
    if (!ensureDir(sessionDir)) return;

    const fileName = `${makeTimestamp()}_${event.runId || "no-run-id"}_input.json`;
    writeJson(path.join(sessionDir, fileName), {
      stage: "llm_input",
      ...inputData,
    });
  });

  // ── llm_output: merge with buffered input, write combined record ──
  api.on("llm_output", (event, ctx) => {
    const inputData = pendingInputs.get(event.runId);
    pendingInputs.delete(event.runId);

    if (!enableLlmOutput) return;

    const sessionId = event.sessionId || ctx.sessionId || "unknown-session";
    const sessionDir = path.join(logDir, sessionId);
    if (!ensureDir(sessionDir)) return;

    const combined = {
      stage: "llm_round" as const,
      timestamp: new Date().toISOString(),
      // metadata
      runId: event.runId,
      sessionId: event.sessionId,
      provider: event.provider,
      model: event.model,
      agentId: ctx.agentId,
      sessionKey: ctx.sessionKey,
      workspaceDir: ctx.workspaceDir,
      // input (from buffered llm_input)
      input: inputData
        ? {
            systemPrompt: inputData.systemPrompt,
            prompt: inputData.prompt,
            historyMessages: inputData.historyMessages,
            imagesCount: inputData.imagesCount,
            capturedAt: inputData.timestamp,
          }
        : null,
      // output (from llm_output)
      output: {
        assistantTexts: event.assistantTexts,
        lastAssistant: event.lastAssistant,
        usage: event.usage,
      },
    };

    const fileName = `${makeTimestamp()}_${event.runId || "no-run-id"}_round.json`;
    writeJson(path.join(sessionDir, fileName), combined);
  });

  // ── agent_end: full turn summary with complete message snapshot ──
  api.on("agent_end", (event, ctx) => {
    pendingInputs.clear();

    if (!enableAgentEnd) return;

    const sessionId = ctx.sessionId || "unknown-session";
    const sessionDir = path.join(logDir, sessionId);
    if (!ensureDir(sessionDir)) return;

    const summary = {
      stage: "agent_end" as const,
      timestamp: new Date().toISOString(),
      agentId: ctx.agentId,
      sessionId: ctx.sessionId,
      sessionKey: ctx.sessionKey,
      workspaceDir: ctx.workspaceDir,
      success: event.success,
      error: event.error,
      durationMs: event.durationMs,
      messageCount: event.messages.length,
      messages: event.messages,
    };

    const fileName = `${makeTimestamp()}_agent-end.json`;
    writeJson(path.join(sessionDir, fileName), summary);
  });
}
