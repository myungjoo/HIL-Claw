---
id: T-0284
title: Make `clang_build.build` refuse, on POSIX and before the start, an empty `env` key or one with `=` anywhere, with a `ValueError` that carries `parameter` "env"
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0283]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 25, files: 2}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
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
   - return BLOCKED, with the test's name and the failing assertion in `## Result`.

   `tests/test_local_run.py` is not touched.
5. **Tests** in `tests/test_clang_build.py`, under CLAUDE.md test rules ①-④. Prove with `forbid_start` (or the stub's `started` flag) that no process was started, and that the output directory holds nothing new (the `refused` helper already checks this). The new cases are `posix_only`: they run in CI (Ubuntu) and not on the Windows development machine, so wait for CI before calling them passed.
   - **error**: for each of `{"": "x"}`, `{b"": b"x"}`, `{"=A": "x"}`, `{b"=A": b"x"}` and `{"=": "x"}`, merged into `os.environ` as the existing tests do, `build` raises `ValueError` with `parameter == "env"` and no `path_role`, and nothing is started. Run it both with `cwd` `None` and with a `cwd`.
   - **premise**: for each of those cases, call `directly` with `cwd` `None` and with `tmp_path`. Assert that every outcome is `None` or `ValueError`, and that at least one is `ValueError`. If CI shows otherwise for a case (both paths accept it, or one raises another class), stop. Do not weaken the assertion: return BLOCKED with the observed classes in `## Result`, because the premise of this task does not hold.
   - **message (negative)**: for `{"=A": "secret"}`, the message does not contain `secret`.
   - **branch / order**:
     - an empty key together with a NUL in another key's value raises `ValueError` with `parameter` `"env"` (assert only class and `parameter`, because dict order decides which entry is met first);
     - an empty-key `env` together with a refused `cwd` (for example `cwd=3`) carries `"env"`;
     - an empty-key `env` together with an earlier defect (for example `timeout_s=0`) gives the earlier error first, with its own `parameter`.
   - **negative / Windows**: `windows_only` tests that `{"": "x"}` and `{"=A": "x"}` are not refused by the check. The existing `UNCHANGED_ENVS` and `ACCEPTED_ENVS` already cover this, so add nothing new if they do.
   - **pickling**: a new test, in the pattern of `test_env_and_cwd_errors_keep_their_parameter_through_pickling`, for one of the new errors. Leave the existing test unedited.
   - **happy**: the existing tests of accepted envs and of `None` inheriting pass unchanged. Do not duplicate them.
   - Do not add tests of test code, CI or hook scripts (rule ⑤).
6. **Gates**:
   - `pytest` and `ruff` (`ruff check`, `ruff format --check`) pass locally.
   - The `hilclaw/` line and function coverage stays at or above 80%.
   - CI is green before merge, which is where the `posix_only` tests run.
7. **Code mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0284-<slug>`.
   - Open a Draft PR with `T-0284` in its title and `Task: T-0284` as the last line of its body.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Squash-merge with `gh pr merge --squash --body`, using the PR body.
   - Delete the branch.
8. **Size**: one non-test file changed, well under 300 changed lines excluding tests.
9. **Result** records:
   - the PR and the merge commit;
   - the review rounds and their findings;
   - the language line (Python, the existing module);
   - the classes CI observed in the premise test, by case and start path;
   - the follow-ups.

   The executor starts no `claude` program, real compiler or container (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADRs, Requirements, OpenDecisionProposals, StandardScenarios). The record of the newly named case is a follow-up.
- Native Windows: the empty key (seen failing with `OSError` at the start), an object with `items` but no `keys`, `values` or `__getitem__`, and any other Windows-only refusal of `subprocess`.
- `hilclaw/local_run.py` and `tests/test_local_run.py`. Their `env` check and its record wait on HQ-0027.
- `hilclaw/harness/timing_build.py` (waits on HQ-0021) and `verification_build.py`.
- `time.monotonic`, the draws of the pid and the random part, the command, and anything else `subprocess.Popen` raises.
- The unlanded branches `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*`.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9).

## Follow-ups

- A doc task (ADR-0095, if free) confirms, under ADR-0089 decision 2, that the new POSIX `ValueError`s with `parameter` `"env"` are S4 `settings_refused`. It narrows ADR-0094 decision 3's open entry to what is left there (the native Windows values) and records that entry's change in place. It writes the edits of `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` and `ARCHITECTURE/StandardScenarios.md` by the recording rules in those files ("행 형식", "기록 규칙", the first paragraph of §검사 결과), not by copying earlier task files.

## Result

- (filled by the executor)
