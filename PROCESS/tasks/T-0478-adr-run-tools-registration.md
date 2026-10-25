---
id: T-0478
title: Record the registration of `sim.run` and `board.run` in the default registry (backend table, source of seeds, predicate "covered", definitions; one more part of OD-18) as a new ADR, and register both tools with the mock entry, with tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12"]
dependsOn: [T-0477]
touchesFiles: [ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, hilclaw/run_definition.py, hilclaw/check_definition.py, hilclaw/tools.py, tests/test_run_definition.py, tests/test_default_registry_schemas.py, tests/test_mcp_front.py, tests/test_tools.py]
estimatedSize: {loc: 330, files: 7}   # tests excluded from the cap; the ADR's lines count (DRIVER §5, D4)
hq: []
---
## Why

PLAN P1-1's completion criterion (D18) needs `sim.run` and `board.run` "registered as tools and called through the MCP front". After T-0477 both tools have a tool function, but `hilclaw.tools.default_registry` holds neither. ADR-0106 Consequences names what is still missing after the tool function: "the binding of a backend table and a source of seeds and the registration in `default_registry`, with the accepted request of each tool for the check of ADR-0077". No record decides that for the run tools. ADR-0070 decided it for `correctness.check` and left this point open: its decision 3 says the default table "offers no operation of a tool the registry does not hold", and "When the default registry holds the mock with those operations is left open by ADR-0066 …, and this record leaves it to the run tools' records". ADR-0068 Consequences says "this record does not judge whether the rest still stops them".

This is a design part of OD-18 that the driver may close (DRIVER §9, D6). It has no owner-only part that is known: the #5 A/B items, C-6, OD-3 and OD-25 are not touched. By D20 ①, the ADR and its first code slice are one task (code mode; the ADR file goes into the PR). The expected content is the run tools' counterpart of ADR-0070: register now, before the `cpu_standin` operation exists; the mock entry of the default table also offers the two run tools with the default scripts of ADR-0066; no `cpu_standin` entry, so a `cpu_standin` run is `no_backend`; the operating system's generator as the source of seeds; the predicate "covered" of ADR-0041 decision 5 (as ADR-0067 decision 3 uses it); the definitions from `hilclaw/run_definition.py` (ADR-0106). The executor must weigh the alternatives in the record, not assume this outcome. If writing it shows an owner-only decision or a data-plane schema change (CLAUDE.md A-13), stop and return BLOCKED with the question.

It depends on T-0477 (the tool function it binds).

## Required Reading

