---
id: T-0346
title: Write ADR-0126 — which actor of a first-case turn session issues a coder call, by what means, and how the coder process is pointed at its spec copy (part of OD-23, PLAN P2-2; for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-5, FR-10, NFR-4, NFR-6, C-7, OD-23, OD-8, OD-18, S0, S1]
dependsOn: [T-0121, T-0155, T-0171, T-0341, T-0345]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round 0) and P2-2 (coder-driver) are the first unchecked items of the P2 order (D18). This task is a slice of both, so the D18 priority rule for non-checklist work does not apply. The P2-5 run needs it. Round 0 is "bring-up": code generated for the hardware (FR-1). That takes a coder call, and `orchestration/round-manager.md` "The round steps" can only be written once it is known how a turn session gets one.

What exists today:

- ADR-0049 fixes the isolation means of one coder call: a container, one scratch per call, the spec copied in, the output brought back. Its slices (a) to (c) are code: `hilclaw/scratch.py` and `hilclaw/bring_in.py`, both "Nothing calls them yet". Slice (d), the container, waits for PLAN P2-2.
- ADR-0055 fixes the form of `output/`.
- ADR-0124 gives the Round-Manager typed registry tools for its own run's files.

Every one of these records leaves the following open, in the same words: the agent roster, which agent or tool holds the `coder/` role, and "whether `coder.run` exists" (ADR-0010, ADR-0049 and ADR-0055 Boundaries; OD-23 "제안으로 남는 부분"). How the coder process is pointed at the copy is also open: "PLAN P2-2" (ADR-0049 decision 4; the `hilclaw/scratch.py` docstring).

This record closes those points for the first case. They are design-level OD-23 points, so under DRIVER §9 the task writes the ADR. Two owner facts bound it:

