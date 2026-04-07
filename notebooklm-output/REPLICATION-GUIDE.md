# notebooklm-output Skill 完整复刻指南

本文档供 OpenClaw 实例阅读后一比一复刻 `notebooklm-output` skill。请严格按照以下结构、路径、文件内容创建。

---

## 0. 前置条件

在开始之前，目标机器需要满足：

1. **Python 3.10+** 已安装且可在命令行中调用
2. **Tkinter 可用** — Python 默认自带，Windows 无需额外安装；Linux 可能需要 `sudo apt install python3-tk`
3. **`notebooklm-py` CLI 已安装并完成认证**（详见下方对接说明）
4. **`notebooklm-intake` skill 已部署** — output 依赖 intake 先把项目同步到云端
5. **OpenClaw 目录结构存在** — 即 `~/.openclaw/` 已初始化

### 0.1 对接 NotebookLM 云端

本 skill 依赖 `notebooklm-py` 项目（来源：https://github.com/teng-lin/notebooklm-py ）提供的 CLI 与 NotebookLM 云端通信。以下是从零开始的完整对接流程：

**Step 1：安装 notebooklm-py（含浏览器登录支持）**

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
```

- 第一行安装 CLI 工具及浏览器认证模块
- 第二行安装 Playwright 需要的 Chromium 内核（login 必需）
- 基础依赖 `click`、`httpx`、`rich` 会自动安装

**Step 2：登录认证**

```bash
notebooklm login
```

- 会通过 Playwright 打开 Chromium 浏览器，进入 Google 账号登录页面
- 登录完成后，回到终端按 **Enter** 保存认证
- 认证凭证保存在 `~/.notebooklm/storage_state.json`
- 需要能访问 Google 服务（中国大陆用户需要网络代理）

如果你的组织要求使用 Microsoft Edge 进行 SSO 登录：

```bash
notebooklm login --browser msedge
```

**Step 3：验证连接**

```bash
notebooklm list
```

正常返回 notebook 列表（空列表也算成功）即表示对接完成。

如果遇到认证问题，可以运行诊断：

```bash
notebooklm auth check --test
```

**补充说明**：
- 认证有有效期，过期后重新执行 `notebooklm login` 即可
- 也支持通过环境变量 `NOTEBOOKLM_AUTH_JSON` 使用文件认证（适合无浏览器的服务器环境）

---

## 1. 目录结构总览

需要创建以下目录和文件（以 `OPENCLAW_HOME` 代指用户的 `.openclaw` 根目录）：

```
OPENCLAW_HOME/
├── skills/
│   └── notebooklm-output/
│       ├── .claude/
│       │   └── settings.local.json
│       ├── SKILL.md
│       ├── USAGE-AND-STATUS.md
│       └── scripts/
│           ├── output.py
│           └── vendor/
│               ├── d3.min.js          ← D3.js 可视化库（mind-map 渲染依赖）
│               └── markmap-view.min.js ← Markmap 库（mind-map 渲染依赖）
└── knowledge/
    └── notebooklm/
        ├── projects/       ← 每个项目的 metadata（由 intake skill 创建）
        ├── output/         ← 所有输出文件的根目录
        └── registry.json   ← 总索引（由 intake skill 创建和维护）
```

**注意**：`scripts/output.py` 已改为自动检测路径（基于脚本位置推算 `.openclaw` 根目录），无需手动修改 `KNOWLEDGE_ROOT`。只要按上述目录结构部署到 `~/.openclaw/` 下即可。`SKILL.md` 中的路径也已使用 `<OPENCLAW_HOME>` 占位符，无需替换。

---

## 2. 文件内容 — 逐文件创建

### 2.1 `SKILL.md`

路径：`OPENCLAW_HOME/skills/notebooklm-output/SKILL.md`

```markdown
---
name: notebooklm-output
description: 基于云端已有 NotebookLM 项目生成、导出并下载结果。用于当用户说"生成 NotebookLM 某项目内容""导出 notebooklm 某项目结果""输出/制作/产出某个 NotebookLM 项目的思维导图、报告、表格、音频、视频、卡片、测验"等场景时触发。默认把这类请求理解为云端项目输出，先按项目名匹配 registry 中的云端 metadata，再告知支持的输出类型并调用脚本生成最终文件。
---

# NotebookLM 输出

## 固定目录

- 项目目录：`OPENCLAW_HOME/knowledge/notebooklm/projects`
- 输出目录：`OPENCLAW_HOME/knowledge/notebooklm/output`
- 状态索引：`OPENCLAW_HOME/knowledge/notebooklm/registry.json`

## 执行原则

1. 默认把"生成 / 制作 / 产出 / 导出 / 输出 NotebookLM 某项目内容"理解为**云端已有项目输出**，优先走本 skill，不要误判成 intake。
2. 用户给出项目名后，先运行脚本查找匹配项目。
3. 必须先告诉用户该项目当前支持哪些输出类型，再询问要哪一种；若用户需求已经明确对应某一种类型，也应先完成项目确认，再继续执行。
4. 用户确认类型后，再调用生成脚本。
5. 输出语言默认优先中文；**仅对 CLI 实际支持 `--language` 的输出类型**，才通过脚本显式传入中文（`zh_Hans`）。对不支持语言参数的类型，不要强塞 `--language`。
6. 只交付**最终文件**；如果脚本或 skill 有问题，先修复再正式生成。不要为了兜底而走底层直出，不要把排障用的中间产物落盘交付给用户。
7. 执行导出任务时，脚本会弹出本地 GUI 进度窗口，每 5 秒刷新一次，展示项目名、输出类型、任务状态、任务 ID、耗时、保存路径或错误信息。
8. 如果当前阶段尚未接通真实云端生成能力，允许输出能力清单与本地路径规划，但不能谎称已从云端生成成功。

## 标准命令

查询项目：

```
python OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py inspect --project "<项目名>"
```

执行输出：

```
python OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py generate --project "<项目名>" --type "<输出类型>"
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
```

> **注意**：上面的 `OPENCLAW_HOME` 占位符需要在创建文件时替换为目标用户的真实绝对路径。

---

### 2.2 `.claude/settings.local.json`

路径：`OPENCLAW_HOME/skills/notebooklm-output/.claude/settings.local.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(notebooklm generate:*)",
      "Bash(notebooklm download:*)",
      "Bash(pip show:*)",
      "Bash(notebooklm artifact:*)",
      "Bash(python:*)",
      "Bash(wc:*)"
    ]
  }
}
```

---

### 2.3 `scripts/output.py`

路径：`OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py`

这是核心脚本（约 1018 行），**必须完整复制，不可省略任何部分**。

