---
id: T-0398
title: Add the reader of the environment variable that names the cpu_standin image, and hand that variable to each turn's MCP server (ADR-0144 code slice 3; bound to no tool)
phase: P1
status: DONE
commitMode: code
coversReq: [NFR-4, C-7, FR-10, OD-14]
dependsOn: [T-0396, T-0397]
touchesFiles:
  - hilclaw/standin_image.py
  - tests/test_standin_image.py
  - hilclaw/turn_loop.py
  - tests/test_turn_loop.py
  - hilclaw/standin_container.py
estimatedSize: {loc: 140, files: 5}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`. P2-5 (the first end-to-end run, `cpu_standin` x GEMM) needs the same, so this is checklist work and the D18 rule for work outside the checklist does not apply. ADR-0144 (landed as `bba593f`, T-0395) decided in decision 5 how the runtime learns which image to use: "the user names it in one environment variable of the process that runs the operation". It says "Its name and its check are the code slice's." Its Consequences list four code slices. Two have landed:

- slice (1), T-0396 (`265d570`): `hilclaw/standin_container.run_in_container`, which takes `image` as an argument and reads no variable;
- slice (2), T-0397 (`bcd04ef`): `hilclaw/standin_copies.place_copies`.

**This task is slice (3)**, "the reading of the environment variable that names the image". It carries the two round-7 reviewer nits of T-0395 that the earlier slices left to it:

- **nit (c)**: the variable check refuses a value that `docker run` would read as an option. Slice (1) already refuses this for its `image` argument.
- **nit (a)**: how the variable reaches the process that runs the operation. During a turn that process is the MCP server process that `hilclaw/turn_loop.py` describes in the server entry of its configuration file. Today that entry's `env` is "exactly" the data-root variable. No record or page states that Claude Code hands its own environment to a stdio server, so the image variable could be missing in the server even when the user set it in the shell that started the loop.

Slice (4), the `cpu_standin` operations, will call the reader and pass its value to `run_in_container`. Slice (4) still waits on HQ-0021, HQ-0026 and OD-14 ① (마), so it is not planned here.

Planner's judgements (from `main` `ca79099`; **the reviewer is asked to re-check each**):

- **No new external dependency** (standard library only). **No tool answer, kind or data-plane member.** The reader is bound to no tool and no backend operation, and it writes nothing.
- **What an operation answers when no image is named or the value is refused is not decided here.** ADR-0144 decision 7 leaves that answer and any kind to OD-18 ⑱/⑲ (HQ-0021, HQ-0026). The reader reports these cases as plain Python facts: a return value for "not named" and a module exception for a refused value. It maps neither to a kind.
- **Not decided here, and left as ADR-0144 leaves them** (① (나)):
  - whether the reference must hold a tag or a digest;
  - whether and where the image's identity is recorded.
  The check therefore does not parse Docker's reference grammar.
- **Forwarding the variable in `turn_loop`** implements ADR-0144 decision 5 ("the process that runs the operation") and is a code choice of the module (ADR-0118 leaves the server entry to the code, see the `turn_loop` docstring "Choices of this module"). It forwards one named, non-credential variable, not a copy of the environment, so it stays clear of ADR-0054's concern about writing a credential to disk (line 93).
- **Runtime acceptance.** ADR-0054's self-check hands its tokens to the server through the same `env` member (line 93), so a passed self-check already shows that `env` values reach the server process. The executor confirms this reading. If it does not hold, the executor names the gap in Follow-ups as a runtime acceptance item for the driver (DRIVER §8, reason `runtime-acceptance`) and does not try to verify it.
- **D16.** Nothing is started: no `docker`, `clang` or `claude`. The turn-loop tests already use their stub `claude`.
- **No open PR overlaps.** PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is touched here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2 h 30 min limit);
  - §5 (task format; naming: branch `claude/T-0398-<slug>`, PR title with `T-0398`, trailer `Task: T-0398`, the PR body's last line `Task: T-0398`; D4 size cap; code-task test rules ① to ⑤);
  - §3 "BLOCKED 사유".
- `CLAUDE.md` (repository), "상시 규칙":
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분" (D16);
  - "도구 계층 언어 정책" (record the language and a one-line reason in the commit body);
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md`:
  - decision 5 (lines 86-105; **lines 98-104 are the rule this task implements**);
  - decision 7 (lines 113-116);
  - Consequences: slices at line 143, runtime acceptance items at line 144, and the open parts at lines 151 and 155.
