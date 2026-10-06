---
id: T-0005
title: Update README with the three-layer model, a repository map and development-process pointers
phase: P0
status: IN_PROGRESS
commitMode: doc
coversReq: ["#5 A-12", "#5 A-13"]
dependsOn: []
touchesFiles: [README.md]
estimatedSize: {loc: 70, files: 1}
hq: []   # no owner-only decision and no OD closure: every fact to be written is already confirmed in CLAUDE.md / ARCHITECTURE / PROCESS
---
## Why
`README.md` is still the owner's original objectives note (34 lines: Objectives, "Agent 실행 시 참고 사항", References, License). It says nothing about what the repository now contains or how it is developed: the three-layer model and the tool-layer language policy (#5 A-12), the MVP scope, the design documents under `ARCHITECTURE/`, the development process (`CLAUDE.md`, the two skills, `PROCESS/`), or how to run the local checks. A reader (or a fresh agent session) landing on the README has no pointer to any of these. PLAN P0-5 asks for exactly that: "README 갱신: 세 층 모델·개발 절차 포인터(PROCESS/, CLAUDE.md)".

The README is a pointer page, not a second source of truth: `CLAUDE.md` stays canonical for rules, `ARCHITECTURE/` for design, `PROCESS/` for the development driver. The new text must summarise in a few lines and link, not restate.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, naming and trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md line 3 (the development driver is **not** the runtime orchestrator), §0 (lines 12-18), §2 (lines 33-45: `PROCESS/` layout, document mode), §7 (lines 122-132: roles; `.claude/agents` definitions are planned in P0-6 and do not exist yet)
- CLAUDE.md — whole file (26 lines). In particular line 16 "세 층 모델", line 17 "도구 계층 언어 정책", line 18 "브랜치·merge 절차" (document mode), line 14 "미결은 발명하지 않는다", lines 22-26 "현재 프로젝트 상태 주의사항" (CI not built, no binaries in git, MVP scope)
- README.md — whole file (the text to extend)
- ARCHITECTURE/Requirements.md lines 1-13 (line 3: the README objectives are cited as a requirements source under the tag **README**; §0 scope: MVP "방법 B", three-layer model) and the FR-13 / C-3 rows (data plane in the separate repository `HIL-Claw-data`, CAS for binaries)
- PROCESS/PLAN.md — P0 section (P0-1 calls the package directory "가칭 `hilclaw/`", i.e. a tentative name; P0-3 CI unchecked; P0-6 agent definitions unchecked)
- PROCESS/tasks/T-0003-ci-skeleton.md — frontmatter only: status BLOCKED (HQ-0001), so no CI exists
- PROCESS/tasks/T-0002-python-project-config.md — "Local verification" in Acceptance Criteria and `## Result` (the three local commands; `[dependency-groups]` needs pip >= 25.1 for `pip install --group dev`)
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; line 10 (document mode replaces tests with document checks, skips steps 13-14), steps 9, 10-12, 15
- .claude/skills/dev-code-review/SKILL.md — document-mode return path (verdict + findings returned to the caller) and the "no invented decisions" check
- Existing files to look at, not to change: `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/driver_state.py` (module docstring only), `.editorconfig`, `.gitattributes`, and the directory listings of `ARCHITECTURE/`, `PROCESS/`, `.claude/`, `tests/`

## Acceptance Criteria
Nothing in the repository fixes the README's section names, section order, level of detail or language. None of these is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below and state each choice with one line of reason in the commit body and in `## Result`. Do not present them as requirements.

Language (provisional, chosen by the planner):
- Write the new README text in **Korean**, like the existing README body and the `ARCHITECTURE/` and `PROCESS/` design documents (DRIVER §5 last bullet: design documents are Korean; only task files, commits and GitHub comments are English). Identifiers, paths and commands stay as they are. Section headings may be English or Korean; the existing README mixes both — be consistent within the new sections.
- No rule in the repository states the README's language. Do not translate the existing sections and do not write a language policy into the README. The question is recorded in Follow-ups.
- The commit message is English.

Existing content:
- The existing sections — the `# HIL-Claw` title, `## Objectives`, `## Agent 실행 시 참고 사항`, `## References`, `# License` — keep their wording **unchanged**, including typos, the empty `- ` bullet and blank lines. Reason: `ARCHITECTURE/Requirements.md` cites the README objectives as a requirements source; editing them is a requirements change, not this task. `git diff origin/main -- README.md` must show additions only, except that removing surplus blank lines directly adjacent to an insertion point is acceptable.
- Placement (provisional): insert the new sections between `## Agent 실행 시 참고 사항` and `## References`, as `##` sections. A one- or two-line status note directly under the `# HIL-Claw` title that links down to them is allowed.

