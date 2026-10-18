# ADR-0095: What the store step of `hilclaw.cas` does when the place of a hash already holds a file whose content is not that hash, or something that is no regular file (first part of sub-question ⑬ of OD-18)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences are those of #5 A-2, quoted from the comment and marked **owner**; they are cited, not reinterpreted, and are not subject to the 7-day window. What an accepted record, a requirement, a task file or a file of `hilclaw/` says is **cited** with its source. **Everything else is this record's own design**: the answer for each kind of occupied place, the reasons, and every weighing.
- Answers **the first part of sub-question ⑬ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): what the **store step** of `hilclaw.cas` (`put_bytes`, `put_file`) does when the place of the hash it computed is already occupied (decisions 2 and 3). The rest of ⑬ stays open (decision 5). OD-18 keeps its status word.
- **Nothing of the data plane changes**: no member of `artifacts.json` or of any other file, no rule on `gc_at`, retention or GC, no member or kind of the result of `blob.push` / `blob.fetch`, no tool failure kind, no layout version.
- It builds on [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decisions 1, 4, 6 and 8; its window runs until 2026-10-19) and cites [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 1) and [ADR-0005](ADR-0005-od8-artifacts-record.md) (decisions 7, 8 and 10; Boundaries). If ADR-0039 is reverted, decision 1's terms are taken from `hilclaw/cas.py` alone and the rest stands.
- **It is a record, not code**: the observations of decision 1 come from reading `hilclaw/cas.py` and `tests/test_cas.py` at `7a1611c` as files; nothing was established by running code, and no compiler, container or `claude` process was started. It binds no code until the code task of Consequences lands.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The question** (cited: ADR-0039 Boundaries, ⑬): "what is done about a file of the local store whose content is not its name, and about a place of a hash that holds something that is no regular file — who removes or replaces it, given that `hilclaw.cas` keeps an existing file when the same content is stored again; whether anything records the finding; and whether a call of the pair should show that a place is occupied". The pair reports such a file and leaves it (cited: ADR-0039 decisions 4 and 6); its alternatives table rejects a push that removes or repairs the file because "a repair needs the content from somewhere; removal belongs with retention and GC (C-3), which are not decided".
- **What the owner fixed** (owner, #5 A-2): "바이너리는 git(LFS 포함)에 넣지 않는다. `HIL-Claw-data/blobs/sha256/<hh>/<hash>` (gitignore 대상)에 content-hash로 저장"; "**MVP는 GC 도구를 만들지 않고 class 기록만** 한다"; "GC 시 `artifacts.json` 해당 항목에 `gc_at`을 기록하는 커밋을 남겨 "무엇이 있었고 언제 지웠나"를 git 이력에 보존한다(NFR-2)"; "CAS는 GC = 파일 삭제". Requirements C-3 mirrors it.
- **Why now**: the store step has the whole content in hand and has computed its hash, so it needs no content from elsewhere; and no module of `hilclaw/` calls `put_bytes` or `put_file` yet (only `tests/test_cas.py` does), so a change of its behaviour reaches no caller.

## Decision

Terms: **the place of a hash** and **the look** are those of ADR-0039 decision 1. **Intact**: the SHA-256 of the content read from the file is the hash, as `verify_blob` answers. **The move**: the existing `os.replace` of the store's temporary file onto the place.

### 1. What the store step does today (observation, binds nothing)

`_store` writes the content to `blobs/sha256/tmp-<pid>-<random>`, hashes it, fsyncs it, then moves it into place only `if not target.is_file()`, and in every case unlinks its temporary file in `finally`. Read as a file, that gives:

| The place holds | Today | Test that shows it |
|---|---|---|
| Nothing | The move; the blob is there whole | `test_put_bytes_stores_the_content_under_its_digest`; `test_a_failed_move_into_place_leaves_no_temporary_file` (a failed move propagates its `OSError`, leaves no temporary file, and a later store succeeds) |
| A regular file, intact (in this table symbolic links are followed, as `is_file()` does) | Kept as it is, mtime included | (none for intact content alone) |
| A regular file, not intact | **Kept**; the `BlobRef` of the new content is returned although that content is not at the place | `test_a_repeated_put_keeps_the_stored_file` (a `marker` file stays, `verify_blob` false); `test_verify_blob_detects_altered_content` |
| A directory | The move fails with an `OSError`; the directory stays; no temporary file remains | `test_a_blob_path_occupied_by_a_directory_is_an_error` |
| Nothing, but its `<hh>` is no directory (a regular file) | `target.parent.mkdir(exist_ok=True)` raises `FileExistsError`; the entry stays | none; read from the code |
| Another entry that is no regular file after links are followed (a link that leads nowhere or to a directory; on POSIX a FIFO, socket or device node) | `is_file()` is false, so the move is tried; POSIX `rename` replaces any entry that is not a directory, so **the entry would be replaced by the blob** | none; this row is read from the code and from rename(2), not tested, and was not established on Windows |

### 2. A regular file at the place that is not intact: the store step replaces it

- When the place itself (not following a link) holds a regular file, the store step re-hashes it. **Intact**: it is kept as it is, as today. **Not intact**: the move puts the new content over it. In both cases the returned `BlobRef` is then true of the place.
- **What a reader sees**: the move is one `os.replace`, so a reader opening the place finds the old file or the new one whole, never a partial or empty place (cited: `hilclaw/cas.py`, "a reader never sees a partial blob under its final name"; POSIX `rename` is atomic, and what Windows guarantees for `os.replace` over an existing file was not established here); a reader that opened the old file before the move reads the old bytes, and its answer is of that moment (cited: ADR-0039 decision 8). Where the move fails — on Windows while a reader holds the file open (cited: T-0008 Result, known limits) — the store step raises that error as for any failed move, its temporary file is removed and the old file stays.
- **What is removed**: the store step unlinks nothing but its own temporary file. The file that was not intact leaves only by being overwritten in the move that puts the content of its name there.
- **Against the cited sentences.** "Blobs are only ever added" (`hilclaw/cas.py`) holds: a blob is "a file named after the SHA-256 of its content", the overwritten file is not one, and after the move the blob of that hash is present. It is not GC in the sense of #5 A-2 / C-3: no blob is deleted, so no `gc_at` falls due ("무엇이 있었고 언제 지웠나" names a blob that is no longer there; here the blob is there afterwards). ADR-0005 decision 10 ("does not guarantee that a blob is present, intact …") stays true; the store step adds no guarantee to a record. ADR-0039 decisions 4 and 6 are unchanged: the pair still reports the file and writes nothing; only the remedy that decision 4 said does not exist ("storing the content again does not replace such a file") now exists. The cost the record accepts: the bytes that were not intact leave no trace (decision 5).
- **Why** (this record's own): with today's behaviour the store step returns a `BlobRef` for content that is not at the place, and a record written after it (cited: ADR-0005 decision 8, "the blob is stored first, then the record is written") would assert "that the blob was in the local store when the record was written" falsely. The store step is the one place that has the content and its hash together, and a file that is not intact cannot be a blob of any hash at that place. This answers the T-0008 follow-up "whether `put_*` should verify an existing blob before trusting it" (its Result names the risk: a blob truncated by a power loss "would be trusted forever"); T-0008's constraint "It never deletes or rewrites a stored blob (no GC, C-3)" holds, since the overwritten file is no stored blob.

### 3. A place that holds something else: the store step refuses and touches nothing

- When the place itself (not following a link) holds an entry that is not a regular file — a directory, a symbolic link, a FIFO, a socket, a device node, or anything else — the store step does not move. It raises `FileExistsError` naming the place, removes its temporary file, and leaves the entry, and any link's target, as they are. **One exception**: a symbolic link that, followed, leads to an intact regular file is kept as today, since the content of the hash is reachable at the place (cited: ADR-0039 decision 1, the look follows links, and its Consequences, "a symbolic link that leads to a regular file counts as one").
- **A `<hh>` that is no directory** is the same case one level up: the store step leaves it, and the `FileExistsError` that `mkdir` raises today is kept: a look of the place that fails only because `<hh>` is no directory (`NotADirectoryError` on POSIX, `FileNotFoundError` where the platform answers so) is read as "nothing at the place" and leads to that `mkdir`. Any other failure in looking at the place (no permission, an I/O error), and a failure to open or read an existing regular file for the re-hash of decision 2, propagates as the `OSError` it is: no move, the temporary file is removed and the existing entry stays.
- **Why**: the store creates no links, directories or special files at a place, so such an entry was put there by a hand or a defect outside the package; removing or renaming it would delete what the store did not create. `FileExistsError` is an `OSError`, so every caller and the directory test that expect an `OSError` still get one, and it tells "the place, or its `<hh>`, is taken by something the store did not put there" apart from an I/O failure. It is a Python exception of layer 2, not a tool failure kind.
- **Limit**: looking at the place and the move are two steps. An entry placed between them by another actor can still be replaced by the move; a no-overwrite move is the open follow-up of T-0008 (concurrent writers) and is not decided here. P1 assumes one run (C-2).

### 4. Walk-through

`H` is the hash of the stored content; `put` is `put_bytes` or `put_file`.

| The place of `H` holds | `put` answers | The place afterwards |
|---|---|---|
| Nothing | `BlobRef(H, size)` | The blob, whole |
| A regular file with content `H` | `BlobRef(H, size)` | The same file, mtime unchanged |
| A regular file with other content (`marker`) | `BlobRef(H, size)` | The blob; `verify_blob` true |
| A directory, a FIFO, a link that leads nowhere, a link to a directory, a link to a file not intact; or nothing, under a `<hh>` that is a regular file | `FileExistsError` | Unchanged; no temporary file |
| A link to a regular file with content `H` | `BlobRef(H, size)` | Unchanged |

### 5. What stays open of sub-question ⑬

- **Removal of a file that is not intact outside a store of the same content** — when the content is not at hand, nothing replaces the file. Placed by the GC design of C-3 (#5 A-2: "MVP는 GC 도구를 만들지 않고"), which also says whether a GC tool removes such files.
- **Whether anything records the finding** — that a store step replaced a file, or refused an occupied place, or that a pair call saw `intact` false. No member or event exists for it (cited: ADR-0005 Boundaries, "whether an event is logged for a blob"). Placed by the event log content (PLAN P1-8; OD-17) and by the first module that calls `put_bytes` / `put_file` and has somewhere to report to.
- **Whether a call of the pair shows that a place is occupied** — ADR-0039 decision 4 stands; any change is a result member and is that tool's contract, placed together with who acts on the answer (OD-23) and the GC design.
- **What clears an occupied place** (decision 3) — only a hand today; placed with the GC design and with OD-10, which ⑬ names (cited: ADR-0039 Boundaries).
- **Retention, GC and `gc_at`** of every kind (C-3, #5 A-2 — owner's decisions; the GC design is later), and whether a `gc_at` once written changes when the content is stored again (cited: ADR-0005 decision 7).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | (b) Keep today's behaviour and leave the part open | The store step would go on returning a `BlobRef` for content that is not at the place, and a record written after it would assert a stored blob that is not there (ADR-0005 decision 8). Nothing in the GC design is needed to decide this part. |
| 2 | (c) Refuse with an error when the existing file is not intact | Every later store of that content fails until a hand removes the file, which is what the store step could do safely itself with the content in hand. It keeps the damaged bytes as evidence, but nothing records or reads that evidence (decision 5). |
| 2 | Move into place always, without the re-hash | Replaces intact files too: their mtime changes, and on Windows every repeated store of a blob held open by a reader fails. The re-hash costs one read of the existing file. |
| 2 | Move the damaged file aside (a quarantine name or directory) | A new kind of entry under `blobs/`, a layout matter (ADR-0004 decision 1; OD-8 ㉒), and bytes that need a retention rule (C-3). |
| 2 | Replace also through a link to a file that is not intact | The move replaces the link itself, an entry the store did not create; the target outside the place stays damaged. |
| 3 | Keep today's behaviour for a place that holds something else | A directory already fails, but any other entry that is not a directory would be replaced by the move — an entry the store did not create. |
| 3 | Remove or rename the entry, then move | A deletion of what the store did not create; removal belongs with retention and GC (C-3; ADR-0039 alternatives, point 6). |
| 3 | Return the `BlobRef` and leave the entry, as for an intact file | The same false `BlobRef` as (b). |

## Consequences

- **The code task** (code mode, one task; nothing is written here): `_store` in `hilclaw/cas.py` replaces its `if not target.is_file()` test by the look of decisions 2 and 3 (an `os.lstat` of the place, the re-hash of a regular file, `FileExistsError` otherwise, the exception of an intact link), and the module docstring and the error lists of the `put_bytes` and `put_file` docstrings (`FileExistsError`) are updated. In `tests/test_cas.py`, `test_a_repeated_put_keeps_the_stored_file` is edited: the `marker` file is now replaced and `verify_blob` is true, and an intact file keeps its mtime; `test_a_blob_path_occupied_by_a_directory_is_an_error` may be narrowed to `FileExistsError`. New tests cover, where the platform allows (a symbolic link on Windows needs a privilege), the link rows of the walk-through, a FIFO and a `<hh>` that is a regular file. `hilclaw/blob_tools.py` is not changed.
- **Not edited and now less exact.** `hilclaw/cas.py` docstring: "Storing content that is already present keeps the stored file as it is" — now only when it is intact. ADR-0039 Context: "Storing content that is already present keeps the stored file as it is" (quoted from the module); decision 4: "storing the content again does not replace such a file"; its alternatives row of point 4 on links ("`hilclaw.cas` follows links when it decides whether a blob is stored already (`is_file()` in `has_blob` and in the store step)") — the store step now looks at the place without following a link first; its Limits: "A file that is not intact is reported and left as it is" (true of the pair, no longer of the store); its alternatives row of point 6 ("a repair needs the content from somewhere") — the store step has it; its sub-question ⑬ sentence "given that `hilclaw.cas` keeps an existing file when the same content is stored again". T-0008 Result: "A repeated put keeps the stored file and does not re-verify it". No earlier ADR is edited.
- **Provisional choices**: replacement only of a regular file at the place itself; `FileExistsError` as the error; the exception of an intact link.
- **A-13 reading**: document mode; no code, dependency, settings or schema file changes.

## Boundaries (not decided here)

- Everything decision 5 lists; what `blob.push` / `blob.fetch` request and answer (ADR-0039 decisions 3 to 6).
- Concurrent writers and a no-overwrite move; whether the directory entry is fsynced; whether stored blobs are read-only (T-0008 follow-ups).
- `artifacts.json` members, retention classes, `gc_at` and data governance (C-3, #5 A-2, OD-25 — owner-only).
- Code, tests, CI and any settings file.

## References

- [Requirements](../Requirements.md): FR-10, NFR-2, C-2, C-3; register rows OD-8, OD-10, OD-17, OD-18, OD-23, OD-25.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18); [StandardScenarios](../StandardScenarios.md) (S10).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 1); [ADR-0005](ADR-0005-od8-artifacts-record.md) (decisions 7, 8, 10; Boundaries); [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decisions 1, 4, 6, 8; alternatives; Boundaries).
- #5 A-2 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; `hilclaw/cas.py`, `hilclaw/blob_tools.py`, `tests/test_cas.py`; tasks T-0008, T-0287.
