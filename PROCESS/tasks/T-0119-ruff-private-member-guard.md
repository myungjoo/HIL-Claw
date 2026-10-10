---
id: T-0119
title: Let the ruff gate report an access to a private name of another object or module inside `hilclaw/` (rule `SLF001`), so that the rule "no module of `hilclaw/` uses a private name of a sibling module" of T-0089 is held by CI and not by a `git grep` at review time; no change of behaviour
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: ["#9", "CLAUDE.md language policy (Python gate: pytest + ruff)", "T-0089 follow-up"]
dependsOn: [T-0089]
touchesFiles: [pyproject.toml, hilclaw/backends.py]
estimatedSize: {loc: 20, files: 2}   # a `[tool.ruff.lint]` table of a few lines; at most five lines of hilclaw/backends.py
hq: []   # no owner-only decision and no OD: a lint rule for a convention two reviewed tasks already follow; see the guarded exit in `## Why`
---
## Why
`hilclaw/hw_tool.py` once called two private names of sibling modules (`journaled_tool._built`, `backends._hw_tool`). T-0064 accepted that as a provisional choice with a follow-up; T-0089 (PR #71) gave both a public name, so that no module of `hilclaw/` uses a private name of another. T-0089 checked the rule with `git grep` in its verification only, and its `## Result` says: "A regression would therefore not be caught by CI (reviewer Nit, accepted as the stated choice)", with the follow-up "(planner) Whether the rule "no private name of a sibling module" gets an automatic guard (a lint rule or a CI step)". T-0098 carried it on ("judge against DRIVER §9 first") with a probe. It was never planned. **This task does it**, before the next HW tool builders (the rest of PLAN P1-1, waiting on HQ-0005) add modules that build on `hw_tool`.

Facts at planning time (`main` at `c14df60`, ruff 0.16.10 as pinned in `pyproject.toml`; verify each at execution time, the files win):
- `pyproject.toml` has `[tool.ruff]` with `target-version = "py311"` only, so ruff's default rule set applies. CI runs `python -m ruff check .` and `python -m ruff format --check .` (`.github/workflows/ci.yml`, lines 40-43), on pull requests and on pushes to `main`.
- `python -m ruff check --select SLF001 hilclaw tests` reports 14 findings: 5 in `hilclaw/backends.py` (lines 124, 125, 126: `backend._name` in `BackendTable.__init__`; line 162: `table._backends` and line 168: `backend._operations` in `select`) and 9 in `tests/` (`tests/test_events.py`, `tests/test_mock_backend.py`, `tests/test_standin_profile.py`). No other module of `hilclaw/` is reported.
- The five of `backends.py` are accesses inside the module that defines the two classes and their attributes; T-0089 listed them as "not findings". The nine of `tests/` are tests reaching for a private constant or class of the module they test, on purpose.
- The package already carries `# noqa: BLE001` twice (`hilclaw/merge_guard.py`).

It ticks **no PLAN checkbox**. It is upkeep of the Python gate of #9 / PLAN P0-3, in the manner of T-0113 to T-0115.

Planner's judgements (2026-10-10, **the reviewer is asked to re-check each**):
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0088, T-0106, T-0107, T-0116 and T-0117 are BLOCKED on HQ-0005 to HQ-0009, all unanswered on #5. No PLAN slice is executable without one of those answers (journal 2026-10-10); the shared once-only write helper stays deferred until 2026-10-16. This follow-up is the one planner-tagged item of the task files that waits on nothing.
- **The weakest point, weigh it first - whether widening the rule set of the gate is this task's to do.** No document states which ruff rules the gate selects: T-0002 left ruff at its defaults, CLAUDE.md and #9 say "pytest + ruff". DRIVER §9 lists the owner-only items and a lint rule is none of them; it is not a Requirements OD either, so no ADR is in scope. The repository owner's HQ-0002 answer made version pins "deliberate tasks"; this task changes no pin. **If a reviewer reads the choice of lint rules as the repository owner's, or the rule as one the code should not be held to, do not argue it out: land nothing and return BLOCKED ("requirement unclear") with that reading as the question.**
- **Second weak point - the guard is partial.** `SLF001` reports an attribute access (`module._name`, `obj._name`); it does not report `from hilclaw.x import _name`. The rule that would (`PLC2701`) is a preview rule at planning time; turning preview on changes the whole gate and is not this task. The limit is stated in `## Result` and the commit body, not papered over.
- **A-13 reading**: code mode (`pyproject.toml`, a file under `hilclaw/`). No new dependency, no data-plane schema, no workflow edit.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers, test rules D12) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph
- CLAUDE.md - whole file; in particular "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙" (rule 5: no test for CI or tooling configuration)
- `pyproject.toml` (whole file) and `.github/workflows/ci.yml` lines 25-46 (how the gate installs and calls ruff; read only)
- `hilclaw/backends.py` lines 60-174 (`Backend`, `BackendTable`, `select`) and `tests/test_backends.py` (read only: what it fixes about `Backend.name`, subclasses and `__slots__`)
- PROCESS/tasks/T-0089-public-names-shared-checks.md: `## Why` and, in `## Result`, the review part and the `git grep` bullet; PROCESS/tasks/T-0098-adr-instance-record-op-signature.md line 129
- `hilclaw/merge_guard.py` lines 199 and 253 (the form of a `noqa` already in the package)
- .claude/skills/dev-item-address/SKILL.md and .claude/skills/dev-code-review/SKILL.md

