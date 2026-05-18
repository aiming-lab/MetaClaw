/**
 * MetaClaw OpenClaw extension:
 *   1. Inject X-Session-Id / X-Turn-Type on LLM fetch
 *   2. Create a Python venv, run `pip install`, and optionally `metaclaw start`
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

/** Directory where this plugin lives — the .venv is created here. */
const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));

/** Guard: prevent register() from running install logic more than once per process. */
let _registered = false;

type MetaClawPluginConfig = {
  sessionIdHeader: string;
  turnTypeHeader: string;
  /** When true: venv + pip + optional default config + `metaclaw start`. When false (default): venv + pip only unless overridden. */
  oneClickMetaclaw: boolean;
  /** Run `pip install <pipInstallSpec>` in the venv when the plugin loads. */
  autoInstallMetaclaw: boolean;
  /** System Python used to create the venv (e.g. `python3`, `python3.12`). Not used after venv creation. */
  pipPython: string;
  /** Passed to pip install. Default is full `[rl,evolve,scheduler]` from GitHub zip (HTTPS; no git CLI). */
  pipInstallSpec: string;
  /** Additional pip install flags. */
  pipExtraArgs: string[];
  autoStartMetaclaw: boolean;
  /** Executable or interpreter path for metaclaw. Default: venv Python. */
  metaclawCommand: string;
  /** Args after command. Default: `-m metaclaw start` when using venv Python. */
  metaclawStartArgs: string[];
  /** If ~/.metaclaw/config.yaml is missing, write MetaClaw defaults (non-interactive). Default false unless oneClickMetaclaw. */
  bootstrapMetaclawConfig: boolean;
  /** Path to the venv directory. Default: `.venv` inside the plugin directory. */
  venvPath: string;
};

/** Resolve the Python binary inside a venv (cross-platform). */
function venvPython(venvDir: string): string {
  return process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");
}

/** Minimum Python version required by aiming-metaclaw. */
const MIN_PYTHON: [number, number] = [3, 10];

/**
 * Auto-detect a suitable Python >= 3.10.
 * Tries: python3.12 → python3.11 → python3.10 → python3.
 * Returns the first one that satisfies the minimum version, or "python3" as last resort.
 */
function findSuitablePython(): string {
  const candidates = ["python3.12", "python3.11", "python3.10", "python3"];

  for (const cmd of candidates) {
    try {
      const r = spawnSync(cmd, ["-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"], {
        encoding: "utf8",
        timeout: 5_000,
        stdio: ["ignore", "pipe", "pipe"],
      });
      if (r.status !== 0 || !r.stdout) continue;
      const parts = r.stdout.trim().split(" ").map(Number);
      if (parts.length === 2 && (parts[0] > MIN_PYTHON[0] || (parts[0] === MIN_PYTHON[0] && parts[1] >= MIN_PYTHON[1]))) {
        return cmd;
      }
    } catch {
      // not found — try next
    }
  }

  return "python3";
}

function resolveConfig(api: OpenClawPluginApi): MetaClawPluginConfig {
  const cfg = (api.pluginConfig ?? {}) as Partial<MetaClawPluginConfig>;
  const oneClick = cfg.oneClickMetaclaw ?? false;
  const pipPy = cfg.pipPython ?? findSuitablePython();
  const venvDir = cfg.venvPath ?? path.join(PLUGIN_DIR, ".metaclaw");
  const venvPy = venvPython(venvDir);

  const explicitCmd = cfg.metaclawCommand?.trim();
  const hasCustomStartArgs = Array.isArray(cfg.metaclawStartArgs) && cfg.metaclawStartArgs.length > 0;

  let metaclawCommand: string;
  let metaclawStartArgs: string[];
  if (hasCustomStartArgs) {
    metaclawCommand = explicitCmd ?? venvPy;
    metaclawStartArgs = cfg.metaclawStartArgs as string[];
  } else if (explicitCmd) {
    metaclawCommand = explicitCmd;
    metaclawStartArgs = ["start"];
  } else {
    // Default: use the venv Python to run metaclaw
    metaclawCommand = venvPy;
    metaclawStartArgs = ["-m", "metaclaw", "start"];
  }

  const autoInstallMetaclaw = oneClick ? true : (cfg.autoInstallMetaclaw ?? true);
  const autoStartMetaclaw = oneClick ? true : (cfg.autoStartMetaclaw ?? false);
  const bootstrapMetaclawConfig = oneClick ? true : (cfg.bootstrapMetaclawConfig ?? false);

  return {
    sessionIdHeader: cfg.sessionIdHeader ?? "X-Session-Id",
    turnTypeHeader: cfg.turnTypeHeader ?? "X-Turn-Type",
    oneClickMetaclaw: oneClick,
    autoInstallMetaclaw,
    pipPython: pipPy,
    pipInstallSpec:
      cfg.pipInstallSpec ??
      "aiming-metaclaw[rl,evolve,scheduler]",
    pipExtraArgs: Array.isArray(cfg.pipExtraArgs) ? cfg.pipExtraArgs : [],
    autoStartMetaclaw,
    metaclawCommand,
    metaclawStartArgs,
    bootstrapMetaclawConfig,
    venvPath: venvDir,
  };
}

