# notebooklm-intake 使用说明与当前状态

## 1. 这个 skill 是干什么的
`notebooklm-intake` 用来把本地准备好的资料批量或单个同步到 NotebookLM 云端，并在本地维护项目映射与状态记录。

它的目标不是只扫描文件，而是尽量完成这条真实闭环：
1. 从 `inbox/` 或指定路径找到待上传资料
2. 建立 / 维护本地项目 metadata
3. 在 NotebookLM 云端创建 notebook（必要时）
4. 上传 source
5. 把 `notebook_id` / `source_id` / `sync_status` 回写到本地
6. 根据结果决定是否自动归档或等待人工确认归档

简单说：
**把“本地文件 → NotebookLM 云端项目”这件事做成一个稳定、可重复执行的工作流。**

---

## 2. 目的是什么
这个 skill 的目的主要是：
- 让 NotebookLM 入库流程可批量、可重复执行
- 降低手动打开网页逐个上传 source 的成本
- 为后续 `notebooklm-output` 提供稳定的项目映射基础
- 在本地留下清晰的索引与状态记录，方便重试、排错和追踪

如果没有这层 intake，output skill 就没有稳定的 `notebook_id` / `source_id` / `sync_status` 作为依赖。

---

## 3. 依赖什么
这个 skill 依赖以下条件：
- 本机已完成 `notebooklm login`
- `notebooklm-py` CLI 可用
- 本地知识库路径为：
  `C:\Users\<username>\.openclaw\knowledge`
- NotebookLM 工作区目录为：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm`

关键依赖文件 / 目录：
- `inbox/`：待上传资料
- `processed/`：已处理 / 已归档资料
- `projects/`：项目 metadata
- `registry.json`：总索引

---

## 4. 当前目录与关键文件
### Skill 目录
`C:\Users\<username>\.openclaw\skills\notebooklm-intake`

### 关键文件
- `SKILL.md`
- `scripts\intake.py`
- `USAGE-AND-STATUS.md`（本说明文件）

### 本地知识库相关目录
- 工作区根：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm`
- 待上传资料：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm\inbox`
- 已处理资料：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm\processed`
- 项目映射：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm\projects`
- 总索引：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm\registry.json`
- 工作区总说明：
  `C:\Users\<username>\.openclaw\knowledge\notebooklm\README.md`

---

## 5. 现在怎么使用
### 5.1 普通入库
```powershell
python C:\Users\<username>\.openclaw\skills\notebooklm-intake\scripts\intake.py
```

作用：
- 扫描 `knowledge/notebooklm/inbox`
- 逐个处理候选文件
- 自动入库到 NotebookLM
- 输出结果 summary / results / projects

### 5.2 指定单个文件或目录
```powershell
python C:\Users\<username>\.openclaw\skills\notebooklm-intake\scripts\intake.py --path "<文件或目录>"
```

作用：
- 只处理指定对象
- 适合定点重试或局部测试

### 5.3 确认归档重复内容
```powershell
python C:\Users\<username>\.openclaw\skills\notebooklm-intake\scripts\intake.py --archive-duplicates
```

作用：
- 对已经 `already_synced` 的重复内容
- 在你确认后再自动归档到 `processed/`

---

## 6. 当前工作流是什么
当前脚本的主流程可以概括成：

1. 扫描候选文件
2. 识别 source 类型（主要用于记录与过滤）
3. 计算 `source_fingerprint`
4. 在本地 registry / projects 中查是否已有记录
5. 如果已有 notebook / source 映射，则尽量复用
6. 必要时创建云端 notebook
7. 必要时上传 source
8. 回写本地 metadata
9. 对新成功上传的内容自动归档
10. 对重复内容给出“是否归档”的确认状态

---

## 7. 参考了哪个 GitHub 项目
核心参考项目是：
- `teng-lin/notebooklm-py`

用途：
- 提供 NotebookLM 的 Python / CLI 调用能力
- 提供 `login / auth / create / source add / list / artifact` 等能力
- 让 intake / output 两个 skills 都可以围绕 `notebooklm` CLI 组装工作流

对于 intake 来说，主要依赖的是：
- `notebooklm login`
- `notebooklm list`
- `notebooklm create`
- `notebooklm use`
- `notebooklm source add`
- `notebooklm source list`

---

## 8. 当前已经做到哪一步了
### 8.1 已从骨架升级为真实上传版 MVP
现在的 `intake.py` 已经不是“只扫目录+写占位 metadata”，而是具备真实入库能力的 MVP。

### 8.2 已完成真实 smoke test
已完成最小闭环实测：
- 成功创建 notebook：`OpenClaw Intake Smoke Test`
- notebook_id：`5f42c4b2-8fe3-4cfd-890b-012b2c0fd2e6`
- 成功上传 source：`notebooklm-smoke-test.txt`
- source_id：`f994bd65-80a6-4ae0-b9e7-729d3d6e737f`
- `source list` 状态：`ready`
- 本地 metadata 已更新为 `synced`

### 8.3 已完成真实业务测试
已将真实项目资料成功上传：
- 项目：`2026-04-04-论文写作项目`
- notebook_id：`b8276b0e-f9a7-40d3-93fb-935f88944785`
- source_id：`cbe2f661-0d22-4938-8215-4354bab84038`
- 状态：`synced`

### 8.4 当前判断
现在 `notebooklm-intake` 已经不是实验骨架，而是：

**可实际使用的 intake MVP。**

---

