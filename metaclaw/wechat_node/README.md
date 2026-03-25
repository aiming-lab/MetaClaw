# MetaClaw WeChat bridge

Uses [weixin-agent-sdk](https://github.com/wong2/weixin-agent-sdk) (install from npm) to connect a **personal WeChat** account to **MetaClaw**.

## Setup

**Run `npm install` in this directory** (`metaclaw/wechat_node` inside your MetaClaw clone), not the repository root.

From the repo root:

```bash
cd metaclaw/wechat_node
npm install
```

If you set `wechat.bridge_dir` in config, run `npm install` in **that** directory instead.

## Config

In `~/.metaclaw/config.yaml`:

```yaml
wechat:
  enabled: true
  # bridge_dir: ""   # optional: absolute path to a custom wechat_node copy (default: bundled metaclaw/wechat_node)
```

Apply config (or edit the YAML and save):

```bash
metaclaw config wechat.enabled true
```

### CLI commands

| Command | When to use |
|--------|-------------|
| **`metaclaw wechat-check`** | Run **first** if something fails. Prints config resolution, paths, whether `bridge.mjs` and `weixin-agent-sdk` exist, and whether `node` is on `PATH`. Exits non-zero if WeChat is not ready. |
| **`metaclaw start`** | Normal way to run MetaClaw **and** auto-start the WeChat bridge when `wechat.enabled` is true. Keep this terminal open; the bridge runs as a child process. |
| **`metaclaw wechat-bridge`** | Run **only the** Node bridge. Use when the MetaClaw proxy is **already** running (e.g. you started the stack another way) and you only need the WeChat process. Reuses a saved login when possible (see below). |
| **`metaclaw wechat-relogin`** | Same as `wechat-bridge`, but **forces a new QR login** for this run (switch account, expired token, or you want a clean login). Does **not** change `config.yaml`; after you stop, the next `metaclaw start` / `wechat-bridge` still prefers the **new** saved session. |

Optional: `-c /path/to/config.yaml` on any of these if your config is not the default `~/.metaclaw/config.yaml`.

### Running: QR, session reuse, relogin

1. **Start MetaClaw with WeChat enabled**  
   In a **foreground** terminal:

   ```bash
   metaclaw start
   ```

   Wait until the proxy is healthy; the launcher then starts `node bridge.mjs` when `wechat.enabled` is true.

2. **First login**  
   If there is **no** usable session yet, the bridge shows a **QR code** in the terminal. Scan it with WeChat to connect.

3. **Later runs**  
   Session data is stored under **`~/.openclaw/openclaw-weixin/`** (same layout as upstream **weixin-agent-sdk**). On the next `metaclaw start` or `metaclaw wechat-bridge`, the bridge **tries to resume** without showing QR.

4. **When to use `wechat-relogin`**  
   Use **`metaclaw wechat-relogin`** when you need to **scan again**: different WeChat account, token problems, or you cleared the state directory. The **MetaClaw proxy must already be listening** (e.g. another terminal ran `metaclaw start` first), because the bridge forwards chat to `http://127.0.0.1:<proxy.port>/v1`.

### Troubleshooting (`metaclaw wechat-check`)

Run:

```bash
metaclaw wechat-check
```

Interpret the output:

- **`wechat.enabled (resolved)`**  
  Must be **`True`** for `metaclaw start` to spawn the bridge. If **`False`**, enable with `metaclaw config wechat.enabled true` (or set `wechat.enabled: true` in YAML). If you set `wechat.enabled` in YAML but this still shows `False`, check for typos or a wrong config file path (`-c`).

- **`bridge_dir`**  
  Shows which directory MetaClaw uses for the bridge (bundled `metaclaw/wechat_node` or your `wechat.bridge_dir`).

- **`bridge.mjs exists`**  
  Must be **`True`**. If **`False`**, you are pointing `wechat.bridge_dir` at the wrong folder, or the install is incomplete.

- **`weixin-agent-sdk installed`**  
  Must be **`True`** (folder `node_modules/weixin-agent-sdk` present). If **`False`**, run **`npm install`** in that `bridge_dir` (see [Setup](#setup)).

- **`node on PATH`**  
  Must show a real path to the `node` binary, not `(not found)`. Install **Node.js** (≥ 22 per SDK) and ensure `node` is on your `PATH`.

The command exits **0** only when WeChat is enabled **and** dependencies look OK **and** `node` is found. Otherwise fix the reported lines and run `wechat-check` again before retrying `metaclaw start`.

## Locale

`bridge.mjs` translates common **weixin-agent-sdk** login strings to **English** (the SDK defaults to Chinese). Deep errors from the SDK may still be Chinese.

## Limitations

Non-official SDK; behavior may change. See upstream [weixin-agent-sdk](https://github.com/wong2/weixin-agent-sdk) on GitHub.
