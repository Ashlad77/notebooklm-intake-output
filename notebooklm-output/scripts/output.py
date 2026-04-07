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
import os
import re


def _resolve_knowledge_root() -> Path:
    """Resolve knowledge root: env var > auto-detect > home default."""
    # 1. Honour explicit environment variable
    env = os.environ.get("OPENCLAW_HOME")
    if env:
        return Path(env) / "knowledge"
    # 2. Auto-detect from script location (.openclaw/skills/xxx/scripts/output.py)
    try:
        openclaw_dir = Path(__file__).resolve().parents[3]
        candidate = openclaw_dir / "knowledge"
        if candidate.is_dir():
            return candidate
    except (IndexError, OSError):
        pass
    # 3. Fall back to ~/.openclaw/knowledge
    return Path.home() / ".openclaw" / "knowledge"


KNOWLEDGE_ROOT = _resolve_knowledge_root()
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
GUI_REFRESH_SECONDS = 5

# ---------- i18n strings ----------

_STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        # TYPE_LABELS
        "report": "报告", "quiz": "测验", "flashcards": "抽认卡",
        "mind-map": "脑图", "infographic": "信息图",
        "audio-overview": "音频总结", "video-overview": "视频总结",
        "slide-deck": "幻灯片", "data-table": "数据表",
        # GUI
        "win_title": "NotebookLM 输出进度",
        "preparing": "准备中", "waiting": "等待开始",
        "elapsed_fmt": "{} 秒",
        "lbl_project": "项目", "lbl_type": "输出类型",
        "lbl_phase": "当前阶段", "lbl_task": "任务 ID",
        "lbl_status": "状态", "lbl_path": "保存路径",
        "lbl_elapsed": "已耗时", "lbl_error": "错误",
        "label_sep": "：",
        # status messages
        "submitted": "任务已提交，云端开始生成",
        "waiting_cli": "正在等待 CLI 返回任务信息…",
        "generating": "生成中",
        "no_task_id": "CLI 未返回 task_id，将尝试直接下载最新产物",
        "generating_wait": "生成中（等待云端完成）",
        "timeout_threshold": "超时阈值 {} 秒",
        "gen_done": "生成完成",
        "gen_ended": "生成结束（{}）",
        "wait_timeout": "等待超时",
        "wait_exceeded": "本地等待超过 {} 秒，云端任务可能仍在进行",
        "cloud_gen": "云端生成中，等待产物就绪",
        "poll_info": "每 {} 秒尝试下载，超时 {} 秒",
        "initial_wait": "云端生成中，{} 秒后开始检查",
        "poll_exceeded": "超过 {} 秒仍未下载成功",
        "try_download": "尝试下载（第 {} 次）",
        "remaining": "剩余 {} 秒",
        "completed": "已完成",
        "not_ready": "产物尚未就绪，{} 秒后重试",
        "download_fail": "第 {} 次下载未成功，云端可能仍在处理",
        "downloading": "下载中",
        "prep_context": "准备上下文",
        "manual_download": "云端可能已完成但下载未成功，请在网页端确认后手动下载",
        "timeout_no_download": "超时未能下载",
        "convert_done": "已转译为 HTML",
        "convert_fail_phase": "下载完成（转译失败）",
        "convert_fail": "转译失败：{}",
        "cmd_timeout": "命令超时（{}秒）: {}",
        "failed": "失败",
        "unnamed": "未命名项目",
        # HTML - quiz
        "html_lang": "zh-Hans",
        "quiz_title_default": "测验",
        "submit_all": "提交全部答案", "retry": "重新答题",
        "q_counter": "第 {} / {} 题",
        "hint_prefix": "💡 提示：",
        "correct_prefix": "✅ 正确答案：",
        "wrong_prefix": "❌ 你选的 ",
        "accuracy": "正确率 {}%",
        # HTML - flashcards
        "fc_title_default": "抽认卡",
        "fc_front": "正面", "fc_back": "背面",
        "fc_prev": "&#9664; 上一张", "fc_flip": "翻面", "fc_next": "下一张 &#9654;",
        "fc_tip": "点击卡片或按空格键翻面，按左右方向键切换",
        # HTML - mind map
        "mm_title_default": "思维导图",
        "mm_fit": "适应窗口", "mm_expand": "全部展开", "mm_collapse": "全部收起",
    },
    "en": {
        "report": "Report", "quiz": "Quiz", "flashcards": "Flashcards",
        "mind-map": "Mind Map", "infographic": "Infographic",
        "audio-overview": "Audio Overview", "video-overview": "Video Overview",
        "slide-deck": "Slides", "data-table": "Data Table",
        "win_title": "NotebookLM Output Progress",
        "preparing": "Preparing", "waiting": "Waiting",
        "elapsed_fmt": "{}s",
        "lbl_project": "Project", "lbl_type": "Output Type",
        "lbl_phase": "Phase", "lbl_task": "Task ID",
        "lbl_status": "Status", "lbl_path": "Save Path",
        "lbl_elapsed": "Elapsed", "lbl_error": "Error",
        "label_sep": ":",
        "submitted": "Task submitted, cloud generation started",
        "waiting_cli": "Waiting for CLI to return task info...",
        "generating": "Generating",
        "no_task_id": "CLI returned no task_id, will try downloading latest artifact",
        "generating_wait": "Generating (waiting for cloud)",
        "timeout_threshold": "Timeout threshold: {}s",
        "gen_done": "Generation complete",
        "gen_ended": "Generation ended ({})",
        "wait_timeout": "Wait timeout",
        "wait_exceeded": "Local wait exceeded {}s, cloud task may still be running",
        "cloud_gen": "Cloud generating, waiting for artifact",
        "poll_info": "Polling every {}s, timeout {}s",
        "initial_wait": "Cloud generating, checking in {}s",
        "poll_exceeded": "Exceeded {}s, download unsuccessful",
        "try_download": "Downloading (attempt {})",
        "remaining": "{}s remaining",
        "completed": "Completed",
        "not_ready": "Artifact not ready, retrying in {}s",
        "download_fail": "Attempt {} unsuccessful, cloud may still be processing",
        "downloading": "Downloading",
        "prep_context": "Preparing context",
        "manual_download": "Cloud may have finished but download failed. Please check the web UI and download manually",
        "timeout_no_download": "Timed out, download failed",
        "convert_done": "Converted to HTML",
        "convert_fail_phase": "Download complete (conversion failed)",
        "convert_fail": "Conversion failed: {}",
        "cmd_timeout": "Command timeout ({}s): {}",
        "failed": "Failed",
        "unnamed": "Unnamed Project",
        "html_lang": "en",
        "quiz_title_default": "Quiz",
        "submit_all": "Submit All", "retry": "Retry",
        "q_counter": "Q {} / {}",
        "hint_prefix": "💡 Hint: ",
        "correct_prefix": "✅ Correct answer: ",
        "wrong_prefix": "❌ You chose ",
        "accuracy": "Accuracy {}%",
        "fc_title_default": "Flashcards",
        "fc_front": "Front", "fc_back": "Back",
        "fc_prev": "&#9664; Prev", "fc_flip": "Flip", "fc_next": "Next &#9654;",
        "fc_tip": "Click card or press Space to flip. Use arrow keys to navigate.",
        "mm_title_default": "Mind Map",
        "mm_fit": "Fit Window", "mm_expand": "Expand All", "mm_collapse": "Collapse All",
    },
}

