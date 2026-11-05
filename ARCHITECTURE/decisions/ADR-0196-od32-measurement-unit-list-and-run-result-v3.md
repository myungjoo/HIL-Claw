# ADR-0196: The measurement unit of `sim.run` and `board.run` (the owner's answer to HQ-0090 (a)·(가)) — the result v3 under two new `step` values `sim_run_timing_v3` and `board_run_timing_v3`, whose `unit` is a value of the approved open list "측정 단위" (`ns`, `cycles`) and applies to `intervals` and `resolution` only; the unit held on the target; `virtual_npu` reporting `cycles` as its ns times 3; every reader reading a point's lines under both its v2 and its v3 value, two results of different units refused as the new tool-layer kind `units_differ`; and the two code slices (part of OD-32 ② and ③, OD-33 ⑥, OD-18 ⑩ and OD-8)

## Status

- **Accepted on 2026-11-05** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Three kinds of content.**
  - **Owner**, marked so: the answer to HQ-0090 (2026-11-05) and the entry "측정 단위" of DRIVER §3 "승인된 열린 목록" registered with it; HQ-0078 ⑤ where cited. The owner's words are **not subject to the objection window** above.
  - **The integrator's reading, cited and not this record's**: the note in HQ-0090's `decision` that marks itself "통합자 독해(오너의 말이 아님)".
  - **This record's own**: every other sentence — where the unit is held, the factor 3, the readers' rules, `units_differ`, the StepValues states, the slices and every weighing.
- **Answers** part of **OD-32** ② (where the unit is held) and ③ (the virtual NPU's unit), the unit-list part of **OD-33** ⑥ that HQ-0090 settled (recorded here, not decided), part of **OD-18** ⑩ (the result format of the run tools) and part of **OD-8** (two `step` values of `events.ndjson` lines by the rule of [ADR-0100](ADR-0100-od8-tool-result-change.md), and their [StepValues](../StepValues.md) rows). Each OD keeps its status.
- **Session entry check** (CLAUDE.md), on 2026-11-05 at `main` `4d3e3ece`: open PRs — none; no open `nightly-failure` issue; no `실패` item in `PROCESS/RuntimeAcceptance.md`; issue #4 last comment 2026-07-31, #5 2026-11-05, #7 2026-09-07, #8 closed. Unresolved HQs: HQ-0081, HQ-0089, HQ-0091 to HQ-0097. None is crossed: HQ-0091 (oracle and data type at `virtual_npu`), HQ-0095 (which execution is which point) and HQ-0097 (device-unavailable kind) are named in Boundaries and not anticipated. **HQ-0091 was answered later the same day** (`main` `c1d2f567`, ① (a)·② (a)); its follow-up is its own task, and nothing here depends on it.
- **Code**: slice 1 of decision 6 lands with this record (readers only; no writer changes). No `claude` process was started, nothing was built or run in a container, and nothing needs a board or a key (D16). Statements about code are observations of `main` at `4d3e3ece`. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The owner's answer** (**owner**, HQ-0090, 2026-11-05; the `decision` of HQ-0090 in `PROCESS/STATE.json`, verbatim up to the integrator's note): "(a)·(가) — 오너(채팅, 2026-11-05): \"예, (a)·(가) 기록\". (a) `sim.run`·`board.run` 결과(`events.ndjson`의 `step_ended` 줄 `result`)의 `unit`을 DRIVER §3의 열린 목록으로 지정하고 첫 값은 `ns`·`cycles`; 새 `step` 값 `sim_run_timing_v3`·`board_run_timing_v3`(ADR-0100)를 모든 대상에 쓰고 읽는 쪽은 v2와 v3를 모두 읽는다; `cpu_standin`은 계속 `ns`; 값은 §9 ADR이 A-13 읽기에 이 목록을 밝히고 더한다. (가) 이 목록은 `intervals`·`resolution`에만 미치고 `memory_bytes`는 형식 그대로다. 질문대로 `virtual_npu`의 `cycles`는 자기 ns에 고정 배수를 곱한 검사용 값이며 실제 NPU의 근거가 아니고, 비교와 ADR-0103의 거친 시계 검사는 run 하나의 한 단위 안에서만이며, OD-33 ⑥의 단위 목록 부분은 이 답으로 정해졌다."
- **The integrator's note** in the same `decision` (cited, not the owner's words): the list's registration in DRIVER §3; the memory figure at vendor targets stays unreported (ADR-0194 decision 4) and is asked separately if needed; the follow-up is ADR-0193 decision 8's small task; and "단위를 대상에 두는지 지점의 측정 수단에 두는지는 그 task의 §9 ADR이 정한다".
- **The list** (**owner**, DRIVER §3 "승인된 열린 목록", "측정 단위"): the `unit` of the `sim.run` / `board.run` result, first values `ns` and `cycles`; a §9 ADR adding a value names the list in its A-13 reading; the list reaches `intervals` and `resolution`, not `memory_bytes`.
- **The rules a result change follows** (cited, ADR-0100 decisions 3 to 5): the result definition of a `step` value never changes; another definition takes a value never used; a call under the new value never returns a result stored under another value. Values are listed in StepValues ([ADR-0101](ADR-0101-od8-failure-kind-change-and-step-values.md) decisions 7 and 8).
- **Today** (cited, [ADR-0183](ADR-0183-od18-tool-result-format-v2.md)): the v2 result of decision 4, with `unit` the closed value `"ns"` applying to `intervals` and `resolution`; one `step` value per tool (decision 2); the readers of decision 8, which admit `unit` exactly `"ns"`. [ADR-0193](ADR-0193-od32-generalization-design.md) decision 3 put `unit` on the `Target` of `hilclaw/targets.py`; decision 4 kept `virtual_npu` at `ns` "until O3 is answered"; decision 8 sized this follow-up. [ADR-0194](ADR-0194-od33-vendor-stack-evaluation-design.md) decision 4 measures vendor targets with the host monotonic clock, `resolution` in `ns`; decision 5 binds each operation to one point's adapters.
- **Observations** (code at `4d3e3ece`): `run_result.UNITS` = `("ns",)`; `run_tool` takes the unit from the run's `Target` (`_UNIT` for the mock); `Target.unit` is checked against `run_result.UNITS`; both targets hold `ns`; `timings_tool._UNIT` = `"ns"`; `run_identity.STEPS` is read by `harness/timing_finding` alone.