- `PROCESS/tasks/T-0395-adr-od14-first-case-build-run-container.md`, `## Result` lines 100-104 (the round-7 nits).
- `hilclaw/config.py` (whole file): the existing `HILCLAW_*` variables, their names as module constants, and the `environ` parameter that defaults to `os.environ`.
- `hilclaw/standin_container.py`:
  - module docstring (lines 1-40);
  - the `run_in_container` docstring (lines 97-125);
  - `_check` and `_check_image` (lines 230-266);
  - the `parameter` attribute convention.
- `hilclaw/turn_loop.py`:
  - module docstring (lines 1-130, especially "The data root reaches the server through the environment");
  - `_config_text` (lines 214-223);
  - `_environment` (lines 264-269);
  - `run` (lines 302-346).
- `tests/test_turn_loop.py`: the stub and fixtures, and `test_configuration_content` / `test_configuration_names_the_real_data_root` (lines 270-297).
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md` line 93 (what the self-check's server entry holds).

## Acceptance Criteria

1. **New module `hilclaw/standin_image.py`** (Python). The executor may choose a clearer name and give the reason in the PR body. Contents:
   - a module constant holding the variable name, in the `HILCLAW_` family of `hilclaw/config.py`. `HILCLAW_STANDIN_IMAGE` is suggested; the executor may choose another and give the reason;
   - one public reader, for example `read_image(environ=None)`. `environ` is any mapping and defaults to `os.environ`.
   The reader returns:
   - **`None`** when the variable is unset or empty. This follows `hilclaw/config.py`, where an empty variable counts as unset. Here no default exists, and "not named" is what slice (4) must answer under decision 7.
   - **The value, unchanged** (no stripping and no case change), when it passes the check.
   When the value fails the check, the reader raises a module exception (a `ValueError` subclass). Its text is fixed and does not quote the value, so a mistyped secret is not echoed into a tool answer.
2. **The check** is the one `run_in_container` already applies to `image`: a `str`, not empty, not beginning with `-` (nit (c)), with no whitespace and no NUL. Do not keep two copies of the rule. Either:
   - expose it from `hilclaw/standin_container.py` as a small public function and use it from the reader and from `run_in_container`, keeping the behaviour, exception classes and `parameter` of `run_in_container` unchanged; or
   - have the reader call an existing public path.
   Record which in the PR body. No grammar of image references is parsed, and no tag or digest is required. The module docstring says so and cites ADR-0144 ① (나) as the open item.
3. **The module docstring** states:
   - what the module is (ADR-0144 slice (3), decision 5);
   - that it is bound to no tool and no operation;
   - that it reads only the one variable, writes nothing, starts no program and names no image;
   - what it does not decide: the answer and kind for "not named" or "refused" (decision 7; OD-18 ⑱/⑲; HQ-0021, HQ-0026), and whether and where the image's identity is recorded (① (나));
   - that a tag can move between two builds without the variable changing (decision 5, "One reference is not always one image"), in one sentence.
4. **`turn_loop` forwards the variable (nit (a)).**
   - When `run` builds the configuration text and the calling process's environment holds the variable with a non-empty value, the server entry's `env` also holds that variable with that value, unchanged. When the variable is unset or empty, `env` is exactly as today.
   - `turn_loop` does not check the value. The server-side reader refuses a bad one. A value that cannot be written as JSON does not arise for a `str` taken from `os.environ`.
   - The value is read once, when the text is built, so every turn of one loop names the same image. This matches ADR-0144 decision 5 ("fixed for its life") and ADR-0107 Limit 3.
   - No other variable is forwarded, and the self-check's entry (ADR-0054) is not changed.
   - The module docstring's bullet "The data root reaches the server through the environment" and the sentence saying `env` is "exactly" the data-root variable are updated to match.
   - The docstring names the runtime fact this relies on: that the `env` member reaches the server process. Cite the self-check of ADR-0054 as what establishes it, or, if the executor finds that reading wrong, name it as a runtime acceptance item in Follow-ups.
5. **Tests** for `tests/test_standin_image.py` (new) and `tests/test_turn_loop.py` (adjusted and extended):
   - **happy:** a tag reference and a digest reference (`name@sha256:<64 hex>`) are returned unchanged; `environ=None` reads `os.environ` (use `monkeypatch.setenv`).
   - **branch:** the variable is unset, or set to `""`, and gives `None`.
   - **negative/error:**
     - a leading `-` (for example `--privileged`), an inner space, a tab, a newline and a NUL are each refused with the module exception;
     - the exception text does not contain the value;
     - a non-mapping `environ` raises `TypeError` (or document the behaviour and test it);
     - the exposed check (criterion 2), if one is added, is covered directly;
     - the existing `tests/test_standin_container.py` image tests keep passing unchanged.
   - **turn loop:**
     - the variable is forwarded when set;
     - it is not forwarded when unset or empty;
     - a change of `os.environ` between turns of one loop does not change the configuration of later turns;
     - the existing exact-`env` assertions are adjusted only for the set case.
   - Every public function and class of the new module is covered.
6. `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass locally. CI is green on the PR, and the `hilclaw/` coverage gate (line ≥ 80 %, function ≥ 80 %) holds. `Result` records:
   - the language (Python) and its one-line reason;
   - the variable name chosen;
   - the PR and the number of review rounds;
   - any follow-up (including the runtime acceptance reading of criterion 4).