_LANG = "zh"


def _t(key: str) -> str:
    """Get translated string for current language."""
    return _STRINGS.get(_LANG, _STRINGS["zh"]).get(key, key)


def _cli_language() -> str:
    """Return the NotebookLM CLI --language value for current language."""
    return "zh_Hans" if _LANG == "zh" else "en"


# ---------- 媒体类型需要更长等待，且用分离式提交+等待 ----------
MEDIA_TYPES = {"audio-overview", "video-overview"}
MEDIA_WAIT_TIMEOUT = 900   # 15 min
HEAVY_TYPES = {"slide-deck", "infographic"}
HEAVY_WAIT_TIMEOUT = 600   # 10 min
DEFAULT_WAIT_TIMEOUT = 300  # 5 min

# ---------- generate 参数映射 ----------
# 只有 CLI 真正支持的类型才附带 --language / --wait，避免子命令参数不兼容
# NOTE: language is injected dynamically via _build_generate_args()
GENERATE_TYPE_BASE: dict[str, tuple[str, list[str]]] = {
    "audio-overview": ("audio",      ["--format", "brief"]),
    "video-overview": ("video",      ["--format", "brief"]),
    "slide-deck":     ("slide-deck", []),
    "quiz":           ("quiz",       []),
    "flashcards":     ("flashcards", []),
    "infographic":    ("infographic",[]),
    "report":         ("report",     ["--format", "briefing-doc"]),
    "mind-map":       ("mind-map",   []),
    "data-table":     ("data-table", ["summarize the uploaded material into a structured table"]),
}

