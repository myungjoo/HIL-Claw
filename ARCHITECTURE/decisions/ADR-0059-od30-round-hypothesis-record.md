# ADR-0059: The hypothesis record of a round — its file under `decision/`, its frame, the members of one hypothesis, the vocabulary of its origin, how hypotheses map to the round's candidates, and round 0 (first part of OD-30)

## Status

- **Accepted on 2026-10-14** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Answers **one part of OD-30** (Open Decisions register in [Requirements](../Requirements.md)): the structured hypothesis record that the technique selection of a round leaves (FR-17 ① to ④) — the file that holds it, the file as a whole, the members of one hypothesis, the vocabulary of its origin, how the hypotheses of a round map to its candidates, and whether round 0 has such a record. The file is a further file of `decision/`, the place ADR-0004's path table pointed to OD-23; it is placed here under OD-30, which owns "어느 파일이 무엇을 담는지" for the decision log (FR-11), and OD-23 keeps the roster and which agent holds the selection role. **OD-30 keeps its status word `제안됨`**: the verdict, the cases, the injection paths and the S6 metric stay open (Boundaries).
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1, the value forms), [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 2, 3 and 5), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1 to 4, 8 and 9), [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decision 4), [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decision 2), [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) (decisions 2 and 3), [ADR-0028](ADR-0028-od8-instance-record-candidates-per-round.md) (decision 5), [ADR-0029](ADR-0029-od8-spec-file.md) (decisions 2 to 7), [ADR-0050](ADR-0050-od6-task-objective-members.md) (decisions 3 to 5) and [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) (decision 7). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **Owner** ([decision of 2026-10-13](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569), point 1): "Each round's technique selection records a structured hypothesis record (hypothesis, rationale, expected effect); evaluate records a verdict and its cause per hypothesis. Both are required structured fields, not free prose. The runtime forms hypotheses itself by default." Point 4: "A hypothesis can be injected from outside … injection at instance start is in the MVP. An injected hypothesis goes through the same experiment, verification and verdict as the runtime's own." [Addendum](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136597638): "Injection must never mean that no new hypothesis is formed." and "Different cycles may test different hypotheses." The same decision leaves to OD-30 "record fields, verdict vocabulary, file places, which cases are fed to the selection, injection after instance start, who derives a hypothesis from a paper, and the metric definition of the S6 criterion".
- FR-17 names the four parts of a record — ① hypothesis ② basis (profile observation, past case (FR-18) or external material (FR-14·15)) ③ expected effect (which metric moves in which direction) ④ origin (set by the system or injected; "값의 어휘 = OD-30"). FR-11 makes the record part of the round's decision log. FR-14 ② records material that was actually used by "식별자+버전(또는 해시)".
- ADR-0004 gives every round a `decision/` directory owned by the selection role, holding `decision.md` ("Why these techniques (FR-11)"; "Further files: OD-23"), and decision 3 says "one choice of techniques covers all candidates of the round". Decision 9: the layout version "is not raised when a file is added in a place this record leaves open".
- ADR-0002 identifies a candidate by `id.candidate` (1 to `id.candidates`, "N of this round") and relates the candidates of a round by `id.relation` (`single`, `same_technique`, `different_techniques`); a *ref* is `{round, candidate, attempt}` and "names an earlier coder call of the same run"; `guidance.techniques[].id` "names the catalog entry". No catalog exists (OD-22), and [ADR-0058](ADR-0058-od6-committed-gemm-spec-example.md) decision 1 left the technique list of the committed example empty for that reason.
- Two names of a measured quantity have landed. The objective type `latency_minimisation`: its quantity is the time of the kernel call, and "lower is better" is the owner's (ADR-0050 decision 3). The constraint type `memory_ceiling`: an upper bound in bytes, defined by ADR-0050 decision 4 and "not yet an admitted value" (ADR-0050 decision 5; [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) decision 7 names the conditions). The Boundaries of ADR-0050 hand to OD-30 "how the expected effect of a hypothesis record (FR-17) names a metric and a direction", and those of [ADR-0053](ADR-0053-od8-instance-record-objective.md) "how a hypothesis record names a metric".
- No case file, no verdict file and no form of an injected input exists; no module of `hilclaw/` reads or writes a hypothesis.

## Decision

