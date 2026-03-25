/**
 * MetaClaw WeChat bridge: login with QR, forward each chat to the local MetaClaw proxy.
 *
 * Env:
 *   METACLAW_OPENAI_BASE, METACLAW_MODEL, METACLAW_API_KEY
 *   METACLAW_WECHAT_FORCE_LOGIN=1 — internal: metaclaw wechat-relogin sets this for one run only
 *   OPENCLAW_STATE_DIR / CLAWDBOT_STATE_DIR — weixin-agent-sdk state (default ~/.openclaw)
 */
import { login, start } from "weixin-agent-sdk";

/** weixin-agent-sdk Chinese strings → English (longer phrases first after sort). */
const ZH_EN_PAIRS = [
  ["\n使用微信扫描以下二维码，以完成连接：\n", "\nScan the QR code below with WeChat to connect:\n"],
  ["\n等待扫码...\n", "\nWaiting for scan...\n"],
  ["\n✅ 与微信连接成功！", "\n✅ Connected to WeChat!"],
  ["\n👀 已扫码，在微信继续操作...\n", "\n👀 Scanned — continue in WeChat...\n"],
  ["正在启动微信扫码登录...", "Starting WeChat QR login..."],
  ["使用微信扫描以下二维码，以完成连接：", "Scan the QR code below with WeChat to connect:"],
  ["等待扫码...", "Waiting for scan..."],
  ["✅ 与微信连接成功！", "✅ Connected to WeChat!"],
  ["二维码链接:", "QR code URL:"],
  ["二维码已过期，正在刷新", "QR code expired, refreshing"],
  ["🔄 新二维码已生成，请重新扫描", "🔄 New QR code generated — scan again"],
  ["[weixin] 检测到多个账号，使用第一个:", "Multiple accounts found, using first:"],
  ["[weixin] 启动 bot, account=", "Starting bot, account="],
].sort((a, b) => b[0].length - a[0].length);

function translateZh(s) {
  if (typeof s !== "string") return s;
  let out = s;
  for (const [zh, en] of ZH_EN_PAIRS) {
    if (out.includes(zh)) out = out.split(zh).join(en);
  }
  return out;
}

/** Drop weixin-agent-sdk's "[weixin]" line prefix so logs show only "[WeChat] …". */
function stripWeixinSdkTag(s) {
  if (typeof s !== "string") return s;
  return s.replace(/^\[weixin\]\s*/gim, "");
}

async function withTranslatedStdoutDuringLogin(run) {
  const orig = process.stdout.write.bind(process.stdout);
  process.stdout.write = (chunk, encoding, cb) => {
    if (typeof chunk === "string") chunk = translateZh(chunk);
    return orig(chunk, encoding, cb);
  };
  try {
    return await run();
  } finally {
    process.stdout.write = orig;
  }
}

const base = (process.env.METACLAW_OPENAI_BASE || "http://127.0.0.1:30000/v1").replace(/\/$/, "");
const model = process.env.METACLAW_MODEL || "metaclaw-model";
const apiKey = process.env.METACLAW_API_KEY || "metaclaw";
/** Fixed channel hint; main behavior comes from the MetaClaw proxy system prompt / skills. */
const systemPrompt = "You are a helpful assistant replying on WeChat. Be concise.";

const MAX_MESSAGES = 32;
const histories = new Map();

function trimHistory(messages) {
  while (messages.length > MAX_MESSAGES && messages.length > 1) {
    messages.splice(1, 1);
  }
}

async function chat(req) {
  const { conversationId, text, media } = req;
  let content = text || "";
  if (media) {
    const hint = `[${media.type}${media.fileName ? `: ${media.fileName}` : ""}]`;
    content = content ? `${content}\n${hint}` : hint;
  }
  if (!content.trim()) {
    return { text: undefined };
  }

  let messages = histories.get(conversationId);
  if (!messages) {
    messages = [{ role: "system", content: systemPrompt }];
    histories.set(conversationId, messages);
  }
  messages.push({ role: "user", content });
  trimHistory(messages);

  const sessionId = `wechat-${conversationId}`;
  const memoryScope = `wechat|${conversationId}`;

  let res;
  try {
    res = await fetch(`${base}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        "X-Session-Id": sessionId,
        "X-Turn-Type": "main",
        "X-Memory-Scope": memoryScope,
      },
      body: JSON.stringify({ model, messages, stream: false }),
    });
  } catch (err) {
    console.error("[MetaClaw-WeChat] fetch error:", err);
    return { text: "Cannot reach MetaClaw proxy — is `metaclaw start` running?" };
  }

  if (!res.ok) {
    const errBody = await res.text();
    console.error("[MetaClaw-WeChat] proxy HTTP", res.status, errBody.slice(0, 500));
    return { text: `Proxy error HTTP ${res.status}` };
  }

  const data = await res.json();
  const reply =
    data.choices?.[0]?.message?.content ?? data.choices?.[0]?.text ?? "";

  if (reply) {
    messages.push({ role: "assistant", content: reply });
    trimHistory(messages);
  }

  return { text: reply || undefined };
}

function formatSdkLine(msg) {
  return stripWeixinSdkTag(translateZh(msg));
}

const sdkLog = (msg) => console.log("[WeChat]", formatSdkLine(msg));
const sdkLogDebug = (msg) => console.debug("[WeChat]", formatSdkLine(msg));

const forceLogin =
  process.env.METACLAW_WECHAT_FORCE_LOGIN === "1" ||
  /^(true|yes|on)$/i.test(process.env.METACLAW_WECHAT_FORCE_LOGIN || "");

async function main() {
  if (!forceLogin) {
    try {
      console.log(
        "[MetaClaw-WeChat] Resuming saved WeChat session if present (use `metaclaw wechat-relogin` to scan QR for a new account).",
      );
      await start({ chat }, { log: sdkLogDebug });
      return;
    } catch (e) {
      const msg = e?.message || String(e);
      console.log("[MetaClaw-WeChat] No usable saved session; starting QR login:", msg);
    }
  }
  const accountId = await withTranslatedStdoutDuringLogin(() => login({ log: sdkLog }));
  console.log("[MetaClaw-WeChat] Logged in, accountId:", accountId);
  await start({ chat }, { accountId, log: sdkLogDebug });
}

await main();