const SIDE_TRIGGERS = new Set(["heartbeat", "memory", "cron"]);

function patchFetchForTrainingHeaders(
  api: OpenClawPluginApi,
  config: Pick<MetaClawPluginConfig, "sessionIdHeader" | "turnTypeHeader">,
): void {
  let pendingHeaders: Record<string, string> | null = null;
  const originalFetch = globalThis.fetch;

  globalThis.fetch = function metaclawPatchedFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    if (pendingHeaders && init?.method?.toUpperCase() === "POST") {
      const extra = pendingHeaders;
      const merged = new Headers(init.headers);
      for (const [k, v] of Object.entries(extra)) {
        if (!merged.has(k)) {
          merged.set(k, v);
        }
      }
      return originalFetch.call(globalThis, input, { ...init, headers: merged });
    }
    return originalFetch.call(globalThis, input, init);
  } as typeof globalThis.fetch;

  api.on("before_prompt_build", (_event, ctx) => {
    const sessionId = ctx.sessionId ?? "";
    const turnType = SIDE_TRIGGERS.has(ctx.trigger ?? "") ? "side" : "main";
    pendingHeaders = {
      [config.sessionIdHeader]: sessionId,
      [config.turnTypeHeader]: turnType,
    };
    return {};
  });

  api.on("agent_end", () => {
    pendingHeaders = null;
  });
}

/**
 * Ensure pip is available inside the venv. On some systems (macOS, minimal installs),
 * `python3 -m venv` creates a venv without pip. This runs `ensurepip` to fix that.
 */
function ensurePipInVenv(api: OpenClawPluginApi, venvPy: string): void {
  // Quick check: can we import pip?
  const check = spawnSync(venvPy, ["-c", "import pip"], {
    encoding: "utf8",
    timeout: 15_000,
  });
  if (check.status === 0) {
    return; // pip already available
  }

  api.logger.info("metaclaw-openclaw: pip not found in venv, running ensurepip…");
  const result = spawnSync(venvPy, ["-m", "ensurepip", "--upgrade"], {
    encoding: "utf8",
    timeout: 60_000,
  });
  if (result.error || result.status !== 0) {
    api.logger.warn(
      `metaclaw-openclaw: ensurepip failed (${(result.stderr ?? String(result.error)).slice(0, 500)}). ` +
      `Try manually: ${venvPy} -m ensurepip --upgrade`,
    );
  } else {
    api.logger.debug?.("metaclaw-openclaw: pip installed via ensurepip");
  }
}

/**
 * Create a Python virtual environment if it does not already exist.
 * Uses the system `pipPython` to create the venv, then all subsequent
 * operations use the venv's own Python.
 * Returns the path to the venv's Python binary, or null on failure.
 */
