---
id: T-0416
title: Widen spec.write in hilclaw/spec_tool.py to the first coder call of a first-case round >= 1 - the request member techniques, check 7 through hilclaw.catalog, checks 8 to 10 through hilclaw.spec_feedback (ADR-0151 code slice 2; for PLAN P2-5)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-1, FR-5, FR-17, OD-6, OD-23, "PLAN P2-5"]
dependsOn: [T-0414, T-0415]
touchesFiles: [hilclaw/spec_tool.py, hilclaw/catalog.py, hilclaw/tools.py, tests/test_spec_tool.py]
estimatedSize: {loc: 230, files: 3}
hq: []
---
## Why

**Where things stand** (as of `main` `ab8b57b`):
- ADR-0151 (T-0414, landed as 3b0d3f5) decides the spec of the first coder call (`candidate` 1, `attempt` 1) of a round >= 1 in a first-case run with one candidate per round. It is written by `spec.write`, widened by one request member.
- Its Consequences name two code slices. Slice 1, `hilclaw/spec_feedback.py` (`attempts(data_root, run_id, round)`, kind `feedback_unreadable`), landed in T-0415 (PR #242, `e17b52e`). Nothing calls it yet.
- This task is slice 2: `spec.write` accepts a round >= 1 tuple with a `techniques` member, checks the techniques against the catalog (check 7), calls slice 1 for checks 8 to 10, and composes and writes the spec. T-0415's Follow-ups name it as the next task.

**D18 reading.** This is not a PLAN checklist item. It is the code of a landed record, so the priority rule of DRIVER §6 applies. It is needed for P2-5: P2-5 runs 5 rounds, and rounds 1 to 4 each need a spec before their coder call. Today `spec.write` refuses every round >= 1 tuple with `invalid_request`. It is not input hardening, wording or a refactor; it adds behaviour the first run needs.

**Not crossed.** The task stays inside ADR-0151 decisions 1 to 3. It does not decide or touch:
- the selection side: who chooses technique ids, by what criteria, how they reach the coder-driver, `hypotheses.json`, `decision.md` (HQ-0048);
- the coder's start, the coder-driver's round >= 1 delegation and `coder.run` for round >= 1 (HQ-0053; PLAN P2-1). `orchestration/` is not edited;
- the run tools' operations and the compiler log's code (HQ-0021, HQ-0026);
- injected cases (HQ-0031), OpenMP (HQ-0034), `profile`, `feedback.base`, repair specs, N > 1.

No data-plane member, file, kind value or version changes. The new kinds `catalog_unusable`, `technique_unknown` and `technique_not_applicable` are tool-layer names (ADR-0151 decision 3, "Kinds"). The request member `techniques` is a tool request member, not a run-file member.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py` only.

**D16.** The tests use fixture files in `tmp_path` and, at most, the repository's `catalog/cpu_standin/` read-only. Nothing starts `claude` or a container, or needs a board or an API key. ADR-0151 Consequences: no runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0416-<slug>`, PR title with `T-0416`, trailer `Task: T-0416`, `Task: T-0416` as the last line of the PR body for the squash); size cap; code-task test rule; language line in `Result`;
  - §8 (lines 136-142): HQ form, used only if you return BLOCKED.
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`. This is the rule for this task:
  - decision 1 (lines 31-35): scope, and the mock run whose list can only be empty;
  - decision 2 table and (b), (c), (e) (lines 37-53, 60-61): the source of each member, the technique list, its checks and kinds, the order, the empty list;
  - decision 3 (lines 63-77): the request, the result, the checks ① to ⑫ in order, what is read, the kinds, `id.round` not held against `STATE.json`, not journaled;
  - Walk-through (lines 79-91);
  - Consequences, slice 2 (line 114) and "Less exact, not edited" (line 120).
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` decisions 2 and 3: the round-0 spec and the checks ① to ⑧ that ADR-0151 reuses as ① to ⑥ and ⑪ to ⑫.
- `ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md` decision 4: the `{id, text}` entry and its applicability rule.
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md` decisions 2 to 4, and `tests/test_default_registry_schemas.py` lines 1-12 and 93-300: the input schema may use only the keywords `type`, `properties`, `required`, `additionalProperties` at the top level and `type`, `enum`, `minimum`, `maximum`, `pattern` inside a property. There is no `items`, `uniqueItems` or `if`/`then`, so the "required exactly when `round` >= 1" rule and the element checks live in the tool function, not the schema.
- Code:
  - `hilclaw/spec_tool.py` (all, 314 lines): the module to widen;
  - `hilclaw/spec_feedback.py` lines 1-160: module docstring and `attempts`. Call it; do not re-implement any of checks ⑧ to ⑩. Its `ToolFailure`s pass through unchanged;
  - `hilclaw/catalog.py` (all, 182 lines): `check`, `technique`, `SOURCE`, `APPLIES_TO`, `InvalidCatalogError`, and what each raises (module docstring lines 33-38);
  - `hilclaw/gemm_contract.py` lines 95-170: the record's `kind`, `dtype`, `layout` and `task_contract`'s `language`;
  - `hilclaw/keys.py` line 30: `MAX_INTEGER`;
  - `hilclaw/tools.py` lines 205-222: the `default_registry` docstring sentence on `spec.write`;
  - `hilclaw/spec.py` `validate`: the spec form of `guidance.techniques` and `feedback.attempts`.
- Tests: `tests/test_spec_tool.py` (all): fixtures `hw`, `op`, `instance_document`, `run`, `request`, `refused`, `tree`, the `KINDS` tuple and the order tests; `tests/test_spec_feedback.py` lines 1-170: its log and spec fixture helpers, which you may copy.

## Acceptance Criteria

### The request (check ①)
1. Members: `run_id`, `round`, `candidate`, `attempt`, all required, and `techniques`.
   - `techniques` is required exactly when `round` >= 1. It is refused with `round` 0, and refused when absent with `round` >= 1.
   - `techniques` is a JSON array (`list`). Each element is a `str` of the *name* form `[a-z][a-z0-9_]{0,31}` (ADR-0001 decision 1). No element occurs twice. The list may be empty and has no length bound.
   - `round` is an `int` (not a `bool`) from 0 to `keys.MAX_INTEGER`. `candidate` and `attempt` must each be 1 (ADR-0151 decision 1: no repair, no other candidate).
   - Every breach is `invalid_request`, with a message naming the member (and the element index for a bad element), raised before the data-root source is asked.
   - **A request of `round` 0 without `techniques` is answered exactly as today**: same checks, same document, same kinds, same messages. The existing round-0 tests keep passing unchanged except where they assert that a round >= 1 tuple is refused.
2. The input schema adds `techniques` as `{"type": "array"}` (not in `required`), and `round` gets `minimum` 0 and `maximum` `keys.MAX_INTEGER`. `candidate` and `attempt` stay fixed at 1. `tests/test_default_registry_schemas.py` must pass unchanged.

### Checks ② to ⑥
3. Unchanged from ADR-0138 (data root, `instance.json`, `candidates_per_round`, `op_signature`, `objective`), for every round.

### Check ⑦: the techniques (round >= 1 only)
4. For a **non-empty** list only:
   - The accelerator is `stated.hw_profile["accelerator"]` of the `instance.json` read at ③.
   - For each id in request order, the entry is `hilclaw.catalog.technique(accelerator, id)`, unchanged. The first id that fails decides.
   - `catalog_unusable` for: a missing directory (`FileNotFoundError`), `InvalidCatalogError` (an accelerator that is not of the *name* form among them), or any other `OSError` of the read. The message names the catalog directory relative to the repository's catalog root (for example `catalog/<accelerator>`), never an absolute path, and reports an `OSError` by class and system text.
   - `technique_unknown` for a `KeyError`: an id of the *name* form that names no entry. The message names the id and the accelerator.
   - `technique_not_applicable` when the spec's `task.op_signature.record` `kind`, `dtype` or `layout`, or `task.contract.language`, differs from the value given by `hilclaw.catalog.APPLIES_TO`. Parse the four `- <member>: <value>` lines; do not restate the values. Within ADR-0151 decision 1 this cannot be triggered by a valid `instance.json`, so test it by monkeypatching `catalog.APPLIES_TO` (or the parsed values).
   - An empty list reads no catalog and never fails here (a mock run with `[]` is written; with any id, `catalog_unusable`).
5. Catalog root: use `hilclaw.catalog.SOURCE` (via `technique`'s default). Tests may point it at a fixture directory with `monkeypatch.setattr(catalog, "SOURCE", ...)`. Do not add a request member or a definition parameter for it.

### Checks ⑧ to ⑩: the feedback (round >= 1 only)
6. Call `hilclaw.spec_feedback.attempts(data_root, run_id, round)` once, after ⑦. Its result is `feedback.attempts`. Its kinds (`feedback_unreadable`, the four `run_file_*`, `check_result_invalid`) pass out of the tool unchanged. Do not import its private helpers.

### Checks ⑪ and ⑫ and the document
7. The document for round `r` >= 1 is the round-0 document of ADR-0138 decision 2 with:
   - `id.round` = `r`; `candidate` 1, `attempt` 1, `candidates` 1, `relation` `single`;
   - `guidance.techniques` = the `{id, text}` list of ⑦ in request order (empty for `[]`);
   - `feedback.attempts` = the list of ⑧ to ⑩;
   - no `feedback.base`, `profile`, `repair`, `task.build` or `ext`.
   Check ⑪ (`spec_invalid`) and ⑫ (`spec_exists`, `spec_not_written`) run as today, with the final name under `rounds/<RRRR>/coder/candidates/01/attempts/01/spec.json`.
8. **Nothing is created before ⑫.** The only files read are `instance.json`, the catalog directory, and what `spec_feedback.attempts` reads. `STATE.json`, `decision/hypotheses.json` and `decision.md` are not read. `id.round` is not compared with `STATE.json`. Nothing is journaled and no line is appended to `events.ndjson`.

### Docstrings and description
9. `hilclaw/spec_tool.py`:
   - The module docstring states the widened request, the checks ① to ⑫ in order with their kinds, the round >= 1 document, and what is read. Replace "a tuple other than 0, 1, 1" and the other round-0-only sentences.
   - `_DESCRIPTION` names the round >= 1 call, the `techniques` member and when it is required, and every kind in check order, including `catalog_unusable`, `technique_unknown`, `technique_not_applicable`, `feedback_unreadable` and `check_result_invalid`. It still says "The result is {}." and that the data root is never part of the request, and still names the spec path pattern.
   - The new kind constants have `#:` one-line docs. `KIND_FEEDBACK_UNREADABLE` is re-exported from `spec_feedback`, not redefined.
