---
id: T-0324
title: Add the start function of ADR-0115 - one deterministic function in a new module `hilclaw/start_instance.py` that checks a first-case instance (ADR-0076), refuses a given `run_id` (ADR-0111), builds the id (ADR-0027), writes `instance.json` (ADR-0025), stops on a taken name (ADR-0109) and returns the id; no caller bound
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-13, NFR-1, OD-8, "#5 A-12", "#5 D12"]
dependsOn: [T-0323]
touchesFiles:
  - hilclaw/start_instance.py
  - tests/test_start_instance.py
estimatedSize: {loc: 140, files: 1}
hq: []
---
## Why

PLAN P1-8 (runtime STATE/instance/events schemas) is open. ADR-0115 (landed in 86abd39 by T-0323) decided that, for the instances of ADR-0076 decision 1, the start is **one deterministic function of the layer-2 package** that every way of starting calls. Its Consequences name the code slice: the function joins `hilclaw.instance_start.prepare`, `hilclaw.run_id.new` and `hilclaw.instance_file.write`; it binds the `accelerators` and `covers` of `prepare`; it builds the bytes in the written form of ADR-0018 decision 2; it answers `NameTakenError` as ADR-0109 says (the code slice of ADR-0109); it has no `run_id` parameter, refuses a given id and returns the built id (the code slice of ADR-0111). ADR-0115 says this slice "waits on no open question" and that the three existing modules need no change. This task is that slice and nothing more. Its callers (a command line, a UI, the Round-Manager of P2-1, a CI) stay open (OD-23, UC-1) and are not part of it.

Choices the records leave to this code task, fixed here so that the executor does not have to invent them (each is to be written in the module docstring as "a convention of this module, not a rule of a record"):

- **Inputs**: a parsed `instance.json` document (exactly a `dict`, as `prepare` takes) and a keyword-only `data_root` (a `str` or path, used as `instance_file.write` uses it; no config lookup, no environment variable). No `run_id` parameter and no `**kwargs`.
- **What counts as a given id** (ADR-0111 decision 2: "the start does not drop a given id unreported and does not use it as the run's id"; "Whether an input form has a place for such a value at all is that form's matter"): the function has no parameter for one, and a document whose top level holds a member named `run_id` is treated as a given id. Without this, such a member would be written into `instance.json` as an undefined member while the run runs under another id, which ADR-0111 decision 2 excludes. This is the start's refusal, not a validity rule: `hilclaw.instance` keeps accepting such a file, and no reader changes.
- **When the id is built**: after every check has passed and immediately before the write (ADR-0115 decision 2 leaves the moment open and notes that building an id creates nothing; a refusal therefore builds no id).
- **Reports** are exceptions to the caller, each told apart from the others (ADR-0109 decision 3, ADR-0111 decision 2): the refusal of a given id, the refusal of ADR-0076 (`instance_start.MissingMembersError`, passed through), the stop of ADR-0109 (a new exception carrying the id in use, no `OSError`), and file-system failures (`OSError`, passed through). Their wording is the module's; no UI form is chosen.

## Required Reading

- `PROCESS/DRIVER.md`: §3 steps 5-6 (lines 63-77: executor procedure, resume rule, branch contention, time cap 2h30), §5 (lines 86-114: format, naming convention with the `Task: T-0324` trailer and the PR-body last line, size cap, test rules D12).
- `CLAUDE.md`: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책" (record the language choice in the commit body), "브랜치·merge 절차" (code mode), "테스트 규칙", "미결은 발명하지 않는다".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`: Decision 1-3 (lines 44-98) and Consequences (lines 110-135, especially lines 112-119).
- `ARCHITECTURE/decisions/ADR-0111-od8-run-under-given-id.md`: decisions 1-3 (lines 24-45), Walk-through (lines 55-65), Consequences (lines 78-85).
- `ARCHITECTURE/decisions/ADR-0109-od8-instance-start-name-taken.md`: decisions 1-3 (lines 23-44), Walk-through (lines 57-66), Consequences (lines 80-86).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md`: decisions 1-3 (lines 23-58).
- `ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md`: decisions 2-4 (lines 29-54).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`: decisions 5 and 6 (lines 57-71).
- `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`: decision 2 (lines 28-40, the written form: one JSON object, UTF-8 without BOM, LF line ends and a final line feed, no member order fixed).
- Code to call, read their docstrings in full: `hilclaw/instance_start.py` (`prepare`, `OutOfScopeError`, `MissingMembersError`), `hilclaw/instance_file.py` (`write`, `NameTakenError`, `WrittenFormError`), `hilclaw/run_id.py` (`new`; tests replace `_utc_now` and `secrets` in that module), `hilclaw/instance.py` (`validate`, `parse`, `read`). The bound names: `hilclaw.mock_backend.NAME`, `hilclaw.standin_profile.ACCELERATOR`, `hilclaw.gemm_contract.covers`.
- Test style to follow: `tests/test_instance_start.py` and `tests/test_instance_file.py` (fixtures for valid documents, `tmp_path` data roots).