Line numbers are those of `main` at `e375a388`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit), **§5** (lines 86-115: task format, naming, size cap D4/D20, trailers, the test rules D12) and **§8** (the `— posted by driver` footer) and **§9** (lines 150-158: which ODs the driver may close, the owner notice on #5 and the objection window).
- CLAUDE.md, the whole file. Above all: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "테스트 규칙", "브랜치·merge 절차" (code mode), "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.
- **The model record**: ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md, whole (decisions 2 to 5 and the Walk-through are lines 32-87). Its format follows ADR-0001's "Record format" section.
- ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md decisions 2, 4 and 5 and Consequences (lines 34-96, 139-148).
- ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md decisions 2 to 5 (lines 30-75); ADR-0021-od18-correctness-check-split.md decision 3 (the property of a source of seeds); ADR-0064-od13-run-tools-timing-seed.md decision 2; ADR-0067-od18-run-tools-admission-kinds.md decision 3 (lines 45-53); ADR-0066-od18-run-tools-mock-script.md decisions 3 and 6 and Boundaries (lines 44-57, 80-96, 147-158); ADR-0077-od18-schema-function-agreement-check.md decisions 2 and 3 (lines 27-41); ADR-0068-od18-run-tools-operation-tool-failure.md Consequences (lines 166-172); ADR-0108-od18-run-tools-timing-build-compiler-log.md decision 8 (lines 90-98).
- **Where the record is entered**: ARCHITECTURE/Requirements.md, the "행 형식" paragraph (line 84) and the OD-18 row (line 109); ARCHITECTURE/OpenDecisionProposals.md, the "기록 규칙" in its header (line 8) and § OD-18 (from line 293; the 채택분 lines near 330-334); ARCHITECTURE/StandardScenarios.md, the check rules and the first paragraph of § 검사 결과 (from line 168).
- Code (whole): `hilclaw/check_definition.py` (the model of `default_table`/`definition`), `hilclaw/run_definition.py`, the module T-0477 added for the tool function, `hilclaw/mock_run.py`, `hilclaw/mock_backend.py`, `hilclaw/backends.py`, `hilclaw/tools.py` (`default_registry`, lines 182-271), `hilclaw/harness/seed_source.py`, `hilclaw/gemm_contract.py` (`covers`).
- Tests: `tests/test_default_registry_schemas.py` (the `ACCEPTED` table, line 31), `tests/test_mcp_front.py` (the fixed tool set test near line 466), `tests/test_check_definition.py` (the model of the tests).

## Acceptance Criteria

1. **The ADR.** A new `ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md` (use the next free number if 0167 is taken; check `ARCHITECTURE/decisions/` and open branches). In the format of ADR-0070, it decides at least:
   - whether the two tools are registered now, before their `cpu_standin` operation exists, with the alternatives weighed (the three of ADR-0070 decision 2 apply here too) and why the rest of the run tools' contract is complete enough (one line per item, cited);
   - the default table: which entry offers `sim.run` and `board.run`, with which operations and scripts (ADR-0066), whether the check's table and the run tools' are one table, and what a `cpu_standin` run or another `accelerator` is answered;
   - the source of seeds and the predicate "covered";
   - the two definitions (names, schemas and descriptions of ADR-0106) and what both fronts then list.
   Every sentence is marked owner, cited, or the record's own, as ADR-0070 does. Its Consequences list the sentences of earlier records that become less exact (ADR-0070 decision 3 "offers exactly `correctness.check`" among them) without editing those records, give the A-13 reading (no data-plane schema change is expected; if one is found, stop and return BLOCKED), and name the runtime acceptance items (expected: none beyond ADR-0077 decision 6). Its Boundaries keep the `cpu_standin` operation, ⑲ (라), ⑳, the result files, spend axes and `profiler.collect` open.
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md OD-18 row: the "행 형식" paragraph (line 84) — one ADR link added after `**확정분**:`, `**잔여**:` rewritten in place if it changes, no restatement of the ADR, no dated paragraph.
   - OpenDecisionProposals.md § OD-18: its header's "기록 규칙" (line 8) — one `- **채택분** [ADR-NNNN](…) — …` line; a sub-question's status rewritten in place only if this record answers part of it.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사") and update § 검사 결과 as its first paragraph says (a history entry only if a verdict changes).
3. **Code.** `hilclaw/run_definition.py` (or a module you name) gives the two tool definitions bound to the data-root source and to the table, source of seeds and predicate the ADR fixes. As `check_definition` does, building a definition or the registry imports no NumPy and calls no source; the tool function is bound at its first call. `hilclaw.tools.default_registry` registers `sim.run` and `board.run`, and its docstring says so. If the ADR makes one default table for all three HW tools, `check_definition.default_table` is changed or shared accordingly, and its docstring with it.
4. **Tests** (D12):
   - Happy: `default_registry` lists `sim.run` and `board.run`; through `hilclaw.tools.call` and through the MCP front (`tools/list` and `tools/call` as `sim_run`/`board_run`), a call about a run at the mock with a covered op_signature and an objective gives a completed result from the default script, and the same request again gives the stored result.
   - Branch: a run at `cpu_standin` and a run at another `accelerator` are `no_backend` with no line; `correctness.check` still behaves as before through the same registry.
   - Negative: a request with a member no record names is `invalid_request`; a non-callable data-root source is refused; building the registry calls neither the data-root source nor the source of seeds and imports no NumPy (pinned).
   - ADR-0077: `tests/test_default_registry_schemas.py` gains one accepted request per run tool, and the agreement check passes over every tool of the default registry.
   - The fixed tool-set test of `tests/test_mcp_front.py` names the two new tools and cites the new ADR.
5. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate holds.
6. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0478`. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what the new ADR decides, the landed commit, the objection window (7 days from the notice); last line `— posted by driver` (DRIVER §8). Record the comment URL in `## Result`.

## Out of Scope

- The `cpu_standin` operation of either run tool, and a `cpu_standin` entry of the default table.
- `profiler.collect` (HQ-0025 answer: `not_offered` on `cpu_standin`; no contract here), ⑲ (라), ⑳, a size bound of the log, spend axes, the result files (PLAN P1-8).
- `orchestration/` prompts and agent files (the experiment-runner of ADR-0142 is PLAN P2 work).
- Editing earlier ADRs or the less-exact sentences listed in Consequences (D18: wording clean-up).
- Starting `claude`, a compiler or a container (D16).

## Follow-ups

- (later; planner) The `cpu_standin` operation of `sim.run` and `board.run`, and the `cpu_standin` entry of the default table for the three HW tools, which P1-1's completion criterion needs. Before planning it, re-read ADR-0068 decision 8, ADR-0144 decision 7 and ADR-0107/0116/0117 Consequences for what still stops it.

## Result
