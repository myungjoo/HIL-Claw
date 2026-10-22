---
id: T-0396
title: Add the start and end of one cpu_standin build or process container behind the local_run seam (ADR-0144 code slice 1; bound to no tool)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [NFR-4, C-7, FR-10, OD-14]
dependsOn: [T-0395]
touchesFiles:
  - hilclaw/standin_container.py
  - tests/test_standin_container.py
estimatedSize: {loc: 220, files: 1}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5 (the first end-to-end run, `cpu_standin` x GEMM) needs the same. ADR-0144 (landed as `bba593f`, T-0395) decided that each of the four first-case builds and processes (verification build and process, timing build and process) runs in a new Docker container, with no fallback to the host. Its Consequences name four code slices; slices (1) to (3) "need no container runtime to test" and are "bound to nothing when they land". **This task is slice (1)**: "the start and end of one build or process container behind a seam that tests replace with a stub runtime (D16) — the properties of decision 6, the name, the forced removal at the limit, the client's status and streams handed back". This is checklist work (P1-1), so the D18 rule for work outside the checklist does not apply.

It also carries one of the three round-7 nits T-0395 left for slice (1): (b) a bind form that does not create a missing source. Nit (c) (refuse an image value `docker run` would read as an option) is carried here only as far as this function's own `image` argument goes; the reading and full check of the environment variable is slice (3). Nit (a) (how the variable reaches the turn's MCP server process) is slice (3)'s and not part of this task.

Planner's judgements (from `main` `714e08b`; **the reviewer is asked to re-check each**):

