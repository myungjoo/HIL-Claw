---
id: T-0366
title: Widen run.commit by ADR-0134 decision 7 so that a run's commit also takes in the two key record files of its key that HEAD does not hold (ADR-0134 slice 1, commit half; PLAN P2-7)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-13, FR-18, NFR-1, OD-26, OD-8, S0, S1]
dependsOn: [T-0364, T-0365]
touchesFiles:
  - hilclaw/run_commit.py
  - tests/test_run_commit.py
estimatedSize: {loc: 90, files: 1}
hq: []
---
## Why

PLAN P2-7 is a checklist item: store a round's hypothesis-outcome case at the round's end and look cases up by exact key. It comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

ADR-0134 (landed as 961dbfd, T-0364) decides that the Round-Manager stores the two key record files of its run's key through `key.store` (landed by T-0365, PR #209) and that `run.commit` takes those files into the run's next round-end commit where `HEAD` does not hold them (decision 7). Its Consequences name both halves as slice 1, "Now". This task is the second half. Without it the record files stay uncommitted in the data repository's working tree, so another clone, and S6 in another checkout, finds no key (ADR-0134 Alternatives, row (e) "Left uncommitted"), and every round-end commit of P2-5's first run leaves `db/` dirty.

The change touches landed behaviour that `tests/test_run_commit.py` pins. It does not need the unlanded start function of PR #186 (T-0324, BLOCKED on HQ-0032), because a test writes `instance.json` itself, and it touches none of that PR's files.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (code mode).
  - §3-5 (executor procedure, the resume rule, the 2 h 30 min time limit).
  - §5: naming (branch `claude/T-0366-<slug>`, a PR title containing `T-0366`, the trailer `Task: T-0366`, and `Task: T-0366` as the last line of the PR body used as the squash message); the size cap, which excludes tests; the language line in the Result; test rules ① to ⑤.
- `CLAUDE.md`: all rules. In particular the test rules (D12), the language policy (Python here, with one line in the commit body saying why), the A-13 code-mode procedure and its BLOCKED reasons (a data-plane schema change is one), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record to implement**: `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`, decision 7 "(e) How they enter a commit" and the Walk-through rows that name a commit; the Consequences item "Slices it enables" 1 and the "Less exact, not edited" item.
- Context: `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` decision 4 (the paths a commit takes in, the refusal for an owed range with a round from 1 and no key directory) and decision 8 (HQ-0043, not answered); `ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md` decision 3 (a record file is written once).
- Code:
  - `hilclaw/run_commit.py` (whole): the module docstring, `_DESCRIPTION`, `owed_rounds`, `commit`, `_assess`, `_keys`, `_is_file`.
  - `hilclaw/layout.py` `hw_profile_record`, `op_signature_file` (with `OP_SIGNATURE_FILES`) and `case_record`.
  - `hilclaw/instance.py` `read` and `Instance` (`hw_profile_key`, `op_signature.key`).
  - `hilclaw/key_records.py` `store_hw_profile` and `store_op_signature`, for writing record files in tests.
  - `hilclaw/further_turn.py`, only to confirm that it uses `owed_rounds` and the kinds, whose behaviour this task must not change.
- Tests: `tests/test_run_commit.py` (whole; its fixtures `a_run`, `write_instance`, `case`, `commit_by_hand`, `snapshot`, `changed`, `refused_unchanged`).
- Before you start, run `gh pr list`. Open PR #186 (T-0324) touches only `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`, so it does not overlap. If another open PR touches a file of `touchesFiles`, stop and return BLOCKED (DRIVER §3-3).

## Acceptance Criteria

