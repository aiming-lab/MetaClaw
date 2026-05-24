import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../hooks/auto-recall.js", () => ({
  registerAutoRecall: vi.fn(),
}));
vi.mock("../hooks/auto-capture.js", () => ({
  registerAutoCapture: vi.fn(),
}));
vi.mock("../tools/memory-search.js", () => ({
  registerMemorySearchTool: vi.fn(),
}));
vi.mock("../tools/memory-store.js", () => ({
  registerMemoryStoreTool: vi.fn(),
}));
vi.mock("../tools/memory-forget.js", () => ({
  registerMemoryForgetTool: vi.fn(),
}));
vi.mock("../tools/memory-status.js", () => ({
  registerMemoryStatusTool: vi.fn(),
}));
vi.mock("../commands/cli.js", () => ({
  registerCli: vi.fn(),
}));
vi.mock("../commands/slash.js", () => ({
  registerSlashCommands: vi.fn(),
}));
vi.mock("../sidecar.js", () => ({
  SidecarManager: vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    waitForReady: vi.fn(),
    stop: vi.fn(),
  })),
}));
vi.mock("../client.js", () => ({
  SidecarClient: vi.fn().mockImplementation(() => ({})),
}));
vi.mock("../config-schema.js", () => ({
  configSchema: {},
}));
vi.mock("../types.js", () => ({
  parseConfig: (cfg: any) => ({ sidecarPort: 19823, scope: "default", ...cfg }),
}));

import plugin from "../index.js";
import { registerAutoRecall } from "../hooks/auto-recall.js";
import { registerAutoCapture } from "../hooks/auto-capture.js";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    pluginConfig: {},
    registerService: vi.fn(),
    logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
    on: vi.fn(),
    ...overrides,
  };
}

describe("plugin index.ts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exports dual kind", () => {
    expect(plugin.kind).toEqual(["memory", "context-engine"]);
  });

  it("has correct id and name", () => {
    expect(plugin.id).toBe("metaclaw-memory");
    expect(plugin.name).toBe("MetaClaw Memory");
  });

  it("registers context-engine when API available", () => {
    const mockRegisterCE = vi.fn();
    const api = makeApi({ registerContextEngine: mockRegisterCE });

    plugin.register(api);

    expect(mockRegisterCE).toHaveBeenCalledWith("metaclaw-memory", expect.any(Function));
  });

  it("skips auto-recall when context-engine is registered (intra-plugin guard)", () => {
    const api = makeApi({ registerContextEngine: vi.fn() });

    plugin.register(api);

    expect(registerAutoRecall).not.toHaveBeenCalled();
    expect(registerAutoCapture).toHaveBeenCalled();
  });

  it("falls back to auto-recall when context-engine API not available", () => {
    const api = makeApi();

    plugin.register(api);

    expect(registerAutoRecall).toHaveBeenCalled();
    expect(registerAutoCapture).toHaveBeenCalled();
  });

  it("registers a service for sidecar lifecycle", () => {
    const api = makeApi();
    plugin.register(api);
    expect(api.registerService).toHaveBeenCalledWith(
      expect.objectContaining({ id: "metaclaw-memory" }),
    );
  });
});