```python
from __future__ import annotations

import argparse
import json
import queue
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import re

KNOWLEDGE_ROOT = Path(r"OPENCLAW_HOME/knowledge")  # ← 替换为目标用户的实际路径
REGISTRY_PATH = KNOWLEDGE_ROOT / "notebooklm" / "registry.json"
DEFAULT_TYPES = [
    "audio-overview",
    "video-overview",
    "slide-deck",
    "quiz",
    "flashcards",
    "infographic",
    "report",
    "mind-map",
    "data-table",
]
DEFAULT_LANGUAGE = "zh_Hans"
GUI_REFRESH_SECONDS = 5

# ---------- 媒体类型需要更长等待，且用分离式提交+等待 ----------
MEDIA_TYPES = {"audio-overview", "video-overview"}
MEDIA_WAIT_TIMEOUT = 900   # 15 分钟
HEAVY_TYPES = {"slide-deck", "infographic"}
HEAVY_WAIT_TIMEOUT = 600   # 10 分钟
DEFAULT_WAIT_TIMEOUT = 300  # 5 分钟

# ---------- generate 参数映射 ----------
# 只有 CLI 真正支持的类型才附带 --language / --wait，避免子命令参数不兼容
GENERATE_TYPE_MAP: dict[str, tuple[str, list[str]]] = {
    "audio-overview": ("audio",      ["--format", "brief", "--language", DEFAULT_LANGUAGE]),
    "video-overview": ("video",      ["--format", "brief", "--language", DEFAULT_LANGUAGE]),
    "slide-deck":     ("slide-deck", ["--language", DEFAULT_LANGUAGE]),
    "quiz":           ("quiz",       []),
    "flashcards":     ("flashcards", []),
    "infographic":    ("infographic",["--language", DEFAULT_LANGUAGE]),
    "report":         ("report",     ["--format", "briefing-doc", "--language", DEFAULT_LANGUAGE]),
    "mind-map":       ("mind-map",   []),
    "data-table":     ("data-table", ["summarize the uploaded material into a structured table"]),
}

DOWNLOAD_TYPE_MAP: dict[str, tuple[str, str, list[str]]] = {
    "audio-overview": ("audio",      ".mp3", ["--latest", "--force"]),
    "video-overview": ("video",      ".mp4", ["--latest", "--force"]),
    "slide-deck":     ("slide-deck", ".pdf", ["--latest", "--force"]),
    "quiz":           ("quiz",       ".json", ["--format", "json"]),
    "flashcards":     ("flashcards", ".json", ["--format", "json"]),
    "infographic":    ("infographic",".png", ["--latest", "--force"]),
    "report":         ("report",     ".md",  ["--latest", "--force"]),
    "mind-map":       ("mind-map",   ".json",["--latest", "--force"]),
    "data-table":     ("data-table", ".csv", ["--latest", "--force"]),
}

TYPE_LABELS: dict[str, str] = {
    "report": "报告",
    "quiz": "测验",
    "flashcards": "抽认卡",
    "mind-map": "脑图",
    "infographic": "信息图",
    "audio-overview": "音频总结",
    "video-overview": "视频总结",
    "slide-deck": "幻灯片",
    "data-table": "数据表",
}


def load_registry() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"projects": []}


def find_project(name: str, registry: dict[str, Any]) -> dict[str, Any] | None:
    lowered = name.strip().lower()
    for project in registry["projects"]:
        if project["project_name"].lower() == lowered or project["source_name"].lower() == lowered:
            return project
    for project in registry["projects"]:
        if lowered in project["project_name"].lower() or lowered in project["source_name"].lower():
            return project
    return None


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def human_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def _sanitize_filename(text: Any) -> str:
    text = "" if text is None else str(text)
    text = re.sub(r'[\\/:*?"<>|]+', "-", text)
    text = re.sub(r'\s+', " ", text).strip()
    text = text.rstrip(". ")
    return text or "未命名项目"


def build_output_filename(project_name: str, output_type: str, ext: str) -> str:
    safe_project = _sanitize_filename(project_name)
    type_label = TYPE_LABELS.get(output_type, output_type)
    safe_type = _sanitize_filename(type_label)
    return f"{safe_project}-{safe_type}-{human_stamp()}{ext}"


def _get_wait_timeout(output_type: str) -> int:
    """根据输出类型返回合理的等待超时秒数。"""
    if output_type in MEDIA_TYPES:
        return MEDIA_WAIT_TIMEOUT
    if output_type in HEAVY_TYPES:
        return HEAVY_WAIT_TIMEOUT
    return DEFAULT_WAIT_TIMEOUT


class ProgressWindow:
    def __init__(self, project: str, output_type: str):
        self.root = tk.Tk()
        self.root.title("NotebookLM 输出进度")
        self.root.geometry("620x320")
        self.root.attributes("-topmost", True)
        self.queue: queue.Queue[tuple[str, dict[str, str]]] = queue.Queue()
        self._start = time.time()

        self.project_var = tk.StringVar(value=project)
        self.type_var = tk.StringVar(value=output_type)
        self.phase_var = tk.StringVar(value="准备中")
        self.task_var = tk.StringVar(value="-")
        self.status_var = tk.StringVar(value="等待开始")
        self.path_var = tk.StringVar(value="-")
        self.elapsed_var = tk.StringVar(value="0 秒")
        self.error_var = tk.StringVar(value="-")

        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        rows = [
            ("项目", self.project_var),
            ("输出类型", self.type_var),
            ("当前阶段", self.phase_var),
            ("任务 ID", self.task_var),
            ("状态", self.status_var),
            ("保存路径", self.path_var),
            ("已耗时", self.elapsed_var),
            ("错误", self.error_var),
        ]
        for i, (label, var) in enumerate(rows):
            tk.Label(frame, text=f"{label}：", anchor="w").grid(row=i, column=0, sticky="nw", pady=4)
            tk.Label(frame, textvariable=var, anchor="w", justify="left", wraplength=460).grid(row=i, column=1, sticky="w", pady=4)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._closed = False
        self.root.after(250, self._drain_queue)
        self.root.after(1000, self._tick)

    def _on_close(self):
        self._closed = True
        self.root.destroy()

    def _tick(self):
        if self._closed:
            return
        elapsed = int(time.time() - self._start)
        self.elapsed_var.set(f"{elapsed} 秒")
        self.root.after(1000, self._tick)

    def _drain_queue(self):
        if self._closed:
            return
        try:
            while True:
                action, payload = self.queue.get_nowait()
                if action == "update":
                    if "phase" in payload:
                        self.phase_var.set(payload["phase"])
                    if "task_id" in payload:
                        self.task_var.set(payload["task_id"])
                    if "status" in payload:
                        self.status_var.set(payload["status"])
                    if "saved_to" in payload:
                        self.path_var.set(payload["saved_to"])
                    if "error" in payload:
                        self.error_var.set(payload["error"])
                elif action == "close":
                    delay_ms = int(payload.get("delay_ms", "3000"))
                    self.root.after(delay_ms, self._on_close)
        except queue.Empty:
            pass
        self.root.after(250, self._drain_queue)

    def update(self, **kwargs: str):
        self.queue.put(("update", {k: v for k, v in kwargs.items() if v is not None}))

    def close_later(self, delay_ms: int = 3000):
        self.queue.put(("close", {"delay_ms": str(delay_ms)}))

    def run(self):
        self.root.mainloop()


def run_notebooklm(*args: str, timeout: int | None = None) -> str:
    """运行 notebooklm CLI 命令，返回 stdout。"""
    cmd = ["notebooklm", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"命令超时（{timeout}秒）: {' '.join(cmd)}"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or result.stdout).strip()
            or f"NotebookLM command failed: {' '.join(cmd)}"
        )
    return result.stdout.strip()


def _parse_json_output(raw: str) -> dict[str, Any]:
    """尝试从 CLI 输出中解析 JSON（可能前面有非 JSON 文本）。"""
    # 先整体尝试
    try:
        return json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # 逐行找第一行以 { 开头的
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
    return {}


def inspect(project_name: str) -> None:
    registry = load_registry()
    project = find_project(project_name, registry)
    print(json.dumps({
        "found": bool(project),
        "project": project,
        "supported_output_types": DEFAULT_TYPES if project else [],
    }, ensure_ascii=False, indent=2))


# ==================== 核心：分离式任务流 ====================


WAIT_SUPPORTED_TYPES = {
    "audio-overview",
    "video-overview",
    "slide-deck",
    "quiz",
    "flashcards",
    "infographic",
    "report",
    "data-table",
}


def _submit_generation(
    notebook_id: str,
    output_type: str,
    progress: ProgressWindow,
) -> str | None:
    """
    阶段 1：提交生成任务，返回 task_id（可能为 None）。
    仅在 CLI 支持时附带 --wait / --no-wait；不支持的子命令（如 mind-map）避免传入。
    """
    generate_cmd, generate_extra = GENERATE_TYPE_MAP[output_type]

    use_wait = output_type in WAIT_SUPPORTED_TYPES and output_type not in MEDIA_TYPES
    use_no_wait = output_type in WAIT_SUPPORTED_TYPES and output_type in MEDIA_TYPES
    timeout_sec = _get_wait_timeout(output_type) + 60  # subprocess 超时比 CLI 超时多留余量

    cmd_args = ["generate", generate_cmd, *generate_extra]
    if use_wait:
        cmd_args.append("--wait")
    elif use_no_wait:
        cmd_args.append("--no-wait")
    cmd_args.append("--json")

    progress.update(
        phase="任务已提交，云端开始生成",
        status="submitting",
        error="正在等待 CLI 返回任务信息…"
    )

    raw = run_notebooklm(
        *cmd_args,
        timeout=timeout_sec,
    )

    task_info = _parse_json_output(raw)
    task_id = task_info.get("task_id") or task_info.get("artifact_id")
    status = task_info.get("status", "unknown")

    if task_id:
        progress.update(phase="生成中", task_id=task_id, status=status, error="-")
    else:
        progress.update(
            phase="任务已提交",
            status="submitted_no_task_id",
            error="CLI 未返回 task_id，将尝试直接下载最新产物"
        )

    # 如果用了 --wait 且 CLI 返回 completed，说明已经完成
    if use_wait and status == "completed":
        return task_id

    return task_id


def _wait_for_completion(
    notebook_id: str,
    task_id: str,
    output_type: str,
    progress: ProgressWindow,
) -> str:
    """
    阶段 2：等待任务完成。
    - 非媒体类型：使用 `notebooklm artifact wait`（可靠）
    - 媒体类型：不使用 artifact wait（其内部 _is_media_ready 对 video
      可能永远返回 False），改为由调用方在 _wait_and_download_media 处理
    """
    timeout = _get_wait_timeout(output_type)

    progress.update(
        phase="生成中（等待云端完成）",
        task_id=task_id,
        status="waiting",
        error=f"超时阈值 {timeout} 秒"
    )

    try:
        raw = run_notebooklm(
            "artifact", "wait", task_id,
            "-n", notebook_id,
            "--timeout", str(timeout),
            "--json",
            timeout=timeout + 60,
        )
        info = _parse_json_output(raw)
        final_status = info.get("status", "unknown")
        progress.update(
            phase="生成完成" if final_status == "completed" else f"生成结束（{final_status}）",
            status=final_status,
            error=info.get("error") or "-"
        )
        return final_status
    except RuntimeError as exc:
        err_msg = str(exc)
        if "超时" in err_msg or "timeout" in err_msg.lower():
            progress.update(
                phase="等待超时",
                status="timeout",
                error=f"本地等待超过 {timeout} 秒，云端任务可能仍在进行"
            )
            return "timeout"
        raise


def _try_download(notebook_id: str, output_type: str, output_path: Path) -> bool:
    """尝试下载最新产物，成功返回 True，失败返回 False。"""
    download_cmd, _ext, download_extra = DOWNLOAD_TYPE_MAP[output_type]
    try:
        run_notebooklm(
            "download", download_cmd, *download_extra, str(output_path),
            "-n", notebook_id,
            timeout=120,
        )
        return output_path.exists() and output_path.stat().st_size > 0
    except RuntimeError:
        return False


MEDIA_POLL_INTERVAL = 15  # 媒体类型每 15 秒尝试一次下载

# ---------- JSON 类型需要下载后转译为可交互 HTML ----------
TEXT_CONVERTABLE = {"quiz", "flashcards", "mind-map"}


def _convert_json_to_html(json_path: Path, output_type: str) -> Path:
    """
    读取 json_path，将 quiz / flashcards / mind-map 转为可交互的 .html 文件。
    返回 HTML 文件路径（与原 JSON 同名但扩展名为 .html）。
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    output_path = json_path.with_suffix(".html")

    if output_type == "quiz":
        html = _render_quiz_html(data)
    elif output_type == "flashcards":
        html = _render_flashcards_html(data)
    elif output_type == "mind-map":
        html = _render_mindmap_html(data)
    else:
        return output_path

    output_path.write_text(html, encoding="utf-8")
    return output_path


def _html_escape(text: Any) -> str:
    """转义 HTML 特殊字符，兼容 None 和非字符串输入。"""
    if text is None:
        return ""
    text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# -------------------- quiz HTML --------------------

def _render_quiz_html(data: dict) -> str:
    title = _html_escape(data.get("title", "测验"))
    questions = data.get("questions", [])
    questions_json = json.dumps(questions, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: #f0f2f5; color: #333; line-height: 1.6; padding: 20px; }}
.container {{ max-width: 800px; margin: 0 auto; }}
h1 {{ text-align: center; margin-bottom: 24px; font-size: 24px; color: #1a1a2e; }}
.summary {{ text-align: center; margin-bottom: 24px; padding: 16px; background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); display: none; }}
.summary .score {{ font-size: 36px; font-weight: bold; color: #16a34a; }}
.summary .detail {{ margin-top: 8px; color: #666; }}
.question-card {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.question-num {{ font-size: 13px; color: #888; margin-bottom: 8px; }}
.question-text {{ font-size: 17px; font-weight: 600; margin-bottom: 16px; }}
.options {{ list-style: none; }}
.option {{ display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; margin-bottom: 8px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.15s; }}
.option:hover {{ border-color: #93c5fd; background: #eff6ff; }}
.option.selected {{ border-color: #3b82f6; background: #eff6ff; }}
.option.correct {{ border-color: #16a34a; background: #f0fdf4; }}
.option.wrong {{ border-color: #dc2626; background: #fef2f2; }}
.option.disabled {{ pointer-events: none; }}
.option .marker {{ width: 22px; height: 22px; border-radius: 50%; border: 2px solid #d1d5db; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; margin-top: 2px; }}
.option.selected .marker {{ border-color: #3b82f6; background: #3b82f6; color: #fff; }}
.option.correct .marker {{ border-color: #16a34a; background: #16a34a; color: #fff; }}
.option.wrong .marker {{ border-color: #dc2626; background: #dc2626; color: #fff; }}
.feedback {{ margin-top: 12px; padding: 12px 14px; border-radius: 8px; display: none; font-size: 14px; line-height: 1.6; }}
.feedback.show {{ display: block; }}
.feedback.correct {{ background: #f0fdf4; border-left: 4px solid #16a34a; }}
.feedback.wrong {{ background: #fef2f2; border-left: 4px solid #dc2626; }}
.feedback .hint {{ color: #b45309; margin-bottom: 6px; }}
.feedback .rationale {{ color: #555; }}
.btn-row {{ text-align: center; margin-top: 24px; }}
.btn {{ display: inline-block; padding: 12px 32px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.15s; }}
.btn-primary {{ background: #3b82f6; color: #fff; }}
.btn-primary:hover {{ background: #2563eb; }}
.btn-reset {{ background: #e5e7eb; color: #333; margin-left: 12px; }}
.btn-reset:hover {{ background: #d1d5db; }}
</style>
</head>
<body>
<div class="container">
<h1>{title}</h1>
<div class="summary" id="summary">
  <div class="score" id="score"></div>
  <div class="detail" id="detail"></div>
</div>
<div id="questions"></div>
<div class="btn-row">
  <button class="btn btn-primary" id="submitBtn" onclick="submitAll()">提交全部答案</button>
  <button class="btn btn-reset" id="resetBtn" onclick="resetAll()" style="display:none">重新答题</button>
</div>
</div>
<script>
const questions = {questions_json};
let submitted = false;
const container = document.getElementById("questions");

questions.forEach((q, qi) => {{
  const card = document.createElement("div");
  card.className = "question-card";
  card.id = "q" + qi;

  let optionsHtml = "";
  q.answerOptions.forEach((opt, oi) => {{
    const label = String.fromCharCode(65 + oi);
    optionsHtml += '<div class="option" data-q="' + qi + '" data-o="' + oi + '" onclick="selectOption(this)">' +
      '<span class="marker">' + label + '</span>' +
      '<span>' + escapeHtml(opt.text) + '</span></div>';
  }});

  const correctIdx = q.answerOptions.findIndex(o => o.isCorrect);
  const correctLabel = String.fromCharCode(65 + correctIdx);
  const correctRationale = q.answerOptions[correctIdx] ? q.answerOptions[correctIdx].rationale || "" : "";

  card.innerHTML =
    '<div class="question-num">第 ' + (qi + 1) + ' / ' + questions.length + ' 题</div>' +
    '<div class="question-text">' + escapeHtml(q.question) + '</div>' +
    '<div class="options">' + optionsHtml + '</div>' +
    '<div class="feedback" id="fb' + qi + '">' +
      (q.hint ? '<div class="hint">💡 提示：' + escapeHtml(q.hint) + '</div>' : '') +
      '<div class="rationale">✅ 正确答案：' + correctLabel + '。' + escapeHtml(correctRationale) + '</div>' +
    '</div>';

  container.appendChild(card);
}});

function escapeHtml(t) {{
  const d = document.createElement("div");
  d.textContent = t;
  return d.innerHTML;
}}

function selectOption(el) {{
  if (submitted) return;
  const qi = el.dataset.q;
  document.querySelectorAll('.option[data-q="' + qi + '"]').forEach(o => o.classList.remove("selected"));
  el.classList.add("selected");
}}

function submitAll() {{
  submitted = true;
  let correct = 0;
  questions.forEach((q, qi) => {{
    const selected = document.querySelector('.option[data-q="' + qi + '"].selected');
    const fb = document.getElementById("fb" + qi);
    const options = document.querySelectorAll('.option[data-q="' + qi + '"]');
    options.forEach(o => o.classList.add("disabled"));

    const correctIdx = q.answerOptions.findIndex(o => o.isCorrect);

    if (selected) {{
      const oi = parseInt(selected.dataset.o);
      if (oi === correctIdx) {{
        selected.classList.add("correct");
        fb.className = "feedback show correct";
        correct++;
      }} else {{
        selected.classList.add("wrong");
        options[correctIdx].classList.add("correct");
        fb.className = "feedback show wrong";

        const selectedRationale = q.answerOptions[oi].rationale || "";
        if (selectedRationale) {{
          const wrongNote = document.createElement("div");
          wrongNote.className = "wrong-rationale";
          wrongNote.style.color = "#dc2626";
          wrongNote.style.fontSize = "14px";
          wrongNote.style.lineHeight = "1.6";
          wrongNote.innerHTML = "❌ 你选的 " + String.fromCharCode(65 + oi) + "：" + escapeHtml(selectedRationale);
          fb.insertBefore(wrongNote, fb.firstChild.nextSibling || null);
        }}
      }}
    }} else {{
      options[correctIdx].classList.add("correct");
      fb.className = "feedback show wrong";
    }}
  }});

  const summary = document.getElementById("summary");
  document.getElementById("score").textContent = correct + " / " + questions.length;
  document.getElementById("detail").textContent =
    "正确率 " + Math.round(correct / questions.length * 100) + "%";
  summary.style.display = "block";
  document.getElementById("submitBtn").style.display = "none";
  document.getElementById("resetBtn").style.display = "inline-block";
  window.scrollTo({{ top: 0, behavior: "smooth" }});
}}

function resetAll() {{
  submitted = false;
  document.querySelectorAll(".option").forEach(o => {{
    o.classList.remove("selected", "correct", "wrong", "disabled");
  }});
  document.querySelectorAll(".feedback").forEach(f => {{
    f.className = "feedback";
    f.querySelectorAll(".wrong-rationale").forEach(r => r.remove());
  }});
  document.getElementById("summary").style.display = "none";
  document.getElementById("submitBtn").style.display = "inline-block";
  document.getElementById("resetBtn").style.display = "none";
}}
</script>
</body>
</html>"""


# -------------------- flashcards HTML --------------------

def _render_flashcards_html(data: dict) -> str:
    title = _html_escape(data.get("title", "抽认卡"))
    cards = data.get("cards", [])
    cards_json = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: #f0f2f5; color: #333; line-height: 1.6; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
h1 {{ margin-bottom: 16px; font-size: 22px; color: #1a1a2e; }}
.progress {{ margin-bottom: 20px; font-size: 15px; color: #666; }}
.card-wrapper {{ perspective: 800px; width: 100%; max-width: 560px; height: 320px; cursor: pointer; margin-bottom: 24px; }}
.card {{ width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.5s; }}
.card.flipped {{ transform: rotateY(180deg); }}
.card-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px; text-align: center; }}
.card-front {{ background: #fff; }}
.card-back {{ background: #e0f2fe; transform: rotateY(180deg); }}
.card-label {{ font-size: 12px; color: #999; position: absolute; top: 16px; left: 20px; }}
.card-text {{ font-size: 18px; line-height: 1.7; }}
.controls {{ display: flex; gap: 12px; align-items: center; }}
.btn {{ padding: 10px 28px; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.15s; }}
.btn-nav {{ background: #e5e7eb; color: #333; }}
.btn-nav:hover {{ background: #d1d5db; }}
.btn-nav:disabled {{ opacity: 0.4; cursor: default; }}
.btn-flip {{ background: #3b82f6; color: #fff; }}
.btn-flip:hover {{ background: #2563eb; }}
.tip {{ margin-top: 16px; font-size: 13px; color: #aaa; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="progress" id="progress"></div>
<div class="card-wrapper" id="cardWrapper" onclick="flipCard()">
  <div class="card" id="card">
    <div class="card-face card-front">
      <span class="card-label">正面</span>
      <div class="card-text" id="frontText"></div>
    </div>
    <div class="card-face card-back">
      <span class="card-label">背面</span>
      <div class="card-text" id="backText"></div>
    </div>
  </div>
</div>
<div class="controls">
  <button class="btn btn-nav" id="prevBtn" onclick="prev()">&#9664; 上一张</button>
  <button class="btn btn-flip" onclick="flipCard()">翻面</button>
  <button class="btn btn-nav" id="nextBtn" onclick="next()">下一张 &#9654;</button>
</div>
<div class="tip">点击卡片或按空格键翻面，按左右方向键切换</div>
<script>
const cards = {cards_json};
let idx = 0;
let flipped = false;

function render() {{
  const c = cards[idx];
  document.getElementById("frontText").textContent = c.front;
  document.getElementById("backText").textContent = c.back;
  document.getElementById("progress").textContent = (idx + 1) + " / " + cards.length;
  document.getElementById("prevBtn").disabled = idx === 0;
  document.getElementById("nextBtn").disabled = idx === cards.length - 1;
  flipped = false;
  document.getElementById("card").classList.remove("flipped");
}}

function flipCard() {{
  flipped = !flipped;
  document.getElementById("card").classList.toggle("flipped", flipped);
}}

function prev() {{ if (idx > 0) {{ idx--; render(); }} }}
function next() {{ if (idx < cards.length - 1) {{ idx++; render(); }} }}

document.addEventListener("keydown", e => {{
  if (e.key === " " || e.key === "Enter") {{ e.preventDefault(); flipCard(); }}
  else if (e.key === "ArrowLeft") prev();
  else if (e.key === "ArrowRight") next();
}});

render();
</script>
</body>
</html>"""


# -------------------- mind-map HTML (markmap) --------------------

VENDOR_DIR = Path(__file__).parent / "vendor"


def _render_mindmap_html(data: dict) -> str:
    title = _html_escape(data.get("name", "思维导图"))
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    # 读取内联的 vendor JS
    d3_js = (VENDOR_DIR / "d3.min.js").read_text(encoding="utf-8")
    markmap_js = (VENDOR_DIR / "markmap-view.min.js").read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: #f0f2f5; }}
.header {{ text-align: center; padding: 16px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
.header h1 {{ font-size: 20px; color: #1a1a2e; }}
.toolbar {{ margin-top: 8px; }}
.toolbar button {{ padding: 5px 14px; margin: 0 4px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }}
.toolbar button:hover {{ background: #f3f4f6; }}
svg#markmap {{ width: 100vw; height: calc(100vh - 72px); display: block; }}
</style>
<script>{d3_js}</script>
<script>{markmap_js}</script>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="toolbar">
    <button onclick="mm.fit()">适应窗口</button>
    <button onclick="expandAll()">全部展开</button>
    <button onclick="collapseAll()">全部收起</button>
  </div>
</div>
<svg id="markmap"></svg>
<script>
const sourceData = {data_json};

function convert(node) {{
  const result = {{ content: node.name, children: [] }};
  if (node.children) {{
    result.children = node.children.map(convert);
  }}
  return result;
}}

const root = convert(sourceData);
const {{ Markmap }} = window.markmap;
const mm = Markmap.create('#markmap', {{
  autoFit: true,
  duration: 300,
  maxWidth: 240,
  paddingX: 16,
}}, root);

function setPayload(node, fold) {{
  if (node.children && node.children.length > 0) {{
    node.payload = node.payload || {{}};
    node.payload.fold = fold;
    node.children.forEach(c => setPayload(c, fold));
  }}
}}

function expandAll() {{
  setPayload(root, 0);
  mm.setData(root);
  setTimeout(() => mm.fit(), 350);
}}

function collapseAll() {{
  if (root.children) {{
    root.children.forEach(child => {{
      setPayload(child, 1);
    }});
  }}
  mm.setData(root);
  setTimeout(() => mm.fit(), 350);
}}
</script>
</body>
</html>"""



def _wait_and_download_media(
    notebook_id: str,
    task_id: str | None,
    output_type: str,
    output_path: Path,
    progress: ProgressWindow,
) -> str:
    """
    媒体类型（audio/video）专用：轮询 + 尝试下载。
    绕过 notebooklm-py 的 _is_media_ready 检查问题。
    """
    timeout = _get_wait_timeout(output_type)
    start = time.time()

    progress.update(
        phase="云端生成中，等待产物就绪",
        task_id=task_id or "-",
        status="polling",
        error=f"每 {MEDIA_POLL_INTERVAL} 秒尝试下载，超时 {timeout} 秒"
    )

    # 先等一段时间让云端有时间生成
    initial_wait = 30
    progress.update(
        phase=f"云端生成中，{initial_wait} 秒后开始检查",
        status="initial_wait",
    )
    time.sleep(initial_wait)

    attempt = 0
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            progress.update(
                phase="等待超时",
                status="timeout",
                error=f"超过 {timeout} 秒仍未下载成功"
            )
            return "timeout"

        attempt += 1
        remaining = int(timeout - elapsed)
        progress.update(
            phase=f"尝试下载（第 {attempt} 次）",
            status=f"attempt_{attempt}",
            error=f"剩余 {remaining} 秒"
        )

        if _try_download(notebook_id, output_type, output_path):
            progress.update(
                phase="已完成",
                status="completed",
                saved_to=str(output_path),
                error="-"
            )
            return "completed"

        progress.update(
            phase=f"产物尚未就绪，{MEDIA_POLL_INTERVAL} 秒后重试",
            status=f"waiting_retry_{attempt}",
            error=f"第 {attempt} 次下载未成功，云端可能仍在处理"
        )
        time.sleep(MEDIA_POLL_INTERVAL)


def _download_artifact(
    notebook_id: str,
    output_type: str,
    output_path: Path,
    progress: ProgressWindow,
) -> None:
    """阶段 3：下载产物到本地（非媒体类型使用）。"""
    download_cmd, _ext, download_extra = DOWNLOAD_TYPE_MAP[output_type]

    progress.update(phase="下载中", status="downloading", error="-")

    run_notebooklm(
        "download", download_cmd, *download_extra, str(output_path),
        "-n", notebook_id,
        timeout=120,
    )

    progress.update(
        phase="已完成",
        status="completed",
        saved_to=str(output_path),
        error="-"
    )


def _generate_worker(
    progress: ProgressWindow,
    result_holder: dict[str, Any],
    project: dict[str, Any],
    output_type: str,
    output_path: Path,
) -> None:
    """Worker 线程：按 提交→等待→下载 三阶段执行，通过 queue 更新 GUI。"""
    notebook_id = project["notebook_id"]

    try:
        # 0. 设置当前 notebook
        progress.update(phase="准备上下文", status="setting_notebook", error="-")
        run_notebooklm("use", notebook_id, timeout=30)

        # 1. 提交生成
        task_id = _submit_generation(notebook_id, output_type, progress)

        # 2. 等待 + 下载
        if output_type in MEDIA_TYPES:
            # 媒体类型：轮询 + 尝试下载（绕过 _is_media_ready 的 bug）
            final_status = _wait_and_download_media(
                notebook_id, task_id, output_type, output_path, progress
            )

            if final_status == "timeout":
                progress.update(
                    phase="超时未能下载",
                    status="timeout",
                    error="云端可能已完成但下载未成功，请在网页端确认后手动下载"
                )
                progress.close_later(delay_ms=8000)
                result_holder["error"] = f"Media download timed out for {output_type}"
                return

        else:
            # 非媒体类型：--wait 已经在 submit 阶段等完了，直接下载
            _download_artifact(notebook_id, output_type, output_path, progress)
            # quiz / flashcards / mind-map 下载后自动转译为可交互 HTML
            if output_type in TEXT_CONVERTABLE and output_path.exists() and output_path.suffix == ".json":
                try:
                    html_path = _convert_json_to_html(output_path, output_type)
                    output_path = html_path  # 主结果指向 HTML
                    progress.update(
                        phase="已转译为 HTML",
                        saved_to=str(html_path),
                        error="-"
                    )
                except Exception as exc:
                    progress.update(
                        phase="下载完成（转译失败）",
                        error=f"转译失败：{exc}"
                    )
            final_status = "completed"

        progress.close_later(delay_ms=5000)
        result_holder["result"] = {
            "project": project["project_name"],
            "notebook_id": notebook_id,
            "output_type": output_type,
            "saved_to": str(output_path),
            "cloud_status": project.get("sync_status"),
            "task_id": task_id or "-",
            "final_status": final_status,
        }

    except Exception as exc:
        progress.update(phase="失败", status="error", error=str(exc))
        progress.close_later(delay_ms=8000)  # 错误时多停留几秒让用户看到
        result_holder["error"] = str(exc)


def generate(project_name: str, output_type: str) -> None:
    registry = load_registry()
    project = find_project(project_name, registry)
    if not project:
        raise SystemExit(f"project not found: {project_name}")
    if output_type not in GENERATE_TYPE_MAP or output_type not in DOWNLOAD_TYPE_MAP:
        raise SystemExit(f"unsupported output type: {output_type}")
    if project.get("sync_status") != "synced" or not project.get("notebook_id"):
        raise SystemExit(f"project not synced to NotebookLM cloud: {project_name}")

    default_output_dir = KNOWLEDGE_ROOT / "notebooklm" / "output" / f"{project['project_name']}_output"
    output_dir = Path(project.get("output_dir") or str(default_output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    _generate_cmd, _generate_extra = GENERATE_TYPE_MAP[output_type]
    _download_cmd, ext, _download_extra = DOWNLOAD_TYPE_MAP[output_type]
    output_filename = build_output_filename(project["project_name"], output_type, ext)
    output_path = output_dir / output_filename

    progress = ProgressWindow(project["project_name"], output_type)
    result_holder: dict[str, Any] = {}

    worker = threading.Thread(
        target=_generate_worker,
        args=(progress, result_holder, project, output_type, output_path),
        daemon=True,
    )
    worker.start()

    # tkinter mainloop 必须在主线程运行（Windows 要求）
    progress.run()

    # GUI 关闭后等 worker 结束
    worker.join(timeout=10)

    if "error" in result_holder:
        raise RuntimeError(result_holder["error"])

    if "result" in result_holder:
        print(json.dumps(result_holder["result"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("--project", required=True)

    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--project", required=True)
    generate_parser.add_argument("--type", required=True)

    args = parser.parse_args()
    if args.command == "inspect":
        inspect(args.project)
    elif args.command == "generate":
        generate(args.project, args.type)


if __name__ == "__main__":
    main()
```

