---
id: T-0331
title: Create orchestration/ with a first Round-Manager prompt and add hilclaw.turn_definition.put, which copies that definition into a turn session directory under the names Claude Code reads (ADR-0118 decisions 4 and 5, code slices (2) and (3))
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, NFR-7, OD-18, OD-23]
dependsOn: [T-0329, T-0330]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 220, files: 2}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). It is a PLAN checklist item, so the D18 priority rule does not apply. P1 has nothing that can be planned now:
- P0.5-4 waits on the owner's hook registration;
- the rest of P1-1 waits on HQ-0021, HQ-0025, HQ-0026 and OD-14 ①;
- P1-8's D18 completion criterion is the driver's to tick.

ADR-0118 (T-0329) fixed the round boundary of a first-case run. T-0330 built its turn loop, `hilclaw.turn_loop.run`. The loop takes a caller's `put_definition(session_dir)`, because the layout of the definition was left to "the definition task" (ADR-0118 decision 5). This task is that definition task's first slice. It covers the rest of code slice (2), the copy of decision 4, and the start of code slice (3), the definition under `orchestration/`:

- it creates the top-level directory `orchestration/` (decision 5) with one file, the Round-Manager's prompt;
- it decides the internal layout of `orchestration/` and which file becomes which name in the session directory. ADR-0118 decision 5 leaves both to this task;
- it adds `hilclaw.turn_definition.put`, the function the turn loop's caller passes as `put_definition`.

**The prompt says only what accepted records say.** The steps of a round depend on later P2-1 slices and on open ODs:
- round 0 and the baseline (OD-28);
- the roster (OD-23);
- the coder (P2-2);
- the evaluator (P2-3);
- hooks and gates (P2-4, OD-3);
- the commit step (OD-8 ⑪);
- the CLAUDE.md invariant list (OD-18).

So this first prompt states the turn contract of ADR-0118 decision 2 and says that the round's steps are not defined yet. Until they are, the turn ends without writing a file. That no-op is this task's placeholder: later slices replace it.

Nothing calls `put` from a command line yet. The loop's entry waits on an OD-8 member. No `claude` is started by the driver or the executor (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0331` trailer (also as the last line of the PR body), size cap, test rules.
- `CLAUDE.md`, these rules: "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화", "미결은 발명하지 않는다".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`:
  - Decision 2 (lines 57-65);
  - Decisions 4 and 5 (lines 91-112);
  - Walk-through (lines 124-134);
  - Consequences (lines 154-185), in particular "A-13 reading": changes under `orchestration/` take the code mode;
  - Boundaries (lines 186-200).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`, decision 3 (lines 41-56) and decision 6 (lines 82-92): `round` and the write that ends a round.
- `hilclaw/turn_loop.py` (301 lines, read it all): how `put_definition` is called, `CONFIG_FILE`, `MARKERS`, `_folded`, the docstring conventions. This task does not edit it.
- `tests/test_turn_loop.py`, the stub-`claude` fixture, only if you write the optional integration test of AC 6.

## Acceptance Criteria

