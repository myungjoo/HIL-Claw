---
id: T-0513
title: Land ADR-0181 code slice 2 — bf16 timing programs of rope (freqs_cis rows on standard input at ADR-0180's start position) and sdpa_kv_cache (one l-row allocation per cache, nothing reset between repeats), added to the T-0512 Python side
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-2, NFR-3, OD-13, OD-16, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0512]
touchesFiles:
  - hilclaw/harness/          # two new bf16 timing programs; the T-0512 Python build/run modules extended to the two kinds
  - tests/harness/
estimatedSize: {loc: 330, files: 4}   # rope ~110, sdpa_kv_cache ~130, Python ~60-90; tests excluded from the cap
hq: []
---
## Why

**State.** This task is **ADR-0181 decision 8 item 2**: "The `rope` and `sdpa_kv_cache` timing programs (decision 2), with the `rope` rows on standard input." It builds on T-0512, which is item 1. That task adds the shared bf16 timing header, the four programs of the ADR-0163 kinds and the Python build, argument and run functions; its `## Result` names them. The order follows ADR-0183 decision 9 item 4. ADR-0181 decision 8 allows slices 1 and 2 to be one task when they fit the size cap together. They do not fit, because the six programs and the header come to about 870 lines, so they are two tasks.

**Why now (PLAN checklist, D24 ⑤).** The D24 freeze was released on 2026-10-30. After the release, P2-11 to P2-14 first get a real run with the minimal operation set: the six instance kinds of ADR-0152 decision 2, which include `rope` and `sdpa_kv_cache`. Starting an instance of a bf16 kind needs that kind's entry to be `timed` (ADR-0177 decision 2), and slice 4 sets those flags after this slice. These are checklist items, so D18 does not apply. This task is planned in one batch with T-0512 and T-0514 (D20 ④).

**RuntimeAcceptance.** No item has the status `실패` as of `main` `b7e65818`. RA-0054 (the `rope` rows reach the timing program through the waiter) already exists. This slice adds no item.

