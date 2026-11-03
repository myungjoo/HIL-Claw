# ADR-0195: Storage clean-up of PLAN P3-14 — the GC of C-3 as a command a person or a script starts, reporting by default and removing on request; a grace period in whole days given on its command line; a run's end read from the `run_status` `"over"` that `HEAD` holds and the commit that wrote it; `gc_at` the UTC clock read after each removal and never changed afterwards; a hash removed only when every record of every run that names it is `intermediate` or `failed` in a run past its grace; one local commit of the edited `artifacts.json` files and no push; and the design of the installer and image half for the next task

## Status

- **Accepted on 2026-11-03** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it**, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it (`hilclaw/blob_gc.py`, `artifacts.set_gc_at`).
- **Three kinds of content.**
  - **Owner**, cited word for word: C-3 / #5 A-2 ("retention class: `best`/`final` = 영구, `intermediate`/`failed` = run 종료 후 유예기간(기본 30일, 설정 가능) 뒤 GC 대상 — MVP는 class 기록만 하고 GC 도구는 후속, GC 시 `gc_at` 기록 커밋으로 감사 흔적 보존(NFR-2)", cited: [Requirements](../Requirements.md) C-3); #5 A-3 ("공동 repo(remote)로의 push는 시스템이 자동 수행하지 않는다", cited: [ADR-0127](ADR-0127-od8-commit-step.md) Context C1); D29 (오너 2026-11-03: "그리고 1: OK, 2: OK. 단 task별로 분리된 subdirectory사용 강제.", cited: DRIVER §5 "스토리지"); the owner's confirmation of the item PLAN P3-14 (2026-11-03). The owner's answers are not subject to the objection window.
  - **The integrator's reading, cited and not this record's**: PLAN P3-14 — "어느 run에서든 `best`·`final`인 해시는 지우지 않고(C-3에서 읽은 통합자 독해), 오너의 data 저장소(`HIL-Claw-data`)에 있는 사례와 감사 기록도 지우지 않는다(FR-18, NFR-2)"; "설치된 도구와 도구 이미지의 삭제는 런타임에서는 FR-4·NFR-4의 허락을, 드라이버에서는 HQ로 오너 승인을 받는다"; "상한을 둘지와 그 값은 OD-33 ③이다"; and DRIVER §5 D29's integrator's application (tool images tagged by tool name and version, one version never installed twice or held in two images, retiring an old tool image version is P3-14 with the owner's approval).
  - **This record's own**: decisions 1 to 11, every sentence no source is named with.
- **What it answers**: the GC points [ADR-0005](ADR-0005-od8-artifacts-record.md) Boundaries left (no OD is registered for them, and none is registered here), the part of [ADR-0099](ADR-0099-od8-moment-form-of-other-files.md) decision 3 it left to the GC design ("which reading of the clock in its work becomes the value, what happens to a `gc_at` when the content is stored again"), and the design of P3-14's second half (decision 10), whose code is the next task's. **Left open**: a storage cap and its value (OD-33 ③, asked as HQ-0094 ③, not asked again); the runtime's acquisition of vendor SDKs (HQ-0094 ①·②) and the WSL2 `libc++` install (HQ-0098), not asked again.
- **A-13 reading: no frame change.** No member, value, version or event kind of `artifacts.json`, `STATE.json`, `instance.json` or `events.ndjson` is added or changed. The GC makes the two edits ADR-0005 decision 7 already allows, and only the first of them (adding `gc_at`, in the form ADR-0099 fixed). The report of decision 2 is no data-plane file. No approved open list is used.
- **Session entry check** (CLAUDE.md), on 2026-11-03 at `main` `046a354e`: open PRs: none; no open `nightly-failure` issue; no `실패` item in `PROCESS/RuntimeAcceptance.md`; #4 last comment 2026-07-31, #5 2026-11-03, #7 2026-09-07, #8 closed. Unresolved HQs: HQ-0081, HQ-0088 to HQ-0098. Of them, HQ-0089 (a `build_settings` blob) and HQ-0097 (V6 (b), a `given_code` blob named by an `instance.json` member) would add places that name a blob; decision 7 states the rule they meet when answered. None is asked again.
- **Code and tests** land with it: `hilclaw/blob_gc.py` and `artifacts.set_gc_at` (decisions 2 to 9), tested on temporary data roots and temporary git repositories. Nothing was run on a real data root, image or installer, and no `claude`, board or accelerator was used (D16). The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0005** fixed the record (`sha256`, `size`, `type`, `round`, `retention_class`, optional `gc_at`), identity by `sha256` within a file, "The same `sha256` may be recorded in the files of two runs" (decision 6), the allowed changes (decision 7: add `gc_at`; replace the class; never remove or move a record) and the order "the blob is stored first, then the record is written" (decision 8). Its Boundaries list the GC: "the tool, when it runs, the grace period and where it is configured, what "run end" means for it, the time form of `gc_at` within a *string*, what happens to a record when its content is stored again after a GC, and how a hash recorded by several runs with different classes is treated".
- **ADR-0099** decision 3 fixed the form of `gc_at` (`YYYY-MM-DDThh:mm:ssZ`, UTC, ADR-0006 decision 3) and `hilclaw/artifacts.py` already checks it. It left the clock reading and a `gc_at` after the content is stored again.
- **ADR-0004**: three top-level data directories `runs/`, `db/`, `blobs/`; `blobs/sha256/` is not in git; "A file that needs a binary names it by hash" (decision 6); "no whole-directory scan is allowed" (Context, from #4 §1).
- **ADR-0121**: `run_status` `"over"` in `runs/<run_id>/STATE.json` says the run is over; "A run that is over is not written again" (decision 3); the Round-Manager writes it in the write that ends the last round. `round.end` appends no line to `events.ndjson` (`hilclaw/round_end_tool.py`), so the log holds no line at the moment of the end.
- **ADR-0127** and [ADR-0143](ADR-0143-od8-first-case-turn-end-commit.md): `run.commit` commits what is owed below `runs/<run_id>/`; it never takes in anything below `blobs/`. ADR-0121 decision 5 leaves open (⑪) a run whose `"over"` is written and whose commit is still owed.
- **ADR-0039**: on one machine `blobs/sha256/` is the only store; push and fetch copy nothing. **ADR-0095**: the store step overwrites a regular file at the place of a hash that is not intact and refuses any other entry.
- **The code of today**: no module of `hilclaw/` other than `cas` and `artifacts` stores a blob or writes a record, and no accepted record defines a member of any other data-plane file that holds a blob's hash ([BlobTypes.md](../BlobTypes.md) has no row).

## Decision

### 1. Scope and terms

- **The GC** removes blobs of `blobs/sha256/` whose records allow it and adds `gc_at` to those records. It removes nothing else, ever: no file below `runs/` or `db/`, no record, no directory, no blob the plan did not name.
- A run is **ended** when the `STATE.json` that the commit `HEAD` of the data repository holds for it is a valid version-1 file whose `run_status` is exactly `"over"` (ADR-0121 decision 2). Its **end** is defined in decision 4. A run is **past its grace** when it is ended, its `artifacts.json` in the working tree holds the same records, in the same order, as the one `HEAD` holds (a file missing on one side and holding records on the other differs), and the grace period (decision 3) has passed since its end.
- A hash is **eligible** under decision 6, **removable** under decision 8.

### 2. (a) The tool and when it runs

- **Entry point**: `python -m hilclaw.blob_gc --data-root <path> [--grace-days <n>] [--remove]`, with the module's functions `plan`, `remove`, `commit` and `collect` beside it. The data root is always named on the command line; no configuration is read, so a destructive command never acts on a root it guessed.
- **A person or a script starts it.** No runtime step, Round-Manager, hook or registry tool starts it, and it is not an FR-10 tool and not in the registry (as ADR-0127 decision 4 reads `run.commit`). The reason: the GC deletes, a run has nothing to gain from deleting during its own rounds, and the owner's "자동 호출하지 않으며, 사용자 명령으로 실행" for the store's other operations (#5 A-3, cited: ADR-0039 decision 8) fits it. The driver never starts it on a real data root (D16).
- **A report comes first.** Without `--remove` it plans and writes the report and changes nothing. With `--remove` it plans, removes, records and commits in that one call, and the same report holds what it did. Standard output gets one JSON document (no `schema_version`; it is no data-plane file and goes nowhere else). Exit statuses: `0` nothing to report beyond what was done, `10` a condition was reported (decision 8; a run of decision 4 that is undetermined or unreadable; a blocked plan), `20` an argument refused and nothing read, `21` a fault (no data root, no git working tree, `git` not runnable, the report not written). None is 1 or 2, the interpreter's, as in `hilclaw.toolchain_check`.
- **Not with a run in progress.** The GC takes no lock (OD-17): it is started when no run of the data root is going (decision 11).

### 3. (b) The grace period

- **Unit: whole days** of 86400 seconds; **default 30** (owner, C-3); **set by `--grace-days <n>`** at each invocation, `n` from 1 (a decimal integer of at most nine digits; `0`, a sign, a fraction or anything else is a usage error and nothing is read).
- It is not written into any data-plane file: a member for it would be a frame change, and the value is a property of one invocation, not of a run. "설정 가능" (C-3) is met by the argument; a configuration file entry is not added, since a person or script that starts the GC names the root anyway.

### 4. (c) Run end

- **What "run end" means**: the run is ended in the sense of decision 1. A run that is not ended — no `STATE.json` in `HEAD`, or no `run_status` in it — is **open**, and its blobs are kept. A `STATE.json` in `HEAD` that is invalid, of another version, or holds a `run_status` other than `"over"` makes the run **undetermined** (as ADR-0121 decision 2 has its readers stop on an unknown value): its blobs are kept and the run is reported.
- **Its moment**: the committer time of the last commit reachable from `HEAD` that changed `runs/<run_id>/STATE.json` (`git log -1 --format=%ct HEAD -- <path>`). By ADR-0121 decision 3 an ended run is not written again, so that commit is the one that holds `"over"`. It comes no earlier than the write of `"over"`, so the grace period never starts before the end. A committer time that cannot be read makes the run undetermined.
- **Why `HEAD` and not the working tree**: the GC edits only committed history's runs; an `"over"` that is written but not committed (ADR-0121 decision 5, ⑪) is not yet durable (#5 A-3) and the run counts as open until it is. **Why not `events.ndjson`**: no line is appended at the end (Context), and the last line's `time` precedes it.
- **A run whose `artifacts.json` differs from `HEAD`** (a change after the commit that ended it, a deleted file or run directory, a file `HEAD` does not hold — ignored by `.gitignore` or never added) is undetermined and its blobs are kept: the GC's commit would otherwise take in a change it did not make. The comparison is of the records as parsed, not of `git status`, so a path git is told to skip (`skip-worktree`, `assume-unchanged`) or a line-end filter neither hides nor causes a difference.
- **A run that never ends keeps its blobs.** No record here lets the GC remove a blob of a run that is open, however old. A later record that defines another end of a run (ADR-0121 decision 4, "Every other end of a run stays open") revisits decision 4.

### 5. (d) The clock reading and (e) content stored again

- **(d)** `gc_at` is the reading of the UTC clock of the GC's process **immediately after the unlink of that blob succeeded**, one reading per blob, in the form of ADR-0099 (seconds, no fraction). Every record that gets a `gc_at` for that blob gets the same value.
- **(e) A `gc_at` once written is never changed or removed** (this answers what ADR-0005 decision 7 left open). It states that a GC removed the blob at that moment; that the content was stored again later is not a change of that fact. A reader asks `hilclaw.cas.has_blob` whether the blob is there now (ADR-0005 decision 8).
- **What follows for the record**: a run that stores the content again and already holds a record of it gets no new record and no change (ADR-0005 decision 6), so its record keeps its `gc_at` while the blob is present. A run that had no record gets a new one without `gc_at`.
- **What follows for a later GC**: the blob is eligible again only under decision 6, counting every record, those with `gc_at` included. When it is removed again, `gc_at` is added to the records that lack one; the others keep theirs. A removal that adds no `gc_at` is still in the report.

### 6. (f) A hash recorded by several runs

- **Eligible** means: every record that names the hash — in the working tree's `artifacts.json` and in the one `HEAD` holds, of every run either of them names — has the class `intermediate` or `failed`, and every such run is past its grace. One record of class `best` or `final` anywhere keeps it, whatever its `gc_at` (the integrator's reading of C-3, PLAN P3-14). One record in a run that is open, within its grace, undetermined, or whose file differs from `HEAD` keeps it.
- **Which records get `gc_at`**: on removal, every record of every run that names the hash and has no `gc_at` (all are `intermediate` or `failed` by the rule above). Each run's file says by itself that the blob is gone, since each file is complete by itself (ADR-0005 decision 6).

### 7. (g) What the GC keeps, and why

- **Places that can name a blob by hash today**: the records of `runs/<run_id>/artifacts.json` (ADR-0005), and by ADR-0004 decision 6 any later file "that needs a binary". No accepted record defines such a member in any other file today — not in `STATE.json`, `instance.json`, `events.ndjson`, a result, a round file, or below `db/` (case files, `hw_profile.json`, `op_signature.json`, `best.json`, `technique_stats.json`) — and no code writes one (Context).
- **The rule for those places**: the GC reads only the classes of `artifacts.json`, so **a need for a blob is stated by the class of a record**. A later record that makes another file name a blob by hash (for example the answers to HQ-0089 or HQ-0097 V6 (b)) states that the run records that blob in its `artifacts.json` with the class `best` or `final` for as long as the naming file needs it, or revisits this record. This keeps the GC from walking `db/` or the round trees (ADR-0004 Context), and keeps FR-18's cases and the audit history intact (PLAN P3-14).
- **Kept by construction**: a blob no `artifacts.json` names (ADR-0005 decision 8: another run may record it, or a failure fell between store and record); a blob of `best` or `final`; a blob of an open, undetermined or in-grace run.
- **Fail safe**: an entry of `runs/`, in the working tree or in `HEAD`, that could hold records and cannot be read — a directory whose name `hilclaw.layout.check_run_id` refuses (ADR-0004 decision 8), a symbolic link, an entry that cannot be looked at, an `artifacts.json` on either side that is no regular file, invalid or unreadable — leaves the GC unable to bound the hashes held, so **nothing at all is removable** and the plan is reported as blocked. A regular file directly in `runs/` holds no records and is passed over. A missing `runs/` holds none.
- **Listing**: `runs/` is listed in the working tree and in `HEAD` (`git ls-tree HEAD -- runs/`), one directory of known path each; each run's `artifacts.json` (both sides) and `HEAD`'s `STATE.json` are read by path. No tree is walked, `blobs/` included. A run that only `HEAD` holds, or only the working tree, is read like any other, so a deleted file or directory hides no record.

### 8. Removal and its failures

- For each removable hash: the blob is re-hashed (`hilclaw.cas.verify_blob`), the file at its place is unlinked, the clock is read (decision 5), then `hilclaw.artifacts.set_gc_at` adds `gc_at` to each record of decision 6. **The record is written after the removal**, mirroring ADR-0005 decision 8, so a `gc_at` never precedes the removal; `set_gc_at` refuses while the blob is in the store.
- **A blob that is gone** when planned: not removable. It is reported when a record that names it has no `gc_at` (removed by hand, never fetched into this checkout, or a GC died between unlink and record), and no `gc_at` is written, since no GC removed it. A blob gone whose records all have `gc_at` is the normal state after a GC and is not reported.
- **A blob that is not intact** (`verify_blob` false, or its read fails): kept, reported, no `gc_at`. Its bytes are no blob of that hash (ADR-0095 decision 2), and the next store of the content replaces them. The GC does not delete what it cannot show is the blob.
- **A change after the plan** (gone or altered before the unlink), an **unlink that fails** with an `OSError`: the blob is reported as failed and its records are not changed.
- **A record that cannot be written** after the unlink: reported with the run and the hash; the blob stays removed without `gc_at` in that run, the harmless state of ADR-0005 decision 8's order. The other records and blobs go on.

### 9. (h) Commit and push

- **The GC commits its own edits** at the end of the call that made them: one local commit on `HEAD` holding the `artifacts.json` files that got a `gc_at`, and nothing else, whatever else the working tree or the index holds. It is built in a temporary index from `HEAD`; `HEAD` moves by `git update-ref` from the old value; then the index entries of those paths are set to the commit (a failure of that last step is reported; the commit stands). `git` runs with an argument list, no shell, and the variables that point it at another repository removed, as `hilclaw.run_commit` runs it. No porcelain `git commit` runs, so its hooks (`pre-commit`, `commit-msg`, `post-commit`) do not; `git update-ref` still runs a `reference-transaction` hook if the data repository has one, and `git add` applies the repository's filters. The message is fixed and read by nothing.
- **Why the GC and not `run.commit`**: an ended run gets no further turn (ADR-0121 decision 5, P2), so no `run.commit` would ever take the edit in, and C-3 asks for "GC 시 `gc_at` 기록 커밋".
- **A commit that is not made** (`git` fails a step before `HEAD` moves, `HEAD` names no commit): reported; `HEAD` is unchanged, the blobs stay removed and the edited files stay uncommitted for a person to commit. Decision 4's check then makes those runs undetermined in the next plan, which removes nothing more of them until they are committed.
- **No push** (#5 A-3, cited: ADR-0127 decision 7). **Nothing under `runs/` or `db/` is ever deleted**, and `blobs/` holds nothing in git (ADR-0004 decision 6), so the commit holds edits only.

### 10. (i) Installers and images — the design of the next task

The second half of P3-14 is a separate code task, planned from this decision. It removes nothing on its own.

- **What it covers**: ① installers and archives a tool was installed from; ② runtime images — the stand-in image (`HILCLAW_STANDIN_IMAGE`, `hilclaw.standin_image`) and the coder image (`HILCLAW_CODER_IMAGE`, `hilclaw.coder_runtime`); ③ the driver's tool images (D29). Not covered: work images and task directories of the driver (DRIVER §5's sweep, already a rule), the CAS (decisions 1 to 9), the data repository.
- **A read-only report command** of layer 2 (one JSON document on standard output, outside the data plane, exit statuses as decision 2) shows, for the directories and image references named on its command line: for each file, its size and SHA-256, and **duplicates** as files with the same SHA-256; for each image, its image id, size, tags, and the components and versions `hilclaw.toolchain_check` reads in it (the adapters' own probes, **no second list of commands**); **duplicates** as two image ids holding the same component at the same version (D29: one version never in two images) — two tags of one image id are one image and no duplicate; **retirement candidates** as a tool image whose tag names a tool and a version, beside one of the same tool at a later version that holds every component it holds. An image a runtime variable names now, and a version the newest image of a tool holds, are never candidates. The command names images given to it and does not list the machine's images unless a person passes the list: what it reads is what it was asked about.
- **Approval and removal**: the report proposes; it never deletes. **In the runtime**, removing an installed tool, an installer or an image is an environment change and needs the user's permission (FR-4, NFR-4): the run waits for the answer, and without it nothing changes. **In the driver**, the proposal is an HQ to the owner (PROCESS/DRIVER.md §8) naming each tag or path, its size and what replaces it; on approval the executor of the approving task removes each by its tag or path (no prune, no wildcard), and records what it removed in `Result`.
- **Left open**: a cap on storage and its value (OD-33 ③, HQ-0094 ③); where the runtime keeps installers, which is bound to the runtime's acquisition (HQ-0094 ①); the format of a tool image tag beyond "tool name and version" (D29), which the next task reads from the images that exist.

### 11. Limits

- **No lock** (OD-17): a run that stores and records a hash between the plan and the unlink loses the blob; a run that ends and is committed during the call is read as it was at the plan. The GC is to be started when no run is going (decision 2).
- **One machine, one checkout**: the GC reads this checkout's `HEAD` and store. Another clone's runs and records are not seen; a blob another clone still records under `best` may be removed here (#5 B-2; ADR-0039 decision 8: there is one store per machine).
- **Time**: the grace is measured against the commit time and the GC's clock; a wrong clock on either side moves the removal.
- **Cost**: every eligible blob is re-hashed at the plan and again before its unlink, so the time grows with the bytes removed.

### Walk-through

Three runs, each committed with `"over"` on 2026-09-02, the GC started on 2026-11-01 with the default 30 days. `A` is `intermediate` in r1; `B` is `best` in r1 and `failed` in r2; `C` is `failed` in r3, whose `artifacts.json` was edited after its last commit; `D` is in the store and named by no record.

| Hash | Outcome | Records |
|---|---|---|
| `A` | Removed | r1's gets `gc_at` |
| `B` | Kept: `best` in r1 | none change |
| `C` | Kept: r3 undetermined (its file differs from `HEAD`), reported | none change |
| `D` | Kept: no record names it | — |

One commit holds `runs/r1/artifacts.json`; exit status 10 (r3 reported). Without `--remove` the same report, `A` under `removable`, nothing changed.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| (a) | The Round-Manager or `run.commit` collects at the end of each run | It deletes inside a run's turn, against "사용자 명령으로 실행" for store operations (#5 A-3), and a run cannot see other runs that hold its hashes as `best` unless every run is read at every end. |
| (a) | Removal by default, `--dry-run` to report | A mistaken invocation would delete. |
| (b) | A grace period in seconds, or an ISO 8601 duration | The owner gave days; an amount in seconds invites a value no one means, and a duration notation is a second notation ADR-0033 already rejected for an amount. |
| (b) | A member in `instance.json` or `artifacts.json` for the grace | A frame change (A-13) for a value of one invocation. |
| (c) | The last `time` of `events.ndjson` | No line is written at the end (Context); the last line precedes the end, so the grace would start early. |
| (c) | The working tree's `STATE.json` | An `"over"` not yet committed is not durable; the GC would edit a run whose ending commit is still owed (⑪). |
| (c) | The file's modification time | Not in git, lost on clone, changed by a checkout. |
| (d) | One clock reading at the start of the call | The removal of a large store takes time; `gc_at` would precede the removal of the later blobs. |
| (e) | Replace or remove `gc_at` when the content is stored again | The history keeps the old value anyway (NFR-2); a changing `gc_at` would answer "is it there now", which `has_blob` answers (ADR-0005 decision 8). The store step does not read records, so it could not do it. |
| (f) | Per-run decision: remove when this run's record allows it | Removes a blob another run holds as `best` (C-3, PLAN P3-14). |
| (g) | Read only the working tree's records, or tell a difference by `git status` | A deleted `artifacts.json` or run directory would hide a `best` record that `HEAD` holds, and an ignored or skipped file would show no difference. |
| (g) | Walk `db/` and the round trees for hashes | Forbidden by ADR-0004 Context; and no file there names a blob today. |
| (g) | On an unreadable run, go on removing the hashes the other runs' records allow | The unreadable file's hashes are unknown, so no hash can be shown to be held by no `best` or `final` record or no open run. |
| (8) | Remove a blob that is not intact and record `gc_at` | The removed bytes were no blob of that hash; `gc_at` would say a blob was removed that was not there. |
| (h) | Leave the edit for a person to commit | C-3 asks for the commit; an uncommitted `gc_at` is lost with the working tree. |
| (h) | `git commit --only` | Runs hooks of the data repository and needs the paths tracked; the temporary index gives the same result without them. |
| (i) | Delete duplicates and old images automatically | FR-4, NFR-4 and PLAN P3-14 require permission or approval. |

## Consequences

- **Code of this task**: `hilclaw/blob_gc.py` (decisions 2 to 9) and `hilclaw.artifacts.set_gc_at` with `BlobPresentError` (decision 8). `hilclaw/artifacts.py`'s docstring "never writes ``gc_at`` (the MVP has no GC tool)" is corrected. Nothing else of `cas`, `artifacts`, `run_commit` or any runtime path changes.
- **Language** (CLAUDE.md): Python, like `cas`, `artifacts` and `run_commit` that the GC builds on, and for `git` through `subprocess` without a shell.
- **Not edited and now less exact**: ADR-0005 Context ("The MVP records the class and builds no GC tool"), decision 3 ("no MVP tool writes the member"), decision 7 ("Whether a `gc_at` once written may be changed or removed … is left to the GC design") and Boundaries (the GC bullet); ADR-0099 decision 3 ("What stays with the GC design") and Boundaries (the GC bullet); ADR-0004 decision 1's table ("Retention, GC … C-3" left to later). The sentence of C-3 is not edited; a more precise wording for the integrator: "… GC 도구는 `python -m hilclaw.blob_gc`(ADR-0195) …".
- **Next task**: the report command of decision 10 and its tests; it plans its own approval HQ form for the driver's images.
- **Runtime acceptance items**: none. The GC needs no `claude`, board or accelerator, and its tests run on temporary repositories on every CI machine.
- **HQ**: none. No point needed a frame change or an owner-only value.

## Boundaries (not decided here)

- A storage cap and its value (OD-33 ③, HQ-0094 ③); the runtime's acquisition and licences of vendor SDKs (HQ-0094 ①·②); `libc++` on WSL2 (HQ-0098).
- Locking and concurrency of the GC with runs and with another GC (OD-17).
- Other ends of a run (ADR-0121 decision 4) and a run's own lifetime beyond `"over"`; resumed or branched runs (OD-8 ①).
- Class policy: who assigns `best` or `final` and when (OD-20, OD-29, OD-23).
- `blob.push` / `blob.fetch` backends and several stores (#5 B-2).
- Files beyond `artifacts.json` that name a blob (decision 7 states only the rule they meet).
- The report command of decision 10 and its code; any deletion of a real image, installer or data.

## References

- [Requirements](../Requirements.md): C-3, FR-4, FR-18, FR-19 ③, NFR-2, NFR-4; OD-8, OD-17, OD-20, OD-23, OD-29, OD-33.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (Context; decisions 1, 6, 8); [ADR-0005](ADR-0005-od8-artifacts-record.md) (decisions 6 to 8; Boundaries); [ADR-0006](ADR-0006-od8-events-log.md) (decision 3); [ADR-0033](ADR-0033-od8-instance-record-wall-clock-budget.md); [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decisions 2, 6, 8); [ADR-0095](ADR-0095-od18-cas-store-over-a-damaged-place.md) (decision 2); [ADR-0099](ADR-0099-od8-moment-form-of-other-files.md) (decision 3; Boundaries); [ADR-0121](ADR-0121-od8-run-over-member.md) (decisions 2 to 5); [ADR-0127](ADR-0127-od8-commit-step.md) (Context; decisions 4, 7); [ADR-0143](ADR-0143-od8-first-case-turn-end-commit.md); [ADR-0194](ADR-0194-od33-vendor-stack-evaluation-design.md) (decisions 7, 10 V3, V6).
- #5 A-2 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D29 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6590711662 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §5 (storage, D29), §6 (D20, D27, D29), §8, §9; PROCESS/PLAN.md P3-14; `hilclaw/cas.py`, `hilclaw/artifacts.py`, `hilclaw/layout.py`, `hilclaw/run_commit.py`, `hilclaw/run_state.py`, `hilclaw/round_end_tool.py`, `hilclaw/toolchain_check.py`; task T-0547.
