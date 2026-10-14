---
id: T-0180
title: Commit the GEMM spec example examples/spec/gemm-485b9bc494d477eb.json fixed by ADR-0058 with a test that makes checks T1-T4 of its decision 4, completing PLAN P1-5
phase: P1
status: DONE
commitMode: code
coversReq: [FR-5, OD-6, "#5 B-4"]
dependsOn: [T-0179]
touchesFiles: [examples/spec/gemm-485b9bc494d477eb.json, tests/test_spec_example.py]
estimatedSize: {loc: 25, files: 1}   # the example file only; the test file (about 100-160 lines) is outside the cap (DRIVER §5)
hq: []
---
## Why

PLAN P1-5 ("GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — OD-6 종결 필요(§9 ADR 경로)") is open. T-0179 landed ADR-0058 (aa00f86), which settles under DRIVER §9 what the committed example is, where it lives, in which form, what stands for the "`spec.json` 스키마" (the records plus `hilclaw/spec.py` and `hilclaw/spec_file.py`; no JSON Schema file), and the **completion criterion of P1-5** (ADR-0058 decision 5): (i) ADR-0058 and its register edits — on `main`; (ii) version 2 in `hilclaw/spec.py` and `hilclaw/spec_file.py` — on `main` since T-0148; (iii) the file of decision 4 with the content of the Example; (iv) a test under `tests/` that makes the checks T1 to T4 and passes in CI. **This task delivers (iii) and (iv).** ADR-0058 Consequences names it as "the code slice for the planner" and states that it needs no new dependency, no schema change and no data-plane file.

**Why this item now.** No lock, no open PR, no TODO or INTERRUPTED task. Every other non-DONE task is blocked by an unanswered HQ (HQ-0013, HQ-0014, HQ-0016..HQ-0019 `runtime-acceptance`; HQ-0020 `data-plane-schema-change` on T-0176). This task depends on none of them and on no HQ answer.

**Planner's judgements (the reviewer is asked to re-check each):**
- **Code mode.** `examples/` is outside the document-mode paths (CLAUDE.md A-13: `ARCHITECTURE/`, `CLAUDE.md`, `.claude/`, `README.md`, `PROCESS/`), and the test is code. Draft PR, review cycle, CI green, squash-merge.
- **No invention.** Every byte of meaning in the example is fixed by ADR-0058's Example (lines 75-111). The executor copies values; it chooses only the text layout (free, decision 4), the test file's name and the test's structure.
- **The ADR-0058 objection window** runs to 2026-10-21 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6166739084). Building on an accepted §9 record inside its window is the normal path; an owner objection on #5 stops this task (see Process).
- **Test rules (D12).** No `hilclaw/` module is added or changed, so coverage is unaffected and the CI test-existence check (which maps `hilclaw/` modules to `tests/`) does not ask for a file; the new test checks a committed example against the package as ADR-0058 requires, which is not a test of test code, CI or hooks (rule 5 does not apply). Rule 2 still applies: the test includes negative cases showing that its checks can fail.
- **D16.** Nothing here needs `claude`, a board or an API key; pytest and ruff only.

## Required Reading

Line numbers are those of `main` at `3f5f428`; the text wins. Read Python sources with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, the D12 test rules, the PR-body `Task:` line and `gh pr merge --squash --body`).
- CLAUDE.md, the whole file; above all "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책" (record the language and reason in the commit body), "개발 드라이버와 런타임의 구분", "코멘트 최소화", "바이너리 금지".
- .claude/skills/dev-item-address/SKILL.md (code mode, whole procedure); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md**: Limits (lines 26-32), decisions 2 to 6 (lines 42-73), **the Example (lines 75-111)**, Consequences (129-139), Boundaries (141-146).
- `hilclaw/spec_file.py` lines 1-60 (module docstring) and `parse` (lines 202-250): takes `bytes`, raises `InvalidSpecFileError` / `UnsupportedVersionError`.
- `hilclaw/spec.py` lines 1-108 (`validate`, `InvalidSpecError`; `_keyed` checks that each `key` is derived from its `record`).
- `hilclaw/gemm_contract.py` lines 1-170 (`FIRST_SHAPES`, `op_signature_record`, `task_contract`, `PROTOTYPE`).
- `hilclaw/keys.py` lines 49-55 (`Key` with `.name`), 99-163 (`hw_profile_key`, `op_signature_key`).
- `tests/test_spec_file.py` lines 1-60 and `tests/test_gemm_contract.py` (house style of tests; imports; synthetic-values note).
- `.gitattributes` (`* text=auto eol=lf`: the JSON file is checked out with LF on every platform) and `.github/workflows/ci.yml` lines 30-50 (ruff check, ruff format --check) and 115-135 (test-existence check).
- `pyproject.toml` (pytest `testpaths`, `pythonpath`; ruff settings).

## Acceptance Criteria

### The example file

