---
id: T-0014
title: Add the coverage gate for hilclaw/ (line >= 80%, function >= 80%) to CI
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#5 D12", "#9"]
dependsOn: [T-0003, T-0009, T-0011]
touchesFiles: [.github/workflows/ci.yml, pyproject.toml]   # plus .gitignore only if the coverage data file or the JSON report is written inside the tree
estimatedSize: {loc: 60, files: 3}   # one job of about 50 workflow lines and one pin line; HQ-0003 answered (a) / inline, so no script file
hq: [HQ-0003]
---
## Why
Owner decision D12 (2026-10-05, issue #5) adopted a coverage gate for the tool package: "**>= 80% line coverage and >= 80% function coverage** for the tool package; branch thresholds decided once data exists". CLAUDE.md test rule ① and DRIVER §5 rule ① already require every code-mode task to keep that level, but nothing measures it: code tasks that add or change a Python module under `hilclaw/` check reachability by hand with the stdlib `trace` module or a `sys.monitoring` script kept outside the repository (29 task files carried that instruction at d5e8e65, T-0055 `## Result` being the latest then). PLAN P0.5-3 is the CI gate that makes the rule mechanical. It is the only open P0.5 item that is not waiting on something else (the harness-pass half of P0.5-1 waits for P1-3 (T-0036); the rest of P0.5-4 is the owner's hook registration).

The task was **BLOCKED on HQ-0003** from 2026-10-06 to 2026-10-08. D12 fixes the two thresholds and the scope (`hilclaw/`) and nothing else; three choices were open, and the first one was a reason for owner involvement under CLAUDE.md A-13 ("new external dependency"). HQ-0003 asked, verbatim:

> PLAN P0.5-3 (coverage gate, D12: `hilclaw/` line >= 80% and function >= 80%) needs three choices D12 leaves open. (1) Tool: (a) add `coverage` (exact pin) to the `dev` dependency group, a new external dependency (A-13); or (b) a stdlib-only tracer (`sys.settrace` around pytest), a 100-150 line gate script that test rule 5 leaves untested? (2) Is "function coverage" = `def`s entered at least once / all `def`s in `hilclaw/` (methods and nested functions counted; lambdas, comprehensions and class bodies not)? (3) Are the thresholds on the package total, and may a CI check script live outside `hilclaw/` (a new top-level directory), or must it stay inline in the workflow as in T-0011?

**The owner's answer** (2026-10-08, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052108898; recorded as the `decision` of `HQ-0003` in `PROCESS/STATE.json`):
1. Tool: **(a)** — `coverage==7.16.2` added to the `dev` dependency group of `pyproject.toml` as an exact pin.
2. "Function coverage": **yes, as written** — a function is every `def` / `async def` under `hilclaw/`, methods and nested functions included; lambdas, comprehensions, generator expressions and class bodies are not functions. A function counts as entered when at least one of its lines executed. coverage.py's unnamed module-level region (name `""` in the JSON report) is not a function and is excluded from both the numerator and the denominator.
3. Aggregation and location: **package total, inline** — both thresholds apply to the package total of `hilclaw/`, not per module; the few lines that compute the function percentage from the JSON report stay inline in the workflow step as T-0011 did; no new top-level directory and nothing under `hilclaw/`.

Facts verified on 2026-10-08 by the integrator session (`main` at d5e8e65; local run on Windows, CPython 3.14.4, no `clang`, tools installed in a venv outside the repository):
- coverage 7.16.2 (released 2026-09-27, Apache-2.0, `requires-python >= 3.10`, cp311 and cp314 wheels, no transitive dependency) is the newest release. Its JSON report carries per-function data since 7.6.0: `files[<path>]["functions"][<qualified name>]` with `executed_lines`, `missing_lines`, `summary` and `start_line`. Methods and nested functions are their own entries (`Registry.get`, `_simple_commands.end_word`), lambdas are not entries, class bodies are listed under `classes`, and every file has one more entry named `""` for its module-level code. `coverage report --fail-under` checks the line total only; no report has a stock function percentage, so the function threshold has to be computed from the JSON report.
- `coverage run --source=hilclaw` lists a tracked module that no test imports with 0 executed lines, and its functions with empty `executed_lines` (checked on a scratch package outside the repository).
- First measurement, `coverage run --source=hilclaw -m pytest` on the whole suite: 5393 passed, 147 skipped; 62 s against 59 s without measurement. Lines 2331/2343 = 99.5%; functions by the definition above 233/233 = 100% (260 entries minus the 27 `""` ones); lowest module `hilclaw/harness/measurement.py` at 97.6% lines. A red first run therefore points at a defect of the measurement, not at the code.
- `pyproject.toml` pins exactly two dev tools (`pytest==9.1.1`, `ruff==0.16.10`); the owner's HQ-0002 answer made pin changes deliberate tasks. T-0011 kept its check inline in the workflow because a script inside `hilclaw/` would need a test file (rule ④) that rule ⑤ forbids, and a new top-level directory is a layout convention nobody has decided (T-0011 `## Result`, "Provisional choices").

The driver set this task back to `TODO` and made it `nextTask` at its §3-2 sync of 2026-10-08T04:39Z (commit f13c69d). The answer closes all three points, and the criteria below state them as requirements. If the executor meets a question this file does not cover, return BLOCKED ("requirement unclear") with the exact question instead of filling the gap.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12 — rules ① and ⑤ in particular, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8, §9, §11 row D12
- PROCESS/STATE.json — `humanQuestions[]` entry `HQ-0003`: `question` and `decision` (the owner's reply https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052108898 is the requirement of this task; read it in full: `gh api repos/myungjoo/HIL-Claw/issues/comments/6052108898 --jq .body`)
- PROCESS/PLAN.md — P0.5-3 (this task); P0.5-1, P0.5-2, P0.5-4 for what is not touched
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- Issue #5, comment "D12 confirmed (owner, 2026-10-05)": `gh api repos/myungjoo/HIL-Claw/issues/comments/5996957869 --jq .body` (items 2, 3, 5); the HQ-0002 answer on pins: `gh api repos/myungjoo/HIL-Claw/issues/comments/6011684226 --jq .body`
- Issue #9 (`gh issue view 9 --repo myungjoo/HIL-Claw --json body,comments`) — the CI gates and "Revision (D10)"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks ("can CI block bad code")
- PROCESS/tasks/T-0010-ci-sh-gate-shellcheck.md, PROCESS/tasks/T-0011-ci-test-presence-check.md and PROCESS/tasks/T-0035-ci-c-gate-clang-build.md — `## Acceptance Criteria` and `## Result`: the conventions of the workflow (first-party actions pinned by full commit SHA, least privilege, a separate job per gate, explicit `shell: bash`, the one-time red/green check with temporary commits and no force push, run evidence format) and why T-0011 stayed inline
- PROCESS/tasks/T-0009-pin-dev-tools-ruff-fixes.md — `## Result`: how an exact pin was added and verified
- PROCESS/tasks/T-0012-data-repo-config.md — `## Result` "Process incident": never put a branch deletion in a command line that also contains another step
- Existing files: `.github/workflows/ci.yml` (whole file, 100 lines: jobs `python` with the 3.11 / 3.14 matrix, `sh`, `c`, `test-presence`), `pyproject.toml`, `.gitignore`, `.editorconfig`, `.gitattributes`, the tracked Python files under `hilclaw/` including the `hilclaw/harness/` subpackage (`git ls-files 'hilclaw/*.py'`; 27 at d5e8e65), and `tests/` (what is measured; `tests/test___main__.py`, `tests/test_data_root_source.py`, `tests/test_driver_state.py`, `tests/test_journaled_tool.py`, `tests/test_mcp_front.py` and `tests/test_merge_guard.py` run `hilclaw` code in child processes: `python -m hilclaw`, `python -m hilclaw.driver_state`, `python -m hilclaw.mcp_front`, `python -m hilclaw.merge_guard`, or a helper script written to `tmp_path` that imports `hilclaw.__main__` and `hilclaw.mcp_front`)

## Acceptance Criteria
The three blocks marked **HQ-0003 (n)** carry the owner's answer of 2026-10-08 as requirements. Choices that neither D12 nor the answer fixes (job id and name, Python version of the measuring job, where the data file and the JSON report are written) are conventions of this task, provisional: state each with one line of reason in the commit body, the PR body and `## Result`.

Gate behaviour:
- The gate runs in `.github/workflows/ci.yml` on every `pull_request` and every `push` to `main`, as its own check (a separate job; suggested id `coverage`, suggested name `Coverage gate (hilclaw)`), so that the merge guard (`hilclaw/merge_guard.py`) and the executor see it by name. `runs-on: ubuntu-latest`; the same `actions/checkout` and `actions/setup-python` commit SHAs, `persist-credentials: false` and dev-tool install steps as the `python` job (copied, not bumped).
- It measures the whole test suite (`python -m pytest`, all of `tests/`) against **every tracked Python file under `hilclaw/`**, taken from the tree and not from what the tests happened to import: a module that no test imports counts with 0 executed lines and 0 entered functions, it does not drop out of the denominator (`coverage run --source=hilclaw` does this; the subpackage `hilclaw/harness/` is included).
- It fails (non-zero exit of the step) when line coverage is below 80% or when function coverage is below 80%, and also when the test run itself fails or the measurement produces no data. Both thresholds are checked independently; exactly 80% passes. The two numbers 80 appear once each, in one place.
- The log shows both percentages and, when the gate fails, which threshold was missed and the files (for functions: the function names) that are not covered.
- No branch-coverage threshold (D12: "decided once data exists"). Printing branch data is allowed only if coverage.py gives it without extra configuration; it never fails the gate.
- The existing jobs `python`, `sh`, `c` and `test-presence`, the triggers, the top-level `permissions` and the `concurrency` block stay byte-for-byte unchanged. In particular the `python` job keeps running the plain `python -m pytest` on 3.11 and 3.14.
- The measuring job uses one Python version of the matrix; say which and why (coverage.py measures with its `sysmon` core on 3.14 and with its C tracer on 3.11). If the two versions could give different verdicts near the threshold, record that as a known limit.
- Code run in a child process (the `python -m hilclaw…` runs and the `tmp_path` helper scripts of the six test files named above) need not be measured; if it is not, say so in `## Result` as a known limit together with the lines it leaves uncounted.
- No coverage data file, report or cache is committed. coverage.py writes `.coverage` into the working directory by default and the JSON report where `-o` points: either direct both outside the checkout (`--data-file`, `-o`) or add both names to `.gitignore` (then `.gitignore` joins `touchesFiles`).
- No exclusion list, no `# pragma: no cover`-style markers and no per-file waivers are introduced by this task: `hilclaw/` is measured as it is. If the gate is red on `main`'s own code at the first run (the 2026-10-08 measurement above says it should not be), do not lower a threshold or exclude code: return BLOCKED ("requirement unclear") with the measured numbers.

**HQ-0003 (1)** — the tool: (a) `coverage==7.16.2`:
- Add exactly one line, `"coverage==7.16.2",`, to the `dev` group of `pyproject.toml` and nothing else there (no `pytest-cov`: the answer does not name it). The CI job gets it through the same `pip install --group dev` step as the `python` job. Install the same version locally, outside the repository (a venv or the user site), before the local runs.
- Function data comes from `coverage json` (`files[<path>]["functions"]`, see `## Why`); the text report has no function figure and `--fail-under` checks the line total only, so the step computes the function percentage itself (block (3)).
- Any configuration goes into `pyproject.toml` (`[tool.coverage.*]`), not into a new file.

**HQ-0003 (2)** — "function coverage", as answered:
- Functions entered at least once during the test run, divided by all functions defined under `hilclaw/`, where a function is every `def` / `async def` (methods and nested functions counted; lambdas, comprehensions, generator expressions and class bodies not counted). A function is entered when at least one of its lines executed, that is when its `executed_lines` in the JSON report is non-empty. The entry named `""` that coverage.py lists under `functions` for every file (module-level code) is not a function: leave it out of numerator and denominator. Entries of `classes` are not functions either.
- Consequence to record as a known limit: a function with no executable line (a docstring-only body) is listed under `functions` with empty `executed_lines` and `num_statements` 0 (verified on 7.16.2 with a scratch file), so it counts as not entered; none existed on `main` at d5e8e65 — re-check the measured tree with a one-line `ast` walk and record the result in `## Result`.
- State the implemented definition in one sentence in the commit body, the PR body and `## Result`, and make the log line name it (for example `functions: 233/233 entered`).

**HQ-0003 (3)** — package total, inline:
- Both thresholds apply to the package total of `hilclaw/`: executed statements over all statements of every measured file, entered functions over all functions of every measured file. No per-module threshold; per-module numbers may be printed.
- All gate logic lives in `.github/workflows/ci.yml` as T-0011's did: the measurement commands and the function computation (Python reading the JSON report, run from a heredoc or `python -c`) are steps of the new job. No script file anywhere in the tree — none under `hilclaw/` (rule ④ would demand a test file that rule ⑤ forbids) and no new top-level directory.
- Language of the inline logic: Python for reading the JSON report, bash for the workflow glue as in T-0010 / T-0011 — within the CLAUDE.md language policy; one line of reason in the commit body and `## Result`. `ruff` does not see Python embedded in YAML: keep it short and lay it out as `ruff format` would.

Tests:
- **No test file is added or changed.** The gate is a CI workflow: tests that target it are forbidden (CLAUDE.md test rule ⑤, DRIVER §5 rule ⑤, the owner's global rule). The two named exceptions (driver `STATE.json` validator, `gh pr merge` guard hook) do not include this gate. No module under `hilclaw/` is touched, so rules ②-④ are vacuous and rule ① is what the gate itself reports.
- The cases a code task would cover with tests are covered by the one-time check below instead: happy (the real tree passes), error (a failing test fails the gate), branch (line threshold and function threshold each fail on their own; an unimported module counts as 0), negative (no data / broken measurement fails the gate instead of passing).

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` exit 0 (5393 passed and 147 skipped at `d5e8e65`; the skips are the real-clang tests, POSIX-only behaviour and symbolic-link cases that the Windows driver machine cannot run). Run the measurement locally as well and record both percentages; local numbers are lower than CI's by the skipped real-clang tests — say by how much. `git ls-files --eol` shows `i/lf` for every changed file; `git status --short` after the runs shows no stray file.
- The PR's first run with the final workflow on the unchanged tree: `gh pr checks <PR> --watch` ends with **six** successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)` and the new job. Quote the two percentages from the new job's log; they are the first coverage data of the project.
- One-time check that the gate works in both directions (dev-code-review: "can CI block bad code"), done **before** requesting the review, with temporary commits on the PR branch and never a force push. Each step is its own commit and its own CI run:
  1. Function threshold alone: add a temporary module `hilclaw/tmp_t0014_a.py` with many trivial functions whose one-line body is on its own line (`def f1():` then `return 1`; a body written on the `def` line executes at import and counts as entered, verified on 7.16.2) and a temporary `tests/test_tmp_t0014_a.py` that imports it and calls none or few of them, sized so that package function coverage falls below 80% while line coverage stays at or above 80% (the `def` lines execute at import; the uncalled functions must number more than a quarter of the entered ones — 59 or more at d5e8e65's 233; `main` has moved since, so take the count from the first green run's `functions: N/N entered` line). Expect: the new job **fails** naming the function threshold; the other five checks stay green.
  2. Line threshold: change the temporary module to one function with a long body that the temporary test never calls, sized so that line coverage falls below 80% (the never-run statements must exceed 1.25 × executed − total, both counted with the temporary module's own `def` line: 572 or more at d5e8e65's 2331/2343 (2332/2344 once that line is counted) — 571 lands exactly on 80.00%, which passes — about 600 for margin; recompute from the first run as in step 1). Expect: the new job **fails** naming the line threshold.
  3. Unimported module: make the temporary test file import nothing from the temporary module (keep the file, so that `Test presence (hilclaw)` stays green). Expect: the module is listed with 0% and the gate is still red — it did not drop out of the denominator.
  4. Failing test: restore full coverage of the temporary module and add one failing assertion to the temporary test. Expect: the new job **fails** because the test run failed (the `python` job is red too, by design).
  5. Delete every temporary file. Expect: all six checks green. `git diff origin/main --stat` must then list only the files in `touchesFiles`.
  The deliberate red runs do **not** count toward the "CI 3 consecutive failures" BLOCKED counter. The squash-merge removes the temporary commits from `main`. The "no data" direction (the measurement step produced nothing) is shown by reading the step's logic in the review, or by one more temporary commit if it can be provoked without editing the final workflow lines; say which.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0014-coverage-gate`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0014`; executor commits end with the trailer `Task: T-0014`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds).
- Squash-merge per CLAUDE.md A-13 with `Task: T-0014` as the last line of the PR body, using `gh pr merge <number> --squash --body-file <file>` with a literal PR number. Merge only when every check of the final head is successful. Delete the branch **after** the merge is confirmed, in a separate command.
- Commit body: the owner's answers to HQ-0003 (1)-(3) with the link https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052108898; the provisional choices with one line of reason each; the first CI-measured percentages; the language line for the inline Python.
- `## Result`: hand the text to the driver in the final report instead of committing this task file on the branch, so that the diff check holds (as T-0008, T-0012 and T-0013 did). `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. **PLAN P0.5-3 is ticked** when this task is DONE.
- Pushing a file under `.github/workflows/` needs the `workflow` scope on the `gh` / git token (present for T-0003, T-0010, T-0011, T-0035). If the push is rejected for that reason, return BLOCKED and name the missing scope.
- Size: about 60 changed lines in 2 files (3 with `.gitignore`); below 300 LOC / 5 files. If it turns out larger, propose a split in Follow-ups and finish the current scope only (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.

## Out of Scope
- Changing any of the HQ-0003 answers; any dependency other than `coverage==7.16.2` (no `pytest-cov`); a script file or a new directory for the gate logic.
- A branch-coverage threshold, a per-PR "coverage must not drop" rule, diff coverage, coverage badges, uploading reports to a third-party service, any third-party GitHub action.
- Raising coverage: no change to `hilclaw/` or `tests/` on `main` (if the first measurement is below a threshold, that is a BLOCKED report, see above).
- Measuring code run in subprocesses, C or sh code, or anything outside `hilclaw/`.
- The harness-pass half of P0.5-1 (the clang-build half landed as the `c` job, T-0035), registering the merge guard hook (rest of P0.5-4, an owner action), bumping `pytest`, `ruff` or the action SHAs, changing the `python`, `sh`, `c` or `test-presence` jobs.
- Editing CLAUDE.md, the skills, README.md, DRIVER.md, PLAN.md or `ARCHITECTURE/` (document mode, separate changes).

## Follow-ups
- (integrator, document mode) Once the gate is on `main`: CLAUDE.md test rule ① and DRIVER §5 rule ① can name the job as the mechanical check; task files no longer need the hand-run `python -m trace` reachability check and the planner stops copying the "install nothing" instruction into code tasks; README "로컬 검사" gains the local command. The "CI 미구축" notes are still pending from T-0003 / T-0010 / T-0011.
- (owner, with data) Branch threshold (D12: "once data exists"): this task's first measurement is the first data point.
- (decision to revisit) Whether subprocess-run code should be measured, and whether the gate should run on both matrix versions.
- (owner) Coverage of C code: `hilclaw/harness/timing_driver.c` (T-0033) is in the tool package but outside this gate, which measures the Python part; D12's wording does not say whether C counts. Raise it as a question when the harness-pass half of P0.5-1 is planned.
- (driver, D15 migration) With this gate, CI on `main` carries six checks; the remaining precondition of the D15 migration is still the owner's hook registration (P0.5-4).

## Result
