---
id: T-0375
title: Write ADR-0137 - how the container and the coder's `claude -p` of a first-case coder call are started (the design points of ADR-0049 slice (d) left by ADR-0126 Consequences, except the time limit and the output stream)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-5, NFR-4, NFR-5, C-7, OD-23, OD-8, OD-14, "#5 A-8"]
dependsOn: [T-0346, T-0371, T-0374]
touchesFiles: [ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-2 (the coder-driver) is the next open checklist item in the first group of the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-5 needs it: without a real runtime behind the seam of `hilclaw/coder_call.py`, no coder call of the first run can happen on a runtime machine.

State of P2-2 on `main` `20a533e`:

- `hilclaw/coder_call.call` performs the whole call (ADR-0126 decision 3) and reads `coder_model` from the run's `instance.json` (ADR-0136, slices 1 to 3: T-0372, T-0373, T-0374). The container and the coder process stand behind a seam: `runtime.available()` and `runtime.run(scratch_root, coder_model=...)`, which returns the coder's exit status or raises `CoderNotStartedError`. Only test stubs implement it.
- What remains is **ADR-0049 slice (d)**: the start and removal of the container and the coder process. ADR-0126 Consequences (code slice 3) says it comes "after the owner's #5 A-8 and the design points below". The model part of A-8 is answered (HQ-0041 part (1), recorded by ADR-0136). The token part (HQ-0041 part (2)) is answered by the owner but not yet recorded; it is not needed to start a process and stays out of this task.
- ADR-0126 Consequences, "Design points left to a later record", lists: the image and what provides it; the container runtime's flags realising P1 and P2; how the sign-in reaches inside (ADR-0049 L5); the permission mode of the coder's `claude -p`; the rest of the coder prompt and how it is passed; the time limit of a call (OD-14); the coder's output stream (OD-23 ① (라)). ADR-0136 decision 7 and Boundaries add: how the model value reaches `claude -p`.

These are design-level points of OD-23 (with OD-8 ㉝ and OD-14 ①), so under DRIVER §9 a record is written first (a code task cannot decide them). **This task writes that record**, for the first case only. To keep one record reviewable, it leaves out two points that a first code slice can go without: the time limit (ADR-0049 L7 already states "No ceiling"; OD-14) and the coder's output stream (OD-23 ① (라)). They stay open and are named in Boundaries.

Planner's judgements (from `main` `20a533e`; **the reviewer is asked to re-check each**):

- **Not owner-only as a whole.** None of #5 A/B open items, C-6, OD-25 or OD-3 is decided by the points in scope. Owner facts that bind them are cited, not decided: C-7 ② (Max subscription, no separate API cost), C-7 ③, HQ-0010 answer (O1 to O4 in ADR-0049), the owner decision of 2026-10-15 items 1 and 2 (toolchain and environment changes only after the user's permission; the container is "its image"), and ADR-0054 O3 ("never with a bypass flag" — said of the self-check's throwaway session; whether it binds the coder's `claude -p` is a reading the record must make explicitly and must not stretch).
- **One possible BLOCKED point: the image.** Adopting a concrete base image, registry or package to install in it may be a **new external dependency** (CLAUDE.md A-13) of the runtime. The record may state what the image must hold and how the runtime is told which image to use, but it must not adopt a concrete image, registry or package. If the executor concludes the record cannot be coherent without adopting one, it returns BLOCKED (`new-external-dependency`) with the question, rather than adopting it.
- **Sign-in is security-sensitive.** ADR-0049 L5 and L8 already accept that a coder with a shell can read the sign-in. The record chooses how the sign-in reaches inside under C-7 ② (no API key, no separate API cost) and states plainly what becomes readable inside. If every available means requires something the owner has not permitted (for example a long-lived credential created by the user, or a credential written to a file of the host the container can read), name it in the record as a cost and, where it needs a user permission, apply the owner decision of 2026-10-15 item 2 (ask and stop) as cited; if the executor finds it is a security concern the record cannot settle, return BLOCKED (`security`).
- **No data-plane schema change** is expected: no member, file, kind, value or version of the data plane is added. If the record needs one (for example to record the image identity, OD-14 ① (나) "이미지 식별을 빌드 설정과 함께 기록하는지"), leave it open instead, or return BLOCKED (A-13 data-plane schema change).
- **No open HQ is crossed.** HQ-0040 (Q1 of ADR-0126, the front of the coder call) is about how the coder-driver reaches the function; the start of the process behind the seam is the same under either answer (ADR-0126 Consequences). HQ-0041 part (2) (token axis) is not touched. HQ-0032 (PR #186) is not touched.
- **No overlap with open PR #186** (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). Unlanded branches `claude/T-0361-*`, `claude/T-0210-*`, `claude/T-0264-*` touch nearby lines of the OD-23 / OD-18 rows and sections; they have no open PR, so this is no conflict, but edit only the cells, bullets and sub-question ends this record needs.

All work is documents and documentation reading. No `claude` is started, no container runtime is used, nothing is tried on this machine (D16). Every fact about `claude` flags, sign-in or Docker comes from official documentation, quoted with its URL and the date read, as ADR-0049 Context and ADR-0054 Context do; what documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2h30m limit); §5 (task format; `T-NNNN` naming: branch `claude/T-0375-<slug>`, trailer `Task: T-0375`; size cap D4); §3 "BLOCKED 사유" paragraph; §8; §9 (OD closing by ADR; the #5 notice with the driver footer; 7-day objection window).
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사"; "미결은 발명하지 않는다"; "세션 진입 점검"; "개발 드라이버와 런타임의 구분"; "브랜치·merge 절차" (document mode; BLOCKED reasons); "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- **`ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`**: Status and Context (lines 3-27); decisions 3, 5 and 7 (sections "### 3." to "### 7.", lines 43-80); Consequences (lines 103-126, in particular "Open parts of the start" and the runtime acceptance items (xii)-(xiv)); Boundaries (lines 128-136).
- **`ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`**: Context O1-O4 and D1-D5 (lines 15-30); decisions 2 to 5 (lines 41-107, in particular P1-P4, L1, L2, L4, L5, L6, L8, L11); Consequences (lines 143-148); Boundaries (lines 150-159, in particular "How the coder process is started" and sub-question ㉝).
- **`ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`**: Context (F1, F2 and "What is open", lines 17-37); decision 7 (lines 106-108); Consequences runtime acceptance items (xxxi), (xxxii); Boundaries (lines 150-157).
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md`: Context (O3, K-facts on `claude -p` flags and `--permission-mode`, lines 13-46) and decision 4 (lines 76-95). Read only; reuse its cited documentation facts where they apply, and re-read the documentation where the coder's case differs.
- `ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md`: the flag values the landed self-check uses. Read only.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: how a turn session's `claude -p` is started and what permission means its item (vii) leaves open. Read only.
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: F6 (a `claude -p` session without `--bare` runs its project's hooks and servers). Read only.
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: what the coder must leave in the scratch for the bring-in. Read only.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84); C-7 (line 64); NFR-4, NFR-5; register rows OD-8, OD-14, OD-23.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header "기록 규칙" (line 8); § OD-8 sub-question ㉝ (around line 151); § OD-14 owner decision of 2026-10-15 and sub-question ① (around lines 227-230); § OD-23 (from line 395), in particular ① (라).
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and the first paragraph of § 검사 결과 (from line 168).
- `hilclaw/coder_call.py`, module docstring and `call` docstring (the seam contract). Read only.
- Issue #5: every comment after the ADR-0136 §9 notice (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`), and the HQ-0041 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368).
  - If the owner has objected to ADR-0049, ADR-0126 or ADR-0136, or has said anything about the image, the sign-in inside the container, or the coder's permission mode, do not start: return BLOCKED ("requirement unclear") and quote the comment.
  - If the owner has answered HQ-0040, name the answer in `## Result` and check that nothing in the record depends on the form; it should not.