1. **Which record files a commit takes in** (ADR-0134 decision 7). Every commit `commit` makes for the run also holds each of the two paths `db/<hw_profile_key>/hw_profile.json` and `db/<hw_profile_key>/<op_signature>/op_signature.json` that:
   - is formed from `hw_profile_key` and `op_signature.key` of the run's `instance.json` through the `layout` functions, with no listing of `db/`;
   - exists in the working tree as a regular file (a directory, a symbolic link or a missing path is not taken in);
   - `HEAD` does not hold. A path `HEAD` holds is never taken in again, even when the working tree's content differs; it stays as the working tree has it, unstaged.
   - is not excluded by the rules the module already applies to every path it takes in (a name ending with `.tmp`, a path the repository ignores, anything below `blobs/`). State this in the docstring; it is the module's existing rule, not a new one.
   No content of a record file is read or checked: a colliding or corrupt record file that `HEAD` does not hold is committed as it is.
2. **When the record files are looked for.** Only when a commit is made (a round end is owed). They are looked for at every owed commit, the round-0 commit included, not only when the owed range holds a round from 1. Nothing about them changes `owed_rounds`: the record files are neither a reason for a commit nor a reason for a refusal. With nothing owed, nothing is written and no record file is staged or committed.
3. **No key, no record, no new refusal.** When `instance.json` gives no key (missing, unreadable, invalid, of an unsupported version, or with no `op_signature`), no record file is taken in and nothing is refused on this account. The existing refusal `NoKeyDirectoryError` for an owed range with a round from 1 is unchanged, in its condition, its message and its order among the checks. Do not raise a new exception class or add a failure kind.
4. **Nothing else changes.** The rest of the commit's paths (`runs/<run_id>/` and the case files of the owed rounds from 1), the index handling, the lock, the torn-tail removal, `MESSAGE`, `owed_rounds`, every exception class and every kind stay as they are. The index entries of the taken-in record files are set to the commit, as for the other taken-in paths. A record file of another key, and every other file below `db/` (for example `best.json`), stays out and unchanged.
5. **Docstrings and description.**
   - The module docstring's paragraph "The commit holds, against `HEAD`, … and nothing else" names the two record files with the conditions of AC 1 and cites ADR-0134 decision 7.
   - `commit`'s docstring stays true.
   - `_DESCRIPTION` (the model-facing text) says the commit also holds the run's two key record files when they exist and the last commit does not hold them. Keep it one plain paragraph like the rest.
   - Do not edit `hilclaw/key_records.py`, `hilclaw/tools.py`, `orchestration/round-manager.md` or any ADR.
6. **Tests in `tests/test_run_commit.py`** (D12; each item is a test or a parametrised case). Write record files with `key_records.store_*` or with `write` as each test needs.
   - **Happy paths** (ADR-0134 Walk-through):
     - A fresh key: the round-0 commit (the first owed commit) holds `instance.json`, `STATE.json`, `events.ndjson` and both record files; `git status --porcelain` is empty afterwards.
     - A later round-end commit takes in record files created after the previous commit (the death-before-commit row) together with the round's case file.
     - Only `hw_profile.json` exists at one commit and `op_signature.json` appears later: each is taken in by the first commit after it exists.
     - Record files another run of the same key created, uncommitted, are taken in by this run's next commit.
   - **Never again** (the T-0364 reviewer hint): a record file `HEAD` holds is not taken in again, even after its working-tree content is changed by hand; that change stays unstaged, and `HEAD`'s blob is unchanged.
   - **Nothing owed**: with record files present and uncommitted and nothing owed, `commit` returns `False`, `HEAD` and the index are unchanged, and no record file is staged.
   - **No key**: for an `instance.json` that is missing, invalid, of version 9 and without `op_signature`, at a round-0 commit, the commit is made without any record file and with no refusal, while a record file present in the working tree stays untracked.
   - **The existing refusal**: an owed range with a round from 1 and no key is still refused with `NoKeyDirectoryError`, nothing removed or committed, with uncommitted record files present.
   - **Not a regular file**: a directory, and (where the platform allows creating one; skip otherwise) a symbolic link, at a record path is not taken in.
   - **Excluded paths**: a record path the repository ignores is not taken in.
   - **Out and unchanged**: a record file of another key and `best.json` stay out; extend or add to the existing "foreign paths" test.
   - **Content not read**: a corrupt `hw_profile.json` that `HEAD` does not hold is committed byte for byte.
   - Every existing test of the file still passes. If one pins the old "nothing else" behaviour for record files, change it to the new behaviour and say which in the Result.
   - Coverage: line ≥ 80% and function ≥ 80% for `hilclaw/`; every public function of `hilclaw/run_commit.py` stays covered.
