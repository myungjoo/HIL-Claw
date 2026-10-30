# ADR-0187: The output stream of a first-case coder call is kept, outside the data plane, when the runtime user names a directory for it — one log file per call, the token's value replaced, mode 0600; nothing is kept when no directory is named, and whether a run's files keep it stays open (part of OD-23 sub-question ① (라))

## Status

- **Accepted on 2026-10-30** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9: written by the owner's integrator session after the owner asked in chat on 2026-10-30 for the coder diagnostics ("Add diagnostics"), and accepted by the approval of a context-isolated reviewer. The owner has not confirmed the content of this record (§9: seven days for an objection from the owner's notice).
- **Two kinds of content.** What an accepted record or a requirement says is **cited**, with its source named. **Everything else is this record's own**: the variable, the file and its name, the replacement of the token, and every weighing.
- **Why now** (observation, an owner-requested test of 2026-10-30 under DRIVER D25): a coder call whose token had expired ended with status 1, and since the coder's output went nowhere the only thing seen was `coder_not_ended` with that status. The cause was found by hand, outside the run.
- **Answers**, for the coder call of the first case only, part of **OD-23 sub-question ① (라)**: whether the coder process's output stream is kept and where — kept, outside the data plane, when the runtime user names a directory. Whether a run's own files keep it, and notes, logs and other files of the coder, stay open (Boundaries).
- **No member, file, kind, value or version of the data plane is added or changed.** The log is a file of the runtime machine; nothing in a run's files names it, and the result of `coder.run` is unchanged (cited: ADR-0141).
- It revises the interim sentence of [ADR-0137](ADR-0137-od23-first-case-coder-process-start.md) decision 6 that the coder's standard output and error "are kept nowhere" for the case where a directory is named; with no directory named that sentence holds as written.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0137 decision 6** (cited): the coder's standard output and error "are not passed to the standard output of the process that runs the function, which the MCP front uses for its protocol (ADR-0141), and are kept nowhere — the interim behaviour until the record on the output stream". `--output-format` and `--verbose` are not used, for the same reason. The token is in the environment of every process of the container, readable to a coder with a shell (ADR-0137 decision 5, "What becomes readable inside").
- **ADR-0055 L7** (cited): "FR-6 is met only for what is taken"; a coder's notes and logs are not kept.
- **OD-23 sub-question ① (라)** (cited, OpenDecisionProposals): whether a coder call keeps anything besides the kernel files — notes, the coder's own build and test logs, the coder process's output stream — and where, with PLAN P2-2 and NFR-5.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

One first-case coder call through `hilclaw.coder_runtime.DockerRuntime` (cited: ADR-0137). The stream is the standard output and standard error of its `docker run` client, which carry those of the coder's `claude -p` and the client's own messages.

### 2. The log

- **The runtime user names a directory in the variable `HILCLAW_CODER_LOG_DIR`** of the process that runs the call. It must be an existing absolute directory, and not the data root or a directory below it when the process names its data root (`HILCLAW_DATA_REPO_LOCAL_PATH`, which `turn_loop` always gives the MCP front), compared by real path: a log there would be committed with the run (`run.commit` takes every new file below `runs/<run_id>/`). A value set but not such a directory, and a log file that cannot be made, stop the call before any process starts, as the other variables of ADR-0137 do (the failure kind `coder_not_started` of `coder.run`). Unset or empty, nothing is kept.
- **One new file per call**, `<UTC start, YYYYMMDDTHHMMSSZ>-<container name>.log`, made with mode 0600 and never over an existing file (`O_EXCL`, and `O_NOFOLLOW` where the platform has it). The standard output and the standard error of the client go together into one pipe, read by the process that runs the call, and from it into the file, in the order the client writes them. `--output-format` stays unset (ADR-0137): the file holds what the coder prints by default.
- **The token.** Every occurrence of the token's exact value is replaced by `<HILCLAW_CODER_OAUTH_TOKEN>` as the pipe is read, before anything is written; the last bytes of each read that could begin a value split across two reads are held back until the next. The value is therefore never written to the file, however the call ends, for a token that holds neither `<` nor `>` and is no part of the marker, as a `setup-token` token is (`sk-ant-oat01-` followed by letters, digits, `_` and `-`); for any other the replacement can form the value again with the bytes beside it: an end that cuts off the read loses at most the bytes held back, and a client left without its reader writes into a pipe, not into the file. Its value goes nowhere else, as before (ADR-0137 decision 5).
- **A write that fails ends the log, not the call.** The pipe is still read to its end so that the client is not blocked, and the call's status is returned as without a log.
- **The variable reaches the MCP front** as the image variables do: `turn_loop` copies a non-empty value unchanged into the server entry's environment, as it does `HILCLAW_CODER_IMAGE` (cited: ADR-0137 decision 4).
- **The nightly routine names a directory**: `<firing>/coder-output`, mode 0700, so that a failed coder call of a nightly run can be read after the firing. Its files are never put into the issue body.

**Why outside the data plane.** A file in a run's directory, or a member of a tool result, is a data-plane change, which needs the owner (CLAUDE.md A-13). The need now is a diagnosis of the runtime machine, which a file of that machine meets. **Why a named directory and no default.** A default place would keep a coder's output on every machine that runs the call, unasked; the interim of ADR-0137 stays the behaviour of a machine that names nothing. **Why replace the token.** The coder can read the token (ADR-0137), and a printed error may quote what it was given. Replacing the one value the runtime knows is exact and needs no guess at other secrets.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | A file of the attempt (`coder/…/output.log`) in the run | A data-plane change (A-13), and a run's files are committed to the data repository, where a coder's output could carry what it read. |
| 2 | A member of the `coder.run` failure result holding the last lines | A change of a tool result in `events.ndjson`, a data-plane change; and the log of a call that succeeded would still be lost. |
| 3 | The MCP front's standard error | It goes into the turn session's log, mixed with every other tool, and only where that session keeps one. |
| 4 | `--output-format json` for the cost and turns | NFR-5 asks for cost aggregation, but the format changes what the coder prints and is OD-23 ① (라) with NFR-5; not needed for the diagnosis. |

## Consequences

- A nightly firing whose coder call fails leaves the reason in `<firing>/coder-output/`, for example an expired login, next to the firing's other files.
- A machine that names no directory behaves exactly as before.
- Other secrets than the token, if a coder prints them, stay in the file, and so does any form of the token that is not its exact value (a prefix, a masked or encoded form); the file is the runtime user's, with mode 0600.
- The process that runs the call now reads the coder's output; a coder that prints without end grows the file without bound (no size bound, Boundaries).

## Boundaries (not decided here)

- Whether a run's own files keep the coder's output, notes, build and test logs (the rest of OD-23 ① (라); FR-6 and ADR-0055 L7 unchanged).
- `--output-format`, `--verbose` and the cost and token figures of a coder call (NFR-5).
- How long the logs are kept and who removes them; any size bound.
- Coder calls other than the first case's.

## References

- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0055](ADR-0055-od23-coder-output-form.md) (L7), [ADR-0137](ADR-0137-od23-first-case-coder-process-start.md) (decisions 4 to 6), [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md).
- Code: `hilclaw/coder_runtime.py` (`ENV_LOG_DIR`, `REDACTED`, `READ_SIZE`), `hilclaw/turn_loop.py`, `hilclaw/nightly.py`.