---

### 2.4 `scripts/vendor/d3.min.js`

路径：`OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/d3.min.js`

这是 D3.js 可视化库的压缩版（约 270KB），用于 mind-map 渲染。**不可手动编写**，需要从官方获取。

**获取方式（选择其一）：**

方式 A — 从 CDN 下载：
```bash
curl -o "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/d3.min.js" "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"
```

方式 B — 通过 npm 获取：
```bash
npm pack d3@7 && tar -xf d3-*.tgz && cp package/dist/d3.min.js "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/" && rm -rf package d3-*.tgz
```

---

### 2.5 `scripts/vendor/markmap-view.min.js`

路径：`OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/markmap-view.min.js`

这是 Markmap 思维导图渲染库的压缩版（约 60KB），用于将 JSON 结构化数据渲染为可交互的树形图。**不可手动编写**，需要从官方获取。

**获取方式（选择其一）：**

方式 A — 从 CDN 下载：
```bash
curl -o "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/markmap-view.min.js" "https://cdn.jsdelivr.net/npm/markmap-view@0.17/dist/browser/index.js"
```

方式 B — 通过 npm 获取：
```bash
npm pack markmap-view@0.17 && tar -xf markmap-view-*.tgz && cp package/dist/browser/index.js "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/markmap-view.min.js" && rm -rf package markmap-view-*.tgz
```