# Types that accept --language flag
_LANGUAGE_SUPPORTED_TYPES = {
    "audio-overview", "video-overview", "slide-deck", "infographic", "report",
}


def _build_generate_args(output_type: str) -> tuple[str, list[str]]:
    """Build generate command args, injecting --language dynamically."""
    cmd, base_extra = GENERATE_TYPE_BASE[output_type]
    extra = list(base_extra)
    if output_type in _LANGUAGE_SUPPORTED_TYPES:
        extra.extend(["--language", _cli_language()])
    return cmd, extra


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
    return text or _t("unnamed")


def build_output_filename(project_name: str, output_type: str, ext: str) -> str:
    safe_project = _sanitize_filename(project_name)
    type_label = _t(output_type)
    safe_type = _sanitize_filename(type_label)
    return f"{safe_project}-{safe_type}-{human_stamp()}{ext}"


def _get_wait_timeout(output_type: str) -> int:
    if output_type in MEDIA_TYPES:
        return MEDIA_WAIT_TIMEOUT
    if output_type in HEAVY_TYPES:
        return HEAVY_WAIT_TIMEOUT
    return DEFAULT_WAIT_TIMEOUT


class ProgressWindow:
    def __init__(self, project: str, output_type: str):
        self.root = tk.Tk()
        self.root.title(_t("win_title"))
        self.root.geometry("620x320")
        self.root.attributes("-topmost", True)
        self.queue: queue.Queue[tuple[str, dict[str, str]]] = queue.Queue()
        self._start = time.time()

        self.project_var = tk.StringVar(value=project)
        self.type_var = tk.StringVar(value=output_type)
        self.phase_var = tk.StringVar(value=_t("preparing"))
        self.task_var = tk.StringVar(value="-")
        self.status_var = tk.StringVar(value=_t("waiting"))
        self.path_var = tk.StringVar(value="-")
        self.elapsed_var = tk.StringVar(value=_t("elapsed_fmt").format(0))
        self.error_var = tk.StringVar(value="-")

        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        sep = _t("label_sep")
        rows = [
            (_t("lbl_project"), self.project_var),
            (_t("lbl_type"), self.type_var),
            (_t("lbl_phase"), self.phase_var),
            (_t("lbl_task"), self.task_var),
            (_t("lbl_status"), self.status_var),
            (_t("lbl_path"), self.path_var),
            (_t("lbl_elapsed"), self.elapsed_var),
            (_t("lbl_error"), self.error_var),
        ]
        for i, (label, var) in enumerate(rows):
            tk.Label(frame, text=f"{label}{sep}", anchor="w").grid(row=i, column=0, sticky="nw", pady=4)
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
        self.elapsed_var.set(_t("elapsed_fmt").format(elapsed))
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
    """Run a notebooklm CLI command and return stdout."""
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
            _t("cmd_timeout").format(timeout, " ".join(cmd))
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or result.stdout).strip()
            or f"NotebookLM command failed: {' '.join(cmd)}"
        )
    return result.stdout.strip()