- Session entry check (CLAUDE.md): `gh pr list`, and issues #4, #7, #8 for anything on the coder's start, image or sign-in.

## Acceptance Criteria

### Files

- New `ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md` (the slug may change; keep `ADR-0137` and `od23`). Use the next free number if 0137 is taken on `origin/main` when you start.
- Edit `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md` as below. Edit `ARCHITECTURE/StandardScenarios.md` only if the recheck changes a verdict.
- Nothing else changes: no code, test, CI, setting, `.claude/`, `orchestration/`, `PROCESS/` (other than this task file's `## Result`), no earlier ADR. If you conclude another file must change, return BLOCKED with the reason.

### The record

Follow the structure and conventions of ADR-0126 and ADR-0136: Status (accepted under DRIVER §9; whose each part is; builds on which records; the 7-day objection window), Context (owner sentences found by a stated search, with terms and counts; cited documentation facts with URL and date read; facts of the code), Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References. Each sentence is marked or evidently **owner's**, **cited** or **this record's own**.

Scope: one coder call of the first case (ADR-0049 decision 1), behind `runtime.available()` and `runtime.run(scratch_root, coder_model=...)` of `hilclaw/coder_call.py`. Decide, for Docker (ADR-0049 "Docker first"):

1. **What `runtime.available()` checks**, so that `no_container_runtime` means what ADR-0049 decision 2 "Without the boundary there is no call" says. What happens when it is missing beyond that kind stays OD-8 ㉝ (가).
2. **The container's start and removal realising P1, P2 and P4**: the scratch as the one writable host mount and the coder's working directory; no other writable mount; no means to direct the container runtime inside; no added privilege; removal when the call has ended, also when the coder failed or the wait was interrupted. Name the means at the level the cited documentation supports (flags may be named where a cited sentence shows what they do); everything not shown by a cited sentence is marked not verified and becomes a runtime acceptance item (ADR-0049 L1).
3. **The image**: what it must hold for the first case (the Claude Code program, clang and what the coder needs to build and try a C kernel inside — ADR-0049 L6), and how the runtime is told which image to use. **Do not adopt a concrete base image, registry, Dockerfile content or package version** (see Why; A-13). Whether an image is pulled or built on the machine, who updates it, and what P4 does with a built one stay open unless a cited owner sentence decides them (O3 speaks of "pulled images" only; owner decision of 2026-10-15 item 2: changes only after the user's permission).
4. **How the sign-in reaches inside** under C-7 ② (Max subscription; no API key and no separate API cost): the means, what it makes readable inside (ADR-0049 L5, L8), what differs per platform of C-7 ① (for example where each platform keeps the credential), and what is not verified.
5. **The coder's `claude -p` command**: how the prompt is passed (argument or standard input) and the rest of its text beyond ADR-0126 decision 5 (which names `spec.json` and `output` relatively) — or, if the text is better left to the code slice, say exactly which parts are fixed here; how the model of ADR-0136 decision 7 reaches the process (flag, environment variable or other — say which, citing the documentation); the permission mode, with an explicit reading of whether ADR-0054 O3's "never with a bypass flag" binds the coder's session (it was said of the self-check) — do not stretch it either way, and if the honest reading is that it is unclear, choose a mode that respects it and say why; whether `--bare`, `--setting-sources` or the like are used so that no project or user settings, hooks or servers of the host are loaded into the coder's session (ADR-0010 F6), and why.
6. **The exit status** that `runtime.run` returns, and which failures it reports as `CoderNotStartedError` (the container or the process could not be started) versus an exit status, consistent with ADR-0126 decision 3 and item (xiv).

State in Consequences:

- **Code slices for the planner** (code mode; tested with stub `docker`/`claude` executables only, D16): the module(s) implementing the seam, and what each slice contains; that `coder_call.call` keeps its contract. Keep the first slice within the D4 cap if possible.
- **Runtime acceptance items**, numbered after the last one in the turn-session series (ADR-0136 used (xxxi), (xxxii); check `origin/main` for any later number), one per fact only a real Docker and a logged-in `claude` on a machine of C-7 can show (for example: the sign-in works inside; the model flag is honoured; the session in the container loads no host settings; P2 holds with the named means).
- **A-13 reading**: document mode; no code, dependency, image, setting or data-plane schema change; nothing required of the development machine.
- **"Less exact, not edited"**: sentences of earlier records (ADR-0049 Boundaries "How the coder process is started", ADR-0126 "Open parts of the start" and Boundaries, ADR-0136 decision 7 and Boundaries, `hilclaw/coder_call.py` docstring "slice (d)'s") that this record narrows; list them, edit none.
- **The cost, plainly** (as ADR-0049 and ADR-0126 do).

Boundaries must name at least: the time limit of a call (OD-14); the coder's output stream (OD-23 ① (라)); the token record and which usage counts (HQ-0041 part (2)); the model that actually ran (ADR-0136 Boundaries); the front (HQ-0040); Podman and the runtime on Windows with WSL (OD-8 ㉝ (라)), unless decided with cited support; leftovers of a dead process (㉝ (나)); whether a checkout is shown inside (㉝ (다)); the isolation of the measured build and run (OD-14 ①).

Do not invent: every value or flag the record adopts is either cited from documentation with what it does, or marked as this record's provisional choice with its reason, and nothing about an owner's preference is assumed.

### The registers (recording rules — follow the rules written in those files, not earlier task files)

- `ARCHITECTURE/Requirements.md`: follow the "행 형식" paragraph (line 84). In the OD-23 row (and in the OD-8 or OD-14 row only if this record answers part of their sub-questions): add **one link** to the new ADR with a few words of its subject under `**확정분**:`, and rewrite `**잔여**:` in place. Do not restate the record, and add no dated paragraph. Change the status cell only if the rule there requires it.
- `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). Add one `- **채택분** [ADR-0137](…) — <what it covers> (답함: …)` line in § OD-23 (and in § OD-8 / § OD-14 only where it answers part of a sub-question). Where a sub-question (for example OD-8 ㉝, OD-14 ① (나), OD-23 ① parts) is partly or fully answered, rewrite the end-of-question status (`→ 부분 답: … 남음: …` / `→ 답함: …`) and the bullet-head status word in place; keep the question's wording. If the record raises a new sub-question, register it with its wording only.
- `ARCHITECTURE/StandardScenarios.md`: recheck coverage with its inspection rules (CLAUDE.md "문서 커버리지 재검사"); per the first paragraph of § 검사 결과, add to the history only if a verdict changes, otherwise record nothing there and say so in `## Result`.

### Process

- Document mode (CLAUDE.md A-13): branch `claude/T-0375-<slug>`; context-isolated reviewer cycle (dev-item-address steps 10-12, at most 7 rounds) to Approve; rebase on `origin/main`; push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0375`. No force push.
- After landing, post the §9 notice on #5 (English; first line `### ADR-0137 accepted under DRIVER §9 — T-0375: <summary>`, naming the landed commit, the 7-day window, and the new runtime acceptance items; last line `— posted by driver`), as earlier ADR tasks did. Put the comment URL in `## Result`.
- If the record adds runtime acceptance items, say so in `## Result` so that the driver raises the HQ with reason `runtime-acceptance` (DRIVER §8).
- No `claude` and no container runtime is started at any point (D16).

## Out of Scope

- Any code: the seam's implementation (the next slice), `hilclaw/coder_call.py`, tests.
- The time limit of a call and the coder's output stream (later records).
- The token record (HQ-0041 part (2)), `ARCHITECTURE/SpendAxes.md`.
- Either front of the coder call (HQ-0040), `orchestration/`, the coder-driver definition.
- The isolation of the measured build and run (OD-14 ①, other than citing it), the build and run tools.
- Adopting a concrete image, registry or package (A-13; see Why).
- Editing any earlier ADR or any less-exact sentence (list them; D18 hold).

## Follow-ups

- Planner's view of what follows: the code slice(s) the record names for the seam's real runtime (P2-2), tested with stub executables only; then the time limit and the output stream records if P2-5 needs them.
- A runtime acceptance HQ for the record's new items (driver, DRIVER §8).
- If the image needs an owner decision (A-13 new external dependency), the HQ the executor names in `## Result`.

## Result
