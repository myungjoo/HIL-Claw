---
id: T-0282
title: Make `clang_build.build` refuse, before the start, an `env` that is not `None` and has no `items` method, with a `TypeError` that carries `parameter` "env"
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0281]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 25, files: 2}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. ADR-0093 (T-0281, landed `9706ed6`) left U4 open. U4 is the pre-start `ValueError` of `clang_build.build` that carries no `parameter`. The record also keeps open what `subprocess.Popen` raises for what `build` hands it, "an `env` with no `items` method included". Its decision 3 names the code change that would let part of this be placed (named there, not decided):

> a code change that makes `build` refuse an `env` with no `items` method, or another such value, in a named check before the start.

This task is that code change, for the `env` with no `items` method only.

What `build` does today (`main` at `7db0c0b`):

- `_check_env` (about line 482) returns at once when `getattr(env, "items", None)` is `None`. Such an `env` reaches `subprocess.Popen` unchecked.
- `subprocess.Popen` refuses it, after the temporary name and the clock were drawn, with an error that carries no `parameter`. The class depends on the platform, the Python version and the start path (planner's observations; the executor re-checks each):
  - On POSIX, the fork/exec path calls `env.items()`, which raises `AttributeError`. The `os.posix_spawn` path is taken when `cwd` is `None`, and its class was not read.
  - On native Windows with Python 3.14.4, seen on this machine: `[1]` and `"A=1"` raise `AttributeError` (`... has no attribute 'keys'`), and `5` raises `TypeError` ("environment must be dictionary or None").
- The existing test `test_an_env_that_is_not_a_mapping_keeps_its_class` (`tests/test_clang_build.py`, about line 2146) pins that behaviour. It expects the class a direct `Popen` raises, and no `parameter`.

Why `TypeError` and `parameter` `"env"`:

- `subprocess` has no single class for this defect, so "the class it would raise for the same single defect" cannot be kept for it.
- The docstring of `build` already gives `TypeError` "for arguments of the wrong type".
- ADR-0089 places a `TypeError` with `parameter` `"env"` in S4 `settings_refused`. So after this change the landed rules already answer the refused `env`, and no new rule is needed.

This is a code change only:

- It records no row of `correctness.check`. The record that confirms the row and narrows the open entry is a doc follow-up.
- It adds no data-plane value and decides nothing of OD-18.
- No owner-only item is touched (DRIVER §9).
- The tests need no real `claude`, compiler, container or board (D16). They use the existing stub compiler and `forbid_start`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0282` trailer in commits and as the last line of the PR body, size cap, D12 test rules.
- `CLAUDE.md`, the standing rules, above all:
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙";
  - "도구 계층 언어 정책" (one line in the commit body on the language choice);
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `7db0c0b`:
  - the docstring of `build` (lines 207-301). Read in particular "Raised before anything is started", the paragraph that begins "After the compiler is found, and still before anything is started, ``env`` and ``cwd`` are checked" (line 239) through "any other ``env`` is left to :mod:`subprocess`", and the `parameter` paragraph through "carries no ``parameter``";
  - the check steps (lines 304-334), `_parameter` (line 474), `_check_env` and `_env_text` (lines 482-502).
- `tests/test_clang_build.py`. Follow its style:
  - `posix_only`, `windows_only` and `PASSED_ON` (lines 1929-1931);
  - `Items` (line 1939), `directly` (line 1948), `forbid_start` (line 1964), `refused` (line 1971);
  - `REFUSED_ENVS` through `test_an_env_error_message_names_the_key_and_not_the_value` (lines 1981-2041);
  - `UNCHANGED_ENVS` and `test_an_env_left_to_subprocess_names_no_parameter` (lines 2108-2143);
  - `test_an_env_that_is_not_a_mapping_keeps_its_class` (lines 2146-2157);
  - `test_a_type_error_of_env_items_names_env` and `test_another_error_of_env_items_is_passed_on` (lines 2160-2177);
  - `test_the_env_is_named_before_the_cwd` and `test_env_and_cwd_errors_keep_their_parameter_through_pickling` (lines 2352-2390).
- `ARCHITECTURE/decisions/ADR-0093-od18-correctness-check-temporary-name-value-error.md`: decision 3 ("What would let it be placed"). Read only; do not edit.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: Context P2 and the decision that places `parameter` `"env"` in S4. Read only; do not edit.
- `PROCESS/tasks/T-0267-clang-build-env-and-cwd-parameter.md`: `## Acceptance Criteria` only. That task added the `env` check, and the change here has the same shape.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): run `gh pr list`. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict risk).
2. **The change** is in `_check_env` of `hilclaw/clang_build.py`, inside the existing `with _parameter("env"):` step:
   - When `env` is not `None` and `getattr(env, "items", None)` is `None`, raise `TypeError`. It then carries `parameter` `"env"` through the existing context manager, and no `path_role`.
   - The message names the type of `env` (as `_env_text` does with `type(...).__name__`) and never its value.
   - `None` still inherits and is not refused.
   - Nothing else changes:
     - the checks of an `env` that has `items`;
     - which keys or values are left to `subprocess` (the empty key, a key whose only `=` is its first character);
     - the order of the checks. An earlier defect of `timeout_s`, `flags`, `trailing_flags`, `sources`, `output` or `compiler` is still raised first. The `env` error still comes before a `cwd` error. No temporary name or clock is drawn for it, and nothing is started;
     - `compiler_version`, `local_run`, `hilclaw/harness/*`.
3. **Docstring of `build`**, briefly and in the existing style:
   - Replace "any other ``env`` is left to :mod:`subprocess`" with a sentence saying that an `env` that is not `None` and has no `items` method is refused with `TypeError`.
   - Make the sentence that says the checks use "the class it would raise for the same single defect" true again. For example, say that for this one defect `subprocess` has no single class (it differs by platform and start path), so `TypeError` is used.
   - Keep true the `parameter` paragraph, which lists `"env"` already, and the sentence that a `TypeError` or `ValueError` "from anywhere else … carries no ``parameter``".
   - Add no comments in code.
4. **Permitted edits of existing tests.** The only existing test that may be edited is `test_an_env_that_is_not_a_mapping_keeps_its_class` in `tests/test_clang_build.py` (about lines 2146-2157, with its `parametrize` line). It pins the old class and the absence of `parameter`. Replace it, in place or by a test with a new name, with the new behaviour of criterion 5 (error). Any other existing test that fails is a stop:
   - do not edit it;
   - return BLOCKED, with the test's name and the failing assertion in `## Result`.

   `tests/test_local_run.py` is not touched. Its test of the same name stays as it is.
5. **Tests** in `tests/test_clang_build.py`, under CLAUDE.md test rules ①-④. Prove with `forbid_start` (or the stub's `started` flag) that no process was started, and that the output directory holds nothing new (the `refused` helper already checks this).
   - **error**: for each of `[("A", "x")]`, `5`, `"A=x"`, `b"A=x"` and `object()`, `build` raises `TypeError` with `parameter == "env"`, no `path_role`, and nothing is started.
   - **message (negative)**: for an `env` such as `"SECRET=1"` (a `str`), the message names the type and does not contain `SECRET`.
   - **branch / order**:
     - with an `env` of no `items` and a refused `cwd` (for example `cwd=3`), the error carries `"env"`;
     - with an `env` of no `items` and an earlier defect (for example `timeout_s=0`), the earlier error comes first, with its own `parameter`.
   - **branch**: an object whose `items` attribute is not callable (for example a class with `items = None`, or with `items = 3`) shows which branch it takes. With `items = None` it is refused by the new check (`getattr` returns `None`). With `items = 3` it is refused by calling it (`TypeError`, `parameter` `"env"`, as today). Assert what the code does.
   - **pickling**: one case of a no-`items` `env` in `test_env_and_cwd_errors_keep_their_parameter_through_pickling` is allowed. Prefer a new test that uses the same pattern, so that the existing test stays unedited.
   - **happy**: the existing tests of accepted envs, `None` inheriting and `UNCHANGED_ENVS` pass unchanged. Do not duplicate them.
   - Do not add tests of test code, CI or hook scripts (rule ⑤).
6. **Gates**:
   - `pytest` and `ruff` (`ruff check`, `ruff format --check`) pass locally.
   - The `hilclaw/` line and function coverage stays at or above 80%.
   - CI is green before merge.
7. **Code mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0282-<slug>`.
   - Open a Draft PR with `T-0282` in its title and `Task: T-0282` as the last line of its body.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Squash-merge with `gh pr merge --squash --body`, using the PR body.
   - Delete the branch.
8. **Size**: one non-test file changed, well under 300 changed lines excluding tests.
9. **Result** records:
   - the PR and the merge commit;
   - the review rounds and their findings;
   - the language line (Python, the existing module);
   - the follow-ups.

   The executor starts no `claude` program, real compiler or container (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADRs, Requirements, OpenDecisionProposals, StandardScenarios). The record of the newly named case is a follow-up.
- An `env` that has `items` but that `subprocess` still refuses on some platform or start path, each left as it is:
  - on native Windows, an object with `items` but no `keys` or `values`;
  - the empty key;
  - a key whose only `=` is its first character.
- `local_run.run` and `tests/test_local_run.py`. Its doc waits on HQ-0027. Making its `env` check match is a separate follow-up.
- `hilclaw/harness/timing_build.py` (waits on HQ-0021) and `verification_build.py`.
- `time.monotonic`, the draws of the pid and the random part, and anything else `subprocess.Popen` raises.
- The unlanded branches `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*`.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9).

## Follow-ups

- A doc task (ADR-0094, if free): confirm that a `TypeError` with `parameter` `"env"` for an `env` with no `items` method is S4 `settings_refused` under ADR-0089. Remove "an `env` with no `items` method" from the open entries of (마). Write the edits of `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` and `ARCHITECTURE/StandardScenarios.md` by the recording rules in those files, not by copying earlier task files.
- A code task for `local_run.run`, the same change, after HQ-0027 is answered or if the planner finds it free of that HQ.

## Result

- **Outcome**: DONE. PR #178 (`claude/T-0282-clang-build-refuses-an-env-without-items`), squash-merged into `main`; the merge commit is the squash of this PR (its message ends with `Task: T-0282`).
- **Change**: `_check_env` of `hilclaw/clang_build.py` raises `TypeError` (message `env must be None or have an items method, not <type>`) for an `env` that is not `None` and has no `items` method, inside the existing `"env"` step, so it carries `parameter` `"env"` and no `path_role`, and no temporary name or clock is drawn. The docstring of `build` states the refusal and that `subprocess` has no single class for this one defect.
- **Tests** (`tests/test_clang_build.py`): the only permitted edit, `test_an_env_that_is_not_a_mapping_keeps_its_class`, is replaced by `test_an_env_without_items_is_a_type_error_naming_env` (`[("A", "x")]`, `5`, `"A=x"`, `b"A=x"`, `object()`, an object with `items = None`), a message negative case (`"SECRET=1"`), a non-callable `items = 3` refused by the call, the order against `cwd=3` and against `timeout_s=0`, and pickling. No other existing test was edited or failed.
- **Gates**: `ruff check`, `ruff format --check` clean; full `pytest` locally on Windows 22662 passed, 485 skipped; `hilclaw/` line coverage 99%; CI green before merge.
- **Review**: 2 rounds. Round 1 Approve with a Minor (one docstring line of about 117 characters after the reflow) and a Nit (repeated "defect"), both fixed in `5974d19`; round 2 Approve with no findings.
- **Language**: Python, the existing module.
- **Follow-ups** (as listed in the task, none new): the doc task (ADR-0094 if free) confirming the S4 `settings_refused` row for this `TypeError` with `parameter` `"env"` and removing "an `env` with no `items` method" from the open entries of (마); the same change for `local_run.run` once HQ-0027 allows.

Landed: PR #178 squash-merged as 4e05627 (driver record).
