---
id: T-0446
title: Add hilclaw/rope_table.py - the host-side builder of the RoPE frequency table of ADR-0161 decision 4 (the scaled frequencies g(i) and the cos/sin table with correctly rounded binary32 entries, every constant an input with no default) with tests (ADR-0161 code slice, second part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0444, T-0445]
touchesFiles: [hilclaw/rope_table.py, tests/test_rope_table.py]
estimatedSize: {loc: 220, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `d0bac75`):
- ADR-0161 (T-0444, landed as `7c8c5c6`) defines the bf16 RoPE contract on `cpu_standin`. T-0445 (PR #262, `849fffa`) landed part 1 of its code slice: the kind `rope` in `hilclaw.keys` and `hilclaw/rope_bf16_contract.py`.
- ADR-0161 decision 4 puts the cos/sin table **outside the kernels**: the host side builds it once per generation from the model parameters `head_dim`, `rope_theta` and the four scaling constants, and passes its rows to every RoPE call as the operand `freqs_cis` (decisions 6 and 10). Each entry must be the binary32 value nearest to the exact cos or sin of the exact angle, ties to even.
- ADR-0161 Consequences (line 189) list "a table builder on the host side (decision 4) with tests against the rule, which carry what decision 13 leaves undetected" as the next part of the slice. Decision 13 says a wrong `rope_theta`, a missing or wrong scaling and a wrong position are **not** detected by the kernel's verification; they are errors of the table builder, for its own tests.
- No code builds this table today.

**This task is part 2 of that slice**: the builder and its tests. The RoPE binding check in `hilclaw/model_binding.py` (call sites `rope_q`, `rope_k`) is the next part and is not done here.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json` (HQ-0021, HQ-0048, HQ-0024; the gate half of P2-4 is owner-only, OD-3), and P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. The table is an operand of every RoPE call of a forward pass (ADR-0161 decisions 2 and 10), so the model executor of P2-13 and the end-to-end of P2-14 need it, and the P2-12 harness needs its rows as the `freqs_cis` value set (decision 13). It is not a follow-up, wording or hardening item; the D18 rule does not set it aside.

**§9, HQ-0070, A-13 and D16.**
- No open decision is needed. The rule, the precision and the shape of the table are ADR-0161 decision 4 and decision 6 as accepted. Decision 4 says "The method is the builder's", so the evaluation method is this task's implementation choice (criterion 3).
- **HQ-0070** (the scale factor of Llama 3.2 1B: 8 in Meta's code, 32 in Hugging Face's converter) is open. It blocks "the table builder's Llama constants", not the builder: the HQ text says the code slice is not blocked. So the builder takes **every constant as a required input with no default**, and this module holds no Llama 3.2 1B value (criterion 2). The tests may use Meta's constants (s = 8) as test data, because decision 13 fixes the verification table with s = 8 whatever the answer.
- No data-plane file, schema or version is touched; the module writes no file. Not an A-13 schema change.
- `numpy` is already a pinned dependency (`pyproject.toml`, ADR-0153 decision 2). The new code uses only the standard library and `numpy`: no new external dependency (no `mpmath`). If one seems needed, stop and return BLOCKED (A-13 new dependency).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit);
  - §5 (task format; naming: branch `claude/T-0446-<slug>`, PR title with `T-0446`, commit trailer `Task: T-0446`, last line of the PR body `Task: T-0446`; size cap; test rules).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`:
  - Context, Meta's reference (lines 24-30): `apply_scaling`, `precompute_freqs_cis`, the constants, and the Hugging Face scale factor;
  - decision 3 (lines 46-50): position and constants reach the kernel only through the table;
  - **decision 4 (lines 52-57), the rule this task implements**: who builds the table and when, the formula for f(i), λ, g(i), the angle and the entries (t, 2i) = cos, (t, 2i + 1) = sin, the constants, the computed band facts for Llama 3.2 1B, the precision rule (correctly rounded binary32, ties to even), and why NumPy float64 `cos`/`sin` alone carry no guarantee;
  - decision 5 (lines 59-61): pair i takes table columns 2i and 2i + 1;
  - decision 6, the `freqs_cis` bullet (line 66): dtype `fp32`, row i is the row of position P + i;
  - decision 13 (lines 131-137): the verification table uses s = 8, and what the kernel's verification does not detect;
  - Consequences, the code-slice bullet (line 189);
  - Boundaries (lines 196-206), in particular the scale factor (OD-31 sub-question 5).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`:
  - decision 2 (lines 35-39): host side in Python with `numpy`, no new dependency;
  - decision 3 (a) and (b) (line 42): the model parameters, "never assumed by the executor", and the table as one more array;
  - decision 6 (lines 64-68): no value of Llama 3.2 1B is assumed.
- `hilclaw/model_binding.py`, lines 186-210 (`check_dimensions`) and 918-931 (`_integer`, `_parameter`): the argument-check style to follow (`TypeError` for a wrong type, `ValueError` otherwise, with the attribute `parameter` set to the argument's name). Read only.
- `hilclaw/rope_bf16_contract.py`, the module docstring (lines 1-60): the docstring style and what that module says it leaves to the table builder. Read only.
- `tests/test_rope_bf16_contract.py` lines 588-600 (`test_module_imports_keys_only_and_is_named_by_no_other_module`): it asserts that no other `hilclaw/*.py` file contains the text `rope_bf16_contract`. Read only.
- `pyproject.toml` lines 1-10 (`numpy` pin).

## Acceptance Criteria

1. **New module `hilclaw/rope_table.py`** (Python; standard library and `numpy` only). Its public names are exactly `frequencies` and `build`.
2. **Inputs.** Both functions take keyword-only arguments, all required, with no default:
   - `head_dim`: exactly an `int` (`bool` and subclasses refused), even, from 2 to `hilclaw.keys.MAX_INTEGER` (ADR-0161 decision 11: "`d` is even and at least 2");
   - `theta`, `scale_factor`, `low_freq_factor`, `high_freq_factor`, `old_context_len`: each exactly an `int` or a `float` (`bool` refused), finite and > 0. In addition `high_freq_factor` > `low_freq_factor`, so σ's denominator b − a is never 0. These are the names of Meta's code (Context): θ, s, a, b and L of decision 4.
   - `build` also takes `positions`: exactly an `int`, from 1, and `positions * head_dim` no larger than `keys.MAX_INTEGER`. The table has rows for positions 0 to `positions` − 1 (decision 4: "for positions 0 to the last position of the generation").
   - Errors follow `hilclaw/model_binding.py`: `TypeError` for a wrong type and `ValueError` otherwise, each with the attribute `parameter` set to the argument's name. The order of the checks is the order of the arguments in the signature, so the first bad argument is reported.
   - The `b > a` and `positions * head_dim` limits are conventions of this module, not rules of the record. Say so in the docstring.
   - The module holds **no** Llama 3.2 1B value: no 500000, no 8 or 32, no 1, 4 or 8192 as a constant or default, no `use_scaled` switch (decision 4's rule always applies the scaling), no position offset, no bf16 table.
3. **The rule and the precision** (ADR-0161 decision 4).
   - For i = 0 … d/2 − 1: f(i) = θ^(−2i/d); λ = 2π / f(i); g(i) = f(i)/s if λ > L/a; g(i) = (1 − σ) · f(i)/s + σ · f(i) with σ = (L/λ − a)/(b − a) if L/b ≤ λ ≤ L/a; g(i) = f(i) otherwise. angle(t, i) = t · g(i).
   - `build` returns a new `numpy.ndarray` of dtype `float32`, shape `(positions, head_dim)`, C-contiguous, whose entry `[t, 2i]` is cos(angle(t, i)) and `[t, 2i + 1]` is sin(angle(t, i)), **each the binary32 value nearest to the exact value, ties to even**. "Exact" means the real-number rule above with the inputs taken as their exact values (a `float` input is its exact binary value).
   - `frequencies` returns a `tuple` of d/2 Python `float`s, entry i the binary64 value nearest to g(i). It is the same g(i) that `build` uses, exposed so the band rule can be tested directly.
   - **Method** (decision 4: "The method is the builder's"). The result must not rest on the accuracy of a binary64 `cos`, `sin` or `pow` (decision 4 says NumPy's have no guaranteed accuracy). Use the standard library's `decimal` at a working precision well above binary32. Notes:
     - `Decimal.exp` and `Decimal.ln` are correctly rounded under the default `ROUND_HALF_EVEN`; `Decimal.__pow__` with a non-integer exponent is not documented as such, so prefer `exp(−(2i/d) · ln θ)`.
     - Compute π to the working precision in the module (for example the series of the `decimal` documentation's recipes).
     - Reduce the angle modulo 2π before a series.
     - Round each value to binary32 exactly: compare against the two neighbouring binary32 values with exact arithmetic (for example `fractions.Fraction`), not by `float(...)` then `numpy.float32(...)`, which rounds twice.
     - If the computed value lies within the evaluation's error bound of a binary32 rounding boundary (the midpoint of two neighbours), recompute that entry at a higher precision until it does not.
     - An angle of exactly 0 gives exactly 1.0 and +0.0.
     - The module docstring states the error bound used and why it holds, in a few sentences.
   - **Speed**: `build(positions=2048, head_dim=64, …)` with Meta's constants finishes within 30 s on the development machine. A pure-`decimal` evaluation of the 65536 angles at about 45 digits took about 1.2 s when this task was planned. Compute g(i) once per column, not per entry. State the measured time in `## Result`.
4. **Docstrings.**
   - The module docstring states:
     - the record (ADR-0161 decision 4, with decisions 5, 6 and 13 for the column pairs, the `fp32` dtype and the verification use) and ADR-0153 decision 3 (a) and (b);
     - the rule, in the notation of decision 4;
     - the precision guarantee and the method;
     - that every constant is an input with no default, and that which scale factor Llama 3.2 1B needs is open (OD-31 sub-question 5; the driver's HQ-0070), not this module's choice.
   - It also states what the module does not do: no model parameters type and no Llama constant; no binding, call site, slice of rows for a position P, or call of a kernel; no model program, file, process, tool or command-line entry; no harness mechanism; no bf16 or float64 table.
   - The text of the module, docstrings included, must not contain the string `rope_bf16_contract` (the test of Required Reading would fail). Name the contract by ADR number and kind `rope` instead.
   - Each public function has a Doxygen-like docstring (arguments, return value, errors) in the style of `hilclaw/model_binding.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, new file `tests/test_rope_table.py`** (D12: happy, error, branch and negative cases; every public function). It covers at least:
   - **Independent reference.** A reference evaluation written in the test file, independent of the module's private helpers: `decimal` at 60 or more significant digits, its own π and series, and exact rounding to binary32. It must agree with the module:
     - for Meta's constants (θ = 500000, s = 8, a = 1, b = 4, L = 8192, d = 64), `build(positions=2048, …)` equals the reference bit for bit on every column of rows 0, 1, 2, 127, 128, 1000, 2046 and 2047;
     - the same for s = 32 on rows 1, 127 and 2047 (the builder takes either scale factor; no answer to HQ-0070 is implied);
     - on every entry of at least two small tables, for example d = 2 and d = 8 with θ = 10000 and other s, a, b, L values such that some column falls in each of the three bands, and both `int` and `float` constants.
   - **Fixed values.** Copy these binary32 bit patterns of `build(positions=2048, head_dim=64, theta=500000, scale_factor=8, low_freq_factor=1, high_freq_factor=4, old_context_len=8192)` into the test. They were computed at planning time with `decimal` at 60 and 90 digits (both agreed) and cross-checked against a float64 evaluation; they guard against a reference that shares an error with the module:
     - `[1, 0]` `0x3F0A5140`, `[1, 1]` `0x3F576AA4`;
     - `[127, 0]` `0x3E6DEF8B`, `[127, 1]` `0x3F78FE49`;
     - `[2047, 0]` `0x3E7FB55B`, `[2047, 1]` `0xBF77E3C6`;
     - `[2047, 30]` `0xBF71E8D8`, `[2047, 31]` `0x3EA78538`;
     - `[2047, 36]` `0x3F7CC1AE`, `[2047, 37]` `0x3E227C93`;
     - `[2047, 62]` `0x3F7FFFFB`, `[2047, 63]` `0x3A4A2867`.
     If one of these disagrees with both the module and the independent reference, stop and report it in `## Result` with BLOCKED (`requirement-unclear`) instead of changing the value.
   - **Row 0**: every cos entry is exactly 1.0 and every sin entry is exactly +0.0 (sign bit clear).
   - **Bands** (decision 4, computed facts), with Meta's constants and d = 64, through `frequencies`:
     - length 32 and `g[0] == 1.0`;
     - i = 0 … 14 equal the unscaled θ^(−2i/d) (compare with a `frequencies` call at s = 1, or with the reference);
     - i = 18 … 31 equal the unscaled value divided by 8 to within one binary64 unit in the last place;
     - i = 15 … 17 lie strictly between those two;
     - `g[31]` is 3.767 · 10^−7 to four significant digits.
   - **What decision 13 leaves to the builder's tests**, each shown as a change of the table:
     - another θ changes it;
     - s = 1 (no scaling) changes every entry of columns 30 … 63 in row 2047 and leaves columns 0 … 29 of every row unchanged;
     - row t equals the reference at position t, not t ± 1;
     - columns 2i and 2i + 1 hold cos and sin of the same angle (for example a pair with cos² + sin² within 2^−22 of 1 and the sign of sin(angle) as the reference).
   - **Result form**: dtype `float32`, shape, C-contiguous; a new array each call (mutating one result does not change the next); every entry finite with magnitude ≤ 1.
   - **Rounding branch**: a test that reaches the higher-precision recompute path (for example by monkeypatching the module's working precision or its error margin so that an entry needs a retry) and checks the result still equals the reference. Also a tie-to-even case of the exact binary32 rounding, if the module's rounding helper can be reached through a public call or a monkeypatch; otherwise say in `## Result` how the line is covered.
   - **Negative inputs** for each argument of both functions: a missing argument and a positional call (`TypeError`); `bool`, `str`, `None`, a `complex`; for the real constants 0, a negative value, `nan`, `inf` and `-inf`; for `head_dim` 0, 1, an odd value, a negative value and `MAX_INTEGER + 1`; for `positions` 0, a negative value and a value with `positions * head_dim > MAX_INTEGER`; `high_freq_factor == low_freq_factor` and `high_freq_factor < low_freq_factor`. Each error carries the right `parameter`.
   - **Independence**:
     - the public names are exactly `frequencies` and `build`;
     - the module imports only the standard library, `numpy` and, if used, `hilclaw.keys`;
     - its text contains none of `rope_bf16_contract`, `model_binding`, `500000` and `8192`;
     - no other `hilclaw/*.py` file names `rope_table` (a later task adds the user and adjusts this test);
     - a call writes no file.
6. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally, with every existing test unchanged.
   - Line and function coverage of `hilclaw/` stay ≥ 80%, and the new module is at 100% line coverage, or as close as the method allows with the uncovered lines named in `## Result`.
   - CI is green, and the CI test-existence check finds `tests/test_rope_table.py`.
   - If the new tests make the suite slower by more than about 30 s, build the large table once per test module (a module-scoped fixture), and state the added time in `## Result`.
7. **No other file changes.**
   - Do not edit any existing `hilclaw/` module or test. In particular `hilclaw/model_binding.py`, `hilclaw/rope_bf16_contract.py`, `hilclaw/keys.py`, the model executor modules and the harness are not edited.
   - Do not edit any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. If an ADR sentence becomes less exact (for example ADR-0153 decision 3 (b)'s "who computes it" is now answered in code), note it in `## Result` and do not edit it.
8. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0446-<slug>`, Draft PR whose title contains `T-0446` and whose body ends with `Task: T-0446`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
   - The commit body has one line on the language choice (Python: host-side array work with `numpy` and exact arithmetic with `decimal` and `fractions`, as ADR-0153 decision 2 places the host side).
   - The reviewer checks at least:
     - the band conditions and σ against decision 4, including which side each boundary falls on;
     - the column order (cos at 2i, sin at 2i + 1) and the row = position rule;
     - that correct rounding does not rest on a binary64 `cos`, `sin` or `pow`, that the rounding to binary32 is single and ties to even, and that the retry rule is sound;
     - that no Llama constant or default is in the module (HQ-0070);
     - the twelve fixed values and the independence of the test's reference.

## Out of Scope

- The RoPE binding check in `hilclaw/model_binding.py` with the call sites `rope_q` and `rope_k`, the shape (rows, heads, head_dim) and the "every shape" binding (ADR-0161 decision 15, Consequences).
- The RoPE constants as model parameters (a `ModelDimensions` field or a new parameters type), any Llama 3.2 1B value in `hilclaw/`, and the choice of the scale factor (HQ-0070; OD-31 sub-question 5, owner).
- Slicing rows P … P+T−1 for a call, copying Q and K ranges, passing the table to the model program, the model program, any C code and any kernel fixture.
- The P2-12 harness: generator, seed, draws, the choice of the T = 1 row, tolerance, comparison.
- Meta's binary32 order of roundings (decision 4's departure; OD-31 sub-question 6, owner).
- The SDPA with KV cache contract; fp16; backends other than `cpu_standin`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next part of the ADR-0161 code slice: the bf16 RoPE binding check in `hilclaw/model_binding.py` with `rope_q` and `rope_k`, in the pattern of T-0443 (that part also adjusts `tests/test_rope_bf16_contract.py`'s "named by no other module" test for the binder). After that, the SDPA with KV cache contract record (doc).

## Result

- **Outcome**: DONE. PR #263 squash-merged as `4c3dac5` (branch deleted). Adds `hilclaw/rope_table.py` and `tests/test_rope_table.py`; no other file changed.
- **Review**: 2 rounds, both Approve; round 1 nit (a test patched `numpy.empty` globally) fixed by stubbing only the module's `numpy` reference.
- **CI**: green; coverage gate reports `hilclaw/rope_table.py` 100% lines, `hilclaw/` 99%; test-presence check passes.
- **Local gates**: `ruff check`/`ruff format` clean; full local suite 28958 passed, 949 skipped (round 1 test file; round 2 touched only that file, re-run alone and passed).
- **Language**: Python - host-side array work with `numpy` and exact arithmetic with `decimal` and integers (ADR-0153 decision 2). No new dependency.
- **Method**: `decimal` interval arithmetic up to the reduced angle (outward rounding, `ln`/`exp` widened by one ulp, pi from Machin's formula in integers); cos/sin from a series with error bound 100*M*10^(1-P); each value rounded once to binary32, ties to even; an undecided entry is recomputed at twice the precision.
- **Known limit** (in the docstring): for the middle band no theorem rules out an exact rounding midpoint, so the recompute loop is not proven to terminate there.
- **Fixed values**: all twelve bit patterns matched the module, an independent 70-digit reference and a float64 cross-check.
- **Speed**: `build(positions=2048, head_dim=64, ...)` with Meta's constants ~2 s; the test file runs in ~7-21 s (module-scoped fixtures).
- **Less exact, not edited**: ADR-0153 decision 3 (b) ("who computes it, and in what precision") is now answered in code by this module.
- **Follow-ups**: none new. The next slice part (RoPE binding check in `hilclaw/model_binding.py` for `rope_q`/`rope_k`) must adjust `test_the_module_is_named_by_no_other_module` in `tests/test_rope_table.py` if it imports `rope_table`.