> **注意**：如果上述 CDN 版本号过期，可将 `@7` / `@0.17` 替换为最新版本号。只要 API 不发生破坏性变更，脚本即可正常运行。

---

### 2.6 `USAGE-AND-STATUS.md`

路径：`OPENCLAW_HOME/skills/notebooklm-output/USAGE-AND-STATUS.md`

这是状态说明文档，新复刻实例应根据自身实际状态更新。初始内容如下：

```markdown
# notebooklm-output 使用说明与当前状态

## 1. 这个 skill 是干什么的
`notebooklm-output` 用来基于本地 `NotebookLM` 项目映射，调用真实的 `notebooklm-py` CLI，从已经同步到 NotebookLM 云端的项目里生成输出，并把结果保存到本地。

目标闭环：
1. 从本地项目索引找到目标项目
2. 读取对应 `notebook_id`
3. 调用 `notebooklm generate ...`
4. 调用 `notebooklm download ...`
5. 把结果保存到本地输出目录

## 2. 依赖
- `notebooklm-intake` 先把项目同步到 NotebookLM 云端
- `registry.json` / `projects/<项目名>/project.json` 中已有 `sync_status = synced` 和 `notebook_id`
- 本机已完成 `notebooklm login`
- `notebooklm-py` CLI 可用（来源：teng-lin/notebooklm-py）

## 3. 使用命令

### 查询项目
```
python OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py inspect --project "<项目名>"
```

### 执行输出
```
python OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py generate --project "<项目名>" --type "<输出类型>"
```

## 4. 支持的输出类型
- `audio-overview`（音频总结，默认 brief 格式）
- `video-overview`（视频总结）
- `slide-deck`（幻灯片，PDF）
- `quiz`（测验，JSON → 可交互 HTML）
- `flashcards`（抽认卡，JSON → 可交互 HTML）
- `infographic`（信息图，PNG）
- `report`（报告，Markdown）
- `mind-map`（脑图，JSON → 可交互 HTML）
- `data-table`（数据表，CSV）

## 5. 当前状态
初次复刻，尚未进行 smoke test。请在创建完成后运行一次输出测试以验证链路。
```

