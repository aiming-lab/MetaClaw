# Memory 模块测试覆盖

## 测试概况

- **测试文件**: `tests/test_memory_system.py` (~11,000 行)
- **测试数量**: 535+ 个测试, 130+ 个测试类
- **状态**: 全部通过 (535/535)
- **E2E 脚本**: `scripts/run_e2e_skills_memory_test.py` (10/10 通过)
- **Live Tinker**: `tests/test_v03_live_tinker.py` (9/9 通过, 需 API key)

## 覆盖矩阵

### 核心存储层
| 测试类 | 覆盖内容 |
|--------|----------|
| `MemoryStoreTests` | 关键词搜索, 类型统计 |
| `FTSSearchTests` | 全文搜索, 作用域隔离 |
| `CorruptedStoreTests` | 损坏/丢失 DB 恢复 |
| `StoreRobustnessTests` | 空查询, 空存储边界 |
| `StoreIntegrityTests` | 孤儿检测, 清理, CSV 导出 |
| `SchemaVersionTests` | schema 版本初始化 |
| `BackupTests` | 备份创建验证 |
| `CompactionTests` | 删除后压缩 |
| `ThreadSafetyTests` | 并发读取 |

### Manager 集成
| 测试类 | 覆盖内容 |
|--------|----------|
| `MemoryManagerTests` | 渲染/合并/提取/作用域统计/混合检索 |
| `CLIIntegrationTests` | 状态渲染, 端到端 ingest/retrieve/render |
| `ManagerIntegrationTests` | 多会话 ingest + 合并 + 衰减 |
| `MemoryRESTAPITests` | 9 个 REST 端点 |

### 检索质量
| 测试类 | 覆盖内容 |
|--------|----------|
| `RetrievalRankingTests` | IDF 稀有词排序 |
| `HybridRetrievalTests` | 混合模式 IDF |
| `ConfidenceWeightedRetrievalTests` | 置信度加权 |
| `TagBasedRetrievalBoostTests` | 标签提升 (15%/tag) |
| `RetrievalCacheTests` | LRU 缓存命中/失效 |
| `RetrievalAutoRouteTests` | 自动模式选择 |
| `RetrievalLatencyTests` | 500 条记忆 < 1s |
| `RetrievalProfileTests` | balanced/recall/precision/recent |
| `ScaleRetrievalTests` | 500 条记忆质量 |
| `LinkedRetrievalExpansionTests` | 链接扩展 |

### 提取质量
| 测试类 | 覆盖内容 |
|--------|----------|
| `ExtractionQualityTests` | response 侧事实提取 |
| `ExtendedExtractionPatternTests` | "I would like", "never" 等模式 |
| `ImprovedExtractionTests` | CamelCase/snake_case 实体 |
| `MultiTurnExtractionTests` | 跨轮次实体继承 |
| `EdgeCaseExtractionTests` | 超长文本, Unicode, 特殊字符 |

### 策略系统
| 测试类 | 覆盖内容 |
|--------|----------|
| `MemoryPolicyTests` | 持久化/回滚/刷新 |
| `PolicyValidationTests` | 范围校验 |
| `PolicyOptimizerTests` | 遥测驱动调优, 安全底线 |

### 自升级
| 测试类 | 覆盖内容 |
|--------|----------|
| `MemoryReplayTests` | 样本加载, 评估对比, 候选回放 |
| `ReplayQualityTests` | grounding/coverage, 晋升标准 |
| `MemorySelfUpgradeTests` | 完整晋升周期, 审核队列, 历史 |
| `MemoryUpgradeWorkerTests` | 跳过/执行/等待/告警/健康快照 |
| `MemoryCandidateTests` | 有界生成, 权重变体 |
| `MemoryPromotionTests` | 阈值/回归拒绝/zero-retrieval |

### 作用域
| 测试类 | 覆盖内容 |
|--------|----------|
| `MemoryScopeTests` | 推导优先级 |
| `ScopeIsolationTests` | 跨作用域隔离 |
| `ScopeAccessControlTests` | ACL grant/check/revoke |
| `ScopeMigrationTests` | 跨作用域迁移 |
| `MergeScopesTests` | 合并去重 |

### 生命周期
| 测试类 | 覆盖内容 |
|--------|----------|
| `ImportanceDecayTests` | 线性/指数衰减 |
| `AdaptiveTTLTests` | 自适应 TTL, pin 豁免 |
| `RetentionPolicyTests` | 保留策略, pin 豁免 |
| `GarbageCollectionTests` | 孤儿链清理 |
| `CascadeArchiveTests` | 级联归档 |

### 性能/压力
| 测试类 | 覆盖内容 |
|--------|----------|
| `StressTests` | 500 条搜索性能 |
| `RetrievalLatencyTests` | 500 条 < 1s |
| `SimulatedProductionTests` | 多用户负载, TTL 压力, 跨作用域共享 |

## E2E 测试 (`run_e2e_skills_memory_test.py`)

针对 Azure OpenAI (gpt-5.1) 的 7 步端到端验证:
1. 基础代理转发
2. 多轮会话构建上下文 (3 轮)
3. 新会话检索验证 (跨会话记忆)
4. 不同话题会话
5. `/v1/memory/health` 端点
6. 直接 SQLite 存储检查
7. 流式响应验证

## 已修复的 7 个 Bug (MEMORY_FIX_PLAN.md)

| # | 问题 | 严重度 |
|---|------|--------|
| 1 | 作用域跨轮次三重嵌套 | CRITICAL |
| 2 | 注入依赖 skill_manager 而非 memory_manager | CRITICAL |
| 3 | RL 模式不缓冲记忆 turns | CRITICAL |
| 4 | skill evolution 清空记忆缓冲区 | HIGH |
| 5 | 跨会话检索被 session scope 锁定 | CRITICAL |
| 6 | 同步注入阻塞事件循环 | MEDIUM |
| 7 | 异步测试缺少 @pytest.mark.asyncio | MEDIUM |
