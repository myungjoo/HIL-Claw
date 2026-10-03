---
id: T-0001
title: Add repository-wide conventions and the empty tool package
phase: P0
status: TODO
commitMode: code
coversReq: [C-7, FR-10, "#9"]
dependsOn: []
touchesFiles: [.gitattributes, .editorconfig, hilclaw/__init__.py]
estimatedSize: {loc: 30, files: 3}
hq: [D9]   # DRIVER.md §11 D9 — skeleton tasks exempt from the "confirm OD-4/6/8 before the first commit" rule; must be answered first
---
## Why
C-7 ① (WSL premise → POSIX across Linux/macOS/WSL) implies, as a derived and still provisional reading recorded in C-7, that line endings must be LF everywhere; Issue #9 lists LF enforcement in the CI scope. Git on the owner's Windows checkout already emits "LF will be replaced by CRLF" warnings for the ARCHITECTURE files, so the rule must land before any code does. FR-10 / #5 A-12 define the tool layer as one package — this task creates its empty root so that later tasks (P0-2 pyproject, P1-1 tool contract) have a fixed location.

## Required Reading
- CLAUDE.md — 상시 규칙 "세 층 모델", "도구 계층 언어 정책"; the merge procedure is #5 A-13 (its CLAUDE.md text is a prerequisite commit, see DRIVER.md header)
- ARCHITECTURE/Requirements.md — C-7 (Constraints table), FR-10 (single-package sentence)
- PROCESS/DRIVER.md §5 (task format), §3-5 (executor procedure)

## Acceptance Criteria
- `.gitattributes` sets `* text=auto eol=lf` and marks common binary types (`*.png`, `*.jpg`, `*.bin`, `*.so`) as `binary` (convention chosen by this task, not a requirement).
- `git add --renormalize .` is run once; afterwards `git ls-files --eol` shows no `i/crlf` for any tracked text file (the `w/` column may still show crlf on a Windows-native checkout until the files are checked out again — that is expected).
- `.editorconfig`: UTF-8, LF, final newline, trim trailing whitespace; 4-space indent for `*.py`, 2-space for `*.yml`/`*.yaml`/`*.json` (convention chosen by this task; ruff defaults are compatible).
- `hilclaw/__init__.py` exists with `__version__ = "0.0.0"` and nothing else; no other Python code and no dependency added.
- Commit body states that no language choice was needed (configuration files only).

## Out of Scope
- `pyproject.toml`, pytest, ruff (P0-2). CI (P0-3). README update (P0-5). Any tool code (P1).

## Follow-ups
- (planner) P0-2 depends on this task's package directory.

## Result
_(executor fills in: commit/PR, review rounds, follow-ups)_
