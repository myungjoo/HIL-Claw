---
id: T-0395
title: Write ADR-0144 - the container in which the cpu_standin builds and processes of a first-case run are carried out (OD-14 sub-question 1, parts (ga) and (da), with the frame of (ra) and the requirements on the image; no tool answer, kind or data-plane member)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [NFR-4, C-7, FR-9, FR-10, OD-14, OD-18, OD-16, "#5 A-7"]
dependsOn: [T-0156, T-0325, T-0327]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P1-1 is open, and its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin` (not only on the mock) and to be registered. P2-5 (the first end-to-end run, `cpu_standin` × GEMM) needs the same. This is checklist work (P1-1), so the D18 rule for work outside the checklist does not apply.

Today the `cpu_standin` operations of those three tools do not exist. The default registry's `correctness.check` table holds the mock alone (`hilclaw/tools.py` `default_registry` docstring; ADR-0070 decision 3), and `sim.run`/`board.run` are not registered (ADR-0142 Context). Those operations wait on three things (journal 2026-10-19): HQ-0021 (T-0210, ADR-0068, unanswered), HQ-0026 (T-0243, the compiler's log, unanswered) and **OD-14 sub-question ①, the build and run container**. Only the third is open to the driver: the owner decided on 2026-10-15 (items 1 and 2, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913) that the toolchain and the kernel's build, correctness run and timing run use a container, and that toolchain and environment changes (for a container, its image) happen only after the user's permission. The OpenDecisionProposals § OD-14 integrator note says that the records describing these builds and processes as unprotected host processes (ADR-0009 decision 10, ADR-0017 decision 10, ADR-0052, ADR-0056, ADR-0049 L3 and L6) and the code (`local_run`, `clang_build`) are not yet replaced, and that a record replacing them is needed once ① is answered. OD-14 is not an owner-only OD (DRIVER §6: #5 A/B items, C-6, OD-25, OD-3), so under DRIVER §9 a design record comes first. **This task writes that record**, for the first case only.

To keep one record reviewable, its scope is OD-14 ① (가) (which of ADR-0049's P1 to P4 apply, network, resource limits) and (다) (a new container per build or process, per call, or reused), with the frame of (라) that the first case needs (which runtime first, as ADR-0049 "Docker first" did) and the requirements an image must meet and how the runtime is told which image to use (the part of (나) a code slice cannot do without). Everything else stays open and is named (Acceptance Criteria 4).

Planner's judgements (from `main` `21bf655`; **the reviewer is asked to re-check each**):

- **No open HQ is crossed.** HQ-0053 (T-0375, the sign-in of the coder's `claude -p` in its container) does not bind this record: no `claude` runs in a build or run container. HQ-0021 (T-0210: the kinds of the situations where `sim.run`/`board.run` have no timing executable) and HQ-0026 (T-0243: the compiler's log) are not touched: this record adds **no situation, answer or kind** of any tool; what a call answers when no container runtime or no image is there is named as open (Acceptance Criteria 4). HQ-0034 (OpenMP on `cpu_standin`, owner-only) is not decided: the image requirements must not require or forbid OpenMP.
- **Unlanded drafts are not records.** Branch `claude/T-0375-adr-first-case-coder-process-start` holds a draft ADR-0137 on the coder's container (image named by the user, never pulled). It is not accepted: do not cite it as a source, do not take its number, and do not decide for it. Whether the build and run container uses the coder call's image stays open (OD-14 ① (나); ADR-0049 L6). Where this record makes a choice that draft also makes, it makes it on its own cited grounds.
- **One possible BLOCKED point: the image.** Adopting a concrete base image, registry, Dockerfile or package is a new external dependency of the runtime (CLAUDE.md A-13). The record may state what the image must hold and how the runtime is told which one to use, but must not adopt a concrete one. If the executor finds the record cannot be coherent without adopting one, return BLOCKED (`new-external-dependency`) with the question instead.
- **No data-plane schema change.** No member, file, kind, value or version of the data plane is added or changed, and no validator changes. If the record needs one (for example to record the image identity, OD-14 ① (나) "이미지 식별을 빌드 설정과 함께 기록하는지", or a change to the `cpu_standin` hw key values, ① (마)), leave it open instead, or return BLOCKED (A-13 data-plane schema change).
- **No open PR overlaps**: PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files. Unlanded branches `claude/T-0210-*`, `claude/T-0264-*`, `claude/T-0361-*` and `claude/T-0375-*` touch nearby rows and sections of the registers; none has an open PR, so this is no conflict, but edit only the cells, bullets and sub-question text this record needs.

All work is documents and documentation reading. No container runtime, compiler, `claude` process or timing run is started on this machine for it (D16). Every fact about Docker (or another runtime) comes from its official documentation, quoted with its URL and the date read, as ADR-0049 Context does; what documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2 h 30 min limit); §5 (task format; naming: branch `claude/T-0395-<slug>`, trailer `Task: T-0395`; D4 size cap); §3 "BLOCKED 사유"; §8; §9 (OD closing by ADR; the #5 notice with the driver footer; the 7-day objection window).
- `CLAUDE.md` (repository), "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), "브랜치·merge 절차" (document mode, BLOCKED reasons), "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format" (the ADR format).
- **`ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`**: Context O1-O4 and D1-D5 (lines 12-31); decisions 2 to 5 (lines 41-107: P1-P4, "Without the boundary there is no call", "Docker first", G1, L1-L11, in particular L3, L6, L7, L11); Consequences and Boundaries (lines 142-169).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decisions 2 to 4 (lines 37-94: the build directory, its place outside both checkouts, its removal, the working directory) and decision 5's table (lines 95-114). Read only.
- `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`: decisions 2 to 5 (lines 32-75; the same settings in both builds). Read only.
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`: decisions 2 and 5 (lines 32-46, 67-76; the one source of settings and the inherited environment). Read only.
- `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md`: decisions 2 to 4 and 6 (lines 31-63, 70-76; what a time limit covers, the rest of the hierarchy). Read only.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 2 and 10 (lines 28-35, 111-117); `ADR-0017-od16-cpu-standin-verification-run.md` decisions 2 and 10 (lines 30-37, 101-108); `ADR-0052-od13-memory-ceiling-measurement.md` decisions 2 and 4 (lines 29-43, 52-63). These are the host-process statements the record replaces in part; read only, do not edit them.
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md` decisions 2 and 3 (lines 34-54; which machine the hw key values describe). Read only; needed to name ① (마) as open.
- `ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md` Status (line 9, how a record states which sentences of earlier records it replaces without editing them). Read only.
- `hilclaw/clang_build.py` and `hilclaw/local_run.py`, module docstrings only (how the builds and processes are run today). Read only.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84); NFR-4 (line 47); C-7 (line 64); register rows OD-13, OD-14, OD-18 (lines 104, 105, 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header "기록 규칙" (line 8); § OD-14 (lines 223-233), in particular the owner decision of 2026-10-15, the integrator note, "채택분" and sub-question ①; § OD-8 sub-question ㉝ (line 154). 
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and the first paragraph of § 검사 결과 (from line 168).
- Issue #5: every comment after the ADR-0117 §9 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6259729110), via `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`. If the owner has objected to ADR-0049 or ADR-0117, or has said anything about the build or run container, its image, or running builds on the host, do not start: return BLOCKED (`requirement-unclear`) and quote the comment.
- Session entry check (CLAUDE.md): `gh pr list`, issues #4, #7 and #8 for anything on the build or run container, and the unresolved `humanQuestions` of `PROCESS/STATE.json`.

## Acceptance Criteria

### Files

1. One new record `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` in the format of ADR-0001 "Record format" (Status, Context, Decision with numbered decisions and a Walk-through, Alternatives considered, Consequences, Boundaries, References). Its Status says which part of OD-14 it answers, that OD-14 keeps its status word, that no data-plane member, file, kind, value or version is added and no validator changes, that it is a record and not code (nothing was started for it, D16), which sentences of ADR-0009, ADR-0017, ADR-0049 (L3, L6), ADR-0052 and ADR-0056 it replaces (quoted, in the manner of ADR-0070 Status, without editing those records), the #5 notice and the 7-day objection window. Every sentence is either cited (a source named with it) or marked as the record's own, as recent records do.

### Decisions the record must make (for the first case only: runs of ADR-0076 decision 1 on a local `cpu_standin`)

2. **Scope**: the four local processes of the `cpu_standin` operations — the verification build and the verification process of `correctness.check` (ADR-0056), the timing build and the timing process of `sim.run` and `board.run` (ADR-0009, ADR-0107) — and nothing else (not the coder call, not a real board, not the mock).
3. Using the owner decision of 2026-10-15 items 1 and 2, ADR-0049 O1-O4 and official documentation:
   - **(가)** which of P1 to P4 hold for these processes and in what form: what runs inside (the compiler, the executable); what of the host is given to the container and whether writable (the build directory of ADR-0056 decision 4 and the kernel's compiled set, the harness sources); what crosses and how (mount or copy, P3); what is removed and when (P4, with the build directory's removal of ADR-0056); whether the network is reachable from inside; and whether any processor, memory or disk bound is set (if none, say so and keep the rest of OD-14 open, as ADR-0049 L7 does).
   - **(다)** whether one container serves one build or process, one call, or is reused across calls, with reasons that cite ADR-0056 (built at each call), ADR-0107 (same settings in both builds) and ADR-0117 (whether its time limits cover the container's start; if the record cannot settle this, name it open).
   - **The frame of (라)** the first case needs: which container runtime is used first and why (cite ADR-0049 "Docker first" and O1-O3), and whether a build or process is ever run on the host when no container runtime is available (a fallback). State the reading of the owner decision that grounds the answer.
   - **The image, as far as a code slice needs it**: what the image must hold for these processes (by function, not by product or version), that no concrete image is adopted, how the runtime is told which image to use, and whether the runtime pulls, builds or updates an image (the owner decision item 2: only after the user's permission). If this cannot be written without adopting a concrete image, stop and return BLOCKED (see Why).
4. **Named as open** in Boundaries (each with the sub-question it belongs to), not decided: whether the image is the coder call's (① (나)); whether and where the image identity is recorded (① (나), NFR-2; no data-plane member); daemon rights, rootless or Podman, and the runtime on macOS and WSL beyond the first choice (① (라); OD-8 ㉝ (라)); whether timings and the maximum resident set taken inside a container are those of ADR-0009 and ADR-0052, and which machine the `cpu_standin` hw key values describe (① (마); OD-13 ⑪; OD-4); a real board (① (바)); what each tool answers when no container runtime or no image is available, and any kind for it (OD-18 ⑱/⑲; HQ-0021 and HQ-0026 not crossed); OpenMP (HQ-0034); the settings of ADR-0116 that the image may affect.
5. **Consequences** lists the code slices for the planner, each bound to nothing when it lands, and the runtime acceptance items (facts that only a container runtime on a machine of C-7 can show — for example that the build directory is the only writable host path, that the network is unreachable, that the measured process behaves as on the host). It does not name a module or decide a signature beyond what the decisions need.

### Register edits, by the recording rules written in those files

6. `ARCHITECTURE/Requirements.md`: the OD-14 row follows the "행 형식" paragraph (line 84): one link to ADR-0144 added to the confirmed parts, and the open part (`잔여`) rewritten in place so that what ADR-0144 answers is no longer listed as open. The status word stays. No other row is edited unless the "행 형식" rule requires it; if one is, list it in `## Result` with the reason.
7. `ARCHITECTURE/OpenDecisionProposals.md`: § OD-14 follows the header's "기록 규칙" (line 8): one link to ADR-0144 under "채택분", and sub-question ① and the integrator note rewritten in place to say which parts are answered and what stays open. No restatement of the record, no dated paragraph. No other section is edited.
8. `ARCHITECTURE/StandardScenarios.md`: re-inspect coverage by its rules (CLAUDE.md "문서 커버리지 재검사") and update § 검사 결과 by its first paragraph: the "최근 재검사" line rewritten in place; a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed.