function ensureVenv(api: OpenClawPluginApi, full: MetaClawPluginConfig): string | null {
  const venvDir = full.venvPath;
  const venvPy = venvPython(venvDir);

  // Already exists — verify the python binary is there and pip is available
  if (fs.existsSync(venvPy)) {
    api.logger.debug?.(`metaclaw-openclaw: venv exists at ${venvDir}`);
    ensurePipInVenv(api, venvPy);
    return venvPy;
  }

  api.logger.info(
    `metaclaw-openclaw: creating venv at ${venvDir} using ${full.pipPython}…`,
  );

  // Try creating the venv with pip included
  const result = spawnSync(full.pipPython, ["-m", "venv", "--upgrade-deps", venvDir], {
    encoding: "utf8",
    timeout: 120_000,
  });

  if (result.error) {
    api.logger.warn(
      `metaclaw-openclaw: failed to create venv (${String(result.error)}). ` +
      `On Debian/Ubuntu, run: apt install python3-venv. ` +
      `Or set autoInstallMetaclaw: false and manage MetaClaw yourself.`,
    );
    return null;
  }

  // If --upgrade-deps failed, retry without it (older Python may not support it)
  if (result.status !== 0) {
    api.logger.info("metaclaw-openclaw: retrying venv creation without --upgrade-deps…");
    const retry = spawnSync(full.pipPython, ["-m", "venv", venvDir], {
      encoding: "utf8",
      timeout: 120_000,
    });
    if (retry.error || retry.status !== 0) {
      const stderr = (retry.stderr ?? result.stderr ?? "").slice(0, 1500);
      api.logger.warn(
        `metaclaw-openclaw: venv creation failed. stderr:\n${stderr}`,
      );
      return null;
    }
  }

  if (!fs.existsSync(venvPy)) {
    api.logger.warn(
      `metaclaw-openclaw: venv created but Python binary not found at ${venvPy}`,
    );
    return null;
  }

  // Ensure pip is installed inside the venv
  ensurePipInVenv(api, venvPy);

  api.logger.info(`metaclaw-openclaw: venv created successfully at ${venvDir}`);
  return venvPy;
}

/** Writes ~/.metaclaw/config.yaml using MetaClaw's defaults if missing (interactive `metaclaw setup` is not runnable here). */
function ensureMetaclawDefaultConfig(api: OpenClawPluginApi, pythonBin: string): void {
  const configPath = path.join(os.homedir(), ".metaclaw", "config.yaml");
  if (fs.existsSync(configPath)) {
    return;
  }
  const script =
    "from metaclaw.config_store import ConfigStore; cs=ConfigStore(); " +
    "cs.save(cs.load()) if not cs.exists() else None";
  const result = spawnSync(pythonBin, ["-c", script], {
    encoding: "utf8",
    timeout: 60_000,
  });
  if (result.error) {
    api.logger.warn(
      `metaclaw-openclaw: could not run Python for config bootstrap (${String(result.error)})`,
    );
    return;
  }
  if (result.status !== 0) {
    api.logger.warn(
      `metaclaw-openclaw: could not write default ~/.metaclaw/config.yaml: ${(result.stderr ?? result.stdout ?? "").slice(0, 1500)}`,
    );
    return;
  }
  api.logger.debug?.(
    "metaclaw-openclaw: wrote default config.yaml",
  );
}

function trySpawnMetaclaw(api: OpenClawPluginApi, full: MetaClawPluginConfig, venvPy: string): void {
  if (!full.autoStartMetaclaw) {
    return;
  }
  if (full.bootstrapMetaclawConfig) {
    ensureMetaclawDefaultConfig(api, venvPy);
  }

  // Use venv Python for metaclaw unless user set a custom command
  const cmd = full.metaclawCommand;
  const args = full.metaclawStartArgs;

  try {
    const child = spawn(cmd, args, {
      detached: true,
      stdio: "ignore",
      shell: process.platform === "win32",
    });
    child.on("error", (err) => {
      api.logger.warn(`metaclaw-openclaw: spawn MetaClaw failed (${String(err)}).`);
    });
    child.unref();
    api.logger.debug?.(
      `metaclaw-openclaw: started MetaClaw (pid=${child.pid ?? "?"})`,
    );
  } catch (err) {
    api.logger.warn(
      `metaclaw-openclaw: autoStartMetaclaw failed (${String(err)}). Run metaclaw setup; check venv or metaclawCommand.`,
    );
  }
}

