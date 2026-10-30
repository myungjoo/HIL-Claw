---
id: T-0286
title: Make `local_run.run` refuse, before the start, an `env` that is not `None` and has no `items` method, with a `TypeError` that carries `parameter` "env"
phase: P1
status: IN_PROGRESS
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
- `PROCESS/tasks/T-0282-clang-build-refuses-an-env-without-items.md`: `## Acceptance Criteria` and `## Result` only. The change here has the same shape, in the other module.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): run `gh pr list`. If an open PR touches `hilclaw/local_run.py` or `tests/test_local_run.py`, stop and return BLOCKED (open-PR conflict risk).
2. **The change** is in `_check_env` of `hilclaw/local_run.py`, inside the existing `with _parameter("env"):` step:
   - When `env` is not `None` and `getattr(env, "items", None)` is `None`, raise `TypeError`. It then carries `parameter` `"env"` through the existing context manager, and no `path_role`.
   - The message names the type of `env` (with `type(env).__name__`) and never its value. Use the same text as `clang_build._check_env`: `env must be None or have an items method, not <type>`.
   - `None` still inherits and is not refused.
   - Nothing else changes:
     - the checks of an `env` that has `items`;
     - what is left to `subprocess` (the empty key, a key whose only `=` is its first character);
     - the order of the checks. An earlier defect of `timeout_s` or `command`, and `ProgramNotFoundError`, still come first. The `env` error still comes before a `cwd` error. Nothing is started for it;
     - `hilclaw/clang_build.py`, `hilclaw/harness/*` and every other module.
3. **Docstring of `run`**, briefly and in the existing style:
   - In the `env` paragraph, remove "an ``env`` that is not a mapping" from what is left to `subprocess`. Add a sentence saying that an `env` that is not `None` and has no `items` method is refused with `TypeError`, as `subprocess` has no single class for it (the class differs by platform and start path).
   - Keep true the sentence "The check refuses nothing that one of the ways :mod:`subprocess` starts a process accepts". If the executor finds a start path that accepts some `env` with no `items` method, stop and report it as BLOCKED (requirement unclear); do not choose.
   - Keep true the "What :mod:`subprocess` raises is passed on" paragraph ("what it raises for an ``env`` the check above leaves to it") and the `parameter` paragraph, which lists `"env"` already.
   - Add no comments in code.
4. **Permitted edits of existing tests.** Only these two existing tests in `tests/test_local_run.py` may be edited, replaced or removed:
   - `test_an_env_that_is_not_a_mapping_keeps_its_class` (about lines 1078-1089, with its `parametrize` lines);
   - `test_a_list_env_still_raises_attribute_error` (about lines 1092-1095).

   Replace them with the new behaviour of criterion 5 (error), in place or under new names. Any other existing test that fails is a stop:
   - do not edit it;
   - return BLOCKED, with the test's name and the failing assertion in `## Result`.

   `tests/test_clang_build.py` is not touched.
5. **Tests** in `tests/test_local_run.py`, under CLAUDE.md test rules ①-④. Prove with `child.started` that no process was started.
   - **error**: for each of `[("A", "x")]`, `5`, `"A=x"`, `b"A=x"`, `object()` and an object whose class sets `items = None`, `run` raises `TypeError` with `parameter == "env"`, no `path_role`, and nothing is started. Cover both wait paths (`platform_wait` `True` and `False`), as the neighbouring tests do.
   - **message (negative)**: for an `env` such as `"SECRET=1"` (a `str`), the message names the type and does not contain `SECRET`.
   - **branch / order**:
     - with an `env` of no `items` and a refused `cwd` (for example `cwd=3`), the error carries `"env"`;
     - with an `env` of no `items` and an earlier defect (`timeout_s=0`, and an empty `command`), the earlier error comes first, with its own `parameter`;
     - with an `env` of no `items` and a missing program, `ProgramNotFoundError` comes first, with no `parameter`.
   - **branch**: an object whose class sets `items = 3` (not callable) is still refused by calling it: `TypeError`, `parameter` `"env"`, as today. Assert what the code does.
   - **pickling**: add a new test with the pattern of `test_the_parameter_survives_pickling` for one no-`items` `env`, so that the existing test stays unedited.
   - **happy**: the existing tests of accepted envs, `None` inheriting and `UNCHANGED_ENVS` pass unchanged. Do not duplicate them.
   - Do not add tests of test code, CI or hook scripts (rule ⑤).
