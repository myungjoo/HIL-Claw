---
id: T-0547
title: Write the storage cleanup ADR of PLAN P3-14 (C-3 GC points left open by ADR-0005, duplicate installers and images, tool image retirement) and land its first code slice, the CAS GC of intermediate and failed blobs
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, C-3, NFR-2, NFR-4, OD-33, D29, "PLAN P3-14"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0195-*.md
  - hilclaw/blob_gc.py
  - hilclaw/artifacts.py
  - tests/test_blob_gc.py
  - tests/test_artifacts.py
estimatedSize: {loc: 600, files: 3}
hq: []
---
## Why

**PLAN P3-14** ("스토리지 정리"; the owner confirmed the item on 2026-11-03, the item's composition is the integrator's). Storage use must not grow without bound. The item asks for two things:

- duplicate management of downloaded installers and images;
- the GC of C-3: removing `intermediate` and `failed` blobs after their grace period.

The item says the GC's open points in ADR-0005 Boundaries are decided **first** by a §9 ADR. Those points are: the tool and when it runs, where the grace period is set, what "run end" means, the time form of `gc_at` inside a string, what happens when content is stored again after a GC, and hashes that several runs record with different classes.

Under DRIVER §6 D20 ①, the ADR and its first code slice form one task. The first code slice is the CAS GC. This task does **not** build the installer and image half. That half depends on what this ADR decides, so it is not planned ahead (D20 ④). The next planner call plans it from the landed ADR.

**Order (DRIVER §6 D27 ①).** On `main` `6d8d5232`:

- No `nightly-failure` issue is open, and no PR is open.
- `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`, and no P2-15 preparation is pending.
- P3-1, P3-2, P3-4, P3-5, P3-7 to P3-10 and P3-13 are checked.
- P3-3 waits on HQ-0090 and HQ-0091 (its rest landed in T-0533). It is treated as handled (D27 ⑦).
- P3-6, P3-11 and P3-12 are "오너 확정 필요", so the planner skips them.

So P3-14 is the next selectable P3 item. If that has changed when this task runs, report it in `## Result` and stop before writing anything.

**Open HQs this task does not ask again (D27 ⑦).**

- HQ-0094 ③ asks whether a storage cap exists and what its value is. PLAN P3-14 says the cap is OD-33 ③. The ADR sets no cap and no cap value.
- HQ-0094 ① and ② cover the runtime's acquisition of vendor SDKs and their licences. HQ-0098 covers the WSL2 `libc++` install.

The ADR anticipates none of these answers.

**Fixed inputs the ADR cites and does not decide again.**

