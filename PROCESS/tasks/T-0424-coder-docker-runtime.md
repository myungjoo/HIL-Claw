---
id: T-0424
title: Add the Docker runtime of the first-case coder call - a new module hilclaw/coder_runtime.py whose DockerRuntime implements the seam runtime.available() / runtime.run(scratch_root, coder_model=...) of hilclaw.coder_call as ADR-0137 decisions 2 to 7 fix it (server-version check, the docker run options, the fixed prompt, the image and token variables, removal by name, exit mapping), bound to nothing yet (ADR-0137 code slice 1; for PLAN P2-2)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-5, NFR-4, C-7, OD-23, OD-8, "PLAN P2-2"]
dependsOn: [T-0375]
touchesFiles: [hilclaw/coder_runtime.py, tests/test_coder_runtime.py]
estimatedSize: {loc: 260, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `8246fb1`):
- PLAN P2 runs in list order (D18): the round loop (P2-1 to P2-4, P2-6, P2-7), then the first run P2-5, then P2-10, then the Llama items P2-11 to P2-14.
- PLAN P2-2 (coder-driver) had its last design point, the start of the coder's container and `claude -p`, blocked on HQ-0053. The owner answered it (a) on 2026-10-23. T-0375 then landed **ADR-0137** (`a1e5c3f`). ADR-0137 Consequences names two code slices. Slice 1 is this task.
- Until a real runtime exists, every `coder.run` call ends with `no_container_runtime` (`hilclaw.coder_tool.NoContainerRuntime`, ADR-0141 decision 3). That makes the coder call, and with it P2-5, impossible on any machine. P2-5 is the near goal.
- T-0423's planner named the joining task of ADR-0153 slice 1 (P2-13) as its candidate. P2-2 comes before P2-13 in the PLAN P2 order, so this task goes first. The joining task is **not** set aside; it stays a candidate after this one.
- The runtime acceptance items of ADR-0137, (lxix) to (lxxiv), are already recorded as HQ-0068. This task closes none of them.

**This task** writes `hilclaw/coder_runtime.py`. It holds the Docker runtime with `available()` and `run(scratch_root, coder_model=...)` as ADR-0137 decisions 2 to 7 say. Nothing binds it yet: slice 2 replaces `NoContainerRuntime` in `hilclaw.tools.default_registry` and changes `hilclaw/turn_loop.py`.

**D18 reading.** This is work of a PLAN checklist item (P2-2, the code of ADR-0137). The D18 hold rule does not apply (DRIVER §6).

**D16.** No `docker` and no `claude` is started by this task or its tests. Every process start is replaced in the tests, either by a recorder patched over the start functions as seen from the module, or by a stub `docker` executable that a test writes. ADR-0137 Consequences: "tested with stub `docker` executables only". Neither form needs Docker, a logged-in `claude` or a token on the development machine.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md`:
  - Status (lines 3-15);
  - Context "Facts of the code" (lines 64-70);
  - the whole Decision (lines 72-183): decisions 1 to 7 and the Walk-through;
  - Consequences, code slices and runtime acceptance items (lines 211-220);
  - Boundaries (lines 239-253).
  Context lines 30-62 (the cited C and D facts) are for lookup only.
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md` decision 3 (lines 43-59) and decision 5 (lines 65-69).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md` decision 4 (lines 68-73) and decision 5 "Admitted names" and B1 to B6 (lines 75-95). The prompt must state these rules.
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md` decision 7 (lines 100-106).
- `hilclaw/coder_call.py`:
  - the module docstring (lines 1-50), which describes the seam;
  - `CoderNotStartedError` (lines 113-114);
  - `_run_and_bring_in` (lines 303-325), which shows how a status or that exception is read.
- `hilclaw/coder_tool.py` lines 73-120: `NoContainerRuntime` and `definition`, which requires a callable `available` and `run`.
- `hilclaw/standin_container.py` (whole file, 336 lines). It is the pattern for `docker run` with a mount, the numeric user, a random name and `rm --force` by name. Its public `check_image` (lines 257-275) is the check ADR-0137 decision 4 points to.
- `hilclaw/standin_image.py` (whole file, 66 lines). It reads an image variable and never quotes a refused value.
- `hilclaw/local_run.py` lines 79-184: `run` and `ProgramNotFoundError`. It needs a finite time limit, so it fits the version check and the removal. It does not fit `docker run` itself, which has no time limit (see criterion 4).
- `tests/test_standin_container.py` lines 1-80: the recorder pattern and the set of forbidden options.

