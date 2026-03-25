import { Type } from "@sinclair/typebox";
export const configSchema = Type.Object({
    autoRecall: Type.Optional(Type.Boolean({ default: true })),
    autoCapture: Type.Optional(Type.Boolean({ default: true })),
    sidecarPort: Type.Optional(Type.Number({ default: 19823 })),
    scope: Type.Optional(Type.String({ default: "default" })),
    retrievalMode: Type.Optional(Type.Union([
        Type.Literal("keyword"),
        Type.Literal("embedding"),
        Type.Literal("hybrid"),
    ], { default: "hybrid" })),
    maxInjectedTokens: Type.Optional(Type.Number({ default: 800 })),
    maxInjectedUnits: Type.Optional(Type.Number({ default: 6 })),
    memoryDir: Type.Optional(Type.String({ default: "~/.metaclaw/memory" })),
    autoUpgradeEnabled: Type.Optional(Type.Boolean({ default: false })),
    pythonPath: Type.Optional(Type.String({ default: "python3" })),
    debug: Type.Optional(Type.Boolean({ default: false })),
}, { additionalProperties: false });
//# sourceMappingURL=config-schema.js.map