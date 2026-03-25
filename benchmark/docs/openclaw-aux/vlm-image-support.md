# OpenClaw 多模态（VLM）图像支持详解

openclaw 提供两种图像处理路径：**原生视觉**（图像直接注入主模型上下文）和**媒体理解**（调用专用 VLM 将图像转为文字描述后注入）。

---

## 一、两种图像处理路径

### 路径 A：原生视觉（Native Vision）

主模型本身支持图像输入（`input` 含 `"image"`），图像以 base64 块直接注入消息的 `content` 数组，发送给主模型 API。

```
图像引用检测 → loadImageFromRef() → 注入 content[] → 发送主模型
```

### 路径 B：媒体理解（Media Understanding）

主模型不支持图像，或配置了专用 VLM。先用 VLM 生成图像的文字描述，再把描述拼接到用户消息体。

```
图像引用检测 → runCapability("image.description") → VLM 生成描述
             → applyMediaUnderstanding() 将描述插入消息体 → 发送主模型
```

---

## 二、支持的图像来源格式

代码位置：`src/agents/pi-embedded-runner/run/images.ts`

| 格式 | 示例 |
|------|------|
| 绝对路径 | `/home/user/screenshot.png` |
| 相对路径 | `./diagram.jpg`, `../images/fig1.png` |
| 主目录路径 | `~/Desktop/photo.jpeg` |
| file:// URL | `file:///path/to/image.png` |
| 消息附件格式 | `[Image: source: /path/to/image.jpg]` |

支持的扩展名：`.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` `.tiff` `.tif` `.heic` `.heif`

---

## 三、配置文件

### 3.1 模型定义中声明视觉能力

在模型配置（`types.models.ts` 中的 `ModelDefinitionConfig`）里，`input` 字段控制模型是否支持原生视觉：

```jsonc
// agent 配置文件中的模型定义片段
{
  "models": [
    {
      "id": "gpt-4o",
      "input": ["text", "image"],   // 含 "image" 则 modelSupportsVision() 返回 true
      "reasoning": false,
      "contextWindow": 128000,
      "maxTokens": 16384,
      "cost": { "input": 2.5, "output": 10, "cacheRead": 0, "cacheWrite": 0 }
    }
  ]
}
```

### 3.2 媒体理解（Media Understanding）配置

在 agent 配置的 `tools.media` 字段下配置，类型定义来自 `src/config/types.tools.ts`：

```jsonc
{
  "tools": {
    "media": {
      "concurrency": 2,          // 最大并发 VLM 调用数
      "models": [                // 全局共享模型列表（image/audio/video 公用）
        { "provider": "openai", "model": "gpt-4o-mini" }
      ],
      "image": {
        "enabled": true,
        "maxBytes": 6291456,     // 6MB，默认上限
        "maxChars": 2000,        // VLM 返回描述的最大字符数
        "timeoutSeconds": 30,
        "prompt": "Describe the image in detail.",
        "models": [              // image 专属模型，优先于全局 models
          { "provider": "anthropic", "model": "claude-opus-4-6" },
          { "provider": "google",    "model": "gemini-3-flash-preview" }
        ]
      },
      "audio": {
        "enabled": true,
        "language": "zh"
      },
      "video": {
        "enabled": false
      }
    }
  }
}
```

各字段说明：

| 字段 | 说明 |
|------|------|
| `enabled` | 是否启用该媒体类型的理解功能 |
| `maxBytes` | 发送给 VLM 的最大图像字节数 |
| `maxChars` | VLM 返回描述的最大字符数 |
| `timeoutSeconds` | VLM 调用超时时间 |
| `prompt` | 传给 VLM 的默认提示词 |
| `models` | 有序 fallback 模型列表，逐个尝试直到成功 |

### 3.3 内置默认 VLM（`src/media-understanding/defaults.ts`）

当配置中未指定 models 时，按 provider 使用以下默认模型：

| Provider | 默认模型 |
|----------|---------|
| `openai` | `gpt-5-mini` |
| `anthropic` | `claude-opus-4-6` |
| `google` | `gemini-3-flash-preview` |
| `minimax` | `MiniMax-VL-01` |
| `zai` | `glm-4.6v` |

---

## 四、各 Provider 的 API 请求格式

### OpenAI / 兼容格式

通过 pi-ai SDK 的 `complete()` 传入 `ImageContent` 块，SDK 负责转换为 OpenAI 的 `image_url` 格式。

### Google Gemini（`src/media-understanding/providers/google/inline-data.ts`）