## 9. 当前已经具备的能力
### 9.1 核心同步能力
- 扫描 inbox / 指定路径
- 自动创建 notebook
- 自动上传 source
- 成功后回写：
  - `notebook_id`
  - `source_id`
  - `sync_status = synced`
- 失败时保留 `pending_cloud_upload`
- 错误会写进 `notes`

### 9.2 去重与冲突保护
- notebook 去重（同名 notebook 复用）
- notebook 同名歧义保护（多个同名时拒绝自动猜测）
- source 去重（同一 notebook 内同名 source 复用）
- source 同名歧义保护（多个同名 source 时拒绝自动猜测）
- `source_fingerprint` 用于增强本地识别稳定性

### 9.3 批量处理能力
- 支持批量扫描多个文件
- 输出统一 summary
- 区分：
  - `synced`
  - `synced_after_retry`
  - `already_synced`
  - `failed`
- 输出更细错误分类：
  - `auth_error`
  - `notebook_conflict`
  - `source_conflict`
  - `source_upload_error`
  - `network_error`
  - `unknown_error`
- 多文件处理间加入节流，降低连续调用压力

### 9.4 失败重试
- 失败自动重试
- 当前默认最大 3 次
- attempt 信息会写到 notes / results

### 9.5 归档逻辑
#### 新成功上传的内容
- 自动归档到 `processed/`

#### 重复内容
- 默认不自动归档
- 返回：`archive_action = needs_confirmation`
- 结果中会列出：`pending_archive_confirmation`

#### 收到确认后
- 可通过 `--archive-duplicates` 自动归档

---

## 10. 当前输出结构
当前脚本输出包含：
- `summary`
- `pending_archive_confirmation`
- `results`
- `projects`

含义如下：
- `summary`：本次处理总体统计
- `pending_archive_confirmation`：等待确认归档的重复内容
- `results`：逐条处理结果
- `projects`：本次处理涉及到的项目快照

---

## 11. 当前策略是什么
### 上传策略
当前明确采用：
- **通用上传优先**
- 不做写死的 source 类型分流上传
- 尽量把文件成功传上去
- 如果失败，明确返回错误原因

### `source_type` 现在主要做什么
当前代码里的类型识别主要用于：
- 本地 metadata 记录
- 扫描入口过滤
- 未来扩展预留

它**不是**当前上传分流策略的核心。

这点非常重要，因为后续如果用户上传：
- Excel
- 代码文件
- 其他 NotebookLM 支持的新类型
不应该因为脚本写死类型分支而轻易出错。

---

## 12. 当前存在什么问题 / 有什么边界
### 12.1 目前仍是 MVP，不是完全收口版
虽然已经可用，但还不是“彻底不用再碰”的状态。

### 12.2 去重仍然部分依赖名字与本地记录
现在已经比最初稳很多，但如果未来出现：
- 大量重名 notebook
- 大量重名 source
- 本地文件多次移动
仍然需要继续增强策略。

### 12.3 对云端 API 行为仍然有外部依赖
skill 本身的能力依赖 `notebooklm-py` CLI 行为稳定。若上游 CLI / API 变化，可能需要继续适配。

### 12.4 批量场景虽已支持，但仍可继续优化
当前已经支持批量处理，但后续仍可以继续增强：
- 批量速度
- 更细的失败分组
- 更丰富的批量 summary

---

## 13. 如果让 Claude Code 来核查，建议重点看什么
### 第一优先级：核对真实上传链路是否完整
重点确认：
- 是否真的调用了 `notebooklm create`
- 是否真的调用了 `notebooklm source add`
- 成功后是否真的回写了本地 metadata
- `sync_status` / `notebook_id` / `source_id` 是否一致

### 第二优先级：核对去重与冲突保护是否有漏洞
重点看：
- notebook 同名冲突处理
- source 同名冲突处理
- 指纹逻辑是否足够稳

### 第三优先级：核对归档逻辑是否可靠
重点看：
- 新上传自动归档是否安全
- 重复内容确认归档的行为是否合理
- `--archive-duplicates` 是否与主流程一致

### 第四优先级：核对说明文档与代码是否一致
重点对照：
- `README.md`
- `SKILL.md`
- 本说明文件
- `scripts/intake.py`

避免出现：
- 文档说有，但代码里没有
- 代码行为已变化，但文档没同步

---

## 14. 当前整体判断
### 这个 skill 现在是什么状态
它已经不是骨架，而是：

**可用的真实 intake MVP。**

### 为什么这么判断
因为它已经满足：
- 真实云端上传已跑通
- smoke test 已通过
- 真实项目入库已通过
- 批量处理已具备
- 去重 / 重试 / 归档 / summary 这些基础工作流都已有了

但同时它仍然保留了 MVP 特征：
- 还可继续打磨
- 还可继续提高稳态和容错
- 还可继续让批量体验更顺手

所以最准确的说法不是“彻底完善”，而是：

**已经进入可实际使用阶段，但后续仍值得继续优化。**

---

## 15. 后续维护建议
后续维护时建议坚持这些原则：
- 保持“通用上传优先”策略
- 不要过早写死 source 类型分流
- 保持本地 metadata 与 registry 一致
- 所有真实行为都尽量写回文档
- 新增逻辑前，优先保证不破坏现有已验证链路

---

## 16. 当前一句话总结
`notebooklm-intake` 已经能稳定把本地资料真实上传到 NotebookLM 云端，并维护好本地项目索引、去重、重试和归档流程，是一个可实际使用的 intake MVP。