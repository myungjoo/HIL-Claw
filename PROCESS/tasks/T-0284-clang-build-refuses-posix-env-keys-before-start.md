---
id: T-0284
title: Make `clang_build.build` refuse, on POSIX and before the start, an empty `env` key or one with `=` anywhere, with a `ValueError` that carries `parameter` "env"
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0283]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 25, files: 2}   # tests excluded from the cap (DRIVER §5, D4)
hq: [HQ-0028]
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. ADR-0094 (T-0283, landed `548baf2`) placed the `env` with no `items` method. In its decision 3 it left one entry open: "an `env` that has `items` and that `subprocess` still refuses on some platform or start path". T-0282's Out of Scope names three such values: on native Windows an object with `items` but no `keys` or `values`, the empty key, and a key whose only `=` is its first character. The record names two ways to close the entry, neither decided ("Either is a later task's"):

> a reading of what `subprocess.Popen` raises for those values; or a code change that makes `build` refuse them in the `"env"` step before the start.

This task is that code change, **for POSIX only** and for two of the three values: the empty key, and a key with `=` as its first character.

What `build` does today (`main` at `197b5e5`):

- `_check_env` (`hilclaw/clang_build.py`, about line 485) converts each key and value with `os.fsencode` on POSIX. It refuses a NUL in either, and a `=` in `key[1:]`. The empty key and a key whose only `=` is its first character pass the check and reach `subprocess.Popen` unchanged.
- On POSIX, `subprocess.Popen` has two start paths, and each refuses a different one of these two values. These are the planner's reading of CPython sources; the executor re-checks both with tests (criterion 5):
  - **fork/exec path** (taken when `cwd` is not `None`, among other conditions). In `Lib/subprocess.py`, `_execute_child` (POSIX) runs `if b'=' in k: raise ValueError("illegal environment variable name")`. That refuses `=` anywhere in a key, the first character included, and accepts the empty key.
  - **`os.posix_spawn` path** (`_USE_POSIX_SPAWN`, taken only when `cwd is None` and further conditions hold). It hands `env` to `os.posix_spawn`, whose environment parser refuses an empty key or a `=` after the first character with `ValueError` ("illegal environment variable name"). That refuses the empty key and accepts a key with `=` only as its first character.
  - Either way the refusal comes after the temporary name and the clock were drawn, and it carries no `parameter`. ADR-0093 decision 3 and ADR-0094 decision 3 leave it in U4.
- The existing test `test_an_env_left_to_subprocess_names_no_parameter` (`tests/test_clang_build.py`, `UNCHANGED_ENVS` about line 2108) pins that behaviour. On POSIX its list holds `{"": "x"}`, `{"=A": "x"}`, `{b"=A": b"x"}` and `{b"": b"x"}`.

Why one rule on POSIX, `ValueError`, and `parameter` `"env"`:

- On POSIX, `ValueError` is the only class either start path raises for these two values. A single rule (refuse the empty key, and refuse `=` anywhere in a key) keeps "the class it would raise for the same single defect" from the docstring of `build`. It is stricter than `subprocess` on one path for each value, and the docstring must say so (criterion 3).
- Which path `subprocess` takes depends on private conditions, `cwd` among them. Today the same `env` can run with one `cwd` and be refused with another. After this change `build` answers both the same way. That follows C-7, which asks for alike behaviour.
- ADR-0089 decision 2 places a named `"env"` error in S4 `settings_refused`. So the landed rules already answer the new refusal, and no new rule is needed.

Native Windows is left as it is, because its behaviour does not fit the same rule. These are the planner's observations on this machine, Windows 11 with Python 3.14.4, and nothing here relies on them:

- A key with `=` only as its first character is accepted there. Such keys are the real per-drive variables. The existing test `ACCEPTED_ENVS` (about line 2041) pins it.
- The empty key fails at the start with `OSError` (WinError 87), not with `ValueError`.

This is a code change only:

- It records no row of `correctness.check`. The record that confirms the row and narrows ADR-0094's open entry is a doc follow-up.
- It adds no data-plane value and decides nothing of OD-18.
- It touches no owner-only item (DRIVER §9).
- Its tests need no real `claude`, compiler, container or board (D16). They use the existing stub compiler, `forbid_start` and `directly`. `directly` starts the running Python interpreter, as the existing env tests already do.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0284` trailer in commits and as the last line of the PR body, size cap, D12 test rules.
- `CLAUDE.md`, the standing rules, above all:
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙";
  - "도구 계층 언어 정책" (one line in the commit body on the language choice);
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `197b5e5`:
  - the docstring of `build` (from line 197). Read in particular "Raised before anything is started" (line 221), the paragraph that begins "After the compiler is found, and still before anything is started, ``env`` and ``cwd`` are checked" (line 239) through "a message that may name the key but never the value", and the `parameter` paragraph;
  - the check steps (about lines 304-338), `_parameter` (line 477), `_check_env` and `_env_text` (lines 485-509).
- `tests/test_clang_build.py`. Follow its style:
  - `posix_only`, `windows_only` and `PASSED_ON` (lines 1929-1931), `directly` (line 1948), `forbid_start` (line 1964), `refused` (line 1971);
  - `REFUSED_ENVS` through `test_an_env_error_message_names_the_key_and_not_the_value` (lines 1981-2038);
  - `ACCEPTED_ENVS` and `test_an_accepted_env_reaches_the_compiler` (lines 2041-2065);
  - `UNCHANGED_ENVS` and `test_an_env_left_to_subprocess_names_no_parameter` (lines 2108-2143);
  - `test_the_env_is_named_before_the_cwd` and `test_env_and_cwd_errors_keep_their_parameter_through_pickling` (from line 2413).
- `ARCHITECTURE/decisions/ADR-0094-od18-correctness-check-env-without-items.md`: decision 3. Read only; do not edit.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: Context P2 and decision 2. Read only; do not edit.
- `PROCESS/tasks/T-0282-clang-build-refuses-an-env-without-items.md`: `## Out of Scope` only. It names the values left to `subprocess`.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): run `gh pr list`. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict risk).
2. **The change** is in `_check_env` of `hilclaw/clang_build.py`, inside the existing `with _parameter("env"):` step. On POSIX only, and for each key after its `os.fsencode` conversion and the NUL check:
   - an empty key raises `ValueError`;
   - a key that contains `=` at any position, the first included, raises `ValueError`.

   Both then carry `parameter` `"env"` through the existing context manager, and no `path_role`. The message may name the key and never the value.

   On native Windows nothing changes. A `=` after the first character is still refused. A key with `=` only as its first character and the empty key still pass the check.

   Nothing else changes:
   - the conversion and the NUL checks;
   - the `TypeError` for an `env` with no `items` method;
   - the order of the checks. An earlier defect of `timeout_s`, `flags`, `trailing_flags`, `sources`, `output` or `compiler` is still raised first. The `env` error still comes before a `cwd` error. No temporary name or clock is drawn, and nothing is started;
   - `env` is still handed on unchanged;
   - `compiler_version`, `hilclaw/local_run.py`, `hilclaw/harness/*`.
3. **Docstring of `build`**, briefly and in the existing style:
   - State the POSIX refusal of the empty key and of `=` anywhere in a key, next to the existing sentence on "a ``=`` after the first character of a key".
   - Keep the sentence true that says the checks use "the class it would raise for the same single defect". For example, say that on POSIX each of these two keys is refused by one of `subprocess`'s start paths with `ValueError`, and that `build` refuses both on every path.
   - Keep the `parameter` paragraph true.
   - Add no comments in code.
4. **Permitted edits of existing tests.** The only permitted edit is to `UNCHANGED_ENVS` in `tests/test_clang_build.py` (about lines 2108-2113):
   - remove the three `posix_only` entries;
   - mark `{"": "x"}` `windows_only`.

   Nothing else in `test_an_env_left_to_subprocess_names_no_parameter` changes. Any other existing test that fails is a stop:
   - do not edit it;
   - return BLOCKED, with the test's name and the failing assertion in `## Result

- **DONE.** Resumed after the owner's HQ-0028 answer, option (a): `build` refuses the empty `env` key on POSIX even where `subprocess` accepts it, and the docstring says so.
- PR: #179, reopened and merged. Merge commit: `69d79f15295a4a97fd11b68e9b40095a79130269`. Branch `claude/T-0284-clang-build-refuses-posix-env-keys` deleted. `origin/main` was merged into the branch rather than rebased, to avoid a force push.
- Change: `_check_env` refuses on POSIX an empty key and a key with `=` at any position (`ValueError`, `parameter` `"env"`, no `path_role`) before any temporary name, clock read or start; native Windows unchanged. The docstring of `build` names both keys as exceptions to "the class it would raise for the same single defect". The only existing test edited is `UNCHANGED_ENVS` (criterion 4); no D21 edit.
- Criterion 5 premise, as applied after HQ-0028 (executor's reading, accepted by the reviewer): `test_an_equals_key_is_refused_by_a_popen_start_path` keeps the original assertion for the three leading-`=` cases; `test_popen_raises_no_other_class_for_an_empty_key` requires only `None` or `ValueError` for the two empty-key cases.
- Review: 2 rounds. Round 1 (Request changes, `e1a40c9`): HIGH 3.11 premise failure (resolved by HQ-0028 and the test split); MEDIUM docstring untrue on some supported Python (reworded); LOW Windows `raise` uncovered on CI (`test_the_windows_branch_refuses_equals_after_the_first_character`). Round 2 (Approve, no findings, `72464a88`); the Python and coverage gates finished green after the Approve, on the same head.
- Language: Python, the existing module.
- Gates: CI run 41099726854 on `72464a88` all pass (Python 3.11, 3.14, coverage, test presence, sh, C). Local (Windows): `ruff check`, `ruff format --check` pass; `pytest` 36473 passed, 2375 skipped, 1 failed: `tests/harness/test_bf16_timing.py::test_standard_error_is_captured_and_not_parsed` (`
` in stderr), not touched here and not re-run on a clean `main`.
- Classes CI observed: run 39079246945 (`e1a40c9`), Python 3.11, `cwd` None then `tmp_path`: `{"": "x"}` -> [None, None], `{b"": b"x"}` -> [None, None]. Run 41099726854 passed all five cases on 3.11 and 3.14, but passing tests print nothing, so criterion 9's by-case, by-path table cannot be filled further.
- Follow-ups: the doc task in `## Follow-ups` is now due (ADR-0094 decision 3's open entry is out of date until it lands); new: the Windows-only failure above.