def _parse_json_output(raw: str) -> dict[str, Any]:
    """Try to parse JSON from CLI output (may have non-JSON text before it)."""
    try:
        return json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError):
        pass
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


# ==================== Core: split-phase task flow ====================


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
    Phase 1: submit generation task, return task_id (may be None).
    Only attach --wait / --no-wait when the CLI subcommand supports it.
    """
    generate_cmd, generate_extra = _build_generate_args(output_type)

    use_wait = output_type in WAIT_SUPPORTED_TYPES and output_type not in MEDIA_TYPES
    use_no_wait = output_type in WAIT_SUPPORTED_TYPES and output_type in MEDIA_TYPES
    timeout_sec = _get_wait_timeout(output_type) + 60

    cmd_args = ["generate", generate_cmd, *generate_extra]
    if use_wait:
        cmd_args.append("--wait")
    elif use_no_wait:
        cmd_args.append("--no-wait")
    cmd_args.append("--json")

    progress.update(
        phase=_t("submitted"),
        status="submitting",
        error=_t("waiting_cli")
    )

    raw = run_notebooklm(
        *cmd_args,
        timeout=timeout_sec,
    )

    task_info = _parse_json_output(raw)
    task_id = task_info.get("task_id") or task_info.get("artifact_id")
    status = task_info.get("status", "unknown")

    if task_id:
        progress.update(phase=_t("generating"), task_id=task_id, status=status, error="-")
    else:
        progress.update(
            phase=_t("submitted"),
            status="submitted_no_task_id",
            error=_t("no_task_id")
        )

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
    Phase 2: wait for task completion.
    - Non-media types: use `notebooklm artifact wait` (reliable)
    - Media types: skip artifact wait (internal _is_media_ready may
      always return False for video), handled by _wait_and_download_media
    """
    timeout = _get_wait_timeout(output_type)

    progress.update(
        phase=_t("generating_wait"),
        task_id=task_id,
        status="waiting",
        error=_t("timeout_threshold").format(timeout)
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
            phase=_t("gen_done") if final_status == "completed" else _t("gen_ended").format(final_status),
            status=final_status,
            error=info.get("error") or "-"
        )
        return final_status
    except RuntimeError as exc:
        err_msg = str(exc)
        if "超时" in err_msg or "timeout" in err_msg.lower():
            progress.update(
                phase=_t("wait_timeout"),
                status="timeout",
                error=_t("wait_exceeded").format(timeout)
            )
            return "timeout"
        raise


def _try_download(notebook_id: str, output_type: str, output_path: Path) -> bool:
    """Try to download the latest artifact. Return True on success."""
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


MEDIA_POLL_INTERVAL = 15

# ---------- JSON types need post-download conversion to interactive HTML ----------
TEXT_CONVERTABLE = {"quiz", "flashcards", "mind-map"}


