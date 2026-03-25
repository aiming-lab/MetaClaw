export const defaultConfig = {
    autoRecall: true,
    autoCapture: true,
    sidecarPort: 19823,
    scope: "default",
    retrievalMode: "hybrid",
    maxInjectedTokens: 800,
    maxInjectedUnits: 6,
    memoryDir: "~/.metaclaw/memory",
    autoUpgradeEnabled: false,
    pythonPath: "python3",
    debug: false,
};
export function parseConfig(raw) {
    return {
        autoRecall: raw.autoRecall ?? defaultConfig.autoRecall,
        autoCapture: raw.autoCapture ?? defaultConfig.autoCapture,
        sidecarPort: raw.sidecarPort ?? defaultConfig.sidecarPort,
        scope: raw.scope ?? defaultConfig.scope,
        retrievalMode: raw.retrievalMode ?? defaultConfig.retrievalMode,
        maxInjectedTokens: raw.maxInjectedTokens ?? defaultConfig.maxInjectedTokens,
        maxInjectedUnits: raw.maxInjectedUnits ?? defaultConfig.maxInjectedUnits,
        memoryDir: raw.memoryDir ?? defaultConfig.memoryDir,
        autoUpgradeEnabled: raw.autoUpgradeEnabled ?? defaultConfig.autoUpgradeEnabled,
        pythonPath: raw.pythonPath ?? defaultConfig.pythonPath,
        debug: raw.debug ?? defaultConfig.debug,
    };
}
//# sourceMappingURL=types.js.map