---
id: T-0347
title: Add hilclaw/coder_call.py, the coder-call function of ADR-0126 decision 3 (no front; container start behind a seam that tests replace)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-5, NFR-4, C-7, OD-23, OD-8, S0, S1]
dependsOn: [T-0346]
touchesFiles:
  - hilclaw/coder_call.py
  - tests/test_coder_call.py
  - hilclaw/scratch.py
  - hilclaw/bring_in.py
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-2 (coder-driver) and P2-1 (round 0 bring-up) are the first unchecked items in the P2 order (D18). This task is a slice of P2-2, so the D18 rule for non-checklist work does not apply. The P2-5 run needs a coder call.

ADR-0126 (landed as a5de4f6) settles two things for the first case:

- one deterministic layer-2 function performs the whole coder call, in ADR-0049's order (decision 3);
- the contract of that function: the request, the result and the failure kinds in their order.

Its Consequences call this "Code slices it enables" item 1, plannable **now**:

- a new module `hilclaw/coder_call.py` with `tests/test_coder_call.py`;
- the function sits over `scratch.create`, `bring_in.bring_in`, `scratch.remove`, `spec_file.parse` and `hilclaw.layout`;
- the container start (ADR-0049 slice (d)) sits behind a seam that the tests replace;
- there is no front.

The open HQs do not block this slice:

- HQ-0040 is the Bash entry vs registry tool `coder.run` question. ADR-0126 says "the contract below holds under either form, so the function slice does not wait for Q1".
- HQ-0041 (#5 A-8, coder model and tokens) blocks only slice (d), the real container and coder start. That stays out of scope here.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": the three-layer model, "개발 드라이버와 런타임의 구분" (D16), the tool-layer language policy, the code-mode branch/merge procedure (A-13), the test rules, and "코멘트 최소화".
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`:
  - decision 3, whole: the contract table and the four bullets under it;
  - decision 5: the scratch is the working directory, and the relative names `spec.json` and `output`;
  - decision 7: not journaled;
  - the Walk-through table;
  - the Consequences bullets "Code slices it enables" (item 1), "Open parts of the start" and "Less exact, not edited" (the `hilclaw/` lines).
- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`: decisions 1 to 4, properties P1, P2 and P4, L9, and the bullet "Slices for the planner".
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`, decisions 2, 3 and 4 (reserved kinds, the data-root source, the request members `run_id`, `round`, `candidate` and `attempt`).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`, decision 5 (B1 to B6).
- `ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`, decisions 2 and 3 (the `id` of a spec file stands to its path), read with `ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md` decisions 1 to 3.
- Code:
  - `hilclaw/scratch.py`, whole;
  - `hilclaw/bring_in.py`, whole;
  - `hilclaw/spec_file.py`: module docstring, `parse`, `final_name`;
  - `hilclaw/layout.py`: `check_run_id`, `attempt_artefact`, `attempt_dir`;
  - `hilclaw/data_root_source.py`, whole;
  - `hilclaw/tools.py`: `ToolFailure`, the reserved kinds, `RESERVED_KINDS`, the `_KIND` name rule;
  - `hilclaw/run_file_tools.py`: how it checks `run_id`, obtains the data root and reports an `OSError` without the data root's path. Use it as a style model for one module of the same layer; do not copy it.
- Tests as style models: `tests/test_scratch.py`, `tests/test_bring_in.py`, `tests/test_run_file_tools.py`.

## Acceptance Criteria

### Before editing

1. Run `gh pr list`. PR #186 (T-0324) touches only `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. If any open PR edits a file of `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).

### The module `hilclaw/coder_call.py`

2. **The language is Python.** It sits over the existing Python modules. Record the choice and the reason in one line of the commit body and of `## Result` (CLAUDE.md language policy).
3. **One public function performs one coder call**, for example `call(request, *, source, runtime)`:
   - `source` is a data-root source (ADR-0015 decision 3; `data_root_source.obtain`).
   - `runtime` is the seam of item 5.
   - There is no default runtime: the real one is slice (d).
   - Define the failure kinds as module constants. Every new kind satisfies the `_KIND` rule of `hilclaw/tools.py` and is not in `RESERVED_KINDS`.
   - A failure raises `hilclaw.tools.ToolFailure` with exactly one kind of ADR-0126 decision 3's table and a text that holds no path of the data root. `data_root_source.obtain` already raises `no_data_root` in that form.
4. **The request** is exactly `run_id`, `round`, `candidate` and `attempt` (ADR-0126 decision 3; ADR-0015 decision 4), all four required. Any other member, a missing one, a non-object request, or a value that `hilclaw.layout` refuses (`check_run_id`, the number rules of `attempt_artefact`) is `invalid_request`. It is checked before the data root is asked for.
5. **The seam.** One small interface stands for "the container and the coder process" (slice (d)). Take the shape below, or one equally narrow, and name it in the docstring:
   - `runtime.available()` returns whether a container runtime is there. `False` gives `no_container_runtime`.
   - `runtime.run(scratch_root)` starts the container with the scratch as the coder's working directory, waits for the coder process to end and removes the container before it returns (ADR-0049 P4). It returns the coder process's exit status as an `int`.
   - `runtime.run` raises a module-defined exception, for example `CoderNotStartedError`, when the container or the process could not be started. That gives `coder_not_started`.
   - A status other than 0 (a killed process included) gives `coder_not_ended`, and there is no bring-in (ADR-0126 decision 3, last bullet).
   - The seam does not compose the coder prompt. Decision 5 has the function compose a prompt that names `spec.json` and `output` relatively, but the rest of its text and how it is passed are open ("Open parts of the start"). This slice writes no prompt text and no `claude` flag. The prompt is slice (d)'s. Say so in the docstring.
6. **The order of the steps and checks follows the table of ADR-0126 decision 3 exactly**:
   1. `invalid_request`.
   2. `no_data_root`.
   3. `output_exists`: the attempt directory of `layout.attempt_artefact(..., "output")` lists an entry `output` of any kind.
   4. `spec_unreadable` and `spec_not_regular_file`, for the spec file of the tuple at `layout.attempt_artefact(..., "spec.json")`, read without following a link. A missing one is `spec_unreadable`.
   5. `spec_invalid`: `spec_file.parse` refuses it, or its `id` is not the tuple of the request, that is `spec_file.final_name(data_root, document)` is not the path read.
   6. `spec_unsupported` (`spec_file.UnsupportedVersionError`).
   7. `no_container_runtime`.
   8. `scratch.create(spec_path, keep_out=(data_root,))`. Its `ScratchError` gives the value it carries: `spec_changed`, or one of the other two if the file changed in between.
   9. `runtime.run`, giving `coder_not_started` or `coder_not_ended`.
   10. `bring_in.bring_in(scratch_root, output_path)`. Its `BringInError` gives the value it carries (the five of `BRING_IN_FAILURES`). An `OSError` of creating `output/` or of writing a file gives `output_not_written`. Its `OutputExistsError` (the name was taken during the call) gives `output_exists`. ADR-0126 decision 3 says `output_exists` refuses before the call "what `bring_in` would refuse after it"; mark this mapping in the docstring as the module's reading.
   11. `scratch.remove(scratch_root, keep_out=(data_root,))`.
7. **Nothing is created or consumed before `no_container_runtime`**: no scratch and no `runtime.run` call (ADR-0126 decision 3).
8. **The scratch is removed whatever happened after it was made**: on success and on every failure of steps 9 and 10.
   - On success the result is exactly `{"taken": [...names in bring_in's order...], "scratch_removed": <bool from scratch.remove>}`.
   - An empty `taken` is a result, not a failure (ADR-0055 B6).
   - On a failure after the scratch was made, a failed removal is added to the failure's text, and the kind stays the kind of the step that failed.
   - The function never retries a removal later (ADR-0049 ㉝ (나)).
9. **An error to which ADR-0126 assigns no kind** propagates unchanged and gets no invented kind. Examples: the `OSError` of making the scratch, and `InvalidScratchArgumentError`. List each such case in the docstring and in `## Result`. If you believe one needs a kind, write it as a follow-up; do not add it.
10. **Not journaled, no data-plane write** other than what `bring_in` writes below `output/` (ADR-0126 decision 7). It adds no event kind, member, file, version or validator. It starts no process of its own and does not import `subprocess`. Only the seam does any starting.
11. **No front**: no `__main__` entry, no `python -m` path and no registry entry in `hilclaw/tools.py`. Both fronts wait for HQ-0040.
12. **The module docstring** says the following, briefly, under "코멘트 최소화":
    - what the module is (ADR-0126 decision 3, ADR-0049 slices (a) to (c) wired together);
    - what it is not: slice (d), the prompt, either front, OD-19 behaviour for a call that does not end normally beyond the interim rule, time limits (OD-14), N > 1;
    - "Nothing calls it yet".

### The two docstrings

13. In `hilclaw/scratch.py` and `hilclaw/bring_in.py`:
    - Replace "Nothing calls them yet" / "Nothing calls it yet" with a sentence naming `hilclaw.coder_call` as the caller. This is the "Less exact" line of ADR-0126 for `hilclaw/`.
    - In `hilclaw/scratch.py`, rewrite "how the coder process is pointed at the copy is PLAN P2-2" in place, to point at ADR-0126 decision 5.
    - Change no behaviour of either module.

### Tests `tests/test_coder_call.py` (D12)

14. **Use a fake runtime object only.** A fake runtime can write files into the scratch's `output/` and return a status. No real container runtime, no `claude` and no stub `claude` is needed or started (D16). Use `tmp_path` as the data root. Build the spec file with a valid version-2 document; a test helper of the existing spec tests may be reused.
15. **Cover at least these cases**:
    - happy: one admitted file taken, `scratch_removed` true, and the scratch no longer exists;
    - an empty `taken`, with no `output/` created;
    - every failure kind of the table, each reached by its own test;
    - the order of the checks: when two failures hold at once, the earlier kind wins (for example `output_exists` before `spec_unreadable`, and `spec_invalid` before `no_container_runtime`);
    - `runtime.run` is not called and no scratch exists for every failure before step 8;
    - the scratch is removed after `coder_not_started`, `coder_not_ended` and a bring-in failure;
    - a failed removal: monkeypatch `scratch.remove` to return `False`. Check `scratch_removed: false` on success, and the text on a failure path;
    - negative requests: an extra member, a missing member, wrong types, `round` or `candidate` out of range, a bad `run_id`, a non-dict request;
    - a spec whose `id` names another tuple, giving `spec_invalid`;
    - a version-1 spec, giving `spec_unsupported`;
    - a spec path that is a directory or a symbolic link, giving `spec_not_regular_file`. Skip the link case where the platform cannot make links.
16. **Coverage gates**: `pytest` and `ruff` pass locally and in CI. `hilclaw/` line and function coverage stay at or above 80 %, and every public function of the new module is tested.

### Mode

17. Code mode (A-13):
    - Branch `claude/T-0347-coder-call-function`, with the trailer `Task: T-0347` on commits.
    - Open a Draft PR whose title contains `T-0347` and whose body ends with `Task: T-0347`.
    - Run the reviewer cycle (dev-code-review, at most 7 rounds), then wait for CI green.
    - Squash-merge with `gh pr merge --squash --body` and delete the branch.
    - Never run `git push --force*`.

## Out of Scope

- ADR-0049 slice (d): the real container runtime adapter, the image, container flags, the sign-in inside, the coder's `claude -p` flags, its model and permission mode, the coder prompt text. These wait on HQ-0041 (#5 A-8) and later records.
- Either front: the `python -m hilclaw.coder_call` entry, and the `coder.run` registry tool. These wait on HQ-0040.
- `orchestration/agents/coder-driver.md`, any edit to `orchestration/round-manager.md`, and `hilclaw/turn_loop.py` / `hilclaw/turn_definition.py`.
- Journaling or spend accounting of the call (ADR-0126 decision 7; #5 A-8). Time limits (OD-14). Repair calls and taking files from a call that does not end normally (OD-19). A second call for one tuple (OD-23 ① (가)). N > 1 (OD-29). Cleanup of scratches left by a dead process (OD-8 ㉝ (나)).
- Writing `spec.json` (OD-6 rest).
- Any `ARCHITECTURE/` edit, data-plane schema or validator change, new external dependency, or `.claude/` / settings edit.
- Starting a real `claude` or a container, or requiring a logged-in `claude`, a container runtime, a board or an API key on this machine (D16).

## Follow-ups

- After HQ-0040: the front (Bash entry or `coder.run`), `orchestration/agents/coder-driver.md`, and the delegation step in `orchestration/round-manager.md`.
- After HQ-0041 and a design record for the start: slice (d), the real `runtime` with the coder prompt.
- Alternatively next: an ADR on OD-8 sub-question ⑪ (which step commits a round, and how a fresh turn learns that a commit is owed).

## Result

- **DONE.** PR #198 squash-merged as `c9466e4`; branch deleted. Reviewer cycle: 2 rounds. Round 1 asked for changes: (1) the docstring wrongly said the runtime composes the prompt; it now says, as ADR-0126 decision 5 does, that the function composes it and its text is slice (d)'s; (2) step 3 had an unassigned `attempt_directory_unlistable`, which was removed, so that `OSError` now propagates; (3) a wrap nit. Round 2: Approve. CI green on `808578b`: Python 3.11 and 3.14, coverage, test presence, sh and C gates.
- **Language:** Python, because the function wires together existing Python modules of the layer-2 package (`scratch`, `bring_in`, `spec_file`, `layout`).
- **Module:** `hilclaw/coder_call.py`.
  - API: `call(request, *, source, runtime)`, `CoderNotStartedError`, `FAILURE_KINDS` (in check order) and seven new `KIND_*` constants, none reserved.
  - The seam: `runtime.available()` and `runtime.run(scratch_root) -> int`. There is no default runtime, prompt, front or journaling, and no `subprocess`.
  - Coverage of the new module: 100 % lines.
  - Local run: 23889 passed, 710 skipped on Windows. The symbolic-link test is skipped there and runs in CI.
- **Errors that propagate unchanged** (ADR-0126 assigns them no kind):
  - `TypeError` for a `source` that is not callable;
  - the `OSError` of listing an attempt directory that exists (step 3);
  - any exception of `runtime.available()`;
  - `scratch.InvalidScratchArgumentError` and the `OSError` of `scratch.create` or `scratch.remove`;
  - any exception of `runtime.run` other than `CoderNotStartedError`;
  - a `TypeError` when the status is not an `int`;
  - `bring_in.InvalidBringInArgumentError`.

  Each one raised after the scratch was made comes after the removal was tried.
- **Readings of the module**, marked in the docstring:
  - `bring_in`'s `OutputExistsError` gives `output_exists`.
  - At step 4, a spec file whose `fstat` identity differs from its `lstat` identity gives `spec_unreadable`.
- **Follow-ups**, beyond those listed above:
  - (a) Possibly a kind for an attempt directory that cannot be listed at step 3. Today its `OSError` propagates, and the text may name a path of the data root.
  - (b) The function validates the bytes it read itself. `scratch.create` then copies the file in a second read, and nothing checks that the copy is the same bytes. A later record could ask for a compare, which would give `spec_changed`.