## Acceptance Criteria

The names below are this task's. The executor may rename them only if the review asks, and records any rename in Result.

1. **Module `hilclaw/coder_runtime.py`** (Python; the language-choice line goes in Result and the commit body).
   - **Its boilerplate docstring** names ADR-0137 (decisions 2 to 7, code slice 1) and the seam of `hilclaw.coder_call`. It says that nothing binds the module yet (slice 2).
   - **It states the choices ADR-0137 leaves to the code slice**, each with its value:
     - the time limit of the version check and of the removal;
     - how "no longer exists" is told from a failed removal;
     - the status returned when the container cannot be shown gone;
     - where the coder's standard output and standard error go;
     - the prompt's wording;
     - the reaction to a platform without numeric ids.
   - **It lists what it does not do**:
     - no time limit on the call (OD-14);
     - no image pulled, built or named;
     - no token created, stored or logged;
     - no `DOCKER_HOST` or `DOCKER_CONTEXT` read or set;
     - no Podman;
     - nothing done about leftovers of a dead process (㉝ (나));
     - no output stream kept (OD-23 ① (라));
     - no data-plane file written.
   - **Public constants**:
     - `ENV_IMAGE = "HILCLAW_CODER_IMAGE"` and `ENV_TOKEN = "HILCLAW_CODER_OAUTH_TOKEN"`;
     - the container's token name `CLAUDE_CODE_OAUTH_TOKEN`;
     - `NAME_PREFIX = "hilclaw-coder-"`;
     - `CONTAINER_SCRATCH = "/scratch"`;
     - `PROMPT`;
     - the status for "not shown gone" (any fixed `int` other than 0).
2. **`class DockerRuntime`**, constructed as `DockerRuntime(*, environ=None, client="docker")`.
   - `environ` is a mapping. `None` means `os.environ`, read at each call and not copied at construction.
   - `client` is the program looked up on `PATH`.
   - A non-mapping `environ`, or a `client` that is not a non-empty `str` without NUL, raises `TypeError`/`ValueError` at construction.
   - It has the methods `available()` and `run(scratch_root, *, coder_model)`, so `hilclaw.coder_tool.definition(source, DockerRuntime())` accepts it.
3. **`available()`** (decision 2).
   - It returns `True` exactly when `<client> version --format '{{.Server.Version}}'` meets all of these:
     - it is started without a shell, with the format as one argument `{{.Server.Version}}`;
     - it exits 0 within the module's limit;
     - its standard output holds a non-empty line after stripping.
   - Every other outcome returns `False` and raises nothing: client not found, a start `OSError`, a non-zero status, empty output, a timeout.
   - It reads neither variable of criterion 1. It checks no image and no token.
