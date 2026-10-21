---
id: T-0385
title: Add the registry tool coder.run of ADR-0141 decisions 2 and 3 over hilclaw.coder_call.call, bound in default_registry to a package runtime that reports no container runtime (ADR-0141 Consequences slice 1; PLAN P2-2)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-5, OD-23, OD-18, NFR-4, S0, S1]
dependsOn: [T-0384]
touchesFiles:
  - hilclaw/coder_tool.py
  - hilclaw/tools.py
  - hilclaw/coder_call.py
  - tests/test_coder_tool.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
estimatedSize: {loc: 170, files: 3}
hq: []
---
## Why

PLAN P2-2 (the coder-driver, "OD-23 종결 필요(§9 ADR 경로)") is a checklist item. In the P2 order of the PLAN P2 head it comes before P2-5, so the D18 rule for work outside the checklist does not apply. P2-5's first run needs a round-0 coder call that an agent can reach.

ADR-0141 (task T-0384, landed on `main` as 3815c42) records the owner's answer to HQ-0040: form (T), the coder-driver reaches `hilclaw.coder_call.call` as the registry tool `coder.run` through the MCP front, with no Bash. ADR-0141 Consequences lists four code slices, in order. This task is **slice 1**: the definition of `coder.run` over `hilclaw.coder_call.call` (decision 2), bound to a package runtime whose `available()` returns false (decision 3), registered in `default_registry` of `hilclaw/tools.py`, with its tests, and the docstrings of `hilclaw/coder_call.py` and `default_registry`. Slices 2 (the turn-session environment in `hilclaw/turn_loop.py`), 3 (`orchestration/agents/coder-driver.md`) and 4 (the Round-Manager's step 2) are later tasks.

