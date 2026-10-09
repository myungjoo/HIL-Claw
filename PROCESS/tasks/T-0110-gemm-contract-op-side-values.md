---
id: T-0110
title: Carry ADR-0008 into the package (decisions 4, 5 and 9) - a new module `hilclaw/gemm_contract.py` that returns the op-side values of a spec for the contract (`gemm`, `fp32`, `row_major`, `c`) - the op_signature record of a shape, the `task.contract` object of a shape, and the shapes of the twelve first instances - bound to no tool, writing no spec and no file
phase: P1
status: DONE
commitMode: code
coversReq: [FR-5, FR-13, OD-6, OD-4, "#5 B-4", "#5 A-7"]
dependsOn: [T-0030]
touchesFiles: [hilclaw/gemm_contract.py, tests/test_gemm_contract.py]
estimatedSize: {loc: 150, files: 1}   # non-test: one new module, about 50 statement lines and about 100 docstring lines; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0008 decisions 4, 5 and 9); closes no OD, writes no ADR, standard library and existing package modules only, writes no data-plane file, registers no tool. Independent of HQ-0005, HQ-0006 and HQ-0007
---
## Why
PLAN P1-5 ("GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 - OD-6 종결 필요(§9 ADR 경로)") is open. Its validator is on `main` (`hilclaw/spec.py`), and the records that give the example its values are closed one by one: ADR-0008 (the op side: `row_major`, the prototype, the operand entries, the twelve op_signature names), ADR-0027 (the form of a `run_id`), ADR-0035 with `hilclaw/standin_profile.py` (the hw side, T-0108 and T-0109).

ADR-0008 Consequences (line 155): "**Committed spec example** (PLAN P1-5): the `op_signature` record, its key and the `task.contract` of the example are now real values." Its Boundaries (last item) leave "code, tests, C files, CI changes, committed example files" to later tasks. **No such task was made for the op side**: nothing in `hilclaw/` holds the prototype text, the operand entries or the rule of the op_signature record. They exist as prose in the record, as a declaration in two C files of the harness (`hilclaw/harness/timing_driver.c` line 46, `hilclaw/harness/verification_program.c` line 65) and as literals copied into several test files. Whoever writes the first spec (PLAN P2-2) or states the op_signature of a run in `instance.json` (ADR-0031) would have to copy them from the record by hand, and nothing checks that the twelve directory names of ADR-0008 decision 9 are what the package derives.