10. `hilclaw/catalog.py`: docstring only. Replace "Nothing calls this module yet" and "the rule of decision 4 against a spec is the composition's and is not checked" (module and `technique` docstrings) with a statement that `spec.write` (`hilclaw.spec_tool`) calls it and checks that rule. No code change.
11. `hilclaw/tools.py`: docstring only. The `default_registry` sentence on `spec.write` ("the spec of the first coder call of round 0") also names the first coder call of a round >= 1 (ADR-0151). No code change.
12. Keep inline comments to a minimum (CLAUDE.md).
13. **Language**: Python, the existing module. Record the reason in one line in the commit body and in `Result`.

### Tests `tests/test_spec_tool.py` (fixture files only)
14. **Happy paths.** Each checks the exact written document, and that it passes `hilclaw.spec.validate`:
    - Round 1 after a round-0 attempt that passed sim and board (log lines and a round-0 spec as fixtures), `techniques` with two ids of a fixture catalog: `guidance.techniques` holds both `{id, text}` in request order; `feedback.attempts` is `[{round 0, candidate 1, attempt 1, techniques []}]`; the file is at `rounds/0001/.../01/spec.json`.
    - Round 1 with `techniques` `[]` and no earlier attempt: empty `techniques`, empty `attempts`, and no catalog read (assert by pointing `catalog.SOURCE` at a missing directory).
    - A round-0 request is still written exactly as before (the existing test).
    - Through the registry and the MCP name, a round >= 1 request succeeds (one test each, or one parametrised test).
