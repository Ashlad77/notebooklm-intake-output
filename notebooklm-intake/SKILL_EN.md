---
name: notebooklm-intake
description: Upload, import, and sync local materials to a cloud-based NotebookLM project. Triggered when the user says things like "upload to NotebookLM", "import into NotebookLM", "send materials to the cloud", "create a new NotebookLM project and ingest materials", "sync local files to NotebookLM", etc. By default, interpret such requests as ingestion/upload rather than generating output. Scans knowledge/notebooklm/inbox for newly added links, PDFs, audio/video, documents, spreadsheets, and other materials, automatically creates a same-named project, uploads the source, and writes local metadata.
---

# NotebookLM Intake

Use the script first; do not manually piece together the workflow in conversation.

## Fixed Directories

The script automatically detects the `.openclaw` root directory; no manual configuration is needed. Below is the relative structure:

- Input directory: `{.openclaw root}/knowledge/notebooklm/inbox`
- Projects directory: `{.openclaw root}/knowledge/notebooklm/projects`
- Output directory: `{.openclaw root}/knowledge/notebook`
- Status index: `{.openclaw root}/knowledge/notebooklm/registry.json`

## Execution Principles

1. By default, interpret "upload / import / ingest / sync to NotebookLM" as **sending local materials to the cloud**, and prefer using this skill.
2. Do not misidentify "generate / create / produce / export / output content from a NotebookLM project" as intake; such requests should default to `notebooklm-output`.
3. Run the script first to scan the inbox for new files.
4. Generate local project metadata for each new file.
5. At the current stage, if real cloud integration is not yet complete, it is acceptable to write local placeholder status first, but you must clearly tell the user "the script skeleton is complete; cloud upload is pending connection".
6. Do not pretend the upload succeeded; only say the material has been ingested to the cloud when the script returns success and the metadata explicitly records notebook_id/source_id.

## Standard Commands

> Script paths are relative to the directory containing this SKILL.md. When executing, use the actual absolute path under this skill directory.

```powershell
python "{this skill directory}/scripts/intake.py"
```

To specify a single file, use:

```powershell
python "{this skill directory}/scripts/intake.py" --path "<file or directory>"
```

## Output Requirements

Report concisely:
- Which files were newly identified
- Which have had metadata written
- Which have actually been uploaded to the cloud / which are still in pending-connection status
- Where the corresponding project directory is located