```jsonc
{
  "contents": [{
    "role": "user",
    "parts": [
      { "text": "Describe the image." },
      {
        "inline_data": {
          "mime_type": "image/jpeg",
          "data": "<base64 string>"
        }
      }
    ]
  }]
}
```

Gemini 认证支持两种方式（`src/infra/gemini-auth.ts`）：
- 传统 API Key → `x-goog-api-key` header
- OAuth JSON `{"token":"...", "projectId":"..."}` → `Authorization: Bearer` header

### Anthropic

通过 pi-ai SDK 统一处理，content block 格式：

```jsonc
{
  "role": "user",
  "content": [
    { "type": "text", "text": "Describe the image." },
    { "type": "image", "source": { "type": "base64", "media_type": "image/jpeg", "data": "<base64>" } }
  ]
}
```

### MiniMax（`src/agents/minimax-vlm.ts`）

使用 data URL 格式：

```jsonc
{
  "prompt": "Describe the image.",
  "image_url": "data:image/jpeg;base64,<base64 string>"
}
```

---

## 五、图像大小限制与自动处理

代码位置：`src/agents/tool-images.ts`

| 限制 | 值 | 说明 |
|------|-----|------|
| `MAX_IMAGE_DIMENSION_PX` | 2000px | 超出则自动缩放（Anthropic API 限制） |
| `MAX_IMAGE_BYTES` | 5MB（工具图像）/ 6MB（媒体理解） | 超出则降质量后重试 |

处理流程：
1. **Base64 规范化**：去除 `data:image/...;base64,` 前缀，URL-safe base64 转标准 base64
2. **格式推断**：从 base64 头部 magic bytes 推断 MIME 类型
3. **自动缩放**：超过最大尺寸时等比缩放，转为 JPEG 输出
4. **大小降质**：缩放后若仍超字节限制，逐步降低 JPEG 质量直到满足要求

---

## 六、Session JSONL 文件中图像消息的存储格式

图像以 base64 编码内联存储在 JSONL 的 `content` 数组中。

### 用户消息（含原生图像）

```jsonl
{"role":"user","content":[{"type":"text","text":"请分析这张图"},{"type":"image","data":"<base64 string>","mimeType":"image/jpeg"}],"timestamp":1740000000000}
```

### 助手消息（含工具调用返回的图像）

工具结果消息中图像存储在 `toolResult.content[]`：

```jsonl
{"role":"tool","toolUseId":"toolu_xxx","content":[{"type":"text","text":"图像分析结果"},{"type":"image","data":"<base64 string>","mimeType":"image/png"}],"timestamp":1740000000001}
```

### 媒体理解路径（图像转文字描述）

若走媒体理解路径，图像本身不存入会话，描述文字被拼接到用户消息体：

```jsonl
{"role":"user","content":[{"type":"text","text":"请分析这张图\n\n[Image: screenshot.png]\n图像描述：这是一张显示系统日志的截图，其中包含三条错误记录..."}],"timestamp":1740000000000}
```

`MediaUnderstanding` 元数据同时记录在 session entry 中，便于追踪来源。

---

## 七、完整消息流

```
用户消息含图像引用
        ↓
detectAndLoadPromptImages()
  检测路径引用 / 附件标记，读取文件为 Buffer
        ↓
        ├─ 主模型支持 input:["image"]？
        │        ↓ Yes
        │   injectHistoryImagesIntoMessages()
        │   将 ImageContent 块注入 content[]
        │        ↓
        │   sanitizeSessionMessagesImages()
        │   验证 base64、自动缩放
        │        ↓
        │   发送给主模型（原生视觉）
        │
        └─ No（或配置了专用 VLM）
             ↓
        runCapability("image.description")
        调用 VLM provider（openai/anthropic/google/minimax/zai）
             ↓
        applyMediaUnderstanding()
        将描述文字插入用户消息体
             ↓
        发送给主模型（纯文本上下文）
```

---

## 八、快速配置示例

在 agent 配置文件中启用图像理解，使用 Google Gemini 作为 VLM：

```jsonc
{
  "model": "gpt-4o",               // 主模型（可不支持视觉）
  "tools": {
    "media": {
      "image": {
        "enabled": true,
        "models": [
          { "provider": "google", "model": "gemini-3-flash-preview" }
        ]
      }
    }
  }
}
```

若主模型本身支持视觉（如 `gpt-4o`、`claude-opus-4-6`），且模型定义中 `input` 含 `"image"`，则无需配置 `tools.media.image`，图像会自动走原生视觉路径。