15. **Branch cases.**
    - A mock-like run (an accelerator with no catalog directory): `[]` is written; one id is `catalog_unusable`.
    - A large `round` (for example 9999) with no earlier rounds is written with empty feedback.
    - The order of ids is the request's, not sorted.
16. **Negative and error cases.** Each asserts the kind, that nothing was created (compare `tree` before and after), and, where a path is named, no absolute path in the message:
    - `invalid_request`: `techniques` with `round` 0; `techniques` absent with `round` 1; `techniques` not a list (string, object, `None`); an element not a `str`; an element not of the *name* form (`"A"`, `""`, 33 characters, `"x-y"`); a duplicate id; `round` `True`, `-1`, `2**53`, `1.0`; `candidate` 2; `attempt` 2; an unknown member. Each is refused before the source is asked.
    - `catalog_unusable`: a missing directory, a directory that fails `catalog.check` (for example a file not named `<name>.md`), and an `OSError` on read (monkeypatch).
    - `technique_unknown`: an id of the *name* form with no entry; the first failing id decides when two fail.
    - `technique_not_applicable`: with `APPLIES_TO` monkeypatched to another `dtype`.
    - `feedback_unreadable`: an earlier attempt's `spec.json` that is not JSON. A damaged log line: `run_file_invalid`. These show the slice-1 kinds pass through.
    - `spec_exists` on a second round-1 call, and nothing changed.
17. **Check order** (one test per adjacent pair that can both fail):
    - `invalid_request` before `no_data_root`;
    - `objective_not_stated` before `catalog_unusable`;
    - `technique_unknown` before `feedback_unreadable`;
    - `feedback_unreadable` before `spec_invalid` (monkeypatched composition);
    - `spec_invalid` before `spec_exists`.
