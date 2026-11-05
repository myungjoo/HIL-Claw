# ADR-0199: The version-3 spec of a compile-settings round — `spec.write` takes `flags` in place of `techniques` and composes the kernel reference itself, writes the version-3 document with no technique and no feedback, answers a request of the other kind's form with `invalid_request`, and the technique-selector writes it in step 6 while the Round-Manager skips step 8 (slice 2b of ADR-0198, second half; part of OD-32, OD-6 and OD-23 for this kind)

## Status

- **Accepted on 2026-11-05** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Two kinds of content.** What [ADR-0198](ADR-0198-od32-compile-settings-candidate-kind.md), the owner's answers it records (HQ-0088, HQ-0089) or another accepted record says is **cited** and not restated beyond what the decisions below need. **Everything else is this record's own**: the request form, the composed document outside `task.build`, the checks that apply and their order, the answer to a request of the wrong form, the two new entries of `hilclaw.spec_file`, the report line and the orchestration text.
- **Answers**, for a run whose `instance.json` states `candidate_kind` `compile_settings` only: the points ADR-0198 decision 3 and decision 8 (row "`spec_tool`", slice 2b) leave to this slice. Of **OD-32**, how the selection role has the spec written; of **OD-6**, the request and the members of the version-3 spec outside `task.build`; of **OD-23**, what writes that spec and when. **No status word of any OD changes.**
- **Session entry check** (CLAUDE.md), on 2026-11-05 at `main` `ed354868`: open PRs — none; no open `nightly-failure` issue; no item of `PROCESS/RuntimeAcceptance.md` whose `상태` is `실패`; issue #4 last updated 2026-10-01, #5 2026-11-05, #7 2026-09-07, #8 closed. Unresolved HQs: HQ-0081, HQ-0095, HQ-0096, HQ-0097; none is crossed or anticipated (Boundaries).
- **Code** lands with this record (decisions 2 to 6). No `claude` process was started and nothing was built or run in a container (D16). The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Cited from ADR-0198**: decision 2 (the kernel of a compile-settings round is the run's own round-0 coder attempt `(0, 1, 1)`; naming it is the selection role's rule, and whether it has a kernel is checked at evaluation), decision 3 (the `technique-selector` chooses the flags and has the version-3 spec of `(round, 1, 1)` written in step 6; step 8 is not taken; steps 9 to 12 follow on the same tuple), decision 4 (the version-3 form, its place `coder/…/spec.json`, an empty `output/`), decision 8 (rows "`spec_tool`", "`coder_call`" and "`spec_feedback`": `spec.write` composes a v3 spec on the technique-selector's request, `coder.run` and `spec_feedback` refuse v3).
- **Cited from earlier records**: [ADR-0138](ADR-0138-od6-first-case-round-zero-spec.md) decisions 2 and 3 and [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md) decisions 1 to 3 give the request `run_id`, `round`, `candidate` 1, `attempt` 1 and, for a round ≥ 1, `techniques`, the checks 1 to 12 and the composed version-2 document; [ADR-0132](ADR-0132-od23-first-case-selection.md) decisions 2, 4, 6 and 7 and [ADR-0171](ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md) decisions 2 to 6 give the selector's record, its `techniques:` line and step 8; [ADR-0139](ADR-0139-od18-first-case-turn-session-permissions.md) and [ADR-0146](ADR-0146-od18-first-case-caller-check-hook.md) decision 3: a sub-agent holds the tools its `tools` line names; [ADR-0029](ADR-0029-od8-spec-file.md): the written form and the write-once name.
- **Observations** at `ed354868`: `spec.write` reads a version-2 `instance.json` as its version-1 twin (T-0554) and writes version 2 only; `catalog.read`, `cases.lookup` and `case.write` refuse a run whose kind is not `c_kernel` with `run_file_unsupported`; `hypotheses.write` reads no case for a record with an empty `cases_read`; `correctness.check`, `sim.run` and `board.run` build a version-3 attempt from the named kernel (T-0555); `hilclaw.spec_file.final_name` and `write` validate version 2 only.

## Decision

### 1. Scope

This record decides only what ADR-0198 leaves to slice 2b for `spec.write` and the two orchestration files. It adds no member, value or version to any file (A-13 reading).

### 2. The request

- **A version-3 request is `{"run_id", "round", "candidate": 1, "attempt": 1, "flags": [...]}`** with `round` ≥ 1: `flags` takes the place of `techniques` and is an array of strings of 1 to 255 printable ASCII characters (the form of `task.build.flags`, ADR-0198 decision 4), possibly empty, repeats allowed, with no length bound. The tool keeps the order. *Why repeats*: a compiler argument can be given twice on purpose (`-mllvm` before each of two options).
- **The kernel reference is composed by the tool**: `kernel_round` 0, `kernel_candidate` 1, `kernel_attempt` 1, ADR-0198 decision 2's rule for the selection role. *Why*: the selector cannot then name a version-3 attempt, a missing tuple or a later round; a later design that names another attempt adds a request member then.
- **Round 0 is unchanged**: a round-0 request holds neither `techniques` nor `flags`, in every run, and gets the version-2 bring-up spec (ADR-0138).

### 3. The composed document and the checks

- **The document** is the round-0 document of ADR-0138 decision 2 with `schema_version` 3, `id.round` the request's round and `task.build` `{"candidate_kind": "compile_settings", "flags": <the request's>, "kernel_round": 0, "kernel_candidate": 1, "kernel_attempt": 1}`, placed after `task.objective`. `guidance.techniques` and `feedback.attempts` are empty and there is no `feedback.base`. *Why no feedback*: no coder reads this spec (ADR-0198 decision 3), and `spec_feedback` refuses a version-3 attempt (decision 8), so feeding back over a round that holds one would fail. The encoding is ADR-0138's.
- **The checks** of ADR-0151 decision 3 apply in their order, with these changes for a `flags` request: check 1 also refuses `flags` with round 0, both `techniques` and `flags`, and a flag outside its form; a new check between 3 and 4 holds the form against the run's kind (decision 4); checks 4 to 6 apply unchanged (the document needs the instance's `candidates_per_round` 1, a covered `op_signature` and an `objective` as a version-2 one does); checks 7 (catalog) and 8 to 10 (feedback) are not made, so neither the catalog nor `events.ndjson` nor an earlier attempt is read; check 11 uses `parse_versioned` and `final_name_versioned` (decision 6); check 12 uses `write_versioned`. The kinds and their order are otherwise unchanged.
- **Not checked by `spec.write`**: that attempt `(0, 1, 1)` exists, is a version-2 attempt or has a compiled set. *Why*: ADR-0198 decision 2 puts that check at evaluation, where the tools refuse with the existing kinds of a missing or unreadable kernel.
- **No `output/`** is created; the only file written is the spec.

### 4. A request of the other kind's form

- **`techniques` in a round ≥ 1 of a `compile_settings` run, and `flags` in a `c_kernel` run**, are refused with **`invalid_request`**, after the read of `instance.json` (check 3) and before check 4; the message names the file, the kind and the member the run takes. Nothing is written. *Why `invalid_request`*: the run is readable and the tool reads it; the request has the wrong form for it, and the selector or the `coder-driver` can correct it. `run_file_unsupported` would say the file is unsupported, which it is not. No new kind is added.
- **`flags` with round 0** and **neither or both members with round ≥ 1** are `invalid_request` at check 1, before the data root is asked: they are wrong in every run. A request with neither member keeps today's message, which names `techniques`.

### 5. The orchestration text

- **`orchestration/agents/technique-selector.md`**: its `tools` line gains `mcp__hilclaw__spec_write` and nothing else. In a run whose instance (from `mcp__hilclaw__instance_read`) states `candidate_kind` `compile_settings`, a new section "A compile-settings run" takes the place of the case lookup and of the choice of techniques: the selector calls neither `mcp__hilclaw__cases_lookup` nor `mcp__hilclaw__catalog_read` (both refuse such a run), gives the record an empty `cases_read`, gives no `techniques:` line, and after the record exists chooses the flags and calls `mcp__hilclaw__spec_write` with the request of decision 2. On `invalid_request` it corrects and sends again; on any other kind it ends. **The report line** is exactly one line `spec: written` when the call returned `{}`, or `spec: <kind>` with the failure kind of its last request, and none when no such request was made. Every rule of a `c_kernel` run is unchanged; the prohibition "Request no check, measurement, spec or coder call" keeps its words and gains the one exception.
- **`orchestration/round-manager.md`**: step 6 says that in such a run the selector also has the spec written and reports a `spec:` line, and step 8 is not taken. Step 8 gains a last paragraph: in such a run (as entry step 6 read `instance.json`) only that paragraph of the step applies: its coder call is not taken and nothing is delegated; when the selector's report holds exactly one line `spec: written` the Round-Manager goes on to step 9 with the tuple `(round, 1, 1)`, and otherwise reports that no spec was written and comes to the stop, asking for no repair. The stop paragraph names that path. Steps 7 and 9 to 12, the round-0 steps, the closing steps (where `case.write`'s refusal lets the round go on) and every `c_kernel` path are unchanged. *Why the kind from `instance.json` and not from the report*: a `c_kernel` round must never skip the coder call because of a stray line.
- *Why `spec_exists` stops*: as in step 8 for a `c_kernel` run (ADR-0172 decision 2), a spec that was already there is not known to be this turn's choice.

### 6. `hilclaw.spec_file`

- **Two entries beside the strict ones**: `final_name_versioned(data_root, document)` and `write_versioned(data_root, content)`, the rules, steps and errors of `final_name` and `write` with `spec.validate_versioned` and `parse_versioned` in the place of `spec.validate` and `parse`. `parse`, `final_name` and `write` keep version 2 for every existing caller. *Why opt-in*: ADR-0198 decision 8's choice for the readers; no caller is widened by accident.

### A-13 reading

- **The frame elements used are exactly HQ-0089's** as ADR-0198 records them: the spec `schema_version` 3 and its `task.build` members, `instance.json` `candidate_kind`; the value `compile_settings` is from the approved open list "후보 종류" (DRIVER §3), and this record adds no value to it.
- **Nothing else changes**: no member, value or version of `instance.json`, the spec, `build.json`, results, `step`, `events.ndjson`, `artifacts.json` or `STATE.json`; the layout version is unchanged. The request member `flags` and the report line `spec: …` are names of a tool's request and of an agent's report, not of a data-plane file, as ADR-0138 and ADR-0171 read their own. No new failure kind is added.
- **No BLOCKED reason remains**: no new dependency (Python, the standard library), no unapproved schema change, no owner part left undecided.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The request names `kernel_round`, `kernel_candidate`, `kernel_attempt` | The selector could name a version-3 or missing attempt; ADR-0198 fixes round 0 as the rule |
| 2 | A separate tool for the version-3 spec | ADR-0198 decision 8 names `spec.write`; one writer of `spec.json` keeps one place for its checks |
| 3 | Feedback over earlier attempts in the version-3 spec | No coder reads it; `spec_feedback` refuses a version-3 attempt |
| 4 | `run_file_unsupported` or a new kind for the wrong form | The file is supported; the request is what is wrong |
| 5 | The Round-Manager decides from the report alone | A stray line could skip a `c_kernel` coder call |

## Consequences

- **Registers are not edited here**: the links of this record in `Requirements.md`, `OpenDecisionProposals.md` and the StandardScenarios scenario come with T-0557 (ADR-0198 slice 4, the landing).
- **Runtime acceptance**: none beyond ADR-0198's item (a live round ≥ 1 of a `compile_settings` run with no coder call), which T-0557 hands to `PROCESS/RuntimeAcceptance.md`. That a live technique-selector follows the new section and that a live Round-Manager skips step 8 belong to that item.
- **Less exact, not edited**: ADR-0151 decision 3's table (check 1 and the new check between 3 and 4 for `flags`) and ADR-0171 decision 6 ("the Round-Manager delegates the coder call in step 8") for a `compile_settings` run; the code docstrings are updated where this slice made them untrue.

## Boundaries (not decided here)

- A kernel from another run or another attempt than `(0, 1, 1)`; more than one candidate per round of this kind.
- Cases, the S6 metric and model runs of a compile-settings run; vendor-language kernels and quantization settings (D27 ①).
- HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0097.

## References

- Owner: HQ-0088, HQ-0089 in `PROCESS/STATE.json` (as ADR-0198 records them); D6, D23, D27.
- Records: ADR-0001, ADR-0029, ADR-0132, ADR-0138, ADR-0139, ADR-0146, ADR-0151, ADR-0171, ADR-0172, ADR-0198.
- Code: `hilclaw/spec_tool.py`, `hilclaw/spec_file.py`, `hilclaw/spec.py`, `hilclaw/instance.py`, `hilclaw/run_file_tools.py`, `hilclaw/spec_feedback.py`, `hilclaw/coder_call.py`, `hilclaw/attempt_kernel.py`; `orchestration/round-manager.md`, `orchestration/agents/technique-selector.md`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3, §5, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-6; task T-0556.
