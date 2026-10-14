---
id: T-0182
title: Move the "outside both checkouts" path check of scratch.py and selfcheck_session.py into one shared module, with no change of behaviour
phase: P1
status: DONE
commitMode: code
coversReq: [NFR-4, OD-8, OD-18, C-7]
dependsOn: [T-0165, T-0171]
touchesFiles: [hilclaw/checkout_boundary.py, hilclaw/scratch.py, hilclaw/selfcheck_session.py, hilclaw/bring_in.py, tests/test_checkout_boundary.py, tests/test_scratch.py]
estimatedSize: {loc: 90, files: 4}   # tests excluded (D4): the new module, three in-place edits; tests/test_checkout_boundary.py is new and one test of tests/test_scratch.py may move
hq: []
---
## Why

T-0171 `## Follow-ups` lists this item: "(planner, code mode, optional) A shared helper for the 'outside both checkouts' check used by `selfcheck_session` and this module." Two modules on `main` (b0f561c) have their own copy of the same check:

- `hilclaw/scratch.py` (ADR-0049 slices (a) and (c), T-0171): `_PACKAGE_DIRECTORY` (line 77), `_refuse_inside_checkout(path, keep_out, *, argument, containing)` (lines 190-204) and `_within(inner, outer)` (lines 207-211, `os.path.commonpath`, `ValueError` read as "not within").
- `hilclaw/selfcheck_session.py` (ADR-0054 / ADR-0057, T-0165): `_PACKAGE_DIRECTORY` (line 183), `_real(path, what)` (lines 208-212) and `_refuse_inside(parent, keep_out)` (lines 215-224, a `str.startswith` test on `normcase(realpath)` with a trailing separator).
- `hilclaw/bring_in.py` (T-0170) has a third copy of `_within` (lines 169-173), used at line 138 for the overlap of a scratch and an attempt's `output/`.

Each copy compares real paths folded by `os.path.normcase`, against the directory that holds the package and the directories of `keep_out`, and refuses a `keep_out` that is one path with the same text. The two tests (commonpath against startswith) are written differently, and a later operation that needs the same check (ADR-0056 decision 4: the build directory of `correctness.check` lies outside both checkouts) would add a fourth copy. One shared function removes the risk that the copies drift apart.

This is cleanup. It decides nothing, changes no record, ticks **no PLAN checkbox** and depends on no open HQ. The substantive P1-1 work waits on HQ-0020 (T-0176, BLOCKED). P1-8 rests on P1-1. P0.5-4 waits on the owner's hook registration. Nothing in this task touches those. Planner's session entry check (2026-10-14, after 5563e9d): no open pull request; open HQs HQ-0013, HQ-0014, HQ-0016..HQ-0019 (`runtime-acceptance`, on DONE tasks) and HQ-0020 (blocks T-0176 only).