4. **`run(scratch_root, *, coder_model)`**, in this order.
   - **(a) Checks before any process.**
     - Python errors (`TypeError`/`ValueError`), each naming the argument:
       - `scratch_root` is not `str`/`os.PathLike` of `str`, is not absolute, or holds a character the mount cannot carry (`,`, `"`, newline, carriage return, NUL — as `standin_container`);
       - `coder_model` is not a non-empty `str`, begins with `-`, or holds whitespace or NUL.
     - **`CoderNotStartedError` naming the variable and never quoting its value**:
       - `ENV_IMAGE` is unset, empty, or refused by `standin_container.check_image`;
       - `ENV_TOKEN` is unset, empty, holds NUL, or is exactly the unexpanded text `${HILCLAW_CODER_OAUTH_TOKEN}` (decision 5);
       - the platform has no `os.getuid`/`os.getgid`;
       - the client is not found on `PATH`.
   - **(b) Start.** One process, started without a shell, with exactly this argument vector:
     - `<client path> run --name hilclaw-coder-<hex> --rm --pull never --mount type=bind,source=<scratch absolute path>,target=/scratch --workdir /scratch --user <uid>:<gid> --entrypoint= --env HOME=/tmp --env CLAUDE_CODE_OAUTH_TOKEN --env DISABLE_UPDATES=1 --cap-drop ALL --security-opt no-new-privileges=true <image>`;
     - then `claude -p <PROMPT> --model <coder_model> --permission-mode dontAsk --allowedTools Bash,Read,Edit,Write --setting-sources project --no-session-persistence`.
     - Option order may differ only if the review asks.
     - The name's random part is new per call (for example `secrets.token_hex(16)`).
     - The child's environment is a copy of `environ` plus `CLAUDE_CODE_OAUTH_TOKEN=<token value>`. That variable overrides any existing value of the same name.
     - Standard input, standard output and standard error are not the calling process's. The MCP front uses those for its protocol. For example, all three are `subprocess.DEVNULL`.
     - **No time limit is applied** (OD-14 open). This is why `local_run.run` is not used for this start.
     - A start that raises `OSError` becomes `CoderNotStartedError`. It is chained, and its text holds no token value.
   - **(c) After `docker run` returns** with status `s`:
     - `s` in {125, 126, 127}: raise `CoderNotStartedError` with the status in its text, after the removal step below;
     - otherwise, request `<client> container rm --force <name>` with the module's removal limit;
     - if the container is shown gone by the module's documented rule, return `s` (an `int`; a negative signal status is returned as is);
     - if it is not shown gone, return the fixed "not shown gone" status even when `s` was 0 (decision 7).
     - The rule must classify the outcomes of `rm --force` as gone or not gone: exit 0, the "No such container" answer, other statuses, a timeout, and an exception of the removal. The executor fixes the rule, writes it in the docstring and tests every branch. Its premise is runtime acceptance item (lxxiii), not verified.
   - **(d) Wait cut off.** If the wait raises any `BaseException` (for example `KeyboardInterrupt`), `run` requests `rm --force` by name before the exception goes on. A failure of that removal is added to the exception as a note and does not replace it. The docker client child is not left running or unreaped.
   - **(e) No secret leaks.** The token value appears in no argument of any process, no exception text or note, and no `repr` of anything the module returns. It reaches only the `docker run` child's environment, under `CLAUDE_CODE_OAUTH_TOKEN`.
5. **`PROMPT`** (decision 6). One fixed `str`, the same for every call.
   - It tells the coder to read the spec in `spec.json` of its working directory.
   - It tells the coder to write the complete source of the kernel as whole files directly in the directory `output` of its working directory, creating that directory. It states:
     - the admitted-name rule N1/N2 in plain words;
     - flat files, no subdirectories;
     - whole files, never a diff;
     - the bounds: at most 16 files, each at most 262,144 bytes.
   - It tells the coder that it may build and try its code with the tools of the image inside its working directory.
   - It tells the coder that nothing outside `output` is kept.
   - It holds no host path, no run id, round, candidate or attempt, no model name and no credential.
   - It holds no `-` at its start, so it cannot be read as an option.
   - The bound values come from `hilclaw.bring_in.MAX_FILES` and `MAX_FILE_BYTES`, or are checked equal to them in a test.