## Out of Scope

- Slice (4): the `cpu_standin` operations of `correctness.check`, `sim.run` and `board.run`; calling the reader from any operation, `backends.py`, `tools.py` or `mcp_front.py`; any answer or kind for a missing or refused image.
- Checking that the image exists, pulling it, or querying the container runtime; recording the image's identity; requiring a digest.
- `hilclaw.config.json` and `hilclaw/config.py` stay unchanged (ADR-0144 decision 5 (b)), as do any data-plane file and validator, and any ADR or `ARCHITECTURE/` register.
- Forwarding any other variable to the server; changing `hilclaw/runtime_self_check*` or `hilclaw/turn_start.py`.
- Refactoring `standin_container.py` beyond exposing the one shared check (no-behaviour-change refactoring is a D18 hold item).
- Starting `docker`, `clang` or `claude` (D16).

## Follow-ups

- After this lands, the remaining ADR-0144 slice is (4). It waits on OD-18 ⑱/⑲ answers (HQ-0021, HQ-0026) and on ① (마) for the memory figure. Its failure-to-kind mapping should also cover the Windows `PermissionError` -> `COPY_UNWRITABLE` case noted in T-0397.

## Result
- **DONE.** PR #232 squash-merged as c52ba55 (`Task: T-0398` is the last line of the squash message); branch deleted. New: `hilclaw/standin_image.py`, `tests/test_standin_image.py`; edited: `hilclaw/standin_container.py`, `hilclaw/turn_loop.py`, `tests/test_turn_loop.py`.
- **What it does**: `ENV_IMAGE = "HILCLAW_STANDIN_IMAGE"` (the proposed name, in the `HILCLAW_` family of `hilclaw/config.py`); `read_image(environ=None)` returns `None` when the variable is absent or empty and the value unchanged when it passes the check; a refused value raises `ImageRefusedError(ValueError)` with a fixed message that does not quote the value (raised outside the `except`, so no `__context__`); a non-mapping `environ` or non-`str` value raises `TypeError`. The check is the former `_check_image` of `standin_container`, now public `check_image`, shared with `run_in_container` (its behaviour, exception, message and `parameter` unchanged; T-0395 nit (c)). `turn_loop` passes the variable, when set and non-empty in the calling process, into each turn server entry's `env` unchecked, read once per `run` (T-0395 nit (a)); the self-check entry is untouched.
- **Review**: 2 rounds (dev-reviewer), Approve. R1 one nit (inaccurate "quotes the value" in the `check_image` docstring), fixed; R2 nothing left.
- **Tests and CI**: ruff clean; full pytest 25820 passed locally (98 `test_turn_loop` tests skip under this Windows host's default temp path and pass with `--basetemp` outside the repo); CI green (Python 3.11/3.14, sh, C, Test presence, Coverage). No `docker`, `clang` or `claude` was started (D16).
- **Language**: Python, because the reader shares its check with, and is called from, Python package modules.
- **Runtime acceptance (criterion 4)**: the planner's reading holds — `selfcheck_server.server_entry` passes its tokens through the same `env` member over the same `--mcp-config` + `--strict-mcp-config` path, so a passing self-check already shows an `env` value reaches the server process. No new runtime-acceptance item.
- **Follow-ups**: ADR-0144 slice (4) only, waiting on OD-18 ⑱/⑲ (HQ-0021, HQ-0026) and ① (마); it should also cover the Windows `PermissionError` -> `COPY_UNWRITABLE` mapping noted by T-0397.
