---
id: T-0399
title: Write ADR-0145 - how the timings and the memory figure of a first-case cpu_standin timing run are taken inside the container of ADR-0144, and whether they are those of ADR-0009 and ADR-0052 (OD-14 sub-question 1 part (ma), measurement half; no tool answer, kind or data-plane member)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [NFR-4, NFR-3, C-7, FR-10, OD-14, OD-13, OD-18, "#5 A-7"]
dependsOn: [T-0395, T-0396, T-0397, T-0398]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5 (the first end-to-end run, `cpu_standin` x GEMM) needs the same. ADR-0144 put every first-case `cpu_standin` build and process in a new Docker container and named four code slices. Slices (1) to (3) have landed (T-0396 `hilclaw/standin_container.py`, T-0397 `hilclaw/standin_copies.py`, T-0398 `hilclaw/standin_image.py`). Slice (4), the `cpu_standin` operations themselves, waits on three things (ADR-0144 Consequences, line 143): HQ-0021 and HQ-0026 (unanswered, not open to the driver) and **OD-14 sub-question ① (마)** for the memory figure. Only the last is open to the driver.

Why ① (마) blocks slice (4): ADR-0052 decision 4 takes the memory figure from the `rusage` of the wait for the ended timing process. Under ADR-0144 the process the operation waits for is the container client, not the timing process, and the landed unit rule (`hilclaw/harness/memory_ceiling.py`) reads the host's `sys.platform`, which under Docker Desktop is not the container's system. ADR-0144 decision 3 ("The memory figure", line 77) therefore says a code slice must not apply that code unchanged to a container run, and reads condition (a) of ADR-0052 decision 7 as not met for those runs. The owner's answer to HQ-0025 counts the memory figure among what the run tools return on `cpu_standin` (timing samples and memory figure), so slice (4) cannot be specified without an answer. The same part asks whether the timings taken inside a container are those of ADR-0009 (with OD-13 ⑪).

D18 judgement: this is an OD sub-question, not a checklist item, so the planner judged it against the two targets. It is needed for P2-5 (and so for P2-14): without it the run tools' `cpu_standin` operations cannot return the result HQ-0025 describes. OD-14 is not an owner-only OD (DRIVER §6), so under DRIVER §9 a design record closes the part.

**Scope, to keep one record reviewable**: the measurement half of ① (마) for the first case — (i) whether the timing samples taken in the container are those ADR-0009 defines, and (ii) whether a maximum resident set taken there is the figure ADR-0052 defines, and if so how it is taken (or, if the record finds no sound way, that a container run yields no figure, with what that means for ADR-0052 decision 5 "not judged" and decision 7). The other half of ① (마), **which machine the `cpu_standin` hw key values describe** (ADR-0035, ADR-0036, with OD-4), stays open and is named in Boundaries; the record does not change any hw key value.

Planner's judgements (from `main` `17106fc`; **the reviewer is asked to re-check each**):