## Acceptance Criteria

1. Entry check: `gh pr list` and `git log origin/main --grep='^Task: T-0324'` (DRIVER §3-5 resume rule). The only open PR expected is #179 (T-0284; `hilclaw/clang_build.py`, `tests/test_clang_build.py`). If an open PR touches `hilclaw/instance_start.py`, `hilclaw/instance_file.py`, `hilclaw/run_id.py` or `hilclaw/instance.py`, report it and stop.
2. New module `hilclaw/start_instance.py` (Python; record the reason in the commit body). Its module docstring states, briefly: what it renders (ADR-0115 decision 2 for the scope of ADR-0076 decision 1); the conventions of the Why section as this module's own; and what it does not do (it binds no caller, is no FR-10 tool and is not registered in `hilclaw.tools`, has no command-line or MCP entry, writes no `STATE.json` or `events.ndjson`, looks at no `runs/<run_id>/` before the write, takes no lock, makes no commit, reads no stored hw_profile record (⑱), checks no source commit (⑳), fills in no `owner`/`project` (㉛), and says nothing of a run directory without `instance.json`). Keep it short; no multi-line comments in the code (CLAUDE.md).
3. Public surface (names may be adjusted only if a collision is found; say so in Result):
   - `GivenRunIdError(Exception)`: the refusal of ADR-0111 decision 2. Not a subclass of `ValueError`, `OSError`, `MissingMembersError` or `OutOfScopeError`. Its message says the start takes no `run_id` and shows no value of the document.
   - `RunIdInUseError(Exception)`: the stop of ADR-0109. Attribute `run_id` holds the id the start built; the message names that id and says nothing was written under the name. Not an `OSError`. Raised `from` the `NameTakenError` or `from None` (choose one and state it); it reports nothing of the entry under the name.
   - `start(document, *, data_root)`: returns the built `run_id` (`str`).