## Decision

### 1. Scope and terms

- **The calls**: every call of `sim.run` or `board.run` at every target (`cpu_standin`, `virtual_npu`, the mock), every contract the run tools admit. **One format for all targets** (**owner**: "모든 대상에 쓰고").
- A *v2 value* is `sim_run_timing_v2` or `board_run_timing_v2`; a *v3 value* is `sim_run_timing_v3` or `board_run_timing_v3`; a *point's values* are its v2 and its v3 value (`sim`: the two `sim_run_timing_*`; `board`: the two `board_run_timing_*`).

### 2. The v3 result and its two `step` values

| Value | Tool | Point |
|---|---|---|
| `sim_run_timing_v3` | `sim.run` | sim |
| `board_run_timing_v3` | `board.run` | board |

- **The spellings are the owner's.** Checked on 2026-11-05: neither string occurs in `hilclaw/`, `tests/`, `orchestration/`, `catalog/` or `.claude/`, and in `ARCHITECTURE/` only in ADR-0193 decision 9 as the value O3 proposed for this very use; neither is in StepValues or a placeholder.
- **The v3 result has exactly the members of ADR-0183 decision 4's table**, with their names, types, presence and meanings, except one: **`unit` is a string that is a value of the approved open list "측정 단위"**, today `"ns"` or `"cycles"` (**owner**). It applies to `intervals` and `resolution` and to no other member (**owner**, (가)); one `unit` states both, for the reason ADR-0183 decision 4 gives (the replay and the coarse-clock test need the two in one unit). **`memory_bytes` keeps its name and meaning, a number of bytes** (ADR-0183 decision 4; **owner** (가)). A broken v3 result is a broken v2 result: no `unit`, `resolution`, `intervals` or `memory_bytes` (ADR-0183 decision 6).
- **The definition refers to the list, not to its present values.** A value the owner's list gains by a later §9 ADR is admitted under the v3 values without a new `step` value: the definition of decision 2 does not change (ADR-0100 decision 3 holds), and the ADR that adds the value adds it to every reader's admitted set (`run_identity.UNITS_OF`) in its own code. The DRIVER §3 paragraph after the list ("결과 정의가 바뀌어 새 `step` 값을 쓰는 경우(ADR-0100)는 그 결과 정의의 변경이 틀인지로 판단한다") is satisfied: the frame change — `unit` from one closed value to the list — is the owner's (a).
- **v2 is unchanged**: `unit` is exactly `"ns"` under a v2 value. **No line under a v2 value ever holds another unit**: no writer writes one (decision 6), and every reader refuses one as `timing_result_invalid` (decision 4).
- **Choice of the value** stays ADR-0062 decision 3's: from the tool alone, one value per tool. No target, contract or unit chooses between v2 and v3; once slice 2 lands, every target writes v3 (**owner**).