A value is **cited** when a source is named with it. Everything else is **this record's own** design: the file name, the frame, every member name, type and validity rule, the values `system`, `injected`, `attempt`, `external`, `case`, `lower` and `higher`, the choice of "written once", the rule that the expected effect names a type of a landed record (in version 1 `latency_minimisation` only), the treatment of round 0 as adopted, and the recommendation on causal misattribution.

### 1. Place, name and the write

- **The hypothesis record of round `<RRRR>` of run `<run_id>` is one file, `runs/<run_id>/rounds/<RRRR>/decision/hypotheses.json`**, beside `decision.md`, which stays the human-readable narrative of the round (FR-11). The file is the selection role's (cited: ADR-0004 decision 4); which agent or tool holds that role is OD-23 and is not decided here.
- **One file per round, not one per candidate**: the hypotheses are set by the one choice that "covers all candidates of the round" (cited: ADR-0004 decision 3), one hypothesis may span several candidates (decision 4), and ADR-0004 fixes no candidate-level file below `decision/` (its tree and decision 3; it leaves such files of a role open). A file per candidate would repeat a hypothesis in every candidate it spans.
- **It is written once and never replaced**: a hypothesis states what an experiment is expected to show before the experiment, and a record that could be rewritten after the measurement could be fitted to the result, so the verdict (FR-17) would compare the measurement with an expectation formed after it (NFR-2). Nothing has to be added to it later in the round: the verdict is the evaluation role's, not the selection role's, so it is not in this file (ADR-0004 decision 4); where it goes is the next part of OD-30 (Boundaries).
- **The write is that of ADR-0029 decisions 4 to 7, with this final name**: the content first, a temporary file `hypotheses.json.<token>.tmp` in `decision/` (the form of ADR-0014 decision 4), stable storage, and a last step that gives the final name only if it does not exist, with no fallback to a replacing rename; a taken name is reported and nothing more is decided about it; the write may create the missing directories above the final name and requires the presence or absence of no other file; a leftover is never given the final name. This is a summary; the steps are ADR-0029's and are not restated in full. "Valid" in the first step means valid by decisions 2 to 5 of this record, and **the final name is derived from the content**: the path that its `run_id` and `round` format to below the data root the write is given (as ADR-0029 decision 3 has it for a spec). **The write reads no other file** — not a spec of the round, not `instance.json`, not `STATE.json` — so no rule of decision 4 that needs another file is checked by it. ADR-0029 decision 6 read ADR-0004 decisions 2 and 7 for a temporary file in an attempt directory; **this record reads them the same way for `decision/`**.
- **The layout version stays 1**: a file is added in a place ADR-0004 left open, and no path, file name or number form changes (cited: ADR-0004 decision 9).

### 2. The file as a whole

- **The text form is that of ADR-0029 decision 2, with this file's members**: one JSON object, UTF-8 without a byte order mark, no member name twice in any object, an *integer* written in decimal digits without sign, fraction or exponent; LF line ends and a final line feed bind the writer, and no member order is fixed, for the reason ADR-0018 decision 2 gives for a file with one content.
- **Top-level members** (*name*, *string*, *integer* are those of ADR-0001 decision 1; *text* and *ref* those of ADR-0002 decision 2):

| Member | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | integer | yes | `1` for this record. |
| `run_id` | string | yes | The run directory name of the file (ADR-0004 decision 8). |
| `round` | integer ≥ 1 | yes | The round of the file (decision 5). |
| `candidates` | integer ≥ 1 | yes | N of this round: the meaning of `id.candidates` of ADR-0002. |
| `hypotheses` | array of hypothesis, at least one | yes | The hypotheses the round tests (decision 3). The order of the entries carries no meaning. |