- **No new external dependency.** The function starts the container runtime's command-line program (`docker`) through the existing `hilclaw.local_run.run`, as ADR-0144 decision 3 says ("the Python standard library holds no client of a container runtime, and a library would be a new external dependency"). No Python package is added, and no image is named anywhere (ADR-0144 decision 5: "No concrete image is adopted").
- **No tool answer, kind or data-plane member.** The function is bound to no tool and no backend operation, adds no failure kind, writes no data-plane file and changes no validator. Every situation of ADR-0144 decision 7 (no runtime, no image, a container that cannot be started or removed) is reported as a plain Python fact (an exception passed on, a status, a removal result) and not mapped to any answer (decision 7: "A code slice that meets one registers it under those sub-questions rather than choosing an answer"). The client's statuses 125 to 127 are handed back unchanged and not interpreted (decision 3, "Which way a code slice reads these statuses ... is not decided here").
- **No value of an undecided item is fixed.** The time limits are the caller's (ADR-0117 is applied by slice (4), not here). The time limit of the forced removal is a required argument, not a constant of this module: ADR-0144 sets no bound for it, and slice (4) will choose it. The in-container path of the build directory, the form of the container name and the module name are slice choices ADR-0144 leaves to "the code slice".
- **D16.** No container runtime, compiler or `claude` is started on the development machine. Tests replace `hilclaw.local_run.run` with a stub (the pattern of `tests/test_selfcheck_session.py`, fixture `starts`) and assert the argument lists; no test starts `docker`.
- **No open PR overlaps.** PR #186 (T-0324, draft, BLOCKED on HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`; none is touched here. No existing module is edited.
- **Native Windows is outside C-7 ①** ("Linux, macOS and Windows with WSL"). Q6 of ADR-0144 decision 2 gives the numeric user and group id "on a POSIX host"; on a platform without `os.getuid`/`os.getgid` the function refuses before starting anything (Acceptance Criterion 6). This is a precondition of the function, not a tool answer.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2 h 30 min limit); §5 (task format; naming: branch `claude/T-0396-<slug>`, PR title with `T-0396`, trailer `Task: T-0396`, the PR body's last line `Task: T-0396`; D4 size cap; the code-task test rules ① to ⑤); §3 "BLOCKED 사유".
- `CLAUDE.md` (repository), "상시 규칙": "코멘트 최소화", "개발 드라이버와 런타임의 구분" (D16), "도구 계층 언어 정책" (record the language and one-line reason in the commit body), "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md`: Context (lines 15-40, the facts E1 to E12), Decision §2 Q2, Q4, Q6 (lines 51-63), §3 (lines 65-79), §4 (lines 80-85), §5 (lines 86-106: the bullets on the entrypoint, the image variable and the pull policy), §6 (lines 107-112, **the list this task implements**), §7 (lines 113-116), Walk-through steps 2, 3 and 5, Consequences "Slices for the planner" and runtime acceptance items (xlviii) to (lii), Boundaries "Leftovers".
- `PROCESS/tasks/T-0395-adr-od14-first-case-build-run-container.md`, section `## Result`, the bullet "Follow-ups" (round-7 nits (a) to (c)).
- `hilclaw/local_run.py` (whole file: `run`, `RunResult`, `ProgramNotFoundError`, the checks before the start and the `parameter` attribute convention).
- `tests/test_selfcheck_session.py` lines 255-290 (how a test replaces `local_run.run`).
- For the module docstring style: the head of `hilclaw/coder_call.py` (lines 1-60).

## Acceptance Criteria

1. **New module `hilclaw/standin_container.py`** (Python; the name may be changed by the executor if a clearer one fits, with `touchesFiles` reasoning in the PR body) with one public function that starts one container for one build or one process of ADR-0144 decision 1 and returns when it has ended. Its inputs are at least: the image reference (`str`), the host path of the build directory, the in-container program and its arguments, the time limit `timeout_s` of the program it starts, and the time limit of the forced removal (a required keyword argument; no default value). A keyword argument naming the client program (default `"docker"`) is allowed. The module docstring states what it is (ADR-0144 slice (1)), that it is bound to no tool and no operation, what it does not decide (decision 7's answers; the reading of 125 to 127; the memory figure, ① (마); the leftovers of Boundaries; whether the start fixes the daemon, ① (라)), and that it reads no environment variable and no configuration of its own.
2. **The one program it starts for the container is the client, through `hilclaw.local_run.run`** looked up as a module attribute at call time (so tests can replace it), with `timeout_s` as given, `env=None` (the client's own environment; no variable is handed into the container) and no `cwd` requirement on the container side. The client's argument list contains, in Docker's documented forms (ADR-0144 decision 6; another option of the same documented effect is acceptable if its effect is cited in the docstring):
   - `run` with `--rm` (E4);
   - `--name <name>` with a name made for this one call only, holding a random part from `secrets` that cannot be guessed (decision 3); two calls never share a name;
   - the build directory as **the one bind mount, writable**, in a form that **does not create a missing source** (T-0395 round-7 nit (b); for Docker, `--mount type=bind,source=...,target=...` rather than `-v`), at one fixed in-container path held as a module constant, which is also the working directory (`--workdir`);
   - `--network none` (E2); `--pull never` (E3);
   - `--user <uid>:<gid>` from `os.getuid()` and `os.getgid()` of the calling process (E6, Q6);
   - `--cap-drop ALL` and `--security-opt no-new-privileges=true` (E11);
   - the image's entrypoint overridden so that the program started inside is the given program itself (E12);
   - then the image reference, then the program and its arguments, unchanged and in order.
   It contains **none of**: `--privileged`, `--cap-add`, `-v`/`--volume`, a second mount, `-e`/`--env`/`--env-file`, `-i`/`-t`, `-p`/`--publish`, a resource bound (`--memory`, `--cpus`, `--pids-limit`, ...; Q7), a mount of the runtime's socket, or any option choosing the daemon (`-H`, `--context`).
3. **Normal end.** When the client ends within `timeout_s`, the function returns its exit status, standard output bytes, standard error bytes, the exact client argument list, the wall-clock duration and the container name, unchanged and uninterpreted — a status of 125, 126 or 127 is returned like any other — and starts no second program. The result carries **no memory figure** (the client's `max_rss` is not handed on; ADR-0144 decision 3, "The memory figure").
4. **Time limit.** When `local_run.run` reports `timed_out`, the function then starts exactly one removal of the container by its name, by force (for Docker: `rm --force <name>`, E5), through `local_run.run` with the removal time limit, and returns a result that says the program timed out (no exit status), carries what was captured, and carries the removal's outcome (its status, whether it timed out, and its output) without interpreting it. Whether the removal found a container ("no such container" when the client was ended before the container was created) is not judged (ADR-0144 decision 3 and Boundaries "Leftovers"). An exception raised by the removal start is passed on (documented in the docstring).
5. **Checks before anything is started**, each raising `TypeError` or `ValueError` with an attribute `parameter` naming the argument (the `local_run` convention), and starting no program:
   - the image: not a `str`, empty, beginning with `-` (it would be read as an option; T-0395 round-7 nit (c) as far as this argument goes), or containing whitespace or a NUL character;
   - the build directory: not `str`/`os.PathLike`, not absolute, containing a character the mount option cannot carry unambiguously (at least `,`, `"`, a newline and NUL), or (raising the `OSError` of the test, or `NotADirectoryError`) not an existing directory;
   - the program: not a `str` or empty; an argument that is not a `str`;
   - the removal time limit: not a number, or not positive and finite (the same rule `local_run` applies to `timeout_s`). `timeout_s` itself may be left to `local_run.run`'s own check, but no container may be started with an invalid removal limit.
6. **No numeric user.** On a platform where `os.getuid` or `os.getgid` is missing, the function raises before anything is started; the exception class is the executor's (document it), and the docstring says it is a precondition of the function for C-7 ① machines, not an answer of any tool.
7. **Exceptions of the client start** (`local_run.ProgramNotFoundError` when no `docker` is on `PATH`, an `OSError` of the start) are passed on unchanged, and no removal is attempted after them; the docstring says that what a tool answers for them is ADR-0144 decision 7's open question.
8. **Tests** in `tests/test_standin_container.py`, with `local_run.run` replaced by a recording stub in every test (a fixture that fails the test if the real `local_run.run` would be called); `os.getuid`/`os.getgid` monkeypatched (with `raising=False`) so the tests run on Linux CI and on a Windows development machine alike. They cover:
   - happy: the full client argument list for a build-like and a process-like call (assert every required option of criterion 2 and its value, the order image → program → arguments, and the absence of every forbidden option); the result fields of criterion 3; a status of 125 and of 127 handed back unchanged;
   - branch: no removal on a normal end; exactly one forced removal with the same name and the removal limit after a timeout, with the removal outcome in the result (removal ending 0, ending non-zero, and itself timing out); two calls get different names matching the documented form;
   - error/negative: every refusal of criterion 5 (with its `parameter` value and with the stub never called), the missing-`getuid` platform of criterion 6, `ProgramNotFoundError` and `OSError` from the stub passed on with no removal attempted;
   - every public function and class of the new module.
9. `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass locally; CI green on the PR; the `hilclaw/` coverage gate (line ≥ 80 %, function ≥ 80 %) holds. `Result` records the language (Python) and the one-line reason, the PR, the review rounds and any follow-up.

## Out of Scope

- Slice (2) (the copies of Q3 into the build directory), slice (3) (reading the environment variable that names the image, its name, its full reference check, and how it reaches a turn's MCP server process — T-0395 round-7 nit (a)), and slice (4) (the `cpu_standin` operations of `correctness.check`, `sim.run`, `board.run`). Do not wire the function into `clang_build`, `local_run`, any `check_*`/`run_*` module, `backends.py` or `tools.py`.
- Making or removing the build directory (ADR-0056 decision 4; slice (4)).
- Any tool answer, failure kind, data-plane member, journal line or validator; any reading of the statuses 125 to 127; any memory figure inside a container (ADR-0144 decision 7, decision 3, ① (마)).
- Any edit of an ADR, of `ARCHITECTURE/` registers or of the docstrings ADR-0144 lists as "less exact" (`local_run.py`, `harness/timing.py`, `harness/memory_ceiling.py`).
- Podman, rootless Docker, fixing the daemon, Docker Desktop specifics (ADR-0144 Boundaries ① (라)).
- Starting `docker`, `clang` or `claude` on the development machine (D16). Nothing about the real behaviour of Docker is verified here; that is HQ-0059 (runtime acceptance items (xlviii) to (lii)).

## Follow-ups

- After this lands: ADR-0144 slice (2) (the copies of Q3) and slice (3) (the image variable, with T-0395 round-7 nits (a) and (c)), each a small code task; then slice (4), which still waits on OD-18 ⑱/⑲ answers (HQ-0021, HQ-0026) and ① (마) for the memory figure.

## Result