### 3. Where the unit is held: on the target

- **On the `Target`** (`Target.unit` of [ADR-0193](ADR-0193-od32-generalization-design.md) decision 3, unchanged in place), together with an integer factor (decision 5), not on the measuring means of a point.
- **Why.** The only unit other than `ns` the owner gave is a property of one target: "`virtual_npu`의 `cycles`는 자기 ns에 고정 배수를 곱한" (**owner**). The measuring means of every point that exists or is designed measure in `ns`: the `cpu_standin` waiter and harness, and every vendor adapter of ADR-0194 (decision 4: the host monotonic clock, `resolution` in `ns`). A per-point place would hold one value twice for every target and serve no case.
- **A target whose two points use means of different units** (ADR-0194 decision 5 allows two means). Nothing in the results or readers depends on where the unit is held: each line states its own `unit`, every comparison is within one point (`timings.compare` reads one point, ADR-0194 decision 5), and decision 4 refuses two units. So when a later record adds such a target or a value whose means differ by point, it moves the unit to the point's adapters in the package source — no frame change, as ADR-0193 decision 3's placement is none. This record does not foresee one.
- **What it means for the mock**: the mock has no `Target` and writes `ns` (as `run_tool` does today), under the v3 values after slice 2.

### 4. The readers

- **The rule** (the form of [ADR-0178](ADR-0178-od23-bf16-check-lines-read.md) decisions 1 to 3, applied to run lines): wherever a reader reads "the run lines of an attempt at a point", it reads the step lines of that attempt under **either of the point's values**, together, in log order. Each line's `result` is held to the definition of **its own** value: under a v2 value an admitted timing result has `unit` exactly `"ns"`; under a v3 value `unit` is a string of the list. Identities stay apart (an identity open under one value is not ended by an end line under the other; `execution` 1 under each value is two runs, ADR-0011 decision 3).
- **One attempt with lines of both values** (it happens to a run whose log spans the landing of slice 2, or to a log not written by the tools): read as one point. Its completed results of both values are its M of ADR-0140 decision 3, so two of them are `measurement_several`; an open identity or a `failure` under either value is `measurement_unknown`; a broken one under either neither enters nor refuses. Nothing is refused for holding both values. A message naming the step of a side names the values its lines are under, the v2 value when it has none.
- **Two results of different units are not compared** (**owner**: "비교 … 는 run 하나의 한 단위 안에서만"). **A new tool-layer kind `units_differ`** answers a comparison whose two results' `unit` differs, checked after `shapes_differ` and before `samples_out_of_domain`. *Why a new kind and not `shapes_differ`*: `shapes_differ` says the two results are not about the same quantity (ADR-0183 decision 8); two results in different units may be about the same quantity and still have no ratio, so the cause differs and the evaluator, who copies only a `difference` and writes no entry on any failure (ADR-0140 decision 6), sees which. The kinds of `timings.compare` are names of the tool layer and are not journaled (cited: ADR-0140 decision 3), so adding one changes no data plane. A v2 result and a v3 result in one unit are compared like two v2 results.
- **"Within one run"** (this record's reading of the owner's sentence, which is about `virtual_npu`'s `cycles`): `timings.compare`, `verdicts.write` and `feedback.base` read one run's log, so they compare within one run by construction. The S6 metric compares two runs (ADR-0074) but admits only runs whose hw_profile names `cpu_standin` or the mock (the runs of ADR-0120 decision 1; `outside_metric` otherwise), whose results are `ns`; it **admits only results in `ns`**, a completed result in another unit in such a run (a log not written by the tools) being a read failure, `timing_result_invalid`, before any best is chosen. So no `cycles` figure is compared, within or across runs, and the best of a run is chosen within one unit. The S6 comparison of `ns` figures across two runs is not reopened.
- **ADR-0103 decision 3** (coarse clock: 100 × `resolution` > the smallest interval) is a ratio of two members in one unit, so it is unchanged under any unit and does not read `unit` (ADR-0183 decision 8); the harness finding reads the run lines of all four values.

| Reader | Record | Under v2 and v3 | What changes | Slice |
|---|---|---|---|---|
| `timings.compare` (`hilclaw.timings_tool`) | ADR-0140 decisions 3, 4; ADR-0183 decision 8 | a point's two values together (`STEPS_OF`) | admitted result per line's value (`run_identity.UNITS_OF`); `units_differ`; `timing_problem` takes the line's `step` (no `step`: the v2 rule) | 1 |
| `verdicts.write`, `comparison` entries | ADR-0140 decision 5 | as above, through `timings_tool` | `timing_result_invalid` scope over both values; `units_differ` is `comparison_unfounded` | 1 |
| The S6 metric (`hilclaw.s6_metric`) — not in ADR-0183's table | ADR-0074 decisions 2, 3 | the board values, through `timings_tool.timing_lines` | a completed result whose `unit` is not `ns` is the read failure `timing_result_invalid` | 1 |
| The imprecise-timing finding (`hilclaw.harness.timing_finding`) | ADR-0104 decisions 3, 4 | `run_identity.STEPS`, now the four values | no code change; docstring in slice 2 | 1 (by `STEPS`) |
| `hilclaw.layout.build_log_file` | ADR-0078, ADR-0108 decision 3 | — | `BUILD_LOG_STEPS` gains the two v3 values; the v2 values stay, so a log named by either is valid | 1 |
| `feedback.base` (`hilclaw.spec_feedback._board_median`) — not in ADR-0183's table | [ADR-0184](ADR-0184-od20-first-case-incumbent-base.md) decision 2; ADR-0189 decision 2 | the board values | `timing_problem` with the line's `step`; the medians are compared within one unit: when the shown attempts' measurements hold more than one unit there is no `base` | 2 |
| `model_run_binding._timed_attempt_without_spec` — not in ADR-0183's table | [ADR-0189](ADR-0189-od31-binding-from-run-incumbents.md) | either board value | the step test widened | 2 |
| The `evaluator` and `experiment-runner` prompts | ADR-0140 decision 6 | through the tools | none: no `step` value or kind is named (observation) | — |

- **The search** (ADR-0183 decision 8's method, repeated on 2026-11-05 over `hilclaw/`, `orchestration/`, `catalog/` and `.claude/agents/`): for `run_identity`, `STEP_SIM_RUN`, `STEP_BOARD_RUN`, `_run_timing_v2`, `timings_tool`, `timing_problem`, `"intervals"`, `unit`. Found beyond ADR-0183's table: `s6_metric`, `spec_feedback._board_median` and `model_run_binding` (above). The writers `run_identity.step_of`, `run_result`, `run_tool`, `targets` and `run_definition` (which takes `NUMBERS` only) are not readers. Not claimed complete for `tests/`.

### 5. `virtual_npu`'s `cycles`

- **`virtual_npu` reports `unit` `"cycles"`**, and every figure it reports in it is **its own `ns` figure times the fixed integer factor 3** (`targets.VIRTUAL_NPU_CYCLES_PER_NS` in slice 2). **It is a check value and says nothing about the cycles or clock of any real NPU** (**owner**: "검사용 값이며 실제 NPU의 근거가 아니고"); it exists so that a reader that assumes `ns` fails a test.
- **Why 3**: an integer above 1, so a converted figure differs from its `ns` figure in every test; not a power of ten, so it is not mistaken for a decimal time unit (µs, ps) by a reader that guesses; small, so a converted figure stays within a few bits of its `ns` figure.
- **The conversion**: after the harness has judged the run in `ns` (convergence, `zero_interval`, the replay: `outcome` and `condition` are the judgement's, unchanged), `run_tool` multiplies **both** `resolution` and every entry of `intervals` by the target's factor, in integers. A `resolution` of 0 stays 0; an interval ≥ 1 stays ≥ 1; the order of `intervals` is kept. `memory_bytes` is not converted ((가)). `cpu_standin` reports `ns` with the factor 1, which converts nothing (**owner**: "`cpu_standin`은 계속 `ns`"); a target with the unit `ns` has the factor 1 (`Target` checks it).
- **What a conversion leaves unchanged within one unit**: ADR-0103 decision 3's test (both sides times 3); the ratio and its interval of ADR-0140 decision 4 (both samples times 3); the order of trimmed means. A replay of the stopping rule from stored `cycles` intervals is not made by any reader (ADR-0104 decision 3 believes `outcome`).

### 6. The code slices, in landing order (for the planner)

Each commit keeps every tool answering under one definition per value: **no writer writes a v3 result before every reader of decision 4's slice-1 rows reads it, and no writer ever writes a unit other than `ns` under a v2 value.** Sizes are changed non-test lines (DRIVER §5: ≤ 10 files, tests excluded; 600 lines advised).

1. **The readers** (this task, with this record): `hilclaw/run_identity.py` (the two v3 constants; `STEPS` = the four values; `UNITS_OF`; `step_of` still returns the v2 values), `hilclaw/layout.py` (`BUILD_LOG_STEPS`), `hilclaw/timings_tool.py` (`STEPS_OF` in place of `STEP_OF`; the unit rule; `units_differ`), `hilclaw/verdicts_tool.py`, `hilclaw/s6_metric.py` (`ns` only). `harness/timing_finding.py` needs no code change because it reads `run_identity.STEPS`; with `s6_metric` in slice 1 this is the file that leaves slice 1 (the task's cap of 5 documents and 5 modules). About 220 changed code lines, docstrings included, 5 modules.
2. **The writers and the remaining readers**: `hilclaw/run_identity.py` (`step_of` returns the v3 values), `hilclaw/run_result.py` (`UNITS` from `UNITS_OF` of the v3 values), `hilclaw/run_tool.py` (the conversion of decision 5; the mock `ns`), `hilclaw/targets.py` (the factor on `Target`; `virtual_npu` `cycles` and 3; `cpu_standin` `ns` and 1; the module docstring), `hilclaw/spec_feedback.py` and `hilclaw/model_run_binding.py` (decision 4), and the docstrings of `hilclaw/harness/timing_finding.py`. Every target switches in this one commit (**owner**: "모든 대상에"). About 250 changed code lines, 7 files.

### 7. The StepValues states

- `sim_run_timing_v3` and `board_run_timing_v3`: **`defined`**, fixed by this record's decision 2.
- `sim_run_timing_v2` and `board_run_timing_v2`: **`not used`**, linking this record: once slice 2 lands no target calls a step under them (StepValues: "the contract no longer calls a step under it"). The readers keep reading their lines (**owner**: "읽는 쪽은 v2와 v3를 모두 읽는다"), which the state does not forbid. The states are this record's and do not change with the slices (as ADR-0183 decision 9 has it).

### A-13 reading

Read under the owner's decision D23 (CLAUDE.md A-13; DRIVER §3 "승인된 열린 목록").

- **The approved open list used is "측정 단위"** of DRIVER §3 (**owner**, HQ-0090 (a)·(가), 2026-11-05). Its first values `ns` and `cycles`, the two v3 `step` values, `cpu_standin`'s `ns`, the meaning of `virtual_npu`'s `cycles` and the reach of the list (`intervals` and `resolution`, not `memory_bytes`) are the owner's. **The frame change** — `unit` from one closed value to the list, under new `step` values — **is the owner's**, made with the list's registration.
- **What this record adds as detail**: the place of the unit (on the target), the factor 3 and the order of the conversion, the readers' rules (both values per point, the unit rule per line's value, an attempt with both, `units_differ` and its place in the order), the StepValues states and the slices.
- **The other files**: no member of `STATE.json`, `instance.json`, a spec or `artifacts.json`, no event kind, no member of the envelope and no layout version changes; the result's member list is ADR-0183's; `memory_bytes` is untouched. The build-log names keep their form with two more `<step>` values. `units_differ` is a tool-layer name (ADR-0140 decision 3). `Target` and its factor are package source, no data-plane value (ADR-0193 decision 3).
- **No BLOCKED reason remains**: the frame change is the owner's, the values are the owner's list's, and the rest is delegated detail.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 3 | The unit on each point's measuring means | Every means measures in `ns`; the one other unit is a target's; nothing reads the place. Reachable later in package source. |
| 3 | A member of `hw_profile` or `instance.json` holding the unit | A frame change no answer made (ADR-0193 decision 3). |
| 4 | Reusing `shapes_differ` for two units | Its meaning is "not about the same quantity"; two units of one quantity are another cause, and the evaluator could not tell them apart. |
| 4 | Converting one side to the other's unit before comparing | The factor is a target's check value, not a fact of the line; the owner limits comparison to one unit. |
| 4 | Refusing an attempt that holds lines of both values | It leaves a run spanning slice 2 with no reading; ADR-0178 decision 3 reads both for the same reason. |
| 4 | Readers reading v3 only | Against the owner ("v2와 v3를 모두 읽는다"); a log written before slice 2 would lose its measurements. |
| 5 | Factor 1000 or 10⁶ | Reads as a decimal time unit, so a reader that confuses units would not be caught. |
| 5 | Measuring cycles from a counter | Not the owner's definition ("자기 ns에 고정 배수를 곱한"), and a counter would be a fact of the host, not of the virtual NPU. |
| 5 | Converting before the judgement | `zero_interval` and the replay are defined on the harness's `ns` report (ADR-0063 decision 3); the outcome must not depend on the factor. |
| 6 | One slice | 11 or more non-test files with the documents; over the cap. |
| 6 | Writers first | A v3 line would be refused by the v2-only readers in between. |

## Consequences

- **PLAN P3-3** stays unchecked: after slice 2 its "measurement unit" difference exists; the item also waits for the follow-up of HQ-0091's answer (ADR-0193 decision 8).
- **Until slice 2 lands** the run tools still write v2 results under the v2 values; the StepValues rows already say `not used`, which describes the contract (as ADR-0183 Consequences has it for its slices).
- **Runtime acceptance items**: none. Every fact here is a statement of records and code a test with constructed `events.ndjson` lines checks (D16, D22).
- **Less exact, not edited** (slice 2 fixes the docstrings it touches; the list is what a search of the records named here and of `hilclaw/` found, not claimed complete):
  - ADR-0193 decision 3 ("The unit stays `ns`"; `unit` among what O3 would ask), decision 4 (the table row "`ns` until O3 is answered", the "Measurement unit" bullet: "`run_result.UNITS` still refuses anything else"), decision 8's P3-3 row ("plus 1 small one on answer O3") and decision 9's O3 and coverage row ③.
  - ADR-0183 decision 4 (`unit` "string: `\"ns\"`" — true of v2 only; "the value list is closed until the owner opens it"), decision 7 ("the four values of decision 2 and no other"), decision 8 ("No reader keeps accepting the retired values" — still true of the six retired values, but the run-line readers now read two values per point; "`unit` exactly `\"ns\"`" — of v2 lines), Consequences ("Owner's later decision (⑤)") and Boundaries ("the open list of units").
  - ADR-0140 decision 3 (one `step` per point; the six kinds), ADR-0184 decision 2 and ADR-0189 decision 2 (`board_run_timing_v2` as the one step of a measurement), ADR-0194 decision 4 (`resolution` "in `ns`" — of its targets) and decision 5 ("`timings.compare` reads one point's value only" — one point's two values).
  - Docstrings: `hilclaw/targets.py` ("has the unit `ns` (until the owner answers whether another unit is admitted)"), `hilclaw/run_result.py` (`UNITS`, "`\"ns\"` alone"), `hilclaw/run_tool.py`, `hilclaw/spec_feedback.py` (the step `STEP_BOARD_RUN`), `hilclaw/harness/timing_finding.py` ("those of the v2 result").

## Boundaries (not decided here)

- **Owner-only or asked**: the form of a GPU or NPU memory figure at vendor targets ((가) leaves `memory_bytes` as it is; ADR-0194 decision 4; asked separately if needed); which execution is which point (HQ-0095); the oracle, tolerance and data types at `virtual_npu` and its `correctness.check` and instance start (HQ-0091, answered 2026-11-05; its own follow-up task); units other than `ns` and `cycles` (each a §9 ADR naming the list); the check of PLAN P3-3, which also waits on that follow-up.
- The result files `sim.json` and `board.json` (ADR-0063 decision 10); a cycle counter of any real device; `profiler.collect`.
- Any change to an accepted record, to `orchestration/` or to `catalog/`.

## References

- Owner: HQ-0090 and HQ-0078 in `PROCESS/STATE.json`; DRIVER §3 "승인된 열린 목록" ("측정 단위"); D6, D23, D27.
- [Requirements](../Requirements.md): FR-10, NFR-6; rows OD-8, OD-18, OD-32, OD-33. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-8, § OD-18, § OD-32, § OD-33; [StandardScenarios](../StandardScenarios.md); [StepValues](../StepValues.md).
- Records: ADR-0001, ADR-0011, ADR-0062, ADR-0063, ADR-0074, ADR-0078, ADR-0100, ADR-0101, ADR-0103, ADR-0104, ADR-0108, ADR-0120, ADR-0140, ADR-0178, ADR-0183, ADR-0184, ADR-0189, ADR-0193, ADR-0194.
- Code read: `hilclaw/run_identity.py`, `run_result.py`, `run_tool.py`, `targets.py`, `timings_tool.py`, `verdicts_tool.py`, `s6_metric.py`, `spec_feedback.py`, `model_run_binding.py`, `layout.py`, `check_standing.py`, `harness/timing_finding.py`; `orchestration/agents/evaluator.md`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3, §5, §6 D27, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-3; task T-0549.
