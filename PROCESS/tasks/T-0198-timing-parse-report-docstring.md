---
id: T-0198
title: Make the `parse_report` docstring of `hilclaw/harness/timing.py` name `judge_report` as the function that reports a zero interval as broken
phase: P1
status: DONE
commitMode: code
coversReq: [FR-9, FR-10, OD-13, "#5 D12"]
dependsOn: [T-0194]
touchesFiles: [hilclaw/harness/timing.py]
estimatedSize: {loc: 4, files: 1}   # docstring sentences only; no code line, no test file expected
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts, `sim.run` / `board.run` included) is open. T-0194 (PR #134, `7ac9490`) split the judging half out of `run_timing` into the public `judge_report` of `hilclaw/harness/timing.py` (ADR-0061 decision 3; code slice (2)). Its round-2 reviewer left one Nit, out of that task's scope because it put `parse_report` out of scope; it has been carried as a follow-up by T-0194, T-0195, T-0196 and T-0197:

> **Nit: one sentence in the `parse_report` docstring is now less exact.** It still says "An `interval_ns 0` line is of the form here; it is :func:`run_timing` that reports the run as broken." After this change `judge_report` also reports it, and `_judgement` is where it happens. The sentence is still not false, and the task puts changes to `parse_report` out of scope, so leaving it is acceptable. If the docstring is touched later, "it is :func:`judge_report` (and so :func:`run_timing`) that reports it as broken" would be exact.

State of `main` at `8be645b`: `hilclaw/harness/timing.py` (372 lines), `parse_report` at lines 193-210, docstring lines 194-201; the sentence is at lines 199-200. This task makes it exact. It is a docstring-only change of a `hilclaw/` module, so code mode (precedents: T-0175, T-0189).

It ticks **no PLAN checkbox** (P1-1 stays open) and changes no OD.

Planner's judgements (the reviewer is asked to re-check each):
- **No undecided design.** `judge_report` reporting `Broken.ZERO_INTERVAL` and `run_timing` using the same private `_judgement` are landed code (T-0194) and stated in the module docstring (lines 50-53). The sentence only describes them.
- **A-13 (data plane)**: nothing of the data plane changes; no code line changes.
- **D16**: nothing here needs the `claude` program, a compiler, a container runtime, a board or an API key.
- **Sibling sentences checked by the planner (2026-10-15, `main` at `8be645b`)**: the module docstring of `timing.py` (lines 1-19, 48-56, 66-70) and the `Judgement` / `TimingResult` docstrings were rewritten by T-0194 and already name `judge_report`. The `run_timing` mentions in `hilclaw/harness/memory_ceiling.py` line 16 (which run yields a figure: still only `run_timing`, since `judge_report` takes no usage), `hilclaw/harness/timing_build.py` line 7 (what starts the executable) and `hilclaw/harness/verification.py` line 61 (the `executable` convention) stay exact. No other sibling nit of the same kind is open, so nothing is folded in. The T-0197 optional wording nits are in ADR-0062 (document mode) and the T-0196 finding on the name `run_identity.step_of` is a note for the tool-function task; neither belongs here.
- **Session entry check (planner)**: `gh pr list --state open` is empty. No comment on issue #5 after the ADR-0062 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6189063464) was found by T-0197. HQ-0013, 0014, 0016..0019 are `runtime-acceptance` notices and block nothing. The task touches no `ARCHITECTURE/` file.

## Required Reading

Line numbers are those of `main` at `8be645b`; the text wins. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, `T-NNNN` naming, the 2h30m limit) and **§5** (task format, naming and trailers, size cap D4, language line, test rules ① to ⑤). These are mandatory for every task (§6). Also read §1-5 (forbidden actions; a denied or failed tool call is BLOCKED) and the "BLOCKED 사유" paragraph after §3-7.
- CLAUDE.md, the whole file. Above all: "코멘트 최소화", "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (code mode), "테스트 규칙".
- .claude/skills/dev-item-address/SKILL.md (code mode path); .claude/skills/dev-code-review/SKILL.md.
- ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md decision 4 (an interval of 0 makes the run broken) and decision 8 (the report form).
- ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md decision 3 (the tool function does all of the judging of a timing run).
- PROCESS/tasks/T-0194-timing-judge-report.md `## Result` (the split as landed).
- **Code to edit**: `hilclaw/harness/timing.py`. Read the module docstring (lines 1-71), `Report`, `Judgement`, `TimingResult` (lines 116-170), `parse_report` (lines 193-210), `judge_report` (lines 213-251), `run_timing` docstring (lines 254-313) and `_judgement` (lines 315-326).
- **Code to read and not to edit**: `hilclaw/harness/memory_ceiling.py` (line 16), `hilclaw/harness/timing_build.py` (lines 4-10), `hilclaw/harness/verification.py` (lines 56-63).
- `tests/harness/test_timing.py`: confirm that no test asserts the docstring text (no `__doc__` use at planning time). Do not edit it.

