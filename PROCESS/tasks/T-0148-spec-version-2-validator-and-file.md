---
id: T-0148
title: Move `hilclaw/spec.py` and `hilclaw/spec_file.py` to version 2 of the spec together - the validator checks the members of `task.objective` (ADR-0050) and the spec file is read and written as a version-2 file (ADR-0051) - with their tests; one move, not split by module
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-2, FR-5, OD-6, OD-1, OD-8, "#5 B-4"]
dependsOn: [T-0092, T-0094, T-0117, T-0147]
touchesFiles: [hilclaw/spec.py, hilclaw/spec_file.py, tests/test_spec.py, tests/test_spec_file.py, tests/test_gemm_contract.py]
estimatedSize: {loc: 140, files: 2}   # non-test: about 30-45 code lines in spec.py, a few in spec_file.py, the rest docstring lines of both; the three test files are excluded from the cap (D4)
hq: []   # implements landed records (ADR-0050, ADR-0051) in two existing modules; writes no ADR, closes no OD, adds no dependency. The spec schema change (version 2) is approved by the owner's answer to HQ-0009, part 4. Independent of HQ-0007, HQ-0011, HQ-0012, HQ-0013: no file of a BLOCKED task is touched and no public name is added to any module
---
## Why
PLAN P1-5 ("GEMM spec 예시 ... 와 `spec.json` 스키마") is open. Two records landed on 2026-10-13 and no code follows them yet:

- **ADR-0050** (T-0117, `fd337bd`): version 2 of the spec. It is version 1 of ADR-0002 with one change: `task.objective` is an object with exactly the members `objectives` and `constraints`. Its section "What the validator of version 2 is to check" lists the checks.
- **ADR-0051** (T-0147, `38589df`): the spec file of version 2. The rules of ADR-0029 hold by reference with three changes: validity is by ADR-0050, `bound` joins the *integer* places (so `task.objective` is no longer a place where a number of any form may stand), and a reader of version 2 sets apart a file whose `schema_version` is an *integer* other than 2 while a write writes version 2 only.

Facts of `main` at `b94ee09` (planner, 2026-10-13): `hilclaw/spec.py` has `SCHEMA_VERSION = 1`, refuses every other version and inspects nothing of `task.objective`. `hilclaw/spec_file.py` has no version of its own: `parse` compares with `spec.SCHEMA_VERSION` and calls `spec.validate`; its message says "not 1" and its pattern `_FREE` names `task.objective` among three places. No other module of `hilclaw/` imports either module.

**Why one task.** ADR-0051, Consequences: "`hilclaw/spec_file.py` takes its version from `hilclaw/spec.py`, so the two modules cannot move at different commits without a state in between that no record defines or that carries wrong messages." ADR-0051 decision 3: the slice "moves it to version 2 in one commit". The planner measured the cut: two files outside tests, an estimated 140 changed lines, well inside D4. **Do not split by module.** If the change outside tests turns out to pass 300 lines, the only allowed cut is by checks inside the one move (ADR-0051 Consequences) - propose it under `## Result` and stop; do not land half a move.

The task ticks **no PLAN checkbox**: the committed GEMM example of P1-5 still lacks a technique (OD-22).