/**
 * After pip install, create a wrapper script so users can run `metaclaw` directly.
 *
 * Strategy (in order of preference):
 *   1. /usr/local/bin  — already on PATH everywhere, works immediately (no new terminal needed)
 *   2. ~/.local/bin    — fallback; add to shell rc files so it works after opening a new terminal
 *   3. Windows         — ~/.local/bin + add to user PATH via registry
 */
function installMetaclawWrapper(api: OpenClawPluginApi, venvDir: string): void {
  const venvPy = venvPython(venvDir);

  const script = process.platform === "win32"
    ? `@echo off\r\n"${venvPy}" -m metaclaw %*\r\n`
    : `#!/usr/bin/env bash\nexec "${venvPy}" -m metaclaw "$@"\n`;

  const ext = process.platform === "win32" ? ".cmd" : "";

  // --- Try /usr/local/bin first (macOS / Linux) ---
  if (process.platform !== "win32") {
    const globalBin = "/usr/local/bin";
    const globalWrapper = path.join(globalBin, "metaclaw");
    try {
      fs.writeFileSync(globalWrapper, script, { mode: 0o755 });
      api.logger.debug?.(
        `metaclaw-openclaw: wrapper at ${globalWrapper}`,
      );
      return; // done — no PATH changes needed
    } catch {
      // Permission denied — fall through to ~/.local/bin
      api.logger.debug?.(
        "metaclaw-openclaw: /usr/local/bin not writable, falling back to ~/.local/bin",
      );
    }
  }

  // --- Fallback: ~/.local/bin ---
  const localBin = path.join(os.homedir(), ".local", "bin");
  const localWrapper = path.join(localBin, "metaclaw" + ext);

  try {
    fs.mkdirSync(localBin, { recursive: true });
    fs.writeFileSync(localWrapper, script, { mode: 0o755 });
    api.logger.debug?.(`metaclaw-openclaw: wrapper at ${localWrapper}`);
  } catch (err) {
    api.logger.warn(
      `metaclaw-openclaw: could not create wrapper (${String(err)}). ` +
      `You can still run: ${venvPy} -m metaclaw <command>`,
    );
    return;
  }

  // --- Ensure ~/.local/bin is on PATH ---
  if (process.platform === "win32") {
    // Windows: add to user PATH via registry
    const result = spawnSync("powershell", [
      "-NoProfile", "-Command",
      `$p = [Environment]::GetEnvironmentVariable('Path','User');` +
      `if ($p -notlike '*${localBin}*') {` +
      `[Environment]::SetEnvironmentVariable('Path', '${localBin};' + $p, 'User')` +
      `}`,
    ], { encoding: "utf8", timeout: 15_000 });
    if (result.status === 0) {
      api.logger.debug?.("metaclaw-openclaw: added ~/.local/bin to Windows user PATH");
    }
  } else {
    // macOS / Linux: append to shell rc files
    const home = os.homedir();
    const exportLine = 'export PATH="$HOME/.local/bin:$PATH"';
    const rcFiles: string[] = [];
    const shell = process.env.SHELL ?? "";
    if (shell.endsWith("/zsh") || process.platform === "darwin") {
      rcFiles.push(path.join(home, ".zshrc"));
    }
    if (shell.endsWith("/bash") || process.platform === "linux") {
      rcFiles.push(path.join(home, ".bashrc"));
    }
    if (process.platform === "darwin") {
      rcFiles.push(path.join(home, ".bash_profile"));
    }
    for (const rcFile of rcFiles) {
      try {
        const content = fs.existsSync(rcFile) ? fs.readFileSync(rcFile, "utf8") : "";
        if (content.includes(".local/bin")) continue;
        fs.appendFileSync(rcFile, `\n# Added by MetaClaw plugin\n${exportLine}\n`);
        api.logger.debug?.(`metaclaw-openclaw: added ~/.local/bin to PATH in ${rcFile}`);
      } catch {
        // Non-fatal
      }
    }
  }

  api.logger.debug?.(
    "metaclaw-openclaw: metaclaw command ready",
  );
}

/**
 * Default flow: create venv → pip install inside venv → create wrapper → optionally start metaclaw.
 * The venv isolates MetaClaw from the system Python — no --user, no --break-system-packages needed.
 */
