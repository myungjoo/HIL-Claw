---
id: T-0286
title: Make `local_run.run` refuse, before the start, an `env` that is not `None` and has no `items` method, with a `TypeError` that carries `parameter` "env"
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0282]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 25, files: 2}   # tests excluded from the cap (DRIVER §5, D4)
hq: [HQ-0029]
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. T-0282 (PR #178, `4e05627`) made `clang_build.build` refuse an `env` that is not `None` and has no `items` method. The refusal is a `TypeError` raised inside its `"env"` step, so it carries `parameter` `"env"`. ADR-0094 (T-0283) confirmed that such an error is S4 `settings_refused` under ADR-0089. The Follow-ups of T-0282 and T-0283 both name the same change for `local_run.run`. This task is that change.

What `local_run.run` does today (`main` at `d707365`):

- `_check_env` (about line 314) returns at once when `getattr(env, "items", None)` is `None`. Such an `env` reaches `subprocess` unchecked, after the program lookup.
- `subprocess` refuses it with an error that carries no `parameter`. The class depends on the platform and the start path:
  - on POSIX, the fork/exec path calls `env.items()`, which raises `AttributeError`;
  - on native Windows, `[("A", "x")]` and `"A=x"` raise `AttributeError`, and `5` raises `TypeError` (T-0282's observation for Python 3.14.4; the executor re-checks).
- Two existing tests pin that behaviour, and both may be edited (criterion 4):
  - `test_an_env_that_is_not_a_mapping_keeps_its_class` (about line 1078);
  - `test_a_list_env_still_raises_attribute_error` (about line 1092).

Why `TypeError` and `parameter` `"env"`, as in T-0282:

- `subprocess` has no single class for this defect, so "the class `subprocess` would raise" cannot be kept for it.
- `run` already raises `TypeError` for a `timeout_s` or an argument of the wrong type.
- The existing `with _parameter("env"):` step names it with no new mechanism.

Why this is free of HQ-0027:

- HQ-0027 asks whether to land ADR-0088, the record that places the named pre-start errors of `local_run.run` in rows of `correctness.check`. This task records no row.
- Code changes to `local_run.run` already landed while HQ-0027 was open: T-0265 (`env` and NUL arguments), T-0266 (`cwd`) and T-0269 (unencodable arguments).
- The draft of ADR-0088 on the unlanded branch says that "neither check of `run` looks at `env`". T-0265 already made that sentence stale, so this change does not contradict a pending record any more than the landed code does.

Scope:

- This is a code change only. It adds no data-plane value and decides nothing of OD-18. The record of the newly named case waits for HQ-0027, with the other `local_run.run` follow-ups.
- No owner-only item is touched (DRIVER §9).
- The tests start only the existing Python child of `tests/test_local_run.py` (the `child` fixture). They need no real `claude`, compiler, container or board (D16).
- The touched files do not overlap open PR #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0286` trailer in commits and as the last line of the PR body, size cap, D12 test rules.
- `CLAUDE.md`, the standing rules, above all:
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙";
  - "도구 계층 언어 정책" (one line in the commit body on the language choice);
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/local_run.py` at `d707365`:
  - the docstring of `run` (lines 79-161). Read in particular:
    - the paragraph "An ``env`` that is not ``None`` and has ``items`` is checked before the start" (lines 102-113), which ends "and an ``env`` that is not a mapping are left to :mod:`subprocess`";
    - the paragraph "What :mod:`subprocess` raises is passed on" (lines 133-142);
    - the `parameter` paragraph (lines 144-156);
  - the check steps (lines 162-169), `_parameter` (line 270), `_check_env` and `_env_text` (lines 314-334).
- `hilclaw/clang_build.py`: lines 239-247 (the docstring sentences T-0282 wrote for the same refusal) and lines 487-493 (`_check_env`, its message). **Read only**: open PR #179 touches this file.
- `tests/test_local_run.py`. Follow its style:
  - `posix_only`, `windows_only` (lines 46-47), the `child` fixture (line 75), `raised` (line 607);
  - `REFUSED_ENVS` through `test_an_env_error_message_names_the_key_and_not_the_value` (lines 766-850), including `PASSED_ON` and `directly`;
  - `UNCHANGED_ENVS` and `test_an_env_left_to_subprocess_names_no_parameter` (lines 1051-1075);
  - `test_an_env_that_is_not_a_mapping_keeps_its_class` and `test_a_list_env_still_raises_attribute_error` (lines 1078-1095);
  - `Items`, `test_a_type_error_of_env_items_names_env`, `test_another_error_of_env_items_is_passed_on` (lines 1098-1120);
  - the order tests `test_the_time_limit_is_named_before_the_env` through `test_a_missing_program_comes_before_the_env` (lines 1123-1138);
  - `test_the_parameter_survives_pickling` (lines 1158-1178);
  - `test_the_env_is_named_before_the_cwd`, `test_the_cwd_is_checked_last` and `test_no_other_error_of_the_checks_has_a_path_role` (lines 1385-1420).
- `PROCESS/tasks/T-0282-clang-build-refuses-an-env-without-items.md`: `## Acceptance Criteria` and `## Result

- Outcome: DONE. PR #337, squash-merged as e4e26d77; branch deleted. This replaces the earlier BLOCKED stop on HQ-0029.
- Owner's answer (HQ-0029 (a), chat 2026-10-25) overrides criterion 3: every non-`None` `env` with no `items` is refused, including a keys/values-only object that native Windows or `posix_spawn` would accept. The docstring says so, and its "refuses nothing" sentence now covers only an `env` with `items`. The `posix_spawn` part comes from reading the source (earlier stop), not from a run. The keys/values refusal is tested.
- Change: `_check_env` in `hilclaw/local_run.py` raises `TypeError` (`parameter` "env", no `path_role`) with the text of `clang_build._check_env`. The two tests criterion 4 permits were replaced; no other existing test or list assertion changed.
- Review: 1 round, Approve; one nit (a 130-column docstring line), fixed without re-review (D20).
- CI: green on the merged head (Python 3.11 and 3.14, coverage, C, sh, test presence). Local: `ruff` clean; full `pytest` on native Windows 1 failed, 36488 passed, 2375 skipped; `hilclaw/` line coverage 97%, function coverage from the CI gate.
- The one local failure is unrelated and also fails on `origin/main`: `tests/harness/test_bf16_timing.py::test_standard_error_is_captured_and_not_parsed` gets `\r\n` from the stand-in's stderr on Windows. No CI job runs on Windows.
- Language: Python, the existing module.
- Runtime acceptance items: none. No `claude`, compiler or container was started by this task.
- Follow-ups: the doc record after HQ-0027 (see `## Follow-ups`); the Windows-only test above is already in the PLAN hold section.