- New file `examples/spec/gemm-485b9bc494d477eb.json` whose parsed document equals the ADR-0058 Example exactly: every member and value as printed there (lines 79-100), `guidance.techniques` the empty array, `feedback.attempts` the empty array, no `repair`, no `task.build`, no `ext`, no `feedback.base`. Copy, do not retype from memory: the prototype string and the hw strings must match byte for byte.
- UTF-8 without a byte order mark, LF line ends, a final line feed, no carriage return byte, no member name twice, integers in decimal digits. Layout (indentation, line breaks, member order) is free; a plain readable layout such as `json.dumps(..., indent=2) + "\n"` or the Example's own layout is fine. `git ls-files --eol` shows `i/lf` for it.
- No other file under `examples/`. No README or index file there (the ADR does not ask for one).

### The test (`tests/test_spec_example.py`, pytest)

Locate the file from the test's own path (for example `Path(__file__).resolve().parent.parent / "examples" / "spec" / "gemm-485b9bc494d477eb.json"`), read it with `read_bytes()`, and make these checks (ADR-0058 decision 4):

- **T1**: `hilclaw.spec_file.parse(content)` accepts the bytes (returns a document, raises nothing).
- **T2**: the bytes end with `b"\n"` and contain no `b"\r"`; they do not start with the UTF-8 byte order mark.
- **T3**: the parsed document equals the Example. Build the expected document in the test: the op side from `gemm_contract.op_signature_record(1, 2048, 8192)` with key `keys.op_signature_key(<that record>).name` (and assert that name is `"gemm-485b9bc494d477eb"`, the value ADR-0008 decision 9 spells), `task.contract` from `gemm_contract.task_contract(1, 2048, 8192)`; the hw_profile record written out literally as in the Example with key `keys.hw_profile_key(<record>).name`, and assert it is `"cpu_standin-8c0be275e5925ab0"`; `id`, `task.objective`, `guidance` and `feedback` literal as in the Example; `schema_version` equal to `spec.SCHEMA_VERSION` and to 2. Compare whole documents (`==`), and assert `guidance.techniques == []`.
- **T4**: for each `(m, k, n)` in `gemm_contract.FIRST_SHAPES` (assert there are twelve), a deep copy of the parsed example with `task.op_signature` replaced by `{"key": keys.op_signature_key(r).name, "record": r}` for `r = op_signature_record(m, k, n)` and `task.contract` replaced by `task_contract(m, k, n)` is accepted by `hilclaw.spec.validate`. Parametrise over the shapes so that each shape is its own test case.
- **Negative cases (D12 rule 2)**, showing the checks are not vacuous; at least:
  - the T4 substitution with the record of one shape and the key of another is refused by `spec.validate` (`InvalidSpecError`);
  - the T4 substitution with the record replaced but `task.contract` left at M = 1 (for a shape with M ≠ 1) is refused by `spec.validate`;
  - the example's bytes with a byte order mark prepended are refused by `spec_file.parse` (`InvalidSpecFileError`);
  - the example document with `guidance.techniques` set to the ADR-0050 placeholder `[{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]` is **not** equal to the expected document of T3 (the T3 comparison distinguishes the placeholder; do not assert anything about whether `validate` accepts it).
  If one of these does not fail as stated, do not weaken the assertion: report it in `## Result` (it would be a finding about `hilclaw/spec.py` or about ADR-0058, outside this task).
- The test reads only the example file and imports only `hilclaw` modules, the standard library and pytest. It writes no file, opens no network and starts no process.
- Use synthetic or cited values only; the file carries no real machine's strings and no real run id (ADR-0058 decision 3).

### Checks

