---
id: T-0008
title: Add the local content-addressed blob store (blobs/sha256/<hh>/<hash>) with its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-3, "#5 A-2", FR-10]
dependsOn: [T-0002]
touchesFiles: [hilclaw/cas.py, tests/test_cas.py]
estimatedSize: {loc: 130, files: 1}   # non-test: the store module; the test file is excluded from the cap (D4)
hq: []   # standard library only; no OD is closed and no ADR is written (see Why)
---
## Why
Constraint C-3 (owner decision #5 A-2, 2026-07-23) fixes how binaries are kept: never in git, but content-addressed under `HIL-Claw-data/blobs/sha256/<hh>/<hash>` (gitignored in the data repository), with git holding only `artifacts.json` records that reference the hash. FR-10 lists "CAS blob" as a part of the single layer-2 package `hilclaw/`. PLAN P1-6 is that part. Every later producer of a binary (the `cpu_standin` build wrapper P1-2, the harness P1-3) needs a place to put its output and get a hash back, so the store is a leaf dependency worth having first.

This task is the **first slice of P1-6**: the local store only (write a blob, locate it, check it). The two other parts of P1-6 are left out on purpose (Out of Scope): the `artifacts.json` record, whose location and "producing round" field depend on the P1 directory layout (OD-8, open) and which is a data-plane schema; and the `blob.push` / `blob.fetch` synchronisation contract, whose backend waits for #5 B-2.

Why this item now (planner's judgement, DRIVER §6): the phase is P0.5, but P0.5-1..3 extend `.github/workflows/ci.yml`, which the open PR #16 (T-0003, BLOCKED on HQ-0002) creates, and the rest of P0.5-4 is an owner action; §6 allows an item of a later phase whose dependencies are met. Among the P1 items this one is fully determined by a confirmed decision. The Requirements sentence "OD-4, OD-6, OD-8 are to be confirmed before the first commit" does not stop it: this slice uses neither the key schema (OD-4), nor the coder spec (OD-6), nor any path that OD-8 still has to decide (the blob path is fixed verbatim by C-3), and PLAN marks the items that do need an OD closed (P1-4, P1-5, P1-8) while P1-6 carries no such mark. If the executor or the reviewer finds that the implementation does need one of those ODs, that is the BLOCKED reason "design choice needing an OD" (DRIVER §3), not something to decide silently.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode, the forbidden actions held by discipline, "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- PROCESS/PLAN.md — P1-6 (and P1-1, P1-7, P1-8 for what is deliberately not touched)
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"; "현재 프로젝트 상태 주의사항" (CI 미구축, 바이너리 금지)
- ARCHITECTURE/Requirements.md — C-3 (the whole row), FR-10 (the single-package sentence), C-2, C-7 (POSIX and WSL, LF), the OD register rows OD-8 and OD-18 (read to know what is **not** decided here)
- Issue #5, comments "A-2 확정 (2026-07-23)" and "A-3 확정 (2026-07-23)" (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`): the CAS decision with its three supplements, and "`blob.push` is never called automatically"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0007-merge-guard-hook.md — `## Result`: conventions of the sibling modules (stdlib only, one test file per module, reachability check with the stdlib `trace` module, local verification commands, how the `## Result` text was handed to the driver)
- PROCESS/tasks/T-0003-ci-skeleton.md — front matter and `## Result`: CI is not on `main` (PR #16 open, BLOCKED on HQ-0002), so verification stays local
- Existing files: `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/driver_state.py` and `tests/test_driver_state.py` (style reference), `.editorconfig`, `.gitattributes`, `.gitignore`

## Acceptance Criteria
C-3 fixes only this for the slice: blobs are stored by content hash at `<data repository>/blobs/sha256/<hh>/<hash>`, outside git. The module name, the public API, the error types, the reading of `<hh>` and the write procedure are **not** fixed anywhere. None of them is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below, state each choice with one line of reason in the commit body and in `## Result`, and do not present them as requirements.

Constraints:
- **Standard library only** (`hashlib`, `os`, `pathlib`, `tempfile`, `typing` as needed). Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Code must run on CPython 3.11 (`requires-python` floor); it is verified locally on 3.14 only. Say so in `## Result`.
- The data repository root is always an **explicit argument**. The module reads no configuration file and no environment variable, has no default location, and never runs `git` (`hilclaw.config.json` is PLAN P1-7).
- No command line entry point, no `main`, no MCP server: how layer-2 tools are exposed to layer 1 is OD-18 (open).
- The module only creates files under `<data_root>/blobs/sha256/`. It never deletes or rewrites a stored blob (no GC, C-3).
- **No binary file is committed**: test blobs are created at run time under pytest's `tmp_path`. No test may touch a real `HIL-Claw-data` checkout.

Module (new, `hilclaw/cas.py`; provisional name. Python because the package is Python and hashing plus atomic file replacement are in the stdlib — one line in the commit body and `## Result`):
- Module docstring and short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested):
  - `blob_path(data_root, digest) -> pathlib.Path` — `<data_root>/blobs/sha256/<digest[:2]>/<digest>`. Pure: does not touch the file system. Raises `ValueError` unless `digest` is a `str` of exactly 64 lowercase hexadecimal characters (this is also what keeps a caller-supplied hash from escaping the store, e.g. `../x`).
  - `put_bytes(data_root, data: bytes) -> BlobRef` and `put_file(data_root, source) -> BlobRef` — store the content and return its reference. `BlobRef` carries the SHA-256 hex digest and the size in bytes (`artifacts.json` will need both, C-3), e.g. a `typing.NamedTuple`.
  - `has_blob(data_root, digest) -> bool` — whether the blob file exists (`ValueError` for a malformed digest).
  - `verify_blob(data_root, digest) -> bool` — re-hash the stored file: `True` if it matches its name, `False` if it does not; a missing blob raises the "not found" error below.
  - `BlobNotFoundError` (a `LookupError` or `FileNotFoundError` subclass; message names the digest).
- Behaviour:
  - `<hh>` is read as the **first two hex characters of the digest** (the usual fan-out, as in git's object store). C-3 writes only `<hh>`; record this reading as provisional.
  - Digests are lowercase hex; uppercase input is rejected, not normalised (one spelling per blob on case-sensitive and case-insensitive file systems alike).
  - `put_file` hashes and copies in bounded chunks (no whole-file read into memory) and does not modify or remove `source`. A `source` that is missing or is a directory raises the underlying `OSError`; nothing is left behind in the store.
  - Writing is atomic for readers: the content goes to a temporary file created **inside `<data_root>/blobs/sha256/`** (same file system as the target, and inside the path the data repository already gitignores) and is moved into place with `os.replace`. A reader never sees a partial blob under its final name. On any failure the temporary file is removed.
  - Idempotent: if the target already exists, the store keeps it, discards the temporary file and returns the same `BlobRef`. Two blobs with the same content are one file. `put_*` does not re-verify an existing blob; that is `verify_blob`.
  - Missing directories (`blobs/`, `sha256/`, `<hh>/`) are created on demand. A `data_root` that does not exist or is not a directory raises an error (provisional: `NotADirectoryError` or `FileNotFoundError`) instead of being created — a mistyped root must not silently grow a new store.
  - `data_root` and `source` accept `str` and `os.PathLike`. The zero-length blob is valid (`e3b0c442...b855`).
  - No permission bits are changed and no file is locked: the retention and protection policy is not decided here.

Tests (new, `tests/test_cas.py`; excluded from the size cap). All under `tmp_path`.
- happy:
  - `put_bytes` of a known input returns the digest computed independently with `hashlib.sha256` and the right size; the file is at `blobs/sha256/<first two>/<digest>` under the root and its content is identical.
  - `put_file` of a file larger than one chunk returns the same reference as `put_bytes` of the same content; `source` is unchanged.
  - the empty blob; a `str` root and a `Path` root give the same result.
  - `has_blob` is `False` before and `True` after; `verify_blob` is `True` for an intact blob.
  - `blob_path` returns the expected path without creating anything (the root may even be absent).
- branch:
  - putting the same content twice returns the same reference and leaves exactly one file (and the existing file is not rewritten, e.g. its modification time or an injected marker is preserved).
  - two different contents with different `<hh>` and, if constructible cheaply, the directory already existing for a second blob.
  - after any `put_*`, successful or failed, no temporary file remains anywhere under `blobs/sha256/`.
- negative:
  - malformed digests to `blob_path`, `has_blob` and `verify_blob`: wrong length, uppercase, non-hex characters, an empty string, a path-like value such as `../../etc/passwd`, a non-`str` (`None`, `bytes`) → `ValueError` (or `TypeError` for the non-`str` case if the executor prefers; state the choice).
  - `verify_blob` on a blob whose stored bytes were altered by the test → `False`; on an absent blob → `BlobNotFoundError`.
  - `put_file` with a missing source and with a directory as source → `OSError`, and the store holds no blob and no temporary file.
  - `put_bytes` / `put_file` with a root that does not exist, and with a root that is a regular file → error, nothing created.
  - a failure while moving the blob into place (`monkeypatch` of `os.replace` raising `OSError`) → the error propagates and the temporary file is gone.
  - `put_bytes` with a non-bytes argument (`str`) → `TypeError`.
- Coverage is not measured in this task (`pytest-cov` belongs to P0.5-3 and would be a new dependency); the tests must still reach every branch above — say in `## Result` how you checked (e.g. the stdlib `python -m trace --count --missing --module pytest`).
- Do not add tests for other test files, `pyproject.toml` or any CI file (test rule ⑤).

Local verification (CI is not on `main` — run before the commit and again before the merge, paste the summary lines into `## Result`):
- `python -m pytest` exits 0 (all tests, including the existing ones), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0. Local ruff is 0.15.14; the CI of PR #16 resolves a newer ruff (0.16.10) that additionally reports `SIM905` (a string literal split with `str.split()` instead of a list literal) — do not introduce that pattern in the new files. Do **not** touch `hilclaw/driver_state.py` or `pyproject.toml`: that is HQ-0002, an open owner decision.
- `git ls-files --eol hilclaw/cas.py tests/test_cas.py` shows `i/lf` for both.
- `git status --short` after the test run shows no stray file (no blob, no temporary file inside the repository).
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.gitignore`, `.claude/` and `.github/` are unchanged.

Process:
- Branch `claude/T-0008-cas-blob-store`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0008`; executor commits end with the trailer `Task: T-0008`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds); the CI step is the local rerun above (`gh pr checks` reports no checks while T-0003 is blocked — expected; the merge guard of T-0007 is not registered).
- Squash-merge per A-13 with `Task: T-0008` as the last line of the PR body, using `gh pr merge --squash` with that body (`--body-file` avoids quoting problems); delete the branch.
- Commit body: the provisional choices (module name, API and return type, `<hh>` = first two hex characters, lowercase-only digests, temporary file inside `blobs/sha256/` + `os.replace`, keep-existing on a repeated put, no creation of a missing root, error types) with one line of reason each, and the language line.
- `## Result`: hand the text to the driver in your final report instead of committing this task file on the branch, so that the diff check above holds (as T-0007 did). `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. PLAN P1-6 is **not complete** after this task; say so in `## Result`.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.

## Out of Scope
- `artifacts.json`: its record shape (hash, size, type, producing round, retention class, `gc_at`), its location in the data repository and any validator. The location and the round and candidate identity depend on OD-8, and it is a data-plane schema (CLAUDE.md BLOCKED reason). Later slice of P1-6, with or after P1-8.
- `blob.push(hash)` / `blob.fetch(hash)`: the synchronisation contract of C-3 and its backends (#5 B-2). C-3 says the MVP has a "local implementation" but not what a local push or fetch does; do not guess it here.
- Retention classes, the grace period, GC, deletion, `gc_at` (C-3: the MVP records the class only; no GC tool).
- `hilclaw.config.json`, environment overrides, discovering or cloning the data repository (PLAN P1-7); any write to the real `HIL-Claw-data` repository.
- The FR-10 HW tool contract and the mock backend (PLAN P1-1), the `cpu_standin` adapter (P1-2), the harness (P1-3).
- A command line, MCP exposure, hook integration (OD-18); read-only protection or sandboxing of the store (OD-14, OD-16).
- Hash algorithms other than SHA-256, compression, deduplicating hard links, a size limit, file locking across processes.
- Editing DRIVER.md, PLAN.md, CLAUDE.md, `ARCHITECTURE/` or the skills (document mode, separate changes); `.github/workflows/ci.yml` (PR #16).

## Follow-ups
- (P1-6 slice 2) `blob.push` / `blob.fetch` 2-function contract with the local implementation: needs a statement of what "local" means on a single machine (candidate: an identity or presence check behind a pluggable backend interface). If that cannot be read from C-3 and #5 A-2/A-3, it is a question for the owner (#5 B-2 is owner-only).
- (P1-6 slice 3, after OD-8 is closed by P1-8's ADR) `artifacts.json` record and validator, using `BlobRef` for hash and size.
- (P1-7) `hilclaw.config.json` supplies the `data_root` this module takes as an argument.
- (P0.5-2) The module-to-test mapping: `hilclaw/cas.py` → `tests/test_cas.py`.
- (P0.5-3 / CI) First coverage measurement and the CPython 3.11 run happen once CI exists.
- (decision to revisit) Whether stored blobs should be made read-only on disk, and whether `put_*` should verify an existing blob before trusting it.

## Result