### Process

9. Document mode (A-13): branch `claude/T-0395-<slug>`, context-isolated reviewer cycle of dev-item-address steps 10-12, rebase on `origin/main`, direct push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0395`. The §9 notice is posted on #5 after landing, with the driver footer.
10. If the record adds runtime acceptance items, list them in `## Result` with their numbers so the driver records them as one HQ with reason `runtime-acceptance` (DRIVER §8).
11. `git diff --stat origin/main` lists only the touchesFiles; `git diff --check` is clean. No code, test, PLAN or STATE file is changed. No `claude`, container runtime, compiler or timing run is started (D16).

## Out of Scope

- Any code: the container seam, the `cpu_standin` operations, `hilclaw/clang_build.py`, `hilclaw/local_run.py`, `hilclaw/tools.py`, the registry.
- The coder call's container, sign-in and image (ADR-0049, T-0375, HQ-0053).
- The kinds and answers of `sim.run`, `board.run` and `correctness.check` in any new situation (HQ-0021, HQ-0026, OD-18 ⑱/⑲).
- Editing ADR-0009, ADR-0017, ADR-0049, ADR-0052, ADR-0056 or any other accepted record; the "Less exact, not edited" style lists are written in this record's Consequences, not fixed elsewhere.
- Any item in the PLAN "보류" section.

## Follow-ups

- After this lands: the first code slice its Consequences names (planner, code mode, stub container runtime only — D16).

## Result
