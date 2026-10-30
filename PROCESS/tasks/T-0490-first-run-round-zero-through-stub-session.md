---
id: T-0490
title: Build the stub `claude` and stub `docker` of PLAN P2-5's end-to-end verification and drive round 0 of a `cpu_standin` x GEMM, N=1 first-case run through the real command-line entries, with tests
phase: P2
status: DONE
commitMode: code
coversReq: [S0, S1, S8, FR-1, FR-17, "PLAN P2-5", "PLAN P2-1", "PLAN P2-4", D16]
dependsOn: []
touchesFiles:
  - tests/test_first_run_end_to_end.py
  - tests/first_run_stubs.py
  - hilclaw/   # only for a defect the run reveals (criterion 5); name each file in the PR body and in ## Result
estimatedSize: {loc: 60, files: 2}   # non-test lines only for defect fixes, if any; the stubs and the test are test code and outside the cap (DRIVER §5, D4/D20). The two test file names are suggestions.
hq: []
---
## Why

PLAN P2 runs its items in listed order (D18): the round loop (P2-1 to P2-4, P2-6, P2-7), then the first run (P2-5). The first-case parts of the round loop that a first run uses have landed:
- the command-line entries: `python -m hilclaw.new_run <file>` (ADR-0155) and `python -m hilclaw.turn_start <run_id>` (ADR-0122), with the turn loop (ADR-0118, ADR-0139, ADR-0141 decision 4) and the self-check before the first turn (ADR-0125);
- the Round-Manager's round 0 (ADR-0142, ADR-0138) and round >= 1 steps (ADR-0171, ADR-0172), with the technique-selector's inputs (ADR-0132, ADR-0150, ADR-0173, ADR-0174);
- the coder's container start (ADR-0137, `hilclaw/coder_runtime.py`) and the `cpu_standin` containers of `correctness.check`, `sim.run` and `board.run` (ADR-0144, ADR-0145, ADR-0168 to ADR-0170);
- the hooks of a turn session: the caller check (ADR-0146), the spend-path budget check (ADR-0147) and the `Stop` commit hook (ADR-0148).

The executors of T-0488 and T-0489 read P2-6 and P2-7 as holding no further work before P2-5. ADR-0172 says: "A whole round >= 1 through a stub `claude` is PLAN P2-5's verification." ADR-0141 decision 3 already names what that verification needs. The OD residuals that P2-1 to P2-4 still name (OD-16, OD-18 and OD-19 beyond the first case; the gate check, which waits on the owner-only OD-3) are not on the path of a first run. The planner's reading is that the round loop is complete enough for P2-5 to start. This end-to-end run is the check of that reading: any piece it shows missing is reported (criterion 5).

PLAN P2-5 requires that the driver's verification use a stub `claude` that a test writes (D16). No real `claude`, no real Docker and no API key are used or required. This task builds the stubs and drives **round 0** through the real entries. T-0491 (dependsOn this task) extends the same run to five rounds.

No ADR is planned: the task decides no runtime design. It writes test code that replays the landed definitions. Its own choices are test choices, for example the stubs' form, the shape and the parameter values of the test instance. If a step cannot be replayed without a design choice that no record makes, see criterion 5.

