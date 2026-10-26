---
id: T-0490
title: Build the stub `claude` and stub `docker` of PLAN P2-5's end-to-end verification and drive round 0 of a `cpu_standin` x GEMM, N=1 first-case run through the real command-line entries, with tests
phase: P2
status: IN_PROGRESS
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

## Result