> **注意**：上面的 `OPENCLAW_HOME` 占位符需要在创建文件时替换为目标用户的真实绝对路径。

---

## 3. 复刻执行步骤（给 OpenClaw 的操作清单）

请严格按以下顺序执行：

### Step 1：确定路径变量

确定目标用户的 `OPENCLAW_HOME` 绝对路径。例如：
- Windows: `C:\Users\<username>\.openclaw`
- macOS/Linux: `/home/<username>/.openclaw`

后续所有 `OPENCLAW_HOME` 均替换为此路径。

### Step 2：确认 intake skill 已就绪

本 skill 依赖 `notebooklm-intake` 提供的项目同步。确认以下条件满足：
- `OPENCLAW_HOME/skills/notebooklm-intake/` 已部署
- `OPENCLAW_HOME/knowledge/notebooklm/registry.json` 存在
- `OPENCLAW_HOME/knowledge/notebooklm/projects/` 目录存在

如果尚未部署 intake skill，请先按 `notebooklm-intake` 的 REPLICATION-GUIDE 完成部署。

### Step 3：创建目录结构

```bash
mkdir -p "OPENCLAW_HOME/skills/notebooklm-output/.claude"
mkdir -p "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/output"
```

### Step 4：创建文件

按第 2 节逐个创建以下文件（路径中的 `OPENCLAW_HOME` 替换为真实路径）：