18. Update `KINDS`, the description order test and the kinds test for the new kinds. Each new kind matches the *name* form and is not in `tools.RESERVED_KINDS`. Replace the round >= 1 cases of `test_a_request_that_is_not_the_bring_up_tuple_is_invalid` with the new rule.
19. Read-only proof: monkeypatch or spy so that a round >= 1 call reads no `STATE.json`, `hypotheses.json` or `decision.md`, and the source is asked once.
20. **Gates.**
    - `python -m pytest` passes, including `tests/test_default_registry_schemas.py`, `tests/test_mcp_front.py`, `tests/test_catalog.py` and `tests/test_spec_feedback.py` unchanged.
    - `python -m ruff check .` and `python -m ruff format --check .` are clean.
    - The coverage gate in `.github/workflows/` is met (line and function >= 80% for `hilclaw/`). `spec_tool.py` should stay near 100%.
    - Every public function of `spec_tool.py` is tested (CLAUDE.md test rule ③).

### Process
21. Before review, `git diff origin/main --stat` lists only `touchesFiles`. Record the non-test LOC; the cap is 300 LOC in 5 files, tests excluded. If the change outgrows the cap, propose a split in `Follow-ups` and finish the current scope.
22. Open a Draft PR (title with `T-0416`). Run the `dev-reviewer` cycle (dev-code-review) for at most 7 rounds. Ask the reviewer explicitly to check:
    - (a) the request rule, the order ① to ⑫ and every kind against ADR-0151 decisions 2 and 3;
    - (b) that a round-0 request behaves exactly as before;
    - (c) that `spec_feedback.attempts` and `catalog.technique` are reused, not re-implemented;
    - (d) that no verification input reaches the spec, and nothing of HQ-0048, HQ-0053, HQ-0021 or HQ-0026 is decided;
    - (e) that the input schema uses only the keywords ADR-0077 reads.

    A finding that starts with `SECURITY` is BLOCKED.
23. With CI green and Approve, squash-merge with `gh pr merge --squash --body` (PR body ending in `Task: T-0416`) and delete the branch. Record the PR, the merge commit, the review rounds and the language reason in `Result`.

## Out of Scope

- `hilclaw/spec_feedback.py` (slice 1, landed); any change of its behaviour. If a defect is found there, note it in `Follow-ups`.
- `orchestration/` (coder-driver, Round-Manager): their round >= 1 steps wait on HQ-0048, HQ-0053 and PLAN P2-1.
- `coder.run` for round >= 1, `hilclaw/coder_tool.py`, `hilclaw/coder_call.py`.
- `profile`, `feedback.base`, repair specs (`attempt` > 1), N > 1, ranking (OD-7), lineage (OD-20), injected cases (HQ-0031).
- Writing compiler logs (HQ-0026), `cpu_standin` check operations (HQ-0021).
- The catalog's content under `catalog/`, and any code change in `hilclaw/catalog.py` or `hilclaw/tools.py` beyond the docstring sentences named above.
- Any data-plane schema change; edits of `ARCHITECTURE/`, `.claude/`, `.github/`, `PROCESS/` (other than this task's `Result`), settings files and `HIL-Claw-data`.

## Follow-ups

- (planner) None planned from ADR-0151 after this slice. The coder-driver's round >= 1 use of `spec.write` belongs to PLAN P2-1 with HQ-0048 and HQ-0053.

## Result

- PR #243, squash-merged as 86074b2 (branch claude/T-0416-spec-write-later-round, deleted). Review: 2 rounds, both Approve. Round 1 gave one Minor (the duplicate check of techniques copied a list prefix per element; now a set) and two Nits (an ADR citation added to the `#:` doc of KIND_TECHNIQUE_NOT_APPLICABLE; the changed round-0 message below, accepted as is). Round 2 found nothing. CI green (Python 3.11/3.14, coverage, C, sh, test presence).
- Language: Python. The tool's module and the modules it calls (catalog, spec_feedback) are already Python.
- Change: hilclaw/spec_tool.py widened (request with `techniques`, required exactly when round >= 1; check 7 through catalog.technique and the APPLIES_TO rule; checks 8 to 10 through one spec_feedback.attempts call; round >= 1 document under rounds/<RRRR>/). New kinds catalog_unusable, technique_unknown, technique_not_applicable; KIND_FEEDBACK_UNREADABLE re-exported. Input schema: techniques {"type": "array"}, round minimum 0 / maximum MAX_INTEGER. hilclaw/catalog.py and hilclaw/tools.py: docstring sentences only.
- One deviation from AC 1: a round-0 refusal for candidate or attempt other than 1 has a new message tail, because the old one ("only the spec of round 0") would now be false. Every other round-0 check, document, kind and message is unchanged.
- Size: non-test +259/-102 lines in 3 files. Tests: tests/test_spec_tool.py +427. spec_tool.py 100% line coverage; hilclaw/ 97%. Full local suite: 26540 passed, 856 skipped.
- Follow-ups: the module docstring of hilclaw/spec_feedback.py still says "Nothing calls this module until spec.write ... is widened", which is now false. That file was out of scope here; fix it in a later task that touches it, docstring only.