function runVenvSetupThenMaybeStart(api: OpenClawPluginApi, full: MetaClawPluginConfig): void {
  if (!full.autoInstallMetaclaw) {
    // Even without auto-install, if autoStart is on, try to use existing venv
    const venvPy = venvPython(full.venvPath);
    if (fs.existsSync(venvPy)) {
      trySpawnMetaclaw(api, full, venvPy);
    } else {
      trySpawnMetaclaw(api, full, full.pipPython);
    }
    return;
  }

  // Step 1: ensure venv exists
  const venvPy = ensureVenv(api, full);
  if (!venvPy) {
    api.logger.warn(
      "metaclaw-openclaw: venv creation failed — skipping pip install. Install MetaClaw manually.",
    );
    return;
  }

  // Step 2: check if metaclaw is already installed and up-to-date
  const versionCheck = spawnSync(venvPy, [
    "-c",
    "import metaclaw; print(getattr(metaclaw, '__version__', '0.0.0'))",
  ], { encoding: "utf8", timeout: 10_000 });

  const installedVersion = versionCheck.status === 0 ? versionCheck.stdout.trim() : null;

  // Already installed — run post-install steps
  api.logger.debug?.(`metaclaw-openclaw: metaclaw already installed`);
  installMetaclawWrapper(api, full.venvPath);
  if (full.autoStartMetaclaw) {
    trySpawnMetaclaw(api, full, venvPy);
  }
  return;

}

// ─── WeChat ──────────────────────────────────────────────────────────
// WeChat channel plugin (openclaw-weixin) is NOT auto-installed here.
// It is installed on-demand when the user enables WeChat via:
//   metaclaw config wechat.enabled true && metaclaw start
// See metaclaw/launcher.py → _ensure_openclaw_weixin_plugin()

/**
 * Ensure this plugin is trusted in OpenClaw config:
 * - plugins.allow: authorizes the plugin id
 * - plugins.load.paths: declares the load path (establishes provenance)
 * Both are needed to suppress the "loaded without install/load-path provenance" warning.
 */
function ensurePluginsTrusted(): void {
  const configPath = path.join(os.homedir(), ".openclaw", "openclaw.json");
  try {
    const raw = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : "{}";
    const cfg = JSON.parse(raw);
    if (!cfg.plugins) cfg.plugins = {};

    let changed = false;

    // plugins.allow
    const allow: string[] = cfg.plugins.allow ?? [];
    if (!allow.includes("metaclaw-openclaw")) {
      cfg.plugins.allow = [...allow, "metaclaw-openclaw"];
      changed = true;
    }

    // plugins.load.paths — declare plugin directory for provenance
    if (!cfg.plugins.load) cfg.plugins.load = {};
    const loadPaths: string[] = cfg.plugins.load.paths ?? [];
    if (!loadPaths.some((p: string) => p.includes("metaclaw-openclaw"))) {
      cfg.plugins.load.paths = [...loadPaths, PLUGIN_DIR];
      changed = true;
    }

    if (changed) {
      fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2) + "\n");
    }
  } catch {
    // non-fatal
  }
}

export default function register(api: OpenClawPluginApi): void {
  ensurePluginsTrusted();
  const full = resolveConfig(api);
  patchFetchForTrainingHeaders(api, full);

  // Prevent duplicate install when register() is called multiple times per process
  if (_registered) return;
  _registered = true;

  // NOTE: WeChat channel plugin (openclaw-weixin) is installed on-demand by
  // `metaclaw start` when wechat.enabled is true in ~/.metaclaw/config.yaml.

  runVenvSetupThenMaybeStart(api, full);

  if (!full.autoInstallMetaclaw && !full.autoStartMetaclaw && !full.oneClickMetaclaw) {
    api.logger.debug?.(
      "metaclaw-openclaw: session/turn headers only",
    );
  } else if (full.oneClickMetaclaw || full.autoStartMetaclaw) {
    api.logger.debug?.(
      "metaclaw-openclaw: one-click mode",
    );
  } else {
    api.logger.debug?.(
      "metaclaw-openclaw: venv + pip install",
    );
  }
}
