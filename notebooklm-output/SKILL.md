---
name: notebooklm-output
description: 基于云端已有 NotebookLM 项目生成、导出并下载结果。用于当用户说“生成 NotebookLM 某项目内容”“导出 notebooklm 某项目结果”“输出/制作/产出某个 NotebookLM 项目的思维导图、报告、表格、音频、视频、卡片、测验”等场景时触发。默认把这类请求理解为云端项目输出，先按项目名匹配 registry 中的云端 metadata，再告知支持的输出类型并调用脚本生成最终文件。
---

# NotebookLM 输出

## 固定目录

> 以下路径中 `<OPENCLAW_HOME>` 指用户的 `.openclaw` 根目录（脚本会自动检测）。

- 项目目录：`<OPENCLAW_HOME>/knowledge/notebooklm/projects`
- 输出目录：`<OPENCLAW_HOME>/knowledge/notebooklm/output`
- 状态索引：`<OPENCLAW_HOME>/knowledge/notebooklm/registry.json`

## 执行原则

1. 默认把“生成 / 制作 / 产出 / 导出 / 输出 NotebookLM 某项目内容”理解为**云端已有项目输出**，优先走本 skill，不要误判成 intake。
2. 用户给出项目名后，先运行脚本查找匹配项目。
3. 必须先告诉用户该项目当前支持哪些输出类型，再询问要哪一种；若用户需求已经明确对应某一种类型，也应先完成项目确认，再继续执行。
4. 用户确认类型后，再调用生成脚本。
5. 输出语言默认优先中文；**仅对 CLI 实际支持 `--language` 的输出类型**，才通过脚本显式传入中文（`zh_Hans`）。对不支持语言参数的类型，不要强塞 `--language`。
6. 只交付**最终文件**；如果脚本或 skill 有问题，先修复再正式生成。不要为了兜底而走底层直出，不要把排障用的中间产物落盘交付给用户。
7. 执行导出任务时，脚本会弹出本地 GUI 进度窗口，每 5 秒刷新一次，展示项目名、输出类型、任务状态、任务 ID、耗时、保存路径或错误信息。
8. 如果当前阶段尚未接通真实云端生成能力，允许输出能力清单与本地路径规划，但不能谎称已从云端生成成功。

## 标准命令

查询项目：

```powershell
python <OPENCLAW_HOME>/skills/notebooklm-output/scripts/output.py inspect --project "<项目名>"
```

执行输出：

```powershell
python <OPENCLAW_HOME>/skills/notebooklm-output/scripts/output.py generate --project "<项目名>" --type "<输出类型>"
```

## 当前默认输出类型

- audio-overview（默认 `brief`，即摘要）
- video-overview
- slide-deck
- quiz
- flashcards
- infographic
- report
- mind-map
- data-table

## 输出要求

简洁汇报：
- 找到的项目名
- 支持的输出类型
- 用户选了哪一种
- 默认语言策略：优先中文；仅在该输出类型支持 `--language` 时显式传入 `zh_Hans`
- 最终文件保存路径
- 若脚本在修复后才成功，要只汇报最终成功结果，不要把排障期的中间文件当成交付物
- 若未接通云端，明确说明当前是骨架阶段