1. `skills/notebooklm-output/SKILL.md` — 内容见 2.1
2. `skills/notebooklm-output/.claude/settings.local.json` — 内容见 2.2
3. `skills/notebooklm-output/scripts/output.py` — 内容见 2.3
4. `skills/notebooklm-output/scripts/vendor/d3.min.js` — 下载方式见 2.4
5. `skills/notebooklm-output/scripts/vendor/markmap-view.min.js` — 下载方式见 2.5
6. `skills/notebooklm-output/USAGE-AND-STATUS.md` — 内容见 2.6

### Step 5：路径替换

在以下文件中，将 `OPENCLAW_HOME` 占位符替换为目标用户的实际绝对路径：

| 文件 | 需替换位置 |
|------|-----------|
| `SKILL.md` | 所有目录路径（3 处）和命令路径（2 处） |
| `scripts/output.py` | 第 15 行 `KNOWLEDGE_ROOT = Path(r"...")` |
| `USAGE-AND-STATUS.md` | 所有出现的路径 |

**Windows 路径注意**：`output.py` 中使用 `Path(r"...")` raw string，反斜杠不需要转义。

### Step 6：下载 vendor 依赖

```bash
# D3.js
curl -o "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/d3.min.js" "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"

# Markmap
curl -o "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/markmap-view.min.js" "https://cdn.jsdelivr.net/npm/markmap-view@0.17/dist/browser/index.js"
```