- **No open HQ is crossed.** HQ-0021 (T-0210, kinds where the run tools have no timing executable) and HQ-0026 (T-0243, the compiler's log) are not touched: the record adds no situation, answer or kind of any tool. HQ-0034 (OpenMP, owner-only) is not decided: the record must neither require nor forbid OpenMP. HQ-0014 (runtime acceptance of ADR-0052's host facts) and HQ-0059 (ADR-0144's items (xlviii)-(lii)) are non-blocking runtime acceptance items; the record may add new numbered items (see criterion 9) but must not treat those as confirmed.
- **No data-plane schema change.** No member, file, kind, value or version of the data plane is added or changed and no validator changes. `memory_bytes` (ADR-0063 decision 6) keeps its form; what the record may say is whether and how a container run gives it. If the record cannot be coherent without a new member (for example a mark that a figure was taken in a container, or an image identity), leave it open, or return BLOCKED (A-13 data-plane schema change).
- **No new external dependency.** A means that needs a library, a package in the image beyond what ADR-0144 decision 5 already requires (clang and a POSIX C library), or a container-runtime feature the user must install is a new dependency (CLAUDE.md A-13): name it as an alternative with its cost, do not adopt it; if the record cannot be coherent without one, return BLOCKED (`new-external-dependency`) with the question. A program written in the package's own allowed languages (CLAUDE.md language policy: Python, POSIX sh, C) and copied into the build directory like the harness program (ADR-0144 Q3) is not a new dependency.
- **Forgery.** ADR-0052 decision 5 makes the comparison on the Python side, outside the kernel's process, and the anti-forgery principle of OD-16 (unforgeability, not hiding) applies: any means by which the figure crosses from inside the container must be weighed against a kernel that writes the same bytes to its own standard output or standard error (ADR-0144 decision 3 "The exit status" makes the same point for the client's words). State what the chosen means does and does not protect; do not claim more than the sources show.
- **Docker Desktop is a VM.** ADR-0103 decision 4 (the class ground: a timing run executed inside a virtual machine) is "not yet active" until a record produces its input (ADR-0103 Limit 1; OD-13 ⑪ (가) remainder, "with OD-14 sub-question ①"). The record says whether its answer to (i) produces that input; if producing it needs a data-plane member or a reading of the machine that ADR-0103 does not already define, name it open instead.
- **Unlanded drafts are not records.** Branch `claude/T-0375-adr-first-case-coder-process-start` (draft ADR-0137) and `claude/T-0264-adr-od18-local-run-parameter` are not accepted: do not cite them as sources and do not take their numbers.
- **No open PR overlaps**: PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files. Unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*` and `claude/T-0375-*` touch nearby register rows; none has an open PR, so edit only the cells and sub-question text this record needs.

All work is documents and documentation reading. No container runtime, compiler, `claude` process or timing run is started on this machine (D16). Every fact about Docker, cgroups or an operating system comes from official documentation, quoted with its URL and the date read, as ADR-0144 Context does; what documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2 h 30 min limit); §5 (task format; naming: branch `claude/T-0399-<slug>`, trailer `Task: T-0399`; D4 size cap); §3 "BLOCKED 사유"; §8; §9 (closing an OD part by ADR; the #5 notice with the driver footer; the 7-day objection window).
- `CLAUDE.md` (repository), "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), "도구 계층 언어 정책", "브랜치·merge 절차" (document mode, BLOCKED reasons).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format" (the ADR format).
- **`ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md`**: Status and Context (lines 3-40); decisions 1 to 3 (lines 45-79, in particular decision 3 "The exit status", "The memory figure", "Standard error"); decisions 5 to 7 (lines 86-116); Consequences (lines 141-148, the slices and items (xlviii)-(lii)); Boundaries (lines 149-161, in particular the ① (마) bullet). This is the record the new one builds on; read only.
- **`ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md`**: decisions 2 to 7 (lines 29-89); Consequences and Boundaries (lines 109-124). Read only.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`: decisions 2, 3, 8 and 10 (lines 28-43, 74-93, 111-117). Read only.
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decision 6 (from line 87, the member `memory_bytes`). Read only.
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`: decisions 2 and 4 (lines 31-36, 49-57) and Limits (lines 80-87). Read only.
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md` decision 2 (lines 34-39) and `ADR-0036-od4-cpu-standin-host-os-macos-version.md` Status (lines 3-11). Read only; needed to name the hw-key half of ① (마) as open.
- Code, module docstrings only (observations, nothing bound): `hilclaw/standin_container.py` (lines 1-40; it hands on no resource usage), `hilclaw/harness/memory_ceiling.py` (lines 1-60), `hilclaw/harness/timing.py` (lines 1-80), `hilclaw/local_run.py` (module docstring).
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84); NFR-3, NFR-4; register rows OD-4, OD-13, OD-14 (lines 95, 104, 105).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header "기록 규칙" (line 8); § OD-13 (lines 201-222, in particular sub-questions ⑩ and ⑪); § OD-14 (lines 223-235, in particular "채택분" and sub-question ①).
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and § 검사 결과 (from line 168).
- Issue #5: every comment after the ADR-0144 §9 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6314771249), via `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`. If the owner has objected to ADR-0144 or ADR-0052, or has said anything about measuring inside the container, do not start: return BLOCKED (`requirement-unclear`) and quote the comment.
- Session entry check (CLAUDE.md): `gh pr list`, issues #4, #7 and #8 for anything on measurement in a container, and the unresolved `humanQuestions` of `PROCESS/STATE.json`.

## Acceptance Criteria

### The record