1. **Session entry check.**
   - Run `gh pr list`.
   - Open Draft PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`; this task touches none of them.
   - If any open PR edits a file of touchesFiles or adds anything under `orchestration/`, stop and report.

2. **The layout of `orchestration/`** (this task's choice under ADR-0118 decision 5). The module docstring of `hilclaw/turn_definition.py` states it as the single place where it is written. A table in the module, `LAYOUT`, maps each source name under `orchestration/` to its name in the session directory:
   - `round-manager.md` → `CLAUDE.md` (the Round-Manager is the main conversation of the turn session, ADR-0118 decision 2);
   - `agents/` → `.claude/agents/`;
   - `skills/` → `.claude/skills/`;
   - `settings.json` → `.claude/settings.json`.
   Only `round-manager.md` exists after this task. The other three entries are copied when present and skipped when absent. Name in the docstring that the roster, skills and settings stay with OD-23 and P2-4.

3. **`orchestration/round-manager.md`**, in English, at most about 40 lines. Every statement in it is one of the following, with its source named in a short parenthesis:
   - it is the Round-Manager, the main conversation of one turn session of a first-case run (ADR-0118 decisions 1 and 2);
   - a turn carries one round at most. It does not begin a second round, and the session ends after the write that ends its round (ADR-0118 decision 2 (i); ADR-0012 decisions 3 and 6);
   - it does not use `/loop` or a scheduling tool to carry rounds (ADR-0118 Walk-through);
   - the steps of a round are not yet defined in this definition. Until they are, the session reports that in one line and ends without writing any file. Mark this as the placeholder of this slice.
   It holds nothing else:
   - no round steps;
   - no tool list;
   - no invariant list (OD-18);
   - no path of the run's files (how the session reaches them is open, ADR-0118 decision 4);
   - no permission statement.

4. **New module `hilclaw/turn_definition.py`** (Python; give the reason in one line of the commit body). It has one public entry, `put(session_dir, *, source=None)`, whose one positional argument matches the `put_definition` of `turn_loop.run`.
   - **`source`** defaults to the `orchestration/` directory beside the directory that holds this package (`Path(__file__).resolve().parent.parent / "orchestration"`). It must be a `str` or path object naming an existing directory: a wrong type raises `TypeError`, a missing path `FileNotFoundError` and a non-directory `ValueError`.
   - **`session_dir`** must be a `str` or path object naming an existing directory. Otherwise raise `TypeError` or `ValueError`.
   - **Checks before anything is written.** Each raises `ValueError` with a fixed text, and nothing is copied:
     - a top-level entry of `source` that is not a key of `LAYOUT`;
     - an entry of the wrong kind: a file where `LAYOUT` names a directory, or a directory where it names a file;
     - any entry at any depth under `source` named `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md`, or a directory named `.claude` (the naming rule of ADR-0118 decision 5). Compare names as `turn_loop` does, folded where the file system ignores case;
     - any symbolic link at any depth under `source`;
     - a `round-manager.md` that is missing.
   - **The copy** (ADR-0118 decision 4, "It replaces whatever definition the directory held before"):
     - for each `LAYOUT` entry present in `source`, remove the target in `session_dir` if it exists, then copy the entry there, making `.claude/` when needed;
     - targets of absent entries that exist in `session_dir` are removed as well, so the copy is the definition as it now is;
     - nothing else in `session_dir` is touched, `turn_loop.CONFIG_FILE` included;
     - the content is copied byte for byte. File modes and times do not matter.
   - It returns `None`. It makes no judgement, calls no model, starts no process and writes nothing outside `session_dir`.

5. **Docstring.** A module docstring in the style of `turn_loop.py`. It names:
   - what ADR-0118 decides: decision 5's place and naming rule, and decision 4's replacement;
   - what is this module's choice: the layout, the placeholder prompt, and the refusal of unknown entries and of links;
   - what is not done: no roster, no skills, no settings or permissions, no round steps, no `--add-dir`, no caller and no command-line entry.
   It ends with the runtime acceptance items it depends on: ADR-0118 (i) and (iii). Keep comments in the code minimal (CLAUDE.md).

6. **Tests `tests/test_turn_definition.py`**, all on `tmp_path` trees. Include at least:
   - **happy:**
     - the real `orchestration/` of the repository copies to `CLAUDE.md` with the bytes of `round-manager.md`, and nothing else is made;
     - a full source with all four entries yields the four targets with equal content, including a nested file under `agents/` and `skills/`;
     - `put` passed unchanged as `put_definition` is accepted by `turn_loop.run`'s callable check. Optional: one run with the stub `claude` of `tests/test_turn_loop.py` that sees `CLAUDE.md` in its working directory.
   - **branch:**
     - default `source` versus given;
     - a target already present is replaced;
     - a stale `.claude/skills/` in `session_dir` with no `skills/` in `source` is removed;
     - an unrelated file in `session_dir` and a file named `turn_loop.CONFIG_FILE` stay untouched.
   - **error and negative:**
     - a wrong type for `session_dir` or `source`;
     - a missing or non-directory `session_dir` or `source`;
     - an unknown top-level entry;
     - `agents` as a file and `settings.json` as a directory;
     - `CLAUDE.md`, `AGENTS.md`, `CLAUDE.local.md` and `.claude` nested at depth, plus a case-variant name where the file system folds case;
     - a symbolic link (skip where links cannot be made);
     - a missing `round-manager.md`;
     - in each refused case, nothing written to `session_dir`.
   - Every public function and the module are covered. Package coverage stays at least 80% line and function (D12). `ruff` passes.

7. **Scope and size.**
   - `git diff --stat origin/main` lists only touchesFiles.
   - At most about 300 changed lines outside the test file.
   - No edit to `hilclaw/turn_loop.py` or any other module, `ARCHITECTURE/`, `.claude/`, `CLAUDE.md`, `README.md`, `pyproject.toml`, CI or `PROCESS/` (besides this task file's Result).
   - No file under `orchestration/` other than `round-manager.md`.
   - No new dependency.
   - No data-plane schema change: no member, file, kind or version.

8. **D16.** No real `claude` is started by the executor or the reviewer (no subcommand, no flag). Only a test-written stub may run. No board, accelerator or API key is required.

9. **Merge.** Code mode under CLAUDE.md A-13 and ADR-0118 "A-13 reading":
   - branch `claude/T-0331-turn-definition-copy`;
   - Draft PR titled with `T-0331`, the PR body ending with `Task: T-0331`;
   - context-isolated reviewer cycle (dev-code-review, at most 7 rounds) until Approve;
   - CI green;
   - `gh pr merge --squash --body` with that body, then delete the branch.

## Out of Scope

- The steps of a round, round 0 and the baseline (OD-28), the roster and agent definitions (OD-23), skills, hook settings (P2-4) and permissions (ADR-0118 decision 4, "Workspace trust").
- How the session reaches the run's files (`--add-dir` or other), and any change to `turn_loop.run` or its command line.
- The loop's command-line entry and any caller, and the start function of ADR-0115 (PR #186).
- Adding `orchestration/` to A-13's document-mode list, the README document table, or the integrator follow-ups of ADR-0118 (NFR-7 ①, S2, CLAUDE.md "세 층 모델").
- Anything held in PLAN's 보류 section, and anything blocked by HQ-0021, HQ-0025, HQ-0026, HQ-0031, HQ-0032 or HQ-0034.

## Follow-ups

- Next P2-1 slice: the round-0 procedure in the Round-Manager prompt. This likely needs an ADR first (OD-28 baseline, OD-18 ⑯ (가), OD-8 ⑩ for who writes the first `STATE.json`).
- How the session reaches the run's files, decided by the definition (ADR-0118 decision 4).

## Result