验证下载成功：
```bash
# 两个文件均应有内容（d3 约 270KB，markmap 约 60KB）
wc -c "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/d3.min.js"
wc -c "OPENCLAW_HOME/skills/notebooklm-output/scripts/vendor/markmap-view.min.js"
```

### Step 7：验证 Python 语法

```bash
python -m py_compile "OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py"
```

无输出即表示语法正确。

### Step 8：Smoke Test

```bash
# 1. 先确认至少有一个已同步的项目
python "OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py" inspect --project "<已同步的项目名>"

# 2. 确认输出 JSON 中 found 为 true 且 project.sync_status 为 "synced"

# 3. 生成一个 report 类型的输出（耗时较短，适合测试）
python "OPENCLAW_HOME/skills/notebooklm-output/scripts/output.py" generate --project "<已同步的项目名>" --type "report"

# 4. 确认：
#    - GUI 进度窗口正常弹出
#    - 最终输出 JSON 中 final_status 为 "completed"
#    - saved_to 指向的文件存在且有内容
```

如果 smoke test 通过，更新 `USAGE-AND-STATUS.md` 中第 5 节的状态为"smoke test 已通过"。

---

## 4. 核心架构说明

### 4.1 信息流

```
用户请求
    ↓
inspect：查询 registry.json → 匹配项目 → 返回支持的输出类型
    ↓
用户选择输出类型
    ↓
generate：
  1. 从 registry 查找项目
  2. 校验项目已同步（sync_status = synced）
  3. 读取 notebook_id
  4. 通过 notebooklm CLI 提交生成任务
  5. 等待/轮询任务完成
  6. 下载结果文件
  7. JSON 类型（quiz/flashcards/mind-map）自动转译为可交互 HTML
  8. 返回最终文件路径
    ↓
GUI 进度窗口（实时反馈）
    ↓
输出文件保存到本地
```