1. One new record `ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md` in the ADR-0001 "Record format". Its Status states: which part of OD-14 ① (마) it answers (the measurement half, for the runs of ADR-0144 decision 1) and that the hw-key half is not answered; that OD-14 and OD-13 keep their status words; that no data-plane member, file, kind, value or version is added and no validator changes; that nothing was started for it (D16); which sentences of earlier records it replaces for those runs, quoted without editing those records (as ADR-0144 Status line 10 does); the #5 notice and the 7-day objection window. Every sentence is cited or marked as the record's own.
2. **(i) Timings**: the record says whether the timing samples a timing process reports inside the container are those ADR-0009 defines (same driver, same report, same judgement of `hilclaw.harness.timing`), on a Linux host and under Docker Desktop, grounded in cited documentation; what differs, if anything (the clock source, the VM), and how that relates to ADR-0103 decision 4 and to the owner decision of 2026-10-15 item 3 (OD-13 section). It does not change the timing run of ADR-0009.
3. **(ii) Memory figure**: the record decides, for those runs, either a way the maximum resident set of the timing process is taken and handed to the Python side, or that a container run yields no figure. Either way it states: whether the result is the figure ADR-0052 decision 3 defines; which unit rule applies (the host's `sys.platform` or the container's system) and why; what a kernel inside the container can do to the figure and what the means protects; and how condition (a) of ADR-0052 decision 7 and ADR-0063 decision 6 (`memory_bytes`) read for these runs after this record. At least two means are weighed under "Alternatives considered", each with its cost (for example a wait-and-report program of the harness run inside the container, a figure the container runtime reports for the container, a report by the timing driver itself, no figure). A means that is a new external dependency or needs a data-plane member is not adopted (see Why).
4. **Named as open** in Boundaries, each with the sub-question it belongs to: which machine the `cpu_standin` hw key values describe and `host.os` on macOS (① (마) rest; OD-4; ADR-0035, ADR-0036); the input of ADR-0103's class ground unless criterion 2 produces it without a new member (OD-13 ⑪ (가)); the rest of ① (나) and ① (라), and ① (바); what each tool answers where no figure, container runtime or image can be had, and any kind (OD-18 ⑱/⑲; HQ-0021 and HQ-0026 not crossed); OpenMP (HQ-0034).
5. **Consequences** lists: the code slice(s) the decision implies for the planner, bound to nothing when they land and testable with a stub container runtime (D16), and how they fit ADR-0144 slice (4); the runtime acceptance items (facts only a container runtime on a machine of C-7 can show, numbered from (liii) onward); and the sentences of earlier records that become less exact (not edited). It names no module or signature beyond what the decisions need.

### Register edits

6. `ARCHITECTURE/Requirements.md`: edit the OD-14 row, and the OD-13 row only if the record answers part of an OD-13 sub-question, by the rule in that file's "행 형식" paragraph (line 84).
7. `ARCHITECTURE/OpenDecisionProposals.md`: edit § OD-14, and § OD-13 only if the record answers part of an OD-13 sub-question (⑩'s sentence on ① (마), ⑪ (가)), by the header's "기록 규칙" (line 8).
8. `ARCHITECTURE/StandardScenarios.md`: re-inspect coverage by its rules (CLAUDE.md "문서 커버리지 재검사") and record the result as the first paragraph of § 검사 결과 prescribes.

### Process

9. Document mode (A-13): branch `claude/T-0399-<slug>`, context-isolated reviewer cycle of dev-item-address steps 10-12, rebase on `origin/main`, direct push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0399`. After landing, post the §9 notice on #5 with the driver footer. List any runtime acceptance items the record adds in `## Result` with their numbers, so the driver records them as one HQ with reason `runtime-acceptance` (DRIVER §8).
10. `git diff --stat origin/main` lists only the touchesFiles (Requirements/OpenDecisionProposals/StandardScenarios only where criteria 6-8 require); `git diff --check` is clean. No code, test, PLAN or STATE file is changed. No `claude`, container runtime, compiler or timing run is started (D16).

## Out of Scope

- Any code: ADR-0144 slice (4), changes to `hilclaw/standin_container.py`, `hilclaw/local_run.py`, `hilclaw/harness/*`, `hilclaw/tools.py` or the registry.
- The hw-key half of ① (마) (ADR-0035, ADR-0036, OD-4), beyond naming it open.
- Admitting `memory_ceiling` (ADR-0050 check 4, ADR-0052 decision 7) or deciding OD-13 ⑩'s result-file member.
- Kinds and answers of the run tools in any new situation (HQ-0021, HQ-0026, OD-18 ⑱/⑲).
- Editing ADR-0009, ADR-0052, ADR-0063, ADR-0103, ADR-0144 or any other accepted record.
- Any item in the PLAN "보류" section.

## Follow-ups

- After this lands: the code slice(s) its Consequences names (planner, code mode, stub container runtime only — D16), if any can be made before HQ-0021 and HQ-0026 are answered.

## Result
