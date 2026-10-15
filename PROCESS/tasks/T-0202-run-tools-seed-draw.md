---
id: T-0202
title: Add hilclaw/run_seed.py, the timing seed draw of sim.run / board.run answered seed_not_drawn (ADR-0064 decisions 2 to 4)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, NFR-3, OD-13, OD-18]
dependsOn: [T-0201]
touchesFiles:
  - hilclaw/run_seed.py
  - tests/test_run_seed.py
  - hilclaw/harness/seed_source.py
estimatedSize: {loc: 140, files: 2}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have four records: ADR-0061 (split), ADR-0062 (call identity), ADR-0063 (result members) and ADR-0064 (timing seed, landed by T-0201 as `d1e68f3`). Code already exists for the admission of the objective (`hilclaw/run_objective.py`, T-0192), the step values (`hilclaw/run_identity.py`, T-0196) and the result object (`hilclaw/run_result.py`, T-0200).

ADR-0064 Consequences, "Code slice made possible", names the next code slice: **the seed draw of the run tools and its tests** — the draw of decision 2 with the answer `seed_not_drawn` and the message rule of decision 4, as `hilclaw/check_seed.py` `draw` is for the check. Names and modules are the code task's. T-0201 Follow-ups and the 2026-10-15 journal name this as the next task.

