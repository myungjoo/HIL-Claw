---
id: T-0170
title: Add the bring-in of a coder call (ADR-0055 decision 5, B1 to B6; ADR-0049 decision 4, slice (b)) - one function that takes the admitted regular files of the place `output/` of a scratch into the not yet existing `output/` of an attempt - with its tests; bound to nothing, no other module edited
phase: P1
status: DONE
commitMode: code
coversReq: [FR-5, FR-6, FR-9, C-3, C-7, NFR-2, OD-23, OD-8, "#5 D12"]
dependsOn: [T-0155, T-0157]
touchesFiles: [hilclaw/bring_in.py, tests/test_bring_in.py]
estimatedSize: {loc: 200, files: 1}   # one new module of about 150-220 lines, docstrings included; the test file is outside the cap (DRIVER §5, D4)
hq: []
---
## Why
ADR-0049 (the isolation means of a coder call) and ADR-0055 (the form of the `output/` of an attempt) both name the bring-in as a code slice that can now be cut:

- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md` Consequences (line 144): "(b) a function that brings regular files from a scratch into the `output/` of an attempt under the rules of decision 4"; "(a) to (c) need no container runtime to test".
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md` Consequences (line 147): "(a) the bring-in function - slice (b) of ADR-0049 - under B1 to B6".