6. **Gates**:
   - `pytest` and `ruff` (`ruff check`, `ruff format --check`) pass locally.
   - The `hilclaw/` line and function coverage stays at or above 80%.
   - CI is green before merge, on every Python version and platform it runs.
7. **Code mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0286-<slug>`.
   - Open a Draft PR with `T-0286` in its title and `Task: T-0286` as the last line of its body.
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

- Any edit of `ARCHITECTURE/` (ADRs, Requirements, OpenDecisionProposals, StandardScenarios). The record of `local_run.run`'s named errors waits for HQ-0027.
- `hilclaw/clang_build.py` and `tests/test_clang_build.py` (open PR #179, HQ-0028).
- An `env` that has `items` but that `subprocess` still refuses on some platform or start path, each left as it is:
  - on native Windows, an object with `items` but no `keys` or `values`;
  - the empty key;
  - a key whose only `=` is its first character.
- The other `local_run.run` follow-ups marked "after HQ-0027": the pre-start refusal of a `timeout_s` too long for the platform's wait (T-0271) and the message fix of `_check_timeout` (T-0272).
- `hilclaw/harness/*`, including `timing_build.py` (waits on HQ-0021).
- The unlanded branches `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*`.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9).

## Follow-ups

- (doc, after HQ-0027) The OD-18 sub-question 18 part (ma) record on the named pre-start errors of `local_run.run` also covers this `TypeError` with `parameter` `"env"`, together with the T-0265 to T-0271 follow-ups.

## Result

- Outcome: BLOCKED (requirement unclear). No branch, commit or PR was created; `main` is unchanged by this task. HQ-0029.
- Entry checks: `git log origin/main --grep='^Task: T-0286'` and `gh pr list --search T-0286 --state all` found nothing. The only open PR is #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`), no overlap.
- Why it stopped: criterion 3 says to stop if a `subprocess` start path accepts some `env` with no `items` method. Such a path exists:
  - Native Windows (seen on the driver machine, Python 3.14.4): `subprocess.run([sys.executable, "-c", ...], env=KV(...))` started the child and passed the variable on (exit 0), where `KV` defines only `keys`, `values`, `__getitem__` and `__len__`. `local_run.run` takes this path on Windows (`_run_without_usage`, no `os.wait4`); the Windows start path reads the environment through `keys` and `values`.
  - POSIX posix_spawn path (from reading the source, not run): `run` meets the conditions under which `subprocess` uses `os.posix_spawn` (absolute program, `cwd` None, DEVNULL stdin with pipes, `close_fds` where `_HAVE_POSIX_SPAWN_CLOSEFROM` holds); `env` is passed unchanged to `os.posix_spawn`, which reads it through `keys`/`values`. Only the fork/exec path calls `env.items()`.
  - Refusing every non-`None` `env` without `items` would make the docstring sentence "The check refuses nothing that one of the ways :mod:`subprocess` starts a process accepts" false; the task says not to choose in that case.
- Note: `clang_build.build` (T-0282, 4e05627) already refuses such a keys/values-only `env`; its docstring does not claim the sentence above, but it is still stricter than Windows `subprocess`. Outside this task's scope; raised in HQ-0029.
- Review: 0 rounds. CI: not run.
- Language: none chosen (no code written); it would have been Python, the existing module.
- Follow-ups: re-plan T-0286 once HQ-0029 is answered; if the answer is (b) or (c), consider a matching change to `clang_build._check_env` when PR #179 / HQ-0028 allows.