- **`run_id` and `round` against the path**: the file is valid only when `run_id` is its run directory name and `round`, zero-padded as ADR-0004 decision 2 has it, is its round directory name — the rule of ADR-0029 decision 3 applied to this file, and for the same reason: a record is found by its round, so a file under the path of another round is no record of either.
- **The file carries its own `schema_version` and does not restate the layout version.** The layout version of a run is read from `instance.json` (cited: ADR-0004 decision 9; ADR-0024 decision 3), and a file whose record defines a `schema_version` carries its own (cited: ADR-0024 decision 2). This file will gain members from later parts of OD-30, which are no change of the layout.
- **The top level is open, as ADR-0018 decision 2 has it**: a reader passes over a top-level member it does not know, and later records add members there (for instance the identification of the cases a selection read, FR-11, FR-18). What raises the version is what ADR-0018 decision 2 lists for its file, read for this one; adding, removing or changing a member inside an entry of `hypotheses`, of `basis` or of `expected` raises it, **except** that two kinds of admission do not: admitting a value that this record defines and does not yet admit (decision 3), together with the members only entries of that value carry, and admitting as a value of `metric` the name of an objective or constraint type of a landed record. A metric that is no such type changes what `metric` names; the record that admits one says whether it raises the version. The cost is ADR-0050's: a reader built before such an admission refuses a file that uses the value.
- **A file that is not valid** — by the text form, by a rule of decisions 2 to 5, or holding a value this record does not admit — is reported, no member of it is used and nothing is repaired; a `schema_version` that is an *integer* other than `1` is set apart and not called damage (OD-11). An empty file is invalid, not missing (all as ADR-0018 decision 2).
- **A missing file** means that the tree holds no hypothesis record for that round and nothing more — in particular not that the round selected no technique. FR-17 does not allow a technique selection without a hypothesis; how that rule is enforced is OD-18 (Boundaries).

### 3. One hypothesis

An entry of `hypotheses` is an object with exactly these members:

| Member | Type | Required | Meaning |
|---|---|---|---|
| `id` | name | yes | Names the hypothesis; unique in the file. A hypothesis is identified by (`run_id`, `round`, `id`). |
| `statement` | text | yes | FR-17 ①: what is changed and what it is expected to improve. |
| `basis` | array of basis entry, at least one | yes | FR-17 ②: what the hypothesis rests on. |
| `expected` | array of expected entry, at least one | yes | FR-17 ③: which metric moves in which direction. No two entries have the same `metric`. |
| `origin` | `system` \| `injected` | yes | FR-17 ④. |
| `tested_by` | array of integer ≥ 1, at least one, no value twice | yes | The `id.candidate` values of this round that test it (decision 4). |