**This task is that code slice**, the op-side counterpart of T-0109: a module that returns these values and a test file that pins them to the record. It ticks **no PLAN checkbox** (P1-5 stays open: `task.objective` waits on #5 A-4, and where and in which form an example file is committed is not decided).

Planner's judgements (2026-10-10 UTC, from the files at `main` `6cce75a`; **the reviewer is asked to re-check each**):
- **This differs from the notes of the previous iterations, so check it first.** The journal of 2026-10-09 and the `## Result` of T-0109 expect no selectable task. Those notes weighed the open decisions (the rest of OD-8, OD-13 sub-question 7, OD-16 sub-question 6) and the hw side; the planner finds no note that weighed a code slice of ADR-0008, which closed its decision on 2026-10-07 and named code as a later task.
- **No decision is taken.** Every value the module returns is written in ADR-0008: the binding (decision 1), `row_major` (decision 2), the prototype text "byte for byte" (decision 4), the three operand entries and their order (decision 5), the rule of the op_signature record and the twelve shapes (decision 9, citing #5 B-4). The module adds no field, no value and no rule to ADR-0001, ADR-0002 or ADR-0008.
- **The weakest point, and the reviewer must weigh it**: a dimension of 0. `hilclaw.keys.op_signature_key` accepts 0 (ADR-0001: an integer from 0), while ADR-0008 decision 6 has the caller guarantee that `m`, `k`, `n` are each at least 1, and no sentence of the record says whether an op_signature of this contract may hold a 0. The planner's reading: the two functions refuse a dimension below 1, since the object they return describes a call the contract never lets a caller make; this is a provisional choice of the task, listed as such. **If the executor or a reviewer reads this as a rule that needs a record, do not block: accept exactly what `op_signature_key` accepts instead, and list the point in `## Result` for a later record.**
- **Second weak point**: the module has no caller in the package, like `standin_profile.local_record`. The planner reads this as acceptable for the same reason the reviewers of T-0109 gave: binding waits on OD-23 (who writes a spec) and OD-26 / OD-18 (the start of an instance), while the values wait on nothing.
- **Independent of every open owner item**: HQ-0005 (which HW tools `cpu_standin` offers), HQ-0006 and HQ-0007 do not touch the op side. `task.objective` (#5 A-4) is not produced, named or given a placeholder.
- **Why this item now**: no lock, no TODO / INTERRUPTED / IN_PROGRESS task file and no open PR at planning time. T-0088, T-0106 and T-0107 are BLOCKED on HQ-0005, HQ-0006 and HQ-0007. Candidates weighed and not taken: `profiler.collect` (ADR-0016 Context: needs points no record holds), `blob.push` / `blob.fetch` (#5 B-2, A-3), the rest of `STATE.json` and the result files (OD-3, OD-20, OD-23, OD-29, the rest of OD-17), a committed example file (its place and form are undecided and it needs `task.objective`), the shared once-only write helper (not before 2026-10-16).
- **A-13 reading** (ask the reviewer explicitly): code mode; no new dependency, no schema file, no data-plane file, no change to `hilclaw/spec.py` or `hilclaw/keys.py`. The BLOCKED reason "data-plane schema change" does not apply: the module returns values of fields that already exist.

Known risk, accepted: ADR-0001 and ADR-0002 are inside their objection windows until 2026-10-13, ADR-0008 until 2026-10-14. An objection that reverts one of them reverts this code with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md - the whole record (about 180 lines)**: Status, **decision 1 (the binding), decision 2 (`row_major`), decision 4 (the prototype text), decision 5 (the operand table and the complete `task.contract` for gate/up at M = 1), decision 6 (the Dimensions row and the bullet "Dimension values other than those of the `op_signature`"), decision 9 (the rule, the canonical form of gate/up at M = 1, the table of twelve names)**, Consequences, **Boundaries (everything the code must not decide)**
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md decision 2 (the rows `task.op_signature`, `task.contract.*`, `task.objective`, `task.build`; the rule that an operand shape value is one of the `op_signature` shape values) and decision 6 - read only
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md decision 2 (the fields of an op_signature) and decision 3 (canonical form and key) - read only
- **`hilclaw/keys.py`** (239 lines: `SCHEMA_VERSION`, `MAX_INTEGER`, `op_signature_key`, `InvalidRecordError`, `Key`) and **`hilclaw/spec.py`** (`validate`, `_task`, `_operand`, `_size`) - read only; what this task returns must be accepted by both
- `hilclaw/standin_profile.py` (module docstring and `local_record`) and `tests/test_standin_profile.py` lines 1-80 - the model for a value module bound to nothing and for its structure tests
- `hilclaw/harness/timing_driver.c` line 46 and `hilclaw/harness/verification_program.c` line 65 - the two declarations of the entry point; read only
- `tests/test_spec.py` lines 1-60 (how a valid spec is built in a test) - a model for the test that puts the returned values into a spec
- PROCESS/tasks/T-0109-cpu-standin-hw-profile-record.md `## Result` ("Provisional choices", "Review rounds", "Follow-ups") - how the sibling slice landed and what its reviews found
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다", "세 층 모델"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` - read only (six checks; `Test presence (hilclaw)` requires `tests/test_gemm_contract.py` for `hilclaw/gemm_contract.py`; `Coverage gate (hilclaw)` holds the package total at 80 % lines and functions)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6089042706 (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`; the ADR-0035 notice was the last comment at planning time). If the repository owner has objected to ADR-0001, ADR-0002 or ADR-0008, or has answered in a way that changes a value used here (the layout name, the prototype, the operand entries, the shapes of #5 B-4), do not start: return BLOCKED ("requirement unclear") quoting the comment. An owner answer to HQ-0005, HQ-0006 or HQ-0007 does not stop this task

## Acceptance Criteria
ADR-0008 fixes the values. Names, call forms and the cases the record does not mention are **this task's choices, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and the record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/gemm_contract.py` (new) and `tests/test_gemm_contract.py` (new). **Nothing else**: `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/instance.py`, `hilclaw/spec_file.py`, `hilclaw/tools.py`, `hilclaw/backends.py`, the harness and its C files, the existing tests, `pyproject.toml`, `.github/`, every ADR and the OD register stay as they are. The literals in existing tests are not replaced by calls of the new module.
- Language: Python is the planner's expectation (`keys` and `spec` are Python and the values are mappings for Python callers); the choice is the executor's within {Python, POSIX sh, C} - one line of reason in the commit body and `## Result`.

### The module (ADR-0008 decisions 1, 2, 4, 5 and 9)
- **Constants** for the binding and the prototype (recommended names `KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`): `"gemm"`, `"fp32"`, `"row_major"`, `"c"`, and the single line of decision 4 byte for byte - `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);` - single spaces, no line break, the semicolon included.
- **The op_signature record of a shape** (recommended `op_signature_record(m, k, n)`): a new plain `dict` with exactly `schema_version` (`hilclaw.keys.SCHEMA_VERSION`), `kind`, `shape` (`{"m": m, "k": k, "n": n}`), `dtype` and `layout` - the rule of decision 9. No `label`, no `ext`. The key is not returned; `hilclaw.keys.op_signature_key(record)` gives it.
- **The `task.contract` object of a shape** (recommended `task_contract(m, k, n)`): a new plain `dict` with exactly `language`, `prototype` and `operands`; `operands` is a new `list` of three new `dict`s in parameter order - `a` `input` `[m, k]`, `b` `input` `[k, n]`, `c` `output` `[m, n]`, each with `dtype` `fp32` and exactly the four members `name`, `role`, `dtype`, `shape` (decision 5; decision 2: no further storage member).
- **The shapes of the twelve first instances** (recommended a tuple constant `FIRST_SHAPES` of `(m, k, n)` triples, or a function returning a new list): the four projections of decision 9 - (k, n) = (2048, 8192), (8192, 2048), (2048, 3072), (2048, 2048) - each at m = 1, 32, 512, in the order of the table (rows by projection, columns by M). **No name is given to a projection** (the words "gate/up", "down", "QKV", "O" are not made identifiers, labels or `label` values); the form of the collection is the task's choice.
- **Arguments**: each of `m`, `k`, `n` must be exactly an `int` (`bool` and other subclasses refused, as in `hilclaw.keys`) and at most `hilclaw.keys.MAX_INTEGER`; the lower bound follows the planner's judgement in `## Why` (at least 1, or 0 as `keys` accepts if a reviewer reads the bound as needing a record). A refused argument raises before anything is returned; recommended: `hilclaw.keys.InvalidRecordError` with a message naming the dimension and the rule, so that a caller meets one exception class for a record `keys` would refuse and for one this module refuses. Whether the arguments are positional or keyword-only is the task's choice.
- Every call returns new objects: changing a returned record, contract, operand or shape list changes neither a later result nor a module constant.
- The module reads and writes no file, starts no process, stores nothing, registers nothing, has no command-line entry and is imported by no other module of the package. It imports `hilclaw.keys` at most (not `hilclaw.spec`, `hilclaw.instance`, `hilclaw.tools`, `hilclaw.backends`).
- **It builds no spec and no part of one beyond these two values**: no `task` object, no `task.objective` (no parameter, no placeholder, no default), no `task.build`, no `hw_profile`, no `id`, no `guidance`. It does not check a spec against the contract (ADR-0008 Consequences leaves that to the code task that writes specs).

### Cases the record leaves to this task - choose, implement, test and list each with one line of reason
- The module, function and constant names; the call form; the form of the first-shapes collection; the exception class.
- The lower bound of a dimension (see `## Why`).
- Anything else you meet. If you read one as a rule about another kind, dtype, layout or language, a build setting, the coder's output, a shape outside the twelve being "first", a name for a projection, the objective, or a check of specs, do not decide it: return BLOCKED ("requirement unclear") with the exact question.

### Docstrings (CLAUDE.md "코멘트 최소화": no multi-line comments; docstrings of the public API may be as long as needed)
- Module docstring: what the module returns and by which record (ADR-0008 decisions 1, 2, 4, 5 and 9, on ADR-0001 and ADR-0002); what it does not do (no spec, no objective, no build settings, no check of a spec, no other contract, no file, no tool); that the guarantees and obligations of decisions 6 and 7 are not represented in any value it returns (decision 8).
- Nothing in a docstring is attributed to the repository owner except through the record's own citations (#5 B-4 for the shapes and the dtype, #5 A-7 for the language). Check every enumerating sentence against the record item by item before the first review.

### Tests (`tests/test_gemm_contract.py`, excluded from the size cap)
Helpers live in the test file and get no tests of their own (test rule 5).
- happy: `op_signature_record(1, 2048, 8192)` has the canonical form and the digest of decision 9 (`485b9bc494d477ebc8c9f02f861c3795beadacfb4cf690680cfaecba09f2d431`, name `gemm-485b9bc494d477eb`); **the twelve first shapes give exactly the twelve names of the table of decision 9, in its order** (write the table into the test as literals); `task_contract(1, 2048, 8192)` equals the JSON object of decision 5 member for member and in operand order; the prototype constant equals the line of decision 4.
- happy, across modules: a `task` built in the test from the two returned values and a synthetic `objective`, inside an otherwise valid synthetic spec, is accepted by `hilclaw.spec.validate` - for the first shape and for all twelve; the prototype constant occurs verbatim as a line of `hilclaw/harness/timing_driver.c` and of `hilclaw/harness/verification_program.c` (read through the package path, not a path relative to the working directory).
- branch: a shape with three different dimensions places each in the right operand position (`[m, k]`, `[k, n]`, `[m, n]`); equal dimensions (the 2048 → 2048 projection) are accepted; the largest accepted value (`MAX_INTEGER`) and the smallest; the first shapes are twelve, pairwise different, and their keys pairwise different; results of two calls are equal and not the same object; mutating a returned record, contract, operand list, operand or shape does not change the next result or a constant.
- error / negative, each raising and returning nothing: for each of `m`, `k`, `n` separately - a value below the lower bound, a negative value, `MAX_INTEGER + 1`, `True`, a `float` (`1.0`), a `str` (`"1"`), `None`, an `int` subclass instance; a missing argument; with the lower bound at 1, the value 0 for each dimension. Assert the exception class and that the message names the dimension.
- structure: no module of `hilclaw/` imports the new module; the new module imports neither `hilclaw.spec` nor `hilclaw.instance` nor `hilclaw.tools` nor `hilclaw.backends`; a call writes no file (a call with a temporary working directory leaves it empty).
- No test names a real machine, and none needs a compiler: every case runs on Linux (CI) and on Windows (the driver's clone).

Test rules of CLAUDE.md / DRIVER §5 (D12): 1 the package total of `hilclaw/` stays at or above 80 % lines and functions (99.49 % / 100.00 % at the T-0109 head; record the two figures of the final head and aim at no unexecuted line in the new module); 2 happy, error, branch and negative cases as above; 3 every public function of the new module has tests; 4 the new module has its test file `tests/test_gemm_contract.py`; 5 no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (measure the pass and skip counts on `origin/main` first; record before and after), `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
- `git diff origin/main --stat` lists only the two files of `touchesFiles`; `git grep -n "gemm_contract" -- hilclaw` matches the new module only; `git grep -n -E "^(import|from) .*(spec|instance|tools|backends)" -- hilclaw/gemm_contract.py` has no match; `git grep -n -i "objective" -- hilclaw/gemm_contract.py` matches docstring lines only; `git ls-files --eol` shows `i/lf` for both files. Record the line count of the non-test diff (cap 300 LOC / 5 files).
- CI on the PR: `gh pr checks <PR> --watch` ends with **every check of the final head successful** - six at planning time: `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. Record the run URL and the two coverage lines. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0110'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0110 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0110-gemm-contract-op-side-values` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0110`; executor commits end with the trailer `Task: T-0110`.
- After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) compare every returned value with ADR-0008 decisions 4, 5 and 9 character by character, the twelve names and their order included; (b) confirm that the module returns nothing the record does not give - no objective, no build setting, no label, no projection name, no further operand member; (c) re-check the planner's judgements in `## Why`: that the slice is selectable without the repository owner, the lower bound of a dimension and the fallback given for it, the module having no caller, and the A-13 reading; (d) confirm that the module is bound nowhere, writes nothing and checks no spec; (e) re-check each provisional choice and every enumerating docstring sentence item by item. If the reviewer reads the slice as needing the repository owner or a record, return BLOCKED with the exact question.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0110`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph, the provisional choices with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **Do not put a fenced code block into `## Result`** (`ruff format --check .` reads Markdown); use inline code, and write a percentage as a plain figure. Record: PR and commit, review rounds and findings, the **public API as landed** (names, signatures, the return forms, which situation raises what), the provisional choices, the lower bound as landed and whether a reviewer asked for the fallback, the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 150 non-test lines in one file; the cap is 300 LOC / 5 files (tests excluded).
- If ADR-0008 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the choices above, do not guess and do not edit a record: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- A committed example file of a spec, its place and its form; `task.objective` (OD-1, #5 A-4); a technique of the stand-in catalog (OD-22); the hw side (`hilclaw/standin_profile.py`); assembling or writing a spec (`hilclaw/spec_file.py`, OD-23).
- Checking that the `task.contract` of a spec is the one of ADR-0008; any change of `hilclaw/spec.py` or `hilclaw/keys.py`.
- `task.build`, compiler flags, the language standard, threads (ADR-0008 Boundaries "Build settings"; OD-6 sub-question 2).
- Any other contract: the SDPA family, another kind, dtype, layout or kernel language; shapes drawn outside the `op_signature` (OD-16 sub-question 1); what holds when a contract changes (OD-6 sub-question 4).
- Generating the C declaration of the harness files from the constant, or editing those files; replacing the literals of existing tests.
- Binding the values: any tool and its contract, `tools.default_registry`, the backends, a command-line entry, the start of an instance, writing `instance.json` or a `db/` record; anything HQ-0005, HQ-0006 or HQ-0007 asks.
- Any edit of an ADR, the OD register, OpenDecisionProposals, StandardScenarios, UsageCases, CLAUDE.md, DRIVER.md, PLAN.md, `.claude/`, `README.md`.

## Follow-ups
- (planner, when a caller exists) Whether the harness C files and the test literals take the prototype from this module; whether the writer of specs checks `task.contract` against it (ADR-0008 Consequences).
- (planner / integrator, a later record) Whether an op_signature of this contract may hold a dimension of 0, if the review left the point open.
- (driver / owner) HQ-0005 (T-0088), HQ-0006 (T-0106), HQ-0007 (T-0107). PLAN P1-5: `task.objective` (#5 A-4); the place and form of a committed example.
- (planner / integrator, a later record) What T-0109 left for ADR-0035: a macOS product version of several words; the unchecked statements (macOS, WSL 1, containers, a WSL kernel without `microsoft`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`).

## Result
**DONE** - landed on `main` as squash commit `24e2282` ("T-0110: Add gemm_contract, the op-side values of a spec for the first gemm contract (ADR-0008) (#82)"), PR https://github.com/myungjoo/HIL-Claw/pull/82 (code mode, Draft with `DONOTMERGE`, then ready and squash-merged by the executor; the squash body is the PR body, last line `Task: T-0110`). The remote and the local task branch were deleted in separate commands after the PR reported `MERGED`. **No BLOCKED exit and no new HQ.** This task ticks **no PLAN checkbox** (P1-5 stays open). Wall clock by `date -u`: started 2026-10-09T22:23Z, push run on `main` finished by 22:43Z. This `## Result` is left uncommitted for the driver.

§3-5 check before starting: no commit with `Task: T-0110` on `origin/main`, no PR for T-0110, no open PR - a fresh start. Issue #5: the last comment was the ADR-0035 notice (issuecomment-6089042706) at the start and again directly before the merge; no objection to ADR-0001, ADR-0002 or ADR-0008.

### Files
`hilclaw/gemm_contract.py` (new, 131 lines: 22 statements, the rest docstrings) and `tests/test_gemm_contract.py` (new, 372 lines, 125 cases). Nothing else changed.

### Public API as landed
- Constants: `KIND` = `"gemm"`, `DTYPE` = `"fp32"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"`, `PROTOTYPE` = the single line of ADR-0008 decision 4 (a `str`, no line break, semicolon included).
- `FIRST_SHAPES`: a `tuple` of twelve `(m, k, n)` tuples, in the order of the table of decision 9 (rows by projection (k, n) = (2048, 8192), (8192, 2048), (2048, 3072), (2048, 2048); columns m = 1, 32, 512). No projection has a name.
- `op_signature_record(m, k, n)`: returns a new plain `dict` with exactly `schema_version` (`keys.SCHEMA_VERSION`), `kind`, `shape` (a new `dict` with `m`, `k`, `n`), `dtype`, `layout`. No `label`, no `ext`; the key is not returned.
- `task_contract(m, k, n)`: returns a new plain `dict` with exactly `language`, `prototype`, `operands`; `operands` is a new `list` of three new `dict`s, `a` `input` `[m, k]`, `b` `input` `[k, n]`, `c` `output` `[m, n]`, each with `dtype` `fp32`, exactly the four members `name`, `role`, `dtype`, `shape`, and a new `list` as `shape`.
- Both functions take the three dimensions positionally or by name. Each must be exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`; otherwise `keys.InvalidRecordError` is raised before anything is built, with the message `shape.<m|k|n>: must be an integer from 1 to 2**53 - 1, got <reprlib.repr of the value>`; the first bad dimension in the order m, k, n is the one named. A missing or surplus argument is Python's own `TypeError`.
- The module imports `reprlib` and `hilclaw.keys` only, is imported by no module of the package, reads and writes no file and has no command-line entry.

### Provisional choices (each with its reason; all reviewed in three rounds)
- Names `gemm_contract`, `op_signature_record`, `task_contract`, `KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `FIRST_SHAPES`: the recommendations of this task file.
- Call form `(m, k, n)`, positional or by name: the order of the definition and of the prototype.
- `FIRST_SHAPES` as a tuple of tuples: a constant no caller can change, in the order of the table.
- No name for a projection: the record's words for them are prose.
- Exception class `keys.InvalidRecordError` with a message starting with `shape.<dimension>`: one class for a record `keys` would refuse and for one this module refuses, in the wording of `keys`.
- A missing or surplus argument: Python's own `TypeError`.
- **Lower bound of a dimension: 1, as the planner read it.** ADR-0001 allows 0; ADR-0008 decision 6 has the caller pass dimensions of at least 1. **No reviewer asked for the fallback**; all three accepted the bound as a provisional choice of the helper (`keys` and `spec` still accept 0, and the docstring, the commit and the PR body say that no record states the bound). A test pins the difference (`op_signature_key` accepts a shape with 0, this module refuses it).

### For a later record (not decided here)
- Whether an op_signature of this contract may hold a dimension of 0. Until a record says so, the bound of 1 is this module's own.
- Round-1 note: `keys.InvalidRecordError` is documented as "breaks a rule of ADR-0001", while the value 0 breaks no rule of ADR-0001 - the module's docstring states the difference; a later record or the first caller may want a class of its own.

### Where a criterion and the record differed
- The criterion for the module docstring asked for the sentence that the guarantees and obligations of decisions 6 and 7 "are not represented in any value it returns". Decision 4 has `restrict` state the no-overlap guarantee of decision 6 in the declaration, so the record wins: the landed sentence excepts what the prototype text itself states (round-2 finding).
- The docstring also lists `feedback` among the parts of a spec the module does not build (the criterion's list stops at `guidance`), so that the enumeration matches the top-level members of ADR-0002.

### Review rounds (3; fresh-context `dev-reviewer` each, model opus; comments on the PR)
- Round 1 (head `a14b2ab`): **Approve**, 3 Nit. Fixed: an unevenly wrapped docstring paragraph; a redundant rebinding of `m`, `k`, `n` in `task_contract`. Recorded above, not changed: the `InvalidRecordError` docstring note.
- Round 2 (head `5741a82`): **Approve**, 1 Nit, fixed: the docstring sentence on decisions 6 and 7 was stronger than the record (above).
- Round 3 (head `f7a4f61`): **Approve**, no finding, nothing trivially fixable left.
- All three compared the prototype, the contract of decision 5, the canonical form, digest and name of decision 9 and the twelve names with the record and found them equal, and agreed with the planner's judgements: selectable without the repository owner; the lower bound of 1 acceptable without the fallback; a module without a caller acceptable as for `standin_profile.local_record`; no A-13 BLOCKED reason applies (no new dependency, no schema or data-plane file). No result started with `SECURITY`.
- Round-3 remark, no finding: the structure test fails as soon as a module of the package imports `gemm_contract`, so the task that binds the values must change that assertion on purpose.

### Verification
- Local (Windows clone, `coverage` not installed - nothing was installed): `python -m pytest` on `origin/main` 11943 passed, 295 skipped; on the final head 12068 passed, 295 skipped (run before the first commit and again before the merge). `python -m ruff check .` and `python -m ruff format --check .` exit 0 (249 files).
- `git diff origin/main --stat` listed only the two files (503 insertions); `git grep -n "gemm_contract" -- hilclaw` has no match outside the new module (the module does not hold its own name, so no match at all); the import grep has no match; `git grep -n -i "objective"` matches one docstring line only; `git ls-files --eol` shows `i/lf` for both. Non-test diff: 131 lines in 1 file (cap 300 / 5).
- CI on the PR, final head `f7a4f61`, run https://github.com/myungjoo/HIL-Claw/actions/runs/38000027152: all six checks successful (`Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`). Coverage lines: `lines: 3186/3202 executed = 99.50` and `functions: 331/331 entered = 100.00`; `hilclaw/gemm_contract.py` 22 statements, none unexecuted. Three CI runs on the PR: the first was cancelled by the next push, none failed.
- After the merge: the `push` run on `main` for `24e2282` concluded `success` (https://github.com/myungjoo/HIL-Claw/actions/runs/38000509037).

### Language
Python - `keys` and `spec`, which must accept the values, are Python and the values are mappings for Python callers.

### Follow-ups left
- The four items of `## Follow-ups` stand as written; the second (a dimension of 0) is open, with the note on the exception class above.
- When a caller binds the values: change the structure assertion of `tests/test_gemm_contract.py` that no module of `hilclaw/` names `gemm_contract`.
