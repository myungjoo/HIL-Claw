---
id: T-0209
title: Add hilclaw/run_admission.py, the run tools' admission of op_signature, objective and n_max in the order of ADR-0067 decision 5
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, OD-8, OD-13]
dependsOn: [T-0192, T-0204, T-0208]
touchesFiles:
  - hilclaw/run_admission.py
  - tests/test_run_admission.py
  - hilclaw/run_objective.py
estimatedSize: {loc: 160, files: 2}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have seven records: ADR-0061 to ADR-0066 and ADR-0067 (landed by T-0208 as `73996b5`), which answers OD-18 sub-question ⑲ (가): the three tool-failure kinds `op_signature_not_stated`, `op_signature_not_covered` and `n_max_not_stated`, and the order of every answer of moment ④ (decision 5, steps 3 to 7).

ADR-0067 Consequences, "Code ... Possible now", names this slice: "the run tools' admission of the op_signature, the dimensions and `n_max`, in the manner of `hilclaw/check_admission.py`, with its tests — the three kinds, the order of decision 5 together with `hilclaw.run_objective.admit`, and what an admitted content gives (the dimensions and `n_max` of the timing parameters). 'Covered' can be `hilclaw.gemm_contract.covers` ... Whether it extends `hilclaw/run_objective.py` or adds a module, and the names, are the code task's." The 2026-10-15 journal names this as the next candidate. No ADR is needed: every design point is fixed by ADR-0067 (with ADR-0061 decisions 3, 4 and 6) or left to the code by it. This task **adds a module** (`hilclaw/run_admission.py`) and leaves `run_objective.admit` as it is, calling it for steps 5 and 6.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention: branch `claude/T-0209-<slug>`, `Task: T-0209` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md` sections "상시 규칙" — the test rule (D12 ①-⑤), the language policy (record the language choice and its reason in one line of the commit body), the branch/merge procedure (code mode: Draft PR, review cycle, CI green, self squash-merge, delete branch), the comment-minimisation rule, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- `ARCHITECTURE/decisions/ADR-0067-od18-run-tools-admission-kinds.md` (167 lines): Decision §1 to §6 (lines 22-99: §2 `op_signature_not_stated`; §3 "covered" is the predicate of ADR-0041 decision 5; §4 `n_max_not_stated`, no bound substituted; §5 the order table and its reasons; §6 properties, the message rule — names the member, says none is stated / not covered, shows nothing of the file's content), the Walk-through (lines 100-117), Limits (lines 118-125) and Consequences (lines 143-150, the "Code" bullet and the `run_objective.py` docstring sentence now less exact).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md` decisions 3, 4 and 6 (what the tool function takes from the read of ④; the objective kinds; the `bound`).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` decision 2 (the six timing parameters: `m`, `k`, `n` each at least 1, `n_max`, sample form, seed).
- `hilclaw/check_admission.py` (whole; the analogue: kinds, `KINDS` order, `Admitted`, `admit(instance, *, covers)`, the docstring structure "Choices that are this module's own" / "What the module does not do").
- `hilclaw/run_objective.py` (whole; `admit`, `Admitted(sample_form, bound)`, its two kinds and the last sentence of its module docstring).
- `hilclaw/instance.py` lines 614-680 (`Tolerance`, `OpSignature(key, record)`, `Instance` fields: `n_max`, `op_signature`, `objective`).
- `hilclaw/gemm_contract.py` `covers` (lines 103-125).
- `hilclaw/run_parameters.py` (whole) and `hilclaw/run_seed.py` lines 1-66 (the draw comes after the last answer of ④; not called by this module).
- `hilclaw/tools.py` `ToolFailure` (lines 65-80).
- `tests/test_check_admission.py` and `tests/test_run_objective.py` (skim the structure: order tables, `covers` call checks, import check, public-names check).

## Acceptance Criteria

1. **New module `hilclaw/run_admission.py`** (Python, as the `run_*` modules and `check_admission.py`; the module name is the executor's choice — if changed, keep `touchesFiles` and the PR in sync). Its docstring cites ADR-0067 (a decision cited by number alone being one of that record) and ADR-0061, says what it renders (steps 3 to 7 of ADR-0067 decision 5 and what an admitted content gives), lists every choice that is the module's own and no rule of a record, and says what the module does not do: no tool, no registration, no file read, no backend selection (steps 1 and 2 of decision 5 — the `run_file_*` kinds, `no_backend`, `not_offered` — are the caller's to keep before it), no seed drawn (`hilclaw.run_seed.draw` is after it; the caller's), no line appended, no kind ever the `failure` of an end line (ADR-0067 decision 6), nothing kept between calls, no reserved kind.
2. **The three kinds as public constants** of this module, spelt exactly `op_signature_not_stated`, `op_signature_not_covered` and `n_max_not_stated` (ADR-0067 decisions 2 to 4), and a `KINDS` tuple of the five answers this module gives in the order of decision 5 steps 3 to 7: `op_signature_not_stated`, `op_signature_not_covered`, `objective_not_stated`, `objective_not_covered`, `n_max_not_stated` (the two objective constants taken from `hilclaw.run_objective`). Whether the two op_signature constants are imported from `hilclaw.check_admission` or defined here is the executor's choice, stated in the docstring; either way a test asserts their values equal those of `check_admission` (the same spelling on purpose, ADR-0067 decision 6). The messages are this module's own: each at most 200 characters, starts with the name of the member it is about (`op_signature` or `n_max`), says that the file states none or that the stated one is not covered by the run tools' contract, and shows nothing of the content; they must not say "check" (the check's message for `op_signature_not_covered` names "check" and is not reused).
3. **`admit(instance, *, covers)`** (or the executor's name, stated):
   - `TypeError` before anything else when `instance` is not exactly `hilclaw.instance.Instance`, then when `covers` is not callable; no default for either; `covers` by keyword.
   - Answers, the first whose condition holds and no other (ADR-0067 decision 5), each a raised `hilclaw.tools.ToolFailure`: (3) `instance.op_signature is None` → `op_signature_not_stated`, `covers` not called; (4) `covers(stated.record)` called once with the record object the instance holds, its exceptions pass through unchanged, a return value not exactly `bool` is `TypeError` (never taken as covered), `False` → `op_signature_not_covered`; (5)-(6) `hilclaw.run_objective.admit(instance.objective)` — its `ToolFailure`s, `TypeError`s and `ValueError`s pass through unchanged; (7) `instance.n_max is None` → `n_max_not_stated`. No bound is substituted: not 10, not `N_MAX_DEFAULT` (ADR-0067 decision 4); `hilclaw.harness.measurement` is not imported.
   - Otherwise returns an admitted value (a `typing.NamedTuple`; field names and order are the module's own) holding `m`, `k`, `n` from `stated.record["shape"]`, `n_max` from the instance, and `sample_form` and `bound` from the `run_objective.Admitted`, each unchanged. No timing parameters are built (no seed exists yet); that a caller can build `hilclaw.run_parameters.TimingParameters` from it plus a seed is shown in a test.
   - Nothing else of the instance is looked at (`hw_profile`, `hw_profile_key`, `tolerance`, `draws`, `others`, the op_signature key); `instance` is not modified or kept; no file read or written.
4. **`hilclaw/run_objective.py` module docstring only**: replace the sentence "Its place relative to the answers for the op_signature and ``n_max`` is not its own to decide (OD-18 sub-question ⑲ (가)): whoever calls places it." with one that says the place is ADR-0067 decision 5 (after the op_signature answers, before `n_max_not_stated`) and that keeping it is the caller's, e.g. `hilclaw.run_admission`. No code or test change in that module.
5. **New test file `tests/test_run_admission.py`** (D12 ②-④), covering at least:
   - happy: a full instance (the ADR-0067 Walk-through first row: `m` 1, `k` 2048, `n` 8192, `gemm`, `fp32`, `row_major`, objective `latency_minimisation`, `n_max` 10) admitted with `gemm_contract.covers`, values equal and taken unchanged; with and without a `memory_ceiling` `bound`; the admitted value plus a seed builds a `TimingParameters`.
   - the order of decision 5 as a table: every combination of {op_signature absent / not covered / covered} × {objective absent / not covered / covered} × {n_max absent / present} gives the first answer of steps 3-7 — including the Walk-through rows (no op_signature and nothing else → `op_signature_not_stated`; `fp16` or `m` 0 → `op_signature_not_covered`; covered, no objective, no `n_max` → `objective_not_stated`; covered, objective, no `n_max` → `n_max_not_stated`).
   - branch: `covers` not called when no op_signature; called exactly once with the same record object otherwise; `run_objective.admit` not reached when an op_signature answer is given (e.g. an objective of an invalid form does not raise `TypeError` then); the result is the same whatever `hw_profile`, `tolerance`, `draws` and `others` hold.
   - error/negative: `instance` not exactly `Instance` (a tuple of equal values, a subclass, `None`) → `TypeError`; `covers` not callable → `TypeError`, checked after `instance`; `covers` returning `1`, `None` or `"True"` → `TypeError`; `covers` raising → the same exception object; an objective form `run_objective.admit` rejects → its `TypeError`/`ValueError` passes through; `covers` passed positionally → `TypeError`.
   - each kind's message: at most 200 characters, starts with its member name, does not contain any value of the instance (record values, the key, a `label`); the op_signature kind constants equal those of `check_admission`; the module imports exactly what its docstring names; its public names are exactly the documented ones; no file written (`tmp_path` + `monkeypatch.chdir`).
6. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; the test-existence check finds `tests/test_run_admission.py`; CI green on the PR.
7. Size: non-test change <= 300 LOC and <= 5 files (expected about 160 LOC in `run_admission.py`, mostly docstrings, plus a one-sentence docstring edit in `run_objective.py`). If exceeded, split per DRIVER §5 and record the split in Follow-ups.
8. No data-plane schema change: no member of a request, a result, a line of `events.ndjson`, `STATE.json`, `instance.json`, a spec or a result file is added, removed or changed; no `error.kind` value beyond the three ADR-0067 names; no reserved kind. If the design seems to need one, stop and return BLOCKED.
9. Nothing in this task starts `claude`, builds or runs a kernel, starts a compiler, or needs a board or an API key (D16).
10. Code mode per CLAUDE.md A-13: branch `claude/T-0209-run-tools-admission-code`, Draft PR whose title contains `T-0209` and whose body ends with `Task: T-0209`, fresh-context reviewer cycle (dev-code-review), CI green, `gh pr merge --squash --body <PR body>`, branch deleted. Fill `## Result` with the commit/PR, review rounds, the language line and any follow-ups.

## Out of Scope

- Any change to `hilclaw/check_admission.py`, `hilclaw/gemm_contract.py`, `hilclaw/instance.py`, `hilclaw/run_seed.py`, `hilclaw/run_parameters.py`, `hilclaw/run_operation.py`, `hilclaw/mock_run.py` or their tests; any code change in `hilclaw/run_objective.py` beyond the one docstring sentence.
- The tool functions of `sim.run` / `board.run`, the read of ④, the backend selection, the seed draw call, start/end lines, the registration, the input schema and description; OD-18 ⑲ (나) to (라), ⑳; the spend (OD-2, OD-19); `profiler.collect`.
- Who writes `n_max` / `op_signature` at the start of an instance and where 10 comes from (OD-8 ㉑, ㉘; OD-23).
- Any `ARCHITECTURE/` edit, including the "Not edited and now less exact" sentence list of ADR-0067 Consequences.
- Any new dependency.

## Follow-ups

## Result
