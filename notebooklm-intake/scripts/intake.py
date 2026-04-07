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

KNOWLEDGE_ROOT = Path(r"C:\Users\<username>\.openclaw\knowledge")
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
