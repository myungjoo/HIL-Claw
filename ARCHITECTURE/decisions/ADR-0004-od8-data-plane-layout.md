# ADR-0004: Directory tree of the data plane with the candidate and attempt dimensions (P1 minimum of OD-8)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes the **P1 minimum** of OD-8 (Open Decisions register in [Requirements](../Requirements.md)): the directory tree of the data plane — paths, file names, the form of the numbers, the level each artefact belongs to, and one writer role per directory. What stays open, first of all: **the isolation means** (candidates ① and ② of OD-8, both kept), and every field and schema of the files named here (see Boundaries).
- It uses the directory names and key records of [ADR-0001](ADR-0001-od4-key-schema.md), the identification tuple and the "every spec is kept" rule of [ADR-0002](ADR-0002-od6-codegen-spec.md), and decision 5 of [ADR-0003](ADR-0003-od16-harness-calibration.md). Their objection windows run until 2026-10-13 (ADR-0001, ADR-0002) and 2026-10-14 (ADR-0003); if one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- FR-13: in P1 the directory tree of the data plane stands in for the database, mirrors the future DB schema and has the candidate multiplicity of a round (N of FR-1) as a first-class dimension. Which directories and files the tree has is OD-8.
- Fixed by the owner: one separate repository `HIL-Claw-data` with `runs/`, `db/` and `blobs/`, never mixed at the top level, so that a directory can later become a repository; `instance.json` records the source commit; the per-round promotion `runs/` → `db/` is one commit (#5 A-1). The repository exists with these three directories (D7). Binaries live at `blobs/sha256/<hh>/<hash>` outside git, and git holds `artifacts.json` records (C-3, #5 A-2). The durability boundary is the local commit (#5 A-3).
- Agreed in #4: two trees that are never merged, `runs/<run_id>/` (execution journal) and `db/<hw_profile_key>/<op_signature>/` (cross-run knowledge); owner and project are meta fields, not path levels; round directories are zero-padded; no full copy of artefacts per turn (§2a-§2c). One small `STATE.json` is the only entry point and no whole-directory scan is allowed (§1). A round has phase markers and an append-only `events.ndjson` (§3b). Roster revision: only the Round-Manager writes `STATE.json`, and expensive results are journaled by the tool layer.
- The "합의 레이아웃 (현재안)" of #4 is a draft: one flat directory per round. It predates the candidate dimension (OD-21), the attempt dimension (ADR-0002) and the CAS decision.
- ADR-0001 needs a place for the full record of each key. ADR-0002 needs one kept spec per (`run_id`, `round`, `candidate`, `attempt`), a place for the coder's output and for the build settings actually used.
- Confirmed parts of OD-16: the harness lives in the tool package; runtime seeds and input values do not exist as files; reads are not restricted.
- The registered proposal ([OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8)) holds two candidates for the isolation means: ① "layout = permission model" (OS boundary) and ② "scratch copy + diff import". Both give each actor one write root. Choosing between them rests on facts only the owner has (container availability, out-of-tree builds of the target toolchain — #5 B-1), so it is not made here.

## Decision

### 1. Top level and scope

- The data repository has exactly three data directories at its top level: `runs/`, `db/` and `blobs/`. Beside them only repository housekeeping files may exist (`README.md`, `.gitignore` and the like); they hold no run data and no knowledge. A fourth data directory needs a new record.
- This record fixes **paths and file names** and, for each file, what it is for and which role is meant to write it. It fixes no field of any file.
- A directory exists only when something was written into it; a missing directory means "nothing yet".

```
<data repository>/
  runs/
    <run_id>/                              one Loop instance (decision 8)
      STATE.json                           the single entry point; mutable
      instance.json                        immutable instance record
      events.ndjson                        append-only event log
      artifacts.json                       blob records of the run (decision 6)
      rounds/
        <RRRR>/                            0000 = bring-up round, then 0001, 0002, ...
          decision/
            decision.md                    decision log of the round (FR-11)
          coder/
            candidates/<CC>/attempts/<AA>/
              spec.json                    the spec of this coder call (ADR-0002)
              output/                      what the call produced
          measure/
            candidates/<CC>/attempts/<AA>/
              build.json                   build record, with the settings actually used
              sim.json  board.json  profile.json
          eval/
            candidates/<CC>/attempts/<AA>/
              eval.json                    evaluation record of the attempt
  db/
    <hw_profile_key>/
      hw_profile.json                      full hw_profile record (ADR-0001)
      <op_signature>/
        op_signature.json                  full op_signature record (ADR-0001)
        best.json  technique_stats.json    names of the #4 draft; content open
  blobs/
    sha256/<hh>/<hash>                     content-addressed store, not in git (C-3)
```

The files, their writers and what stays open for each (`…` stands for the path of decisions 2-4):

| Path | Purpose | Written by | Decided by / open in |
|---|---|---|---|
| `runs/<run_id>/STATE.json` | Where the run stands and what to load next | Round-Manager only (#4 roster revision) | Fields: PLAN P1-8, OD-17 (lock, budget — #8 M7), OD-3 |
| `runs/<run_id>/instance.json` | What the instance was started with; source commit (#5 A-1); layout version | The start of the instance, once | Fields: PLAN P1-8, OD-11 |
| `runs/<run_id>/events.ndjson` | Events of the run in the order they happen; an expensive result is appended as soon as it exists (#4 §3b) | Tool layer, append only | Fields: PLAN P1-8, OD-17 |
| `runs/<run_id>/artifacts.json` | One record per blob of the run (C-3) | Tool layer, with the blob store | Fields: PLAN P1-6; retention and GC: C-3 |
| `…/decision/decision.md` | Why these techniques (FR-11) | Selection role | Further files: OD-23 |
| `…/coder/…/spec.json` | Input of one coder call; never changed | Coder-call role | Schema: ADR-0002, PLAN P1-5; who composes it: OD-23 |
| `…/coder/…/output/` | Output of that call; source as text | Coder-call role | Files and form: OD-23; how it gets there: isolation means |
| `…/measure/…/build.json` | Build outcome and the settings actually used | Measurement role | Fields: code tasks, OD-23 |
| `…/measure/…/sim.json`, `board.json`, `profile.json` | Result of each step for the attempt | Measurement role | Content: OD-13; more records per step: OD-10, OD-11, OD-13 |
| `…/eval/…/eval.json` | Evaluation of the attempt (the evaluator's file in the #4 roster) | Evaluation role | Fields, and which file holds the correctness verdict of each execution point: OD-20, OD-13, OD-23; round-level files: OD-20, OD-29 |
| `db/<hw_profile_key>/hw_profile.json`, `…/<op_signature>/op_signature.json` | Full key records (ADR-0001) | Whatever creates the directory | When a key is first registered: OD-26 |
| `…/<op_signature>/best.json`, `technique_stats.json` | Best reference and technique statistics of the pair | Promotion step | Content: OD-20, OD-7 |
| `blobs/sha256/<hh>/<hash>` | Binary content, not in git | `hilclaw.cas` | Retention, GC, `blob.push` / `blob.fetch`: C-3, #5 B-2 |

### 2. The run tree

- Directly under `runs/<run_id>/` are the four run-level files and `rounds/`. Everything that changes after a round has ended is at run level (`STATE.json`, `artifacts.json`, appends to `events.ndjson`); no file fixed here needs a write into the directory of an earlier round.
- A round directory is named by the round number in decimal, zero-padded to **at least four digits** (#4 §2c). The first round is **`0000`**, the bring-up and baseline round of FR-1; this is the `id.round` of ADR-0002 unchanged.
- A run has one sequence of rounds, numbered by a single integer: the round is one number in the tuple of ADR-0002 and in "turn ≡ Round" of #4 §3, and the tree adds no level that the tuple does not have. So the tree has **no branch level**, and a round number is used once per run. How a branch or a continuation (FR-6) is represented — a new run, or rounds with later numbers in the same run whose starting point is named by `feedback.base` of ADR-0002 — is not decided here; the tree admits both.

### 3. The candidate and attempt dimensions

- Below a role directory of a round (decision 4), a candidate is `candidates/<CC>/` and an attempt of it is `attempts/<AA>/`: the `id.candidate` and `id.attempt` of ADR-0002 in decimal, zero-padded to **at least two digits**, both starting at `01`. A number that needs more digits is written in full and never truncated, so the tree sets no upper bound on rounds, N or repair calls (OD-29, OD-19).
- The tuple of ADR-0002 maps to a path by formatting alone: the spec of (`run_id`, `round`, `candidate`, `attempt`) is `runs/<run_id>/rounds/<RRRR>/coder/candidates/<CC>/attempts/<AA>/spec.json`, and the other artefacts of that attempt are at the same suffix below `measure/` and `eval/`. No listing is needed to find a named artefact. Which rounds, candidates and attempts exist is known from `STATE.json` or from listing one directory of known path, never from walking the tree (#4 §1).
- **Per attempt**: everything that comes from one source — the spec, the coder's output, the build record, the sim, board and profile results, and the evaluation. A repaired candidate has a new source, so each attempt has its own; the failed attempts stay (FR-6).
- **Per round**: the decision log, `decision/decision.md` — one choice of techniques covers all candidates of the round.
- **Per candidate**: no file is fixed. A candidate is the sequence of its attempts. Files of a role that concern a whole candidate or a whole round (a ranking, which attempts went to the board, cost per candidate) go directly under `candidates/<CC>/` or under the role directory; which exist is left to OD-20, OD-29 and OD-19.
- `sim.json`, `board.json`, `profile.json` and `eval.json` are the draft's names, kept for the first record of each kind for the attempt. Whether a step may leave more than one record for one attempt, and how further records are named, is left to OD-13, OD-10 and OD-11.
- `build.json` replaces the draft's `build.log`: the settings an attempt was actually built with need a structured record (ADR-0002 decision 6 (b)). Settings used at run time are recorded in the record of the step that used them.
- `build.json` is under `measure/` because it describes the build whose binary is executed and measured, and ADR-0002 makes the used settings a property of the build and measurement results, recorded with them. No source says which agent or tool runs that build (#4 §3c lists compile with the repair loop; the roster names no builder). If OD-23 gives it to the side that issues coder calls, a later record moves the file below `coder/`; builds the coder runs for itself during a call are part of its output.
- `profile.json` is under `measure/` as well: a profile is collected by running the attempt's binary at an execution point (`profiler.collect`, FR-10), like the sim and board results, and the roster assigns `profiler.collect` and `profile.json` to no agent (the evaluator's only listed call is `correctness.check`). The #4 sketch lists it next to `eval.json` without naming a writer; if OD-23 gives profiling to the evaluation side, a later record moves the file below `eval/`.

### 4. One writer role per directory

- A round is divided by **writer role** first, and by candidate and attempt below it: `decision/` (selection), `coder/` (the side that issues coder calls: it writes the spec before the call and holds the output after it), `measure/` (build and execution on sim and board), `eval/` (evaluation). The names are those of candidate ① item 1.
- This is a property of the paths only: every file of a round has exactly one role directory above it, role directories do not nest, and the files of one role in one round share one prefix, `rounds/<RRRR>/<role>/`. Both isolation candidates need one write root per actor, and either can use this prefix or a narrower one below it (one candidate, one attempt).
- A role is not an agent. Which agent or tool holds a role, whether a role is split between two, and whether the Round-Manager acts in a role itself is OD-23; a split would subdivide the role directory in a later record.
- The coder process (`claude -p`) holds no role: nothing in this tree is written by it directly under either candidate. How its files reach `output/` is the isolation means.
- Outside the role directories: the run-level files. `STATE.json` is written by the Round-Manager only, `events.ndjson` and `artifacts.json` by the tool layer (decisions 2 and 6), `instance.json` once at instance start.

### 5. The knowledge tree

- `db/<hw_profile_key>/hw_profile.json` holds the full hw_profile record and `db/<hw_profile_key>/<op_signature>/op_signature.json` the full op_signature record of ADR-0001 (key fields and attributes). They are written when the directory is created; the stored canonical form that ADR-0001 compares on a lookup is derived from them. A file name contains a dot and a key directory name never does (`[a-z0-9_-]`), so the two cannot collide.
- `best.json` and `technique_stats.json` keep the names and the place of the #4 draft, directly in the key directory. Their content, and any further file of a key directory, is OD-20 and OD-7.
- The role directories of a run do not apply here. `best.json` and `technique_stats.json` are written by the promotion step, in the same commit as the round it promotes (#5 A-1); a key record file is written by whatever creates its directory, which may be onboarding rather than a promotion (OD-26).

### 6. Blob records

- `artifacts.json` is **one file per run**, `runs/<run_id>/artifacts.json`, with one record per blob the run produced. C-3 lists the producing round as a member of each record, which a file per round would make redundant; and a record changes after its round (C-3: a GC adds `gc_at`), which a file per round would turn into a write into an earlier round directory.
- Reading of #5 A-1, detail 1, which says "`runs/` + `db/` + `blobs/`(메타)": that detail predates #5 A-2, which made the metadata of a blob a committed `artifacts.json` record and left its place open. This record takes from A-1 the three directories and "not mixed", and places the records with the run that produced the blobs; it is a reading of this record, not a statement of the owner.
- It is written by the tool layer together with the blob store, as `events.ndjson` is, so no role needs write access to it.
- A file that needs a binary names it by hash. `blobs/` holds nothing in git except the placeholder that keeps the directory; `blobs/sha256/` is ignored, including the temporary files `hilclaw.cas` creates there.

### 7. What is never a file in the data plane

- Seeds and input values of a verification run (FR-9; confirmed part of OD-16). ADR-0002 also keeps expected values out of the spec; what a result file may say about a failed check is its schema and is not decided here.
- The harness, its reference implementation and the calibration kernels: they are in the source repository (FR-9, ADR-0003 decision 5).
- Binaries in git (C-3), and copies of reference material whose original is elsewhere (FR-14 ①).
- Secrets — credentials, tokens, private endpoint data: the repository is pushed at the owner's decision and its history is the audit log and is not rewritten (NFR-2; rationale of #5 A-2), so a secret committed once stays.
- Scratch, temporary and build-cache directories: no path of this tree is one, no file fixed here lives in one, and their content is never committed. Whether they are outside the checkout or inside it under an ignored name is decided with the isolation means.

### 8. `run_id`

Only its constraints as a directory name are fixed: `run_id` matches `[a-z0-9][a-z0-9_-]{0,63}` and is unique within `runs/` of a data repository. Lowercase letters, digits, `_` and `-` are valid in a file name on the POSIX environments of C-7 (Linux, macOS, WSL) and stay distinct on a case-insensitive file system; the first character rules out hidden and option-like names; the length keeps full paths short. Every such value is a *string* of ADR-0002. **The form stays open**: how a new id is built, how uniqueness is obtained, and whether ids sort by time.

### 9. Stability, versioning and the DB mirror

- This tree is **layout version 1**. The version is raised when a path, file name or number form fixed here changes; it is not raised when a file is added in a place this record leaves open.
- The version is recorded **per run, in `instance.json`**: a finished run is not rewritten into a newer layout, because its history is its audit record (NFR-2), so runs of different versions can stand side by side. The path `runs/<run_id>/instance.json` is the same in every layout version: a reader finds the version there before it uses any other path of the run. The name of that stamp, and whether it is a field of its own or follows from a `schema_version`, belongs to the instance schema and to OD-11. `db/` needs no stamp of its own in version 1: its two levels are fixed by FR-13 and ADR-0001, and its files carry their own `schema_version` (NFR-7 ②).
- What each level would become in a database (FR-13, NFR-6) — an illustration, not a P2 schema:

| Level | Would become |
|---|---|
| `runs/<run_id>/` with `instance.json`, `STATE.json` | one row of a run table (owner and project as columns) and its current state |
| `events.ndjson`, `artifacts.json` | an append-only event table and an artefact table, keyed by run |
| `rounds/<RRRR>/` | a round row keyed by (run, round) |
| `<role>/candidates/<CC>/attempts/<AA>/<file>` | one table per record kind, keyed by (run, round, candidate, attempt) |
| `db/<hw_profile_key>/`, `…/<op_signature>/` | a hw_profile row; an (hw, op) row with its best and its statistics |
| `blobs/sha256/` | an object store, unchanged |

### 10. Limits

The tree is a naming convention. By itself it does not enforce the single writer, isolates nothing, gives no concurrency control (the lock is OD-17; P1 assumes one run, C-2), makes no write atomic beyond what a git commit gives, and does not check the content of any file.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | A version or index file at the top level | A-1 keeps the top level to three directories that can each become a repository; a top-level file would belong to none of them. |
| 2 | Round directories from `0001`, the bring-up round kept apart | FR-1 and ADR-0002 number the bring-up round 0; a second numbering would need a mapping. |
| 2 | A branch level inside a run (`branches/<b>/rounds/…`) | The tuple of ADR-0002 has no branch member, so a spec could no longer be found from its tuple. How a branch is represented without such a level stays open. |
| 3 | The draft's flat round directory with one `spec.json` | Cannot hold one kept spec per tuple (ADR-0002) and has no candidate dimension (FR-13). |
| 3 | Unpadded numbers, or a fixed width | Unpadded names sort badly in listings; a fixed width is an upper bound that OD-29 and OD-19 have not set. |
| 3 | Results per candidate instead of per attempt | A result would not say which source it measured once a candidate has been repaired. |
| 3 | `build.json` below `coder/`, or a role directory `build/` of its own | Below `coder/`: the record of the binary that is measured would sit with the side whose output is being checked (OD-16 threat A), and no source makes that side the builder. A role of its own: a fifth write root for one file. Revisited with OD-23 (decision 3). |
| 4 | Candidate first: `rounds/<RRRR>/candidates/<CC>/attempts/<AA>/{coder,measure,eval}/` | Keeps a candidate in one place, but an actor that serves a whole round would need one write root per attempt, so the single root holds only if every actor is invoked per attempt — a constraint on OD-23 and OD-29. Role first serves both cases. The candidate remains a fixed level of every path (FR-13 "or equivalent"). |
| 4 | No division by writer | The draft lets one actor overwrite another's result (candidate ①, item 1); neither isolation candidate could give an actor a single root. |
| 4 | `spec.json` in `decision/`, or in a directory of its own | Repair specs are issued by the side that manages coder calls (#4 roster revision); a directory of its own would give that side two roots. |
| 5 | One file per key directory holding both records | The hw record would be repeated in every op directory and could diverge. |
| 6 | `artifacts.json` per round (the draft), per attempt, or under `blobs/` | Per round and per attempt: see decision 6, and listing the blobs of a run would need a walk. Under `blobs/`: `runs/` could no longer become a repository with its own records. |
| 8 | A chosen id form (timestamp, counter, random) | No source gives one (ADR-0002), and the tree needs only a valid directory name. |
| 8 | Any *string* of ADR-0002 as the directory name, or no length limit | A string may hold `/`, `:` or spaces, and two ids that differ only in case collide on a case-insensitive file system (C-7). The limit of 64 is this record's own choice, not a sourced value. |
| 9 | One layout version for the repository | Forces every old run to be migrated at once, which decides part of OD-11. |

## Consequences

- A code task can build every path from the tuple of ADR-0002 and the names of `hilclaw.keys`, without reading a file (PLAN P1-8). `hilclaw/keys.py` and `hilclaw/cas.py` are consistent with the tree and unchanged; what is still missing is a module that builds paths, the writer of the two key record files with the collision check of ADR-0001, and the `artifacts.json` record (PLAN P1-6).
- The draft layout of #4 is superseded where this record differs: role directories, the candidate and attempt levels, `build.json`, the run-level `artifacts.json`, the two key record files, round `0000`. The issue body is not edited.
- The README of `HIL-Claw-data` still lists the layouts as open; updating it, and adding nothing else to that repository, is a follow-up. The repository as it is today fits the tree: its `.gitkeep` placeholders in `runs/` and `db/` start with a dot and can be neither a `run_id` nor a key directory name.
- The tree has no branch level (decision 2). Whether a branch or a continuation (FR-6) is a new run or later rounds of the same run, and how it names its starting point, is not decided (Boundaries).
- A candidate's files are spread over three role directories; reading one candidate's story means three known paths.

## Boundaries (not decided here)

- **The isolation means** (rest of OD-8, with OD-14, OD-18, OD-23): candidate ① versus candidate ②, read-only mounts, containers, scratch copy and diff import, where scratch and build caches are, per-agent tool allowlists, `PreToolUse` path checks, the check of a round's diff against allowed paths. Waits for two facts from the owner: container availability and #5 B-1. Both candidates stay registered.
- **Owner-only (DRIVER §9)**: OD-3 / #5 A-5 (gates and any gate record); OD-25 (physical form of the data plane, fork or branch model, promotion PR policy, what is shared); #5 B-8 (datasets and where they would live); #5 B-1, B-2, B-3; C-6; #5 A-8.
- **Fields and schemas** of every file named here (PLAN P1-8, P1-6, P1-5 and their code tasks; OD-17, OD-20, OD-7, OD-11); whether one instance covers several values of M (the instance schema); the lock.
- **Sub-questions this record raises** (registered under OD-8): whether a branch or a continuation of a run is a new run or later rounds of the same run, and how it names its starting point (with OD-20); whether a key directory holds an index of the runs that used the key, or a query reads the runs (S5 step 1; with OD-20); where a baseline that is not a candidate of the run is recorded (OD-28); where excerpt snapshots of reference material would live (OD-12); how further records of one step for one attempt are named (decision 3; OD-13, OD-10, OD-11).
- Retention, GC, `gc_at`, and the meaning of a local `blob.push` / `blob.fetch` (C-3, #5 B-2). The commit and push cadence beyond #5 A-3.
- The agent roster and each agent's files beyond the directory of its role (OD-23); parallel or sequential candidates and promotion (OD-29, OD-15); measurement content (OD-13); budget enforcement (OD-19); the onboarding registry (OD-26).
- The values of the first GEMM, the harness design (PLAN P1-3), the FR-10 contract (PLAN P1-1).
- Code, tests, schema files, CI, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-1, FR-5, FR-6, FR-9, FR-11, FR-13, FR-14, NFR-1, NFR-2, NFR-6, NFR-7, C-2, C-3, C-7; register rows OD-3, OD-7, OD-8, OD-10, OD-11, OD-12, OD-13, OD-14, OD-17, OD-18, OD-19, OD-20, OD-21, OD-23, OD-25, OD-26, OD-28, OD-29.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8) (registered proposal: candidates ① and ②); [StandardScenarios](../StandardScenarios.md) S1, S3, S5, S8, S10; [UsageCases](../UsageCases.md) glossary "데이터 plane", "CAS".
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format, decision 3); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 1, 5, 6; `id`); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decision 5).
- #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-2 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · D7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5996366069 · #5 body items A-5, B-1, B-8.
- #4 body §1, §2a-§2e, §3b, §3c, "합의 레이아웃 (현재안)", §4; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; candidate ① and the owner premises https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #8 M7.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-5, P1-6, P1-8; `hilclaw/keys.py`, `hilclaw/cas.py`; task T-0021.
