---
id: T-0325
title: Record an ADR on where the `cpu_standin` backend's own flags, trailing flags and environment come from and what their values are, for the first case (OD-18 sub-questions 18 (ra) and 19 (ra), source and values; OD-16 sub-question 6 and OD-6 sub-question 2 where they meet)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, FR-9, OD-18, OD-16, OD-6, C-7, "#5 A-7"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P1-1 is open. Its completion criterion (D18) says that `sim.run`, `board.run` and `correctness.check` must work on `cpu_standin` and on the mock. P2-5, the near goal, is a run on `cpu_standin` × GEMM. Today no operation of `cpu_standin` exists for any of the three tools. `hilclaw.check_definition.default_table` holds the mock alone (ADR-0070 decision 3), and a run whose hw_profile names `cpu_standin` is answered `no_backend`.

The records name the stops in front of that operation:
- ADR-0060 decision 3 makes every build and run setting "the backend's own" and leaves "the source and the values" open:
  - flags, trailing flags and environment (thread settings among them) under OD-18 sub-question ⑱ (라);
  - the compiler under OD-14 ①;
  - the two time limits under OD-14.
- Its Consequences say: "Not yet possible: the operation of `cpu_standin` for this tool … It lacks every setting value — flags and environment (⑱ (라)), the two time limits (OD-14) …".
- ADR-0107 decision 3 requires the verification build and the timing build of an attempt to use the same compiler, flags, trailing flags and environment. Its decision 4 says the operations of both tools take them "from one source". Both leave the source and the values open (⑲ (라), "the source and values").

This task closes the flags, trailing flags and environment part with an ADR. OD-18 is a design-level OD, so the §9 path applies: an ADR, reviewer Approve, and the owner notice. This is a PLAN checklist item inside the P1-1 completion criterion and on the path to P2-5, so the D18 priority rule does not set it aside.