4. Order of `start` (observable behaviour; the implementation may call `prepare` once and map its outcome):
   1. What `instance_start.prepare(document, accelerators=(mock_backend.NAME, standin_profile.ACCELERATOR), covers=gemm_contract.covers)` raises for type, validity (`hilclaw.instance.validate`) and scope (`OutOfScopeError`) passes through unchanged.
   2. Then, if the top level of `document` holds `run_id`: `GivenRunIdError`; no id is built, nothing is written, and this comes before any `MissingMembersError` (ADR-0111 decision 2 places the look between the scope and the filling-in of `n_max`).
   3. Then `MissingMembersError` from `prepare` passes through unchanged.
   4. Then one id from `run_id.new()`; the prepared document is turned into bytes (UTF-8, no BOM, LF line ends, final line feed, `allow_nan=False`; indentation and member order are the module's choice, stated in the docstring) and handed to `instance_file.write(data_root, run_id, content)`.
   5. `NameTakenError` becomes `RunIdInUseError` with that id; nothing is retried and no other id is built. Every other exception of `write` (`OSError` and its subclasses, `FileNotFoundError`/`NotADirectoryError` for a bad `data_root`) passes through unchanged.
   6. On success the id is returned. `document` is never modified.
5. `hilclaw/instance_start.py`, `hilclaw/instance_file.py`, `hilclaw/run_id.py`, `hilclaw/instance.py` and every other existing module are unchanged. No change to `hilclaw/tools.py`, `hilclaw/__main__.py`, `hilclaw/mcp_front.py` or any registry. No new dependency.
6. Tests in `tests/test_start_instance.py` (D12: every public function and class; happy, error, branch and negative cases):
   - Happy: a valid `cpu_standin` document and a valid mock document, each with all required members, write `runs/<id>/instance.json`; the returned id matches `hilclaw.layout.check_run_id` and the form of ADR-0027 (with `run_id._utc_now` and `secrets.randbits` replaced, the id equals the composed one); `hilclaw.instance.read` reads the written file and states what the document stated; `n_max` is filled with `measurement.N_MAX_DEFAULT` when absent and a given `n_max` is kept; the bytes end with `\n`, hold no `\r`, have no BOM; undefined members of the document are kept.
   - Given id: a document with a top-level `run_id` (valid or not as a name; with all members, and with members missing) raises `GivenRunIdError`, not `MissingMembersError`; no directory under `runs/` is created and `run_id.new` is not called.
   - Refusals pass through: invalid document (`InvalidInstanceError`, `UnsupportedVersionError`, non-`dict` `TypeError`), out-of-scope accelerator and an op_signature `gemm_contract.covers` does not cover (`OutOfScopeError`), each missing member set (`MissingMembersError` with the `REPORT_ORDER` order); none writes anything or builds an id.
   - Name taken: a pre-existing `runs/<id>/instance.json` for the patched id raises `RunIdInUseError` with `.run_id` equal to that id, is no `OSError`, leaves the existing file byte-for-byte unchanged, builds exactly one id, and leaves no temporary file of this call.
   - File system: a `data_root` that does not exist (`FileNotFoundError`) and one that is a file (`NotADirectoryError`) pass through; an `OSError` raised by a patched `once_write.write_once` passes through unchanged.
   - Negative: a value that cannot be written as JSON without NaN (if `validate` lets one through; otherwise assert `validate` refuses it), `start` called with a `run_id=` keyword (`TypeError` from Python, not swallowed), positional `data_root` (`TypeError`), and `document` not mutated in every case above.
   - Do not add tests of test code, CI or hooks (D12 rule 5).
7. Local gates: `pytest` (whole suite) passes, `ruff check` and `ruff format --check` (as configured in `pyproject.toml`) are clean, and `hilclaw/` line and function coverage stay at or above 80% as CI measures them. The test-existence check of P0.5-2 passes for the new module.
8. No other file changes: `git diff --stat origin/main` lists only the two touchesFiles; `git diff --check` is clean. Name check: `hilclaw/`, `tests/` and `ARCHITECTURE/` hold no earlier `GivenRunIdError`, `RunIdInUseError` or `start_instance`; the module adds no event kind, member, `step` value, blob `type`, spend axis, tool or tool-failure kind.
9. Code mode (CLAUDE.md A-13): branch `claude/T-0324-instance-start-function`; Draft PR with `T-0324` in the title and `Task: T-0324` as the last line of the body; context-isolated reviewer cycle of at most 7 rounds; CI green; then `gh pr merge --squash --body` with that body, and delete the branch. If the reviewer finds that a convention in the Why section decides something a record left open (for example the `run_id` member as a given id), stop with BLOCKED `requirement-unclear` and quote the finding in Result instead of choosing another reading.
10. Start no `claude` process, compiler, kernel or container (D16). The tests touch only `tmp_path`.

## Out of Scope

- Any caller of the start: a command-line entry (`python -m hilclaw.<module>`), a UI, a Round-Manager prompt or agent definition (P2-1), a CI job, an MCP or registry entry (ADR-0115 decision 3).
- Writing or ordering the first `STATE.json` (⑩), an `events.ndjson` line (⑧), a lock (OD-17), a git commit of the run (⑪).
- Where values come from: a stored hw_profile record (⑱), the source-commit check (⑳), `owner`/`project` (㉛), `injections` (T-0233, BLOCKED), budgets, N ranges.
- Instances outside ADR-0076 decision 1; branches, continuations, resumes (①); a run directory without `instance.json` (⑰'s last part).
- Any change to `hilclaw/instance_start.py`, `hilclaw/instance_file.py`, `hilclaw/run_id.py`, `hilclaw/instance.py`, their docstrings (ADR-0115 lists two docstrings as less exact; they are not edited here), or any `ARCHITECTURE/` file.
- PR #179 (T-0284) and the unlanded branches of the BLOCKED tasks T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286, T-0318.

## Follow-ups

- A small document task for the three round-7 findings on ADR-0115 left by T-0323 (Result, Follow-ups): the decision 3 / (a') wording on "choosing an agent as a caller", the "at its last step" nit in decision 2, and the ADR-0111 Alternatives row 2 (c) entry in the less-exact list.
- Callers of the start, when OD-23 and UC-1 allow one to be chosen.

## Result
