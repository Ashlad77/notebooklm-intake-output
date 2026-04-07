# notebooklm-intake-output

**[English](README_EN.md)** | 中文

把本地资料批量同步到 [NotebookLM](https://notebooklm.google.com/) 云端，并从云端项目生成多种输出（报告、测验、思维导图、音频、视频等），全部通过本地脚本自动完成。

> 本项目基于 [@teng-lin](https://github.com/teng-lin) 的 [notebooklm-py](https://github.com/teng-lin/notebooklm-py) 构建。该项目提供了 NotebookLM 的非官方 Python API 与 CLI，intake 和 output 的整个云端通信链路均依赖其接口。

---

## 简介

本仓库包含两个面向 [OpenClaw](https://github.com/Ashlad77) 的 skill：

| Skill | 用途 |
|-------|------|
| **notebooklm-intake** | 本地文件 → NotebookLM 云端（上传、建项目、去重、归档） |
| **notebooklm-output** | NotebookLM 云端 → 本地文件（生成报告、测验、音频等并下载） |

两个 skill 组成完整闭环：先用 intake 把资料入库，再用 output 从云端生成各种输出。

---

## 前置条件

1. **Python 3.10+**
2. **Tkinter** — Windows 默认自带；Linux 可能需要 `sudo apt install python3-tk`
3. **`notebooklm-py` CLI** 已安装并完成认证：

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
notebooklm login
```

> 中国大陆用户需要网络代理才能访问 Google 服务。
> 如需使用 Microsoft Edge SSO 登录，可用 `notebooklm login --browser msedge`。

4. 验证连接：

```bash
notebooklm list
```

正常返回 notebook 列表（空列表也算成功）即表示对接完成。

---

## 目录结构

```
~/.openclaw/
├── skills/
│   ├── notebooklm-intake/
│   │   ├── SKILL.md              ← skill 指令（中文）
│   │   ├── SKILL_EN.md           ← skill 指令（英文）
│   │   ├── REPLICATION-GUIDE.md  ← 复刻指南（中文）
│   │   ├── REPLICATION-GUIDE_EN.md ← 复刻指南（英文）
│   │   └── scripts/
│   │       └── intake.py         ← 入库核心脚本
│   └── notebooklm-output/
│       ├── SKILL.md              ← skill 指令（中文）
│       ├── SKILL_EN.md           ← skill 指令（英文）
│       ├── REPLICATION-GUIDE.md  ← 复刻指南（中文）
│       ├── REPLICATION-GUIDE_EN.md ← 复刻指南（英文）
│       └── scripts/
│           ├── output.py         ← 输出核心脚本
│           └── vendor/
│               ├── d3.min.js     ← D3.js（mind-map 渲染依赖）
│               └── markmap-view.min.js ← Markmap（mind-map 渲染依赖）
└── knowledge/
    └── notebooklm/
        ├── inbox/                ← 待上传资料放这里
        ├── processed/            ← 上传成功后自动归档
        ├── projects/             ← 每个项目的本地 metadata
        ├── output/               ← 所有输出文件的根目录
        └── registry.json         ← 总索引
```

> 脚本会根据自身位置自动检测 `.openclaw` 根目录，无需手动配置路径。也可通过环境变量 `OPENCLAW_HOME` 覆盖。

---

# notebooklm-intake

## 功能

- 扫描 `inbox/` 目录（或指定路径）中的待上传资料
- 自动在云端创建同名 Notebook（已存在则复用）
- 自动上传 Source，回写 `notebook_id`、`source_id`、`sync_status` 到本地
- 支持批量处理，文件间自动节流
- 本地 + 云端双重去重，防止重复上传
- 自动重试（最多 3 次，退避递增），失败分类报告
- 成功上传后自动归档到 `processed/`
- 输出结构化 JSON summary，便于追踪和排错

## 快速开始

### 批量入库（扫描整个 inbox）

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py
```

### 指定单个文件或目录

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py --path "<文件或目录路径>"
```

### 确认归档重复内容

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py --archive-duplicates
```

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

## 支持的文件类型

| 类型 | 扩展名 |
|------|--------|
| 文档 | `.pdf` `.txt` `.md` `.doc` `.docx` |
| 表格 | `.xls` `.xlsx` `.csv` `.tsv` |
| 音频 | `.mp3` `.wav` `.m4a` |
| 视频 | `.mp4` `.mov` `.avi` |
| 链接/网页 | `.url` `.webloc` `.html` |

## 错误处理

| 错误类型 | 行为 |
|----------|------|
| `auth_error` | 立即停止所有后续处理，提示重新登录 |
| `notebook_conflict` | 云端存在多个同名 Notebook，报错等待人工介入 |
| `source_conflict` | 云端存在多个同名 Source，报错等待人工介入 |
| `source_upload_error` | 自动重试，最多 3 次 |
| `network_error` | 自动重试，最多 3 次 |
| `unknown_error` | 自动重试，最多 3 次 |

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

# notebooklm-output

## 功能

- 从本地项目索引匹配目标项目，校验云端同步状态
- 调用 NotebookLM 云端 API 生成 9 种输出类型
- 自动下载生成结果到本地统一输出目录
- JSON 类型（测验、抽认卡、思维导图）自动转译为**可交互的 HTML 文件**
- 弹出本地 GUI 进度窗口，实时展示任务状态
- 媒体类型（音频、视频）使用专用轮询下载策略，绕过 CLI 已知 bug
- **支持中英文双语界面**（`--language zh` / `--language en`）

## 支持的输出类型

| 输出类型 | 文件格式 | 说明 |
|---------|---------|------|
| `report` | `.md` | Markdown 报告 |
| `quiz` | `.json` → `.html` | 可交互测验（选择题、即时判分、解析） |
| `flashcards` | `.json` → `.html` | 可交互抽认卡（3D 翻卡、键盘快捷键） |
| `mind-map` | `.json` → `.html` | 可交互思维导图（Markmap 渲染，展开/收起/缩放） |
| `data-table` | `.csv` | 结构化数据表 |
| `slide-deck` | `.pdf` | 幻灯片 |
| `infographic` | `.png` | 信息图 |
| `audio-overview` | `.mp3` | 音频总结（默认 brief 格式） |
| `video-overview` | `.mp4` | 视频总结 |

## 快速开始

### 查询项目

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py inspect --project "<项目名>"
```

### 生成输出（中文，默认）

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py generate --project "<项目名>" --type "<输出类型>"
```

### 生成输出（英文）

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py generate --project "<项目名>" --type "<输出类型>" --language en
```

`--language` 控制：GUI 界面语言、输出文件名标签、HTML 交互页面文本、云端生成内容的语言。

## 分离式任务流

脚本按输出类型自动选择不同的执行路径：

**非媒体类型**（report / quiz / flashcards / mind-map / data-table / slide-deck / infographic）：
1. 使用 `--wait` 提交生成任务（CLI 自行等待完成）
2. 直接下载产物
3. JSON 类型自动转译为可交互 HTML

**媒体类型**（audio-overview / video-overview）：
1. 使用 `--no-wait` 提交（立即返回 task_id）
2. 先等 30 秒，然后每 15 秒尝试下载，直到成功或超时（15 分钟）

> 媒体类型完全绕过 `notebooklm artifact wait`，因为其内部 `_is_media_ready()` 对 video 存在已知 bug。

## GUI 进度窗口

执行生成任务时会自动弹出 Tkinter 进度窗口（620×320，置顶），实时展示：

- 项目名、输出类型
- 当前阶段、任务 ID
- 状态、保存路径
- 已耗时、错误信息

窗口语言随 `--language` 参数切换。任务完成后窗口自动关闭（成功延迟 5 秒，失败延迟 8 秒）。

## JSON → HTML 自动转译

`quiz`、`flashcards`、`mind-map` 三种类型在下载 JSON 后会自动转译为可交互 HTML：

| 类型 | HTML 特性 |
|------|----------|
| quiz | 多选题界面、即时判对错、显示正确答案和解析、计分、重做 |
| flashcards | 3D 翻卡效果、键盘快捷键（空格翻面、方向键切换）、进度显示 |
| mind-map | Markmap 交互式树图、展开/收起/适应窗口、完全离线可用 |

mind-map 的 HTML 内联了 D3.js 和 Markmap 库，生成的文件**完全自包含**，无需网络即可打开。HTML 页面的按钮文字也随 `--language` 切换中英文。

## 超时配置

| 类型 | 超时时间 |
|------|---------|
| 媒体类型（audio/video） | 900 秒（15 分钟） |
| 重型类型（slide-deck/infographic） | 600 秒（10 分钟） |
| 其他类型 | 300 秒（5 分钟） |

## 输出文件命名

```
{项目名}-{类型标签}-{YYYY-MM-DD_HH-MM}{扩展名}
```

- 中文（默认）：`我的项目-报告-2026-04-07_14-30.md`
- 英文（`--language en`）：`my-project-Report-2026-04-07_14-30.md`

---

## 在新机器上复刻

每个 skill 都有独立的复刻指南（中英双语），包含完整的文件内容、部署步骤和 Smoke test 流程：

- **intake**：[中文](notebooklm-intake/REPLICATION-GUIDE.md) | [English](notebooklm-intake/REPLICATION-GUIDE_EN.md)
- **output**：[中文](notebooklm-output/REPLICATION-GUIDE.md) | [English](notebooklm-output/REPLICATION-GUIDE_EN.md)

复刻顺序：**先 intake，再 output**（output 依赖 intake 创建的项目数据）。

> 脚本会自动检测部署路径，按标准目录结构放置即可，无需手动修改代码中的路径。

---

## 当前状态

两个 skill 均已完成 MVP，真实云端链路已跑通：

- **intake**：批量入库、去重、重试、归档全流程已通过真实业务测试
- **output**：全部 9 种输出类型已通过真实云端生成 + 下载测试

目前仅为个人测试通过的版本，如使用中遇到问题欢迎随时[提 Issue](../../issues)，会不定期更新和维护。

## 致谢 / Acknowledgements

- 本项目的 NotebookLM 云端通信能力基于  
  [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) 提供的非官方 Python API 与 CLI 实现。
- 部分与 NotebookLM 交互的实现思路和代码结构，参考并改写自该项目的相关模块，具体来源已在代码注释中标明。
- 感谢原作者 @teng-lin 对 NotebookLM 生态的探索与封装工作。

## 许可证

本项目使用 [MIT License](LICENSE) 开源。
