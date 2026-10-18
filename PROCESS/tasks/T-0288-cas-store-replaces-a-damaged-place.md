---
id: T-0288
title: Apply ADR-0095 in `hilclaw/cas.py` — the store step replaces a regular file at a hash's place whose content is not that hash, and raises `FileExistsError` for any other entry there
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, C-3, NFR-2, OD-18, "#5 A-2"]
dependsOn: [T-0287]
touchesFiles: [hilclaw/cas.py, tests/test_cas.py]
estimatedSize: {loc: 60, files: 2}
hq: []
---
## Why

ADR-0095 was accepted on 2026-10-18 under DRIVER §9 (T-0287, landed as `d174de3`). It answers the first part of OD-18 sub-question 13: what the store step of `hilclaw.cas` (`put_bytes`, `put_file`) does when the place of the hash it computed is already occupied. Its Consequences section names one code task. This is that task.

Today `_store` moves its temporary file into place only `if not target.is_file()`. That has two effects:

- A regular file at the place whose content is not the hash is kept, and the call still returns a `BlobRef` for content that is not there.
- An entry that is no regular file is handled inconsistently. A directory makes `os.replace` fail with an unnamed `OSError`. On POSIX, other entries (a dangling link, a FIFO) would be replaced.

ADR-0095 decisions 2 to 4 fix the behaviour completely, row by row. The task needs no new design choice. No module of `hilclaw/` calls `put_bytes` or `put_file` yet. Only tests call them (`tests/test_cas.py`, `tests/test_blob_tools.py`, `tests/test_artifacts.py`), and none of those outside `tests/test_cas.py` relies on a damaged file being kept by a later put.

The owner's 7-day window on ADR-0095 runs to 2026-10-25. If the owner objects, the revert task also reverts this change.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0288` trailer, and the `Task:` last line of the PR body for the squash-merge.
- `CLAUDE.md`, standing rules: "코멘트 최소화", "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0095-od18-cas-store-over-a-damaged-place.md`: the Terms paragraph (line 22), decisions 2, 3 and 4 (lines 37-63), and Consequences (lines 85-91), the code-task bullet in particular. **This is the specification.** Where this task file and ADR-0095 differ, ADR-0095 wins. Report the difference in `## Result`.
- `hilclaw/cas.py` on `main` (whole file, 120 lines).
- `tests/test_cas.py` on `main` (whole file, 354 lines), especially:
  - the `put` and `root` fixtures (lines 56-74);
  - `test_a_repeated_put_keeps_the_stored_file` (line 173);
  - `test_a_failed_move_into_place_leaves_no_temporary_file` (line 300);
  - `test_a_failed_read_of_the_source_leaves_no_temporary_file` (line 321);
  - `test_a_blob_path_occupied_by_a_directory_is_an_error` (line 341).
- `tests/test_bring_in.py` lines 45-51 (the `symlink` helper): the pattern this repository uses for links. It skips where the machine refuses to create a link, but it fails on GitHub Actions.

## Acceptance Criteria

1. **Session entry check.**
   - Run `gh pr list`. If an open PR changes `hilclaw/cas.py` or `tests/test_cas.py`, return BLOCKED (open-PR conflict risk).
   - PR #179 (T-0284) touches only `hilclaw/clang_build.py` and `tests/test_clang_build.py`, so it does not overlap.
   - Read issue #5 for an owner objection to ADR-0095 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6244351320. If there is one, return BLOCKED.