New content — each item must be present, short, and linked to its canonical source:
1. **Status and MVP scope** (source: CLAUDE.md lines 22-26, Requirements §0, FR-13, C-3):
   - MVP is "방법 B" (Claude Code Orchestrator), a single compute-kernel optimisation; in Phase 1 a Git directory tree stands in for the database named in Objectives.
   - Run data and artifacts live in a separate repository `HIL-Claw-data` (#5 A-1); binaries and large artifacts are not committed to git (A-2: CAS `blobs/` plus hash references).
   - The repository is at the bootstrap stage: the runtime that performs optimisation runs does not exist yet. Do not list per-item progress (it goes stale); point to `PROCESS/PLAN.md` for the plan and `PROCESS/STATE.json` for the current phase.
2. **Three-layer model** (source: CLAUDE.md line 16-17; keep the definitions equivalent to CLAUDE.md, do not extend them):
   - Layer 1 = Claude Code orchestration in Markdown (CLAUDE.md, skills, `.claude/agents` definitions, technique Skills); layer 2 = deterministic tool package called by layer-1 agents (FR-10 tools, backends, CAS, schema validation, hook entry points, verification harness); layer 3 = C kernels produced by the coder (`claude -p`).
   - The language policy applies to layer 2 only: {Python, POSIX sh, C}; anything else needs an ADR. Link to CLAUDE.md for the rule.
   - Say what exists today per layer, truthfully: layer 1 has `CLAUDE.md` and `.claude/skills/` (two development-process skills); `.claude/agents/` and technique Skills do not exist yet. Layer 2 is the `hilclaw/` Python package — call the name tentative ("가칭", PLAN P0-1) — currently holding only the package version and the `PROCESS/STATE.json` validator, with tests in `tests/`. Layer 3 has nothing in the repository; do not state where kernels will be stored (data-plane layout is OD-8, undecided).
3. **Repository map**: one line each for `ARCHITECTURE/` (with links to `Requirements.md`, `UsageCases.md`, `StandardScenarios.md`, `OpenDecisionProposals.md`), `PROCESS/` (`DRIVER.md`, `PLAN.md`, `STATE.json`, `tasks/`, `journal/`), `.claude/skills/`, `hilclaw/`, `tests/`, `CLAUDE.md`. A list or a small table; no file-by-file inventory beyond this.
4. **Development process pointers** (source: CLAUDE.md lines 3-8 and 18, DRIVER line 3 and §0):
   - `CLAUDE.md` is the canonical rule set for every Claude Code session; changes follow the `dev-item-address` skill and are reviewed with `dev-code-review` (link both `SKILL.md` files).
   - `PROCESS/DRIVER.md` describes the automated development driver (one iteration = one task from `PROCESS/PLAN.md`); state explicitly that it is the process that **builds** HIL-Claw and is distinct from the runtime orchestrator that HIL-Claw will run.
   - One or two sentences on the two change modes (document mode: reviewed, pushed to `main` without a PR; code mode: Draft PR, review cycle, squash-merge), linking to CLAUDE.md for the details. Do not copy the BLOCKED list or the test rules.
   - Where decisions live: Open Decisions in `ARCHITECTURE/Requirements.md`, and GitHub issues #4 (architecture decisions), #5 (owner decisions pending), #7 (external research), #8 (contradiction tracker) as named in CLAUDE.md line 15. Issue links, if any, use the full URL `https://github.com/myungjoo/HIL-Claw/issues/<n>`.
5. **Local checks** (source: `pyproject.toml`, T-0002): Python >= 3.11; install the dev tools with `python -m pip install --group dev` (pip >= 25.1); `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`. State that CI is **not built yet** and that these local runs replace it for now. Run the three commands yourself before writing them down and confirm they exit 0 (do not run the install command if the tools are already present).

Do not invent (CLAUDE.md "미결은 발명하지 않는다"):
- Every statement in the new sections must be traceable to CLAUDE.md, `ARCHITECTURE/`, `PROCESS/` or a file that exists on `main`. Anything not confirmed there is either left out or explicitly marked as undecided / planned.
- In particular, do not: claim that CI, `.claude/agents/`, technique Skills, tool backends, a harness, a CAS implementation, or a runnable optimisation loop exist; present `hilclaw` as a final package name; state a data-plane directory layout, a spec format or a key schema (OD-4/6/8 are open); name a licence (the README says it is to be determined); name specific Claude models; add badges, installation-as-a-package instructions (there is no build backend) or usage examples for the runtime.
- If, while writing, you find that a required item above contradicts CLAUDE.md or `ARCHITECTURE/`, follow those documents, note the discrepancy in `## Result`, and do not edit them in this task. If you cannot write an item without deciding something undecided, return BLOCKED ("요구 불명확·미결 발명 의심") with the exact question.

Size and form:
- Only `README.md` changes. Expected about 50-80 added lines; hard cap 300 changed lines / 5 files (D4). If you find yourself beyond roughly 100 added lines, you are restating canonical documents — cut and link instead.
- UTF-8, LF, final newline, no trailing whitespace on added lines (`.editorconfig`). The Windows working copy may show `README.md` as CRLF; the committed blob must be LF.

Verification (document mode — no tests are added; paste the outcomes into `## Result`):
- Every relative link target in `README.md` exists. From the repository root, for example: `grep -oE '\]\([^)]+\)' README.md | sed -E 's/^\]\(//; s/\)$//; s/#.*$//' | grep -vE '^(https?:|mailto:|$)' | sort -u | while read -r p; do test -e "$p" || echo "MISSING $p"; done` prints nothing. In-page anchors (`#...`), if used, are checked by eye against the headings.
- `git diff origin/main --stat` lists only `README.md`; `git diff origin/main -- README.md` shows no change to the wording of the existing sections.
- `git ls-files --eol README.md` shows `i/lf`.
- `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .` exit 0 (unchanged code; this confirms the commands documented in the README).
- `ARCHITECTURE/` is not touched, so the StandardScenarios coverage re-check (CLAUDE.md "문서 커버리지 재검사") does not apply; say so in the commit body.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Branch `claude/T-0005-readme-three-layer-pointers` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context sub-agent that follows `.claude/skills/dev-code-review/SKILL.md`, give it the branch name (review target = diff against `origin/main`), and receive the verdict and findings as its return value. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED (security).
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase, never onto a `main` that moved since). Before pushing, `git show --stat HEAD` must list exactly `README.md`; if anything else appears, stop and fix. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0005:`; body explains what was added and lists the provisional choices (language, placement, section names) with one line of reason each, and the coverage-re-check note; the message ends with the trailers, in this order:
  `Reviewed-by: reviewer agent (N rounds, Approve)`
  `Task: T-0005`
  followed by any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Then delete the remote and local branch and check out `main` at `origin/main`.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to the task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the provisional choices, the verification outcomes, and follow-ups.
- Do not edit `.claude/settings.json` or `.claude/settings.local.json`. If a needed tool call is denied or fails, return BLOCKED rather than working around it.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Rewording, translating, reordering or fixing typos in the existing README sections (Objectives, "Agent 실행 시 참고 사항", References, License), and choosing a licence.
- Any change to `CLAUDE.md`, `ARCHITECTURE/`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, `pyproject.toml`, or code. `PROCESS/STATE.json` and the PLAN checkbox are driver-owned.
- Other documentation files (`CONTRIBUTING.md`, `docs/`, a `LICENSE` file, an ADR directory), badges, diagrams or images.
- Agent definitions (`.claude/agents/`, P0-6), CI (T-0003 / P0-3), and anything about the runtime design beyond what the linked documents already state.
- Deciding the repository's documentation-language policy.

## Follow-ups
- (owner, non-blocking) README language: this task keeps Korean to match the existing README and design documents. If the owner wants an English README (or a policy line in CLAUDE.md), that is a separate document-mode change.
- (owner) The existing README has an empty `- ` bullet under References, trailing blank lines and typos ("형대", "최적과"); left untouched here because the section is owner-authored and cited by Requirements.
- (after T-0003 / P0-3) Replace the "CI is not built yet" sentence with a pointer to the workflow once CI exists.
- (after P0-6) Mention `.claude/agents/` in the layer-1 line and the repository map once the agent definitions land.
- (later) Revisit the "tentative" marker on `hilclaw/` if the package name is confirmed, and the layer-3 line once OD-8 fixes the data-plane layout.

## Result
