# Memory 模块进度与后续计划

## 当前进度

### 已完成 (Phase 0–4 全部完成)

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 规划与设计 | ✅ |
| Phase 1 | 基础记忆: 提取/存储/检索/注入/合并 | ✅ |
| Phase 2 | 自适应策略: 运行时参数自动调优 | ✅ |
| Phase 3 | 离线评估: 回放评估框架 | ✅ |
| Phase 4 | 受控自升级: 候选生成→回放评估→晋升门控 | ✅ |

### 代码量级

- `metaclaw/memory/`: 18 个文件
- `store.py`: ~1,800 行 (SQLite schema v6)
- `manager.py`: ~2,400 行 (门面 API)
- `test_memory_system.py`: ~11,000 行, 535+ 测试

### 测试通过率

| 类别 | 结果 |
|------|------|
| 单元测试 | 535/535 ✅ |
| Live Tinker | 9/9 ✅ |
| E2E | 10/10 ✅ |
| RL 训练实验 | 3/3 步, 28 条提取, 11 条活跃 ✅ |

### 已修复关键 Bug

7 个 bug 全部修复 (4 个 CRITICAL, 1 个 HIGH, 2 个 MEDIUM)

### OpenClaw 插件

`openclaw-metaclaw-memory/` TypeScript 插件已就绪, 内嵌 Python sidecar

---

## 当前状态评估

### 强项
- 功能完备: 从基础 CRUD 到自升级的完整流水线
- 测试覆盖极其全面 (535+ 测试覆盖所有层)
- 7 个集成 bug 已修复并验证
- 自升级有人工审核门控, 安全可控

### 需关注的点

1. **默认关闭**: `memory_enabled=False`, `memory_auto_upgrade_enabled=False` — 需要用户主动开启
2. **仅 keyword 模式默认**: `memory_retrieval_mode="keyword"`, embedding 默认关闭
3. **无生产环境长期运行数据**: RL 训练实验仅跑了 3 步
4. **store.py 和 manager.py 体量大**: 单文件 1800-2400 行, 维护成本较高

---

## 后续可能的工作方向

### 近期 (建议优先)

1. **生产就绪验证**
   - 在真实 RL 训练中长时间运行 memory (10+ episodes)
   - 验证记忆积累、合并、衰减的长周期行为
   - 收集遥测数据, 验证 policy_optimizer 的调优效果

2. **Embedding 模式端到端验证**
   - 默认用 `HashingEmbedder`, 但 `SentenceTransformerEmbedder` / 自定义模型 (`Qwen3-Embedding-0.6B`) 需真实场景验证
   - 验证 hybrid 模式检索质量是否优于纯 keyword

3. **自升级循环端到端验证**
   - 积累足够回放数据后, 实际运行一次完整的 auto-upgrade cycle
   - 验证候选生成→评估→晋升→策略生效的全链路

### 中期

4. **性能优化**
   - 当前 500 条记忆检索 < 1s, 但更大规模 (5000+) 需要 benchmark
   - 考虑 embedding 索引 (FAISS/hnswlib) 替代全量 cosine scan

5. **manager.py 拆分**
   - 2400 行的门面类可考虑拆分: 核心 CRUD / 分析诊断 / 质量管理 / 作用域管理

6. **记忆质量提升**
   - 当前提取基于模式匹配, 可引入 LLM 辅助提取
   - `MemoryReplayJudge` 已预留 LLM 评判接口, 但只实现了 `HeuristicReplayJudge`

### 长期

7. **跨实例记忆共享**
   - 当前 ACL 支持 scope 级权限, 但实际的多实例同步未实现
   - SQLite 单文件存储限制了分布式场景

8. **记忆蒸馏**
   - 将大量 episodic 记忆压缩为更高质量的 semantic 记忆
   - 利用 LLM 生成 working_summary 而非规则拼接