7. **No data-plane change.** No member, file, path, value, version or `events.ndjson` kind of any data-plane file is added or changed, and no validator changes. Which paths a commit holds is none of these (ADR-0134 Consequences, A-13 reading). If the implementation needs any of these, stop and return BLOCKED with the question.
8. **Procedure.**
   - Code mode: open a Draft PR, run the reviewer cycle (dev-code-review), and get CI green (pytest, ruff, the test-existence gate and the coverage gate).
   - Then squash-merge with `gh pr merge --squash --body`, whose last line is `Task: T-0366`, and delete the branch.
   - The commit body carries one line on the language choice: Python, because the module and its tests are Python.
   - Never start `claude`, and use no stub of it either: this change needs none (D16).

## Out of Scope

- The `key.store` step in "The round steps" of `orchestration/round-manager.md` (ADR-0134 slice 2, written with P2-1's round steps).
- Whether a turn's end that ends no round commits anything (HQ-0043, ADR-0127 decision 8).
- Committing any other file of a key directory (`best.json`, `technique_stats.json`), the onboarding registry (#5 B-2, OD-26), OD-8 ⑱, HQ-0032.
- Any `ARCHITECTURE/` edit, any edit of an earlier ADR, and the "less exact" texts ADR-0134 Consequences lists other than the `hilclaw/run_commit.py` docstring and description.
- The bounded T-0349 follow-up on a failing fallback reset (PLAN "보류").
- Starting `claude`, or requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- ADR-0134 slice 2: the `key.store` step in `orchestration/round-manager.md`, with P2-1.

## Result

- **Outcome**: DONE. PR #210 (`claude/T-0366-run-commit-key-records`), squash-merged by the executor after reviewer Approve and CI green.
- **Review**: 1 round (dev-reviewer, Approve; https://github.com/myungjoo/HIL-Claw/pull/210#issuecomment-6288834354). Two nits left as they are, as the reviewer allowed: `_is_regular`'s `OSError` branch is reached only when a listed path vanishes before `lstat`, and `_stated_keys` mirrors `_keys` because the two fail differently (none vs. `NoKeyDirectoryError`).
- **Change** (`hilclaw/run_commit.py`): when a commit is owed, the two record paths are formed through `layout` from the keys of `instance.json` (the keys `_assess` already read, else a tolerant read that gives none for a missing, invalid, unsupported or op_signature-less file) and listed with `git ls-files --others --exclude-standard` against the scratch index read from `HEAD`; an exact match that is a regular file (`lstat`) joins the commit's paths and their index entries. A path `HEAD` holds is never listed, so never taken in again; ignored paths stay out; no content is read. `owed_rounds`, the refusals (including `NoKeyDirectoryError`, whose exception tuple is now the shared `_NO_INSTANCE`), the kinds, `MESSAGE` and the index handling are unchanged. Module docstring and `_DESCRIPTION` name the two files.
- **Tests** (`tests/test_run_commit.py`): 12 new tests (15 cases) for every item of AC 6; the symbolic-link case skips where none can be made (it skipped on the Windows development machine and runs on Linux CI). The existing foreign-paths test was extended with another key's two record files, which stay untracked; no existing assertion pinned the old "nothing else" behaviour for record files, so none changed.
- **Language**: Python, because the module and its tests are Python.
- **Follow-ups**: none new (ADR-0134 slice 2 stays with P2-1, as the task says).