2. **`_store` in `hilclaw/cas.py`** follows ADR-0095 decisions 2 to 4. It looks at the place of the computed hash without following a link (`os.lstat`) before the move.
   - **Nothing at the place.** The look raises `FileNotFoundError` or `NotADirectoryError`. The store makes `<hh>` with `mkdir(exist_ok=True)`, then makes the existing `os.replace` move, as today. This covers a `<hh>` that is no directory: the look may raise either of the two errors, depending on the platform. The existing `mkdir` then raises `FileExistsError` and the entry stays.
   - **A regular file at the place itself.**
     - Re-hash it (SHA-256 in `CHUNK_SIZE` reads).
     - If it is intact, keep it untouched: no move, mtime unchanged.
     - If it is not intact, make the move over it.
   - **A symbolic link.**
     - If, followed, it leads to a regular file that is intact, keep it untouched.
     - Otherwise raise `FileExistsError`: a link that leads nowhere, a link to a directory, or a link to a file that is not intact. Do not touch the link or its target.
   - **Any other entry** (a directory, a FIFO, a socket, a device node, anything else): raise `FileExistsError` and leave the entry untouched.
   - Every `FileExistsError` raised by the new code names the place, for example `FileExistsError(errno.EEXIST, "<reason>", str(target))` or an equivalent message that contains the path.
   - **Other failures propagate as the `OSError` they are**, with no move:
     - a failure of the look other than the two "nothing here" errors;
     - a failure to open or read an existing file for the re-hash.
   - In every case:
     - the `finally` still removes the store's temporary file;
     - the store unlinks, renames or rewrites nothing else;
     - the returned `BlobRef` is unchanged in form.
   - `blob_path`, `has_blob`, `verify_blob`, `BlobRef`, `BlobNotFoundError` and `CHUNK_SIZE` keep their behaviour and signatures. The re-hash may share a private helper with `verify_blob`, provided that `verify_blob`'s answers and errors do not change.
3. **Docstrings** (no other comments, CLAUDE.md "코멘트 최소화"):
   - In the module docstring, replace "Storing content that is already present keeps the stored file as it is" with a sentence that matches decisions 2 and 3: an intact file is kept, a file at the place that is not intact is replaced, and any other entry makes the store fail. Keep "Blobs are only ever added".
   - In the error lists of `put_bytes` and `put_file`, add `FileExistsError` (the place or its `<hh>` holds an entry the store did not put there), and add that an `OSError` from looking at the place or reading an existing file propagates.
4. **Tests in `tests/test_cas.py`.** Edits to existing tests are limited to exactly these two. Every other existing test in `tests/test_cas.py`, `tests/test_blob_tools.py` and `tests/test_artifacts.py` must pass unedited.
   - `test_a_repeated_put_keeps_the_stored_file` may be renamed or split into two tests, for both `put` variants (the fixture):
     - (i) an intact stored file is kept with its mtime: set it with `os.utime`, put again, and assert the same `st_mtime`;
     - (ii) a `marker` file at the place is replaced: the call returns `BlobRef(DIGEST, len(DATA))`, the place reads `DATA`, `verify_blob` is true, `stored_files(root)` holds exactly the one blob, and no `tmp-*` file is left.
   - `test_a_blob_path_occupied_by_a_directory_is_an_error`: narrow it to `pytest.raises(FileExistsError)`, assert that the message contains the place, and keep its existing assertions. Also assert that no `tmp-*` entry is left under `blobs/sha256/`, and that a file placed inside the directory beforehand is unchanged.

   New tests, for both `put` variants where the fixture applies:

   - a. **`<hh>` is a regular file.** Make the store directory, and write a regular file named `DIGEST[:2]` with some bytes. The put raises `FileExistsError`. The file's bytes are unchanged, and no `tmp-*` entry is left.
   - b. **Links** (ADR-0095 walk-through rows), each with the place as a symbolic link:
     - to a directory;
     - to nothing (dangling);
     - to a regular file holding other bytes;
     - to a regular file holding `DATA`.

     The first three raise `FileExistsError`. The link is still a link to the same target, the target's content (where there is one) is unchanged, and no `tmp-*` entry is left. The fourth returns `BlobRef(DIGEST, len(DATA))` and leaves the link and its target unchanged. Create links through a helper in the pattern of `tests/test_bring_in.py` `symlink`: skip when the OS refuses a link (an unprivileged Windows account cannot create one), and re-raise when `GITHUB_ACTIONS` is `"true"`, so the Linux CI always runs them. Put the link targets under `tmp_path`, outside the data root.
   - c. **FIFO.** `@pytest.mark.skipif(not hasattr(os, "mkfifo"), ...)` (it skips on Windows). A FIFO at the place gives `FileExistsError`, the entry is still a FIFO (`stat.S_ISFIFO` on `os.lstat`), and no `tmp-*` entry is left. The test must not open the FIFO.
   - d. **A failed look.** Use `monkeypatch` on `cas.os.lstat` so that it raises `PermissionError` only for the place's path and passes every other path to the real function. The put raises `PermissionError` (not `FileExistsError`), an intact or damaged file put there beforehand is unchanged, and no `tmp-*` entry is left.
   - e. **A failed re-hash read.** A damaged regular file is at the place. Inject a read failure only for the re-hash. With `put_bytes`, for example, monkeypatch `cas._chunks` to raise `OSError` (`put_bytes` does not use `_chunks` for its input). Or patch `open` in `cas` only for the place's path, to fit the implementation. The put raises that `OSError`, the damaged file is unchanged, and no `tmp-*` entry is left.
   - f. **The empty blob.** A damaged file at the place of `EMPTY` is replaced, and the put returns `BlobRef(EMPTY, 0)`. This is a negative edge case of the re-hash.

   Every new test asserts the state of the store after the call, not only the exception. No test sleeps or depends on timing. Do not add tests of test helpers (CLAUDE.md test rule ⑤).
