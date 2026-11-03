---
id: T-0548
title: Land the read-only installer and image report of ADR-0195 decision 10 (duplicates and retirement candidates), the second half of PLAN P3-14
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, C-3, NFR-4, OD-33, D29, "PLAN P3-14"]
dependsOn: []
touchesFiles:
  - hilclaw/storage_report.py
  - tests/test_storage_report.py
  - hilclaw/toolchain_check.py
  - tests/test_toolchain_check.py
  - ARCHITECTURE/decisions/ADR-0195-p3-14-storage-cleanup-and-cas-gc.md
estimatedSize: {loc: 450, files: 3}
hq: []
---
## Why

**PLAN P3-14** ("스토리지 정리"; the owner confirmed the item on 2026-11-03, the item's composition is the integrator's). The item asks for two tools: the C-3 GC of the CAS, and duplicate management of downloaded installers and images. T-0547 (PR #363) landed ADR-0195 and the GC (`hilclaw/blob_gc.py`). ADR-0195 **decision 10** designs the second half and its Consequences name it as the next task: "the report command of decision 10 and its tests; it plans its own approval HQ form for the driver's images". This task is that half. When it lands, both tools of P3-14 exist, so the driver can check P3-14 in its §3-6 state commit unless `## Result` says a part remains.

**Order (DRIVER §6 D27 ①).** On `main` `cf2f73d8`:

- No `nightly-failure` issue is open, and no PR is open.
- `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`, and no P2-15 preparation is pending.
- P3-1, P3-2, P3-4, P3-5, P3-7 to P3-10 and P3-13 are checked.
- P3-3 waits on HQ-0090 and HQ-0091 and is treated as handled (D27 ⑦).
- P3-6, P3-11 and P3-12 are "오너 확정 필요", so the planner skips them.

So the rest of P3-14 is the next selectable work. If that has changed when this task runs, report it in `## Result` and stop before writing anything.

**Fixed inputs, not decided again.**

- ADR-0195 decision 10, whole. In short:
  - Scope: ① installers and archives a tool was installed from; ② runtime images: the stand-in image (`HILCLAW_STANDIN_IMAGE`, `hilclaw.standin_image`) and the coder image (`HILCLAW_CODER_IMAGE`, `hilclaw.coder_runtime`); ③ the driver's tool images (D29). The CAS, the data repository, and the driver's work images and task directories are out of scope.
  - A read-only layer-2 report command. It writes one JSON document on standard output, outside the data plane, with the exit statuses of ADR-0195 decision 2 (0, 10, 20, 21; never 1 or 2).
  - For each named file: its size and SHA-256. Duplicates are files with the same SHA-256.
  - For each named image: its image id, size and tags, plus the components and versions `hilclaw.toolchain_check` reads in it. These come from the adapters' own probes; there is **no second list of commands**.
  - Image duplicates are two image ids holding the same component at the same version. Two tags of one image id are one image, not a duplicate.
  - A retirement candidate is a tool image whose tag names a tool and a version, beside an image of the same tool at a later version that holds every component the first holds. Two kinds of image are never candidates: an image a runtime variable names now, and an image holding a version that the newest image of a tool holds.
  - The command reads only what it was given on its command line. It does not list the machine's images by itself.
  - The report proposes and never deletes.
- ADR-0195 decision 10 "Left open": a storage cap and its value (OD-33 ③, HQ-0094 ③), and where the runtime keeps installers (HQ-0094 ①). This task decides neither and does not ask them again (D27 ⑦).
- DRIVER §5 D29 storage paragraph: tool images are tagged by tool name and version; one version of a tool is never installed twice or held in two images; retiring an old tool image version needs the owner's approval; nothing the owner placed is removed.

**The tag form.** ADR-0195 decision 10 leaves "the format of a tool image tag beyond 'tool name and version' (D29)" to this task, to be read "from the images that exist". The planner found no driver tool image recorded in any task `## Result`; T-0543 to T-0546 made no image. The images their Results name are the runtime images `hilclaw-standin:2026-10-29` and `hilclaw-coder:2026-10-29`. If the machine still holds no driver tool image, the executor fixes the reading of a tool image tag under §9. It must be the plainest reading D29 allows. It is recorded by rewriting the "Left open" tag clause of ADR-0195 decision 10 in place (see criterion 3). The same applies to the version order the "later version" rule needs. This is a design detail of layer 2 and not an owner value. If the executor still judges that it needs the owner, the retirement-candidate part reports no candidate. The executor then writes an HQ in `## Result` with the concrete form (DRIVER §6 D27 ⑥), lands the rest and returns `DONE`.

**D16.** The tests run on the development machine with temporary directories and a stub container client (`docker`) that the tests write, as `tests/test_toolchain_check.py` does. Nothing starts `claude`. Nothing removes a real image, installer or file.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 and §5: branch `claude/T-0548-<slug>`; the `Task: T-0548` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; **the storage paragraph (D29)**, with temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0548/`.
  - §3 "BLOCKED 사유".
  - §6 D27 (①, ⑥, ⑦) and the D29 toolchain paragraph (image tags, "the owner's approval").
  - §8: HQ structure (Korean, the concrete form, options with a recommendation, what it blocks and what it does not); runtime acceptance items (D22).
  - §9: the ADR path and the owner notice.
- `CLAUDE.md`:
  - A-13 code mode;
  - "테스트 규칙";
  - "도구 계층 언어 정책": one line with the language and the reason, in the commit body and in `## Result`;
  - "코멘트 최소화";
  - "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md` line 75 (P3-14).
- `ARCHITECTURE/Requirements.md`: C-3, FR-4, FR-19 ③, NFR-4, and the OD-33 row.
- `ARCHITECTURE/decisions/ADR-0195-p3-14-storage-cleanup-and-cas-gc.md`: decisions 2 and 10, Consequences and Boundaries.
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`: decision 7 (the read-only check) and decision 10 V3.
- Code:
  - `hilclaw/toolchain_check.py`, whole: the command-line, report and exit-status conventions to mirror, and `COMPONENTS` and `check`, to reuse for image components;
  - `hilclaw/blob_gc.py` lines 1-90: the module docstring and exit statuses of the sibling tool;
  - `hilclaw/standin_container.py`: `check_image` and `run_in_container`'s signature;
  - `hilclaw/local_run.py`: `run`'s docstring;
  - `hilclaw/cas.py` lines 90-110 (`_chunks`, `_sha256_of`);
  - `hilclaw/standin_image.py` (`ENV_IMAGE`, `read_image`) and `hilclaw/coder_runtime.py` lines 70-85 and `_read_image`.
- Tests: `tests/test_toolchain_check.py`, for its stub-client fixtures and its list assertions on `COMPONENTS` and report keys.

## Acceptance Criteria

1. **Machine reading first (D29), read only.** Before writing code, the executor reads which images and tool installs exist on the machine. It uses `docker image ls` in WSL2 and on Windows if a client exists, and the install paths earlier Results name (for example `/usr/local/cuda-13.1`, `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724`). It records the reading in `## Result`. Nothing is installed, pulled, downloaded or removed.
2. **The report command**, a new module `hilclaw/storage_report.py` (the name may differ if the executor has a better one). It implements ADR-0195 decision 10:
   - **Command line**: `python -m hilclaw.storage_report [--file-dir <path> ...] [--image <ref> ...]`, or an equivalent form the executor documents in the module docstring. Every directory and image reference is named; nothing is guessed or listed beyond them.
   - Image references are checked by `standin_container.check_image` before anything starts. An argument that begins with `-` where a value is due, an empty list of both kinds, a missing value or an unknown flag is a usage error: exit status 20, nothing read.
   - **Files**:
     - For each regular file in a named directory: its path relative to that directory, its size and its SHA-256 (hash in chunks, as `cas` does).
     - Duplicates are groups of two or more files with one SHA-256, across all named directories.
     - Symbolic links are not followed and are reported as skipped.
     - Whether the walk recurses below a named directory is the executor's choice, stated in the docstring.
     - A file or directory that cannot be read is reported as unreadable, which gives exit status 10, and the rest goes on.
   - **Images**:
     - For each named reference: the image id, size and tags, read from the container client by one call per reference under a time limit, through `local_run.run` with no shell. Example: `docker image inspect --format '{{json .}}'`, or another form the executor finds the client supports and records.
     - The components and versions the image holds come from `hilclaw.toolchain_check`'s probes. The executor reuses `check` or a small public helper it adds there, so that no command text enters the new module.
     - References that resolve to one image id are one image.
     - An image the client cannot read, or that no container of can be used, is reported as unreadable (exit status 10).
     - Duplicates are two or more image ids that hold the same component at the same `present` version.
     - Retirement candidates follow decision 10, with the tag reading and version order of the Why. An image named now by `HILCLAW_STANDIN_IMAGE` or `HILCLAW_CODER_IMAGE` is never a candidate; the command reads that from the process environment through `standin_image.read_image` and `coder_runtime`'s reader, or equivalents. A version the newest image of its tool holds is never a candidate either.
   - **Report**:
     - One JSON document and one LF on standard output, ASCII. It holds no environment value, token or command line.
     - It has no `schema_version`, since it is no data-plane file.
     - Exit statuses 0, 10, 20 and 21 have the meanings of ADR-0195 decision 2 and `toolchain_check`. A missing or unwritable standard output is 21.
     - Standard error gets one fixed line only when no report was written.
   - **Read only.** It removes, installs, pulls and changes nothing. It writes only its report, plus any temporary directory `toolchain_check`'s container call already makes and removes.
3. **ADR-0195.**
   - If the Why's tag reading or version order is fixed here, rewrite the "Left open" tag clause of decision 10 in place to state it, in one or two sentences, and point to the module.
   - In Consequences and Boundaries, rewrite in place the "Next task" bullet and the Boundaries bullet "The report command of decision 10 and its code" so they say the command landed. Do not add a dated paragraph or restate the record.
   - The driver's approval HQ form of decision 10 ("naming each tag or path, its size and what replaces it") stays as written. If it needs one more field to be usable, add that field there.
   - Other ADRs are not edited. List any sentence that becomes less exact under Consequences.
4. **Tests** (`tests/test_storage_report.py`; D12). They use temporary directories and a stub `docker` written by the tests.
   - **Happy path:** two identical files in two named directories are one duplicate group; two image ids holding the same `nvcc` version are a duplicate; a tool image at an older version beside a newer one of the same tool that holds all its components is a retirement candidate.
   - **Branches:**
     - two tags of one image id are no duplicate;
     - an image named by `HILCLAW_STANDIN_IMAGE` or `HILCLAW_CODER_IMAGE` is never a candidate;
     - the newest image of a tool is never a candidate;
     - an older image holding a component the newer one lacks is no candidate;
     - a tag that does not read as tool and version gives no candidate;
     - a symbolic link is skipped;
     - only files given, or only images given.
   - **Negative cases:**
     - each usage error of criterion 2, with nothing started;
     - a named directory that does not exist or cannot be read;
     - the client absent, timing out, or giving malformed output for one image while the others are still read;
     - a closed standard output;
     - an exception in a probe.
   - Every public function of the new module, and any helper added to `toolchain_check`, is covered. Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Existing behaviour is unchanged.**
   - `toolchain_check`'s command line, report and exit statuses, `blob_gc`, `cas` and every runtime path behave as before.
   - No existing test changes, except the list assertions DRIVER §5 D21 allows. The foreseen one: an assertion in `tests/test_toolchain_check.py` that pins the module's public names, if a helper is added. List every such edit in the PR body.
6. **Run on the machine, read only.** After the tests pass, the executor runs the command once in WSL2. It names the images found in criterion 1 and the installer directories that still exist from earlier tasks' installs; if none exist, it names a task-directory fixture. It records the report, or a summary of it, in `## Result`.
   - If the report shows a duplicate or retirement candidate that the driver installed or made (D29 tool images or tool installs; not the owner's runtime images, not anything the owner placed), write in `## Result` the approval HQ of ADR-0195 decision 10, in the §8 structure (Korean). The HQ names each tag or path, its size and what replaces it. Remove nothing.
   - Otherwise say there is none.
7. **`## Result`** records:
   - the machine reading;
   - the command line and report shape;
   - the tag reading and version order, and where they are recorded;
   - every HQ to ask (or "none");
   - any runtime acceptance item, for example the client's `image inspect` output on a C-7 machine kind it was not seen on, if the executor finds one (D22);
   - the language line;
   - whether P3-14 is complete with this task, and what remains if it is not.

## Out of Scope

- Deleting any real image, installer, tool install or data, on any machine. Deletion follows an approved HQ in a later task (driver) or the user's FR-4/NFR-4 permission (runtime).
- A storage cap or its value (OD-33 ③, HQ-0094 ③); where the runtime keeps installers (HQ-0094 ①); WSL2 `libc++` (HQ-0098).
- Making the runtime run the report or ask permission on its own. ADR-0195 decision 10 gives the runtime's permission rule; wiring it into a run is not this task.
- Changes to `blob_gc`, the CAS or the data-plane frame.
- The deferred lines in PLAN "보류". They are not judged again.

## Follow-ups

## Result
- **Order check (Why)**: unchanged at `main` `1e0d09ed` — no open PR, no open `nightly-failure` issue; the rest of P3-14 was the next selectable item.
- **Machine reading (criterion 1, read only; nothing installed, pulled, downloaded or removed)**:
  - WSL2 Ubuntu, `docker image ls`: 15 references, 13 image ids — `hilclaw-coder:2026-10-29` = `hilclaw-coder:local` (`sha256:de56ff9d…`, 1.15 GB), `hilclaw-standin:2026-10-29` = `hilclaw-standin:local` (`sha256:0c17146e…`, 530 MB), and images the owner placed: `nns-i5188-f3:deps`, `nns-cf21:latest`, `armnn4425:deps`, `ov4425:base`, `nns3503:noble`, `nns3503:jammy`, `bash:latest`, `nns-4920-h3h4:deps`, `ubuntu:22.04`, `ubuntu:24.04`, `ubuntu:26.04`. **No driver tool image** (no tag read as a D29 tool image made by the driver).
  - Windows: no `docker` client on `PATH`.
  - Tool installs named by earlier Results: `/usr/local/cuda-13.1` (WSL2, 4.8 GB; `/usr/local/cuda` and `/usr/local/cuda-13` point to it) and `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724` (T-0544). **No installer or archive remains** (T-0544 removed the QNN archive after install; no other task kept one).
- **Command line**: `python -m hilclaw.storage_report [--file-dir <path> ...] [--image <ref> ...]`. Usage errors (no argument, missing or empty value, a value beginning with `-`, an unknown or positional argument, a reference `check_image` refuses) exit 20 with nothing read.
- **Report shape**: `{"files": {"directories": [{directory, state, message, files: [{path, size, sha256}], skipped: [{path, reason}], unreadable: [{path, message}]}], "duplicates": [{sha256, size, files: [{directory, path}]}]}, "images": {"images": [{references, id, size, tags, state, message, components}], "duplicates": [{component, version, images}], "retirement_candidates": [{id, tag, size, replaced_by: {id, tag}}]}}`; one ASCII JSON document and LF, no `schema_version`, no environment value. Exit 0 everything read, 10 something unreadable, 20 usage, 21 fault (standard output included).
- **Tag reading and version order** (fixed here, ADR-0195 decision 10 "Left open" clause rewritten in place, and the module docstring): a tool tag is `<tool>:<version>`, the repository being the tool's name and the version one or more decimal numbers joined by `.`; a later version is the greater one compared number by number, a prefix first. An image holding no `present` component (no tool `toolchain_check` reads, e.g. a base OS image) is never a candidate; this keeps `ubuntu:22.04`/`ubuntu:24.04` from being proposed beside `ubuntu:26.04`, which the first machine run showed.
- **Machine run (criterion 6, WSL2, read only)**: all 15 references plus a task-directory fixture (two directories with one duplicated file and one symbolic link). Exit 0 in about 10 s; 13 images all `read`; components: `clang` `Ubuntu clang version 18.1.3 (1ubuntu1)` present in both runtime images, everything else absent. File duplicates: the fixture pair; the link skipped. **Image duplicate**: `clang` 18.1.3 in `hilclaw-coder` and `hilclaw-standin` — the owner's runtime images, not driver tool images, so no HQ. **Retirement candidates: none.** No container left behind. Nothing removed.
- **HQ**: none. No duplicate or retirement candidate of anything the driver installed or made.
- **Runtime acceptance items**: none. `docker image inspect --format {{json .}}` was read on WSL2's Docker; the report adds no new runtime path.
- **Language**: Python — it reuses `toolchain_check`, `local_run` and `standin_container` (all Python) and runs the client through `local_run.run` without a shell.
- **Code**: `hilclaw/storage_report.py` (new), `hilclaw.toolchain_check.image_entry` (new public helper; command line, report and exit statuses of `toolchain_check` unchanged). Tests: `tests/test_storage_report.py` (new), two `image_entry` tests appended to `tests/test_toolchain_check.py`; no existing test changed and no D21 list assertion needed an edit.
- **P3-14**: complete with this task (the C-3 GC from T-0547 and this report). What stays open is outside the item's tools: the storage cap (OD-33 ③, HQ-0094 ③) and where the runtime keeps installers (HQ-0094 ①).