## Acceptance Criteria

### The change
1. In the docstring of `parse_report`, the sentence "An ``interval_ns 0`` line is of the form here; it is :func:`run_timing` that reports the run as broken." is made exact: it names :func:`judge_report` as the function that reports such a report as broken (``Broken.ZERO_INTERVAL``), and says that :func:`run_timing` does so through the same judging. The reviewer's suggestion ("it is :func:`judge_report` (and so :func:`run_timing`) that reports it as broken") is acceptable; the wording is the executor's. It keeps "An ``interval_ns 0`` line is of the form here". Keep it short (CLAUDE.md "코멘트 최소화"); do not name the private `_judgement`.
2. Read the rest of the `timing.py` docstrings for any other sentence that T-0194's split made less exact and bring it in line the same way. List each sentence changed, and each checked and left, in `## Result`.
3. **No code line changes.** No signature, constant, import, message or behaviour of `hilclaw/harness/timing.py` changes. `git diff` shows changes inside docstrings only.

### Do not invent
- No new condition, order or rule of the judging; no change to the report form.
- No edit of any module other than `hilclaw/harness/timing.py`. A less exact sentence found elsewhere is listed in `## Result` as a follow-up, not edited.
- No ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit. No new external dependency.
- **Guarded exit**: if making a sentence exact seems to need a decision that no record holds, stop and return BLOCKED (`requirement-unclear`), quoting the sentence and writing the question for an HQ.

### Tests (CLAUDE.md test rules, D12; DRIVER §5)
- Docstring-only change: no new test is required. The existing tests in `tests/harness/test_timing.py` cover every public function of the touched module (rule ③: `driver_arguments`, `parse_report`, `judge_report`, `run_timing`) with happy, error, branch and negative cases. Confirm this in `## Result` by naming the test groups.
- No test targets test code, the CI workflow or a script (D12 rule ⑤).
- `hilclaw/` line and function coverage stay >= 80% (CI gate).

### Gates
- `python -m pytest` passes locally. `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- CI is green on the PR, all jobs. Put the coverage figures from the CI gate in `## Result`.
- `git diff --stat origin/main` lists only `hilclaw/harness/timing.py`. `git diff --check` is clean.

### Process
- Work only in the driver's dedicated clone. First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0198'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0198 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR that touches `hilclaw/harness/timing.py` makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6189063464 and skip comments ending `— posted by driver`. An owner comment that objects to ADR-0061 decision 3 or ADR-0009 decision 4 makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, 0014, 0016..0019 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Reviewers are spawned with the session's own agent tool and told to write no file and to start no `claude` process.
- **Code mode** (CLAUDE.md A-13):
  - Branch `claude/T-0198-timing-parse-report-docstring` from `origin/main`.
  - Open a Draft PR with `T-0198` in its title and `Task: T-0198` as the last line of its body.
  - Run the reviewer cycle with a fresh-context `dev-reviewer` each round, given the PR and this task file's path. At most 7 rounds; past the cap without Approve: BLOCKED. A result starting with `SECURITY`: BLOCKED. If no reviewer can be spawned: BLOCKED; do not self-review.
  - Ask the reviewer to (a) check the edited sentence against `judge_report`, `run_timing` and `_judgement` as they are; (b) confirm that no code line changed; (c) look for any other less exact sentence in `timing.py`, and name any in other modules.
