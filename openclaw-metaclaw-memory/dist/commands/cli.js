import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, unlinkSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
/**
 * Register CLI commands under `openclaw metaclaw <subcommand>`.
 */
export function registerCli(api, getClient, config) {
    api.registerCli(({ program }) => {
        const cmd = program.command("metaclaw").description("MetaClaw Memory commands");
        // --- setup ---
        cmd
            .command("setup")
            .description("Set up the Python sidecar (venv + dependencies)")
            .action(async () => {
            const python = config.pythonPath;
            // Check Python version
            try {
                const version = execSync(`${python} --version`, {
                    encoding: "utf-8",
                }).trim();
                const match = version.match(/Python (\d+)\.(\d+)/);
                if (!match) {
                    console.error(`Could not parse Python version: ${version}`);
                    return;
                }
                const major = parseInt(match[1], 10);
                const minor = parseInt(match[2], 10);
                if (major < 3 || (major === 3 && minor < 10)) {
                    console.error(`Python 3.10+ required, found ${version}`);
                    return;
                }
                console.log(`Found ${version}`);
            }
            catch {
                console.error(`Python not found at '${python}'. Set pythonPath in plugin config.`);
                return;
            }
            // Create venv
            const venvDir = resolve(homedir(), ".openclaw", "plugins", "@metaclaw", "memory", ".venv");
            if (!existsSync(venvDir)) {
                mkdirSync(resolve(venvDir, ".."), { recursive: true });
                console.log(`Creating virtual environment at ${venvDir} ...`);
                execSync(`${python} -m venv "${venvDir}"`, { stdio: "inherit" });
            }
            else {
                console.log(`Virtual environment already exists at ${venvDir}`);
            }
            // Install sidecar package from the bundled sidecar/ directory
            const pip = resolve(venvDir, "bin", "pip");
            const pluginDir = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
            const sidecarPkgDir = resolve(pluginDir, "sidecar");
            console.log("Installing metaclaw-memory-sidecar from local bundle ...");
            execSync(`"${pip}" install --upgrade "${sidecarPkgDir}"`, {
                stdio: "inherit",
            });
            // Init memory directory
            const memoryDir = config.memoryDir.replace(/^~/, homedir());
            if (!existsSync(memoryDir)) {
                mkdirSync(memoryDir, { recursive: true });
                console.log(`Created memory directory: ${memoryDir}`);
            }
            console.log("Setup complete. Database will be initialized on first sidecar start.");
        });
        // --- status ---
        cmd
            .command("status")
            .description("Show memory system health and statistics")
            .action(async () => {
            try {
                const client = getClient();
                const [health, stats] = await Promise.all([
                    client.health(),
                    client.stats(),
                ]);
                console.log("Memory System Status");
                console.log(`  Status:   ${health.status}`);
                console.log(`  Scope:    ${health.scope}`);
                console.log(`  Memories: ${health.memories}`);
                console.log();
                const entries = Object.entries(stats);
                if (entries.length > 0) {
                    console.log("Statistics:");
                    for (const [key, value] of entries) {
                        console.log(`  ${key}: ${value}`);
                    }
                }
            }
            catch {
                console.error("Could not reach sidecar. Is it running? Try: openclaw metaclaw setup");
            }
        });
        // --- search ---
        cmd
            .command("search <query>")
            .description("Search memories by query")
            .option("-l, --limit <n>", "Max results", "10")
            .action(async (query, opts) => {
            try {
                const client = getClient();
                const results = await client.search(query, config.scope, parseInt(opts.limit, 10));
                if (results.length === 0) {
                    console.log("No memories found.");
                    return;
                }
                console.log(`Found ${results.length} result(s):\n`);
                for (const [i, r] of results.entries()) {
                    console.log(`[${i + 1}] ${r.unit.summary || r.unit.content.slice(0, 120)}`);
                    console.log(`    id: ${r.unit.memory_id}  type: ${r.unit.memory_type}  score: ${r.score.toFixed(3)}`);
                    console.log(`    tags: ${r.unit.tags.join(", ") || "none"}`);
                    if (r.reason)
                        console.log(`    reason: ${r.reason}`);
                    console.log();
                }
            }
            catch {
                console.error("Search failed. Is the sidecar running?");
            }
        });
        // --- wipe ---
        cmd
            .command("wipe")
            .description("Delete all memories (irreversible)")
            .option("-y, --yes", "Skip confirmation")
            .action(async (opts) => {
            const memoryDir = config.memoryDir.replace(/^~/, homedir());
            if (!existsSync(memoryDir)) {
                console.log("No memory directory found. Nothing to wipe.");
                return;
            }
            if (!opts.yes) {
                console.log(`This will permanently delete all memory data in ${memoryDir}.`);
                console.log("Re-run with --yes to confirm.");
                return;
            }
            const files = readdirSync(memoryDir);
            let removed = 0;
            for (const file of files) {
                if (file.endsWith(".db") ||
                    file.endsWith(".db-journal") ||
                    file.endsWith(".db-wal") ||
                    file.endsWith(".db-shm")) {
                    unlinkSync(resolve(memoryDir, file));
                    removed++;
                }
            }
            console.log(`Wiped ${removed} database file(s) from ${memoryDir}.`);
        });
        // --- upgrade ---
        cmd
            .command("upgrade")
            .description("Trigger a memory self-upgrade cycle")
            .action(async () => {
            try {
                const client = getClient();
                console.log("Triggering upgrade cycle ...");
                await client.upgradeTrigger();
                console.log("Upgrade started. Polling for completion ...");
                const maxPolls = 60;
                const pollInterval = 2_000;
                for (let i = 0; i < maxPolls; i++) {
                    await new Promise((r) => setTimeout(r, pollInterval));
                    const status = await client.upgradeStatus();
                    if (status.state === "idle" ||
                        status.state === "complete") {
                        console.log(`Upgrade complete. Last cycle: ${status.last_cycle ?? "unknown"}`);
                        return;
                    }
                    if (status.state === "error") {
                        console.error("Upgrade cycle ended with an error.");
                        return;
                    }
                    if (i % 5 === 4) {
                        console.log(`  still running (state: ${status.state}) ...`);
                    }
                }
                console.log("Timed out waiting for upgrade. Check 'openclaw metaclaw status' later.");
            }
            catch {
                console.error("Upgrade failed. Is the sidecar running?");
            }
        });
    }, { commands: ["metaclaw"] });
}
//# sourceMappingURL=cli.js.map