def _convert_json_to_html(json_path: Path, output_type: str) -> Path:
    """
    Read json_path and convert quiz / flashcards / mind-map to interactive HTML.
    Returns HTML file path (same name, .html extension).
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
    """Escape HTML special characters, handles None and non-string input."""
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
    title = _html_escape(data.get("title", _t("quiz_title_default")))
    questions = data.get("questions", [])
    questions_json = json.dumps(questions, ensure_ascii=False).replace("</", "<\\/")

    s_submit = _t("submit_all")
    s_retry = _t("retry")
    s_q_counter = _t("q_counter")
    s_hint = _t("hint_prefix")
    s_correct = _t("correct_prefix")
    s_wrong = _t("wrong_prefix")
    s_accuracy = _t("accuracy")
    html_lang = _t("html_lang")

    # Build JS-safe counter template: e.g. "第 " + (qi+1) + " / " + len + " 题"
    # Split the pattern on {} placeholders
    qc_parts = s_q_counter.split("{}")
    qc_js = "'" + _html_escape(qc_parts[0]) + "' + (qi + 1) + '" + _html_escape(qc_parts[1] if len(qc_parts) > 1 else "") + "' + questions.length + '" + _html_escape(qc_parts[2] if len(qc_parts) > 2 else "") + "'"

    # Accuracy template
    acc_parts = s_accuracy.split("{}")
    acc_js = "\"" + _html_escape(acc_parts[0]) + "\" + Math.round(correct / questions.length * 100) + \"" + _html_escape(acc_parts[1] if len(acc_parts) > 1 else "") + "\""

    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
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
  <button class="btn btn-primary" id="submitBtn" onclick="submitAll()">{s_submit}</button>
  <button class="btn btn-reset" id="resetBtn" onclick="resetAll()" style="display:none">{s_retry}</button>
</div>
</div>
<script>
const questions = {questions_json};
let submitted = false;
const container = document.getElementById("questions");
const S_HINT = {json.dumps(s_hint, ensure_ascii=False)};
const S_CORRECT = {json.dumps(s_correct, ensure_ascii=False)};
const S_WRONG = {json.dumps(s_wrong, ensure_ascii=False)};

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
    '<div class="question-num">' + {qc_js} + '</div>' +
    '<div class="question-text">' + escapeHtml(q.question) + '</div>' +
    '<div class="options">' + optionsHtml + '</div>' +
    '<div class="feedback" id="fb' + qi + '">' +
      (q.hint ? '<div class="hint">' + S_HINT + escapeHtml(q.hint) + '</div>' : '') +
      '<div class="rationale">' + S_CORRECT + correctLabel + '. ' + escapeHtml(correctRationale) + '</div>' +
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
          wrongNote.innerHTML = S_WRONG + String.fromCharCode(65 + oi) + ": " + escapeHtml(selectedRationale);
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
    {acc_js};
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
    title = _html_escape(data.get("title", _t("fc_title_default")))
    cards = data.get("cards", [])
    cards_json = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")
    html_lang = _t("html_lang")

    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
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
      <span class="card-label">{_t("fc_front")}</span>
      <div class="card-text" id="frontText"></div>
    </div>
    <div class="card-face card-back">
      <span class="card-label">{_t("fc_back")}</span>
      <div class="card-text" id="backText"></div>
    </div>
  </div>
</div>
<div class="controls">
  <button class="btn btn-nav" id="prevBtn" onclick="prev()">{_t("fc_prev")}</button>
  <button class="btn btn-flip" onclick="flipCard()">{_t("fc_flip")}</button>
  <button class="btn btn-nav" id="nextBtn" onclick="next()">{_t("fc_next")}</button>
</div>
<div class="tip">{_t("fc_tip")}</div>
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
    title = _html_escape(data.get("name", _t("mm_title_default")))
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html_lang = _t("html_lang")

    d3_js = (VENDOR_DIR / "d3.min.js").read_text(encoding="utf-8")
    markmap_js = (VENDOR_DIR / "markmap-view.min.js").read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
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
    <button onclick="mm.fit()">{_t("mm_fit")}</button>
    <button onclick="expandAll()">{_t("mm_expand")}</button>
    <button onclick="collapseAll()">{_t("mm_collapse")}</button>
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
    Media types (audio/video): poll + attempt download.
    Bypasses notebooklm-py's _is_media_ready check issue.
    """
    timeout = _get_wait_timeout(output_type)
    start = time.time()

    progress.update(
        phase=_t("cloud_gen"),
        task_id=task_id or "-",
        status="polling",
        error=_t("poll_info").format(MEDIA_POLL_INTERVAL, timeout)
    )

    initial_wait = 30
    progress.update(
        phase=_t("initial_wait").format(initial_wait),
        status="initial_wait",
    )
    time.sleep(initial_wait)

    attempt = 0
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            progress.update(
                phase=_t("wait_timeout"),
                status="timeout",
                error=_t("poll_exceeded").format(timeout)
            )
            return "timeout"

        attempt += 1
        remaining = int(timeout - elapsed)
        progress.update(
            phase=_t("try_download").format(attempt),
            status=f"attempt_{attempt}",
            error=_t("remaining").format(remaining)
        )

        if _try_download(notebook_id, output_type, output_path):
            progress.update(
                phase=_t("completed"),
                status="completed",
                saved_to=str(output_path),
                error="-"
            )
            return "completed"

        progress.update(
            phase=_t("not_ready").format(MEDIA_POLL_INTERVAL),
            status=f"waiting_retry_{attempt}",
            error=_t("download_fail").format(attempt)
        )
        time.sleep(MEDIA_POLL_INTERVAL)


