# ADR-0136: The model of a first-case coder call — the `instance.json` member `coder_model`, a full Claude model name; the start puts in the full name of Opus when none is given, and the coder call reads the member and refuses a run that states none (owner answer HQ-0041 part 1; part of OD-8 and OD-23, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-21** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Three kinds of content.**
  - **Owner**: the answer to HQ-0041, part (1), and the owner's note on it, quoted in Context as **O1** and **O2**, and the original #5 A-8 item (**O0**). They are not subject to the objection window below.
  - **Cited**: what a requirement, an accepted record, a code docstring or the Claude Code documentation says, with its source named. The two documentation pages were read on 2026-10-21 (**F1**, **F2**). Nothing was tried on any machine (D16).
  - **This record's own**: everything else, namely the scope, the name, place and form of the member, its rule of validity, the reading of "Opus" as a full name, how the start fills it in, the read at the call with its order and its kinds, and every weighing. **The owner has not confirmed these.**
- **The owner-sentence search.** Searched: the body of #5 and the 41 of its 224 comments that carry no "posted by driver" marker; the bodies and comments of #4, #7 and #8. Terms: opus, sonnet, `--model`, coder model, 코더 모델. Found: O0, O1, O2, and the B-6 "Design consequences" line "shapes A-8 (Opus vs Sonnet assignment within the plan)", which is the integrator's derivation (C-7) and is not read further. #4, #7 and #8 hold none.
- **Answers**, **for the runs of ADR-0120 decision 1 only**, part of **OD-8** (one more member of `runs/<run_id>/instance.json`) and part of **OD-23** (the model of the coder process of ADR-0126, an open part of its start). **OD-8, OD-23 and every other OD keep their status.** No sub-question is registered.
- **The one data-plane addition** is the member of decision 2. It is a member that may be absent, so `schema_version` stays `1` (decision 4). The owner asked for the record in `instance.json` (O1). **No other member, file, kind of event or version changes.** It is a record, not code.
- It builds on [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 2, 4, 6), [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decision 2) as [ADR-0124](ADR-0124-od23-round-manager-run-file-access.md) (decision 3) widens it, [ADR-0025](ADR-0025-od8-instance-file-write.md) (decision 2), [ADR-0076](ADR-0076-od8-instance-start-required-members.md) (decisions 1 to 3), [ADR-0115](ADR-0115-od8-instance-start-performer.md) (decision 2), [ADR-0049](ADR-0049-od8-coder-call-isolation-means.md) (decision 1, slice (d)), [ADR-0120](ADR-0120-od8-first-state-file.md) (decision 1) and [ADR-0126](ADR-0126-od23-coder-call-issuer.md) (decisions 3, 5, 7). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. For this record's own choices the owner may object within 7 days of that notice; an objection creates a task that reverts them and the edits made with them.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **O0** — #5 body, item A-8 (owner-only, https://github.com/myungjoo/HIL-Claw/issues/5): "코더(`claude -p`)에 Orchestrator와 다른 모델을 기본 지정할지(예: 코더=상위 모델 vs 동급), budget의 토큰 요소를 Orchestrator/코더 합산으로 볼지 분리 한도로 볼지."
- **O1** — the answer to HQ-0041, 2026-10-20 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368), point 1: "**Coder model**: an instance parameter. When the instance names none, the start applies Opus and records it in `instance.json`."
- **O2** — the same comment: "two design points stay with the record: the form of the recorded model value (alias or full model name), and which usage counts as tokens (input, output, cache)." Point 2 there (the token axis) is **not** taken up here.
- **NFR-5**: "코더에 별도 모델 지정이 가능해야 하며 …". **C-7 ②**: Claude Code is used "with a **Max subscription**" and no separate API cost.
- **F1** — the CLI reference (https://docs.claude.com/en/docs/claude-code/cli-reference), the `--model` row: "Sets the model for the current session with a model alias such as `sonnet`, `opus`, `haiku`, or `fable`, or a model's full name. Overrides the `model` setting and `ANTHROPIC_MODEL`".
- **F2** — model configuration (https://docs.claude.com/en/docs/claude-code/model-config):
  - "**`opus`** | Uses the latest Opus model for complex reasoning tasks". The aliases "resolve to the newest version on the Anthropic API and to an earlier version on some other providers"; the table row "Anthropic API | Opus 5.5".
  - "Aliases point to the recommended version for your provider and update over time. To pin to a specific version, use the full model name, for example `claude-opus-5-5`".
  - "`default` … **Pro, Max, Team, Enterprise, and Anthropic API**: defaults to Opus 5.5"; and "Earlier versions resolve these aliases to older models".
  - "If you set the model with the `--model` flag … Claude Code doesn't check it up front, and a mistyped value produces There's an issue with the selected model on the first request."
  - "When the requested model has a scheduled retirement date or is automatically remapped to a newer version, Claude Code shows a warning that names the requested model"; with `--output-format json` and `stream-json`, "read the actual model from the `modelUsage` field of the result message".
  - "Fable models, Opus 5.5, Sonnet 5.5, and Opus 5 run with safety classifiers"; for Opus 5.5, "biology-flagged requests re-run on Opus 5, and cybersecurity-flagged requests re-run on Opus 4.8"; "After a fallback, the session continues on the fallback model".
- **What is open** (cited): ADR-0126 Consequences, "Waiting on the owner's #5 A-8": "the coder's model (NFR-5 requires that one can be named; which one, and whether a default applies, is A-8)"; ADR-0049 Boundaries: "the model and permissions of `claude -p`".
- **What exists** (code, as observation only):
  - `hilclaw.coder_call.call(request, *, source, runtime)` performs the call of ADR-0126 decision 3 with the container start behind the seam `runtime.run(scratch_root)`. It "writes no prompt text and no `claude` flag". It reads no `instance.json`.
  - `hilclaw.instance` defines thirteen top-level members and passes over any other.
  - `hilclaw.instance_start.prepare` fills in `n_max` when absent (ADR-0076 decision 2).
  - **Name search on 2026-10-21** of `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/`: `coder_model` and `coder_model_not_stated` occur nowhere. `"model"` occurs once, in `tests/test_turn_definition.py`, about an agent definition.

## Decision

A sentence is **cited** when a source is named with it, and **owner** when it renders O0 to O2. Every other sentence is **this record's own**.

### 1. Scope

- **The runs of ADR-0120 decision 1**, whose `instance.json` the start function of ADR-0115 writes, and **their coder calls** of ADR-0126 decision 3: the model the coder's `claude -p` runs with. Nothing else.
- **Outside**: the model of every other agent (the Round-Manager, the coder-driver, the evaluator, the selection); the token axis and which usage counts (O1 point 2, O2); every other point of slice (d).

### 2. (a) The member

- **The member is `coder_model`, a top-level member of `instance.json`.** It states the model the instance's coder calls run with (decision 7).
- **Not `model`**: in this system "model" names the neural network the instance optimises (S0 step 2; OD-9). **Not inside another member**:
  - inside `hw_profile` raises the version (cited: ADR-0018 decision 2) and is no property of the hardware;
  - an object `coder` with one member would be shaped by members that do not exist (the reason of ADR-0032 decision 3).

### 3. (b), (c) The form of the value, and what a valid value is

- **The value is a full Claude model name, not an alias.** The form is a *str* of at most 64 characters that begins with `claude-`, continues with one or more ASCII lowercase letters, digits and `-`, and does not end with `-`. Examples: `claude-opus-5-5`, `claude-sonnet-4-5-20250929`.
  - **Not values**: an alias (`opus`, `best`) or the special value `default`, a name with a context suffix (`claude-opus-5-5[1m]`), a provider name such as an inference-profile ARN, the empty string, and anything that is not a *str*.
- **Why a full name** (Alternatives):
  - **The value is the model the call requests, not a proof of the model that ran.** F2 says a requested model may be "automatically remapped to a newer version", and a flagged request may "re-run on" another model, after which "the session continues on the fallback model". What actually ran is read from `modelUsage` (F2), and recording it is left to a later record (Boundaries).
  - Within that limit, the file states "What the instance was started with" (cited: ADR-0004), and S10 reproduces from it. F2 says an alias "update[s] over time" and resolves by provider and version, so `opus` would not even state which model was requested. Two calls of one run could request two models without any change to the file.
  - The full name is the one F2 gives "To pin to a specific version".
  - C-7 ② limits the provider to the Max plan's own. So the names of other providers are left out.
- **The check is of the form only, not against a list of offered models.**
  - A list would go stale. The file is never rewritten (cited: ADR-0018 decision 2), so a source with a shorter list would make a run's whole file invalid in the middle of the run.
  - Whether a name is offered can only be learned from the provider (F2), and a validator makes no network call.
  - **The cost:** a misspelt name of the right form (`claude-opsu-5-5`) is valid and stays for the life of the run. F2: Claude Code "doesn't check it up front", and a mistyped value fails "on the first request". What the coder call then reports is decision 6's last row.
- **A present member must be valid.** A `coder_model` that breaks this decision makes the file invalid in the sense of ADR-0018 decision 2: no member of it is used. This is the rule of ADR-0032 decision 4 and its predecessors.

### 4. (d), (e) The default at the start; a file without the member; the version

- **Owner** (O1): when none is named, the start "applies Opus and records it in `instance.json`".
- **The value that stands for Opus is the full name of the Opus model that F2 lists for the alias `opus` on the Anthropic API.** On 2026-10-21 that is `claude-opus-5-5` (F2: "Opus 5.5"; "for example `claude-opus-5-5`"). It is also the model F2 gives as `default` for the Max plan of C-7 ② ("Pro, Max, …: defaults to Opus 5.5").
  - This record reads O1's "Opus" as the model family, not one version.
  - The code task that sets the package's constant cites F2 with the date it was read. A later task may replace the value with a newer Opus name in the same way, without a new record.
  - **A file once written keeps its value.** A later change of the constant changes no file (as ADR-0023 decision 4 says of `N_MAX_DEFAULT`).
- **How the start fills it in** (for the instances of ADR-0076 decision 1):
  - It takes the step where it fills in `n_max` (cited: ADR-0076 decisions 2, 3; ADR-0115 decision 2): after validity and scope, before the required set.
  - **A value the user gives is never replaced.** A given value that breaks decision 3 makes the content invalid. An invalid content is not written (cited: ADR-0025 decision 2), and the start reports it.
  - After the fill-in, `coder_model` is never missing, so the report order of ADR-0076 decision 3 is unchanged.
  - **How the start learns of a given value is not decided here**, and neither is how it learns of a given id (HQ-0032).
- **The member may be absent from a valid file, and `schema_version` stays `1`.** This is the first of the two choices ADR-0018 decision 2 leaves to the record of a member. **No reader that passes over it acts wrongly**: no source starts a coder process yet (slice (d) does not exist), and the one reader that needs the value is the coder call of decision 5, so slice (d) lands no earlier than the read of slice 3 (Consequences). A file written before this record, or by a writer other than the start, may lack it.
- **A valid file without the member states no coder model.** No reader substitutes a value, not the default included. Only the start applies the default, and it records the value (O1).

### 5. (f) How the coder call learns the model

- **The request stays exactly as ADR-0126 decision 3 fixes it.** `run_id`, `round`, `candidate` and `attempt`; no member is added.
- **The function reads the run's `instance.json` at each call**, under the data root from the data-root source. It reads the file as a whole, as `hilclaw.instance.read` does (cited: ADR-0018 decisions 2, 4). Nothing is kept between calls (cited: ADR-0010 decision 7).
- **The read comes right after `no_data_root` and before `output_exists`.** It concerns the run as a whole, which comes before the tuple, as ADR-0076 decision 3 puts the run-wide members first. It is a read, so it stays before `no_container_runtime` and creates and consumes nothing (cited: ADR-0126 decision 3).
- **Failure kinds, in this order:**
  1. `run_file_missing`, `run_file_unreadable`, `run_file_invalid`, `run_file_unsupported`, for a missing, unreadable, invalid or other-version `instance.json`. These are the reserved kinds of ADR-0019 decision 2. **This record widens that decision's "only at the lookup or the selection" to this read**, as ADR-0124 decision 3 widened it to `instance.read`. The property it states holds here too: such a call appended no line, called no backend, ran no step and consumed nothing. Under form (B) of ADR-0126, where the function is no tool, using the four with the same meaning is this record's reading, as ADR-0126 decision 3 reads `invalid_request` and `no_data_root`; this also widens ADR-0019's "Only a tool function raises them".
  2. **`coder_model_not_stated`** (new), for a valid file without the member. Not one of the four, because the file is valid. No other kind says it.
- **The rest of decision 3's order is unchanged.** A later code slice inserts these kinds into `FAILURE_KINDS`.

### 6. Walk-through, and a model no longer offered

| Situation | What follows |
|---|---|
| A start with no model named | The start fills in `"coder_model": "claude-opus-5-5"` (decision 4) and writes the file. The file states it |
| A start naming `claude-sonnet-4-5-20250929` | Valid by decision 3. Written as given, never replaced |
| A start naming `opus`, `claude-opus-5-5[1m]`, `""` or `5` | The content is invalid, is not written and is reported (cited: ADR-0025 decision 2). No default stands in |
| A coder call; the file holds `claude-opus-5-5` | The read passes. The function hands the value to the container start, and the coder's `claude -p` runs with it (decision 7) |
| A coder call; a valid file lacks the member (for example, one written before this record) | `coder_model_not_stated` before anything is created. No coder runs, and no default applies |
| A coder call; `instance.json` missing, unreadable, invalid or of another version | The matching `run_file_*` kind. Nothing is created |
| The named model is no longer offered under the user's plan when the call starts | **This record decides only this:** the call passes the recorded value and no other. It adds no fallback and no alias, and does not rewrite the file. What `claude -p` then does (an error, or a remapping, F2) is item (xxxii). If it exits non-zero, the call fails `coder_not_ended` (cited: ADR-0126 decision 3) |

### 7. (g) What the value is for

- **It is the model the coder's `claude -p` inside the container is asked to run with.** How it reaches that process is slice (d)'s: a flag (F1), an environment variable, or the seam `runtime.run`. So is anything about a model other than the requested one running (Boundaries).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| (a) | `model` | Collides with the network model of S0 step 2 and OD-9 |
| (a) | Inside `hw_profile` | Raises `schema_version` (ADR-0018 decision 2). The coder model is no property of the hardware |
| (a) | An object `coder: {model}` | Shaped by members no record has. A later member would change its form, which raises the version |
| (b) | An alias (`opus`), which F1 accepts | Resolves "over time" and by provider (F2), so the file would not even say which model was requested, and one run could request two. A full name states the requested one, though what ran can still differ (F2). The alias's gain, that the call still runs after a model is withdrawn, costs reproducibility (FR-13, S10) |
| (b) | Either form | Two kinds of statement in one member. A reader could not tell a pinned value from a moving one |
| (b) | The start resolves an alias to a full name | The package would need an alias table, which F2 says changes. The user can give the full name |
| (c) | A list of offered names | Goes stale. A shorter list in a later source would make a written file invalid in the middle of a run, and offering is per account (F2) |
| (c) | Any non-empty *str* | Lets an alias or a provider ARN in. The written value could then move (point (b)) |
| (e) | The call applies the default for a file without the member | The run would run on a model it never recorded, against O1's "records it" |
| (e) | Required member, `schema_version` 2 | Every file and reader of today becomes another version before a first run (OD-11). The start already fills it in |
| (f) | A request member `model` | Changes ADR-0126 decision 3, and lets the coder-driver choose a model the run did not record |
| (f) | New kinds for the four unreadable-file cases | The same situations already have reserved names (ADR-0019; ADR-0124 decision 3) |

## Consequences

- **Code slices it enables** (code mode, later tasks, each within the D4 cap; tested with stubs only, D16):
  1. `hilclaw/instance.py`: the member by decision 3, a reader `coder_model_of`, the docstring; with `tests/test_instance.py`.
  2. `hilclaw/instance_start.py`: the fill-in of decision 4, with the constant cited from F2; with `tests/test_instance_start.py`. It comes after slice 1, whose check it applies to a given value. **It must not overlap open PR #186** (`hilclaw/start_instance.py`) while that PR is open.
  3. `hilclaw/coder_call.py`: the read and the kinds of decision 5, and the hand-over of the value to the seam (the form of the hand-over is the code task's); with `tests/test_coder_call.py`. It comes after slice 1, and slice (d) comes after it (decision 4).
- **Less exact, not edited** (D18 hold; found by a search of `ARCHITECTURE/decisions/` and `hilclaw/` for "coder model", "model and token", "model and permissions"; not claimed complete):
  - ADR-0126 Consequences, "Waiting on the owner's #5 A-8" (the model part), and Boundaries, "model and token budget (#5 A-8, owner)"; its decision 3 table, which gains the kinds of decision 5.
  - ADR-0049 Boundaries, "the model and permissions of `claude -p`".
  - ADR-0032 Context and Boundaries, "the token axis and the coder model (#5 A-8, owner)"; the same words in ADR-0033 (Context, Boundaries), ADR-0018 (Context, Boundaries), ADR-0029 and ADR-0127 Boundaries.
  - ADR-0023, ADR-0028, ADR-0031, ADR-0034 Boundaries (the other members of `instance.json`).
  - ADR-0019 decision 2, "Only a tool function raises them, and only at the lookup or the selection".
  - ADR-0076 decision 3 and ADR-0115 decision 2, where the order of the start gains one fill-in.
  - The `hilclaw/coder_call.py` docstring stays true until slice 3: it lists the kinds the code has, and the call reads no `instance.json` yet.
- **Runtime acceptance items** (D16; the driver raises their HQ), numbered after ADR-0135's (xxix) and (xxx):
  - **(xxxi)** The coder's `claude -p` inside the container, given the recorded full name in the form slice (d) chooses, runs on that model under the user's Max plan; and whether the model it actually ran on, after any remapping or content-based fallback (F2), can be read back, for example from `modelUsage`.
  - **(xxxii)** What the coder's `claude -p` does when the recorded full name is no longer offered under the plan, or is remapped (F2): whether it exits non-zero, runs on another model, or warns, and whether its output tells which.
- **UsageCases and StandardScenarios**: no sentence becomes false.
- **A-13 reading.** Document mode; no code, test, setting or dependency changes.
  - **One data-plane addition**: the top-level member `coder_model` of `instance.json`. It may be absent, so by ADR-0018 decision 2 the version stays `1`. The set of valid version-1 files becomes narrower, as with ADR-0032. No such file exists yet.
  - **The owner authorised it** (O1: "records it in `instance.json`").
  - No other member, no other data-plane file, no key record and no event kind changes. `coder_model_not_stated` names a failure of the call, not a value of the data plane (cited: ADR-0126 decision 3).

## Boundaries (not decided here)

- **The token axis and which usage counts** (O1 point 2, O2): the first row of `ARCHITECTURE/SpendAxes.md`, and how the call reads and reports the coder's usage. That is the next record, with the output stream (OD-23 ① (라)).
- **Every other design point of slice (d)** (ADR-0126 Consequences, "Design points left to a later record"): image, container flags, sign-in, permission mode, prompt, time limit, output stream. Also how the value reaches `claude -p`; whether a configured fallback chain, the content-based fallback and the remapping of F2 are turned off, asked about or detected (for example from `modelUsage`); and what a run records of the model that actually ran (with the token record, which reads the same result message).
- **The models of every other agent**: the Round-Manager, the coder-driver, the evaluator, the selection.
- **Q1 of ADR-0126 (HQ-0040)**: under either form the model reaches the function the same way, from the file. **HQ-0032**: how the start learns of a given id or value.
- What offers the user the choice of a model, and whether anything warns that a named model is not offered (UC-1, OD-23).
- Any edit of an earlier record, of FR or NFR text, `hilclaw/`, `orchestration/`, tests, `.claude/`, any settings file or the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): NFR-5, FR-5, FR-13, C-7 ②; register rows OD-8, OD-19, OD-23. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-8](../OpenDecisionProposals.md#od-8), [OD-23](../OpenDecisionProposals.md#od-23). [StandardScenarios](../StandardScenarios.md) S0, S1, S2, S10.
- ADR-0001 (record format); ADR-0004; ADR-0010 (decision 7); ADR-0018; ADR-0019; [ADR-0023](ADR-0023-od8-instance-record-n-max.md); ADR-0025; [ADR-0032](ADR-0032-od8-instance-record-round-budget.md); ADR-0049; ADR-0076; ADR-0115; ADR-0120; ADR-0124; ADR-0126; [ADR-0135](ADR-0135-od23-first-case-round-end-write.md).
- #5 body item A-8; HQ-0041 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6273054804 and its answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368; D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- F1 https://docs.claude.com/en/docs/claude-code/cli-reference and F2 https://docs.claude.com/en/docs/claude-code/model-config, read 2026-10-21.
- Code, as observation only: `hilclaw/coder_call.py`, `hilclaw/instance.py`, `hilclaw/instance_start.py`. [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-2, P2-5; task T-0371.
