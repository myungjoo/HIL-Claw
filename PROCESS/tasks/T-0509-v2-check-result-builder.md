---
id: T-0509
title: Land ADR-0183 code slice 1 — the v2 result builder of correctness.check for every contract of the table, and the sdpa judge's cache differences per allocation (no tool path changes)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-1, OD-8, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/check_result.py
  - hilclaw/harness/bf16_sdpa_kv_cache_verification.py
  - hilclaw/check_judging.py
  - tests/test_check_result.py
  - tests/harness/test_bf16_sdpa_kv_cache_verification.py
  - tests/test_check_judging.py
estimatedSize: {loc: 250, files: 3}   # non-test lines; check_judging.py only if the slice puts the per-operand mapping there (ADR-0183 decision 9 item 1: "2 to 3 files"); tests excluded from the cap
hq: []
---
## Why

**State.** ADR-0183 (T-0508, `main` `8b6c7318`) records the owner's answer to HQ-0078: one result format v2 for `correctness.check`, `sim.run` and `board.run`, under four new `step` values with the six values of today retired. Its decision 9 lists the code slices in landing order. This task is **item 1**: "**The v2 check result builder** — `hilclaw/check_result.py` gains the builder of a v2 result for every contract of the table (`contract_key`, `shape` from the covering entry and the dimensions, `draws`, `tolerance`, `counts` per output operand with the entry form of its judging, the outcome over all operands; the bounds of decision 3), and the judging of each operand where the slice puts it; `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` returns the cache differences per allocation, the present result keeping their sum until slice 2. **No tool path changes; no result written under any value changes.** About 250 lines, 2 to 3 files."

**Why P2-14 needs it (PLAN checklist, D18 does not apply).** PLAN P2-14 needs every bf16 contract `timed`; ADR-0181's bf16 timing slices wait behind the v2 code of both tools (owner order, HQ-0078; ADR-0183 decision 9 item 4). This slice is the first of that code. P2-11 and P2-14 are PLAN checklist items. P2-10 waits on HQ-0076 (T-0493).

**Task unit (D20).** No ADR is written: ADR-0183 decides this slice. The slice is under half the size cap, but it cannot be merged with item 2 (ADR-0183 decision 9 sizes item 2 at "10 to 12 files" alone) or with item 3 (8 files; together over 10 files), so it stands alone. T-0510 (item 2) and T-0511 (item 3) are planned in the same batch and depend on this task.

**RuntimeAcceptance.** `PROCESS/RuntimeAcceptance.md` has no `실패` item as of `main` `ac8e143c`. ADR-0183 Consequences: "Runtime acceptance items: none."