The reader side of ADR-0055 (N1, N2, R1 to R8) landed as `hilclaw/kernel_source.py` (T-0157, PR #106); the bring-in is the writing side, and it is what makes an attempt's `output/` exist at all. PLAN P2-2 (coder-driver) and the run-tool contracts of P1-1 will call it. This task writes it as one new module that nothing calls yet. It ticks **no PLAN checkbox** and changes no OD.

Planner's judgements (the reviewer is asked to re-check each):
- **No undecided design is needed, under one conservative refusal.** B1 to B6, N1, N2 and the two bounds (16 files, 262,144 bytes) are fixed word for word. ADR-0055 scopes itself to "a bring-in ... into an `output/` that did not exist before it" (line 32) and leaves "what a bring-in does when it finds an `output/` already there" to OD-23 sub-question ① (가) (lines 88, 108). The function therefore **refuses** a call whose attempt `output/` already exists (any entry of that name, of any kind): it raises before anything is read or written and takes nothing. This decides nothing about what a bring-in does then - it states that this function is only the bring-in of the record's scope - and the error must say so in its docstring. If the reviewer reads this refusal as an invention of ① (가), return BLOCKED (`unclear-requirement`) rather than choose another behaviour.
- **What stays open and must not be invented**: whether what was not taken is reported (B5, sub-question ① (나)) - the function returns only the names it took, writes no record of what it did not take, and logs nothing; what happens after a bring-in that died part-way (L5) - the function does not remove what it wrote before a failure, and the docstring says an unfinished bring-in looks like a finished one; when a bring-in is carried out or given up, and anything about a call that did not end normally (OD-19); a rule of the bytes (① (다)).
- **A-13**: code mode. No new dependency (standard library only). No data-plane schema, member or layout version is touched: ADR-0055 decision 8 keeps layout version 1 and `hilclaw/layout.py` unchanged.
- **D16**: nothing here needs the `claude` program, a container runtime, a board or an API key. The tests build scratch directories in `tmp_path` by hand.
- **Why this item and not the others**: of the two code candidates the last journals name, the ADR-0052 harness slice changes how `hilclaw/local_run.py` waits (a POSIX-only `os.wait4` path that the Windows development machine cannot run, and a module many tools depend on); the bring-in is a new module with no caller, fully testable on every platform, and it unblocks P2-2. The two document nits of T-0169 (StandardScenarios quotes, ADR-0057 "0 to 15") are too small to be worth an iteration of their own and stay as follow-ups.
- **Session entry check (planner, 2026-10-14, `main` at 9f38400)**: no open pull request. HQ-0013, 0014, 0016, 0017, 0018, 0019 are `runtime-acceptance` notices that block no task.

## Required Reading
- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit 2 h 30 min) and §5 (naming convention: branch `claude/T-0170-<slug>`, `T-0170` in the PR title, trailer `Task: T-0170` in commits and as the last line of the PR body; D4 size cap; D12 test rules).
- `CLAUDE.md` "상시 규칙" (comment minimisation, test rules ①-⑤, language policy - record the language and reason in the commit body).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: Status (lines 3-11), decision 1 (lines 30-34), Limits L1-L7 (lines 36-44), decision 5 whole (lines 74-94: N1, N2, B1 to B6, the paragraph on the place), decision 6 first and third bullets (lines 98, 100), decision 7 (lines 104-108), Walk-through (lines 122-127), Consequences first bullet (line 147), Boundaries last bullet (line 163).
- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`: decision 3 (lines 66-72, the write root; the scratch is "no path of that tree") and decision 4 (lines 74-86), Consequences line 144.
- `hilclaw/kernel_source.py` whole (181 lines): `is_admitted_name`, `OUTPUT_NAME`, the path conventions of its module docstring (lines 22-43) - the new module follows the same conventions for its output-path argument; `_checked_output_path` (line 156) is private and is not imported - repeat the check or write it in the new module.
- `hilclaw/once_write.py` lines 1-60 (`write_once` and its limits) - one possible way to create each file without replacing an entry; see "Left to this task".
- `hilclaw/layout.py` lines 104-131 (`attempt_dir`, `attempt_artefact`: how a caller forms the path of an attempt's `output/`).
- `tests/test_kernel_source.py` lines 1-80 (the `symlink` helper and the skip pattern for platforms that cannot make a link) - reuse the pattern.

## Acceptance Criteria
A new module (suggested `hilclaw/bring_in.py`; the name is the executor's) with one public function, suggested `bring_in(scratch_root, output_path) -> tuple[str, ...]`, and the public names below. Behaviour:

1. **Arguments.** `output_path` is the path of the attempt's `output/` as `hilclaw.layout.attempt_artefact(..., "output")` forms it: a `str` or `os.PathLike` of `str`, no NUL character, last component exactly `output`; otherwise a `ValueError` subclass (e.g. `InvalidBringInArgumentError`) before anything is looked at. `scratch_root` has the same type rules (no last-component rule). If, after `os.path.realpath` of both, one of the two lies inside the other (or they are equal), the same error is raised before anything is read (ADR-0049 decision 3: the scratch is no path of the tree; ADR-0049 decision 4: "no name it meets can make it write elsewhere").
2. **Refusal of an existing `output/`** (planner's judgement above): if the attempt directory (parent of `output_path`) lists an entry named exactly `output` of any kind (directory, file, symbolic link - dangling included), a dedicated exception (e.g. `OutputExistsError`) is raised, nothing below the scratch is read and nothing is written. Checked again at creation time: `output/` is created with a call that fails if the name exists (`os.mkdir`, never `exist_ok=True`), and that failure is the same exception.
3. **B1 - the place.** The place is the entry of `scratch_root` whose listed name is exactly `output` (no case folding; an entry `Output` is not the place) and that is itself a directory per `os.lstat` (a symbolic link is not, whatever it points to). No place, or a place that is not a directory: nothing is taken, the return value is `()`, nothing is created. Nothing directly below the scratch root and nothing below a sub-directory of the place is looked at as output.
4. **B2 - which entries.** An entry directly below the place is a candidate when, per `os.lstat`, it is a regular file (not a symbolic link, directory, FIFO, socket or device), `kernel_source.is_admitted_name(listed name)` is true, and its size is at most 262,144 bytes. Both bounds are public module constants (e.g. `MAX_FILES = 16`, `MAX_FILE_BYTES = 262_144`) with a one-line note that they are ADR-0055's provisional values.
5. **B3 - all or none above the number.** If more than `MAX_FILES` entries are candidates, nothing is taken: return `()`, nothing created, no file read.
6. **B4 - same name, same bytes.** Each taken entry becomes a new regular file below `output/` under the same name with the same bytes. The file is read without following a symbolic link (on POSIX open with `os.O_NOFOLLOW`, and `O_NONBLOCK` so a swapped-in FIFO cannot block; on every platform compare `os.fstat` of the opened file with the earlier `os.lstat` - same device and inode, still regular - and treat a mismatch as not a candidate). At most `MAX_FILE_BYTES + 1` bytes are read; a file that yields more than `MAX_FILE_BYTES` is not taken ("The bound of B2 holds for the bytes written, whatever a query of the size said"). The new file is created as a new entry that never replaces or writes through an existing one; no mode bit, owner, time or other attribute of the scratch file is carried over (the new file has the mode a plain new file gets under the process umask; never executable bits set by this module). All reads finish before `output/` is created, so a call that takes nothing never creates it.
7. **B5 - not taken means not there.** An entry that is not taken is never renamed, truncated, converted or copied; the scratch is never written, removed or modified by the function.
8. **B6 - `output/` only when something was taken.** `output/` (and any missing parent directory of it, with `os.makedirs(..., exist_ok=True)` for the parents only) is created only when at least one file is taken.
9. **Return value**: the tuple of taken names in ascending byte order of the names (the order of R3), and nothing else (no list of what was not taken - B5 / ① (나)).
10. **Failures** (a convention of this module, like R8 of the reader): a scratch root or place that exists and cannot be listed, an entry whose kind cannot be determined, and a read error of a candidate other than the link/identity cases of point 6 raise an exception of the module (e.g. `BringInError` with a member naming the failure from a public tuple of values, `__cause__` the original `OSError`, `str()` holding no path, entry name or system text) **before** `output/` is created. A scratch root that does not exist raises the same kind of failure (not `()`: a missing scratch is a mistake of the caller, not "nothing in the place"). An `OSError` while creating `output/` or writing a file is raised as it is (or wrapped the same way - the executor's choice, stated in the docstring); files already written stay (L5) and the docstring says so.
11. **Docstring** (module): cites ADR-0055 decision 5 and ADR-0049 decision 4; lists what the module does not do - it judges no content (L2), reports nothing that was not taken (① (나)), handles no existing `output/` (① (가)), does not tell a finished bring-in from one that died (L5), knows nothing of containers, the moment of the call or a call that did not end normally (OD-19), creates or removes no scratch (ADR-0049 slices (a), (c)), and that nothing calls it yet. Keep it within the comment-minimisation rule otherwise.
12. **Tests** (`tests/test_bring_in.py`, D12 ②-④; symlink cases skip where the platform cannot make a link, as in `tests/test_kernel_source.py`):
    - happy: the Walk-through step 1 of ADR-0055 (`gemm.c`, `pack.c`, `pack.h` in the place; `try/test_main.c` and `a.out` elsewhere) - exactly the three taken, same bytes, return value in byte order, `hilclaw.kernel_source.read_compiled_set(output_path)` then gives `gemm.c`, `pack.c`;
    - Walk-through step 2: `Notes.md`, `Fast.c`, a sub-directory `old/` with a `.c` file inside, a symbolic link `ref.c` - none taken, none renamed, scratch unchanged;
    - Walk-through step 3: no place / empty place / place that is a regular file / place that is a symbolic link to a directory / place listed as `Output` - `()` and no `output/` (no attempt directory created either);
    - bounds: exactly 16 candidates taken; 17 candidates - nothing taken; a file of exactly 262,144 bytes taken, 262,145 not taken while its neighbours are; reserved stems (`con.c`, `nul.h`, `com1.c`) and N1 failures (`A.c`, `_a.c`, `a.cc`, `a.c.c`, 65-character name) not taken;
    - attributes: a scratch file with executable bits yields a taken file without them (POSIX only);
    - refusal: `output/` existing as a directory, as a file, as a dangling symbolic link - the exception, scratch not read (e.g. a candidate made unreadable is not reached), nothing written;
    - arguments: wrong types, NUL, last component not `output`, scratch inside the attempt tree, attempt tree inside the scratch, equal paths;
    - failures: missing scratch root; an unlistable place or scratch root (monkeypatch `os.listdir`/`os.lstat` to raise `PermissionError`) - the failure value, `__cause__`, `str()` without the path; an identity mismatch between `lstat` and `fstat` (monkeypatched) - entry not taken; a file that grows above the bound between `lstat` and the read (monkeypatched read) - not taken;
    - the order of the return value is independent of the listing order (monkeypatch `os.listdir` to reverse).
13. Local gates: `python -m pytest`, `ruff check .`, `ruff format --check .` pass; CI green on all jobs; coverage gate (line and function ≥ 80%) holds, the new module at or near 100%.

## Left to this task
- How each new file is created: `hilclaw.once_write.write_once` (temporary name plus hard link; leaves a `<name>.<token>.tmp` that R2/R6 pass over if killed; hard-link limits stated in its docstring) or `os.open(..., O_CREAT | O_EXCL | O_WRONLY)` directly. Either meets B4; state the choice and its reason in the docstring and the commit body. A `write_once` that returns `FileExistsError` is impossible after point 2 unless a race; treat it as the refusal exception.
- The exact public names, the exception hierarchy and the failure values.
- Whether the scratch root itself may be a symbolic link to a directory (the reader's convention in `hilclaw/kernel_source.py` lines 30-34 counts a linked attempt directory as a directory; following that convention is recommended).

## Out of Scope
- Any edit of `hilclaw/kernel_source.py`, `hilclaw/layout.py`, `hilclaw/once_write.py` or any other existing module; any caller of the new function.
- Creating or removing a scratch, placing copies in it (ADR-0049 slices (a), (c)); containers (slice (d), PLAN P2-2).
- Anything of OD-23 sub-question ① (가)-(마), OD-19, OD-16; any change of an ADR or of `ARCHITECTURE/`.
- The ADR-0052 harness slice; the T-0169 document nits.

## Follow-ups
- (planner, code mode) ADR-0049 slices (a) (create a scratch, refusing a location inside a checkout, and place the copy of `spec.json` - never in the place) and (c) (remove a scratch without following a link out of it).
- (planner, code mode) The ADR-0052 harness slice (`hilclaw/local_run.py` hands on the usage of the waited-for process; `hilclaw/harness/timing.py` yields the figure; the verdict of decision 5).
- (planner, document mode, small) T-0169 nits: StandardScenarios 2026-10-14 paragraph drops the quotes around "설계됨"; ADR-0057 "For P2-1" reads "with 0 or 10 to 15"; ADR-0055 decision 3's "not verified" include expectation shown by T-0157's clang test; the ADR-0053 Consequences sentences and the `hilclaw/spec.py` docstring sentence that can name `objective` (T-0168). Could ride together in one document task.
- (commit body) ADR-0055 and ADR-0049 are within or near their objection windows (ADR-0055 notice 2026-10-13, until 2026-10-20); an objection creates a reverting task and this module is reverted with it.

## Result
- **DONE.** PR #118 was squash-merged as `409698d` ("T-0170: Add the bring-in of a coder call (ADR-0055 decision 5, ADR-0049 slice (b)) (#118)"). The squash message ends with `Task: T-0170`. The remote and local branches were deleted. Not BLOCKED. The task ticks no PLAN checkbox and changes no OD.
- **Review**: 3 rounds with a fresh-context `dev-reviewer`.
  - Round 1, Request changes. `test_an_unlistable_attempt_directory` failed on Python 3.11, where `Path.iterdir` goes through the patched `os.listdir`. The fix undoes the patch before the last check (`c60dd95`). A test of the `ValueError` branch of `os.path.commonpath` (other drives) was added for coverage (`ce5a9b0`).
  - Round 2, Approve. One nit was fixed: an `O_NOFOLLOW` open that fails with `EMLINK` (FreeBSD) or `EFTYPE` (NetBSD) now means "a link, not taken", as `ELOOP` does (`e778607`). Two nits were declined:
    - B3 counts the candidates by `lstat`. Counting after the reads would read files when more than 16 are candidates, which AC 5 forbids.
    - An empty path string is accepted, following the `kernel_source` path convention.
  - Round 3, Approve, with info notes only. Each reviewer judged that the refusal of an existing `output/` is not an invention of OD-23 sub-question ① (가): it is the precondition of ADR-0055 decision 1's scope.
- **CI**: run 38512487873 was green on the head `e778607`, all six jobs. `hilclaw/bring_in.py` has 100 % line coverage, and function coverage of `hilclaw/` is 100 %. Locally on Windows: the full `python -m pytest` gave 18388 passed and 323 skipped, on the first commit. `ruff check` and `ruff format --check` were clean. The symlink, FIFO and mode-bit cases skip on this machine and ran in CI.
- **Language**: Python, because it is the language of the 2nd-layer package and of its reader `hilclaw/kernel_source.py`.
- **Public API as landed** (`hilclaw/bring_in.py`, 256 lines):
  - `bring_in(scratch_root, output_path) -> tuple[str, ...]`.
  - `MAX_FILES = 16` and `MAX_FILE_BYTES = 262_144`.
  - The exceptions `InvalidBringInArgumentError(ValueError)`, `OutputExistsError(Exception)` and `BringInError(Exception)`. The `failure` of `BringInError` is one of `BRING_IN_FAILURES` = (`attempt_directory_unlistable`, `scratch_root_unlistable`, `place_unlistable`, `entry_kind_undetermined`, `candidate_unreadable`).
- **Choices**:
  - **File creation**: `os.open(O_CREAT | O_EXCL)` with mode `0o666` under the umask, not `write_once`. It needs no hard link and leaves no temporary name.
  - **Scratch root**: a symbolic link to a directory counts as a directory, following the reader's convention.
  - **Kind checks**: only admitted names have their kind asked for.
  - **Missing scratch root**: reported as `scratch_root_unlistable`.
  - **Unlistable attempt directory**: an attempt directory that exists but cannot be listed is `attempt_directory_unlistable`.
  - **OSErrors of creation and writing**: raised unwrapped, and the files already written stay (L5).
- **Follow-ups**: none new beyond those listed above.