- **`basis` entries**, each an object with exactly the members of its `kind`:
  - `kind` `attempt` — an observation of an earlier attempt of the same run: `ref` (a *ref* of ADR-0002 whose `round` is lower than the file's `round`) and `text` (what of that attempt the hypothesis rests on: its profile, its failure, its measurement). Which file of that attempt holds what is ADR-0004's and OD-13's; the entry names the attempt, not a file.
  - `kind` `external` — external material (FR-14, FR-15): `source` (*string*, the identifier of the material), `version` (*string*, its version or hash, FR-14 ②) and `text`. The cost of *string*: an identifier longer than 255 characters or outside printable ASCII does not fit, and a later record may widen the form. How `source` relates to the source registry of FR-14 ① is OD-12; this record adds no rule to its form.
  - `kind` `case` — a stored case (FR-18): **defined and not admitted**. No case file exists, so a case has no landed form of reference; the record that gives cases their file (P2-7) admits the value with its reference member.
  - **`basis` has at least one entry**: the owner makes the rationale a required structured field, "not free prose", so a hypothesis whose only reason is its `statement` is not a valid entry. **The cost**: a round-1 hypothesis can cite any attempt of round `0000` (the bring-up code, FR-1); only if round 0 has no attempt of the run — a baseline that is not one, whose record is OD-28 — and no external material applies, is it not recordable until OD-28 or the case file gives another form of reference (Boundaries). An empty basis is not the answer to that gap.
- **`expected` entries** have exactly `metric` and `direction`.
  - `metric` is a *name*. **In version 1 its only admitted value is `latency_minimisation`**, meaning the quantity of the objective type of that name (cited: ADR-0050 decision 3). A metric is named by a type of a landed record so that no new name is coined. **`memory_ceiling` is not admitted here**: it is a constraint, judged as within or over a bound (ADR-0050 decision 4), not a quantity whose direction is the type's own, and a spec cannot state it yet (ADR-0052 decision 7). A further objective type (OD-1), `memory_ceiling`, or a metric that is no type (a profile counter — OD-13; the open metric vocabulary of FR-3 ④) is admitted by a later record. The record that admits a value defines what quantity `metric` then names. Admitting a further type name does not raise the version (decision 2). Whether the metric must be an objective of the run's own `instance.json` is not required here, since the write reads no other file.
  - `direction` is `lower` or `higher`: the direction in which the hypothesis expects the quantity to move. It names the movement of the quantity, not "better" or "worse"; for `latency_minimisation`, `lower` is an improvement (owner, cited: ADR-0050 decision 3).
  - **Not recorded in version 1**: a magnitude, and what the movement is measured against (the base attempt, the incumbent or the baseline). Both depend on the verdict's comparison (Boundaries); a later record that adds them raises the version.
- **`origin`**: `system` — set by the runtime itself, including a hypothesis it draws from a stored case or from material it found itself (the `basis` says so; a third value would mix the origin with the basis). `injected` — given from outside (FR-15; owner, point 4), whether written by the user or derived from material the user gave (FR-15 counts both as injection). **`injected` is defined and not admitted**: an injected hypothesis must be identifiable as such in the decision log (FR-11), and the form and place of what is injected is not decided (Boundaries). The record that decides that form admits `injected` with the member that points to the injected input. Until then a valid file holds system hypotheses only, which FR-17 makes the default ("The runtime forms hypotheses itself by default", owner).
- **No technique reference.** FR-17 and the OD-30 proposal speak of the technique a hypothesis applies; `guidance.techniques[].id` names a catalog entry, and no catalog entry exists (OD-22; ADR-0058 decision 1). An entry therefore names no technique. The techniques that a candidate testing the hypothesis applies are those of that candidate's specs, which `tested_by` leads to (ADR-0004 decision 3). Whether a hypothesis names a subset of them is for a later record and raises the version.

### 4. Hypotheses and candidates

- **Every candidate of the round tests at least one hypothesis**: each integer from 1 to `candidates` occurs in the `tested_by` of at least one entry, and no `tested_by` holds a value above `candidates`. This is a rule of the file's validity; how FR-17's rule against a selection without a hypothesis is enforced is OD-18.
- **A hypothesis may span several candidates and a candidate may test several hypotheses.** A hypothesis tested by all candidates of a `same_technique` round, a hypothesis per candidate of a `different_techniques` round, and two hypotheses on one candidate are all valid. **No rule ties `id.relation` to the mapping**: two variants of one technique may test two hypotheses (for instance two blocking factors), and different techniques may test one hypothesis about a shared cause.
- **All attempts of a candidate test the same hypotheses**: the mapping names candidates, not attempts. A repair call fixes a failure of the same candidate (ADR-0002 decision 5) and does not change what the candidate tests.
- **What `candidates` stands against**: it has the meaning of `id.candidates` of the round's specs. That the two are equal is meant and is not checked by the write (decision 1); what checks it is not decided (Boundaries). Whether `id.candidates` must equal `candidates_per_round` of `instance.json` stays sub-question ㉕ (ii) of OD-8 (cited: ADR-0028 decision 5).
- **Causal misattribution: a recommendation, not a rule.** A candidate that tests two hypotheses, or applies changes beyond one hypothesis, makes it hard to say which change caused the effect. The mapping already states which hypotheses share a candidate, so no member "applied together" is added: it would repeat `tested_by`. The selection role **should** keep each hypothesis narrow and give each candidate one hypothesis where N allows; the file does not enforce it, and how the verdict treats a candidate shared by several hypotheses is the verdict's record.

### 5. Round 0

**Round `0000` has no hypothesis record; a file whose `round` is 0 is invalid.** The OD-30 proposal is adopted: round 0 is bring-up and baseline (FR-1), which applies no technique, and FR-17 binds "라운드의 기법 선택". Its results are what later hypotheses rest on, through `basis` entries of kind `attempt` when the baseline is an attempt of the run (OD-28).

### Example

The record of round `0001` of a run with N = 1 and one system hypothesis. The run id is the example of [ADR-0027](ADR-0027-od8-run-id-form.md); the metric is cited (ADR-0050 decision 3); the texts are placeholders, as ADR-0050 uses them, because no source gives a hypothesis (ADR-0058 decision 1 refused a placeholder in a committed data file that is copied as a template; an example inside a record is not one); the `ref` assumes a round-0 attempt `0000/01/01`, which no record yet says exists (OD-28). Path: `runs/20261009t012331z-9f3a6c1e0b7d4a52/rounds/0001/decision/hypotheses.json`.

```json
{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "candidates": 1,
  "hypotheses": [
    {
      "id": "h1",
      "statement": "NOT-DECIDED-HERE",
      "basis": [
        {"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}
      ],
      "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
      "origin": "system",
      "tested_by": [1]
    }
  ]
}
```

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | Hypotheses inside `decision.md` | FR-17 and the owner require structured fields, not prose; `decision.md` stays the narrative. |
| 1 | One file per candidate, or the hypotheses in `spec.json` | A hypothesis spanning candidates would be repeated; ADR-0004 fixes no candidate-level file below `decision/`; a spec member would change an existing data-plane file. |
| 1 | A replaceable file (ADR-0013's write) | A hypothesis could then be rewritten after its measurement (decision 1). |
| 2 | No own `schema_version`, relying on the layout version | The layout version is raised by paths only (ADR-0004 decision 9); this file's members will grow with later parts of OD-30. |
| 2 | A closed top level | Every later member of OD-30 would be a new version before a first record exists (ADR-0018 decision 2's reason). |
| 3 | `origin` with a third value `case` (the OD-30 proposal) | It mixes the origin with the basis; FR-17 ④ distinguishes "system or injected". |
| 3 | `injected` admitted now without a pointer | The decision log could not say which injected input a hypothesis came from (FR-11). |
| 3 | A technique catalog id per hypothesis | No catalog entry exists (OD-22); any id would be invented. |
| 3 | Free metric names, or a magnitude now | Would coin names FR-3 ④, OD-1 and OD-13 leave open, and a magnitude needs the verdict's reference point. |
| 3 | `memory_ceiling` admitted as a metric now | It is a bound with a feasibility verdict, not yet admitted in a spec (ADR-0052 decision 7); its admission as a metric needs no new version (decision 2). |
| 3 | `basis` that may be empty | The reason would then be free prose in `statement`, which the owner rules out; the round-1 gap (round 0 without an attempt) goes to OD-28 and the case file instead. |
| 4 | A member "applied together" | It would repeat what `tested_by` states. |
| 4 | One hypothesis per candidate as a rule | Would forbid a hypothesis about variants of one technique across candidates (`same_technique`). |
| 5 | A record for round 0 | Bring-up applies no technique; the OD-30 proposal says the same. |

## Consequences

- **A code slice can be cut** (code mode, P2-6's 2층 part): a reader and validator of the bytes of this file by decisions 2 to 5, a writer by the steps of ADR-0029 decision 4 with this final name, and the path in `hilclaw/layout.py` beside `decision_log`. Its names and call forms are that task's. Binding it to an agent, a prompt or a hook is not part of that slice.
- **A-13 reading**: document mode. A new file is added in a place ADR-0004 left open; no member, value or version of `STATE.json`, `instance.json`, `spec.json`, `eval.json`, `artifacts.json`, `events.ndjson` or a key record changes, and `decision.md` is unchanged — the route ADR-0029 and ADR-0018 took for their files. Nothing was built or run, and no `claude` process was started.
- **If round 0 leaves no attempt of the run** (a baseline that is not one, OD-28), a round-1 hypothesis needs external material as its basis until OD-28 or the case file gives another form of reference (decision 3).
- **Until `injected` and `case` are admitted**, an instance cannot record an injected hypothesis or rest a hypothesis on a stored case in this file. The owner puts injection at instance start in the MVP, so the record that admits `injected` is needed before the MVP is complete.
- **Not edited and now less exact** (follow-ups for the integrator): the path table row of ADR-0004 for `decision.md` ("Further files: OD-23"), its Boundaries item "each agent's files beyond the directory of its role (OD-23)" as far as the selection role's files go, and its decision 3 "Per round: the decision log, `decision/decision.md`"; ADR-0029 Boundaries "Every other file … `decision.md`" as far as it lists the round's decision files; the Boundaries of ADR-0050 and ADR-0053 that hand to OD-30 how a hypothesis names a metric and a direction; the OD-30 bullets of [OpenDecisionProposals](../OpenDecisionProposals.md#od-30) on fields and file places beyond the line added with this record; FR-11's parenthesis "어느 파일이 무엇을 담는지 = OD-30" and the parenthesis of FR-17 listing "필드·…·파일 자리, 가설과 기법·후보(N)의 대응, …, 라운드 0의 취급 = OD-30", which is now partly answered and still true as a pointer. The docstring of `decision_log` in `hilclaw/layout.py` ("the decision log of the round") now names one of two files of that log; it is for the code slice.

## Boundaries (not decided here)

- **The verdict and cause of each hypothesis** (FR-17): its vocabulary, its file (the natural place is `eval/`), what it compares a measurement against, the magnitude of an effect, and how it treats a candidate shared by several hypotheses — the next part of OD-30.
- **The hypotheses of a round that never reaches evaluate** (budget exhausted, process death): whether they are closed, left open or resumed (NFR-1, OD-17).
- **The case file under `db/`** and the lookup: its fields, immutability, the reference a `case` basis entry carries, which cases are read and how many, and the identification of the cases a selection read (FR-11, FR-18, P2-7; OD-7, OD-20, OD-24).
- **Injected hypotheses**: the form and place of what is injected at instance start (FR-15 — whether `instance.json` or another run file carries it) and the member an `injected` entry points to it with; **injection at a gate or during a run, and whether either is in the MVP** (owner, HQ, per the OD-30 section); who derives a hypothesis from material; the boundary between a supported injected hypothesis and the catalog (UC-5, OD-24).
- **A basis that cites an attempt of another run** — a branch or continuation represented as a new run (sub-question ① of OD-8): a *ref* names a call of the same run only (ADR-0002). Until a record gives a cross-run reference, a case (FR-18) is the intended path.
- **What checks that `candidates` equals the `id.candidates` of the round's specs**, and when (with sub-questions ⑩ and ㉕ of OD-8; OD-23).
- **The order and share** of injected versus system hypotheses across rounds and candidates.
- **A basis that cites an earlier hypothesis or verdict of the run** (FR-17: the next round takes earlier verdicts as input): until the verdict has a file, an `attempt` entry and its `text` stand in; a kind of its own is for the verdict's record.
- **The S6 metric**, its boundary cases, repetitions and control (P2-8).
- **Which agent writes the file**, when it is written against the round's specs and other files (sub-question ⑩ of OD-8), and how its presence and its rules are enforced — "가설 없는 기법 선택을 허용하지 않는다" (OD-23, OD-18). What a second write for a round means after the name was taken (a resumed turn, a stop) goes with the rounds that never reach evaluate (OD-30, OD-17).
- Technique catalog entries and ids (OD-22); metric names beyond `latency_minimisation` (FR-3 ④, OD-1, OD-13); the baseline and its record, including how a hypothesis cites a baseline that is not an attempt of the run (OD-28); reading a file of another version (OD-11).
- **Owner-only (DRIVER §9)**: #5 A and B items, C-6, OD-25, OD-3. Nothing of them is touched.
- Code, tests, schema files and prompts (P2-1, P2-3, P2-6's later slices); any change to an accepted record or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, FR-11, FR-14, FR-15, FR-17, FR-18, NFR-1, NFR-2; register rows OD-1, OD-7, OD-8, OD-11, OD-12, OD-13, OD-17, OD-18, OD-20, OD-22, OD-23, OD-24, OD-28, OD-30.
- [OpenDecisionProposals OD-30](../OpenDecisionProposals.md#od-30); [StandardScenarios](../StandardScenarios.md) S0, S6, S8, S11.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 2, 3, 5); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1 to 4, 8, 9; path table); [ADR-0013](ADR-0013-od8-state-file-replacement.md) (the replacing write, as an alternative); [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decision 4); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decision 2); [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) (decisions 2, 3); [ADR-0027](ADR-0027-od8-run-id-form.md) (example); [ADR-0028](ADR-0028-od8-instance-record-candidates-per-round.md) (decision 5); [ADR-0029](ADR-0029-od8-spec-file.md) (decisions 2 to 7); [ADR-0050](ADR-0050-od6-task-objective-members.md) (decisions 3 to 5; Boundaries); [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) (decision 7); [ADR-0053](ADR-0053-od8-instance-record-objective.md) (Boundaries); [ADR-0058](ADR-0058-od6-committed-gemm-spec-example.md) (decision 1).
- Owner decision 2026-10-13 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569 and its addendum https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136597638 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-6, P2-7, P2-8; `hilclaw/layout.py`; task T-0184.
