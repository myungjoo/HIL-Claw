---
id: T-0225
title: Move the JSON text helpers that `hilclaw/spec_file.py`, `hilclaw/hypotheses_file.py`, `hilclaw/verdicts_file.py` and `hilclaw/cases_file.py` repeat into one shared helper module `hilclaw/json_text.py`, with no change of behaviour of any public function
phase: P1
status: BLOCKED
commitMode: code
coversReq: [FR-13, FR-11, FR-18, OD-8, OD-30, "ADR-0029", "ADR-0059", "ADR-0071", "ADR-0072"]
dependsOn: [T-0224]
touchesFiles: [hilclaw/json_text.py, hilclaw/spec_file.py, hilclaw/hypotheses_file.py, hilclaw/verdicts_file.py, hilclaw/cases_file.py, tests/test_json_text.py]
estimatedSize: {loc: 160, files: 5}   # non-test: one new module of about 40 statement lines plus its docstring; in each of the four callers about 25 lines of private helpers removed and the calls renamed; one new test file besides (outside the cap, D4)
hq: [HQ-0022]
---
## Why

Four file modules of the layer-2 package carry the same private helpers for the JSON text rules, written out four times (lines at `main` `4329b88`):

- `hilclaw/spec_file.py` lines 171 (`_MINUS_ZERO`), 325-350 (`_object`, `_nan`, `_literal`, `_unsigned`) - ADR-0029 decision 2 as ADR-0051 carries it over
- `hilclaw/hypotheses_file.py` lines 91, 236-260 - ADR-0059 decision 2
- `hilclaw/verdicts_file.py` lines 79, 224-248 - ADR-0071 decision 2
- `hilclaw/cases_file.py` lines 100, 262-286 - ADR-0072 decision 2

The repeated pieces are: an `object_pairs_hook` that refuses a member name twice in an object (`ValueError("a JSON object repeats a member name")`); a `parse_constant` that refuses `NaN`, `Infinity`, `-Infinity` (`ValueError(f"{name} is not a JSON value")`); a `parse_int` that maps the literal `-0` to a sentinel object and every other literal to `None`; and a recursive walk of that second parse ("spelling") that finds the first place written `-0` (pre-order: object members in order, then array items in order) and raises `<path>: is written as -0, which is no integer` as the module's own invalid-file error. Every caller also runs the same two `json.loads` calls on the decoded text.