This task adds that slice as a new module `hilclaw/run_seed.py` with its test file, and corrects the one docstring line ADR-0064 Consequences says becomes less exact when `hilclaw.harness.seed_source` serves both contracts. No ADR is needed: every design point is fixed by ADR-0064 or left to the code by it. The tool functions, their registration and the operations stay out of scope (ADR-0064 Consequences, "Not yet possible").

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention: branch `claude/T-0202-<slug>`, `Task: T-0202` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md` sections "상시 규칙" — the test rule (D12 ①-⑤), the language policy (record the language choice and its reason in one line of the commit body), the branch/merge procedure (code mode: Draft PR, review cycle, CI green, self squash-merge, delete branch), and the comment-minimisation rule.
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md`: Status, Decision §1 to §5 and §7, Walk-through, §8 Limits, Consequences (the bullets "Code slice made possible" and "Not edited and now less exact"), Boundaries.
- `ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md` §3 to §6 (the check's draw, whose kind, cases and message rule ADR-0064 decision 4 takes over).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md` §3 and §4 (the seed as an input the operation does not choose; kinds of the run tools' contract serve both tools with one meaning).
- `hilclaw/check_seed.py` (whole; the analogue: `draw`, `KIND_SEED_NOT_DRAWN`, the two messages and how the two cases are told apart and kept out of `__cause__` / `__context__`).
- `hilclaw/harness/seed_source.py` (whole).
- `hilclaw/run_objective.py` lines 1-70 (how a kind of the run tools' contract is declared and documented).
- `hilclaw/tools.py` lines 60-90 (`ToolFailure`).
- `tests/test_check_seed.py` lines 1-370 and 678-744 (the test pattern for `draw`, the import check and the public-names check).

## Acceptance Criteria

1. **New module `hilclaw/run_seed.py`** (Python — the run tools' code is Python and the source module is Python). Its module docstring cites ADR-0064 and says what the module renders and what it does not (in the manner of `check_seed.py`, kept shorter where possible). It has:
   - `KIND_SEED_NOT_DRAWN = "seed_not_drawn"`: the run tools' own kind of ADR-0064 decision 4, not reserved, with the same spelling and meaning as `check_seed.KIND_SEED_NOT_DRAWN`. Define it in this module (ADR-0064 decision 4: the run tools' contract defines its own); a test asserts it equals the check's value.
   - `draw(source)`: asks `source` exactly once and returns the timing seed of the call (exactly an `int`, 0 <= seed < 2**64, the same object), or raises `hilclaw.tools.ToolFailure` of kind `KIND_SEED_NOT_DRAWN` for both cases of a draw that yields no seed (the source raised an `Exception`, a `ToolFailure` included, or cannot be called without arguments; the source returned what is no seed). No second ask, no other source, no constant stands in (decision 3). A `BaseException` that is no `Exception` passes through as the same object (decision 4, "A raised request to end"). A `source` that is not callable is `TypeError` and nothing is asked (as `check_seed.draw`; state it as the module's own choice).
   - Messages (decision 4, by ADR-0048 decision 6): exactly a `str` of at most 200 characters, built at import; they say the draw of the timing seed yielded no seed and which of the two cases it was; they show nothing a source returned or raised and no type name. Neither `__cause__` nor `__context__` of the raised `ToolFailure` is the source's error or the `SeedSourceError`.
   - Whether `draw` goes through `hilclaw.harness.seed_source.draw` directly or reuses `hilclaw.check_seed` is the executor's choice (ADR-0064 decision 2 leaves it to the code); if it reuses `check_seed.draw`, the raised failure's message must still name the timing seed, so a re-raise with the run tools' own message (and clean `__cause__` / `__context__`) is needed. Do not change `hilclaw/check_seed.py`.
   - The module binds no source and holds no default source, keeps nothing between calls, writes no file, prints nothing, and composes no message holding the seed (decision 5). It does not check that the call reached the draw (that its identity has no line and moment ④ gave no answer) — say so in the docstring as the caller's order, together with the order "after the last answer of ④, before the start line" (decision 3).
2. **`hilclaw/harness/seed_source.py`**: change only the module docstring so it no longer says it is the source of the seed of a correctness check alone — it is the form of a seed source with the property of ADR-0021 decision 3, which ADR-0064 decision 2 takes for the timing seed of `sim.run` / `board.run`. No code change in this file. (`hilclaw/harness/__init__.py` stays: its sentence is still true.)
3. **New test file `tests/test_run_seed.py`** (D12 ②-④), covering at least:
   - happy: a seed at 0, a middle value and `2**64 - 1` is returned as the same object and the source is asked once; two draws ask twice and keep nothing; `seed_source.system` as the source yields a seed.
   - error/negative: a source raising `Exception` subclasses (including a `ToolFailure` of another kind and of `seed_not_drawn`) → `seed_not_drawn`; a source needing an argument → `seed_not_drawn` in the "raised" case; a source returning `None`, `True`, a `float`, an `int` subclass instance, `-1`, `2**64`, a `str` → `seed_not_drawn` in the "no seed" case; a non-callable `source` (e.g. `None`, `7`) → `TypeError` and never the kind.
   - branch: the two messages differ, are `str` of length <= 200, and contain no marker value the source returned or raised and no type name; `__cause__` and `__context__` are not the source's error nor a `SeedSourceError`, including when `draw` is called inside an `except` block (only the outer error may appear as context, as in `test_check_seed.py`).
   - `KeyboardInterrupt` / `SystemExit` from the source pass through as the same object.
   - `KIND_SEED_NOT_DRAWN == "seed_not_drawn" == check_seed.KIND_SEED_NOT_DRAWN`, and the name is not one of `run_objective.KINDS`.
   - No file written (`tmp_path` + `monkeypatch.chdir`), the module's imports are exactly the ones its docstring names, and its public names are exactly `KIND_SEED_NOT_DRAWN` and `draw` (adjust if the executor adds a justified public name, and document it).
4. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; CI green on the PR.
5. Size: non-test change <= 300 LOC and <= 5 files (expected about 140 LOC in two non-test files).
6. Nothing in this task starts `claude`, builds or runs a kernel, or needs a board or an API key (D16).
7. Code mode per CLAUDE.md A-13: branch `claude/T-0202-run-tools-seed-draw`, Draft PR whose title contains `T-0202` and whose body ends with `Task: T-0202`, fresh-context reviewer cycle (dev-code-review), CI green, `gh pr merge --squash --body <PR body>`, branch deleted. Fill `## Result` with the commit/PR, review rounds, the language line and any follow-ups.

## Out of Scope

- The tool functions of `sim.run` / `board.run`, their registration, the start line and the call order (ADR-0062 decision 6); the form of what crosses the cut and the neither-form answer (ADR-0061 Consequences item (4), a later doc task); the operations of `cpu_standin` and the mock.
- Which tool failures an operation may raise onto an end line, and the guard that no end line holds `seed_not_drawn` (ADR-0064 decision 4 asks it of a later slice).
- Any change to `hilclaw/check_seed.py`, `hilclaw/check_tool.py`, `hilclaw/harness/timing.py`, `hilclaw/run_objective.py`, `hilclaw/run_result.py` or any ADR / `ARCHITECTURE/` file; the integrator's "less exact" sentence list of ADR-0064 Consequences.
- Reserving the kind in the frame (`hilclaw/tools.py`), any new dependency, any data-plane member.

## Follow-ups

- (planner, document mode, §9, P1-1) ADR-0061 Consequences item (4): the form of what crosses the cut of `sim.run` / `board.run` and what a call answers when an operation returns neither form (in the manner of ADR-0043 and ADR-0045); it should also carry ADR-0064 decision 4's request that no end line holds `seed_not_drawn`.

## Result
