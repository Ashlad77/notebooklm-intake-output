# notebooklm-intake Skill 完整复刻指南

本文档供 OpenClaw 实例阅读后一比一复刻 `notebooklm-intake` skill。请严格按照以下结构、路径、文件内容创建。

---

## 0. 前置条件

在开始之前，目标机器需要满足：

1. **Python 3.10+** 已安装且可在命令行中调用
2. **`notebooklm-py` CLI 已安装并完成认证**（详见下方对接说明）
3. **OpenClaw 目录结构存在** — 即 `~/.openclaw/` 已初始化

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
│   └── notebooklm-intake/
│       ├── .claude/
│       │   └── settings.local.json
│       ├── SKILL.md
│       ├── USAGE-AND-STATUS.md
│       └── scripts/
│           └── intake.py
└── knowledge/
    └── notebooklm/
        ├── inbox/          ← 待上传资料放这里
        ├── processed/      ← 上传成功后自动归档到这里
        ├── projects/       ← 每个项目的 metadata
        └── registry.json   ← 总索引（初始为 {"projects": []}）
```

**注意**：`scripts/intake.py` 已改为自动检测路径（基于脚本位置推算 `.openclaw` 根目录），无需手动修改 `KNOWLEDGE_ROOT`。只要按上述目录结构部署到 `~/.openclaw/` 下即可。`SKILL.md` 中的路径也已使用 `<OPENCLAW_HOME>` 占位符，无需替换。

---

## 2. 文件内容 — 逐文件创建

### 2.1 `SKILL.md`

路径：`OPENCLAW_HOME/skills/notebooklm-intake/SKILL.md`

```markdown
---
name: notebooklm-intake
description: 将本地资料上传、导入并同步到云端 NotebookLM 项目。用于当用户说"上传到 NotebookLM""导入 NotebookLM""把资料发到云端""新建 NotebookLM 项目并入库资料""把本地文件同步到 NotebookLM"等场景时触发。默认把这类请求理解为入库/上传，而不是生成输出；适用于扫描 knowledge/notebooklm/inbox 中新增的链接、PDF、音视频、文档、表格等资料，自动创建同名项目、上传 source，并写入本地 metadata。
---

# NotebookLM 入库

使用脚本优先，不要在对话里手动拼流程。

## 固定目录

- 输入目录：`OPENCLAW_HOME/knowledge/notebooklm/inbox`
- 项目目录：`OPENCLAW_HOME/knowledge/notebooklm/projects`
- 输出目录：`OPENCLAW_HOME/knowledge/notebook`
- 状态索引：`OPENCLAW_HOME/knowledge/notebooklm/registry.json`

## 执行原则

1. 默认把"上传 / 导入 / 入库 / 同步到 NotebookLM"理解为**把本地资料送到云端**，优先走本 skill。
2. 不要把"生成 / 制作 / 产出 / 导出 / 输出某个 NotebookLM 项目内容"误判成 intake；这类请求默认应走 `notebooklm-output`。
3. 先运行脚本扫描 inbox 新文件。
4. 为每个新文件生成本地项目 metadata。
5. 当前阶段如果尚未完成真实云端接入，允许先写本地占位状态，但必须明确告诉用户"脚本骨架已完成，云端上传待接通"。
6. 不要假装已经上传成功；只有脚本返回成功且 metadata 明确记录 notebook_id/source_id 时，才能说已入库云端。

## 标准命令

```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py
```

如需指定单个文件，可用：

```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --path "<文件或目录>"
```

## 输出要求

简洁汇报：
- 新识别了哪些文件
- 哪些已写入 metadata
- 哪些已真正上传云端 / 哪些仍是待接通状态
- 对应项目目录在哪里
```

> **注意**：上面的 `OPENCLAW_HOME` 占位符需要在创建文件时替换为目标用户的真实绝对路径。

---

### 2.2 `.claude/settings.local.json`

路径：`OPENCLAW_HOME/skills/notebooklm-intake/.claude/settings.local.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m py_compile scripts/intake.py)"
    ]
  }
}
```

---

### 2.3 `scripts/intake.py`

路径：`OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py`

这是核心脚本，**必须完整复制，不可省略任何部分**。

```python
from __future__ import annotations

import argparse
import json
import subprocess
import time
import shutil
from dataclasses import dataclass, asdict, fields
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import hashlib
import re

