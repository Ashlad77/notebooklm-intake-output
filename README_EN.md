# notebooklm-intake-output

English | **[中文](README.md)**

Batch-sync local materials to [NotebookLM](https://notebooklm.google.com/) cloud and generate various outputs (reports, quizzes, mind maps, audio, video, etc.) from cloud projects — all automated via local scripts.

> Built on top of [@teng-lin](https://github.com/teng-lin)'s [notebooklm-py](https://github.com/teng-lin/notebooklm-py), which provides an unofficial Python API and CLI for NotebookLM. Both intake and output rely entirely on its interface for cloud communication.

---

## Overview

This repository contains two skills for [OpenClaw](https://github.com/Ashlad77):

| Skill | Purpose |
|-------|---------|
| **notebooklm-intake** | Local files → NotebookLM cloud (upload, create projects, deduplicate, archive) |
| **notebooklm-output** | NotebookLM cloud → Local files (generate reports, quizzes, audio, etc. and download) |

The two skills form a complete loop: use intake to upload materials first, then use output to generate various outputs from the cloud.

---

## Prerequisites

1. **Python 3.10+**
2. **Tkinter** — included by default on Windows; on Linux you may need `sudo apt install python3-tk`
3. **`notebooklm-py` CLI** installed and authenticated:

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
notebooklm login
```

> Users in mainland China need a proxy to access Google services.
> For Microsoft Edge SSO login, use `notebooklm login --browser msedge`.

4. Verify connection:

```bash
notebooklm list
```

A successful response (even an empty list) confirms the setup is complete.

---

## Directory Structure

```
~/.openclaw/
├── skills/
│   ├── notebooklm-intake/
│   │   ├── SKILL.md              ← Skill instructions (Chinese)
│   │   ├── SKILL_EN.md           ← Skill instructions (English)
│   │   ├── REPLICATION-GUIDE.md  ← Replication guide (Chinese)
│   │   ├── REPLICATION-GUIDE_EN.md ← Replication guide (English)
│   │   └── scripts/
│   │       └── intake.py         ← Core intake script
│   └── notebooklm-output/
│       ├── SKILL.md              ← Skill instructions (Chinese)
│       ├── SKILL_EN.md           ← Skill instructions (English)
│       ├── REPLICATION-GUIDE.md  ← Replication guide (Chinese)
│       ├── REPLICATION-GUIDE_EN.md ← Replication guide (English)
│       └── scripts/
│           ├── output.py         ← Core output script
│           └── vendor/
│               ├── d3.min.js     ← D3.js (mind-map rendering dependency)
│               └── markmap-view.min.js ← Markmap (mind-map rendering dependency)
└── knowledge/
    └── notebooklm/
        ├── inbox/                ← Place materials to upload here
        ├── processed/            ← Auto-archived after successful upload
        ├── projects/             ← Per-project local metadata
        ├── output/               ← Root directory for all outputs
        └── registry.json         ← Master index
```

> Scripts automatically detect the `.openclaw` root directory based on their own location — no manual path configuration needed. You can also override it with the `OPENCLAW_HOME` environment variable.

---

# notebooklm-intake

## Features

- Scans the `inbox/` directory (or a specified path) for materials to upload
- Automatically creates a Notebook with the same name in the cloud (reuses if one exists)
- Uploads Sources and writes back `notebook_id`, `source_id`, `sync_status` locally
- Batch processing with automatic throttling between files
- Local + cloud dual deduplication to prevent duplicate uploads
- Auto-retry (up to 3 times with exponential backoff), classified failure reports
- Auto-archives successfully uploaded files to `processed/`
- Outputs structured JSON summary for tracking and debugging

## Quick Start

### Batch intake (scan entire inbox)

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py
```

### Specify a single file or directory

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py --path "<file or directory path>"
```

### Archive confirmed duplicates

```powershell
python ~/.openclaw/skills/notebooklm-intake/scripts/intake.py --archive-duplicates
```

## Output Format

The script outputs structured JSON with four sections:

| Field | Description |
|-------|-------------|
| `summary` | Overall statistics (scanned, synced, failed, etc.) |
| `pending_archive_confirmation` | List of duplicates awaiting archive confirmation |
| `results` | Per-file results (status, notebook_id, source_id, archive path) |
| `projects` | Snapshot of project metadata processed in this run |

**Result status codes:**

| Status | Meaning |
|--------|---------|
| `synced` | Successfully uploaded for the first time |
| `synced_after_retry` | Uploaded after retry |
| `already_synced` | Cloud record already exists, skipped |
| `failed` | Upload failed (with error type and reason) |
| `skipped` | Skipped due to a prior auth error |

## Supported File Types

| Type | Extensions |
|------|------------|
| Documents | `.pdf` `.txt` `.md` `.doc` `.docx` |
| Spreadsheets | `.xls` `.xlsx` `.csv` `.tsv` |
| Audio | `.mp3` `.wav` `.m4a` |
| Video | `.mp4` `.mov` `.avi` |
| Links/Web | `.url` `.webloc` `.html` |

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `auth_error` | Immediately stops all further processing, prompts re-login |
| `notebook_conflict` | Multiple Notebooks with the same name found, requires manual intervention |
| `source_conflict` | Multiple Sources with the same name found, requires manual intervention |
| `source_upload_error` | Auto-retry, up to 3 times |
| `network_error` | Auto-retry, up to 3 times |
| `unknown_error` | Auto-retry, up to 3 times |

## Local Metadata Fields

Each uploaded material is recorded in `projects/<project-name>/project.json`:

| Field | Description |
|-------|-------------|
| `project_name` | Derived from filename (without extension) |
| `source_name` | Original filename |
| `source_path` | Absolute file path (auto-updated after archiving) |
| `sync_status` | `pending_cloud_upload` / `synced` / `failed` etc. |
| `notebook_id` | NotebookLM cloud notebook UUID |
| `source_id` | NotebookLM cloud source UUID |
| `source_fingerprint` | SHA256 fingerprint based on path, size, and mtime (first 16 hex chars) |
| `notes` | Status notes or error messages |

---

# notebooklm-output

## Features

- Matches target project from local index and validates cloud sync status
- Calls NotebookLM cloud API to generate 9 output types
- Auto-downloads results to a unified local output directory
- JSON types (quiz, flashcards, mind-map) are automatically converted to **interactive HTML files**
- Pops up a local GUI progress window with real-time task status
- Media types (audio, video) use a dedicated polling download strategy to work around a known CLI bug
- **Bilingual UI support** (`--language zh` / `--language en`)

## Supported Output Types

| Output Type | File Format | Description |
|-------------|-------------|-------------|
| `report` | `.md` | Markdown report |
| `quiz` | `.json` → `.html` | Interactive quiz (multiple choice, instant scoring, explanations) |
| `flashcards` | `.json` → `.html` | Interactive flashcards (3D flip, keyboard shortcuts) |
| `mind-map` | `.json` → `.html` | Interactive mind map (Markmap rendering, expand/collapse/zoom) |
| `data-table` | `.csv` | Structured data table |
| `slide-deck` | `.pdf` | Slide presentation |
| `infographic` | `.png` | Infographic image |
| `audio-overview` | `.mp3` | Audio summary (default: brief format) |
| `video-overview` | `.mp4` | Video summary |

## Quick Start

### Inspect a project

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py inspect --project "<project-name>"
```

### Generate output (English)

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py generate --project "<project-name>" --type "<output-type>" --language en
```

### Generate output (Chinese, default)

```powershell
python ~/.openclaw/skills/notebooklm-output/scripts/output.py generate --project "<project-name>" --type "<output-type>"
```

The `--language` flag controls: GUI text, output filename labels, HTML page text, and cloud-generated content language.

## Split Task Flow

The script automatically selects different execution paths based on output type:

**Non-media types** (report / quiz / flashcards / mind-map / data-table / slide-deck / infographic):
1. Submit with `--wait` (CLI waits for completion)
2. Download the artifact directly
3. JSON types are auto-converted to interactive HTML

**Media types** (audio-overview / video-overview):
1. Submit with `--no-wait` (returns task_id immediately)
2. Wait 30 seconds, then attempt download every 15 seconds until success or timeout (15 minutes)

> Media types completely bypass `notebooklm artifact wait` due to a known bug in its internal `_is_media_ready()` check for video.

## GUI Progress Window

A Tkinter progress window (620x320, always-on-top) automatically appears during generation, displaying:

- Project name, output type
- Current phase, task ID
- Status, save path
- Elapsed time, error messages

The window language switches with the `--language` flag. The window auto-closes after task completion (5s delay on success, 8s on failure).

## JSON → HTML Auto-Conversion

`quiz`, `flashcards`, and `mind-map` types are automatically converted to interactive HTML after JSON download:

| Type | HTML Features |
|------|---------------|
| quiz | Multiple-choice UI, instant correct/wrong feedback, answer explanations, scoring, retake |
| flashcards | 3D flip effect, keyboard shortcuts (space to flip, arrow keys to navigate), progress display |
| mind-map | Markmap interactive tree, expand/collapse/fit-to-window, fully offline-capable |

The mind-map HTML inlines D3.js and Markmap libraries, making the generated file **fully self-contained** — no network required to open. HTML button text also switches between Chinese and English with `--language`.

## Timeout Configuration

| Type | Timeout |
|------|---------|
| Media types (audio/video) | 900 seconds (15 minutes) |
| Heavy types (slide-deck/infographic) | 600 seconds (10 minutes) |
| Other types | 300 seconds (5 minutes) |

## Output File Naming

```
{project-name}-{type-label}-{YYYY-MM-DD_HH-MM}{extension}
```

- Chinese (default): `my-project-报告-2026-04-07_14-30.md`
- English (`--language en`): `my-project-Report-2026-04-07_14-30.md`

---

## Replication on a New Machine

Each skill has its own replication guide (bilingual) with complete file contents, deployment steps, and smoke test procedures:

- **intake**: [Chinese](notebooklm-intake/REPLICATION-GUIDE.md) | [English](notebooklm-intake/REPLICATION-GUIDE_EN.md)
- **output**: [Chinese](notebooklm-output/REPLICATION-GUIDE.md) | [English](notebooklm-output/REPLICATION-GUIDE_EN.md)

Replication order: **intake first, then output** (output depends on project data created by intake).

> Scripts automatically detect the deployment path — just place them under the standard directory structure, no manual code changes needed.

---

## Current Status

Both skills have reached MVP status with real cloud workflows verified:

- **intake**: Full pipeline (batch upload, deduplication, retry, archiving) tested with real data
- **output**: All 9 output types tested with real cloud generation + download

This is a personally tested version. If you encounter any issues, feel free to [open an Issue](../../issues) — updates and maintenance will be provided periodically.

## Acknowledgements

- This project is built on top of
  [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py),  
  which provides an unofficial Python API and CLI for NotebookLM.  
  All intake/output cloud communication relies on its interfaces.
- Some of the design ideas and implementation details for interacting
  with NotebookLM are inspired by and adapted from that project.
  Specific sources are noted in the corresponding code comments.
- Many thanks to @teng-lin for the great work on notebooklm-py
  and for pushing the NotebookLM ecosystem forward.

## License

This project is licensed under the [MIT License](LICENSE).