T-0220 `## Follow-ups` first named this ("A shared private helper module for the JSON text rules now duplicated in `spec_file.py`, `hypotheses_file.py` and this module"); T-0224 `## Follow-ups` repeats it with four copies, and the journal of 2026-10-16 (last line) records it as the open follow-up. A rule written four times can drift, and the next record of OD-30 (the lookup of P2-7) is likely to add a fifth file module. This task makes the helper before that. It ticks **no PLAN checkbox**; it is upkeep of code that PLAN P2-6 and P2-7 slices landed. The precedent is T-0123 (`hilclaw/once_write.py`, PR #102).

### What differs between the four callers (and therefore stays in the callers)

- **The error class** raised for a `-0`: `InvalidSpecFileError`, `InvalidHypothesisFileError`, `InvalidVerdictFileError`, `InvalidCaseFileError`. The message text is the same in all four.
- **Where the walk starts and what it skips.** `spec_file` walks the whole spelling from the path `""` and skips the paths matched by `_FREE` (`ext` and `feedback.attempts[<n>].profile`, ADR-0051 decision 2); its join is `f"{path}.{name}" if path else name`. `hypotheses_file` and `verdicts_file` walk only the members named in `_DEFINED`, each from its own name. `cases_file` walks its own `_DEFINED` and, inside each copy, the copy's defined members with the prefix `<copy>.`, and it has an extra `_version` helper of its own.
- **The order of the checks in `parse`**, the version rule, the call of the record's validator, the wrapping of `ValueError` / `RecursionError` into the module's own error with the module's own message prefix, `final_name` and `write`.

### Planner's judgements (2026-10-16, from the files at `main` `4329b88`; the reviewer is asked to re-check each)

- **Why this item now, and not the P2-7 lookup record.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0210 is BLOCKED on HQ-0021; HQ-0013, HQ-0014, HQ-0016 to HQ-0019 (runtime acceptance) and HQ-0021 are unanswered. The 2층 code slice of ADR-0072 is complete (T-0223, T-0224). The remaining P2-7 work is a document-mode §9 record (the lookup with the `basis` kind `case` and the FR-11 identification of read cases); the planner puts this smaller code task first so that the record's own code slice later finds one helper, not four copies, and names the record as the next candidate.
- **The scope stops at the four `*_file.py` modules** because of the file cap (D4: five non-test files). The same `_object` (and in some `_nan`) are also in `hilclaw/artifacts.py`, `hilclaw/events.py`, `hilclaw/instance.py`, `hilclaw/key_records.py` and `hilclaw/run_state.py`; `hilclaw/hypotheses.py` and `hilclaw/selfcheck_wire.py` have a different function of the same name. They are **not touched** here; a later task may move them (Follow-ups).
- **"No change of behaviour" is the whole contract.** No record is written or reworded, no data-plane schema or layout changes, no new dependency (standard library only). Every existing test in the four test files passes **unchanged**; no existing test is edited. If the move cannot be done without changing something a public function's docstring promises or an existing test asserts, stop and return BLOCKED ("task needs re-planning") with the finding.
- **A public module, not `_json_text.py`.** The CI job "Test presence (hilclaw)" requires `tests/test_<name>.py` for every `hilclaw/*.py` but `__init__.py`, and ruff's `SLF001` (pyproject.toml line 22) forbids importing private names across modules. So the module is `hilclaw/json_text.py` with public names, as `hilclaw/once_write.py` is.
- **Language**: Python, because the four callers are Python modules of `hilclaw/` (CLAUDE.md language policy; one line in the commit body and in `## Result`).
- **D16**: nothing here needs `claude`, hardware or an API key.

## Required Reading

Line numbers are those of `main` at `4329b88`; the text wins. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, `T-NNNN` naming, trailers, size cap D4, the language line, the test rules ① to ⑤) - mandatory for every task (§6).
- PROCESS/DRIVER.md §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around) and the §3 "BLOCKED 사유" paragraph.
- CLAUDE.md, the whole file; above all "코멘트 최소화", "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode: Draft PR, reviewer cycle, CI green, squash-merge), "개발 드라이버와 런타임의 구분".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **hilclaw/spec_file.py**: the module docstring (lines 1-160, the paragraphs on `-0`, `ext`, `feedback.attempts`, and the order of checks), `_FREE` (170), `parse` (202-250), the helpers (325-350).
- **hilclaw/hypotheses_file.py**: the module docstring (1-88), `_DEFINED` (90), `parse` (122-171), the helpers (236-260).
- **hilclaw/verdicts_file.py**: the module docstring (1-76), `_DEFINED` (78), `parse` (110-159), the helpers (224-248).
- **hilclaw/cases_file.py**: the module docstring (1-87), `_DEFINED` and `_COPIES` (89-99), `parse` (130-184), `_version` (252-259), the helpers (262-286).
- hilclaw/once_write.py, the module docstring and `write_once` (the precedent: what a shared helper module of this package looks like and says).
- tests/test_spec_file.py, tests/test_hypotheses_file.py, tests/test_verdicts_file.py, tests/test_cases_file.py - search them for `-0`, `repeats`, `NaN`, `too deep`, `too long` and `monkeypatch.setattr`: these fix the observable behaviour (messages, the first path reported, the error class and its chaining).
- PROCESS/tasks/T-0123-shared-once-only-write-helper.md `## Acceptance Criteria` and `## Result` (how the precedent was scoped and reviewed).
- pyproject.toml (the ruff tables, `SLF001`) and .github/workflows/ci.yml (the jobs "Python gate", "Test presence (hilclaw)", "Coverage gate (hilclaw)": the commands to run locally).
- Read only, no record is edited: ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md decision 2; ADR-0059 decision 2; ADR-0071 decision 2; ADR-0072 decision 2 (the text rules the helpers implement).

## Acceptance Criteria

Verify the description of `## Why` against the files at execution time; the file wins and a difference is named in `## Result`.

### New module `hilclaw/json_text.py`