**Planner's judgements (the reviewer re-checks each):**
- **Observable behaviour is unchanged.** Exception types, exception texts, return values, the order of the checks and what is made or removed before a refusal stay as they are for every public function of `scratch`, `selfcheck_session` and `bring_in`. The existing tests of those three modules must pass unchanged. The one exception is a test of a private helper that moves with it (see criterion 4).
- **Argument checking stays in each caller.** `scratch` refuses a bad path or a bad `keep_out` entry with `InvalidScratchArgumentError` naming the argument (`_checked_path`). `selfcheck_session` refuses with `TypeError` (`_real`). The shared module takes already-checked `str` paths, so the two error contracts stay where they are.
- **startswith and commonpath must agree.** The executor checks that the shared test gives the same answer as `selfcheck_session._refuse_inside` for every case its tests cover: a parent equal to a root, below a root, beside a root with a common name prefix (`/a/data` against `/a/data2`), a root that is the file system root, different drives on Windows, and a link into a root. If any case differs, the executor keeps `selfcheck_session`'s documented behaviour ("a `parent` that is, or lies inside, the directory that holds this package or a directory of `keep_out`") and reports the difference in `## Result`. The executor does not change it silently.
- **No record is edited.** ADR-0049, ADR-0054 and ADR-0057 leave "names and modules" to the code. A module docstring sentence that names a removed private helper is updated in the same change. No sentence of `ARCHITECTURE/` names these helpers.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72): executor procedure, resume rule, the 2h30m limit.
- `PROCESS/DRIVER.md` §5 (lines 86-114): task format, naming `claude/T-0182-*`, the `Task: T-0182` trailer (also as the last line of the PR body, used as the squash body), size cap D4, D12 test rules.
- `PROCESS/DRIVER.md` §1-5 (line 28): Bypass permissions and the forbidden actions; a denied or failed tool call is BLOCKED.
- `CLAUDE.md` "상시 규칙": comment minimisation, "개발 드라이버와 런타임의 구분" (no `claude` is started; the selfcheck tests use a stub), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙" (D12).
- `.claude/skills/dev-item-address/SKILL.md` (whole; code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/scratch.py`: module docstring (lines 1-58, especially the first convention bullet, lines 16-20), lines 61-110 (imports, `_PACKAGE_DIRECTORY`, error classes), `create` and `remove` (lines 110-174), `_checked_path`, `_refuse_inside_checkout`, `_within` (lines 177-211).
- `hilclaw/selfcheck_session.py`: module docstring lines 50-70 ("*The directory*" convention) and 88-94 ("*What is raised*"), lines 116-130 and 183, `_real` and `_refuse_inside` (lines 208-224), `run` (lines 260-279).
- `hilclaw/bring_in.py`: lines 120-145 (the overlap check that calls `_within`) and 169-173.
- `tests/test_scratch.py`: lines 160-215 and 530-580 (the `keep_out` and checkout tests; `test_paths_on_different_drives_are_not_within_each_other` at line 574 tests the private `_within`).
- `tests/test_selfcheck_session.py`: line 54 (`FIXED_REFUSAL`), lines 780-850 (the parent, link and `keep_out` tests).
- `tests/test_bring_in.py`: lines 375-405 (the overlap tests).
- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md` decision 3 (the scratch outside both checkouts). Read only.

Read Python sources with `PYTHONIOENCODING=utf-8` on this machine. Line numbers are those of `main` at 5563e9d; the text wins.

## Acceptance Criteria

1. **New module** `hilclaw/checkout_boundary.py`. The name is a proposal: the executor may choose another under review and must then update `touchesFiles` in `## Result`. It holds:
   - the directory that holds the package, computed as both modules compute it now;
   - the "one path as `keep_out`" refusal (`TypeError`, the existing text `keep_out must be a sequence of paths, not one path`);
   - a containment test `within(inner, outer)` with today's `_within` semantics (`commonpath`, `ValueError` means not within);
   - one function that, given a checked `str` path, the checked roots of `keep_out` and whether "contains a root" also counts, says whether the path meets a checkout, on `normcase(realpath(...))` of every operand. The package directory is always one of the roots.

   It raises no module-specific error and prints nothing. It has a short module docstring and docstrings on its public functions.
2. **Callers.**
   - `scratch._refuse_inside_checkout` and `selfcheck_session._refuse_inside` call the shared function and keep their own exception class and text: `InvalidScratchArgumentError` with `"{argument}: must not be or lie inside a checkout"` and the `", nor contain one"` suffix, and `ValueError("the directory of the check would lie inside a checkout")`. They also keep their own argument checks and return values (the real path).
   - `bring_in` uses the shared `within` in place of its own copy.
   - The copies of `_PACKAGE_DIRECTORY` and `_within` are removed from the three modules.
3. **No behaviour change.** Every existing test in `tests/test_scratch.py`, `tests/test_selfcheck_session.py` and `tests/test_bring_in.py` passes without being edited, with the one exception of criterion 4. If a test monkeypatches a removed private name, the executor stops and reports it rather than weakening the test.
4. `test_paths_on_different_drives_are_not_within_each_other` (tests/test_scratch.py line 574) moves to `tests/test_checkout_boundary.py` and targets the shared `within`. The same applies to any other test of a moved private helper.
5. **Tests of the new module** (`tests/test_checkout_boundary.py`, D12 ②-④), covering every public function:
   - happy: a path beside every root;
   - branch: a path equal to a root, below a root, containing a root with `containing` true and with it false, and a path that differs only in case where `normcase` folds case;
   - negative: one path given as `keep_out` (`str`, `bytes`, `os.PathLike`), a common name prefix that is not containment (`data` against `data2`), different drives (`commonpath` raising `ValueError`), and a symbolic link that resolves into a root (skipped where links cannot be made, as the existing tests do).
6. `python -m pytest` and `ruff check` / `ruff format --check` pass locally. CI (six jobs) is green. `hilclaw/` line and function coverage stay ≥ 80%, and the new module's line coverage is reported in `## Result`.
7. The commit body states the language (Python, the language of the two modules it serves) in one line. `## Result` records the outcome of the startswith/commonpath agreement check from Why.

## Out of Scope

- Any change of what is refused or accepted, of an exception class or text, or of a docstring rule beyond naming the shared module.
- The build directory of `correctness.check` (ADR-0056; T-0176 is BLOCKED on HQ-0020) and any new caller.
- `bring_in`'s other checks; `_checked_path` and `_remove` of `scratch` and `selfcheck_session` (similar but not the same; not merged here).
- Any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`.
- Starting `claude`, a container runtime or anything needing a board or an API key (D16).

## Follow-ups

- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered. The operation of `cpu_standin` for `correctness.check`, which comes after it, should use this shared module for its build directory.

## Result

- **Outcome:** DONE. PR #126 was squash-merged as 3910a5f, and its branch was deleted. The review took 1 round: Approve, with two nits and a reminder.
- **Files:** as in `touchesFiles`, keeping the proposed module name `hilclaw/checkout_boundary.py`. The new module holds four public names:
  - `PACKAGE_DIRECTORY`;
  - `refuse_one_path(keep_out)`;
  - `within(inner, outer)`;
  - `meets_checkout(path, roots, *, containing)`, which reads `roots` lazily after the package directory.
- **Callers:** `_PACKAGE_DIRECTORY` and `_within` are removed from scratch, selfcheck_session and bring_in. Each module now imports the shared module under the private alias `_checkout_boundary`, so its public names are unchanged; `tests/test_selfcheck_session.py::test_public_names` pins them. The check order is kept:
  - scratch checks every `keep_out` entry before the path;
  - selfcheck_session checks the parent first, then unpacks `(*keep_out,)` eagerly (the same `TypeError` text for a non-iterable), and checks each root only when it is reached.
- **Language:** Python, the language of the two modules it serves.
- **startswith/commonpath agreement:** the old `selfcheck_session._refuse_inside` test and the shared `meets_checkout` were compared on 170 cases on Windows. The cases covered:
  - a path equal to a root, below a root, and beside one with a common name prefix (`data` against `data2`);
  - a root with a trailing separator, and case variants;
  - the drive root and a drive-relative `c:` root;
  - other drives, and a junction into a root;
  - the package directory and its parent.

  No case differed. On POSIX, `realpath` never returns a `//` prefix, so the two tests agree for the cases listed in Why; this was not run here. The documented behaviour is unchanged.
- **Tests:** `tests/test_checkout_boundary.py` is new. `test_paths_on_different_drives_are_not_within_each_other` moved there from `tests/test_scratch.py`. The other tests of scratch, selfcheck_session and bring_in were not edited and pass. Local results: full suite 18663 passed, 354 skipped; ruff check and ruff format --check are clean. CI: all six jobs are green.
- **Coverage (CI coverage gate):** `hilclaw/checkout_boundary.py` 100% line (20/20). `hilclaw/` overall: 99.62% line, 100% function (494/494). Local coverage was not measured because `coverage` is not installed on this machine.
- **Follow-ups:** none required. `hilclaw/selfcheck_server.py:99` keeps its own `_PACKAGE_DIRECTORY`, which serves a different purpose (the server's start argument) and was out of scope. A later cleanup could import `checkout_boundary.PACKAGE_DIRECTORY` there.