### 4.2 分离式任务流 — 按类型分路径

脚本按输出类型分为两条执行路径：

**非媒体类型**（report / quiz / flashcards / mind-map / data-table / slide-deck / infographic）：
1. `_submit_generation()` — 使用 `--wait` 提交（CLI 自行等待完成）
2. `_download_artifact()` — 直接下载
3. JSON 类型自动转译为 HTML

**媒体类型**（audio-overview / video-overview）：
1. `_submit_generation()` — 使用 `--no-wait` 提交（立即返回 task_id）
2. `_wait_and_download_media()` — 先等 30 秒，然后每 15 秒尝试 `download --latest`，直到成功或超时（15 分钟）

**关键设计**：
- 媒体类型**完全绕过** `notebooklm artifact wait`（因为其内部 `_is_media_ready()` 对 video 有 bug）
- 改为直接尝试下载来判断产物是否就绪
- 所有 subprocess 调用都有 timeout 保护

### 4.3 输出类型参数映射

不同输出类型需要不同的 CLI 参数，脚本通过两个映射表实现：

**GENERATE_TYPE_MAP** — 生成参数：

| 输出类型 | CLI 子命令 | 附加参数 |
|---------|-----------|---------|
| audio-overview | `audio` | `--format brief --language zh_Hans` |
| video-overview | `video` | `--format brief --language zh_Hans` |
| slide-deck | `slide-deck` | `--language zh_Hans` |
| quiz | `quiz` | （无） |
| flashcards | `flashcards` | （无） |
| infographic | `infographic` | `--language zh_Hans` |
| report | `report` | `--format briefing-doc --language zh_Hans` |
| mind-map | `mind-map` | （无） |
| data-table | `data-table` | `summarize the uploaded material into a structured table` |

**DOWNLOAD_TYPE_MAP** — 下载参数：

| 输出类型 | CLI 子命令 | 文件扩展名 | 下载参数 |
|---------|-----------|-----------|---------|
| audio-overview | `audio` | `.mp3` | `--latest --force` |
| video-overview | `video` | `.mp4` | `--latest --force` |
| slide-deck | `slide-deck` | `.pdf` | `--latest --force` |
| quiz | `quiz` | `.json` | `--format json` |
| flashcards | `flashcards` | `.json` | `--format json` |
| infographic | `infographic` | `.png` | `--latest --force` |
| report | `report` | `.md` | `--latest --force` |
| mind-map | `mind-map` | `.json` | `--latest --force` |
| data-table | `data-table` | `.csv` | `--latest --force` |

### 4.4 JSON → HTML 自动转译

`quiz`、`flashcards`、`mind-map` 三种类型在下载 JSON 后，会自动转译为可交互的 HTML 文件：

| 类型 | HTML 特性 |
|------|----------|
| quiz | 多选题、即时判对错、显示正确答案和解析、计分、重做 |
| flashcards | 3D 翻卡、键盘快捷键（空格翻面、左右切换）、进度显示 |
| mind-map | Markmap 交互式树图、展开/收起/适应窗口按钮 |

mind-map 的 HTML 渲染依赖内联的 `d3.min.js` 和 `markmap-view.min.js`（从 vendor 目录读取并嵌入 HTML），因此生成的 HTML 文件是**完全自包含**的，无需网络即可打开。

### 4.5 GUI 进度窗口

- 使用 Tkinter 实现，620x320 像素，置顶显示
- 主线程运行 Tkinter mainloop（Windows 要求），工作逻辑在子线程执行
- 通过 `queue.Queue` 从子线程向 GUI 推送状态更新
- 每秒刷新耗时计数器
- 任务完成后自动延迟关闭（成功 5 秒，失败 8 秒）

### 4.6 项目匹配策略

1. **精确匹配**：按 `project_name` 或 `source_name` 精确匹配（不区分大小写）
2. **模糊匹配**：如果精确匹配无结果，回退到 `project_name` 或 `source_name` 包含搜索词

### 4.7 超时配置

| 类型 | 超时时间 |
|------|---------|
| 媒体类型（audio/video） | 900 秒（15 分钟） |
| 重型类型（slide-deck/infographic） | 600 秒（10 分钟） |
| 其他类型 | 300 秒（5 分钟） |

subprocess 调用的超时比上述阈值多 60 秒，避免 subprocess 先于 CLI 超时。

### 4.8 输出文件命名规则

```
{项目名}-{类型中文名}-{YYYY-MM-DD_HH-MM}{扩展名}
```

例如：`2026-04-04-论文写作项目-报告-2026-04-07_14-30.md`

文件名中的非法字符（`\ / : * ? " < > |`）会被替换为 `-`。

---

## 5. 关键常量

| 常量 | 值 | 说明 |
|------|----|------|
| `DEFAULT_LANGUAGE` | `"zh_Hans"` | 默认输出语言（简体中文） |
| `GUI_REFRESH_SECONDS` | 5 | GUI 刷新间隔 |
| `MEDIA_WAIT_TIMEOUT` | 900 | 媒体类型超时（秒） |
| `HEAVY_WAIT_TIMEOUT` | 600 | 重型类型超时（秒） |
| `DEFAULT_WAIT_TIMEOUT` | 300 | 默认超时（秒） |
| `MEDIA_POLL_INTERVAL` | 15 | 媒体类型下载轮询间隔（秒） |

---

## 6. 复刻完成检查清单

- [ ] `notebooklm` CLI 可用且已 login
- [ ] `notebooklm-intake` skill 已部署且有至少一个已同步的项目
- [ ] 所有 6 个文件已创建（SKILL.md、settings.local.json、output.py、d3.min.js、markmap-view.min.js、USAGE-AND-STATUS.md）
- [ ] `output.py` 中 `KNOWLEDGE_ROOT` 已替换为正确路径
- [ ] `SKILL.md` 和 `USAGE-AND-STATUS.md` 中所有路径已替换
- [ ] `d3.min.js` 和 `markmap-view.min.js` 已下载且文件大小合理（d3 约 270KB，markmap 约 60KB）
- [ ] `output/` 目录存在于 `knowledge/notebooklm/` 下
- [ ] `python -m py_compile` 通过
- [ ] Smoke test 通过（inspect 返回项目 → generate report 成功 → 文件落盘）

全部通过即复刻完成。