The task deliberately does not cover:
- the compiler installation and version, and the container (OD-14 ①, owner decision of 2026-10-15);
- the two time limits and their hierarchy (OD-14);
- ⑱ (가), settings prescribed in `task.build` or chosen by the coder.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0325` trailer, size cap;
  - §9 (lines 142-149): OD closure by ADR and owner notice.
- `CLAUDE.md`: these rules:
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "문서 커버리지 재검사";
  - "개발 드라이버와 런타임의 구분";
  - "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- The record format: `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`, whole file (137 lines). This is the closest earlier record. Read decisions 3 and 4 (lines 41-66), Limits (88-93) and Boundaries (117-130) closely.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`:
  - decision 2 (lines 38-45);
  - decision 3 and its settings table (lines 46-68);
  - Consequences (154-161);
  - Boundaries (162-176), with the text of ⑱ (가) to (마).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decision 4 (lines 73-94).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: decisions 9 and 10 (lines 86-108).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`: decisions 9 and 10 (lines 94-120).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`:
  - line 15, the #5 A-7 ② and C-7 inputs;
  - lines 97 and 104: threads allowed, how many is a build or run setting; `<omp.h>` and SIMD headers allowed.
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md`: decisions 2 to 4 (lines 34-83), which machine the hw key describes and `toolchain`.
- `ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md`: decision 2 (lines 33-41).
- `ARCHITECTURE/Requirements.md`:
  - the "행 형식" paragraph (line 84);
  - C-7 (line 64);
  - the OD-6, OD-14, OD-16 and OD-18 rows (lines 97, 105, 107, 109).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the "기록 규칙" (line 8);
  - OD-6 (lines 59-76), sub-question ②;
  - OD-14 (lines 216-226), the owner decision of 2026-10-15 and sub-question ①;
  - OD-16 (lines 235-256), sub-question ⑥;
  - OD-18 (lines 267-344), especially ⑱ (line 340) and ⑲ (line 341).
- `ARCHITECTURE/StandardScenarios.md`: the check rules near the top (line 26), and the first paragraph of §검사 결과 (from line 168).
- Code, docstrings only, to see what a setting is in the code:
  - `hilclaw/clang_build.py`, `build` (from line 196);
  - `hilclaw/local_run.py`, `run` (lines 79-184);
  - `hilclaw/harness/verification_build.py`;
  - `hilclaw/harness/timing_build.py`.

## Acceptance Criteria

1. **Session entry check.** Run `gh pr list` and read #4, #5, #7 and #8 for anything on build flags, OpenMP, thread count or the environment of a kernel's build or run. Draft PR #186 (T-0324) touches only `hilclaw/` and `tests/`. If any open PR edits the OD-6, OD-14, OD-16 or OD-18 row or section, stop and report it. Quote every owner sentence found, with its link. Say in Result which threads were searched.
2. **Record number.** Write a new record `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md` in the format ADR-0107 uses. ADR-0068, 0074, 0088 and 0112 sit on unlanded branches. On 2026-10-19 the highest number on `origin/main` and on any remote branch was ADR-0115. Check again with `git ls-tree` over `origin/main` and every remote branch. If 0116 is taken, take the next free number and rename the file and the touchesFiles entry. Say so in Result.
3. **Scope.** The scope is the runs of ADR-0107 decision 1: the first case, on `cpu_standin`. The mock is out of scope: it is given no setting (ADR-0060 decision 3). The record answers two questions:
   - **(i) The source.** Where the backend's own flags, trailing flags and environment come from. It must be one source for the operations of both `correctness.check` and the run tools, as ADR-0107 decision 4 requires. Weigh at least these alternatives:
     - (a) fixed values in the package source, changed only by a commit, like the fixed tool set of `hilclaw.tools.default_registry`;
     - (b) a configuration file such as `hilclaw.config.json` (PLAN P1-7), or an environment variable;
     - (c) derived from the hw_profile the operation is handed. ADR-0060 decision 3 says no operation reads a setting from the hw_profile. So (c) would reopen that decision and must be weighed as such.
     For each alternative, state what it does to:
     - NFR-7 ③ (which source commit made a result);
     - C-7 (Linux, macOS and WSL behave alike);
     - Limit 3 of ADR-0107 (a change between two calls);
     - the owner's rule that the toolchain and the environment change only after the user's approval (O4 item 2).
   - **(ii) The values.** The values of the flags (at least the language standard, the optimisation level, OpenMP, and whether target-specific code such as `-march=native` is allowed), of the trailing flags, and of the environment. For the environment, decide whether it is inherited from the calling process or fixed, and which thread setting it carries (for example `OMP_NUM_THREADS`), with its value or the rule for it.
4. **The values must not invent.** Ground each value in a cited sentence (#5 A-7 ② via ADR-0008, ADR-0008 lines 97 and 104, C-7, ADR-0107) or in a stated reason. Check every value on all three systems of C-7. In particular, state what each flag needs from the compiler installation on macOS: OpenMP with Apple's clang needs a separately installed runtime.
   - **A value that needs an external dependency**, or a toolchain install or update on any C-7 system: do not choose it. Leave it open as a part of ⑱ (라). If no workable set of values remains without it, stop with BLOCKED (new external dependency).
   - **A value that needs the owner's reading of #5 A-7**: stop with BLOCKED (owner-only decision) and give the driver one question with options. One example is whether OpenMP must be usable by every kernel on every C-7 system. Do not record the value.
   - **The container.** The values must hold whether the build runs on the host, as the records still say, or in the container of the owner decision of 2026-10-15. If a value only makes sense inside one of them, leave it open and name OD-14 ①.
5. **What the record does not decide.** The compiler installation and version (OD-14 ①); the two time limits and their hierarchy (OD-14); settings that reach an operation from a file of the run or the attempt (⑱ (가)), including `task.build` (OD-6 ②); the container design (⑱ (다)); ⑲ (나); ⑱ (마); any record of a build's settings (⑰ (다), `build.json`). Boundaries list all of these. They also list any change to earlier records, `hilclaw/`, tests, CI, `.claude/`, settings files and `HIL-Claw-data`.
6. **No schema change and no code change.** The record adds no member, file, kind, `step` value, blob `type`, spend axis or reserved kind to the data plane. It changes no code. Consequences carries an A-13 reading that says so, backed by a name check over `hilclaw/`, `tests/` and `ARCHITECTURE/`. If the decision cannot be written without such a change, stop with BLOCKED (data-plane schema change).
7. **Consequences.**
   - Name the code slice the record makes possible: the one source of settings that both operations read. State what that slice still waits on: the time limits (OD-14), HQ-0021 (T-0210, ⑲ (나)) for the run tools' tool function, and HQ-0026 (T-0243, ADR-0078) for the compiler's log. Bind no module or function name.
   - List the sentences of earlier records that become less exact, found by grep. Include at least the "open" cells of the ADR-0060 decision 3 table and the "values stay open" sentences of ADR-0107. Do not edit them.
   - Name the runtime acceptance items (D16) or say there are none. One candidate: that each chosen flag is accepted by the clang of each C-7 system. No item may be closed by starting `claude` or by requiring a board or an API key.
8. **Status.** State that the record was accepted under DRIVER §9 and not yet confirmed by the owner. State the records it builds on: at least ADR-0008, ADR-0009, ADR-0017, ADR-0056, ADR-0060 and ADR-0107. Say that it is revisited if one of them is reverted. Keep cited sentences apart from the record's own choices.
9. **`ARCHITECTURE/Requirements.md`.** The "행 형식" paragraph at line 84 governs every edit.
   - Edit the OD-18 row.
   - Edit the OD-16 row only if the record answers part of sub-question ⑥ beyond what ADR-0107 answered. Edit the OD-6 row only if it answers part of sub-question ②.
   - Leave every other row alone.
   - Keep the number of rows unchanged.
10. **`ARCHITECTURE/OpenDecisionProposals.md`.** The header's "기록 규칙" at line 8 governs every edit.
    - Edit only the sections whose register row criterion 9 touched.
    - In OD-18, update the ⑱ and ⑲ bullets in place: the head status word, and the status tail of (라) in each.
11. **`ARCHITECTURE/StandardScenarios.md`.** Re-check coverage under CLAUDE.md "문서 커버리지 재검사", using the document's own rules. Change §검사 결과 only as its first paragraph says.
12. **Hygiene.**
    - `git diff --stat origin/main` lists only the touchesFiles.
    - `git diff --check` is clean.
    - Every relative link added resolves.
    - No `claude` program is started, and no board, accelerator or API key is required (D16).
    - The landed commit has the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and the `Task: T-0325` trailer, each on its own line after a blank line.

## Out of Scope

- Any code. That includes:
  - the operation of `cpu_standin` for `correctness.check` or the run tools;
  - the run tools' tool function and their registration;
  - any change to `hilclaw/clang_build.py`, `hilclaw/local_run.py` or `hilclaw/harness/`.
- The compiler installation and version, the container, and the time limits (OD-14).
- `profiler.collect` (HQ-0025).
- The ADR-0115 round-7 wording findings and the `standin_profile.py` docstring sentence. Both are held under D18.
- Editing earlier ADRs, `UsageCases.md`, `PROCESS/`, `.claude/` or any settings file.

## Follow-ups

- If the record fixes the source and the values: a code task for the one source of settings that the `cpu_standin` operations read. It would be the first piece of the `cpu_standin` operation of `correctness.check`, which then still waits on the time limits (OD-14) and on HQ-0026.
- If the time limits turn out to be the next stop: an ADR on the two time limits for the first case (OD-14, hierarchy part).

## Result