**D16.** Tests build with the local `clang`, where present, and run with stub kernels. They do not use `claude`, Docker, a board or real weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5. These cover the branch name `claude/T-0513-<slug>`, the `Task: T-0513` trailer in commits and as the last line of the PR body, the size cap, D12 and D21. Also read §8 (D22).
- `CLAUDE.md`: the A-13 code mode, the BLOCKED reasons, the test rules, the language policy and comment minimisation.
- `PROCESS/tasks/T-0512-bf16-timing-programs-four-kinds.md`, in particular its `## Result`. It gives the file names, the header factoring and the public Python names this task extends.
- `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`. Read decision 2 (lines 30-38), especially the `rope` bullet (line 36) and the `sdpa_kv_cache` bullet (line 37). Also read decision 8 (87-95) and Alternatives (109-120), on fixed P and on the cache reset.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`. Read decision 3 (lines 45-51) on how the rows reach the program, decision 5 (60-64) on the table, decision 6 (65-69) on the drawn `x`, and decision 7 (70-77) on the command line.
- `ARCHITECTURE/decisions/ADR-0180-od16-bf16-rope-check-start-position.md` decision 1 (lines 27-36), the start position rule.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`. Read decision 3 (lines 46-53), which covers the command line and P = l − m, and decision 4 (54-60), which covers the drawn inputs, including cache rows 0 … P − 1.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`, decisions 5 to 9 (lines 50-110).
- Code:
  - `hilclaw/harness/bf16_verification_rope.c` (140 lines) and `hilclaw/harness/bf16_verification_sdpa_kv_cache.c` (179): the prototypes, the stdin reading and its status, the draws and the dimension rules.
  - `hilclaw/harness/bf16_rope_verification.py`, mainly `program_arguments`, `start_position` and `run_bf16_rope_verification`, which builds rows with `bf16_rope_arrays.table_rows` and passes them as `stdin_data`.
  - `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`, mainly `program_arguments`.
  - `hilclaw/harness/bf16_rope_arrays.py`, mainly `table_rows`.
  - the T-0512 header, programs and Python modules.
  - `hilclaw/local_run.py`, mainly `run(..., stdin_data=...)`.
- Tests to mirror: `tests/harness/test_bf16_verification_rope.py`, `tests/harness/test_bf16_verification_sdpa_kv_cache.py` and the T-0512 tests.

## Acceptance Criteria

1. **Two programs** under `hilclaw/harness/`. They use the shared header of T-0512, and each holds exactly one call site: `hilclaw_rope_bf16` or `hilclaw_sdpa_kv_cache_bf16`. Each prototype is byte for byte that of the kind's verification program. ADR-0009's clock, loop, untimed call, report form and exit statuses are kept, as in T-0512 criterion 2.
2. **Command lines** (ADR-0181 decision 2). The dimensions come in `task_contract` order: `m h d` for `rope` and `m l h h_kv d` for `sdpa_kv_cache`. Then come `n_min n_max cv_max sample_form seed`. The kind's rules between dimensions apply: `d` is even for `rope`; for `sdpa_kv_cache`, `l` ≥ `m` and `h` is a multiple of `h_kv`. A breach of a rule is refused with status 2, as the verification programs refuse it.
3. **`rope`.**
   - The program reads exactly 4·m·d bytes of `freqs_cis` rows on standard input before the untimed call, as `bf16_verification_rope.c` does. It copies them once into the kernel's array.
   - Short, longer or unreadable input ends the program with a non-zero status of its own. That status is documented in the program header and differs from statuses 2 to 5.
   - `x` is drawn once with the timing seed and draw 0, as the verification program draws it.
   - On the Python side, the run function for `rope` computes P with `bf16_rope_verification.start_position(dims, seed=seed)`, which is ADR-0180 decision 1's rule: P = 0 when m ≥ 2; when m = 1, P = 127 for an even seed and 2047 for an odd one. It builds the rows with `bf16_rope_arrays.table_rows(dims, start=P)` and hands their bytes as `stdin_data`.
   - No other kind gets standard input.
   - The run function judges the report as in T-0512, through `hilclaw.harness.timing`, which is unchanged.
4. **`sdpa_kv_cache`.**
   - Each cache is one allocation of exactly l rows, with no guard rows.
   - Rows 0 … P − 1 (P = l − m) are drawn once, from the timing seed with draw 0, as ADR-0165 decision 4 draws them. Rows P … l − 1 are not initialised.
   - `q`, `k_new` and `v_new` are drawn once.
   - Nothing is reset between repeats.
5. **Python side.** The T-0512 build, argument and run functions accept the two kinds, and their docstrings say so. Dims are refused by the kind's rules before anything is started. If the module the run tools will import stays free of NumPy, the `rope` row building that needs NumPy is kept where the existing tests allow. State the choice in the Result. Slice 4's run path imports the module, and `hilclaw.run_tool`'s pin that `hilclaw.harness.timing` imports no NumPy must stay true.
6. **No tool path changes**, as in T-0512 criterion 6. `hilclaw/harness/timing.py`, `timing_driver.c` and every verification program and header stay unchanged.
7. **C gate.** Both new `.c` files compile under `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.
8. **Tests.** They follow D12: happy, error, branch and negative cases, every public function touched, and coverage of at least 80 % for lines and for functions. Tests that need `clang` or POSIX are skipped where it is absent.
   - `rope`:
     - a stub kernel receives exactly the rows `table_rows` gives for P from the seed, for m = 1 with an even seed, m = 1 with an odd seed, and m ≥ 2;
     - it receives the drawn `x`;
     - the report judges completed;
     - the program refuses short input, longer input and an odd `d`.
   - `sdpa_kv_cache`:
     - a stub kernel sees rows 0 … P − 1 of both caches equal to the drawn ones at every call;
     - its writes to rows P … l − 1 persist between calls, so nothing is reset;
     - the report judges completed;
     - the program refuses `l < m`, an `h` that is not a multiple of `h_kv`, and wrong counts and spellings.
   - Python negative cases: dims of the wrong length for each kind, an odd `d`, `l < m`, and an `h` that is not a multiple of `h_kv`.
9. **Existing tests.** No existing assertion changes, except a list assertion that pins kind lists or public names of the T-0512 modules, if one exists (D21). That includes a test asserting that `rope` and `sdpa_kv_cache` are refused, which this task reverses by design. List each such edit in the PR body.
10. **No record edits.** No file under `ARCHITECTURE/` changes.
11. **Result** records:
    - the language (C and Python) and the reason;
    - the files;
    - the `rope` input status value;
    - where the NumPy import sits;
    - the edited assertions;
    - runtime acceptance items (none expected);
    - the next candidate, T-0514.

## Out of Scope

- Run-tool admission and per-kind parameters (T-0514).
- The `cpu_standin` operation, the limits, rows through the container client, the header copies and the `timed` flags (slice 4).
- Defending against a kernel that changes cache rows 0 … P − 1. The check catches that, not the timing run (ADR-0181 decision 2).
- Owner-only values. fp16. OpenMP.
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
