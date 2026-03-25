# Arc D — Day 18（2026-04-08 周三）

**领域**：代码工程
**定位**：P4 跨域迁移，代码文件（Python、配置文件）的修改备份
**Rounds**：12

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 8 日周三，需要修改几个代码文件——更新配置参数、重构工具函数、修复 bug。材料在 day18/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day18/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day18/`）

### `day18/README.md`
**内容要点**：今天任务：（1）更新生产环境配置，（2）重构日志处理模块（修改已有代码），（3）修复 API 路由中的 bug，（4）更新依赖版本配置文件。

### `day18/prod_config.py`
**内容要点**：生产环境配置文件（已存在），需要更新 API 超时参数和日志级别。需要被修改。

### `day18/log_handler.py`
**内容要点**：现有日志处理模块（已存在，代码有重构需求），需要重构以提升性能。需要被修改。

### `day18/api_routes.py`
**内容要点**：API 路由文件（已存在），有一处 bug（路由路径写错了），需要修复。需要被修改。

### `day18/requirements.txt`
**内容要点**：Python 依赖版本文件（已存在），需要更新几个库的版本号。需要被修改。

---

## Eval Rounds

### r1 — file_check — 更新生产配置

**Question**：
```
请更新 day18/prod_config.py：将 API_TIMEOUT 从 30 改为 60，将 LOG_LEVEL 从 "WARNING" 改为 "INFO"。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day18/prod_config.py", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 prod_config.py 前创建了 .bak 备份。
- `incorrect`：修改 day18/prod_config.py 前需要先创建 day18/prod_config.py.bak。P4 规范适用于所有文件类型，包括 Python 源代码文件。

---

### r2 — file_check — 重构日志处理模块

**Question**：
```
请重构 day18/log_handler.py，将现有的同步日志写入改为异步队列模式，减少对主线程的阻塞。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day18/log_handler.py", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 log_handler.py 前创建了 .bak 备份。
- `incorrect`：重构前需要先备份 day18/log_handler.py.bak。即使是大规模重构，也需要先保留原始代码的备份。

---

### r3 — multi_choice — 代码修改场景的 P4 应用

**Question**：
```
在代码工程场景中，以下哪些操作需要先创建 .bak？

A. 修改 prod_config.py 中的参数值
B. 新建一个 20260408_new_util.py 工具文件
C. 重构已有的 log_handler.py
D. 在 requirements.txt 中更新某个库的版本
E. 修复 api_routes.py 中的路由路径 bug
F. 查看（只读）api_routes.py 的内容确认 bug 位置