- Public names (no leading underscore), so the four callers use them without `# noqa: SLF001`. Names and signatures are the executor's choice under review; a suggestion:
  - `MINUS_ZERO` - the sentinel the spelling parse gives for the literal `-0`;
  - `object_pairs(pairs)` - the `object_pairs_hook` that raises `ValueError("a JSON object repeats a member name")`;
  - `no_constant(name)` - the `parse_constant` that raises `ValueError(f"{name} is not a JSON value")`;
  - `integer_literal(literal)` - the `parse_int` that returns `MINUS_ZERO` for `"-0"` and `None` otherwise;
  - optionally `load(text)` returning `(document, spelling)` from the two `json.loads` calls, letting `ValueError` and `RecursionError` pass to the caller;
  - `minus_zero(path, value, skip=None)` (or a function taking the caller's error class) that finds the first place written `-0` in the same pre-order as now, with the join `f"{path}.{name}" if path else name` for object members and `f"{path}[{index}]"` for array items, and with an optional predicate on the path for `spec_file`'s `_FREE`.
- **Messages, the first path reported and the error class seen by a caller of `parse` are exactly as now**, in all four modules. If the walk returns a path instead of raising, each caller raises its own error with the unchanged message; if it takes an error class, it raises that class.
- The module holds only what the four callers repeat. It does not decode bytes, check a BOM, check versions, validate, or know any file name or record; it imports nothing from `hilclaw`.
- A module docstring in the manner of `hilclaw/once_write.py`: which text rules the helpers carry (ADR-0029 decision 2 and the records that apply it: ADR-0051, ADR-0059, ADR-0071, ADR-0072 decision 2), which modules use it, and what it does not do (each caller keeps its error classes, the order of its checks, which members it walks). It states no rule those records do not state. Each public function has a docstring naming its arguments, result and exceptions. No multi-line comments (CLAUDE.md).

### The four callers

- Each of `spec_file.py`, `hypotheses_file.py`, `verdicts_file.py`, `cases_file.py` drops its own `_MINUS_ZERO`, `_object`, `_nan`, `_literal` and the walk of `_unsigned` and uses `hilclaw.json_text` instead. A thin private wrapper that only binds the module's own error class (or `_FREE`) is allowed if it keeps the call sites readable. `cases_file._version` stays in `cases_file`.
- Everything else is untouched: public names, signatures, exception classes, docstrings of public functions (except a sentence that names a removed private helper, which is corrected), the order of checks, `final_name`, `write`.
- A module docstring sentence that now becomes untrue (for example one saying the module has small private helpers of its own) is corrected in the fewest words; no other docstring text changes.

### Tests (D12)

- **`tests/test_json_text.py`** (new; required by the test-presence job) covers every public function of `hilclaw/json_text.py`:
  - happy: an object with distinct names is returned as a `dict` in order; `integer_literal("-0")` is `MINUS_ZERO`, other literals (`"0"`, `"7"`, `"-1"`, a long literal) give `None`; a spelling with no `-0` gives no finding (or raises nothing);
  - error: a repeated member name raises `ValueError` with the exact message; `NaN`, `Infinity`, `-Infinity` raise `ValueError` with the exact message; a `-0` is reported with the exact path;
  - branch: `-0` at the top-level path `""`, in a nested object (dotted path), in an array (indexed path), in an array of objects; the first `-0` in pre-order is the one reported when there are several; a skipped path (the `skip` predicate or equivalent) hides a `-0` below it but not beside it; if `load` exists, both results of one text and the propagation of `ValueError` and `RecursionError`;
  - negative: non-`-0` values that look close (`0`, `-0.0` as a float, the string `"-0"`, `False`) are not reported; a `dict` with a key `"-0"` is not reported.
- The existing tests of the four callers pass **unchanged** (no edit to `tests/test_spec_file.py`, `tests/test_hypotheses_file.py`, `tests/test_verdicts_file.py`, `tests/test_cases_file.py`). If one of them fails, the move changed behaviour: fix the move, not the test.
- Local gate before the PR, as the CI jobs run them: `ruff check`, `ruff format --check`, the whole `pytest` suite, the coverage gate (`hilclaw/` line ≥ 80%, function ≥ 80%; `hilclaw/json_text.py` at 100% is expected), and the test-presence check.

### Commit, PR, Result

- Code mode (CLAUDE.md A-13): branch `claude/T-0225-shared-json-text-helper`, Draft PR whose title contains `T-0225` and whose body ends with `Task: T-0225`, reviewer cycle (dev-code-review), CI green, squash-merge with `--body`, branch deleted.
- Commit body: the language line (Python, as the callers); "no change of behaviour of any public function"; the list of the four callers and the five modules with copies left untouched.
- `## Result`: PR and merge commit, review rounds, CI run, local results, the chosen public names, the net line change of the four callers, any difference from `## Why` found at execution time.

## Out of Scope

- `hilclaw/artifacts.py`, `hilclaw/events.py`, `hilclaw/instance.py`, `hilclaw/key_records.py`, `hilclaw/run_state.py` (their `_object` / `_nan` copies), `hilclaw/hypotheses.py`, `hilclaw/selfcheck_wire.py` (different functions of the same name), and every other module.
- Any change of a text rule, an error message, a version rule, a validator, a file name, a layout path, a record or a register; any edit under `ARCHITECTURE/`.
- Sharing `parse`, `final_name`, `write`, the exception classes or the decode / BOM / version steps between the four modules.
- Editing any existing test file.
- The P2-7 lookup and the `basis` kind `case` (a later document-mode §9 task).

## Follow-ups

- (planner, code mode, optional) Move the `_object` / `_nan` copies of `hilclaw/artifacts.py`, `hilclaw/events.py`, `hilclaw/instance.py`, `hilclaw/key_records.py` and `hilclaw/run_state.py` onto `hilclaw/json_text.py`, if they are the same functions, in the same no-change-of-behaviour manner.
- (planner, document mode, §9) The lookup of P2-7 with the `basis` kind `case` and the FR-11 identification of read cases (later OD-30 records); the round promotion `runs/` → `db/` timing named in the OD-29 row; the two R7 nits of T-0222 (from T-0223 / T-0224 `## Follow-ups`).

## Result

BLOCKED (task needs re-planning), 2026-10-16, executor. No PR was opened and nothing was pushed or merged; review rounds 0; CI not run.

- **Finding.** Four existing tests pin the import surface of the callers. `tests/test_spec_file.py::test_the_module_imports_only_what_it_needs` (lines 920-937) asserts that the set of names `spec_file` imports is exactly `{codecs, json, re, pathlib.Path, hilclaw.keys, hilclaw.layout, hilclaw.once_write, hilclaw.spec}`. `test_the_public_names` in `tests/test_hypotheses_file.py` (851-868), `tests/test_verdicts_file.py` (around 905) and `tests/test_cases_file.py` (around 1136) asserts that the module's non-underscore names are exactly a fixed list that includes `json`. Any static import of `hilclaw.json_text` adds `hilclaw.json_text` / `json_text`, and the callers no longer need `json`; keeping an unused `import json` fails ruff F401. An alias such as `from hilclaw import json_text as _json_text` still fails the spec test, and a dynamic import would only get round the tests. The task says that in this case the executor stops (`## Why`, "No change of behaviour is the whole contract"; `## Acceptance Criteria`, "no existing test is edited").
- **State of the work.** Local branch `claude/T-0225-shared-json-text-helper`, commit `42f345b` (not pushed): `hilclaw/json_text.py` (public names `MINUS_ZERO`, `object_pairs`, `no_constant`, `integer_literal`, `load(text)` -> `(document, spelling)`, `minus_zero(path, value, skip=None)` returning the path of the first `-0` or `None`), `tests/test_json_text.py`, and the four callers moved onto it, each keeping a three-line `_unsigned` that raises its own error class (spec_file passes `_FREE.fullmatch` as `skip`). Net change of the callers: -117 / +20 lines. Local result: ruff check and ruff format --check clean; the five test files run 1116 passed, 2 skipped, and 4 failed, which are exactly the four tests above. All the `-0`, repeated-name, NaN, nesting and long-literal tests of the four callers pass unchanged.
- **Differences from `## Why`.** None in the helper code (line numbers and behaviour as described). The file names of ADR-0051, ADR-0071 and ADR-0072 are `ADR-0051-od6-spec-file-version-2.md`, `ADR-0071-od30-hypothesis-verdict-record.md` and `ADR-0072-od30-hypothesis-outcome-case-file.md`.
- **For re-planning.** Either (a) allow these four import and public-name assertions to be updated (swap `json` for `json_text`, and `hilclaw.json_text` for `json` in the spec set): they pin the import list, not any behaviour of a public function. This is an exception to "no existing test is edited", so the planner or the owner decides it. Or (b) drop the task. Language: Python, as the callers.
