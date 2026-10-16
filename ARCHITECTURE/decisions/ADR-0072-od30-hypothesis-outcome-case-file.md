# ADR-0072: The stored hypothesis-outcome case of a round — its file in the key directory, its name and write, its frame, what one case holds, and its relation to the key and to the other files of `db/` (one more part of OD-30)

## Status

- **Accepted on 2026-10-16** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Answers **one more part of OD-30** (Open Decisions register in [Requirements](../Requirements.md)): the **case** that FR-18 requires to be stored under `db/<hw_profile_key>/<op_signature>/` — the file that holds it, its name and write, the file as a whole, what one case holds (rejected and failed included), and how it stands to the key and to the other files of the key directory. It builds on the hypothesis record of [ADR-0059](ADR-0059-od30-round-hypothesis-record.md) and the verdict record of [ADR-0071](ADR-0071-od30-hypothesis-verdict-record.md), whose Boundaries name "the case file under `db/`" as a later part of OD-30. **OD-30 keeps its status word `제안됨`**: the lookup, the `basis` kind `case`, the injection paths and the S6 metric stay open (Boundaries).
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3, 4 and 7), [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 2, the *ref*; decision 4, `feedback.attempts`), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 2, 5, 8 and 9), [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decisions 3 and 4), [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 2 and 3), [ADR-0029](ADR-0029-od8-spec-file.md) (decisions 2 to 7), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decisions 3 and 5), ADR-0059 (decisions 1 to 5) and ADR-0071 (decisions 1 to 6). The objection window of ADR-0071 runs until 2026-10-23; if it or another of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **Owner** ([decision of 2026-10-13](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569)), as FR-18 states it: "라운드의 가설 레코드·판정·원인을 측정 결과에 이어 **사례**로 `db/<hw_profile_key>/<op_signature>/` 아래에 저장한다" and "**기각된 가설과 실패한 시도도 저장한다**"; a new instance "같은 (hw_profile, op_signature) 키의 사례를 조회" and records which cases it used (FR-11); "MVP 최소분은 정확 일치 키의 조회"; "사례의 저장과 조회는 agent-memory에 기대지 않는다". FR-18 leaves to OD-30 "사례의 필드·파일, 조회해 싣는 사례의 선택과 양, 기법 통계(OD-7)·후보 아카이브(OD-20)와의 관계". **#5 A-1** ([owner](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826)): `runs/`, `db/` and `blobs/` are "최상위에서 섞지 않는다" so that a later split into a runs repository and a db repository is a mechanical promotion of a directory to a repository, and the per-round promotion `runs/` → `db/` is one atomic commit.
- ADR-0004 decision 5 keeps `best.json` and `technique_stats.json` directly in the key directory, written "by the promotion step, in the same commit as the round it promotes (#5 A-1)", and says "Their content, and any further file of a key directory, is OD-20 and OD-7". The register rows of OD-7 and OD-20 both say "사례 필드 = OD-30". Decision 9: layout version 1 "is not raised when a file is added in a place this record leaves open"; "`db/` needs no stamp of its own in version 1: its two levels are fixed by FR-13 and ADR-0001, and its files carry their own `schema_version`". Decision 8: a `run_id` "is unique within `runs/` of a data repository".
- ADR-0059 fixed `decision/hypotheses.json` and ADR-0071 `eval/verdicts.json`: one file each per round ≥ 1, written once, with their own `schema_version` 1 and an open top level; a hypothesis is identified by (`run_id`, `round`, `id`); every *ref* in them names an attempt of the same run (ADR-0002); ADR-0071 decision 1 states rules between the two files of a round and says "A hypothesis without a verdict entry has no verdict". ADR-0059 decision 3 defines the `basis` kind `case` and does not admit it: "the record that gives cases their file (P2-7) admits the value with its reference member".
- ADR-0014 decision 3 and ADR-0029 decision 4 give a file that has one content a write whose last step never replaces. No result file (`sim.json`, `board.json`, `eval.json`: by ADR-0004's path table the content of the first two is OD-13 and the fields of `eval.json` OD-20, OD-13 and OD-23; PLAN P1-8) has members. The code has `hilclaw/layout.py` (`op_signature_dir`; `op_signature_file` accepts the three names of ADR-0004 only), `hilclaw/hypotheses.py`, `hilclaw/verdicts.py` and the check between the two, `hilclaw/verdicts_hypotheses.py` (observations; this record binds no code).

## Decision

A value is **cited** when a source is named with it. Everything else is **this record's own** design: the file name, the frame, every member name, type and validity rule, the choice of one file per round, of a copy, of "written once", of no subdirectory and of no created directory, and the treatment of a round without verdicts.

### 1. Place, name and the write

- **The case of round `<RRRR>` of run `<run_id>` is one file, `db/<hw_profile_key>/<op_signature>/case-<run_id>-<RRRR>.json`**, directly in the key directory, with `<RRRR>` the round directory name (ADR-0004 decision 2). The key directory is that of the run's instance — the keys of the records its `instance.json` states in `hw_profile` and `op_signature` (ADR-0018 decision 3, ADR-0031 decision 3): FR-18's "같은 (hw_profile, op_signature) 키". That is a rule between files and is not checked by the write.
- **Why this is OD-30's to place**: ADR-0004 decision 5 leaves further files of a key directory to OD-20 and OD-7, and both of their register rows, with FR-18's closing parenthesis, hand the fields and file of the case to OD-30. Nothing of `best.json` or `technique_stats.json` is decided here.
- **One file per round**, not one per hypothesis and not one growing file per key. The round is the unit of promotion (#5 A-1) and of both source files, and ADR-0071's rules between them hold per round; a file per hypothesis would cut a candidate shared by several hypotheses (ADR-0071 decision 5) and those rules apart. A growing file would be rewritten by every promotion of every run of the key — against the write-once precedent of ADR-0014 decision 3 and ADR-0029 decision 4, and a second writer of one file as soon as two runs share a key (OD-17).
- **The name is unique**: a `run_id` is unique within `runs/` of a data repository (ADR-0004 decision 8) and a round number is used once per run (ADR-0004 decision 2). `<RRRR>` is the part after the last hyphen (a `run_id` may hold hyphens, a round directory name does not). Two data repositories may hold one `run_id`; how their cases meet is OD-25 (Boundaries).
- **No subdirectory such as `cases/`.** ADR-0004 decision 9 does not raise the layout version for "a file … added in a place this record leaves open"; a directory level below the key directory is more than that, and the two levels of `db/` are what lets it go without a stamp of its own. A file directly in the key directory keeps **layout version 1**. The cost: a listing of the key directory holds the cases beside the three named files; the prefix `case-` tells them apart, and a key directory name never contains a dot (ADR-0004 decision 5). The temporary file of the write below ends in `.tmp` and a case in `.json`, so a case is never of the form `<final name>.<token>.tmp` that ADR-0014 decision 4 gives a temporary file, and a leftover is never taken for a case.
- **The writer role is the promotion step**, in the same commit as the round it promotes (cited: ADR-0004 decision 5 for `best.json` and `technique_stats.json`, from #5 A-1). Which agent or tool holds that step is OD-23. The owner's rationale for #5 A-1 speaks of "매 라운드 `runs/`→`db/` 승격 커밋"; this record reads it as the form of a promotion commit, not as a rule that every round — one without verdicts included — is promoted, which stays open (Boundaries).
- **It is written once, and no write modifies or replaces it**: a later run rests hypotheses on what it read (FR-18, FR-11), and a case that could change afterwards would no longer be what that run read (NFR-2). Its two sources are written once too.
- **The write is that of ADR-0029 decisions 4, 6 and 7 with this final name** (decision 5 of ADR-0029 is replaced by the next bullet), as ADR-0059 decision 1 cites decisions 4 to 7, here without decision 5: the content first, valid by decisions 2 and 3 of this record (the rules between the two copies included); a temporary file `case-<run_id>-<RRRR>.json.<token>.tmp` in the key directory (the form of ADR-0014 decision 4); stable storage; a last step that gives the final name only if it does not exist, with no fallback to a replacing rename; a taken name is reported. The final name is derived from the content's `run_id` and `round` below the key directory the write is given. **The write reads no other file** — not the source files in `runs/`, not `instance.json`, not the key record files.
- **The write creates no directory**: the key directory must exist, and a missing one fails the write with nothing stored. A key directory is created together with its record files by whatever creates it (cited: ADR-0004 decision 5; ADR-0014 decision 3); a case write that created one would leave a key directory without its records. The limit: since the write reads no key record file, a case can still be written into a key directory that holds no record (the window of ADR-0014 decision 3), that is, below a key that is not stored.

### 2. The file as a whole

- **The text form is that of ADR-0029 decision 2, with this file's members**, as ADR-0059 decision 2 and ADR-0071 decision 2 have it.
- **Top-level members** (*string* and *integer* of ADR-0001 decision 1):

| Member | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | integer | yes | `1` for this record. |
| `run_id` | string | yes | The run of the round the case is of (the source run). |
| `round` | integer ≥ 1 | yes | That round. |
| `hypothesis_record` | object | yes | The round's `decision/hypotheses.json` (decision 3). |
| `verdict_record` | object | no | The round's `eval/verdicts.json` (decision 3). |

- **`run_id` and `round` against the name and the copies**: the file is valid only when its name is formed from its `run_id` and `round` (the rule of ADR-0029 decision 3 applied to this name) and both equal the `run_id` and `round` of each copy.
- **Its own `schema_version`**, and **the top level is open**, both for the reason of ADR-0059 decision 2: later records add members here. The version is raised when a member of the table is removed or changes its type, meaning or requirement, when a later record makes a further top-level member required (the list of ADR-0018 decision 2, read for this file as ADR-0059 decision 2 reads it), or when the rule of the copy (decision 3) changes; adding an optional top-level member does not raise it. **It is not raised when the version of a copied file rises**: each copy carries its own `schema_version` and is valid by the record of that version; a reader that does not know it sets the case apart and does not call it damage (OD-11).
- **An invalid file** is reported, no member of it is used and nothing is repaired; an empty file is invalid, not missing (all as ADR-0059 decision 2). **A missing file** means that the key directory holds no case of that round and nothing more — not that the round was not promoted, nor that it had no hypotheses.

### 3. What one case holds

- **A copy, with the identification of its source.** `hypothesis_record` is the document the round's `hypotheses.json` parses to, and `verdict_record` the one its `verdicts.json` parses to, **whole and unchanged**: every member, top-level members the writer does not know included; nothing added, removed or altered. Equality is of parsed JSON values; bytes and member order are not compared (no order is fixed in either file). `run_id` and `round` lead back to the source files and each hypothesis keeps its (`run_id`, `round`, `id`) of ADR-0059.
- **Why a copy and not a reference into `runs/`**: a later run can read the cases of its key from the key directory alone, without opening another run (FR-18; a hit "makes the stored knowledge of that pair available as a hint (FR-15)", ADR-0001 decision 4); `db/` is the cross-run tree, kept apart from `runs/` so that each can become a repository of its own (#5 A-1), and no record decides that `runs/` is kept, or shared and present wherever `db/` is read (OD-25). A reference-only case would stop being readable at that split. The identification still serves audit (NFR-2): while `runs/` holds the source, the copy can be checked against it.
- **Why whole documents and not chosen members**: a selection would be a second schema of a hypothesis and a verdict that every later version of ADR-0059 or ADR-0071 would have to follow; a whole copy adds no member to either and coins none. The cost: a case repeats a few kilobytes of text, the round's `candidates` included.
- **Rejected and failed are stored**: every hypothesis of the round is in the case, whatever its verdict, and nothing is filtered by value. A `refuted` or `inconclusive` verdict is its entry in `verdict_record`, unchanged, with its `cause` and `evidence` (FR-18; ADR-0071 decision 4). A failed attempt appears as far as the landed records carry it: as `check` evidence with `outcome` `fail` or `broken` where a verdict lists it (not required: an `inconclusive` entry may have empty evidence), with its comparisons not counted (ADR-0071 decision 4), and in the `text` of a later `attempt` basis entry that rests on it. Its failure stage and report, its build record and its results are **not** in a case: the files that would hold them have no members (each left open in ADR-0004's path table; PLAN P1-8; the `failure` of ADR-0002 is a member of a later spec). A later record may add them at the open top level. **No magnitude, sample, interval or file path** is in a case beyond what the copies hold, and they hold none (ADR-0059 decision 3; ADR-0071 decision 3).
- **The *refs* inside the copies** — `basis` entries of kind `attempt`, `ref`, `measured` and `against` of `evidence` — name attempts of the case's `run_id` (ADR-0002: "an earlier coder call of the same run", the run being the source run). A reader of another run reads them so, never as attempts of its own run. Whether and how it opens the source run's files is not decided (Boundaries).
- **The two copies obey the rules between their files**: a case that holds `verdict_record` is valid only when the copies satisfy every rule ADR-0071 states between `verdicts.json` and `hypotheses.json` of one round (decision 1: one verdict per hypothesis `id`; decision 3: `measured` within `tested_by`; decision 4: the value against `expected`), and each copy is valid by its own record — decisions 2 to 5 of ADR-0059, decisions 2 to 6 of ADR-0071 — except their rule of `run_id` and `round` against the file's path, which a copy has no path for and which decision 2 of this record replaces. In one file these rules become checkable by the write, so a promotion cannot store a pair that breaks them.
- **A round with a hypothesis record and no verdicts file**: the case form admits it, with `verdict_record` absent. The absence means only that the round's tree held no verdicts file when the case was written; **it is never read as `inconclusive` or any other value** (the rule of ADR-0071 decision 1, read for a case). **Whether such a round is promoted**, and so whether such a case exists, is not decided (NFR-1, OD-17; Boundaries). The cost, stated for that decision: a case written without verdicts never gains them — a later verdicts file of the round does not change it, and a second case of the round finds its name taken.
- **Round 0 has no case**, and a case whose `round` is 0 is invalid: round `0000` has neither file (ADR-0059 decision 5; ADR-0071 decision 6). A round without a hypothesis record yields no case: the content of a case is the hypothesis record, and FR-17 allows no technique selection without one.

### 4. The key and the other files of the key directory

- **The key is the exact-match key** of ADR-0001 decisions 3 and 4: a case belongs to the one (hw_profile, op_signature) pair whose directory holds it, and the case does not restate the key (its directory and the key record files beside it do). Which cases a run reads, how many and in what order is the lookup and is not decided; the use of a similar key is OD-4's residue.
- **`best.json` and `technique_stats.json`**: no content is decided and no member of a case points at them, or they at a case. The commit that promotes a round may write them beside its case (ADR-0004 decision 5); whether it does is OD-20 and OD-7.
- **The question of OD-20** ("후보 레코드(본 항목)와 가설–결과 사례(OD-30)가 한 파일인지 서로를 가리키는 두 파일인지"): **two files**. A case is fixed at its round's promotion with a content this record closes, and a candidate record has the open fields and lifetime of OD-20; one file would make either follow the other. Whether and how they point at each other — a later member of the case's open top level, or a member of OD-20's record — is for OD-20 together with a later record of OD-30.
- In the ExpeL split of the OD-7 proposal, these files are the `cases/` side (immutable cases) by their role, not by a directory name; `insights/` stays with OD-7 and OD-24.

### Example

The case of the round of the ADR-0059 and ADR-0071 Examples (run id of [ADR-0027](ADR-0027-od8-run-id-form.md), round `0001`, hypothesis `h1`, verdict `supported`), copied from those Examples unchanged. The key directory names are those of ADR-0001 decision 7, which says they are "not the names of the real first instance". Path: `db/cpu_standin-b0d8610d8f470856/gemm-c43e96fb16cc3f35/case-20261009t012331z-9f3a6c1e0b7d4a52-0001.json`.

```json
{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "hypothesis_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "candidates": 1,
    "hypotheses": [
      {"id": "h1", "statement": "NOT-DECIDED-HERE",
       "basis": [{"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
       "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
       "origin": "system", "tested_by": [1]}
    ]
  },
  "verdict_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1,
    "verdicts": [
      {"hypothesis": "h1", "verdict": "supported", "cause": "NOT-DECIDED-HERE",
       "evidence": [
         {"kind": "check", "ref": {"round": 1, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "check", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "comparison", "metric": "latency_minimisation", "point": "board",
          "measured": {"round": 1, "candidate": 1, "attempt": 1},
          "against": {"round": 0, "candidate": 1, "attempt": 1}, "difference": "lower"}]}
    ]
  }
}
```

A reader of another run reads `{"round": 0, "candidate": 1, "attempt": 1}` as attempt `0000/01/01` of run `20261009t012331z-9f3a6c1e0b7d4a52`. Had `h1` been refuted, the case would differ only in the copied `verdict_record`.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | One growing file of all cases of a key | Rewritten by every promotion of every run; against the write-once precedent (ADR-0014, ADR-0029); two writers of one file across runs (OD-17). |
| 1 | One file per hypothesis | Cuts apart a shared candidate and the per-round rules of ADR-0071; the promotion unit is the round. |
| 1 | A subdirectory `cases/` or `cases/<run_id>/` | A level below the key directory, which ADR-0004 decision 9 does not cover as "a file added"; a flat name serves. |
| 1 | The case write creates a missing key directory | It would leave a key directory without its record files (ADR-0004 decision 5, ADR-0014 decision 3). |
| 3 | A reference only (`run_id`, `round`, `id`) | A later run would have to open another run, and `runs/` may be absent, unshared or gone where `db/` is read. |
| 3 | A selection of members (statement, verdict, cause) | A second schema to keep in step with every version of ADR-0059 and ADR-0071; the selection itself would be invented. |
| 3 | Copies of results, failure reports or magnitudes | Their files have no members (ADR-0004's path table; PLAN P1-8); ADR-0059 and ADR-0071 record no magnitude. |
| 3 | No case for a round without verdicts; or such a round's verdicts read as `inconclusive` | The first decides a promotion policy (Boundaries) by the form; the second reads an absence as a value, which ADR-0071 decision 1 forbids. |
| 4 | Case and candidate record in one file | Ties a closed, write-once content to OD-20's open fields. |
| 4 | A `basis` kind `case` admitted now | It needs no version raise (ADR-0059 decision 2), but this record changes nothing of `hypotheses.json`, and the reference member is best fixed with the lookup and the FR-11 identification. |

## Consequences

- **A code slice can be cut** (code mode, P2-7's first 2층 part): a validator of a parsed case (decisions 2 and 3, using the validators of ADR-0059 and ADR-0071 and the check of `hilclaw/verdicts_hypotheses.py`), a bytes reader and writer by ADR-0029 decision 4 with this final name, the path in `hilclaw/layout.py` beside `op_signature_dir`, and a pure builder of a case from a parsed hypothesis record and an optional verdict record — decision 3 makes it determinate. Names are those tasks'. Binding it to an agent, a promotion step, a commit or a prompt is not part of it.
- **A-13 reading**: document mode. A new file is added in the key directory, a place ADR-0004 decision 5 left open; no member, value or version of `hypotheses.json`, `verdicts.json`, `eval.json`, `STATE.json`, `instance.json`, `spec.json`, `artifacts.json`, `events.ndjson`, `hw_profile.json`, `op_signature.json`, `best.json` or `technique_stats.json` changes, the `basis` kind `case` stays not admitted, and the layout version stays 1. Nothing was built or run, and no `claude` process was started.
- **What a later `case` entry can carry**: a case is found by its key directory and (`run_id`, `round`), and a hypothesis in it by its `id`; a reference of that form names one stored hypothesis and its verdict. Admitting the kind with its members is a later record: by ADR-0059 decision 2 it raises no version of `hypotheses.json`; this record changes nothing of that file, and the A-13 reading of the admission is that record's.
- **Names checked on 2026-10-16 in `hilclaw/`, `tests/` and `ARCHITECTURE/`.** `case-` occurs as no file name; the word `case` occurs as a test parameter and as the `basis` kind ADR-0059 defines (unchanged). `hypothesis_record` and `verdict_record` are the functions of `hilclaw/layout.py` that build the paths of the two copied files, and aliases of `hilclaw.hypotheses` and `hilclaw.verdicts` in `hilclaw/verdicts_hypotheses.py`; they are taken here on purpose for members that hold the content of those same files. No member is a reserved kind, `step`, `condition` or `outcome` value.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0059 Boundaries "The case file under `db/` and the lookup" (its fields and immutability now answered), its decision 3 "No case file exists, so a case has no landed form of reference" and "the record that gives cases their file (P2-7) admits the value with its reference member" — this record gives cases their file and does not admit the value, for the reason in Alternatives (point 4) —, and its Boundaries on a cross-run basis ("a case (FR-18) is the intended path"); ADR-0071 decision 1 "what checks it and when is not decided" (a case write now checks the rules between the two files for the pair it copies), its Boundaries "The case file under `db/`, the lookup, and how a later round or run reads verdicts" and its decision 4's "a case built from it (FR-18, P2-7)"; ADR-0004 decision 5 "any further file of a key directory, is OD-20 and OD-7", its tree (which shows no case) and the `db/` row of its decision 9 table; the OD-30 proposal bullet "파일 자리(제안)" ③ of [OpenDecisionProposals](../OpenDecisionProposals.md#od-30) beyond the line added with this record, and the OD-20 line on one file or two; FR-18's parenthesis "사례의 필드·파일 … = OD-30", now partly answered and still true as a pointer.

## Boundaries (not decided here)

- **The lookup**: which cases a run reads, how many, in what order and at what context cost (OD-30 "조회해 싣는 사례의 선택과 양"); the use of cases of a similar key (OD-4 residue); whether a reader opens the source run's files.
- **The `basis` kind `case`** in `hypotheses.json` and the reference member it carries — no version raise by ADR-0059 decision 2; for a later record of OD-30, fixed with the lookup.
- **The identification of the cases a selection read** in the decision log (FR-11), and any spec member that carries cases to the coder (ADR-0002 `feedback.attempts` names attempts of the same run only).
- **Promotion**: when a round is promoted and whether every round is — ADR-0004 Boundaries puts promotion with OD-29 and OD-15, whose register row names only the promotion of candidates to the board, so until a row names the promotion `runs/` → `db/` it is held open here, under OD-30 with OD-29 —, which agent or tool promotes (OD-23), whether a round without verdicts is promoted (NFR-1, OD-17), what a second case write for a round means after its name was taken, what promotion does with a round whose pair of files breaks the rules of ADR-0071 (it can have no case), the failed attempts of a round ≥ 1 that has no hypothesis record (they stay in `runs/` only; the order of writes is sub-question ⑩ of OD-8), where the case of a run goes whose valid `instance.json` states no op_signature (cited: ADR-0031 decision 5; sub-question ㉘ of OD-8, OD-26) or would state several (ADR-0031 decision 4; sub-question ③ of OD-6, #5 B-4), and what happens to a case when a promotion fails part-way (NFR-1, OD-17).
- **Owner-only (DRIVER §9)**: OD-25 — promotion PR policy and what is shared, including cases across forks or data repositories and two repositories that hold one `run_id`; #5 A and B items, C-6, OD-3. Nothing of them is touched.
- **The content of `best.json` and `technique_stats.json`**, the candidate archive and how it points at cases (OD-20, OD-7); `insights/` and the agent-memory ladder (OD-24).
- **An index of the runs that used a key** (sub-question ② of OD-8): the names of the cases show the `run_id`s of promoted rounds, but they are not made such an index here.
- **Retention, removal and migration** of cases and of `db/` (#5 A-1 re-evaluates the layout at P2; OD-11).
- **Further members of a case**: failure records, build and result records of attempts (PLAN P1-8, OD-13), the source commit or harness version of the source run.
- **Reading a case** whose own version, a copy's version or the source run's layout version is one the reader does not know, or whose source commit or harness differs from the reader's (OD-11).
- **Injection in any form** — at instance start, at a gate or during a run (owner, HQ, per the OD-30 section).
- **The S6 metric**, its boundary cases, repetitions and control (P2-8).
- Code, tests, schema files and prompts (P2-7's later slices); any change to an accepted record or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-11, FR-13, FR-15, FR-17, FR-18, NFR-1, NFR-2, C-3; register rows OD-4, OD-7, OD-11, OD-17, OD-20, OD-23, OD-24, OD-25, OD-29, OD-30.
- [OpenDecisionProposals](../OpenDecisionProposals.md#od-30) OD-30, OD-7, OD-20; [StandardScenarios](../StandardScenarios.md) S0, S5, S6, S11.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3, 4, 7; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 2, 4); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (Context; decisions 2, 5, 8, 9); [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decisions 3, 4); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 2, 3); [ADR-0027](ADR-0027-od8-run-id-form.md) (example); [ADR-0029](ADR-0029-od8-spec-file.md) (decisions 2 to 7); [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decisions 3, 5); [ADR-0059](ADR-0059-od30-round-hypothesis-record.md) (decisions 1 to 5; Example; Boundaries); [ADR-0071](ADR-0071-od30-hypothesis-verdict-record.md) (decisions 1 to 6; Example; Boundaries).
- Owner decision 2026-10-13 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569 · #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-8, P2-7, P2-8; `hilclaw/layout.py`, `hilclaw/hypotheses.py`, `hilclaw/verdicts.py`, `hilclaw/verdicts_hypotheses.py`; tasks T-0184, T-0218.