def _download_artifact(
    notebook_id: str,
    output_type: str,
    output_path: Path,
    progress: ProgressWindow,
) -> None:
    """Phase 3: download artifact to local (non-media types)."""
    download_cmd, _ext, download_extra = DOWNLOAD_TYPE_MAP[output_type]

    progress.update(phase=_t("downloading"), status="downloading", error="-")

    run_notebooklm(
        "download", download_cmd, *download_extra, str(output_path),
        "-n", notebook_id,
        timeout=120,
    )

    progress.update(
        phase=_t("completed"),
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
    """Worker thread: submit -> wait -> download, updating GUI via queue."""
    notebook_id = project["notebook_id"]

    try:
        # 0. Set current notebook
        progress.update(phase=_t("prep_context"), status="setting_notebook", error="-")
        run_notebooklm("use", notebook_id, timeout=30)

        # 1. Submit generation
        task_id = _submit_generation(notebook_id, output_type, progress)

        # 2. Wait + download
        if output_type in MEDIA_TYPES:
            final_status = _wait_and_download_media(
                notebook_id, task_id, output_type, output_path, progress
            )

            if final_status == "timeout":
                progress.update(
                    phase=_t("timeout_no_download"),
                    status="timeout",
                    error=_t("manual_download")
                )
                progress.close_later(delay_ms=8000)
                result_holder["error"] = f"Media download timed out for {output_type}"
                return

        else:
            _download_artifact(notebook_id, output_type, output_path, progress)
            if output_type in TEXT_CONVERTABLE and output_path.exists() and output_path.suffix == ".json":
                try:
                    html_path = _convert_json_to_html(output_path, output_type)
                    output_path = html_path
                    progress.update(
                        phase=_t("convert_done"),
                        saved_to=str(html_path),
                        error="-"
                    )
                except Exception as exc:
                    progress.update(
                        phase=_t("convert_fail_phase"),
                        error=_t("convert_fail").format(exc)
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
        progress.update(phase=_t("failed"), status="error", error=str(exc))
        progress.close_later(delay_ms=8000)
        result_holder["error"] = str(exc)


def generate(project_name: str, output_type: str) -> None:
    registry = load_registry()
    project = find_project(project_name, registry)
    if not project:
        raise SystemExit(f"project not found: {project_name}")
    if output_type not in GENERATE_TYPE_BASE or output_type not in DOWNLOAD_TYPE_MAP:
        raise SystemExit(f"unsupported output type: {output_type}")
    if project.get("sync_status") != "synced" or not project.get("notebook_id"):
        raise SystemExit(f"project not synced to NotebookLM cloud: {project_name}")

    default_output_dir = KNOWLEDGE_ROOT / "notebooklm" / "output" / f"{project['project_name']}_output"
    output_dir = Path(project.get("output_dir") or str(default_output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    _generate_cmd, _generate_extra = _build_generate_args(output_type)
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

    progress.run()

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
    generate_parser.add_argument("--language", default="zh", choices=["zh", "en"],
                                 help="UI and output language (default: zh)")

    args = parser.parse_args()
    if args.command == "inspect":
        inspect(args.project)
    elif args.command == "generate":
        global _LANG
        _LANG = args.language
        generate(args.project, args.type)


if __name__ == "__main__":
    main()