6. **Tests `tests/test_coder_runtime.py`.** No real `docker`, no real `claude` and no network are used.
   - Process starts are replaced as seen from the module: `local_run.run` and the start used for `docker run`. Optionally, a test-written stub `docker` executable on a temporary `PATH` is used (POSIX only, skipped elsewhere with a reason).
   - Where the tested path needs `os.getuid`/`os.getgid` and the platform lacks them (native Windows), the test monkeypatches them, so the tests run on every platform. The negative test for their absence removes them.
   - The tests cover:
     - **happy**: the exact argument vector of criterion 4 (b) for a given scratch, image and model;
     - the child environment: it holds the token under `CLAUDE_CODE_OAUTH_TOKEN` and keeps the other variables of `environ`;
     - standard input, output and error not inherited;
     - the removal request by the same name;
     - the return of status 0 and of a non-zero status such as 1 or 143;
     - **forbidden options**: none of `--privileged`, `--cap-add`, `--device`, `-v`/`--volume`, `--env-file`, `--network`, `--pid`, `--ipc`, `--userns`, `-i`/`--interactive`, `-t`/`--tty`, `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, `bypassPermissions`, `--bare`, `--mcp-config`;
     - only one `--mount` and exactly three `--env`;
     - **available()**: true for exit 0 with a version line; false for client not found, `OSError`, non-zero exit, empty or whitespace-only output, and a timeout; neither variable is read;
     - **exit mapping**: 125, 126 and 127 each raise `CoderNotStartedError` with the status, and the removal was still requested;
     - **removal branches**: every branch of the documented rule, including a removal that raises, gives the documented result; "not shown gone" after status 0 returns the fixed non-zero status;
     - **wait cut off**: a `KeyboardInterrupt` from the wait leads to one `rm --force` by name and then reaches the caller; a removal failure there appears as a note;
     - **negative**: each `CoderNotStartedError` of criterion 4 (a) is raised with no process started, and its text names the variable. It never contains a sentinel token or image value. Cases: image unset, empty, `-x`, holding a space; token unset, empty, `${HILCLAW_CODER_OAUTH_TOKEN}`; client not on `PATH`; no numeric ids. Each `TypeError`/`ValueError` of criterion 4 (a) and criterion 2 is also tested;
     - **secret**: with a sentinel token, the sentinel appears in no recorded argument, no exception text or note, and no returned value;
     - **PROMPT**: it contains `spec.json` and `output` and the bound values; it contains no path separator sequence of the test's scratch path, no sentinel model name, and no `run_id`;
     - **definition**: `hilclaw.coder_tool.definition(lambda: None, DockerRuntime())` succeeds;
     - every public name of the module is used.
7. **CLAUDE.md test rules hold.**
   - Package line and function coverage stay ≥ 80%.
   - `ruff check .` and `ruff format --check .` are clean.
   - The new module has a test file.
   - Every public function and method is tested.
   - Local `pytest` passes, and CI is green before the self squash-merge.
   - DRIVER §5 naming applies: branch `claude/T-0424-<slug>`, PR title with `T-0424`, and `Task: T-0424` as the last line of the PR body.

## Out of Scope

- **Slice 2.** No edit to `hilclaw/tools.py` (`default_registry` keeps `NoContainerRuntime`), `hilclaw/turn_loop.py`, `hilclaw/coder_tool.py` or `hilclaw/coder_call.py`.
- Docstrings these files have that become less exact, for example `coder_call.py`'s "the prompt is slice (d)'s". Slice 2 updates them (ADR-0137 Consequences). Name them in Result's follow-ups; do not edit them.
- **The open points of ADR-0137 Boundaries**:
  - a time limit on the call (OD-14) and the coder's output stream (OD-23 ① (라));
  - the token record;
  - leftovers of a dead process (㉝ (나));
  - Podman and WSL (㉝ (라));
  - asking the user (㉝ (가));
  - any image, Dockerfile or registry.
  These need no new external dependency and get none.
- Any edit to `ARCHITECTURE/`, `orchestration/`, `.claude/`, `hilclaw/standin_container.py`, `hilclaw/standin_image.py`, `hilclaw/local_run.py` or `hilclaw/bring_in.py`.
- Any check that needs a real Docker daemon, a real `claude` or a token. Those are runtime acceptance items (lxix) to (lxxiv), already HQ-0068 (D16).

## Follow-ups

- **ADR-0137 code slice 2** (P2-2, code). In `hilclaw.tools.default_registry`, bind `coder.run` to `coder_runtime.DockerRuntime()` in place of `NoContainerRuntime`. In `hilclaw/turn_loop.py`, copy a non-empty `HILCLAW_CODER_IMAGE` into the server entry's `env`. Also write the reference `${HILCLAW_CODER_OAUTH_TOKEN}` there, never the value, when the turn loop's environment holds a non-empty value. Update the docstrings of `coder_call.py`, `coder_tool.py`, `tools.py` and `turn_loop.py` that call the runtime "slice (d)'s".
- The joining task of ADR-0153 slice 1 (P2-13; T-0423 Follow-ups) stays a candidate.

## Result