Planner's judgements (**the reviewer is asked to re-check each**):
- **Code over landed records; no ADR (DRIVER §9).** Member names, type values, the rules of validity, which version is read and written, the spelling rule and what a file of another version is are fixed by ADR-0050 and ADR-0051. This task decides only what those records hand to the code: private names, message texts, the order of the new checks, docstring wording.
- **A-13 reading**: code mode. No new dependency. "데이터 plane 스키마 변경 (spec)" is the change the owner approved: "version 2 of the spec, with the members of `task.objective` defined by the record and checked by the validator" (O4 of ADR-0050, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136238336). Anything beyond what O4 and the two records name is BLOCKED.
- **D16**: no `claude` process, login, board or API key is needed; everything is a pure function or a write below `tmp_path`.
- **Why this item now.** No lock, no TODO / INTERRUPTED file, no open PR. T-0107, T-0123, T-0126 wait on HQ-0007, HQ-0011, HQ-0012. This slice is ready-cut by the Results of T-0117 and T-0147 and ends the state in which two records describe a version no code accepts. The record of OD-13 sub-question 9 is the candidate after it.
- **Known risk, accepted.** The objection windows are open: ADR-0029 until 2026-10-16, ADR-0050 and ADR-0051 until 2026-10-20. Code slices were carried out inside such windows before (T-0133 to T-0146). The most contestable consequence, already put first in the ADR-0051 notice: after this change nothing in the package interprets a version-1 spec file (OD-11 stays open; no spec file of any version is stored in either repository). Say both in one or two lines of the commit body.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; the forbidden actions, never starting `claude` as a child process among them; a denied or failed tool call is BLOCKED, never worked around), §2 last bullets (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0050-od6-task-objective-members.md**: decision 1 (lines 31-46, the table), decision 2 (lines 48-55), decision 3 (line 60: the one admitted value), decisions 4 and 5 (lines 65-81), **"What the validator of version 2 is to check" (lines 101-108)**, Limits (lines 110-119), the Example (lines 121-169)
- **ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md**: Limits (lines 27-37), **decision 1 (lines 39-60), decision 2 (lines 62-69), decision 3 (lines 71-81)**, decision 5 (lines 88-92), Consequences (lines 109-124)
- ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md decisions 2 and 3 (the rules carried over) and ADR-0002-od6-codegen-spec.md decision 2 (the tables; "An object holds exactly the members listed for it") and decision 7 - read only
- **`hilclaw/spec.py`** (268 lines, whole) and **`hilclaw/spec_file.py`** (352 lines, whole; the module docstring is 145 lines and names version 1, ADR-0002 and "three places" in several sentences)
- `tests/test_spec.py` (767 lines) and `tests/test_spec_file.py` (1624 lines): the helpers `minimal`, `full`, `repair`, `changed`, `other_version`, the table of free places near line 32 of `tests/test_spec_file.py`, and every test that names `schema_version`, `objective`, "not 1" or "the integer 1"; `tests/test_gemm_contract.py` lines 100-140 and 240-260 (`synthetic_spec`)
- CLAUDE.md - "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분"
- .claude/skills/dev-item-address/SKILL.md and .claude/skills/dev-code-review/SKILL.md
- `.github/workflows/ci.yml` and `pyproject.toml` - read only (the gates: pytest, ruff, test presence, coverage lines and functions at 80%)
- PROCESS/tasks/T-0147-adr-od6-spec-file-version-2.md `## Result`, "Follow-ups left" (first bullet) - read only
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6138568593 (the ADR-0051 notice, the last comment at planning time). If the repository owner has objected to ADR-0029, ADR-0050 or ADR-0051, changed the answer to HQ-0009, or said anything about reading a version-1 spec, do not start: return BLOCKED ("requirement unclear") quoting the comment. An answer to HQ-0007, HQ-0011, HQ-0012 or HQ-0013 does not stop this task; name it in `## Result`

## Acceptance Criteria
Where a criterion below and a landed record disagree, **the record wins**: follow it and say so in `## Result`. Private names, message texts and docstring wording are this task's choices; what is given below for them is recommended.

### Files
- Changed: `hilclaw/spec.py`, `hilclaw/spec_file.py`, `tests/test_spec.py`, `tests/test_spec_file.py`, `tests/test_gemm_contract.py`. **Nothing else.** `tests/test_instance.py` is named by ADR-0051 among the tests that build a spec, but at `b94ee09` it builds none (it only places bytes under spec paths and checks that `hilclaw.instance` does not import the spec modules); it is expected to pass unchanged. If any other file must change for the suite to pass, change the least and say why in `## Result`; if a file under `hilclaw/` other than the two must change, return BLOCKED with the reason.
- No public name is added, removed or renamed in either module, and no signature changes. No ADR, register row, `README.md`, `pyproject.toml` or workflow file is edited.
- Language: Python (both modules exist in Python) - one line in the commit body and `## Result`.

### `hilclaw/spec.py`
- `SCHEMA_VERSION` is the `int` 2. `validate` accepts a document whose `schema_version` is exactly the `int` 2 and refuses every other value, the integer 1 among them, with `InvalidSpecError` as today (it does not tell version 1 from any other wrong value; setting a version apart is `hilclaw.spec_file`'s).
- Every check of version 1 holds unchanged for every section but `task.objective` (ADR-0050 decision 1).
- `task.objective` (ADR-0050, checks 1 to 3):
  1. it is an object with exactly the members `objectives` and `constraints`; a missing or an unknown member is refused;
  2. `objectives` is an array of exactly one entry; the entry is an object with exactly the member `type`; `type` is the `str` `latency_minimisation`. An empty array, two or more entries, an entry with `weight`, `priority` or any other member, and any other value of `type` (`throughput_maximisation`, `memory_ceiling`, a subclass of `str`, a non-string) are refused;
  3. `constraints` is an array and is empty. A value that is no array and an array with any entry - the well-formed `{"type": "memory_ceiling", "bound": 123456789}` included - are refused.
- **Check 4 of the record is not implemented**: it begins "Once `memory_ceiling` is admitted", and no constraint type is admitted (ADR-0050 decision 5). Do not write code for the shape of a constraint entry, for `bound` or for the uniqueness of `type`: it would admit nothing, and the admission belongs to the record of OD-13 sub-question 9. Say this in the module docstring in one sentence.
- Each refusal names the path below `task.objective` (for example `task.objective.objectives[0].type`) and the rule, in the form of the existing messages; the existing helpers (`_object`, `_array`, `_one_of`, `_fail`, `_broken`) are used where they fit. An array holds only a `list`, an object only a `Mapping`, as elsewhere in the module.
- The docstrings of the module and of `validate` are true of version 2: validity by ADR-0002 with the change of ADR-0050; `task.objective` leaves the "Not inspected" list; the list of what is not checked gains, in a clause each, that the type is not checked against a backend or an execution point (ADR-0050 L1) and that nothing ties the value to the instance (L2); the text form of a file is ADR-0029's as ADR-0051 carries it over. Keep the edits to the sentences that became false; do not rewrite the docstring.

### `hilclaw/spec_file.py`
- `parse` (ADR-0051 decisions 1 to 3): a content whose `schema_version` is an `int` from 0 to `keys.MAX_INTEGER` other than 2, spelt without `-0`, raises `UnsupportedVersionError` before any other member is looked at - **a version-1 content among them**; the message names the version found and the version read (recommended: built from `spec.SCHEMA_VERSION`, so the literal is not repeated). A version-2 content is validated by `spec.validate` and returned as before. The order of the checks is unchanged.
- `task.objective` is removed from `_FREE`; the two places left are the top-level `ext` and the `profile` of an entry of `feedback.attempts` (ADR-0051 decision 2). Stated plainly, so that no reviewer looks for a test that cannot exist: in version 2 as ADR-0050 leaves it a number anywhere inside `task.objective` already makes the document invalid in `spec.validate`, which runs before the spelling check, so the removal changes no outcome of `parse` today. It is made so that the module does not name a free place the record no longer has, and so that a `bound` spelt `-0` is refused by its text once a constraint type is admitted.
- `final_name` and `write` change in nothing but what follows from the above: `write` puts a version-2 content under its name and refuses a version-1 content with `UnsupportedVersionError` before the file system is touched; `final_name` raises `InvalidSpecError` for a version-1 document.
- Docstrings (module, `UnsupportedVersionError`, `parse`, `final_name`, `write`): every sentence that says "version 1", "other than 1", "valid by ADR-0002" or "three places" is made true - the record of the file is ADR-0029 as carried over and changed by ADR-0051; validity of the document is by ADR-0050; two places are left; `bound` is an *integer* place that no valid document holds yet. One sentence says that a version-1 file is set apart and not read, and that reading it is OD-11. Keep the edits to those sentences.

### Tests (D12: happy, error, branch and negative cases; every public function of both modules stays covered)
`tests/test_spec.py`:
- The helpers build version-2 documents (`schema_version` 2; `task.objective` `{"objectives": [{"type": "latency_minimisation"}], "constraints": []}`); the embedded key records keep their own `schema_version` 1.
- `SCHEMA_VERSION` is the `int` 2; a document of version 1, 0, 3, `True`, `2.0`, `"2"` is refused at `schema_version`.
- **The restated example of ADR-0050** (lines 131-152 of the record), copied into the test word for word, passes `validate`; so does the one-line `task.objective` example (line 126). If the copied example does not pass, do not alter the copy or the record: return BLOCKED ("requirement unclear") with the message of the validator.
- The test that today says `task.objective` is not inspected is replaced by refusals, each with its path: `task.objective` that is `None`, a string, a number, a list, `{}`; a missing `objectives`; a missing `constraints`; a third member; `objectives` that is no array, is empty, has two entries (two equal ones included); an entry that is no object, lacks `type`, carries `weight`, carries `priority`, carries another member; each wrong `type` value named above; `constraints` that is no array (`None`, `{}`, a tuple) or holds an entry (the `memory_ceiling` form of the record, a `bound` of 0, an empty object).
- A read-only mapping as `task.objective` and as the objective entry is accepted; the document is not modified.
- What the existing tests assert about version 1's other sections is kept; an existing assertion is changed only where version 2 makes it false, and each such change is listed in `## Result`.

`tests/test_spec_file.py`:
- The helpers build version-2 contents. A version-2 content parses to its document, yields its final name and is written under it.
- **A version-1 content is set apart**: `parse` and `write` raise `UnsupportedVersionError` (no `ValueError`, no file or directory created) for the full version-1 document of the old helper and for `{"schema_version": 1}`; versions 0, 3 and `keys.MAX_INTEGER` likewise; `schema_version` spelt `2.0`, `2e0`, `-0`, `"2"`, `true` is invalid and not set apart; a missing `schema_version` is invalid.
- The rules for the whole text still come before the version (the existing cases, with a version other than 2 where they used 2).
- The table of free places has two entries. For `task.objective`: a content with `-0`, `1.5`, `1e999` or a nested value anywhere inside it is `InvalidSpecFileError` carrying the validator's message; the existing cases for `ext` and `profile` are kept.
- `-0` at each *integer* place of a version-2 content is still refused by its text; `-0` as `schema_version` is invalid, not another version.
- `final_name` raises `spec.InvalidSpecError` for a version-1 document.
- The order-of-checks tests of `parse` and of `write` hold with the versions exchanged.

`tests/test_gemm_contract.py`: `synthetic_spec` builds a version-2 spec with the `task.objective` of the first case; no other assertion changes.

No test is added for test helpers or for CI files (CLAUDE.md 테스트 규칙 5).

### Checks before the merge (list each with its outcome in `## Result`)
- `python -m pytest` passes; `python -m ruff check .` and `python -m ruff format --check .` exit 0; coverage of `hilclaw/` stays at or above 80% for lines and for functions (report both numbers, and those of the two modules).
- `git grep -n "version 1\|not 1\|other than 1\|three places" -- hilclaw/spec.py hilclaw/spec_file.py`: every remaining hit is read and is true (for example the `schema_version` of an embedded key record).
- `git diff --stat origin/main`: only the five files; the two files under `hilclaw/` change by at most 300 lines together.
- CI green on the PR (all checks) before the squash-merge.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check (`git log origin/main --grep='^Task: T-0148'`, `gh pr list --repo myungjoo/HIL-Claw --search T-0148 --state all`), then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR that edits one of the five files is BLOCKED ("open PR conflict").
- Code mode (CLAUDE.md A-13): branch `claude/T-0148-spec-version-2-validator-and-file`; Draft PR with `T-0148` in its title and `Task: T-0148` as the last line of its body; the reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, BLOCKED - no self-review). Ask the reviewer explicitly to (a) check each refusal and each acceptance against ADR-0050 lines 101-108 and decisions 2, 4 and 5; (b) check `parse` and `write` against ADR-0051 decisions 1 to 3, above all that nothing reads, repairs or converts a version-1 content; (c) look for code that admits or half-admits `memory_ceiling`, `weight` or `priority`; (d) read every changed docstring sentence against the records; (e) re-check the planner's judgements in `## Why`.
- Then squash-merge with `gh pr merge --squash --body` carrying the PR body (last line `Task: T-0148`) and delete the branch, remote and local in separate commands. Commit and PR text in English.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Reviewers are spawned with the session's own agent tool.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around.
- `## Result`: fill it in on `main` after the merge and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the PR and the merge commit, review rounds and findings, the language line, each choice of this task with one line of reason, each changed existing assertion, the checks, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

### Do not invent
- No reader, converter or migration of a version-1 spec, no flag or parameter that selects a version, no second version constant (OD-11; ADR-0051 decision 3).
- No admitted constraint type, no code for `bound`, no type or meaning for `weight` or `priority`, no second objective type (ADR-0050 decisions 2, 3 and 5; the rest of #5 A-4 is owner-only).
- No check that ties `task.objective` to an instance record, a backend or an execution point (ADR-0050 L1, L2; PLAN P1-8).
- No JSON Schema file, no committed example file, no builder of a spec.
- **If a point turns out to need the repository owner or a record that does not exist, decide nothing, merge nothing, and return BLOCKED ("requirement unclear") with the exact question and the sentence it turns on.**

## Out of Scope
- The committed GEMM spec example of PLAN P1-5 (lacks a technique, OD-22).
- The memory measurement and the admission of `memory_ceiling` (OD-13 sub-question 9); the member of `instance.json` that states the objectives (PLAN P1-8).
- OD-11: reading or migrating a spec of another version.
- The "now less exact" sentences of earlier records listed by ADR-0050 and ADR-0051 (integrator); any edit under `ARCHITECTURE/`, of `README.md` or of PLAN.
- Anything HQ-0007, HQ-0011, HQ-0012 or HQ-0013 ask.

## Follow-ups
- (planner, document mode, §9 ADR; no further owner answer by ADR-0050 decision 5) The record of OD-13 sub-question 9: the memory measurement on `cpu_standin`, its execution point, from when `memory_ceiling` is admitted; then its harness slice and check 4 of ADR-0050 in `hilclaw/spec.py`.
- (planner, PLAN P1-8) The record of the `instance.json` member that states objectives and constraints, then its code.
- (planner, code mode) The slices ADR-0049 cut that need no container runtime (scratch creation, bring-in to `output/`, scratch removal).
- (planner, PLAN P1-9) The ADR of the runtime self-check, then its code against a stub `claude` only (D16).
- (planner, PLAN P1-5) The committed GEMM spec example, once a technique of the stand-in catalog exists (OD-22) or a §9 judgement on an empty `guidance.techniques` is recorded.
- (owner / OD-11) What reads or migrates a version-1 spec file after this move.
- (driver / owner) HQ-0007 (T-0107), HQ-0011 (T-0123), HQ-0012 (T-0126), HQ-0013.

## Result
