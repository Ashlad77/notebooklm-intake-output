# notebooklm-intake

把本地资料批量或单个同步到 [NotebookLM](https://notebooklm.google.com/) 云端，并在本地维护项目映射与状态记录。

---

## 简介

`notebooklm-intake` 是一个面向 [OpenClaw](https://github.com/Ashlad77) 的 Claude Code skill，用来把本地准备好的文档、音视频、表格等资料**自动入库到 NotebookLM 云端**，并维护本地项目索引、去重、重试和归档流程。

**一句话定义**：把"本地文件 → NotebookLM 云端项目"这件事做成一个稳定、可重复执行的工作流。

---

## 功能

- 扫描 `inbox/` 目录（或指定路径）中的待上传资料
- 自动在云端创建同名 Notebook（已存在则复用）
- 自动上传 Source，回写 `notebook_id`、`source_id`、`sync_status` 到本地
- 支持批量处理，文件间自动节流
- 本地 + 云端双重去重，防止重复上传
- 自动重试（最多 3 次，退避递增），失败分类报告
- 成功上传后自动归档到 `processed/`
- 输出结构化 JSON summary，便于追踪和排错

---

## 前置条件

1. **Python 3.10+**
2. **`notebooklm-py` CLI** 已安装并完成认证：

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
notebooklm login
```

> 中国大陆用户需要网络代理才能访问 Google 服务。
> 如需使用 Microsoft Edge SSO 登录，可用 `notebooklm login --browser msedge`。

3. 验证连接：

```bash
notebooklm list
```

正常返回 notebook 列表（空列表也算成功）即表示对接完成。

---

## 目录结构

```
~/.openclaw/
├── skills/
│   └── notebooklm-intake/
│       ├── SKILL.md
│       ├── REPLICATION-GUIDE.md
│       └── scripts/
│           └── intake.py          ← 核心脚本
└── knowledge/
    └── notebooklm/
        ├── inbox/                 ← 待上传资料放这里
        ├── processed/             ← 上传成功后自动归档
        ├── projects/              ← 每个项目的本地 metadata
        └── registry.json          ← 总索引
```

---

## 快速开始

### 批量入库（扫描整个 inbox）

```powershell
python C:\Users\<你的用户名>\.openclaw\skills\notebooklm-intake\scripts\intake.py
```

### 指定单个文件或目录

```powershell
python ...\intake.py --path "<文件或目录路径>"
```

### 确认归档重复内容

```powershell
python ...\intake.py --archive-duplicates
```

---

## 输出说明

脚本输出结构化 JSON，包含四个部分：

| 字段 | 说明 |
|------|------|
| `summary` | 本次处理总体统计（扫描数、成功数、失败数等） |
| `pending_archive_confirmation` | 等待确认归档的重复内容列表 |
| `results` | 逐条处理结果（含状态、notebook_id、source_id、归档路径） |
| `projects` | 本次处理涉及的项目 metadata 快照 |

**结果状态说明：**

| 状态 | 含义 |
|------|------|
| `synced` | 首次上传成功 |
| `synced_after_retry` | 重试后上传成功 |
| `already_synced` | 已有云端记录，跳过上传 |
| `failed` | 上传失败（含错误类型和原因） |
| `skipped` | 因前序 auth 错误而跳过 |

---

## 支持的文件类型

| 类型 | 扩展名 |
|------|--------|
| 文档 | `.pdf` `.txt` `.md` `.doc` `.docx` |
| 表格 | `.xls` `.xlsx` `.csv` `.tsv` |
| 音频 | `.mp3` `.wav` `.m4a` |
| 视频 | `.mp4` `.mov` `.avi` |
| 链接/网页 | `.url` `.webloc` `.html` |

---

## 错误处理

| 错误类型 | 行为 |
|----------|------|
| `auth_error` | 立即停止所有后续处理，提示重新登录 |
| `notebook_conflict` | 云端存在多个同名 Notebook，报错等待人工介入 |
| `source_conflict` | 云端存在多个同名 Source，报错等待人工介入 |
| `source_upload_error` | 自动重试，最多 3 次 |
| `network_error` | 自动重试，最多 3 次 |
| `unknown_error` | 自动重试，最多 3 次 |

---

## 本地 Metadata 字段

每个上传资料在 `projects/<项目名>/project.json` 中会记录：

| 字段 | 说明 |
|------|------|
| `project_name` | 从文件名（不含扩展名）派生 |
| `source_name` | 原始文件名 |
| `source_path` | 文件绝对路径（归档后自动更新） |
| `sync_status` | `pending_cloud_upload` / `synced` / `failed` 等 |
| `notebook_id` | NotebookLM 云端 notebook UUID |
| `source_id` | NotebookLM 云端 source UUID |
| `source_fingerprint` | 基于路径、大小、修改时间的 SHA256 指纹（前 16 位） |
| `notes` | 状态备注或错误信息 |

---

## 在新机器上复刻

详见 [`REPLICATION-GUIDE.md`](notebooklm-intake/REPLICATION-GUIDE.md)，包含：
- 完整目录结构创建步骤
- 路径替换说明
- Smoke test 流程
- 复刻完成检查清单

---

## 参考来源

本项目基于 [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) 构建。

[notebooklm-py](https://github.com/teng-lin/notebooklm-py) 提供了通过 Python 和 CLI 与 NotebookLM 云端通信的能力，包括认证、创建 notebook、上传 source、查询列表等核心操作。`notebooklm-intake` 的整个上传链路均依赖该项目提供的接口。

---

## 当前状态

MVP 已完成，真实云端上传链路已跑通并通过 smoke test 和真实业务测试。