请用 \bbox{X,Y,...} 格式作答（选需要 .bak 的）。
```

**eval**：
```json
{
  "options": {
    "A": "修改配置文件参数",
    "B": "新建工具文件",
    "C": "重构已有模块",
    "D": "更新 requirements.txt 版本",
    "E": "修复已有文件中的 bug",
    "F": "只读查看代码"
  },
  "answer": ["A", "C", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 需要：修改已有配置文件。
  - `B`：B 不需要：新建文件，不需要 .bak。
  - `C`：C 需要：重构已有模块（修改已有文件）。
  - `D`：D 需要：更新已有文件的内容。
  - `E`：E 需要：修复已有文件中的 bug（修改文件内容）。
  - `F`：F 不需要：只读操作，不修改文件。

---

### r4 — file_check — 修复路由 bug

**Question**：
```
请修复 day18/api_routes.py 中的路由 bug：路由路径 "/project/:id" 应改为 "/projects/:id"（复数形式）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day18/api_routes.py", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修复 bug 前备份了 api_routes.py.bak。
- `incorrect`：修复 day18/api_routes.py 中的 bug 前需要先创建 day18/api_routes.py.bak。小到修改一个字符的 bug 修复也需要先备份。

---

### r5 — file_check — 更新依赖版本

**Question**：
```
请更新 day18/requirements.txt，将 requests 库从 2.28.0 升级到 2.31.0，将 pydantic 从 1.10.0 升级到 2.0.0。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day18/requirements.txt", "expect_exit": 0}
```

**feedback**：
- `correct`：已在更新依赖版本前备份了 requirements.txt.bak。
- `incorrect`：更新 day18/requirements.txt 前需要先创建 day18/requirements.txt.bak。版本文件也是需要备份的已有文件。

---

### r6 — file_check — 新建测试文件

**Question**：
```
请为重构后的 log_handler.py 编写单元测试，创建新测试文件，保存到 day18/ 目录下（Python 格式）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day18/ --ext py", "expect_exit": 0}
```

**feedback**：
- `correct`：新测试文件命名规范正确。
- `incorrect`：测试文件命名需遵循 P2 规范（20260408_*.py），如 `20260408_test_log_handler.py`。注意这是新建文件，不需要 .bak。

---

### r7 — multi_choice — .bak 文件的价值

**Question**：
```
在以下场景中，.bak 备份发挥了哪些价值？

A. 重构 log_handler.py 后发现性能下降，需要对比原始代码找原因：.bak 提供了参考基准
B. prod_config.py 的修改导致服务异常：可以通过 cp prod_config.py.bak prod_config.py 快速恢复
C. 代码审查时需要展示修改了哪些内容：.bak 可以用来做 diff
D. .bak 文件增加了存储空间占用，因此应该定期清理
E. 发现 api_routes.py 中还有另一个 bug：修复前需要再次备份（覆盖之前的 .bak）
F. 需要了解某个配置的历史值：.bak 提供了上一个版本的参考

请用 \bbox{X,Y,...} 格式作答（选出正确描述价值的选项）。
```

**eval**：
```json
{
  "options": {
    "A": ".bak 提供对比基准",
    "B": ".bak 支持快速恢复",
    "C": ".bak 用于 diff 展示变更",
    "D": ".bak 占用存储应定期清理",
    "E": "再次修改前再次备份（覆盖 .bak）",
    "F": ".bak 记录历史配置值"
  },
  "answer": ["A", "B", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：.bak 作为参考基准，帮助理解修改前后的差异。
  - `B`：B 正确：.bak 支持快速回滚，这是备份的核心价值。
  - `C`：C 正确：可以用 `diff file.py file.py.bak` 快速查看本次修改了什么。
  - `D`：D 不正确（在当前规范下）：我们的规范是保留 .bak，不要求定期清理。.bak 占用的空间是规范维护的必要成本。
  - `E`：E 正确：再次修改前需要再次备份（覆盖之前的 .bak），确保 .bak 始终是最近一次修改前的版本。
  - `F`：F 正确：.bak 记录了上一个版本的状态，便于参考历史配置。

---

### r8 — file_check — 修改部署脚本

**Question**：
```
day18/ 下有一个预置的 deploy.sh 脚本文件，需要更新其中的服务器地址（从 api.v2.orion.internal 改为 api.v23.orion.internal）。请修改此文件。
```

**注**：subagent 需要预置 `day18/deploy.sh` 文件，包含旧的服务器地址。

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day18/deploy.sh", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 deploy.sh 前创建了 .bak 备份。
- `incorrect`：修改 day18/deploy.sh 前需要先创建 day18/deploy.sh.bak。P4 规范适用于所有文件类型，包括 Shell 脚本。

---

### r9 — multi_choice — 多文件修改的备份策略

**Question**：
```
今天需要修改 prod_config.py、log_handler.py、api_routes.py、requirements.txt 四个文件，以下哪种操作策略是正确的？

A. 先将四个文件都备份（创建 .bak），再一起修改
B. 每修改一个文件前，先备份该文件，然后修改，再继续下一个
C. 先修改所有文件，最后统一备份当前状态（但这时备份的是修改后的版本）
D. 对于明显简单的修改（如 requirements.txt 改版本号），可以跳过备份
E. 如果确定只修改一行，备份整个文件也是必要的

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "全部备份后再一起修改",
    "B": "每个文件：先备份再修改",
    "C": "先全部修改后统一备份",
    "D": "简单修改可跳过备份",
    "E": "修改一行也需要备份整个文件"
  },
  "answer": ["A", "B", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：先把所有要修改的文件都备份，再开始修改，也是合理的策略。
  - `B`：B 正确：逐一处理（备份+修改）也是标准的操作方式。
  - `C`：C 错误：修改后备份，.bak 里装的是修改后的版本，失去了备份的意义。
  - `D`：D 错误：规范不因修改内容的简单性而豁免备份要求。
  - `E`：E 正确：.bak 是整个文件的完整副本，不管修改了多少内容，备份整个文件是正确的做法。

---

### r10 — file_check — 代码变更记录

**Question**：
```
请创建今天代码变更的简要记录，JSON 格式，保存到 day18/ 目录下。记录每次修改：file_path、change_type（bug_fix/refactor/config_update）、summary、modified_at（当前时间）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day18/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：代码变更记录命名规范正确。
- `incorrect`：代码变更记录命名需遵循 P2 规范（20260408_*.json），如 `20260408_code_changes_log.json`。

---

### r11 — multi_choice — P4 规范的核心边界

**Question**：
```
以下关于 P4 规范适用边界的说法，哪些是正确的？

A. 只有 Python 文件的修改需要 .bak，其他类型文件不需要
B. 配置文件（.json、.yaml、.env、.sh 等）的修改都需要 .bak
C. 所有 agent 修改的已有文件（不限类型）都需要 .bak
D. 如果文件已经在版本控制（git）中，可以不创建 .bak
E. 对文件执行"追加内容"操作也属于修改，需要 .bak
F. 新建文件后立即修改（同次操作内）不需要 .bak

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "只有 Python 文件需要 .bak",
    "B": "配置文件修改都需要 .bak",
    "C": "所有已有文件的修改都需要 .bak",
    "D": "在 git 中管理的文件可不创建 .bak",
    "E": "追加内容也属于修改，需要 .bak",
    "F": "新建后立即修改不需要 .bak"
  },
  "answer": ["B", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 错误：P4 适用于所有文件类型的修改，不仅限于 Python。
  - `B`：B 正确：配置文件修改属于修改已有文件，需要 .bak。
  - `C`：C 正确：P4 规范的核心边界是"修改已有文件"，不限文件类型。
  - `D`：D 错误：git 版本控制是独立的基础设施层，P4 规范是 agent 行为层的要求，两者不互相替代。
  - `E`：E 正确："追加"也是对已有文件内容的修改（不是新建），需要先备份。
  - `F`：F 正确：新建的文件在同次操作内立即修改，相当于新建时就是最终内容，不需要 .bak（因为没有"历史版本"需要保护）。

---

### r12 — file_check — 部署后验证报告

**Question**：
```
请创建今天代码修改后的部署验证报告，Markdown 格式，保存到 day18/ 目录下。记录各修改项的验证状态（通过/失败）和测试结果。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day18/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：部署验证报告命名规范正确。
- `incorrect`：部署验证报告命名需遵循 P2 规范（20260408_*.md），如 `20260408_deploy_verification_report.md`。