Open HQs checked: HQ-0053 (how the sign-in reaches the coder's container, slice (d)) is not crossed. Nothing here starts a container, names an image, a flag, a sign-in, a prompt or a permission mode of the coder's `claude -p`; the package runtime starts nothing. HQ-0042 and HQ-0056 are runtime acceptance items; nothing here closes them. HQ-0041 (2) (the coder's tokens) is not crossed: nothing is counted. Nothing of the unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*` or `claude/T-0375-*` is relied on. The files do not overlap open draft PR #186 (T-0324), which touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`. This is the specification. Read closely: **decision 2** (the tool), **decision 3** (the runtime while slice (d) is absent, and what P2-5's stub verification needs), the Walk-through rows "A round-0 turn today" and "A test of a call that brings in files", Consequences **slice 1**, and the "Less exact, not edited" bullet on `hilclaw/coder_call.py`. Decisions 4 to 6 are read only to know what slices 2 to 4 will do.
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`: decision 3 (the request, the result and the kinds, "Under (T)") and decision 7 (not journaled).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4. `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`: decisions 2 to 4 (what the `ACCEPTED` entry of the new tool must satisfy).
- `hilclaw/coder_call.py`, the whole file: `call`, `FAILURE_KINDS`, the kind constants, `CoderNotStartedError`, and the runtime seam in the module docstring.
- `hilclaw/spec_tool.py`: the module docstring, `NAME`, `_DESCRIPTION`, `definition` and `_input_schema`. This is the closest pattern (same request members, same data-root source handling).
- `hilclaw/tools.py`: the module docstring, `ToolDefinition`, `ToolFailure`, the reserved kinds, `Registry`, and `default_registry` with its docstring. `hilclaw/mcp_front.py`: the module docstring, `mcp_name`, and `main` with its `registry` argument. `hilclaw/__main__.py`: `main` with its `registry` argument.
- `hilclaw/layout.py`: `attempt_artefact` and `check_run_id` (the forms of the request's members). `hilclaw/keys.py`: `MAX_INTEGER`.
- Tests as the pattern for the new test file and for the listing tests that must be updated: `tests/test_coder_call.py` (`FakeRuntime` and its fixtures: a data root with `instance.json` stating a `coder_model` and a `spec.json` written for the tuple), `tests/test_spec_tool.py`, `tests/test_default_registry_schemas.py` (its schema reading knows only the keywords `type`, `enum`, `minimum`, `maximum`, `pattern` inside a property), and the `spec.write` / `spec_write` and `timings.compare` / `timings_compare` entries in `tests/test___main__.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`, `tests/test_mcp_front.py` and `tests/test_tools.py`.

## Acceptance Criteria

1. **New module** `hilclaw/coder_tool.py`. The executor may choose a clearer name and then updates `touchesFiles` in `## Result`. Its module docstring names ADR-0141 decisions 2 and 3, says that the tool performs `hilclaw.coder_call.call` and adds nothing to its contract (the request, the result and the kinds are those of `coder_call`, referred to and not restated), that it is not journaled, and the choices left to the code slice (ADR-0141 decision 2, "Left to the code slice") as made here. It exposes:
   - `NAME = "coder.run"`;
   - `definition(source, runtime)`, which returns one `tools.ToolDefinition` for `coder.run`. Its tool function calls `coder_call.call(request, source=source, runtime=runtime)` and returns what it returns. The source is not called and the runtime is not used at definition time. A non-callable `source` raises `TypeError`, as `spec_tool.definition` does. What a `runtime` lacking `available` or `run` does at definition time is the executor's choice, stated in the docstring and tested;
   - the package runtime of ADR-0141 decision 3: an object (class or instance, the executor's choice) whose `available()` returns `False`. It starts no process and no container, reads no environment variable and takes no option. What its `run` does if called directly is the executor's choice (for example raising `coder_call.CoderNotStartedError`); it must start nothing, and the choice is stated and tested. Its docstring says that slice (d) replaces this binding in the source (ADR-0126 slice 3).
2. **No handling added** (ADR-0141 decision 2). The tool function adds no check, kind, message or exception handling of its own: a `tools.ToolFailure` of `coder_call.call` passes through unchanged, and every exception the function propagates propagates unchanged (the front's `tool_crashed` handling in `tools.call` stays the front's). The message of `no_container_runtime` stays the function's text. No kind is added to `RESERVED_KINDS` and no new kind is added anywhere.
3. **Description and input schema** (left to the slice by ADR-0141 decision 2).
   - The description tells the model: that the tool performs the coder call for one attempt of a run (the spec of that attempt must already be written by `spec.write`), that the data root is never part of the request, the four request members and their forms, the result's shape (`taken`, `scratch_removed`), and every kind of `coder_call.FAILURE_KINDS` with its meaning, in that order. It follows the manner of `spec_tool._DESCRIPTION`.
   - It does **not** ask the user to install anything and does not tell the model to ask for an installation: which part asks is OD-8 ㉝ (가) (ADR-0141 decision 3). It may say that `no_container_runtime` is the answer while the package can start no container.
   - The input schema states `run_id` (the pattern of `spec_tool`), `round` (integer, minimum 0), `candidate` and `attempt` (integers, minimum 1), the maxima that `layout.attempt_artefact` enforces if it enforces any, `required` all four and `additionalProperties: false`. Every request the schema refuses must be refused by the function before the data-root source is asked (ADR-0077; checked by `tests/test_default_registry_schemas.py`).
4. **`hilclaw/tools.py`**: `default_registry(data_root_source)` keeps its signature and registers `coder.run` from the new module, bound to `data_root_source` and to the package runtime of AC 1, in the source only. Its docstring names the tool, ADR-0141 decisions 2 and 3, that the coder-driver performs the round-0 coder call with it, and that until slice (d) replaces the binding every call that passes the checks before `no_container_runtime` fails with that kind. The sentence "A tool is added here, in the source, and in no other way…" stays true. Building the registry still imports no NumPy (the existing checks in `tests/test_check_definition.py`).
5. **`hilclaw/coder_call.py` docstrings** (ADR-0141 "Less exact, not edited", slice 1's part): "Nothing calls it yet" becomes the fact that the registry tool `coder.run` calls it; "either front of ADR-0126 decision 3 (Q1)" becomes the front of ADR-0141 (form (T), the tool), no longer a "what this module is not" item; the sentence "`runtime.available()` returns whether a container runtime is there" is made accurate for the package runtime, which answers false wherever one is there until slice (d). Behaviour of `coder_call` is unchanged; no other sentence is edited.
6. **Tests** in a new file `tests/test_coder_tool.py`. They use a temporary data root built by the test and stub runtimes defined in the test (as `tests/test_coder_call.py` does). No `claude` is started, stub or real, and no container program is run. They pass on Linux CI and on the local Windows machine. They cover at least:
   - **happy**: with a data root holding a valid `instance.json` (stating a `coder_model`) and the spec of tuple 0/1/1, and a stub runtime whose `available()` is true and whose `run` writes `kernel.c` into the scratch's `output` and returns 0, the tool returns `{"taken": ["kernel.c"], "scratch_removed": true}` and the file is brought in under the attempt's `output`. The same result through `tools.call` on a registry holding the definition, and **through the MCP front**: a registry with `coder.run` bound to the stub runtime, served by `hilclaw.mcp_front.main(registry=...)`, answers `tools/call` of `coder_run` with that result (ADR-0141 decision 3, Walk-through "A test of a call that brings in files").
   - **the package runtime**: `available()` is `False`; with the same fixtures and the package runtime, the tool fails with `no_container_runtime` and the function's message, and creates nothing under the data root (the tree is unchanged; no scratch is left); its `run` behaves as AC 1 chose. The tool of `default_registry` (bound to a source returning the test's data root) gives the same answer (Walk-through "A round-0 turn today").
   - **pass-through (branch)**: kinds raised before the runtime is asked pass through unchanged with the function's kind and message: `invalid_request` (an extra member, a missing member, a bad `run_id`, a negative or `bool` number, `candidate` 0), with the source not asked; `no_data_root`; `run_file_missing` for a missing `instance.json`; `coder_model_not_stated`; `output_exists`; `spec_unreadable` for a missing spec. Kinds after the runtime: `coder_not_started` (stub `run` raises `CoderNotStartedError`) and `coder_not_ended` (stub returns non-zero). One case per kind is enough; the full ordering is `tests/test_coder_call.py`'s.
   - **negative and error**: a non-callable `source` raises `TypeError` at definition time; the definition-time choice of AC 1 for a bad `runtime`; an exception of the stub runtime other than `CoderNotStartedError` propagates from the tool function unchanged and becomes `tool_crashed` through `tools.call`; the tool function is not journaled (no `events.ndjson` is created or changed by any call).
   - **registry**: `coder.run` is listed by `default_registry` and through the MCP front as `coder_run`, and through the command-line front; the listing tests in the test files of `touchesFiles` are updated; `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry (`{"run_id": "r1", "round": 0, "candidate": 1, "attempt": 1}` or another that satisfies ADR-0077).
7. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases; ③ every public function of the new module and of each touched module that changes behaviour is tested; ④ the new module has its own test file; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
8. **No data-plane change**: no member, file, kind of event, value or version of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `spec.json` or any other data-plane file is added or changed, and no validator changes. If the work turns out to need one, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
9. **Size**: the non-test change stays within the D4 cap (≤ 300 LOC, ≤ 5 files). If it would not, the executor keeps the tool and its registration in this task and proposes a split in `## Follow-ups`.
10. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
11. **Code mode (A-13)**: a Draft PR whose title contains `T-0385`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0385`, and the branch `claude/T-0385-coder-run-tool` deleted.
12. No `claude` process is started, no container is started, and nothing runtime-only is required (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/`: no ADR, register row, proposal section or scenario note. The "less exact, not edited" sentences of ADR-0141 Consequences are not edited, except the `hilclaw/coder_call.py` and `default_registry` docstrings of AC 4 and AC 5.
- Slice 2: any change of `hilclaw/turn_loop.py` (the turn session's environment) and its tests.
- Slice 3: `orchestration/agents/coder-driver.md`, the `hilclaw/turn_permissions.py` docstring, and the tools tests in `tests/test_turn_definition.py` and `tests/test_turn_permissions.py`.
- Slice 4: `orchestration/round-manager.md` and its test.
- Slice (d): the real runtime, any container image, flag, sign-in, prompt or permission mode of the coder's `claude -p` (HQ-0053); any change of `coder_call.call`'s behaviour, of the MCP front's protocol behaviour (no progress notifications), of `hilclaw/scratch.py` or `hilclaw/bring_in.py`, or of the files of open PR #186.

## Follow-ups

- Next for the planner: ADR-0141 Consequences slice 2 (the three environment changes in `hilclaw/turn_loop.py`), then slice 3 (`orchestration/agents/coder-driver.md`), then slice 4 (the Round-Manager's step 2).

## Result
