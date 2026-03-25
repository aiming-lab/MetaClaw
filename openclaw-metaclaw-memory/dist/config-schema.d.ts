export declare const configSchema: import("@sinclair/typebox").TObject<{
    autoRecall: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TBoolean>;
    autoCapture: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TBoolean>;
    sidecarPort: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TNumber>;
    scope: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    retrievalMode: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TUnion<[import("@sinclair/typebox").TLiteral<"keyword">, import("@sinclair/typebox").TLiteral<"embedding">, import("@sinclair/typebox").TLiteral<"hybrid">]>>;
    maxInjectedTokens: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TNumber>;
    maxInjectedUnits: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TNumber>;
    memoryDir: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    autoUpgradeEnabled: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TBoolean>;
    pythonPath: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    debug: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TBoolean>;
}>;