State at planning (`main` `9b41f48f`): no open PR, no unresolved HQ, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming, size cap, test rules, D21 pinning lists).
- `CLAUDE.md`: "개발 드라이버와 런타임의 구분" (D16), "테스트 규칙" (rule ⑤: no tests of test code; the stubs are test code), "도구 계층 언어 정책".
- `PLAN.md` P2-5 line.
- Entries and loop: `hilclaw/new_run.py` and `hilclaw/turn_start.py` (module docstrings); `hilclaw/turn_loop.py` (module docstring: the session directory, `--mcp-config`, the hook settings file, the environment); `hilclaw/selfcheck.py` (what the self-check asks of `claude`).
- Existing stub practice to reuse, not to re-invent: `tests/test_turn_start.py` lines 100-480 (the `STUB` program, the `isolated_git`, `root`, `parent`, `stub` and `only_the_stub` fixtures, and the self-check stub answering over the MCP front). Also `tests/test_selfcheck_session.py` (a stub that serves and speaks to the front), and `tests/test_backend_conformance.py` and `tests/test_coder_runtime.py` (how `docker` invocations are shaped and stubbed).
- The definitions the stub replays: `orchestration/round-manager.md` (whole; entry steps, "The round steps" for round 0, "The closing steps of a round", "The end of a session") and `orchestration/agents/coder-driver.md`, `evaluator.md`, `experiment-runner.md`.
- Records, at the decisions named:
  - ADR-0155 decisions 2-3 (the instance document);
  - ADR-0076 decision 1 (required members) and ADR-0032 / ADR-0121 decision 4 (round 0 counts; the run is over when `round` >= `round_budget`);
  - ADR-0120 decision 1 (the first-case runs);
  - ADR-0138 decision 1 (round-0 spec);
  - ADR-0142 (round-0 steps after the coder call);
  - ADR-0055 (the coder's `output/` form) and ADR-0008 (the GEMM kernel contract);
  - ADR-0137 decisions 2-7 (the coder's `docker run`; `HILCLAW_CODER_IMAGE`, `HILCLAW_CODER_OAUTH_TOKEN`);
  - ADR-0144 decisions 1-3, ADR-0145 (the waiter), ADR-0168 to ADR-0170 and `hilclaw/standin_image.py` (`HILCLAW_STANDIN_IMAGE`) for the stand-in containers;
  - ADR-0146 decisions 2-4, ADR-0147 decision 4 and ADR-0148 decision 4 (the hook settings, their inputs and exit statuses);
  - ADR-0141 decision 3 ("What P2-5's stub-`claude` verification then needs").

## Acceptance Criteria

1. **Stub `claude`** (test code; `tests/first_run_stubs.py` is a suggestion, and a helper module under `tests/` that is not itself a test file is fine). A Python program that the test writes into a `bin` directory put first on `PATH`, as `tests/test_turn_start.py` does. It handles:
   - `claude auth status` and the self-check session, as the existing stubs do. The self-check must report `passed` or `no_call` so that the first turn starts.
   - A **turn session**. It reads the prompt and the options the loop passes. It starts the server named in the `--mcp-config` file and speaks MCP to it over stdio (initialize, `tools/list`, `tools/call`). It then replays, in order, the tool requests that `orchestration/round-manager.md` and the agent definitions prescribe for the run's state. The Round-Manager's own requests come first; a delegated sub-agent's requests are made in its name (below). The replay is a script of the definitions as landed. It is not a model and makes no judgement beyond the branches the definitions state.
   - **Hooks, as a session would run them.** Before every `mcp__hilclaw__*` call, the stub runs each `PreToolUse` entry of the session directory's `.claude/settings.json` whose matcher matches. It passes the hook input the records describe (`tool_name`, `tool_input`, and `agent_id`/`agent_type` for a sub-agent call, none for the main session). On exit 2 it does not make the call and treats the line as a refusal. At the end of the main session it runs the `Stop` entry, as ADR-0148 decision 4 describes, including `stop_hook_active` on the follow-up stop. Everything the stub cannot know of a live session's hook behaviour is already runtime acceptance (RA-0030 to RA-0032); do not restate it.
   - It writes a log of every request it made, with the acting agent, and every answer, into a file the test reads.
2. **Stub `docker`**, written into the same `bin` directory. It answers `docker version` and `docker container rm --force` as `hilclaw/coder_runtime.py` and the stand-in modules expect.
   - For the **coder's container** (ADR-0137): it writes into the call's scratch `output/` the files ADR-0055 prescribes, holding a correct fp32 GEMM kernel under ADR-0008's contract. The test supplies the kernel source. No `claude` is started inside it.
   - For the **stand-in build and process containers** (ADR-0144, ADR-0145, ADR-0168 to ADR-0170): either run the command on the host with the bind-mounted build directory mapped to its host path, using a host `clang` found before `PATH` is narrowed, or answer with output the readers in `hilclaw/standin_answer.py` and `hilclaw/standin_waiter_line.py` accept. Choose per container and argue the choice in `## Result`. The correctness check must reach a real comparison against the reference wherever the host can run it. Where the waiter cannot run outside a PID namespace, the stub may give its last line from the host run's figures. Say so in `## Result`.
   - The test sets `HILCLAW_CODER_IMAGE`, `HILCLAW_CODER_OAUTH_TOKEN` and `HILCLAW_STANDIN_IMAGE` to fake values. No token is real.
3. **The round-0 run** (`tests/test_first_run_end_to_end.py` is a suggestion):
   - Use a temporary data root that is a fresh git repository (as the `root` fixture does), configured through `hilclaw.config` environment variables. Use a session parent outside both checkouts.
   - The test writes an instance document for `cpu_standin` x GEMM fp32 with `candidates_per_round` 1. Its `round_budget` makes the run over after round 0, which is `1` under ADR-0121 decision 4. Pick an `op_signature` shape the contract and the spec accept and that keeps the run short, and give every other required member a test value. Start the run with `python -m hilclaw.new_run <file>` as a child process.
   - Run `python -m hilclaw.turn_start <run_id>` as a child process with the stub `bin` first on `PATH`.
   - **Happy path, asserted**:
     - the entry's one stdout line has `outcome` `run_over` and exit status 0;
     - `runs/<run_id>/STATE.json` holds `round` 1 and `run_status` `"over"`, and parses with the package's parser;
     - round 0's spec, attempt `0000/01/01`, check results, timing result and baseline are where ADR-0004/ADR-0119/ADR-0142 place them, and each parses with the package's own reader or validator where one exists;
     - `events.ndjson` and `artifacts.json` parse;
     - the two key record files of ADR-0134 exist;
     - the data repository's history holds the turn's commit(s) and a clean tree for the run's files;
     - the stub's log shows the requests in the order of `orchestration/round-manager.md` round 0, with each sub-agent's requests under that agent;
     - every hook entry ran for every `mcp__hilclaw__*` call, and none refused one.
   - **Branch / error / negative**, each a separate test on the same infrastructure:
     - a coder container that writes no kernel (or a kernel that fails the correctness check): the run ends round 0 as ADR-0142 says for that report, and the test asserts the outcome line and the files that this leaves;
     - a sub-agent request that the caller check must refuse (for example the Round-Manager calling `mcp__hilclaw__coder_run` itself): the hook refuses it with exit 2, and the server receives no such call;
     - a turn that exits non-zero before progress: `failed_turn`, as ADR-0122 decision 5 says;
     - a stub-driven run whose `round_budget` is already reached at entry: the run goes over with no round begun (ADR-0121), if that state can be reached through the entries; otherwise say why in `## Result`.
4. **Platform and tools.**
   - Skip the end-to-end tests with a stated reason where `os.getuid` is missing (the coder runtime refuses native Windows) or where git or a needed host `clang` is missing. CI's Linux job must run them, and they must pass there.
   - Never start a real `claude` or `docker` (D16). The `only_the_stub` style guard of `tests/test_turn_start.py` that refuses any other child program should be reused or matched.
   - Keep the whole module's run time reasonable for CI (target under a few minutes). State the measured time in `## Result`.
5. **Defects the run reveals.**
   - A defect in `hilclaw/` or `orchestration/` whose fix needs no design choice: fix it in this PR. Add a unit test in that module's own test file (D12: happy/error/branch/negative, every public function of a touched module). Name each fix in the PR body.
   - A gap that needs a design choice no record makes: do not invent it (CLAUDE.md "미결은 발명하지 않는다"). Mark the affected end-to-end assertion `pytest.mark.xfail(strict=True, reason=...)` naming the gap. Land the rest, and write the gap in `## Follow-ups` for the planner. If the gap is owner-only (#5 A/B, C-6, OD-25, OD-3), return BLOCKED with a Korean question instead (DRIVER §8).
   - **Pinning lists** (D21) change only if a fix adds or removes a public name; list each change in the PR body. No other existing assertion changes unless a fix makes it wrong; state each such change and its reason in the PR body.
6. **Checks.** Run `python -m pytest`, `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%. The test-presence check holds. CI must be green before the squash-merge.
7. **Landing.** The commit body names the language and the reason in one line. The PR body ends with `Task: T-0490`. No owner notice is needed unless an ADR is written. None is planned.
8. **Result.** In `## Result`, write:
   - the stubs' form and the choice made per container (criterion 2);
   - the instance values used;
   - the asserted outcome and files;
   - any defect fixed or gap marked;
   - the module run time;
   - any runtime acceptance item that is new and not already in `PROCESS/RuntimeAcceptance.md`, for the driver to add there (not as an HQ).

## Out of Scope

- Rounds >= 1 and the five-round run (T-0491).
- Any new ADR, any change to an `ARCHITECTURE/` document, any data-plane schema change (a BLOCKED reason, CLAUDE.md A-13).
- The nightly routine (P2-10), the S6 tool (P2-8), any real `claude`, Docker or API key (D16).
- Tests of the stubs themselves (CLAUDE.md test rule ⑤).
- `.claude/settings.json`, `.claude/settings.local.json`; any new external dependency.

## Follow-ups

- (planner) T-0491 extends this run to five rounds.
- (executor T-0490, gap, not invented) `hilclaw/turn_loop.py` gives every turn session the calling process's standard output ("its standard output and standard error are those of the calling process"). A `-p` session writes its reply there, before the entry's one line, so the rule in `hilclaw/turn_start.py` that "standard output gets exactly one line" does not hold under a real session. No record says where a turn session's output should go instead (`DEVNULL`, the entry's standard error, or a file), so this is a design choice. It is marked `xfail(strict=True)` in `tests/test_first_run_end_to_end.py::test_the_entry_writes_one_line_on_standard_output`. Whatever task makes the choice removes that marker.

## Result

**DONE.** PR #304 was squash-merged as `ee870edd` after 1 review round, with an Approve and three nits that concerned only this Result. CI was green on every job. Files: `tests/first_run_stubs.py` and `tests/test_first_run_end_to_end.py`, both new test code. Nothing in `hilclaw/` or `orchestration/` changed, no pinning list changed and no existing assertion changed. Language: Python, the language of the existing suite and of the stubs it already writes.

**Stubs.**
- **Form.** `tests/first_run_stubs.py` is a helper module, not a test file. `install()` writes three POSIX launchers into a `bin` directory that is the only entry on `PATH`:
  - `claude` and `docker` exec this module as a program, together with the scenario file;
  - `git` execs the machine's git.
- **Stub `claude`, login and self-check.** It answers `auth status` and the self-check session the way the stub in `tests/test_turn_start.py` does. The check reports `passed`.
- **Stub `claude`, turn session.**
  - It starts the server in the `--mcp-config` file, expanding `${...}` from its own environment, and speaks MCP over stdio.
  - It replays the requests of `orchestration/round-manager.md` and of `coder-driver`, `evaluator` and `experiment-runner` for round 0: the entry steps, the round-0 steps, the closing steps, the end of a session and the stops.
  - Each delegation acts with its own `agent_id` and `agent_type`. The Round-Manager's own calls carry neither.
  - Before every `mcp__hilclaw__*` request it runs each matching `PreToolUse` entry of the session's `.claude/settings.json`. An exact-list matcher is matched by name and any other matcher as a regular expression. The hook gets `CLAUDE_PROJECT_DIR` and the input the records describe. Exit 2, or a failure under `onFailure: block`, refuses the call, and a refused call is never sent to the server.
  - At the end of the main session it runs `Stop` with `stop_hook_active` false. If that stop is refused it calls `run_commit` once and stops again with `true`.
  - Every request, hook status, answer and report goes to an ndjson log.
  - Like a real `-p` session, it writes its last reply to standard output.
  - Rounds >= 1 are not replayed; that is T-0491.
- **Stub `docker`.** It answers `version` and both forced removals.
  - **Coder container** (`/scratch` mount): it writes the test's kernel into `output/`, and starts nothing. It also logs that `CLAUDE_CODE_OAUTH_TOKEN` reached it.
  - **Build containers** (verification, timing and waiter builds): it runs the host `clang`, found before `PATH` was narrowed, with `/build` mapped to the bind-mounted host directory. These are real compiles.
  - **Verification process container:** it runs the built executable on the host with the mapped arguments. The correctness check is therefore a real comparison against the reference at both points.
  - **Timing process container:** where `unshare --user --pid --fork --mount-proc --kill-child` works, it runs the real waiter as PID 1 of a new namespace. That works on WSL2 and on CI's Linux runners, which already allow it for `tests/harness/test_timing_waiter.py`. Otherwise it runs the timing executable directly and writes the waiter's last line from the host's `RUSAGE_CHILDREN` figure. That fallback passed in a local run with `unshare` forced off, but no CI job takes it.
  - It never runs the waiter on the host: W0 refuses that, and W4's `kill(-1, SIGKILL)` would be unsafe there.

**Instance values (test values).**
- `hw_profile`: `cpu_standin`, revision `stub-revision`.
- `op_signature`: GEMM fp32 row_major, shape m=8, k=16, n=8.
- `objective`: `latency_minimisation`.
- `candidates_per_round` 1, `n_max` 6, `draws` 1, tolerance `rtol` 1e-4 / `atol` 1e-5, `round_budget` 1.
- `coder_model`: the default that `new_run` adds.
- Environment: the fake values `HILCLAW_CODER_IMAGE=stub.invalid/coder:fake`, `HILCLAW_CODER_OAUTH_TOKEN=fake-token-not-a-real-one` and `HILCLAW_STANDIN_IMAGE=stub.invalid/standin:fake`.
- Setup: the data root is a fresh git repository named through the `HILCLAW_DATA_REPO_*` variables. `TMPDIR` is a session parent outside both checkouts.

**What the tests assert.**
- **Happy path.**
  - `python -m hilclaw.turn_start` exits 0 and its last line has `outcome` `run_over`, with a `passed` check.
  - `STATE.json` holds round 1 and `run_status` `"over"`, and parses with both `run_state.parse` and `run_file_tools.read`.
  - The spec is at `rounds/0000/coder/candidates/01/attempts/01/spec.json` and passes `spec_file.parse` and `spec.validate`. `output/gemm.c` is the kernel.
  - `events.ndjson` passes `events.read` and `events.validate`. It holds the step lines of `correctness_check_sim`, `correctness_check_board` and `board_run_timing` for `0000/01/01`.
  - Both checks `pass`, by `checks_tool.checks_of`, and stand `verified`, by `check_standing.standing`.
  - The board timing result is the baseline of ADR-0119 decision 2. `timings_tool.timing_problem` admits it, and its outcome is `converged` or `not_converged`.
  - The three build logs are under `measure/`.
  - The key records under `db/` load with `key_records`.
  - Git history holds two `run.commit` commits, one from entry step 0 and one from closing step 3. The tree is clean and `commit_owed` is false.
  - The stub log shows the exact request order of round 0, each sub-agent's requests under its own agent, both hook entries on every spending call and the caller entry on every other call, all exiting 0, and one passing `Stop`.
  - The docker log shows the container sequence, the fake images and that the token reached the coder container.
- **Not written by round 0**, asserted absent:
  - `artifacts.json`: no round-0 step pushes a blob, and only `blob.push` writes the file (ADR-0005).
  - `eval/` and `decision/`: round 0 writes no verdicts and no hypotheses (ADR-0142 decision 6).
  - Check and timing result files: ADR-0011, ADR-0062 and ADR-0131 put those results in `events.ndjson`, not in result files.
- **Branch and negative cases.**
  - **No kernel / wrong kernel:** turn 1 stops after `coder_run` (empty `taken`) or after a `fail` sim check (`not_verified`), and calls `run_commit`. Turn 2 meets `spec_exists` and stops. The outcome is `unchanged_turn` (12), with STATE round 0, the spec kept and a clean tree.
  - **Round-Manager calls `coder_run` itself:** the caller check exits 2 and the budget check exits 0. The call is never sent, only the coder-driver's container ever starts, and the run still ends `run_over`.
  - **Turn exits 3 before progress:** `failed_turn` with `exit_status` 3. Only `instance.json` exists, and no request or container was made.
  - **Round budget reached at entry:** the run goes over with no round begun. This state cannot be reached through the entries alone: `round_budget` is at least 1 (ADR-0032 decision 3), and `round.end` writes `run_status` in the same write that reaches the budget (ADR-0135 decision 4). The test therefore writes STATE round 1 with the package's `run_state_file.replace` after `new_run`. The turn then runs entry step 6, writing `"over"` with `state.write`, and the outcome is `run_over`, with no `key.store`, no `db/`, no `rounds/` and no container.

**Defects and gaps.** No defect was fixed. One gap is marked xfail(strict): the turn session's standard output (see Follow-ups).

**Run time.**
- This module: about 16 s locally (WSL2 Ubuntu, Python 3.12; 6 passed, 1 xfailed).
- On CI the module ran and was not skipped (the job's summary shows the 1 xfail). CI's Python gate (3.11) took 7 m 44 s for the whole suite.
- Native Windows skips the module at import, since it has no `os.getuid`; the full Windows suite passed.

**Runtime acceptance items:** none new. The hook behaviour the stub assumes is already covered by RA-0030 to RA-0032. A real `-p` session writing its reply to standard output is not an open runtime fact; it is the gap in Follow-ups.

**nextTask candidate:** T-0491.
