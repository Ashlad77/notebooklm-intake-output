# notebooklm-intake Skill Complete Replication Guide

This document is intended for an OpenClaw instance to read and replicate the `notebooklm-intake` skill one-to-one. Please strictly follow the structure, paths, and file contents below.

---

## 0. Prerequisites

Before starting, the target machine must meet:

1. **Python 3.10+** is installed and callable from the command line
2. **`notebooklm-py` CLI is installed and authenticated** (see the integration instructions below)
3. **OpenClaw directory structure exists** — i.e., `~/.openclaw/` has been initialized

### 0.1 Integrating with the NotebookLM Cloud

This skill depends on the `notebooklm-py` project (source: https://github.com/teng-lin/notebooklm-py) to communicate with the NotebookLM cloud via its CLI. Below is the complete integration process from scratch:

**Step 1: Install notebooklm-py (with browser login support)**

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
```

- The first line installs the CLI tool and the browser authentication module
- The second line installs the Chromium engine required by Playwright (needed for login)
- Base dependencies `click`, `httpx`, `rich` are installed automatically

**Step 2: Login authentication**

```bash
notebooklm login
```

- Uses Playwright to open a Chromium browser and navigate to the Google account login page
- After login is complete, return to the terminal and press **Enter** to save the authentication
- Authentication credentials are saved at `~/.notebooklm/storage_state.json`
- Requires access to Google services (users in mainland China need a network proxy)

If your organization requires using Microsoft Edge for SSO login:

```bash
notebooklm login --browser msedge
```

**Step 3: Verify the connection**

```bash
notebooklm list
```

A normal response with a notebook list (an empty list also counts as success) indicates the integration is complete.

If you encounter authentication issues, you can run diagnostics:

```bash
notebooklm auth check --test
```

**Additional notes**:
- Authentication has an expiration period; when it expires, simply re-run `notebooklm login`
- File-based authentication via the `NOTEBOOKLM_AUTH_JSON` environment variable is also supported (suitable for server environments without a browser)

---

## 1. Directory Structure Overview

The following directories and files need to be created (using `OPENCLAW_HOME` to refer to the user's `.openclaw` root directory):

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
        ├── inbox/          ← Place materials to upload here
        ├── processed/      ← Automatically archived here after successful upload
        ├── projects/       ← Metadata for each project
        └── registry.json   ← Master index (initial value: {"projects": []})
```

**Important**: All hardcoded paths `C:\Users\sakai\.openclaw\` appearing in the file contents below need to be replaced with the target user's actual `OPENCLAW_HOME` path. Specific replacement locations:
- All paths in `SKILL.md`
- The `KNOWLEDGE_ROOT` variable in `scripts/intake.py` (line 15)

---

## 2. File Contents — Create File by File

### 2.1 `SKILL.md`

Path: `OPENCLAW_HOME/skills/notebooklm-intake/SKILL.md`

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
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --path "<file or directory>"
```

## 输出要求

简洁汇报：
- 新识别了哪些文件
- 哪些已写入 metadata
- 哪些已真正上传云端 / 哪些仍是待接通状态
- 对应项目目录在哪里
```

> **Note**: The `OPENCLAW_HOME` placeholder above needs to be replaced with the target user's actual absolute path when creating the file.

---

### 2.2 `.claude/settings.local.json`

Path: `OPENCLAW_HOME/skills/notebooklm-intake/.claude/settings.local.json`

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

Path: `OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py`

This is the core script — **it must be copied in full; no parts may be omitted**.

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

KNOWLEDGE_ROOT = Path(r"OPENCLAW_HOME/knowledge")  # ← Replace with the target user's actual path
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

Path: `OPENCLAW_HOME/skills/notebooklm-intake/USAGE-AND-STATUS.md`

This is a status documentation file; newly replicated instances should update it according to their actual status. Initial content is as follows:

```markdown
# notebooklm-intake Usage Instructions and Current Status

## 1. What this skill does
`notebooklm-intake` is used to sync locally prepared materials — individually or in batch — to the NotebookLM cloud, while maintaining local project mappings and status records.

Target closed loop:
1. Find materials to upload from `inbox/` or a specified path
2. Establish / maintain local project metadata
3. Create a notebook on the NotebookLM cloud (when necessary)
4. Upload the source
5. Write back `notebook_id` / `source_id` / `sync_status` to local storage
6. Decide whether to auto-archive or wait for manual archive confirmation based on the result

## 2. Dependencies
- `notebooklm login` has been completed on this machine
- `notebooklm-py` CLI is available (source: teng-lin/notebooklm-py)
- Local knowledge base path: `OPENCLAW_HOME/knowledge`

## 3. Usage Commands

### Standard intake
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py
```

### Specify a file or directory
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --path "<file or directory>"
```

### Confirm archiving of duplicate content
```
python OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py --archive-duplicates
```

## 4. Current Status
Initial replication; smoke test has not yet been performed. Please run an intake test after creation to verify the pipeline.
```

---

### 2.5 `registry.json` (Initialization)

Path: `OPENCLAW_HOME/knowledge/notebooklm/registry.json`

```json
{
  "projects": []
}
```

---

## 3. Replication Execution Steps (Action Checklist for OpenClaw)

Please execute strictly in the following order:

### Step 1: Determine the path variable

Determine the target user's `OPENCLAW_HOME` absolute path. For example:
- Windows: `C:\Users\<username>\.openclaw`
- macOS/Linux: `/home/<username>/.openclaw`

All subsequent `OPENCLAW_HOME` references should be replaced with this path.

### Step 2: Create the directory structure

```bash
mkdir -p "OPENCLAW_HOME/skills/notebooklm-intake/.claude"
mkdir -p "OPENCLAW_HOME/skills/notebooklm-intake/scripts"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/inbox"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/processed"
mkdir -p "OPENCLAW_HOME/knowledge/notebooklm/projects"
```

### Step 3: Create files

Create the following files one by one according to Section 2 (replace `OPENCLAW_HOME` in paths with the actual path):

1. `skills/notebooklm-intake/SKILL.md` — content per 2.1
2. `skills/notebooklm-intake/.claude/settings.local.json` — content per 2.2
3. `skills/notebooklm-intake/scripts/intake.py` — content per 2.3
4. `skills/notebooklm-intake/USAGE-AND-STATUS.md` — content per 2.4
5. `knowledge/notebooklm/registry.json` — content per 2.5

### Step 4: Path replacement

In the following files, replace the `OPENCLAW_HOME` placeholder with the target user's actual absolute path:

| File | Locations to replace |
|------|---------------------|
| `SKILL.md` | All directory paths (4 locations) and command paths (2 locations) |
| `scripts/intake.py` | Line 15: `KNOWLEDGE_ROOT = Path(r"...")` |
| `USAGE-AND-STATUS.md` | All occurrences of the path |

**Windows path note**: `intake.py` uses `Path(r"...")` raw string, so backslashes do not need escaping.

### Step 5: Verify Python syntax

```bash
python -m py_compile "OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py"
```

No output means the syntax is correct.

### Step 6: Smoke Test

```bash
# 1. Place a test file in inbox
echo "NotebookLM intake smoke test" > "OPENCLAW_HOME/knowledge/notebooklm/inbox/smoke-test.txt"

# 2. Run intake
python "OPENCLAW_HOME/skills/notebooklm-intake/scripts/intake.py"

# 3. Check whether summary.synced is 1 in the output JSON
# 4. Check whether registry.json contains a corresponding record with sync_status = "synced"
# 5. Check whether smoke-test.txt has been moved to processed/
```

If the smoke test passes, update Section 4 of `USAGE-AND-STATUS.md` to say "smoke test passed".

---

## 4. Core Architecture Description

### 4.1 Data Model — `ProjectRecord`

Each uploaded file corresponds to a `ProjectRecord` containing the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `project_name` | str | Derived from the filename (without extension) |
| `source_name` | str | Original filename |
| `source_path` | str | Absolute path |
| `source_type` | str | document / audio / video / spreadsheet / link / unknown |
| `created_at` | str | ISO 8601 UTC |
| `updated_at` | str | ISO 8601 UTC |
| `sync_status` | str | pending_cloud_upload / synced / synced_after_retry / already_synced / failed |
| `notebook_id` | str? | NotebookLM cloud notebook UUID |
| `source_id` | str? | NotebookLM cloud source UUID |
| `output_dir` | str? | Reserved output directory path |
| `notes` | str? | Status notes or error messages |
| `source_fingerprint` | str? | First 16 hex chars of SHA256(path\|size\|mtime) |

### 4.2 Workflow

```
Files in inbox/
    ↓ iter_candidates() scans
    ↓ ensure_project_record() creates/finds record
    ↓ sync_record_to_cloud() core sync
    │   ├── create_notebook()     → notebooklm create / notebooklm list
    │   ├── upload_source()       → notebooklm source add / notebooklm source list
    │   ├── Success → archive_processed_source() → move to processed/
    │   └── Failure → retry (up to 3 times, with increasing backoff)
    ↓ Update registry.json + projects/{name}/project.json
    ↓ Output JSON summary
```

### 4.3 Deduplication Strategy

- **Local deduplication**: Matches existing records in the registry by `source_path` or `source_fingerprint`
- **Cloud notebook deduplication**: Matches by name via `notebooklm list`; if 1 match, reuse it; if multiple, raise an error and refuse to guess
- **Cloud source deduplication**: Matches by name via `notebooklm source list`; same logic as above

### 4.4 Error Classification

| Type | Trigger keywords | Behavior |
|------|-----------------|----------|
| `auth_error` | authentication, login, unauthorized, 401, 403 | **Immediately stop** processing all remaining files |
| `notebook_conflict` | multiple notebooks with the same title | Error; requires manual intervention |
| `source_conflict` | multiple sources with the same title | Error; requires manual intervention |
| `source_upload_error` | source add/upload related | Retry |
| `network_error` | timeout, connection related | Retry |
| `unknown_error` | Other | Retry |

### 4.5 Archiving Logic

- **Newly uploaded successfully**: Automatically moved to `processed/`; files with the same name get a timestamp suffix
- **Already-synced duplicate files**: Not archived by default; returns `needs_confirmation`; requires explicit confirmation via `--archive-duplicates`

### 4.6 Output JSON Structure

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
  "projects": [ /* ProjectRecord snapshot array */ ]
}
```

---

## 5. Supported File Types

| Extension | Type | Category |
|-----------|------|----------|
| `.pdf`, `.txt`, `.md`, `.doc`, `.docx` | document | Document |
| `.xls`, `.xlsx`, `.csv`, `.tsv` | spreadsheet | Spreadsheet |
| `.mp3`, `.wav`, `.m4a` | audio | Audio |
| `.mp4`, `.mov`, `.avi` | video | Video |
| `.url`, `.webloc` | link | Link |
| `.html` | link | Web page (may contain mind maps, flashcards, quizzes, etc.) |

---

## 6. Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_RETRIES` | 3 | Maximum retry count per file |
| `RETRY_DELAY_SECONDS` | 2 | Base retry delay (actual delay = base x attempt) |
| `BATCH_ITEM_DELAY_SECONDS` | 1 | Throttle delay between files during batch processing |

---

## 7. Replication Completion Checklist

- [ ] `notebooklm` CLI is available and logged in
- [ ] All 5 files have been created
- [ ] `KNOWLEDGE_ROOT` in `intake.py` has been replaced with the correct path
- [ ] All paths in `SKILL.md` have been replaced
- [ ] `python -m py_compile` passes
- [ ] `inbox/`, `processed/`, `projects/` directories exist
- [ ] `registry.json` has been initialized to `{"projects": []}`
- [ ] Smoke test passed (create test file → run script → confirm synced)

All items passing means replication is complete.
