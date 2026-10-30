---
id: T-0400
title: Add the operation's reading of a timing process container's output - the waiter's last line, the report before it, the figure by the Linux rule (ADR-0145 code slice 6; bound to no tool)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, NFR-3, NFR-4, OD-14, OD-13, "#5 A-7"]
dependsOn: [T-0399]
touchesFiles:
  - hilclaw/standin_waiter_line.py
  - tests/test_standin_waiter_line.py
estimatedSize: {loc: 90, files: 2}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5 (the first end-to-end run, `cpu_standin` x GEMM) needs the same. The owner's answer to HQ-0025 counts the memory figure among what `sim.run` / `board.run` return on `cpu_standin`. ADR-0144 put every first-case build and process in a container. ADR-0145 (landed as `a0601f4`, T-0399) then decided how the memory figure is taken there: a C program of the harness, *the waiter*, is process 1 of the timing process's container. It writes one line feed and then one last line carrying the raw `ru_maxrss`. The operation takes that last line, returns the bytes before it as the report, and converts the value by the Linux unit rule.

ADR-0145 Consequences (line 103) names two code slices. **This task is slice (6)**, "the operation's reading of the client's output — the last line, the report before it, the Linux rule — a pure function over stated bytes, testable everywhere". This is checklist work for P1-1 and P2-5, so the D18 rule for work outside the checklist does not apply. Slice (6) comes before slice (5) for two reasons:
- it is a pure function that needs no namespace-capable CI runner;
- W5 of ADR-0145 leaves the waiter line's spelling to "the code slice". The module made here fixes that spelling as the text the C waiter of slice (5) is later written against, in the same way that the `hilclaw/harness/timing.py` docstring fixes the driver's report form for `timing_driver.c`.

Planner's judgements (from `main` `7c82b14`; **the reviewer is asked to re-check each**):

