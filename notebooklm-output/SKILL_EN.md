---
name: notebooklm-output
description: Generate, export, and download results from existing cloud-based NotebookLM projects. Triggered when the user says things like "generate NotebookLM project content", "export notebooklm project results", "output/create/produce a mind map, report, table, audio, video, flashcards, or quiz for a NotebookLM project". By default, these requests are interpreted as cloud project output — the script first matches the project name against cloud metadata in the registry, then reports the supported output types and calls the script to generate the final file.
---

# NotebookLM Output

## Fixed Directories

The script auto-detects the `.openclaw` root directory; no manual configuration is needed. Below is the relative structure:

- Project directory: `{.openclaw root}/knowledge/notebooklm/projects`
- Output directory: `{.openclaw root}/knowledge/notebooklm/output`
- Status index: `{.openclaw root}/knowledge/notebooklm/registry.json`

## Execution Principles

1. By default, interpret "generate / create / produce / export / output NotebookLM project content" as **output from an existing cloud project** — use this skill first; do not misroute to intake.
2. After the user provides a project name, run the script to find a matching project.
3. You must first tell the user which output types the project currently supports, then ask which one they want. If the user's request already clearly maps to a specific type, still confirm the project first before proceeding.
4. Only call the generation script after the user confirms the type.
5. The default output language depends on the `--language` flag: use `--language en` for English output, or omit / use default for Chinese (`zh_Hans`). **Only pass `--language` for output types that the CLI actually supports it**. Do not force `--language` on types that don't accept it.
6. Only deliver **final files**. If the script or skill has issues, fix them before generating. Do not fall back to raw low-level output, and do not save troubleshooting intermediates as deliverables.
7. During export tasks, the script pops up a local GUI progress window that refreshes every 5 seconds, showing the project name, output type, task status, task ID, elapsed time, save path, or error message.
8. If real cloud generation capability has not yet been connected, you may output a capability list and local path plan, but must not falsely claim that cloud generation succeeded.

## Standard Commands

> Script path is relative to the directory containing this SKILL.md. When executing, use the actual absolute path under this skill directory.

Query a project:

```powershell
python "{this skill directory}/scripts/output.py" inspect --project "<project name>"
```

Generate output (Chinese, default):

```powershell
python "{this skill directory}/scripts/output.py" generate --project "<project name>" --type "<output type>"
```

Generate output (English):

```powershell
python "{this skill directory}/scripts/output.py" generate --project "<project name>" --type "<output type>" --language en
```

## Currently Supported Output Types

- audio-overview (default `brief`, i.e. summary)
- video-overview
- slide-deck
- quiz
- flashcards
- infographic
- report
- mind-map
- data-table

## Output Requirements

Provide a concise report including:
- The matched project name
- Supported output types
- Which type the user selected
- Language strategy: the script supports `--language en` for English and defaults to Chinese (`zh_Hans`). Only pass `--language` for output types that actually support it.
- Final file save path
- If the script only succeeded after a fix, report only the final successful result — do not treat troubleshooting intermediates as deliverables
- If cloud connectivity is not yet established, state clearly that this is the scaffold stage