## Acceptance Criteria
### `pyproject.toml`
- ruff's default rules stay selected and `SLF001` is added to them (for example `[tool.ruff.lint]` with `extend-select = ["SLF001"]`; not `select`, which would drop the defaults). No other rule is added, no preview mode, no change of `target-version`, of a pin, of a dependency or of the pytest table.
- The rule does not apply under `tests/` (for example `[tool.ruff.lint.per-file-ignores]` with `"tests/**" = ["SLF001"]`). No test file is edited.
- No other setting of the rule (`ignore-names` and the like) unless a finding at execution time needs it; if so, say which and why in `## Result`.

### `hilclaw/backends.py` - the five findings, with no change of behaviour
- Each of the five accesses ends up either unchanged with a `# noqa: SLF001` at the end of its line, or replaced by an expression that is equal for every object the code can meet there. The choice per line is yours; state it and the reason in `## Result`. Constraints:
  - Replacing `backend._name` by the public `backend.name` is allowed **only** if you show that the two cannot differ at that place (`isinstance(backend, Backend)` admits a subclass, and a subclass may override the property - check what `tests/test_backends.py` and the docstrings say about subclasses before choosing). If in doubt, keep the access and mark it.
  - No new public name, method or property; no change of a signature, a message, the order of the refusals or a docstring sentence; no file-wide ignore for `hilclaw/backends.py` (it would switch the guard off for the module the next builders extend).
  - A `noqa` carries the rule code and no explanation text (CLAUDE.md "코멘트 최소화"; the reason goes into the commit body).
- No other file under `hilclaw/` changes. If the rule reports a finding outside `hilclaw/backends.py` and `tests/` at execution time, name it; fix it here only if it is of the same kind (an access inside the defining module), otherwise stop and return BLOCKED ("task needs re-planning") with the list.

### Tests
- **No test is added and none is changed**: the change is lint configuration plus line-end markers (CLAUDE.md test rule 5 and the repository owner's user-level rule on tooling). If a line of `backends.py` is replaced and not marked, the existing cases of `tests/test_backends.py` must already exercise it (happy path, the duplicate-name refusal, `no_backend`, `not_offered`); name the cases in `## Result`. If none does, keep the access and mark it instead of writing a test.

### Verification (list each with its outcome in `## Result`)
- `python -m ruff check .` and `python -m ruff format --check .` pass; `python -m pytest` passes with the same number of tests as on `origin/main`; coverage of `hilclaw/` (the command of `ci.yml`) is not lower than on `origin/main`.
- **The guard bites, shown without committing a file**: pipe a two-line module that imports a `hilclaw` module and reads a private name of it (for example `from hilclaw import tools` / `print(tools._x)`) to `python -m ruff check --stdin-filename hilclaw/_probe.py -` and show that `SLF001` is reported; the same text with `--stdin-filename tests/_probe.py` is not reported. If the first probe reports nothing, the premise of the task is false: stop and return BLOCKED ("requirement unclear").
- **The limit, shown the same way**: `from hilclaw.tools import _x` under `hilclaw/` - report what ruff says (expected: no `SLF001`). Do not add a second mechanism for it.
- `git diff --stat origin/main` lists only files of `touchesFiles`; `git ls-files --eol` shows `i/lf` for them; the non-test lines added and removed.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0119'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0119 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that edits `pyproject.toml` or `hilclaw/backends.py` is BLOCKED ("open PR conflict").
- Code mode (CLAUDE.md A-13): branch `claude/T-0119-ruff-private-member-guard`, Draft PR with `T-0119` in the title and `Task: T-0119` as the last line of the body; the reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`, the weakest point first**; (b) confirm that no behaviour of `hilclaw/backends.py` changed, line by line; (c) run the two probes; (d) confirm that the defaults of ruff are still selected.
- Merge only with the PR checks green: `gh pr merge --squash --body` with the PR body (keeping `Task: T-0119`), then confirm the `push` run on `main` and delete the branch, remote and local in separate commands. Commit and PR text in English; the commit body says why the rule, what it does not catch, and how each of the five lines was handled. Python is the only language touched (configuration and markers); one line on that in `## Result`.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around.
- `## Result`: fill it in after the merge, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any other ruff rule, preview mode, a pin bump, `.github/workflows/ci.yml`, a custom check script, a test that reads the sources.
- A guard for `from ... import _name`; the private accesses of `tests/`.
- Refactoring `Backend` / `BackendTable`, new public names, docstring edits; every other module of `hilclaw/`.
- CLAUDE.md, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, `ARCHITECTURE/`, `README.md`.
- Anything HQ-0005 to HQ-0009 ask; the task files of T-0088, T-0106, T-0107, T-0116 and T-0117.

## Follow-ups
- (planner, when ruff makes the rule stable or a second private import appears) A guard for `from hilclaw.x import _name` (`PLC2701`, preview at planning time).
- (driver / planner) T-0116 `## Required Reading` line 42 says "search the long OD-8 row for `blob`"; since T-0118 that text is in the OD-8 section of `ARCHITECTURE/OpenDecisionProposals.md`. One parenthesis, to be corrected when T-0116 is taken up again.
- (planner - after T-0088 and T-0116 are done or re-planned, document mode) The move of T-0118 for the OD-18 row, then a judgement on the rows of 1,100 to 1,800 characters (T-0118 `## Follow-ups`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).
- (integrator / repository owner) CLAUDE.md "CI 미구축" and "(CI 구축 전: 로컬 테스트)" no longer match `main`; DRIVER §3-3 / §6 do not say whether the planner may create upkeep tasks for ticked PLAN items (journal 2026-10-10, T-0115).
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4. HQ-0009 (T-0117): PLAN P1-5.

## Result