- **Merge**: when the last review is an Approve and CI is green on the head, run `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0198` (then any attribution trailer the session requires). Delete the branch, then check out `main` at `origin/main`.
- **Commit and PR text**: English. Executor commits end with the trailer `Task: T-0198`. The commit body has one line on the language (Python, as the rest of the `hilclaw` package; docstring only).
- **CI**: three consecutive failing runs are BLOCKED (`ci-3-consecutive-failures`). A run that starts no job counts as a failure and is reported, not worked around.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. No edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. A rejected push of the task branch: one rebase and one retry, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock: write the state into `## Result` and return BLOCKED (`task-timeout`).
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). Include the PR and squash commit, review rounds and findings, CI run and coverage, the language line, the sentences changed and checked-and-left, and follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR/commit, BLOCKED or not).

## Out of Scope

- Any change to the behaviour of `parse_report`, `judge_report`, `run_timing`, `driver_arguments`, or to `timing_driver.c` / `timing_build.py`.
- Any change to `hilclaw/harness/memory_ceiling.py`, `verification.py`, `timing_build.py`, `hilclaw/run_identity.py`, `hilclaw/run_objective.py`.
- The tool functions of `sim.run` / `board.run`, and the next run-tools contract slice (result members, timing seed).
- The optional ADR-0062 wording nits of T-0197 (document mode).
- Anything HQ-0013, 0014, 0016..0019 ask.

## Follow-ups

- (planner, document mode, §9, P1-1; candidate for the next task) The next run-tools contract slice: the result members carrying the measurement, the state or condition, the figure, the verdict and *no ceiling stated* (ADR-0061 Consequences (2), OD-13 sub-question ⑩ third clause; written to `events.ndjson`, so judge the A-13 data-plane reading first), or the timing seed (ADR-0061 Consequences (3), OD-13 sub-question ⑦).

## Result

DONE. Landed as squash commit `cd9468b` via PR #136 (branch `claude/T-0198-timing-parse-report-docstring`, deleted; commits `c3df0cc`, `494dce5`).

- **Entry checks**: no `Task: T-0198` on `origin/main`, no PR for T-0198, no open PR. No comment on issue #5 after issuecomment-6189063464; no HQ answer to name.
- **Sentence changed** (`parse_report` docstring): "it is :func:`run_timing` that reports the run as broken." became "it is :func:`judge_report` (and so :func:`run_timing`, which judges in the same way) that reports such a report as broken, ``Broken.ZERO_INTERVAL``." The opening "An ``interval_ns 0`` line is of the form here" is kept; `_judgement` is not named.
- **Checked and left** in `timing.py`: module docstring (lines 1-77), `TimingArgumentError`, `Broken` ("The condition of a completed run (decision 8) that a broken run failed first." - `Judgement.broken` now also carries it for a report without a process; still true when read as the run whose report it is, and the module docstring states that `judge_report` tests the last three only; reviewer round 2 suggested listing it here, not editing), `Report`, `Judgement`, `TimingResult`, `driver_arguments`, `judge_report`, `run_timing`.
- **Other modules** (read, not edited; still exact): `hilclaw/harness/memory_ceiling.py` line 16, `hilclaw/harness/timing_build.py` line 7, `hilclaw/harness/verification.py` line 61. No follow-up.
- **No code line changed**: diff is inside the docstring only (+2/-1 overall), only `hilclaw/harness/timing.py`; `git diff --check` clean. No test uses `__doc__`.
- **Tests**: none added (docstring only). Public functions stay covered by `tests/harness/test_timing.py`: `driver_arguments` (`test_driver_arguments_*`), `parse_report` (`test_parse_report_accepts_the_form`, `..._refuses_every_other_form`, `..._never_raises_on_bytes`), `judge_report` (`test_judge_report_*`, incl. bad arguments, non-bytes, zero interval, replay), `run_timing` (completed/broken/argument-error/figure groups).
- **Reviews**: 2 rounds, `dev-reviewer` in fresh context. Round 1 Approve with 2 optional Nits: "reports it" referred to the line, fixed in `494dce5` ("such a report"); `Broken` docstring, listed above. Round 2 Approve, one Nit (list `Broken` here), done.
- **Gates**: local `python -m pytest` 19802 passed, 354 skipped; ruff check and format check clean. CI run 38720284334 on `494dce5` green on all jobs (Python 3.11/3.14, C gate, sh gate, Test presence, Coverage gate); coverage of `hilclaw/`: lines 5282/5301 = 99.64%, functions 523/523 = 100.00%.
- **Language**: Python, as the rest of the `hilclaw` package (docstring only).
- **Follow-ups**: none from this task.
