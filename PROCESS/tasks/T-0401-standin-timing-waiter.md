---
id: T-0401
title: Add the waiter, the C program of the harness that is process 1 of a timing process container and reports the child's ru_maxrss on its last line (ADR-0145 code slice 5; bound to no tool)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, NFR-3, NFR-4, OD-14, OD-13, "#5 A-7", "#9"]
dependsOn: [T-0399, T-0400]
touchesFiles:
  - hilclaw/harness/timing_waiter.c
  - tests/harness/test_timing_waiter.py
  - .github/workflows/ci.yml
estimatedSize: {loc: 220, files: 3}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`. P2-5, the first end-to-end run (`cpu_standin` x GEMM), needs the same. The owner's answer to HQ-0025 counts the memory figure among what `sim.run` / `board.run` return on `cpu_standin`.

ADR-0145 (main `a0601f4`, T-0399) decided how that figure is taken inside the container of ADR-0144. A C program of the harness, *the waiter*, is process 1 of the timing process's container. It runs steps W0 to W6 and writes, after a line feed, one last line carrying the raw `ru_maxrss` of its child. Its Consequences (line 103) name two code slices:
- slice (6), the operation's reading of that line, landed as `hilclaw/standin_waiter_line.py` (T-0400, PR #233, `80e0b8b`). That module fixes the two spellings the waiter writes.
- **This task is slice (5)**, the waiter itself. It is checklist work for P1-1 and P2-5, so the D18 rule for work outside the checklist does not apply to it. ADR-0144 slice (4), which builds and starts the waiter, still waits on HQ-0021 and HQ-0026 and is not this task.

T-0400's Follow-ups asked that this task first weigh two T-0399 follow-ups (T-0399 Result, lines 100-101). Planner's weighing:
- **(a) `prlimit(2)` against W5.** A same-uid process can lower the waiter's `RLIMIT_AS` / `RLIMIT_STACK`, so ADR-0145 decision 5's "no way is known for a kernel to make W5 fail" is too strong.
  - The code half is taken here: W3 to W5 call no function that allocates memory (criterion 1). This is an implementation choice inside ADR-0145 W3-W5 and decides nothing new.
  - The ADR-text half is not needed for P2-5 or P2-14 and is returned as a D18 hold line: naming the path in decision 5 and adding it to item (liii).
- **(b) The build order within B_t.** This is ADR-0145 decision 3, "The waiter's build", and slice (4)'s code, not the waiter's source. With ordinary compile times both builds fit B_t, and the case it names is an OD-18 ⑲ situation that stays open either way. It is not needed for P2-5 or P2-14 and is returned as a D18 hold line.
- T-0400 follow-up (a), that slice (4) must apply the W6 status before using the figure, is slice (4)'s and is not done here.

Planner's judgements (from `main` `7ed103c`). **The reviewer is asked to re-check each.**

- **Spellings are fixed by `hilclaw/standin_waiter_line.py`.** There are two lines:
  - the value line `waiter_max_rss_kib <v>`, where `<v>` is the raw `ru_maxrss` as `printf("%ld")` writes a `long`;
  - the none line `waiter_max_rss none`.

  Each is ASCII, preceded by the one LF of W5 and ended by one LF. The tests check the waiter's output through `standin_waiter_line.read`, so the two sides cannot drift.
- **Off Linux.** ADR-0145 W5 writes the none line "where it was not compiled for Linux". `PR_SET_DUMPABLE` (W1) and PID namespaces (W0) are Linux interfaces.
  - This planner reads the record as follows: where the waiter is not compiled for Linux, W1 is only "establishes no signal handler", and W0 is the check that the waiter's process id is 1.
  - Reason: the protections of decision 5 exist for the figure, and off Linux there is no figure.
  - The reviewer is asked to re-check this reading against ADR-0145 decisions 3 to 5. If the record decides otherwise, follow the record.
  - The off-Linux branch is compiled but not run by CI (CI is Linux only). `Result` says so.
- **Tests run the waiter only inside a new Linux PID namespace** (ADR-0145 Consequences, "tested only inside a new Linux PID namespace … never with a container runtime on the development machine"). Each start of the waiter's executable in a test is inside such a namespace, the W0 refusal case included. That way a faulty W0 can never send `kill(-1, SIGKILL)` to the test host's processes.
  - The namespace is made with util-linux `unshare` (for example `unshare --user --map-root-user --pid --fork`) or an equivalent. No container runtime, `docker`, `podman` or `claude` is started (D16).
  - On a machine where no such namespace can be made (Windows, macOS, a restricted Linux), the tests skip. Under `GITHUB_ACTIONS=true` they fail instead of skipping, the pattern of `tests/harness/test_timing_driver.py` lines 190-197 for clang.
- **CI.** `ubuntu-latest` (24.04) may forbid unprivileged user namespaces through AppArmor (`kernel.apparmor_restrict_unprivileged_userns`). If so, `.github/workflows/ci.yml` gets one step, in each job that runs these tests, that allows them for that ephemeral runner. That is the sysctl, or a narrower means the executor finds.
  - This is code mode under CLAUDE.md A-13 and adds no external dependency: `unshare` is part of util-linux on the runner image.
  - Under CLAUDE.md test rule ⑤, no test of the workflow is added.
  - Only one case is a BLOCKED reason ("security suspicion", CLAUDE.md A-13): no means is found that avoids running the test suite as root of the runner. Then stop and report it.
- **No Python module of `hilclaw/` changes.** The waiter's source is located by path in the test, as `tests/harness/test_timing_driver.py` locates `timing_driver.c`. ADR-0144 slice (4) will copy it, build it and start it. The CI test-presence check covers `hilclaw/*.py` only; the new test file mirrors the C file's name, as `test_timing_driver.py` does.
- **No data-plane change, and no answer, situation or kind** (ADR-0145 decision 6; OD-18 ⑲; HQ-0021, HQ-0026 not crossed). The waiter's exit statuses are documented in its head comment. Nothing reads them as the run's.
- **No open PR overlaps.** PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is touched here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2 h 30 min limit);
  - §5 (task format; naming: branch `claude/T-0401-<slug>`, PR title with `T-0401`, trailer `Task: T-0401`, the PR body's last line `Task: T-0401`; D4 size cap; code-task test rules ① to ⑤);
  - §3 "BLOCKED 사유".
- `CLAUDE.md` (repository), "상시 규칙":
  - "코멘트 최소화" (the head comment of a C harness program is its external documentation, as in `timing_driver.c`);
  - "개발 드라이버와 런타임의 구분" (D16);
  - "도구 계층 언어 정책" (C; record the one-line reason in the commit body);
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙" (⑤: no test of `ci.yml`).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md`. Read only:
  - Context F5 to F9 (lines 26-30);
  - decision 3 (lines 48-60): **W0 to W6 (lines 50-57) are the behaviour this task implements**, and "Process 1" (line 58);
  - decision 4 (lines 62-66);
  - decision 5 (lines 68-71);
  - decision 6 (lines 73-77);
  - Consequences, slice (5) and items (liii) to (lv) (lines 103-104).
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md` decision 3 (lines 47-60): the waiter must build under `-std=gnu11 -O2 -ffp-contract=off`.
- `hilclaw/standin_waiter_line.py`:
  - module docstring (lines 1-52);
  - `VALUE_KEYWORD`, `NONE_LINE` (lines 59-60);
  - `WaiterRead` and `read` (from line 66).
- `hilclaw/harness/timing_driver.c`:
  - head comment and includes (lines 1-45), for the form of a harness program's head comment, its feature macro and its documented exit statuses;
  - its report-writing loop, for how a write to descriptor 1 is retried.
- `tests/harness/test_timing_driver.py`:
  - lines 1-30 (strict flags, timeouts);
  - lines 189-215 (the build fixture, `clang_build.build`, the CI fail-instead-of-skip pattern).
- `.github/workflows/ci.yml`:
  - the `python` (lines 16-46), `c` (lines 61-104) and `coverage` (from line 136) jobs: which of them run `pytest` over `tests/harness/`;
  - the C gate's per-file compile under `-std=c99 -Wall -Wextra -Wpedantic -Werror -O2`.

## Acceptance Criteria

1. **New C source `hilclaw/harness/timing_waiter.c`.** The executor may choose a clearer name and give the reason in the PR body.
   - It is one translation unit and includes only system headers (ADR-0145 decision 3). It sets its own feature macro so that `wait4` and `prctl` are declared under `-std=c99` and `-std=gnu11` (for example `_DEFAULT_SOURCE` or `_GNU_SOURCE`).
   - It compiles with no warning under:
     - the CI C gate's `-std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`;
     - ADR-0116 decision 3's `-std=gnu11 -O2 -ffp-contract=off`.
   - Command line: `<timing executable path> <argument>...`. The waiter does, in order:
     - **W0**: when its process id is not 1, it starts nothing, writes nothing on standard output and ends with a non-zero status.
     - **W1** (Linux): `prctl(PR_SET_DUMPABLE, 0)`. A failure ends the waiter at once. No signal handler is established anywhere.
     - **W2**: starts the executable as its one child, with `argv[1]` as the path and `argv[1..]` as its argument vector. Environment, working directory, standard output and standard error are handed on unchanged.
       - The executor chooses `fork`+`execve` or `posix_spawn`, and documents whether an executable that cannot be started is a W2 failure (no line) or a started child that ends non-zero (line written). Either must keep W6's "a waiter's line always means that its child was started and waited for".
     - **W3**: `wait4` on that child's pid only, never `-1`, because orphans re-parented to process 1 are also its children. Retried on `EINTR`. It keeps `ru_maxrss`. `RUSAGE_CHILDREN` is not used.
     - **W4**: `kill(-1, SIGKILL)` and reaps with `waitpid(-1, …)`, sending again while any child is left, until `ECHILD`.
     - **W5**: clears `O_NONBLOCK` on descriptor 1. It then writes `"\n"` followed by the value line (Linux) or the none line (otherwise), with `write(2)`, until every byte is written or a write fails. Partial writes are continued and `EINTR` is retried.
     - **W6**: status 0 exactly when the child exited by itself with status 0 and W3 to W5 succeeded, non-zero otherwise. A failed step ends the waiter at once and does no later step.
   - **No allocation from W3 to W5** (T-0399 follow-up (a), code half): no `malloc` and no `stdio` output. The value is formatted into a fixed buffer, for example by hand. `LONG_MIN` must be written correctly.
   - **Head comment** (the documentation of an external interface, as in `timing_driver.c`). It states:
     - what the program is (ADR-0145 decision 3, slice (5));
     - the command line;
     - W0 to W6 in one line each;
     - the two spellings, as fixed by `hilclaw/standin_waiter_line.py`;
     - the exit statuses;
     - that off Linux it writes the none line, and the planner's off-Linux reading from Why, marked as a reading;
     - that it compares nothing, is handed no bound and decides no tool answer (ADR-0145 decisions 5 and 6).
2. **Tests** in `tests/harness/test_timing_waiter.py` (new). The waiter is built with `clang_build.build` under both flag sets of criterion 1. Child programs are small C programs built the same way, or `/bin/sh` scripts. Every start of the waiter is inside a new PID namespace (Why). Each case asserts the waiter's exit status and parses its standard output with `standin_waiter_line.read`.
   - **happy:**
     - a child that writes a report-like text and exits 0: `read` returns exactly those bytes as `report`, and a positive `memory_bytes`. The waiter's status is 0.
     - a child that allocates and touches, for example, 64 MiB: its figure is at least that size and exceeds the figure of a child that does not.
   - **branch:**
     - a child that exits non-zero, and a child killed by a signal: the line is written and the status is non-zero;
     - a child that sets `O_NONBLOCK` on its standard output: the line is still written whole;
     - a child that writes a forged `waiter_max_rss_kib 1` line: `read` takes the figure from the waiter's last line, and the forged line stays in `report`;
     - a child that leaves trailing bytes without LF: they stay in `report`.
   - **W4:**
     - a child that leaves a background process (also one in a new session via `setsid`) which writes after a delay: no byte follows the waiter's line, and the namespace holds no process after the waiter ends.
     - a child that sends `SIGKILL` / `SIGTERM` to process 1: the waiter survives and writes its line (F6).
   - **negative:**
     - **W0**: the waiter started as a process other than 1 inside a new PID namespace (for example under a `sh -c '…; exit $?'` that stays process 1). It starts no child (a marker file the child would create is absent), writes nothing on standard output and ends non-zero.
     - an executable path that does not exist, and too few arguments (no executable): the documented behaviour and status.
   - The dumpable and capability properties (`/proc/1/*` unreadable to the child) depend on capabilities a `--map-root-user` namespace grants. Test them only if the executor finds a setup where they are meaningful. Otherwise `Result` names them as left to runtime acceptance item (liii) (HQ-0060).
   - Skips: the tests skip when not on Linux, when clang is missing, or when no PID namespace can be made. Under `GITHUB_ACTIONS=true` each of these fails instead.
3. **CI.** If needed, `.github/workflows/ci.yml` gets the step of Why in each job whose `pytest` collects these tests. The PR shows them run, not skipped, on CI. No test of the workflow is added (rule ⑤).
4. `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass locally (the new tests skip on this Windows machine). CI is green on the PR, including the C gate, the test-presence check and the `hilclaw/` coverage gate. `Result` records:
   - the language (C) and its one-line reason;
   - the file name;
   - the W2 start-failure choice and the exit statuses;
   - the namespace means and any CI step;
   - which (liii) properties were tested and which were left to runtime acceptance;
   - the PR and the number of review rounds;
   - any follow-up.

## Out of Scope

- ADR-0144 slice (4): copying the waiter's source, its build within B_t, starting the timing process container with it, the W6 status handling before the figure is used (T-0400 follow-up (a)), and any change to `standin_container.py`, `standin_copies.py`, `backends.py`, `tools.py`, `mcp_front.py` or `local_run.py`.
- Any change to `hilclaw/standin_waiter_line.py` (if its spelling proves wrong for C, stop and report it as a follow-up), `timing_driver.c`, `timing.py`, `timing_build.py` or `memory_ceiling.py`.
- Any ADR, `ARCHITECTURE/` register, data-plane file or validator. The ADR-text halves of T-0399 follow-ups (a) and (b) and follow-up (c) are D18 hold lines.
- Starting `docker`, `podman`, any container runtime or `claude` (D16). Running the waiter outside a new PID namespace.

## Follow-ups

- After this lands, ADR-0144 slice (4) (the `cpu_standin` operations) is code-ready for the memory figure. It still waits on HQ-0021 and HQ-0026.

## Result