5. **Gates.**
   - Locally on Windows, `python -m pytest`, `ruff check` and `ruff format --check` (whatever the CI runs for Python) pass. Report which tests skipped and why.
   - CI (Linux) must be green: the link and FIFO tests run there.
   - The CI coverage step keeps `hilclaw/` at ≥ 80% line and ≥ 80% function coverage.
   - Every new branch of `_store` and its helpers is reached by a test on Linux. Name any branch that only Windows or only Linux reaches in `## Result`.
6. **Code mode** (CLAUDE.md A-13, DRIVER §5):
   - Work on branch `claude/T-0288-cas-store-replaces-a-damaged-place`.
   - Open a Draft PR whose title contains `T-0288`.
   - Run the review cycle (dev-code-review) until Approve, within 7 rounds, with CI green.
   - Squash-merge with `gh pr merge --squash --body`. The PR body ends with the line `Task: T-0288`. Delete the branch.
   - The commit body records the language choice (Python, the existing module) in one line.
7. **Size and limits.**
   - At most about 60 non-test lines in `hilclaw/cas.py`. Only the two files in `touchesFiles`.
   - Add no dependency.
   - Change no data-plane file or schema, nothing in `hilclaw/blob_tools.py`, no tool result member and no tool failure kind.
   - Start no `claude`, compiler or container (D16).
8. **Result** records:
   - the PR and merge commit;
   - the review rounds and their findings;
   - the test counts and skips on Windows and in CI;
   - the coverage numbers;
   - which `OSError` subclass the look raised under a regular-file `<hh>` on each platform seen;
   - any difference from ADR-0095 found.

## Out of Scope

- `hilclaw/blob_tools.py` and what `blob.push` / `blob.fetch` answer (ADR-0039 decisions 3 to 6). Whether the pair shows an occupied place.
- Everything ADR-0095 decision 5 leaves open:
  - removing a damaged file outside a store of the same content;
  - clearing an occupied place;
  - recording the finding (event log, OD-17);
  - retention, GC and `gc_at` (C-3, #5 A-2, OD-25).
- Concurrent writers and a no-overwrite move, whether the directory entry is fsynced, whether stored blobs are read-only (T-0008 follow-ups; ADR-0095 decision 3, "Limit").
- Editing any ADR, `ARCHITECTURE/` file or `PROCESS/` file other than this task's `## Result`. The sentences that ADR-0095 Consequences lists as "now less exact" stay as they are.
- `hilclaw/clang_build.py`, `hilclaw/local_run.py` and their tests (PR #179, HQ-0021 to HQ-0029). Windows junctions and reparse points other than symbolic links.

## Follow-ups

- None required by ADR-0095 beyond this task. Record any new one found (for example a Windows-only behaviour of `os.lstat` under a non-directory `<hh>`) in `## Result`.

## Result