- C-3 / #5 A-2, owner: `best` and `final` are permanent. `intermediate` and `failed` become GC targets a grace period after run end. The default grace period is 30 days and it is configurable. A GC records `gc_at` in a commit (NFR-2).
- ADR-0099: the time form of `gc_at` is already decided (ADR-0006 decision 3, `YYYY-MM-DDThh:mm:ssZ`). Of that ADR-0005 point, only "which reading of the clock becomes the value" is left.
- ADR-0005 decision 7: the allowed changes are adding `gc_at` and replacing the class. Removing or moving a record is never allowed.
- PLAN P3-14:
  - A hash that is `best` or `final` in **any** run is never removed (the integrator's reading of C-3).
  - Cases and audit records in the owner's data repository (`HIL-Claw-data`) are never removed (FR-18, NFR-2).
  - Deleting installed tools and tool images needs the user's permission in the runtime (FR-4, NFR-4) and an HQ approved by the owner in the driver.
- DRIVER §5 D29 storage paragraph:
  - tool images are tagged by tool name and version;
  - one version of a tool is never installed twice or held in two images;
  - retiring an old tool image version is P3-14 and needs the owner's approval.

**Frame changes (CLAUDE.md A-13; D23; D27 ⑥).** The ADR must not change the data-plane frame. Examples of frame changes:

- a new member or a version raise of `artifacts.json`, `STATE.json` or `instance.json`;
- a change to ADR-0005 decision 7's allowed changes;
- a new event kind outside an approved open list.

Prefer a reading that needs no frame change. For example, "run end" could be read from what the data plane already holds. If a point cannot be closed without a frame change:

- the ADR leaves that point open and states the concrete form to ask;
- the executor writes the HQ in `## Result` in the §8 structure (Korean, the concrete form, options with a recommendation, what it blocks and what it does not);
- the executor lands the rest and returns `DONE`.

The same applies to any owner-only part the work reveals.

**Size.** The ADR is roughly 250 lines and the GC module with an `artifacts` addition is roughly 350 LOC, excluding tests. That is near the 600-LOC recommendation (DRIVER §5 D30). The task is kept whole because D20 ① puts an ADR with its first code slice. If the code alone would clearly pass the recommendation, the executor lands the GC planning and removal and writes the commit of the `gc_at` edits as a follow-up split. The split is recorded in `## Follow-ups`.

**D16.** Everything runs on the development machine with temporary data roots and temporary git repositories that the tests make. Nothing starts `claude`, real Docker, a board or an accelerator. Nothing touches the owner's `HIL-Claw-data` checkout, any real data root or any image on the machine.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 and §5: branch `claude/T-0547-<slug>`; the `Task: T-0547` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; **the storage paragraph (D29)**, with temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0547/`.
  - §3 "BLOCKED 사유".
  - §6 D27 (①, ⑥, ⑦) and the D29 toolchain paragraph (image tags, installs, "the owner's approval").
  - §8: HQ structure; runtime acceptance items (D22).
  - §9: the ADR path and the owner notice.
- `CLAUDE.md`:
  - A-13 code mode and its schema-change definition;
  - "테스트 규칙";
  - "도구 계층 언어 정책": one line with the language and the reason, in the commit body and in `## Result`;
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분";
  - "문서 커버리지 재검사".
- `PROCESS/PLAN.md`: line 75 (P3-14), and the paragraph above P3-7 (line 66) for the tool-install rules.
- `ARCHITECTURE/Requirements.md`: C-3, FR-4, FR-18, FR-19 ③, NFR-2, NFR-4, the OD-33 row, and "행 형식" (line 85).
- `ARCHITECTURE/decisions/`:
  - `ADR-0005-od8-artifacts-record.md`, whole: the binding record and the GC points of Boundaries.
  - `ADR-0099-od8-moment-form-of-other-files.md`, decisions 2 and 3 and Boundaries.
  - `ADR-0004-od8-data-plane-layout.md`, decisions 1, 2, 6 and 10, and the Context line on "no whole-directory scan". Listing one directory of known path is allowed; walking the tree is not.
  - `ADR-0039-od18-blob-push-fetch-local.md`, decisions 2, 5, 6 and 8.
  - `ADR-0095-od18-cas-store-over-a-damaged-place.md`, Decision.
  - `ADR-0121-od8-run-over-member.md`, decisions 2 and 3: the `run_status` member and when it is written.
  - `ADR-0127-od8-commit-step.md`, the decision on who commits, and #5 A-3 as it cites (no automatic push).
  - `ADR-0194-od33-vendor-stack-evaluation-design.md`: decision 7 (the read-only check and tool images), decision 9, decision 10 V3.
- Code:
  - `hilclaw/cas.py`, whole;
  - `hilclaw/artifacts.py`, whole;
  - `hilclaw/layout.py` lines 1-100;
  - `hilclaw/run_commit.py` lines 1-60 and its `git` invocation helper (how the module runs `git` with no shell and a cleaned environment);
  - `hilclaw/toolchain_check.py` lines 1-60 (how tool images are named today).
- Tests: `tests/test_artifacts.py` (fixtures and the public-name assertions), `tests/test_cas.py`.

## Acceptance Criteria

1. **ADR `ARCHITECTURE/decisions/ADR-0195-<slug>.md`** (verify the next free number). It follows the record format of the existing ADRs (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References) and is accepted under §9.
   - Each point below is either closed with its reason, or left open with the concrete HQ form (see Why).
   - Cite owner sources word for word where they decide something. Mark every other choice as this record's own.

   **GC points from ADR-0005 Boundaries:**
   - **(a) The tool and when it runs.** Whether a person or script starts it, or a runtime step does. Whether a dry-run report comes before removal. Name the entry point.
   - **(b) The grace period.** Where it is set and in what unit. The default is the owner's 30 days.
   - **(c) Run end.** How a run's end and its moment are read from what the data plane holds (for example `run_status` of ADR-0121 with a moment the history or `events.ndjson` already gives). Also what a run that never ended means for its blobs.
   - **(d) The clock reading that becomes `gc_at`.** Its form is ADR-0099's and is not decided again.
   - **(e) Content stored again after a GC.** What the record and its `gc_at` say then, inside ADR-0005 decision 7.
   - **(f) A hash recorded by several runs with different classes.** It is never removed while any run holds it as `best` or `final` (PLAN P3-14). When it is removed, the ADR says which records get `gc_at`.

   **Further points:**
   - **(g) Blobs the GC must keep.** Name every place in the data plane that can name a blob by hash today, `db/` included. State why the GC never removes a blob that such a place still needs. Blobs that no `artifacts.json` records are kept (ADR-0005 decision 8).
   - **(h) Commit and push.** Who commits the `gc_at` edits and when (C-3: "GC 시 `gc_at` 기록 커밋"). No push (#5 A-3). Nothing under `runs/` or `db/` is ever deleted.
   - **(i) Duplicates and retirement**, the second half of P3-14, for the next task. This covers:
     - downloaded installers and their duplicates;
     - runtime images (the stand-in and coder images) and the driver's tool images: how duplicates are found, and how a retired version is proposed;
     - who approves deletions: the runtime under FR-4 and NFR-4, the driver by an HQ;
     - what a read-only report shows.

     Use `toolchain_check`'s image reading where it fits, and do not add a second list of commands. Decide only what §9 allows. The cap is OD-33 ③ / HQ-0094 ③ and stays open.
   - **Consequences** list the ADR and docstring sentences that become less exact. Edit only what this task's code makes wrong; leave the rest for a follow-up.
2. **Registers.** If the executor links the ADR in `ARCHITECTURE/Requirements.md` or `ARCHITECTURE/OpenDecisionProposals.md`, the edit follows those files' own rules:
   - Requirements: the register's "행 형식", line 85;
   - OpenDecisionProposals: the header's "기록 규칙", line 8.

   That means one link per new ADR, open parts rewritten in place, no restatement of the record and no dated paragraph.

   No new OD is registered for the GC, since no OD exists for it (ADR-0005 Boundaries).

   If any of `Requirements.md`, `UsageCases.md` or `StandardScenarios.md` changes, re-run the coverage check. Update `StandardScenarios.md` §검사 결과 by the rule in its first paragraph.

   The C-3 sentence is not edited.
3. **First code slice: the CAS GC.** It is a new module `hilclaw/blob_gc.py` (the name may change if the ADR names it otherwise). It implements the ADR's (a) to (h) and has these parts:
   - **Read-only plan.** The plan lists `runs/` (one directory of known path) and reads each run's `artifacts.json` through `hilclaw.artifacts.load`. It also reads what (c) and (g) need. It returns the blobs eligible for removal, and for each blob the runs and records it touches. It changes nothing.
   - **Removal.**
     - It removes only blobs the plan made eligible, only from `blobs/sha256/<hh>/<hash>`.
     - It never removes anything under `runs/` or `db/`, and never removes a blob the plan did not name.
     - It adds `gc_at` to the records (f) names, through a new function in `hilclaw/artifacts.py`. The record is written after the blob is removed, mirroring ADR-0005 decision 8 so that a `gc_at` never precedes the removal.
     - It commits as (h) says, running `git` without a shell as `run_commit` does.
   - **Command line.** It follows the `python -m hilclaw.<module>` pattern of `toolchain_check`, with the dry run as the default if the ADR so decides.
   - **Fail safe.**
     - If any run's `artifacts.json` is unreadable or invalid, or a run's end cannot be determined as (c) requires, nothing is removed for the hashes that run may hold. If the ADR cannot bound which hashes those are, nothing is removed at all. Either way the condition is reported.
     - A blob whose content no longer matches its hash (`cas.verify_blob`) is handled as the ADR says, and is reported.
4. **Tests** (`tests/test_blob_gc.py`, plus the `tests/test_artifacts.py` additions; D12). They use temporary data roots and, for the commit, temporary git repositories made by the tests.
   - **Happy path:** an `intermediate` and a `failed` blob of an ended run past the grace period are removed, and their records get `gc_at` in the ADR-0099 form.
   - **Branches:**
     - a blob within the grace period is kept;
     - a blob of a run that has not ended is kept;
     - a hash that is `best` in one run and `intermediate` in another is kept;
     - a `final` blob is kept;
     - a blob no record names is kept;
     - a blob already gone is handled as the ADR says;
     - content stored again after a GC behaves as (e) says;
     - the dry run changes nothing.
   - **Negative cases:**
     - an invalid `artifacts.json`;
     - a `run_id` directory name that `layout` refuses;
     - a non-positive or non-integer grace period;
     - a data root that is not a git working tree, if the commit needs one;
     - a removal that fails with `OSError`: the record gets no `gc_at` and the error is reported.
   - Every public function of `blob_gc` and the new `artifacts` function is covered. Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Existing behaviour is unchanged.**
   - `cas`, `artifacts` (beyond the one new function), `run_commit` and every runtime path behave as before. No existing test changes, except the list assertions DRIVER §5 D21 allows.
   - The foreseen D21 edit: a public-name or `__all__`-style assertion in `tests/test_artifacts.py` that pins the module's names, if one exists, to take in the new function. List every such edit in the PR body.
   - `artifacts.py`'s module docstring sentence "never writes ``gc_at`` (the MVP has no GC tool)" becomes wrong with this task and is corrected here.
6. **No deletion outside tests.** The executor does not run the GC, any image removal or any installer removal on the development machine's real data roots, images or files. Following D29, it removes only its own task directory at the end.
7. **`## Result`** records:
   - the ADR number and which of (a) to (i) it closed;
   - every HQ to ask, in the §8 structure (Korean). If there are none, say so;
   - any runtime acceptance item, for example how the GC behaves on a C-7 machine's file system or under a concurrent run (OD-17), if the ADR leaves one;
   - the language line;
   - the follow-up that plans the installer and image half from (i).

## Out of Scope

- The installer and image half of P3-14: the duplicate report and the retirement tool. The next task plans it from the landed ADR.
- Any storage cap or its value (OD-33 ③, HQ-0094 ③).
- Deleting any real tool image, installer or data on any machine.
- Changing the data-plane frame (A-13): any new member, version or event kind. If one is needed it becomes an HQ.
- `blob.push` and `blob.fetch` backends (#5 B-2), and making the runtime start the GC on its own unless the ADR decides so within §9.
- The deferred lines in PLAN "보류". They are not judged again.

## Follow-ups

## Result
- **Order check (Why)**: unchanged at `main` `046a354e` — no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`; P3-14 was the next selectable P3 item.
- **ADR**: [ADR-0195](../../ARCHITECTURE/decisions/ADR-0195-p3-14-storage-cleanup-and-cas-gc.md), accepted under §9. It closes all of (a) to (h) and decides the §9 part of (i):
  - (a) `python -m hilclaw.blob_gc --data-root <path> [--grace-days <n>] [--remove]`, started by a person or a script, never by a runtime step; report (dry run) by default, `--remove` removes, records and commits.
  - (b) whole days, default 30 (owner), given by `--grace-days` per invocation; not stored in any data-plane file.
  - (c) a run is ended when `HEAD`'s `STATE.json` holds `run_status` `"over"`; its end is the committer time of the last commit that changed that file; a run whose `artifacts.json` differs from `HEAD`, or whose `STATE.json` is invalid or holds another status, is undetermined and keeps its blobs; a run that never ends keeps its blobs.
  - (d) the UTC clock read right after each unlink, ADR-0099 form.
  - (e) a `gc_at` once written is never changed or removed; content stored again keeps the record (ADR-0005 decision 6); a later removal adds `gc_at` only to records that lack one.
  - (f) a hash is removed only when every record of every run naming it is `intermediate`/`failed` in a run past its grace; then every such record lacking `gc_at` gets it.
  - (g) only `artifacts.json` names blobs today; a later record that makes another file name a blob must keep it `best`/`final` in `artifacts.json` or revisit ADR-0195; an unreadable `runs/` entry (refused name, symlink, invalid `artifacts.json`) blocks every removal.
  - (h) the GC commits the edited `artifacts.json` files itself in one local commit built in a temporary index; no push; nothing under `runs/` or `db/` deleted.
  - (i) design of the next task: a read-only report of installer/image duplicates and retirement candidates using `toolchain_check`'s image reading; deletion only with FR-4/NFR-4 permission (runtime) or an approved HQ (driver). The cap stays OD-33 ③ / HQ-0094 ③.
- **Registers**: `Requirements.md`, `OpenDecisionProposals.md`, `UsageCases.md` and `StandardScenarios.md` are not edited (no OD exists for the GC), so no coverage re-check was needed. The C-3 sentence is not edited.
- **Code**: `hilclaw/blob_gc.py` (new) and `hilclaw.artifacts.set_gc_at` with `BlobPresentError`; the `artifacts.py` docstring sentence on `gc_at` corrected. Tests: `tests/test_blob_gc.py` (new) and `set_gc_at` tests appended to `tests/test_artifacts.py`. No existing test changed; no D21 list assertion needed an edit (`tests/test_artifacts.py` pins no public-name list).
- **Language**: Python — the GC builds on `cas`, `artifacts` and `run_commit` (all Python) and runs `git` through `subprocess` without a shell.
- **Size**: about 640 LOC of code (`blob_gc.py` 590 lines, most of it docstrings; `artifacts.py` +45) plus the 162-line ADR, above the 600-LOC recommendation (D30); kept whole because D20 ① puts the ADR with its first code slice and the plan, removal and commit are one feature.
- **HQ**: none. No point needed a frame change or an owner-only value.
- **Runtime acceptance items**: none.
- **Follow-up for the planner**: the installer and image half of P3-14 from ADR-0195 decision 10 — a read-only report command (duplicates by SHA-256 for named files; duplicates and retirement candidates for named images via `toolchain_check`'s probes), with the driver's approval HQ form for removals.
- **Nothing was run on a real data root, image or installer** (AC 6); every test uses temporary data roots and temporary git repositories.
- **PR**: #363. **Review**: 2 rounds, Approve. Round 1 found that the plan read only the working tree's records, so a deleted `artifacts.json` or run directory could hide a `best` record that `HEAD` holds; fixed by reading `runs/` and the records on both sides and comparing them as parsed (ADR-0195 decisions 1, 4, 6, 7). Round 1's two nits (hook wording, `OSError` from the commit on the command line) were fixed too.
- **Local tests**: full suite 38664 passed, 2211 skipped at the first head; `tests/test_blob_gc.py` and `tests/test_artifacts.py` 436 passed, 4 skipped (symbolic link cases on Windows) at the final head; coverage `blob_gc.py` 93% lines, `artifacts.py` 100%.
