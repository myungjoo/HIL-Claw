---
id: T-0001
title: Add repository-wide conventions and the empty tool package
phase: P0
status: DONE
commitMode: code
coversReq: [C-7, FR-10, "#9"]
dependsOn: []
touchesFiles: [.gitattributes, .editorconfig, hilclaw/__init__.py]
estimatedSize: {loc: 30, files: 3}
hq: []   # D9 confirmed 2026-10-05: skeleton tasks are exempt from the "confirm OD-4/6/8 before the first commit" rule
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
- No tests are required for this task: the package root exposes no public function (DRIVER §5 test rule ③ is vacuous here) and the coverage gate starts with P0-2.

## Out of Scope
- `pyproject.toml`, pytest, ruff (P0-2). CI (P0-3). README update (P0-5). Any tool code (P1).

## Follow-ups
- (planner) P0-2 depends on this task's package directory.

## Result
- PR #13 (code mode), squash-merged to main as e501cff ("T-0001: Add repository-wide conventions and the empty tool package (#13)"); branch commit 73b600e. Authored change: 3 files, +22 lines (.gitattributes, .editorconfig, hilclaw/__init__.py).
- Review: 1 round by a reviewer agent, verdict Approve (0 Critical/High/Medium, 1 Low, 4 Nit); no code change was needed, so no re-review.
- Renormalization: `git add --renormalize .` ran once and changed 0 files; all tracked text files were already stored with LF (`git ls-files --eol` shows no i/crlf).
- Language: no language choice was needed (configuration files only). No dependency added. No tests (package root exposes no public function).
- Local checks (CI not built): `git ls-files --eol` check and `python -c "import hilclaw; print(hilclaw.__version__)"` -> 0.0.0, passed before commit and again before merge.
- Follow-ups:
  - (P0-2 / P0.5-2) Test rule 4 has no exemption for `hilclaw/__init__.py`: either add an import/version test in P0-2 or have the P0.5-2 test-existence check exclude `__init__.py` explicitly (reviewer L1).
  - (P0-2) Keep `__version__` single-sourced with `pyproject.toml` to avoid drift (reviewer N3).
  - (later) `.editorconfig`: consider a `[*.md]` override for `trim_trailing_whitespace` if Markdown hard line breaks are ever used, and add indent rules for `*.sh` / `*.c` / `Makefile` when the first such file lands (reviewer N1, N2).