- **No tool answer, situation or kind is added** (ADR-0145 decision 6). When the stream has no waiter's line, the function reports that as a plain Python fact (a return value). It does not map that fact to a kind and does not raise for it. What a call answers then is OD-18 sub-question ⑲ (ADR-0144 decision 7), and HQ-0021 and HQ-0026 are not crossed.
- **No data-plane change.** The waiter's line is "an interface between two parts of the harness of one source commit, carries no version and is no file or field of the data plane" (ADR-0145 W5). `memory_bytes` (ADR-0063 decision 6) is not touched.
- **A last line of neither waiter spelling is "no waiter's line".** ADR-0145 decision 3 reads the last line "as the waiter's" and lists three streams with no waiter's line: last line empty, no final line feed, no line feed before it. It does not name a last line whose text is of neither spelling. W5 always writes one of the two spellings, so such a line was not written by a waiter that reached W5. This planner reads that case as a fourth form of "no waiter's line", not as a waiter's line that yields no figure. The reviewer is asked to re-check this reading against ADR-0145 decisions 3 and 5. If the reviewer finds that the record decides otherwise, follow the record.
- **The unit rule reuses `hilclaw.harness.memory_ceiling.figure(raw, "linux")`.** No second copy of the ×1024 rule or of the "positive integer" rule is made (ADR-0145 decision 4; ADR-0052 decision 4). `sys.platform` is never read (ADR-0145 decision 4, "never the host's `sys.platform`").
- **Bound to nothing.** No caller is changed. ADR-0144 slice (4) will call this function. Slice (4) still waits on HQ-0021 and HQ-0026.
- **D16.** Nothing is started (no `docker`, `clang` or `claude`). The function starts no process.
- **No open PR overlaps.** PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them is touched here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (executor procedure, resume rule, the 2 h 30 min limit);
  - §5 (task format; naming: branch `claude/T-0400-<slug>`, PR title with `T-0400`, trailer `Task: T-0400`, the PR body's last line `Task: T-0400`; D4 size cap; code-task test rules ① to ⑤);
  - §3 "BLOCKED 사유".
- `CLAUDE.md` (repository), "상시 규칙":
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분" (D16);
  - "도구 계층 언어 정책" (record the language and a one-line reason in the commit body);
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md`. Read only:
  - decision 3 (lines 48-60): W5 and W6 (lines 56-57), and **"What the operation takes" (line 60), the rule this task implements**;
  - decision 4 (lines 62-66);
  - decision 5 (lines 68-71), for what the last-line rule must protect;
  - decision 6 (lines 73-77);
  - Consequences (line 103, slice (6)).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decision 8 (from line 74): the report's line forms, which the waiter's spellings must not share. Read only.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md` decision 3 (lines 49-59): (A) the report unchanged with the figure. Read only.
- `hilclaw/harness/memory_ceiling.py` (whole file; `figure` is the unit rule to reuse).
- `hilclaw/harness/timing.py`:
  - module docstring (lines 1-80): the report form, and the "C side is written against this text" convention;
  - `parse_report` (lines 193-211);
  - `_integer` (lines 343-350) and `_INTEGER`, for the digit convention.
- `hilclaw/standin_container.py` module docstring (lines 1-40): the `standin_*` module family and how it states what it does not decide.

## Acceptance Criteria

1. **New module `hilclaw/standin_waiter_line.py`** (Python). The executor may choose a clearer name and give the reason in the PR body. It holds:
   - **The waiter line's two spellings**, as module constants and stated in the module docstring as the text the C waiter of ADR-0145 slice (5) is written against. Both spellings are ASCII and ended by one LF:
     - a **value line**: a fixed keyword, one space, and the raw `ru_maxrss` written as `printf("%ld")` writes a `long` (an optional `-`, then `0` or digits that do not start with `0`);
     - a **none line**: a fixed text that says there is no value.
     The keyword is the executor's choice, for example `waiter_max_rss_kib <v>` and `waiter_max_rss none`. It must be none of the report keywords of ADR-0009 decision 8 (`resolution_ns`, `interval_ns`, `stop`). The docstring states that the value is in KiB, as the waiter writes it only where it was compiled for Linux (ADR-0145 W5).
   - **One public pure function**, for example `read(stdout)`. It takes exactly `bytes` (any other type, a `bytearray`, a `memoryview` and a `bytes` subclass included, raises `TypeError`, as `timing.judge_report` does). It returns:
     - when the stream has a waiter's line: a small result (for example a `NamedTuple`) holding `report` and `memory_bytes`.
       - `report` is the bytes before the one LF of W5 that precedes the last line, unchanged (it may be empty).
       - `memory_bytes` is `memory_ceiling.figure(int(v), "linux")` for a value line, so it is `None` for a value below 1. It is `None` for the none line.
     - when the stream has **no waiter's line**: a distinct value (for example `None`), with no report. This covers each of these streams:
       - empty;
       - not ended by LF;
       - its last line empty;
       - no LF before the last line (the whole stream is one line);
       - its last line of neither spelling, including a value line whose value is not of the `%ld` form (a leading zero, `+`, a space, a CR, non-ASCII digits).
     - The function never reads `sys.platform`, starts no process, reads no file, clock or environment variable, keeps nothing between calls and judges nothing. It does not parse or judge the report. Judging stays with `hilclaw.harness.timing` above the cut (ADR-0061 decision 3).
2. **Module docstring** states:
   - what the module is: ADR-0145 slice (6), its decision 3 "What the operation takes" and decision 4's unit rule;
   - that it is bound to no tool and no operation (ADR-0144 slice (4) will call it);
   - the spellings, as above;
   - why a figure is taken only from the last line (ADR-0145 decision 5, in one sentence);
   - what it does not decide: the answer and kind of a call with no waiter's line, a non-zero waiter status, or a failed waiter build (ADR-0145 decision 6; OD-18 ⑲; HQ-0021, HQ-0026). Also that the client's exit status is not read here: ADR-0145 decision 6 says a status is not read as the run's "before it has looked for the waiter's line", and that order is slice (4)'s.
   - The planner's reading in Why ("a last line of neither spelling is no waiter's line"), marked as the module's reading of ADR-0145 decision 3, in one sentence.
3. **Tests** in `tests/test_standin_waiter_line.py` (new):
   - **happy:**
     - a well-formed ADR-0009 report followed by LF and a value line gives that exact report and `value * 1024`;
     - the report bytes are returned byte-exact, including a report that is itself not of the ADR-0009 form (judging is not done here) and an empty report (`b"\n" + value line`).
   - **branch:**
     - the none line gives the report and `None`;
     - value `0` and a negative value (`-5`) give the report and `None` (through `memory_ceiling.figure`);
     - a very large value is converted without loss.
   - **forgery (ADR-0145 decision 5):**
     - a stream where a waiter-form line appears earlier (inside the report) and the real last line is the waiter's: the figure comes only from the last line, and the earlier line stays in the report;
     - bytes without LF left after the driver's last line, then the W5 LF and the waiter's line: those bytes stay in the report, and the last line is still read.
   - **negative / no waiter's line:**
     - empty stream; no final LF; a stream ending in `b"\n\n"`; a single value line with no LF before it;
     - a last line of another keyword (for example `stop converged`);
     - value lines with a leading zero, `+`, a trailing space, CR before LF, a tab, and non-ASCII digits;
     - each gives the "no waiter's line" value.
   - **type:** `bytearray`, `memoryview`, `str` and a `bytes` subclass each raise `TypeError`.
   - Every public function and class of the module is covered. `sys.platform` is not consulted: monkeypatching it to `"darwin"` does not change the figure.
4. `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass locally. CI is green on the PR, including the test-presence check and the `hilclaw/` coverage gate (line ≥ 80 %, function ≥ 80 %). `Result` records:
   - the language (Python) and its one-line reason;
   - the module name and the two spellings chosen;
   - the PR and the number of review rounds;
   - any follow-up.

## Out of Scope

- ADR-0145 slice (5), the C waiter (`hilclaw/harness/*.c`), and any CI workflow change.
- ADR-0144 slice (4): calling this function from any operation, `backends.py`, `tools.py`, `mcp_front.py` or `standin_container.py`; any answer or kind for a stream with no waiter's line.
- Changing `hilclaw/harness/timing.py`, `hilclaw/harness/memory_ceiling.py`, `hilclaw/local_run.py` or any docstring that ADR-0145 Consequences lists as less exact.
- Any ADR, `ARCHITECTURE/` register, data-plane file or validator.
- The three Low follow-ups of T-0399 (`prlimit` and W3-W5 allocation, the build order within B_t, the F3 summary). They are ADR-0145 text and not this slice.
- Starting `docker`, `clang` or `claude` (D16).

## Follow-ups

- After this lands: ADR-0145 slice (5), the waiter (C, W0-W6), written against this module's spellings. It is tested only inside a new Linux PID namespace on a CI runner allowed to make one. That task should first weigh T-0399 follow-ups (a) (`prlimit` against W5; no allocation in W3-W5) and (b) (the build order within B_t), because both bear on the waiter and on slice (4).

## Result

- **Outcome**: DONE. PR #233 squash-merged as `80e0b8b` (trailer `Task: T-0400`), branch deleted. CI green on all 6 jobs including the coverage gate.
- **Language**: Python — the reading is a pure function on the Python side of the cut and reuses `memory_ceiling.figure`.
- **Module**: `hilclaw/standin_waiter_line.py` — `read(stdout)` (exactly `bytes`, else `TypeError`), `WaiterRead(report, memory_bytes)`, `VALUE_KEYWORD`, `NONE_LINE`.
- **Spellings** (ASCII, each ended by one LF): value line `waiter_max_rss_kib <v>` (`<v>` as `printf("%ld")` writes it, at most 19 digits, within a 64-bit long, KiB); none line `waiter_max_rss none`. The value line gives `memory_ceiling.figure(v, "linux")`; `sys.platform` is never read.
- **No waiter's line** (`read` returns `None`): empty stream, no final LF, empty last line, no LF before the last line, or a last line of neither spelling.
- **Tests**: `tests/test_standin_waiter_line.py` (new), 74 tests, module coverage 100 %; full local pytest passed, ruff clean.
- **Review**: 2 rounds. Round 1 Approve + one Low (the `int()` `ValueError` branch depended on `int_max_str_digits`; now only values of at most 19 digits within -2**63..2**63-1 are taken). Round 2 Approve. The planner's reading (a last line of neither spelling is "no waiter's line") was confirmed against ADR-0145 decisions 3, 5 and 6.
- **Size**: 320 lines (102 module, 218 tests) against the 90 LOC estimate; the excess is mostly parametrized tests, which the cap does not count.
- **Follow-ups**: (a) for the ADR-0144 slice (4) task text: the spelling alone does not prove the waiter wrote the line — slice (4) must apply the client status of W6 (0 only when W3-W5 succeeded) before using the figure. (b) ADR-0145 slice (5), the C waiter, written against these two spellings.