- `python -m pytest` passes (whole suite), `python -m ruff check .` and `python -m ruff format --check .` are clean, locally and in CI (all jobs green). Coverage of `hilclaw/` is unchanged and above the gate.
- `git diff --check` is clean. Size: one non-test file of about 25 lines plus the test file.
- No file outside `touchesFiles` changes; in particular no `hilclaw/` module, no ADR, no register, no `PROCESS/` file, no README.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0180'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0180 --state all`. Then the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR touching `examples/` or `tests/test_spec_example.py` makes the task BLOCKED ("open PR conflict"); none was open at planning time (2026-10-14).
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6166739084 (the ADR-0058 owner notice). Skip the driver's own comments (ending `— posted by driver`). An owner comment that objects to ADR-0058 (or to ADR-0002, ADR-0008, ADR-0050, ADR-0051 on a point the example uses) makes the task BLOCKED ("requirement unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0180-committed-gemm-spec-example` from `origin/main`; Draft PR whose title contains `T-0180` and whose body ends with the line `Task: T-0180`; reviewer cycle of dev-item-address with a fresh-context `dev-reviewer` each round, at most 7 rounds (past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; no reviewer can be spawned: BLOCKED — do not review your own work). Ask the reviewer to (a) compare the example file value by value with the ADR-0058 Example and with `hilclaw.gemm_contract`; (b) check that T1-T4 and the negative cases are each present and can fail; (c) confirm no file outside `touchesFiles` changed. CI green on the head (CI 3 consecutive failures: BLOCKED), then `gh pr ready`, `gh pr merge --squash --delete-branch --body "<PR body>"` so the squash message keeps `Task: T-0180`. Commit messages in English, ending with the trailer `Task: T-0180` and any attribution trailer the session requires; the commit body names the language (JSON data plus a Python/pytest test) and why in one line.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). Record the PR and squash commit, review rounds and findings, CI run, the test count, whether each of ADR-0058's completion items (i)-(iv) is now on `main` (so the driver can tick P1-5), and follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any change to `hilclaw/` (spec, spec_file, gemm_contract, keys): a defect found there is a follow-up, not fixed here.
- Any JSON Schema file (ADR-0058 decision 5), any technique entry or catalog document (OD-22), any constraint value (ADR-0050 O2), any real machine's hw strings or real run id, examples of other call shapes (repair, N > 1, a base) or other op_signatures as files.
- Editing ADR-0058 or any other record, the registers, StandardScenarios, README or PLAN (the PLAN tick is the driver's).
- The four non-blocking round-7 nits of T-0179 on ADR-0058 and StandardScenarios (a separate document-mode task).
- OD-18 sub-question 17 / HQ-0020 (T-0176) and the run-tool contracts of P1-1.

## Follow-ups

- (driver) If `## Result` reports (iii) and (iv) of ADR-0058 decision 5 on `main`, tick PLAN P1-5.
- (planner, document mode, small) The four non-blocking round-7 findings of T-0179 on ADR-0058 and `StandardScenarios.md` (listed in `PROCESS/tasks/T-0179-adr-od6-committed-gemm-spec-example.md` `## Follow-ups`).

## Result

- **Outcome: DONE.** PR #125 (https://github.com/myungjoo/HIL-Claw/pull/125) squash-merged as `5f5621a` on `main`; branch deleted. Squash message ends with `Task: T-0180`.
- **Checks before work.** Landed check: no commit with `Task: T-0180`, no PR matching T-0180; no open PR at all. Issue #5 after the ADR-0058 notice (comment 6166739084): no further comment, so no owner objection and no answer to HQ-0013, HQ-0014, HQ-0016..HQ-0020.
- **Files.** `examples/spec/gemm-485b9bc494d477eb.json` (20 lines): lines 80-99 of ADR-0058 copied verbatim (the Example's own layout), so every string is byte-identical; `git ls-files --eol` gives `i/lf w/lf`; no BOM, no CR, final LF. `tests/test_spec_example.py` (22 tests): T1 parse; T2 written form; T3 whole-document `==` against a document built from `gemm_contract.op_signature_record/task_contract(1, 2048, 8192)` and `keys`, with `gemm-485b9bc494d477eb`, `cpu_standin-8c0be275e5925ab0` and `SCHEMA_VERSION == 2` asserted; T4 parametrised over the 12 `FIRST_SHAPES` (count asserted); negatives: key of another shape (refused), record at M = 512 with the example's contract left at M = 1 (refused), prepended BOM (refused by `parse`), ADR-0050 placeholder technique (not equal to T3's expected), plus a changed run id (not equal). Every negative failed as stated; no finding on `hilclaw/spec.py` or ADR-0058.
- **Language.** JSON data as ADR-0058 fixes it; Python/pytest test because the checks call the `hilclaw` package (in the commit body).
- **Review.** 2 rounds, fresh-context `dev-reviewer` each. Round 1 Approve with two non-blocking nits: the M = 1 negative used `task_contract(1, 8192, 2048)` instead of leaving the example's own contract (fixed in 7e1dacf: now replaces only the op_signature with (512, 2048, 8192) and asserts the contract is unchanged); an extra run-id negative beyond the list (kept, harmless). Round 2 Approve, no findings. Reviewer noted `spec.validate` does not check the prototype string's value; T3's whole-document comparison covers it for the example (not a defect, ADR-0002 does not make it a rule).
- **CI.** Run 38557063652 on head 7e1dacf: all six jobs green (Python 3.11, 3.14, Coverage, C, sh, Test presence). Locally: `python -m pytest` 18627 passed, 351 skipped; ruff check and format clean; `git diff --check` clean. No `hilclaw/` module changed, so coverage is unchanged.
- **ADR-0058 decision 5 completion items on `main`:** (i) ADR-0058 and register edits — yes (aa00f86); (ii) version 2 in `hilclaw/spec.py` and `hilclaw/spec_file.py` — yes (since T-0148); (iii) the example file — yes (5f5621a); (iv) the T1-T4 test passing in CI — yes (5f5621a, run 38557063652). **The driver can tick PLAN P1-5.**
- **D16.** No `claude` process started by the executor or the reviewers; nothing needed a board or API key.
- **Follow-ups.** None new. The existing one stands: the four non-blocking round-7 nits of T-0179 on ADR-0058 and StandardScenarios (document mode).