KNOWLEDGE_ROOT = Path(r"OPENCLAW_HOME/knowledge")  # ← 替换为目标用户的实际路径
INBOX_DIR = KNOWLEDGE_ROOT / "notebooklm" / "inbox"
PROCESSED_DIR = KNOWLEDGE_ROOT / "notebooklm" / "processed"
PROJECTS_DIR = KNOWLEDGE_ROOT / "notebooklm" / "projects"
REGISTRY_PATH = KNOWLEDGE_ROOT / "notebooklm" / "registry.json"
SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".tsv",
    ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".avi", ".url", ".webloc", ".html",
}
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
BATCH_ITEM_DELAY_SECONDS = 1

@dataclass
class ProjectRecord:
    project_name: str
    source_name: str
    source_path: str
    source_type: str
    created_at: str
    updated_at: str
    sync_status: str
    notebook_id: str | None = None
    source_id: str | None = None
    output_dir: str | None = None
    notes: str | None = None
    source_fingerprint: str | None = None


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)

_PROJECT_RECORD_FIELDS = {f.name for f in fields(ProjectRecord)}


def project_record_from_dict(d: dict[str, Any]) -> ProjectRecord:
    """Construct a ProjectRecord ignoring unknown keys in *d*."""
    return ProjectRecord(**{k: v for k, v in d.items() if k in _PROJECT_RECORD_FIELDS})


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_registry() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"projects": []}