- **C-7 ③** (owner, #5 B-6): "메인 오케스트레이터는 Claude Code 세션이고, sub-agent를 띄우며, sub-agent가 `claude -p`를 호출한다". The record must not decide against it.
- **#5 A-8** (owner-only, open): the coder's model, and whether the token budget sums the orchestrator and the coder. The record must decide neither, and must not decide either by default.

So the record does not cover how the coder process itself is started: the image, the container runtime's flags, the `claude -p` flags and model, the permission mode, how the sign-in reaches inside, and the rest of the coder prompt. Those stay open, and the record says which of them wait on A-8.

No open HQ covers this point. HQ-0013 to HQ-0039 were checked. HQ-0013 and HQ-0017 are runtime-acceptance notices for ADR-0049 and ADR-0055; HQ-0032 is about the start function.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", the three-layer model, "개발 드라이버와 런타임의 구분" (D16), and the document-mode branch/merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format".
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`, whole file. It is the closest model for the record's shape and for how a registry tool is specified. Do not copy its wording.
- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`: decisions 1 to 4, the Walk-through, the Consequences bullet "Slices for the planner", and Boundaries.
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: decision 5 (the bring-in and the place) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`, decisions 2 and 6 (the spec file of a tuple and its writer, the coder-call role).
- `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md`: the decision that one spec is one coder call, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`, decision 4 (roles, `coder/`, "The coder process (`claude -p`) holds no role").
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`, decisions 1, 3, 5 and 6. `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`, decisions 2 to 4 and 7.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`, decisions 2, 5 and 6 (one round per turn; where the definition and its `agents/` live; how the session gets the MCP server).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: the decision headings, and the bullets that name #5 A-8. Read them for what journaling a call would add.
- `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` and `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md`, decision headings only. Read them for what counts as a data-plane change.
- `ARCHITECTURE/Requirements.md`:
  - the register's "행 형식" paragraph (around line 84);
  - the rows FR-1, FR-5, NFR-4, NFR-5, C-7, OD-8, OD-14, OD-18 and OD-23.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - § OD-23, whole;
  - § OD-8: candidate ① items 4 and 5 (in-process agents behind a path check, privileged actions through typed tools; per-agent allowlists), and sub-question ㉝.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과, the "최근 재검사" line, and the S0 and S1 rows of the judgement table.
- Code, as observation only:
  - module docstrings of `hilclaw/scratch.py`, `hilclaw/bring_in.py`, `hilclaw/run_file_tools.py` and `hilclaw/turn_definition.py` (`LAYOUT`);
  - `hilclaw/tools.py`: `default_registry`, the name rule and the reserved failure kinds;
  - `orchestration/round-manager.md`, whole.
- GitHub:
  - #5 body items A-8 and B-6, and the owner's B-6 answer (the source of C-7);
  - #4 body §3a and §6, and the comment that proposes the five-agent roster (find it by "coder-driver").

## Acceptance Criteria

### Before editing

1. Run the session entry check of CLAUDE.md: `gh pr list`, and issues #4, #5, #7 and #8. PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files. If any open PR edits a file of `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).
2. Search for owner sentences on the point, as ADR-0124 Status did. Search #4 body and comments, #5 comments without the "posted by driver" marker, #7 and #8. Use terms such as coder-driver, 코더, coder, `claude -p`, sub-agent, subagent, Task, 로스터, roster, coder.run, scratch and container.
   - Record in Status what was searched and every owner sentence found that touches the point. Read each one for what it says and no further.
   - **If an owner sentence decides a point, cite it and do not decide against it.**
   - **If the design you reach needs an owner-only decision, stop and return BLOCKED with the question (DRIVER §9).** That includes the coder's model or a token axis (#5 A-8), or a reading of C-7 ③ that its words do not carry.

### The record `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`

3. Use the format of ADR-0001 "Record format". Status states:
   - accepted under DRIVER §9 (D6), not confirmed by the owner;
   - the OD points it answers (part of OD-23; any part of OD-8 or OD-18 only if it really answers one), and that the OD statuses are unchanged;
   - the records it builds on, with "if one of them is reverted, this record is revisited with it";
   - that it is a record and not code, and that no `claude` was started (D16).
4. **Scope.** One coder call of the first case (ADR-0049 decision 1) that the turn session of a run of ADR-0120 decision 1 needs: round 0's bring-up call first, and any later call of the same kind. Say what is outside, at least:
   - the composition and the writing of that call's `spec.json` (OD-6 rest; ADR-0029's writer, unless decision 6 below assigns it);
   - N > 1 and parallel calls (OD-29);
   - repair calls and calls that do not end normally (OD-19; OD-23 sub-question ①);
   - every other backend (#5 B-1).
5. **Decide the issuer**, consistent with C-7 ③. Weigh at least these in an Alternatives table:
   - (a) a sub-agent of the turn session (for example a coder-driver) requests one layer-2 operation that performs the call;
   - (b) the Round-Manager requests that operation itself;
   - (c) a sub-agent starts the container and `claude -p` itself through the Bash tool;
   - (d) the layer-2 turn loop performs the call between turn sessions.

   Use columns you find relevant. They must include:
   - fit with C-7 ③'s words — state any reading as a reading;
   - what a hook can see (ADR-0010 decision 6);
   - what a per-agent allowlist can express (OD-8 candidate ① item 5);
   - whether P2 of ADR-0049 then rests on a model writing container flags (L2);
   - NFR-6 (method A);
   - one round per turn (ADR-0118 decision 2).
6. **Decide the means**, as far as the chosen issuer needs:
   - Whether the call (scratch, copy, container, bring-in and removal, in ADR-0049's order) is performed by one deterministic layer-2 function.
   - Whether that function is a tool of the registry. This answers "whether `coder.run` exists".
   - Which actor or tool holds the `coder/` role of ADR-0004 decision 4.

   If a tool is added, give it, as ADR-0124 decision 3 did for its four tools:
   - its name, under `hilclaw/tools.py`'s name rule and ADR-0010's MCP naming;
   - its request members. `run_id` is one. The tuple of the attempt whose `spec.json` it uses is another. The data root never is (ADR-0015 decision 3).
   - its result members, and the failure kinds it uses, reusing the reserved kinds where they fit;
   - the existing functions it builds on (`scratch.create`, `bring_in.bring_in`, `scratch.remove`) and the slice it still lacks (ADR-0049 slice (d)).

   **Decide whether the call is a journaled step only if no new event kind, payload or spend axis is needed** (ADR-0011, ADR-0098, ADR-0100). Otherwise leave it open as a boundary and say why: a token axis is #5 A-8.
7. **Decide how the coder process is pointed at its spec copy**: for example, the scratch is its working directory and the coder prompt names `scratch.SPEC_COPY_NAME` there; or another way you weigh. Decide only the pointing. Do not write the rest of the coder prompt, and choose no `claude -p` flag. If the pointing itself needs a flag or a model choice, stop and return BLOCKED. ADR-0055 has the coder "told the place" (`output/` in the scratch), so keep that consistent.
8. **If a sub-agent is chosen**, say where its definition lives under ADR-0118 decision 5 (for example `orchestration/agents/<name>.md`, copied as `.claude/agents/`). Say what the definition carries: the run id and the tuple, from the Round-Manager. Do not write the definition.
9. **Add no member, file, kind or value of the data plane, no version, and change no validator.** A new tool failure kind is a tool-layer name, not a data-plane change; if you add one, say so. If the decision turns out to need a data-plane schema change or a new external dependency (for example, adopting an image), stop and return BLOCKED (CLAUDE.md A-13).
10. **Walk-through.** Cover at least these cases:
    - a round-0 turn that reaches its bring-up call;
    - a call whose container runtime is missing (ADR-0049 "Without the boundary there is no call"; sub-question ㉝ (가) stays open);
    - a call whose coder writes nothing admitted;
    - a call that dies mid-way (OD-19 stays open);
    - an issuer that names another run's id (nothing stops it, ADR-0123 decision 4).
11. **Consequences:**
    - The code slices it enables (code mode, later tasks, stub `claude` and a stub container runtime only — D16). Name the modules, the registry entry and the definition section each would touch.
    - **The parts of the coder-process start that stay open, each with its owner.** Mark which wait on the owner's #5 A-8 (model; token budget) and so need an HQ before their slice is planned. The others are design points left to a later record: image, container flags, sign-in, permission mode, rest of the prompt, time limit (OD-14).
    - A "Less exact, not edited" list. Build it from a search of `ARCHITECTURE/decisions/` and `hilclaw/` for the "whether `coder.run` exists" / "Nothing calls them yet" / "PLAN P2-2" sentences, and say that it is not claimed complete.
    - The UsageCases and StandardScenarios sentences that become false, or "none".
    - The A-13 reading: document mode, no data-plane change.
    - New runtime acceptance items, if any, numbered after the existing series as ADR-0125's Consequences describe them. Examples: whether a sub-agent of a `-p` turn session can request the tool without a permission prompt, and how long a call takes against the session's own limits. They are only listed. Nothing is required of the development machine.
12. **Boundaries**, at least:
    - the rest of the roster and the other agents (selection, evaluator, promoter);
    - allowlists and hooks (rest of OD-18, PLAN P2-4);
    - everything in item 11's open list;
    - `spec.json` composition (OD-6);
    - the end-of-round write and the spend-view fold (OD-23);
    - the commit step (OD-8 ⑪);
    - gates (OD-3, owner-only);
    - any edit to `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, settings or the `HIL-Claw-data` repository.
13. Keep it a decision record, not an essay. Each sentence is either cited with its source or the record's own, and readings are marked as readings. Aim at about 150 to 200 lines.

### The registers

Each file states its own recording rule. Apply that rule as written, not the wording of earlier task files.

14. `ARCHITECTURE/Requirements.md`: follow the register's "행 형식". In the OD-23 row, put one link to ADR-0126 with a few words of topic after `**확정분**:`. Rewrite in place the part of `**잔여**:` it narrows. Touch the OD-8 or OD-18 row only if the record answers part of it. Keep the status words. Do not restate the record and add no dated paragraph.
15. `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙".
    - Add one `**채택분**` line for ADR-0126 under § OD-23, and under any other section whose point it answers.
    - Rewrite in place the open parts it narrows in § OD-23's "제안으로 남는 부분": the roster, the `coder/` role, the existence of `coder.run`, and "코더를 띄우고 그 자리를 알리는 방법". Keep in that same place, as open, what it leaves.
    - Do not restate the record and add no dated note.
16. `ARCHITECTURE/StandardScenarios.md`: recheck coverage under the file's rules (CLAUDE.md "문서 커버리지 재검사"). Update the "최근 재검사" line in place, as the first paragraph of § 검사 결과 says. Add to "판정 변화 이력" or change a judgement-table note only when that paragraph calls for it.

### Mode, review and notice

17. Document mode (A-13):
    - Work on branch `claude/T-0346-adr-coder-call-issuer`, and put the trailer `Task: T-0346` on the commit.
    - Run the context-isolated reviewer cycle (dev-code-review, at most 7 rounds).
    - Then rebase on `origin/main` and push to main without a PR, with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)`.
    - Never run `git push --force*`.
18. In `## Result`:
    - Write the owner notice for #5 that the driver posts (DRIVER §9; §8 footer `— posted by driver`).
    - If the record lists new runtime acceptance items, also write a one-paragraph HQ text (reason `runtime-acceptance`) for the driver to record.
    - If the record names points that wait on #5 A-8, write them as one suggested owner question for the driver. Do not post it.
    - Do not post on GitHub yourself.

## Out of Scope

- Any code: `hilclaw/`, `orchestration/` (including any new agent definition), tests, CI, `pyproject.toml`, `.claude/`, settings. The tool, the container slice (d) and the definition steps are later tasks.
- The start of the coder process itself: image, container flags, `claude -p` flags, model, permission mode, sign-in, the rest of the coder prompt. The coder's model and token budget are owner-only (#5 A-8).
- Composing or writing the round-0 `spec.json` (OD-6 rest), unless the record only assigns its writer (decision 6).
- Repair calls, calls that do not end normally, a second bring-in (OD-19, OD-23 ①), N > 1 (OD-29), time limits (OD-14), a missing container runtime (OD-8 ㉝ (가)).
- Hooks, allowlists, access control (OD-18, P2-4); the end-of-round write and the spend-view fold; the commit step (OD-8 ⑪).
- Editing earlier ADRs: the less-exact sentences are listed, not edited. The wording follow-ups held in the PLAN 보류 section.
- Any data-plane schema or validator change, any new external dependency.
- Starting a real `claude` or a container, or requiring a logged-in `claude`, a container runtime, a board or an API key of this machine (D16).

## Follow-ups

- The code slice of ADR-0126's tool or operation (stub `claude` and a stub container runtime only), and the definition steps that use it.
- If the record names #5 A-8 points, the driver records that HQ before the coder-process start slice is planned.
- Alternatively next: an ADR on OD-8 sub-question ⑪ (which step commits a round, and how a fresh turn learns that a commit is owed).

## Result