**D16.** Pure Python on in-memory values and existing harness reports; no `claude`, no container runtime, no board.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0509-<slug>`, `Task: T-0509` trailer in commits and as the last line of the PR body, size cap, test rules D12, D21 list-assertion rule), §8 (runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, D22).
- `CLAUDE.md` (rules; A-13 code mode and BLOCKED reasons; test rules; language policy; comment minimisation).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` — Context table of output operands (lines 22-34), decision 1 (lines 38-42), decision 3 (lines 59-80), decision 5 examples (lines 107-119), decision 6 (lines 121-125), decision 9 (lines 152-161), A-13 reading (lines 163-175).
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md` decisions 5 and 8 (lines 61-68, 82-89): the cache allocations of l + 2m rows and the comparison.
- `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` decisions 1 to 5 (form rules, `counts` per draw, bounds).
- `hilclaw/check_result.py` (whole file, 327 lines) — today's builders, their checks and error style.
- `hilclaw/contract_table.py` (whole file, 148 lines) — `Entry`, `TABLE`, `entry`, `task_contract`.
- One contract module for the operand list form: `hilclaw/sdpa_kv_cache_bf16_contract.py` (`task_contract`, operand `role`s) and `hilclaw/gemm_contract.py` (`task_contract`).
- `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` lines 85-112 (`DrawCounts`) and 234-283 (`_judgement`, `_counts`).
- `hilclaw/check_judging.py` (whole file, 278 lines) — how a `Judgement` of each harness becomes a result today.
- `hilclaw/harness/verification_arrays.py` lines 70-80 (`Counts`).
- `tests/test_check_result.py` lines 580-600 (`test_public_names_of_the_module`); `tests/harness/test_bf16_sdpa_kv_cache_verification.py` lines 226-260 (public names, `test_draw_counts_fields`); `tests/test_check_judging.py` lines 630-660 (public names).

## Acceptance Criteria

1. **The v2 builder(s) in `hilclaw/check_result.py`.** New public function(s) — names and exact signatures are this slice's (state them in the module docstring) — build a v2 result of `correctness.check` (ADR-0183 decision 3) for **any entry of `contract_table.TABLE`**, given the covering entry (or its table key), the dimensions in the order of the contract's `task_contract` parameters, `draws`, `rtol`, `atol` and, for a completed run, the per-operand per-draw counts; and a broken v2 result given the `condition` and the same values but counts (ADR-0183 decision 6). The result:
   - has exactly the members of decision 3, in its table order (`outcome`, `condition`, `contract_key`, `shape`, `draws`, `tolerance`, `counts`), a member that does not apply left out, no `None`;
   - `contract_key` is a new `dict` with exactly `kind`, `dtype`, `layout` from the entry's contract (`KIND`, `DTYPE`, `LAYOUT`), no `language`;
   - `shape` pairs the `task_contract` parameter names with the dimensions, each exactly an `int` ≥ 1 (and the `rope` even-`d` rule that `bf16_completed` applies today kept for `rope`);
   - `counts` has exactly one member per operand of `task_contract(*dims)` whose role is `output` or `inout`, named by the operand's name, each a list of `draws` entries; an entry of an operand judged bit-exact is `{"differs": n}`, of any other `{"failed": n, "non_finite": n}`. **Bit-exact today: exactly `cache_k` and `cache_v` of the bf16 `sdpa_kv_cache` contract** (ADR-0183 decision 3); hold this as one constant of the module, keyed so that no other contract's operand is bit-exact;
   - bounds of decision 3: `non_finite` ≤ `failed` ≤ the number of elements of the operand (the product of its `shape` in the `task_contract` object); `differs` ≤ (l + 2m)·h_kv·d for the two caches (ADR-0165 decisions 5 and 8);
   - `outcome` is `"pass"` iff every `failed` and every `differs` of every draw is 0, else `"fail"`; a broken result has `"broken"`, a `condition` of `CONDITIONS`, and no `counts`.
   Arguments not admitted are refused as the module refuses today (`TypeError` / `ValueError`, message starting with the parameter name, nothing returned). An entry that is not a `contract_table.Entry` of `TABLE` (or a key not in `TABLE`) is refused. The builder judges nothing and reads no file.
2. **The judging of each operand** (ADR-0183 decision 9 item 1, "where the slice puts it"): the mapping from a harness `Judgement` of each of the four judges (fp32 `hilclaw.harness.verification`, `bf16_verification`, `bf16_rope_verification`, `bf16_sdpa_kv_cache_verification`) to the per-operand counts of the v2 builder exists after this task, in `check_result.py` or as new function(s) of `hilclaw/check_judging.py`, so that slice 2 only switches callers. It is not called by any tool path in this task.
3. **Per-allocation cache differences.** `hilclaw.harness.bf16_sdpa_kv_cache_verification.DrawCounts` holds the differences of `cache_k` and of `cache_v` as two fields (names this slice's), each counted over its allocation of l + 2m rows, guard rows included, as `_counts` counts them today; the verdict is unchanged (fail iff some `failed` or some difference is 1 or more). The docstring of `DrawCounts` says so.
4. **No result written under any value changes.** `completed`, `broken`, `bf16_completed`, `bf16_broken` and the existing functions of `check_judging.py` return exactly what they return today for every input they accept today; in particular an `sdpa_kv_cache` result under today's builders keeps one `cache_differs` per draw equal to the **sum** of the two allocation counts. Where the sum is formed (in `bf16_completed`, or in the existing bf16 path of `check_judging`) is this slice's; state it in the docstring. No change to `check_tool.py`, `check_identity.py`, `check_answer.py`, `check_operation.py`, `layout.py` or any reader.
5. **Tests** (D12: happy, error, branch and negative cases; every public function of the touched modules covered; coverage ≥ 80 % line and function):
   - the v2 builder for each of the seven entries of `TABLE`: `contract_key`, `shape` member names and order, `counts` member names (`c`; `c`; `y`; `c`; `out`; `out`; `cache_k`, `cache_v`, `out`) and entry forms; the three check-result lines of ADR-0183 decision 5 (the first three) reproduced exactly (as `dict`s);
   - pass/fail branches: all zero → pass; one `failed` → fail; one `differs` with all `failed` 0 → fail (ADR-0183 decision 5 second line); broken results for each condition with no `counts`;
   - negative: wrong entry or key, wrong dims arity/type, `rope` odd `d`, counts missing an operand / extra operand / wrong entry form for the operand / wrong number of draws / bound exceeded (`failed` over the operand size, `non_finite` over `failed`, `differs` over (l + 2m)·h_kv·d) / non-`int` or negative values / bad `condition` / bad tolerance;
   - the per-operand mapping of criterion 2 for a `Judgement` of each harness;
   - `DrawCounts`: an sdpa report whose `cache_k` differs in k elements and `cache_v` in v elements gives the two fields k and v; today's result keeps `cache_differs == k + v`.
6. **Existing tests.** No existing assertion changes except: list assertions this task's added or changed names touch (D21) — expected: `tests/test_check_result.py::test_public_names_of_the_module` (gains the new builder names), `tests/harness/test_bf16_sdpa_kv_cache_verification.py::test_draw_counts_fields` (the two per-allocation fields), and `tests/test_check_judging.py::test_public_names_of_the_module_and_no_default` if functions are added there; and tests that construct a `DrawCounts` or an sdpa counts entry of `bf16_completed` positionally with three items, which follow the new arity **without changing any asserted result**. List every edited assertion in the PR body.
7. **No record edits.** No file under `ARCHITECTURE/` changes (`StepValues.md` already holds ADR-0183's rows). Docstrings of `check_result.py` and the sdpa harness describe what is now true. Sentences of records that become less exact are listed in Result, not edited.
8. **Result** records the language (Python, the language of the touched layer-2 modules) and the reason, the names and signatures of the new public functions (T-0510 calls them), where the sdpa sum is formed, the edited list assertions, and any runtime acceptance item (none expected).

## Out of Scope

- Any change of the tool path or of a `step` value (T-0510, ADR-0183 decision 9 item 2); `sim.run` / `board.run` (T-0511, item 3).
- Removing today's builders (T-0510).
- ADR-0181's bf16 timing slices (after T-0510 and T-0511).
- Any tolerance, seed, number of draws, unit beyond `ns` or other owner-only value (ADR-0183 Boundaries).
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