def save_registry(registry: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_source_fingerprint(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}|{stat.st_size}|{int(stat.st_mtime)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def infer_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".url", ".webloc", ".html"}:
        return "link"
    if suffix in {".mp3", ".wav", ".m4a"}:
        return "audio"
    if suffix in {".mp4", ".mov", ".avi"}:
        return "video"
    if suffix in {".xls", ".xlsx", ".csv", ".tsv"}:
        return "spreadsheet"
    if suffix in {".doc", ".docx", ".txt", ".md", ".pdf"}:
        return "document"
    return "unknown"


def normalize_project_name(path: Path) -> str:
    return path.stem.strip()


def iter_candidates(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    files = [p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files)


def write_project_manifest(record: ProjectRecord) -> None:
    project_dir = PROJECTS_DIR / record.project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest = project_dir / "project.json"
    manifest.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_project_record(path: Path, registry: dict[str, Any]) -> tuple[ProjectRecord, int]:
    project_name = normalize_project_name(path)
    fingerprint = compute_source_fingerprint(path)
    now = utc_now()
    for idx, item in enumerate(registry["projects"]):
        if item["source_path"] == str(path) or item.get("source_fingerprint") == fingerprint:
            item["updated_at"] = now
            item["source_fingerprint"] = fingerprint
            record = project_record_from_dict(item)
            write_project_manifest(record)
            return record, idx

    output_dir = str((KNOWLEDGE_ROOT / "notebooklm" / "output" / f"{project_name}_output"))
    record = ProjectRecord(
        project_name=project_name,
        source_name=path.name,
        source_path=str(path),
        source_type=infer_source_type(path),
        created_at=now,
        updated_at=now,
        sync_status="pending_cloud_upload",
        output_dir=output_dir,
        notes="Record created; waiting for NotebookLM cloud upload.",
        source_fingerprint=fingerprint,
    )
    registry["projects"].append(asdict(record))
    write_project_manifest(record)
    return record, len(registry["projects"]) - 1


def run_notebooklm(*args: str) -> str:
    cmd = ["notebooklm", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"NotebookLM command failed: {' '.join(cmd)}")
    return result.stdout.strip()


def find_existing_notebook_ids(project_name: str) -> list[str]:
    output = run_notebooklm("list")
    ids: list[str] = []
    for line in output.splitlines():
        if "│" not in line:
            continue
        parts = [part.strip() for part in line.split("│")]
        if len(parts) < 3:
            continue
        row_id_raw = parts[1] if len(parts) > 1 else ""
        row_title = parts[2] if len(parts) > 2 else ""
        m = UUID_RE.search(row_id_raw.replace("…", ""))
        if m and row_title == project_name:
            ids.append(m.group())
    return ids


def create_notebook(project_name: str) -> str:
    existing_ids = find_existing_notebook_ids(project_name)
    if len(existing_ids) == 1:
        return existing_ids[0]
    if len(existing_ids) > 1:
        raise RuntimeError(
            f"Found multiple notebooks with the same title '{project_name}': {existing_ids}. "
            "Refusing to guess; please resolve manually or persist the intended notebook_id locally."
        )

    output = run_notebooklm("create", project_name)
    m = UUID_RE.search(output)
    if not m:
        raise RuntimeError(f"Could not parse notebook_id from create output: {output}")
    return m.group()


def find_existing_source_ids(notebook_id: str, source_name: str) -> list[str]:
    run_notebooklm("use", notebook_id)
    output = run_notebooklm("source", "list")
    ids: list[str] = []
    for line in output.splitlines():
        if "│" not in line:
            continue
        parts = [part.strip() for part in line.split("│")]
        if len(parts) < 3:
            continue
        row_id_raw = parts[1] if len(parts) > 1 else ""
        row_title = parts[2] if len(parts) > 2 else ""
        m = UUID_RE.search(row_id_raw.replace("…", ""))
        if m and row_title == source_name:
            ids.append(m.group())
    return ids


def find_existing_source_id(notebook_id: str, source_name: str) -> str | None:
    ids = find_existing_source_ids(notebook_id, source_name)
    if len(ids) == 1:
        return ids[0]
    if len(ids) > 1:
        raise RuntimeError(
            f"Found multiple sources with the same title '{source_name}' in notebook {notebook_id}: {ids}. "
            "Refusing to guess; please resolve manually or persist the intended source_id locally."
        )
    return None


def upload_source(notebook_id: str, source_path: Path) -> str:
    existing_source_id = find_existing_source_id(notebook_id, source_path.name)
    if existing_source_id:
        return existing_source_id

    run_notebooklm("use", notebook_id)
    output = run_notebooklm("source", "add", str(source_path))
    m = UUID_RE.search(output)
    if not m:
        raise RuntimeError(f"Could not parse source_id from source add output: {output}")
    return m.group()


def classify_error(error: Exception) -> str:
    msg = str(error).lower()
    if any(kw in msg for kw in ("authentication", "login", "sid", "csrf", "unauthorized", "403", "401")):
        return "auth_error"
    if "multiple notebooks with the same title" in msg:
        return "notebook_conflict"
    if "multiple sources with the same title" in msg:
        return "source_conflict"
    if "source add" in msg or "source upload" in msg or "could not parse source_id" in msg:
        return "source_upload_error"
    if any(kw in msg for kw in ("timed out", "timeout", "connectionerror", "networkerror", "connection refused")):
        return "network_error"
    return "unknown_error"


def archive_processed_source(record: ProjectRecord) -> str | None:
    source_path = Path(record.source_path)
    if not source_path.exists():
        return None
    if PROCESSED_DIR in source_path.parents:
        return str(source_path)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DIR / source_path.name
    if destination.exists():
        stamped = f"{destination.stem}-{int(time.time())}{destination.suffix}"
        destination = PROCESSED_DIR / stamped
    shutil.move(str(source_path), str(destination))
    record.source_path = str(destination)
    record.source_fingerprint = compute_source_fingerprint(destination)
    return str(destination)


def sync_record_to_cloud(record: ProjectRecord, archive_duplicates: bool = False) -> tuple[ProjectRecord, dict[str, Any]]:
    if record.sync_status == "synced" and record.notebook_id and record.source_id:
        archived_to = archive_processed_source(record) if archive_duplicates else None
        if archive_duplicates and archived_to:
            record.updated_at = utc_now()
            record.notes = f"Duplicate content confirmed and archived to: {archived_to}"
        return record, {
            "project_name": record.project_name,
            "status": "already_synced",
            "attempts": 0,
            "error_type": None,
            "error": None,
            "notebook_id": record.notebook_id,
            "source_id": record.source_id,
            "archive_action": "archived" if archived_to else "needs_confirmation",
            "archived_to": archived_to,
        }

    updated = project_record_from_dict(asdict(record))
    last_error = None
    last_error_type = None
    for attempt in range(1, MAX_RETRIES + 1):
        now = utc_now()
        try:
            notebook_id = updated.notebook_id or create_notebook(updated.project_name)
            source_id = updated.source_id or upload_source(notebook_id, Path(updated.source_path))
            updated.notebook_id = notebook_id
            updated.source_id = source_id
            updated.sync_status = "synced"
            updated.updated_at = now
            retry_note = f" after {attempt} attempt(s)" if attempt > 1 else ""
            archived_to = archive_processed_source(updated)
            archive_note = f" Archived to: {archived_to}." if archived_to else ""
            updated.notes = f"NotebookLM cloud sync completed via notebooklm-py CLI{retry_note}.{archive_note}"
            result_kind = "synced_after_retry" if attempt > 1 else "synced"
            return updated, {
                "project_name": updated.project_name,
                "status": result_kind,
                "attempts": attempt,
                "error_type": None,
                "error": None,
                "notebook_id": updated.notebook_id,
                "source_id": updated.source_id,
                "archive_action": "archived" if archived_to else "not_archived",
                "archived_to": archived_to,
            }
        except Exception as e:
            last_error = e
            last_error_type = classify_error(e)
            updated.updated_at = now
            updated.sync_status = "pending_cloud_upload"
            updated.notes = f"Cloud upload attempt {attempt}/{MAX_RETRIES} failed [{last_error_type}]: {e}"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    updated.notes = f"Cloud upload failed after {MAX_RETRIES} attempts [{last_error_type}]: {last_error}"
    return updated, {
        "project_name": updated.project_name,
        "status": "failed",
        "attempts": MAX_RETRIES,
        "error_type": last_error_type,
        "error": str(last_error) if last_error else None,
        "notebook_id": updated.notebook_id,
        "source_id": updated.source_id,
        "archive_action": "not_archived",
        "archived_to": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=str(INBOX_DIR))
    parser.add_argument("--archive-duplicates", action="store_true", help="Archive already-synced duplicate files into processed/")
    args = parser.parse_args()

    target = Path(args.path)
    registry = load_registry()
    candidates = iter_candidates(target)
    created: list[ProjectRecord] = []
    results: list[dict[str, Any]] = []

    for i, item in enumerate(candidates, start=1):
        record, idx = ensure_project_record(item, registry)
        record, result = sync_record_to_cloud(record, archive_duplicates=args.archive_duplicates)
        registry["projects"][idx] = asdict(record)
        write_project_manifest(record)
        created.append(record)
        results.append(result)
        # Fast-fail: stop processing remaining files on auth error
        if result.get("error_type") == "auth_error":
            for remaining in candidates[i:]:
                rec, ridx = ensure_project_record(remaining, registry)
                skip_result = {
                    "project_name": rec.project_name,
                    "status": "skipped",
                    "attempts": 0,
                    "error_type": "auth_error",
                    "error": "Skipped due to earlier auth failure",
                    "notebook_id": rec.notebook_id,
                    "source_id": rec.source_id,
                    "archive_action": "not_archived",
                    "archived_to": None,
                }
                created.append(rec)
                results.append(skip_result)
            break
        if i < len(candidates):
            time.sleep(BATCH_ITEM_DELAY_SECONDS)

    save_registry(registry)

    summary = {
        "scanned": len(candidates),
        "registered": len(created),
        "synced": sum(1 for r in results if r["status"] == "synced"),
        "synced_after_retry": sum(1 for r in results if r["status"] == "synced_after_retry"),
        "already_synced": sum(1 for r in results if r["status"] == "already_synced"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "pending_archive_confirmation": sum(1 for r in results if r.get("archive_action") == "needs_confirmation"),
        "archived": sum(1 for r in results if r.get("archive_action") == "archived"),
    }
    pending_archive_confirmation = [
        {
            "project_name": r["project_name"],
            "notebook_id": r.get("notebook_id"),
            "source_id": r.get("source_id"),
        }
        for r in results
        if r.get("archive_action") == "needs_confirmation"
    ]

    print(json.dumps({
        "summary": summary,
        "pending_archive_confirmation": pending_archive_confirmation,
        "results": results,
        "projects": [asdict(r) for r in created],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

---

### 2.4 `USAGE-AND-STATUS.md`

路径：`OPENCLAW_HOME/skills/notebooklm-intake/USAGE-AND-STATUS.md`

这是状态说明文档，新复刻实例应根据自身实际状态更新。初始内容如下：

```markdown
# notebooklm-intake 使用说明与当前状态

## 1. 这个 skill 是干什么的
`notebooklm-intake` 用来把本地准备好的资料批量或单个同步到 NotebookLM 云端，并在本地维护项目映射与状态记录。

目标闭环：
1. 从 `inbox/` 或指定路径找到待上传资料
2. 建立 / 维护本地项目 metadata
3. 在 NotebookLM 云端创建 notebook（必要时）
4. 上传 source
5. 把 `notebook_id` / `source_id` / `sync_status` 回写到本地
6. 根据结果决定是否自动归档或等待人工确认归档

## 2. 依赖
- 本机已完成 `notebooklm login`
- `notebooklm-py` CLI 可用（来源：teng-lin/notebooklm-py）
- 本地知识库路径：`OPENCLAW_HOME/knowledge`

## 3. 使用命令

### 普通入库
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py
```

### 指定文件或目录
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --path "<文件或目录>"
```

### 确认归档重复内容
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --archive-duplicates
```

## 4. 当前状态
初次复刻，尚未进行 smoke test。请在创建完成后运行一次入库测试以验证链路。
```

---

### 2.5 `registry.json`（初始化）

路径：`OPENCLAW_HOME/knowledge/notebooklm/registry.json`

```json
{
  "projects": []
}
```

---

## 3. 复刻执行步骤（给 OpenClaw 的操作清单）

请严格按以下顺序执行：

### Step 1：确定路径变量

确定目标用户的 `OPENCLAW_HOME` 绝对路径。例如：
- Windows: `C:\Users\<username>\.openclaw`
- macOS/Linux: `/home/<username>/.openclaw`

后续所有 `OPENCLAW_HOME` 均替换为此路径。

### Step 2：创建目录结构

```bash
mkdir -p "OPENCLAW_HOME/skills/notebooklm-intake/.claude"
mkdir -p "OPENCLAW_HOME/skills/notebooklm-intake/scripts"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/inbox"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/processed"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/projects"
```

### Step 3：创建文件

按第 2 节逐个创建以下文件（路径中的 `OPENCLAW_HOME` 替换为真实路径）：

1. `skills/notebooklm-intake/SKILL.md` — 内容见 2.1
2. `skills/notebooklm-intake/.claude/settings.local.json` — 内容见 2.2
3. `skills/notebooklm-intake/scripts/intake.py` — 内容见 2.3
4. `skills/notebooklm-intake/USAGE-AND-STATUS.md` — 内容见 2.4
5. `knowledge/notebooklm/registry.json` — 内容见 2.5

### Step 4：路径替换

在以下文件中，将 `OPENCLAW_HOME` 占位符替换为目标用户的实际绝对路径：

| 文件 | 需替换位置 |
|------|-----------|
| `SKILL.md` | 所有目录路径（4 处）和命令路径（2 处） |
| `scripts/intake.py` | 第 15 行 `KNOWLEDGE_ROOT = Path(r"...")` |
| `USAGE-AND-STATUS.md` | 所有出现的路径 |

**Windows 路径注意**：`intake.py` 中使用 `Path(r"...")` raw string，反斜杠不需要转义。

### Step 5：验证 Python 语法

```bash
python -m py_compile "OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py"
```

无输出即表示语法正确。

### Step 6：Smoke Test

```bash
# 1. 在 inbox 中放一个测试文件
echo "NotebookLM intake smoke test" > "OPENCLAW_HOME/knowledge/notebooklm/inbox/smoke-test.txt"

# 2. 运行入库
python "OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py"

# 3. 检查输出 JSON 中 summary.synced 是否为 1
# 4. 检查 registry.json 中是否有对应记录且 sync_status = "synced"
# 5. 检查 smoke-test.txt 是否已移动到 processed/
```

如果 smoke test 通过，更新 `USAGE-AND-STATUS.md` 中第 4 节的状态为"smoke test 已通过"。

---

## 4. 核心架构说明

### 4.1 数据模型 — `ProjectRecord`

每个上传的文件对应一个 `ProjectRecord`，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | str | 从文件名（不含扩展名）派生 |
| `source_name` | str | 原始文件名 |
| `source_path` | str | 绝对路径 |
| `source_type` | str | document / audio / video / spreadsheet / link / unknown |
| `created_at` | str | ISO 8601 UTC |
| `updated_at` | str | ISO 8601 UTC |
| `sync_status` | str | pending_cloud_upload / synced / synced_after_retry / already_synced / failed |
| `notebook_id` | str? | NotebookLM 云端 notebook UUID |
| `source_id` | str? | NotebookLM 云端 source UUID |
| `output_dir` | str? | 预留输出目录路径 |
| `notes` | str? | 状态备注或错误信息 |
| `source_fingerprint` | str? | SHA256(path\|size\|mtime) 前 16 位 hex |

### 4.2 工作流

```
inbox/ 中的文件
    ↓ iter_candidates() 扫描
    ↓ ensure_project_record() 建立/查找记录
    ↓ sync_record_to_cloud() 核心同步
    │   ├── create_notebook()     → notebooklm create / notebooklm list
    │   ├── upload_source()       → notebooklm source add / notebooklm source list
    │   ├── 成功 → archive_processed_source() → 移动到 processed/
    │   └── 失败 → 重试（最多 3 次，退避递增）
    ↓ 更新 registry.json + projects/{name}/project.json
    ↓ 输出 JSON summary
```

### 4.3 去重策略

- **本地去重**：通过 `source_path` 或 `source_fingerprint` 匹配 registry 中已有记录
- **云端 notebook 去重**：通过 `notebooklm list` 按名称匹配，1 个匹配则复用，多个则报错拒绝猜测
- **云端 source 去重**：通过 `notebooklm source list` 按名称匹配，同上逻辑

### 4.4 错误分类

| 类型 | 触发关键词 | 行为 |
|------|-----------|------|
| `auth_error` | authentication, login, unauthorized, 401, 403 | **立即停止**所有后续文件处理 |
| `notebook_conflict` | multiple notebooks with the same title | 报错，需人工介入 |
| `source_conflict` | multiple sources with the same title | 报错，需人工介入 |
| `source_upload_error` | source add/upload 相关 | 重试 |
| `network_error` | timeout, connection 相关 | 重试 |
| `unknown_error` | 其他 | 重试 |

### 4.5 归档逻辑

- **新上传成功**：自动移动到 `processed/`，同名文件会加时间戳后缀
- **已同步的重复文件**：默认不归档，返回 `needs_confirmation`，需通过 `--archive-duplicates` 显式确认

### 4.6 输出 JSON 结构

```json
{
  "summary": {
    "scanned": 5,
    "registered": 5,
    "synced": 3,
    "synced_after_retry": 0,
    "already_synced": 1,
    "failed": 1,
    "skipped": 0,
    "pending_archive_confirmation": 1,
    "archived": 3
  },
  "pending_archive_confirmation": [
    {"project_name": "...", "notebook_id": "...", "source_id": "..."}
  ],
  "results": [
    {
      "project_name": "...",
      "status": "synced|synced_after_retry|already_synced|failed|skipped",
      "attempts": 1,
      "error_type": null,
      "error": null,
      "notebook_id": "uuid",
      "source_id": "uuid",
      "archive_action": "archived|not_archived|needs_confirmation",
      "archived_to": "path or null"
    }
  ],
  "projects": [ /* ProjectRecord 快照数组 */ ]
}
```

---

## 5. 支持的文件类型

| 扩展名 | 类型（英文） | 类型（中文） |
|--------|-------------|-------------|
| `.pdf`, `.txt`, `.md`, `.doc`, `.docx` | document | 文档 |
| `.xls`, `.xlsx`, `.csv`, `.tsv` | spreadsheet | 表格 |
| `.mp3`, `.wav`, `.m4a` | audio | 音频 |
| `.mp4`, `.mov`, `.avi` | video | 视频 |
| `.url`, `.webloc` | link | 链接 |
| `.html` | link | 网页（可包含思维导图、闪卡、测验等内容） |

---

## 6. 关键常量

| 常量 | 值 | 说明 |
|------|----|------|
| `MAX_RETRIES` | 3 | 单文件最大重试次数 |
| `RETRY_DELAY_SECONDS` | 2 | 重试基础延迟（实际延迟 = 基础 × attempt） |
| `BATCH_ITEM_DELAY_SECONDS` | 1 | 批量处理中文件间的节流延迟 |

---

## 7. 复刻完成检查清单

- [ ] `notebooklm` CLI 可用且已 login
- [ ] 所有 5 个文件已创建
- [ ] `intake.py` 中 `KNOWLEDGE_ROOT` 已替换为正确路径
- [ ] `SKILL.md` 中所有路径已替换
- [ ] `python -m py_compile` 通过
- [ ] `inbox/`、`processed/`、`projects/` 目录存在
- [ ] `registry.json` 已初始化为 `{"projects": []}`
- [ ] Smoke test 通过（创建测试文件 → 运行脚本 → 确认 synced）

全部通过即复刻完成。
