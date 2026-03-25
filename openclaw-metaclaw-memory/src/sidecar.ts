import { spawn, type ChildProcess } from "node:child_process"
import { existsSync } from "node:fs"
import { resolve, dirname } from "node:path"
import { homedir } from "node:os"
import { fileURLToPath } from "node:url"
import type { PluginConfig } from "./types.js"

export class SidecarManager {
  private process: ChildProcess | null = null

  constructor(private config: PluginConfig) {}

  /**
   * Resolve the Python interpreter to use.
   * Prefers the venv created by `openclaw metaclaw setup`, falls back to config.
   */
  private resolvePython(): string {
    const venvPython = resolve(
      homedir(),
      ".openclaw", "plugins", "@metaclaw", "memory", ".venv", "bin", "python",
    )
    if (existsSync(venvPython)) return venvPython
    return this.config.pythonPath
  }

  async start(): Promise<void> {
    if (this.process) return

    const pluginDir = resolve(dirname(fileURLToPath(import.meta.url)), "..")
    const sidecarDir = resolve(pluginDir, "sidecar")
    const python = this.resolvePython()

    const args = [
      "-m", "metaclaw_memory_sidecar",
      "--port", String(this.config.sidecarPort),
      "--scope", this.config.scope,
      "--retrieval-mode", this.config.retrievalMode,
      "--memory-dir", this.config.memoryDir,
    ]

    this.process = spawn(python, args, {
      cwd: sidecarDir,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        PYTHONPATH: sidecarDir,
        METACLAW_SIDECAR_MAX_INJECTED_UNITS: String(this.config.maxInjectedUnits),
        METACLAW_SIDECAR_MAX_INJECTED_TOKENS: String(this.config.maxInjectedTokens),
        METACLAW_SIDECAR_AUTO_UPGRADE_ENABLED: this.config.autoUpgradeEnabled ? "1" : "0",
      },
    })

    this.process.on("exit", (code) => {
      if (code !== null && code !== 0) {
        console.error(`[metaclaw-memory] sidecar exited with code ${code}`)
      }
      this.process = null
    })

    this.process.stderr?.on("data", (chunk: Buffer) => {
      const msg = chunk.toString().trim()
      if (msg) console.error(`[metaclaw-memory] ${msg}`)
    })
  }

  async waitForReady(timeoutMs = 15_000): Promise<void> {
    const url = `http://127.0.0.1:${this.config.sidecarPort}/health`
    const deadline = Date.now() + timeoutMs
    const interval = 250

    while (Date.now() < deadline) {
      try {
        const res = await fetch(url)
        if (res.ok) return
      } catch {
        // sidecar not ready yet
      }
      await new Promise((r) => setTimeout(r, interval))
    }
    throw new Error(`Sidecar did not become ready within ${timeoutMs}ms`)
  }

  async stop(): Promise<void> {
    if (!this.process) return

    const proc = this.process
    this.process = null

    return new Promise((resolve) => {
      proc.on("exit", () => resolve())
      proc.kill("SIGTERM")

      // Force kill after 5 seconds
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill("SIGKILL")
        }
        resolve()
      }, 5_000)
    })
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed
  }
}
