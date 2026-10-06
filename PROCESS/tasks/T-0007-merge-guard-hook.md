---
id: T-0007
title: Add the gh pr merge guard hook script (denies a merge unless the PR checks are green) with its tests
phase: P0.5
status: IN_PROGRESS
commitMode: code
coversReq: ["#5 D10", "#5 D12", OD-18]
dependsOn: [T-0002]
touchesFiles: [hilclaw/merge_guard.py, tests/test_merge_guard.py]
estimatedSize: {loc: 160, files: 1}   # non-test: the guard module; the test file is excluded from the cap (D4)
hq: []   # standard library only; registration in .claude/settings.json is NOT part of this task (owner action, see Out of Scope)
---
## Why
Owner decision D10 (2026-10-05, issue #5; #8 M24) keeps `main` without branch protection: the merge gate is procedural (reviewer approval + green CI, read by the executor) and is to be **reinforced by a driver-side `PreToolUse` hook that intercepts `gh pr merge` and refuses it unless the PR's checks are all successful**, so that the gate is enforced by the harness and not only by agent discipline. PLAN P0.5-4 is that hook. D12 names it as one of the two tool-code exceptions whose tests are **mandatory** ("if either breaks, the autonomous loop fails silently").

This task is the **first slice of P0.5-4**: the guard as a tested, runnable script. Activating it means adding a `hooks` entry to `.claude/settings.json`, which the driver and the executor must never edit (DRIVER §1-5), so registration is left to the owner (Follow-ups). The other P0.5 items (P0.5-1..3) extend `.github/workflows/ci.yml`, which the open PR #16 (T-0003, BLOCKED on HQ-0002) is creating; this slice touches no file of that PR.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode, the forbidden actions held by discipline, "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §11 rows D10, D12, D13
- PROCESS/PLAN.md — P0.5-4 (and P0-3, P0.5-1..3 for what is deliberately not touched)
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성"), "테스트 규칙" ①-⑤ (⑤ names this hook as a mandatory-test exception), "코멘트 최소화", "미결은 발명하지 않는다"; "현재 프로젝트 상태 주의사항: CI 미구축"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow (steps 4, 9, 13, 15; step 15 is the `gh pr merge` call this hook will guard)
- .claude/skills/dev-code-review/SKILL.md — the test-rule and "no invented decisions" checks the reviewer applies
- Issue #5, comments "D10 confirmed (owner, 2026-10-05)" and "D12 confirmed (owner, 2026-10-05)" items 3 and 5, and "D13 recorded in `main`" (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`)
- PROCESS/tasks/T-0004-driver-state-schema.md — `## Result`: the conventions of the sibling driver tool (`hilclaw/driver_state.py`: stdlib only, `main(argv=None) -> int`, `python -m` entry, one test file per module, reachability check with the stdlib `trace` module)
- PROCESS/tasks/T-0003-ci-skeleton.md — front matter and `## Result`: CI is not on `main` (PR #16 open, BLOCKED on HQ-0002), so verification stays local
- Existing files: `pyproject.toml`, `hilclaw/driver_state.py` and `tests/test_driver_state.py` (style reference), `.editorconfig`, `.gitattributes`, `.claude/settings.json` (read only — the allowlist; it has no `hooks` key today)
- Claude Code hooks reference (PreToolUse input and blocking behaviour), if reachable: https://code.claude.com/docs/en/hooks — see "Hook protocol" below for what to do when it is not

## Acceptance Criteria
D10 fixes only this: a `PreToolUse` hook intercepts `gh pr merge` and refuses it unless the PR's checks are all successful. The module location and name, the public API, how a `gh pr merge` call is recognised, the meaning of "all successful" for skipped or absent checks, and the behaviour on errors are **not** fixed anywhere. None of them is an owner-only decision (DRIVER §9) or a registered OD; OD-18 (runtime hook layer) is **not** closed or changed by this task and no ADR is written. They are **conventions chosen by this task, provisional**: follow the criteria below, state each choice with one line of reason in the commit body and in `## Result`, and do not present them as requirements.

Constraints:
- **Standard library only** (`json`, `shlex`, `re`, `subprocess`, `sys`, `argparse` as needed). Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Code must run on CPython 3.11 (`requires-python` floor); it is verified locally on 3.14 only. Say so in `## Result`.
- The guard is **read-only**: the only external command it may run is `gh pr checks ...`. It never merges, comments, edits or pushes.
- **Do not edit `.claude/settings.json` or `.claude/settings.local.json`**, and do not register the hook by any other route (user-level settings, environment, a wrapper). The module is inert until the owner registers it.

Module (new, `hilclaw/merge_guard.py`; provisional location — next to the other driver tool `hilclaw/driver_state.py`, so that it is covered by pytest, ruff and the future coverage gate. Python because it parses JSON and a command line with the stdlib and the rest of the package is Python — one line in the commit body and `## Result`):
- Module docstring and short docstrings on the public functions (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Entry point `python -m hilclaw.merge_guard`, ending with `if __name__ == "__main__": raise SystemExit(main())`.
- Public API (provisional names; the executor may rename or regroup them, but every public function must be tested and `gh` must be replaceable in tests without a real process):
  - `merge_invocations(command: str) -> list[list[str]]` — every `gh pr merge` invocation found in a shell command line, each returned as the argument list to pass to `gh pr checks` (the PR selector if given, plus `--repo <value>` if given). Empty list = the command does not merge a PR.
  - `checks_problem(checks: list[dict]) -> str | None` — `None` if the check list allows a merge, otherwise a one-line reason naming the offending checks.
  - `evaluate(payload: dict, run=subprocess.run) -> str | None` — `None` to let the tool call proceed, otherwise the denial reason. `run` is the injection point for tests.
  - `main(argv=None) -> int` — reads the hook payload (one JSON object) from stdin and returns the exit code.

Hook protocol (as understood by the planner — **verify against the hooks reference above if it is reachable and record in `## Result` whether you could**; if it is not reachable, implement exactly this and list the verification under Follow-ups):
- Input: a JSON object on stdin with, among others, `tool_name`, `tool_input` (for shell tools an object with a string `command`) and `cwd`.
- Let the call proceed: exit code 0 with **nothing on stdout**. Never print a permission decision of "allow": the guard must not grant permissions, it only refuses.
- Refuse: exit code **2** with the reason on stderr (one or a few lines, starting with `merge guard:`). Other non-zero exit codes are non-blocking errors in Claude Code, so every failure of the guard itself that must block uses exit code 2 too.

Behaviour:
- Payload without a string `tool_input.command` (another tool, e.g. an edit) → proceed. Do not filter on `tool_name`: the same check applies to any shell tool the hook is registered for (Bash, PowerShell).
- Command with no `gh pr merge` invocation → proceed, without running `gh`.
- Recognition of `gh pr merge` (provisional): tokenise the command the way a POSIX shell would (`shlex`, with `;`, `&`, `|`, parentheses and newlines treated as separators) and look for a simple command whose command word is `gh` (optionally preceded by `VAR=value` assignments) and whose first two non-flag words are `pr` and `merge`; `gh -R owner/repo pr merge ...` and `gh --repo owner/repo pr merge ...` count. Text inside a quoted argument is one token and must **not** match (a commit message or PR body that mentions `gh pr merge` is not a merge). If the command cannot be tokenised (unbalanced quotes), fall back to a regular-expression search of the raw text and, when it looks like a merge, treat it as a merge whose selector is unknown → refuse (fail closed).
- PR selector: the first positional argument after `merge` (number, URL or branch), skipping flags and the values of the `gh pr merge` flags that take one (`-b/--body`, `-F/--body-file`, `-t/--subject`, `-A/--author-email`, `--match-head-commit`, `-R/--repo`, in both `--flag value` and `--flag=value` forms). No selector → `gh pr checks` without one (current branch, like `gh pr merge` itself).
- For every merge invocation found, run `gh pr checks <selector> [--repo <value>] --json name,bucket` with the payload's `cwd` as working directory (if present) and a timeout (provisional: 60 s). All invocations must pass; the first problem refuses the whole tool call.
- Observed with gh 2.88.1 (planner, 2026-10-06; rely on stdout, not on the exit code): with `--json` the command prints a JSON array of `{name, bucket}` and exits 0 even when checks failed (PR #16 → two entries with `bucket: "fail"`); `bucket` is one of `pass`, `fail`, `pending`, `skipping`, `cancel`; a PR with no checks prints `no checks reported on the '<branch>' branch`, no JSON, exit 1 (PR #15); an unknown PR prints a GraphQL error, exit 1.
- "All successful" (provisional): the list has **at least one** entry with `bucket == "pass"` and every other entry is `pass` or `skipping`. Any `fail`, `pending`, `cancel` or unknown bucket → refuse, naming the checks. Reasons: a skipped job (conditional gates such as a future C gate) is how GitHub itself treats a passing required check, and "no checks at all" must not count as green or the guard would be vacuous exactly when CI is missing or broken. Record the stricter alternative (only `pass`) in `## Result` as not chosen.
- Fail closed, all with exit code 2 and a reason that says what failed: stdin is not a JSON object; `gh` is not found; `gh` times out; stdout is not a JSON array of objects (this includes "no checks reported" and the unknown-PR error — include gh's own message in the reason); any unexpected exception inside the guard.
- `main` takes no positional arguments; `--help` via `argparse` is fine.

Tests (new, `tests/test_merge_guard.py`; mandatory per D12 exception ②; excluded from the size cap). No test may call the real `gh` or the network: use the `run` injection (or `monkeypatch`) with canned `subprocess.CompletedProcess` values and exceptions.
- happy:
  - merge with all checks `pass` → proceed (exit 0, empty stdout), and `gh` was called with `pr checks <selector> --json name,bucket` and the payload `cwd`.
  - `pass` + `skipping` → proceed.
  - non-merge commands → proceed and `gh` is **not** called: `git status`, `gh pr view 16`, `gh pr checks 16`, `gh pr list`, `gh issue view 5`.
  - a payload of a non-shell tool (no `command`) → proceed.
- branch (recognition), each asserting the arguments handed to `gh pr checks`:
  - `gh pr merge 17 --squash --body "x"`; a URL selector; a branch selector; no selector; selector after flags (`gh pr merge --squash 17`); `--body`/`--body-file`/`--subject` values that look like a selector are skipped; `--flag=value` form.
  - `-R owner/repo` before `pr` and `--repo owner/repo` after `merge` are forwarded.
  - compound commands: `cd x && gh pr merge 17 --squash`, `gh pr ready 17; gh pr merge 17`, a leading `GH_TOKEN=... gh pr merge 17`, two merges in one command (both checked; the second failing refuses).
  - quoted mentions do not match: `git commit -m "run gh pr merge later"`, `gh pr comment 17 --body "gh pr merge 17"`, `echo 'gh pr merge'`.
- negative, each asserting exit code 2 and a stderr reason that names the cause:
  - a `fail` check; a `pending` check; a `cancel` check; an unknown bucket value; only `skipping` checks; an empty JSON array.
  - "no checks reported" (non-JSON stdout, exit 1); unknown PR (GraphQL error text).
  - `gh` not found (`FileNotFoundError`); timeout (`subprocess.TimeoutExpired`); stdout is JSON but not a list of objects.
  - untokenisable command that looks like a merge (`gh pr merge 17 --body "unterminated`) → refuse; an untokenisable command that does not → proceed.
  - stdin empty, not JSON, or a JSON value that is not an object → refuse.
  - an exception raised inside the injected `run` other than the two above → refuse (not a traceback with exit 1).
- `checks_problem` and `merge_invocations` are also tested directly (table-driven is fine); `evaluate` with a payload lacking `cwd`.
- `main`: via `monkeypatch` of `sys.stdin` and `capsys`; plus one `subprocess` run of `python -m hilclaw.merge_guard` (with `sys.executable`, `cwd` at the repository root, a non-merge payload on stdin) to cover the `__main__` entry without calling `gh`.
- Coverage is not measured in this task (`pytest-cov` belongs to P0.5-3 and would be a new dependency); the tests must still reach every branch above and every exit path — say in `## Result` how you checked (e.g. the stdlib `python -m trace --count --missing --module pytest`).
- Do not add tests for other test files, `pyproject.toml` or any CI file (test rule ⑤).

Local verification (CI is not on `main` — run before the commit and again before the merge, paste the summary lines into `## Result`):
- `python -m pytest` exits 0 (all tests, including the existing ones), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0. Local ruff is 0.15.14; the CI of PR #16 resolves a newer ruff (0.16.10) that additionally reports `SIM905` (a string literal split with `str.split()` instead of a list literal) — do not introduce that pattern in the new files. Do **not** touch `hilclaw/driver_state.py:26` or `pyproject.toml`: that is HQ-0002, an open owner decision.
- Manual read-only smoke, only if `gh` is authenticated (not part of the automated tests; record the outcome or "not run"): pipe `{"tool_name":"Bash","tool_input":{"command":"gh pr merge 15 --squash"},"cwd":"."}` into `python -m hilclaw.merge_guard` → exit 2 with the "no checks reported" reason (PR #15 is merged and has no checks); the same with PR 16 → exit 2 naming the failing checks, if PR #16 is still red. The guard only runs `gh pr checks`, so nothing is merged.
- `git ls-files --eol hilclaw/merge_guard.py tests/test_merge_guard.py` shows `i/lf` for both.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `.claude/settings.json`, `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/driver_state.py` and `.github/` are unchanged.

Process:
- Branch `claude/T-0007-merge-guard-hook`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0007`; executor commits end with the trailer `Task: T-0007`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (≤ 7 rounds); the CI step is the local rerun above (`gh pr checks` will report no checks for this PR — expected while T-0003 is blocked; the guard is not registered, so it does not apply to this PR's own merge).
- Squash-merge per A-13 with `Task: T-0007` as the last line of the PR body, using `gh pr merge --squash --body "<that body>"`; delete the branch.
- Commit body: the provisional choices (module location and name, API, recognition rule and its known limits, selector handling, "all successful" = at least one `pass` and otherwise `pass`/`skipping`, fail-closed cases, exit code 2 + stderr, 60 s timeout) with one line of reason each, and the language line.
- `PROCESS/STATE.json`, `PROCESS/journal/` and the `PROCESS/PLAN.md` checkbox belong to the driver. PLAN P0.5-4 is **not complete** after this task (registration is pending); say so in `## Result`.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5).

## Out of Scope
- **Registering the hook**: any edit of `.claude/settings.json` / `settings.local.json` (a `hooks.PreToolUse` entry), or any other activation route. Owner action (Follow-ups).
- The guard for the forbidden commands (`git push --force*`, `rm -rf *`, `gh repo delete *`) that PLAN P0.5-4 lists as a follow-up to consider. Decided here per DRIVER §9 (not owner-only): **not in this slice**, because the D12 mandatory-test exception covers only the `gh pr merge` guard, so a second guard in the same module would be either untested or tested against test rule ⑤, and shell-command pattern matching has its own false-positive risks that deserve a separate review.
- Changing `.github/workflows/ci.yml`, `pyproject.toml` or `hilclaw/driver_state.py` (PR #16 / HQ-0002).
- Editing DRIVER.md, PLAN.md, CLAUDE.md or the skills (document mode, separate changes).
- Runtime hooks of the HIL-Claw orchestrator (PLAN P2-4: budget/gate checks, journaling, Stop commit) and any decision on OD-18 or OD-19.
- Intercepting merges that do not go through `gh pr merge` (`gh api .../merge`, the web UI, a local `git merge` + push), checking the reviewer verdict, the `DONOTMERGE` label or the Draft state.
- A build backend, console-script entry point, or a POSIX sh wrapper for the hook command.

## Follow-ups
- (**owner action**, completes PLAN P0.5-4) Register the guard in `.claude/settings.json` as a `PreToolUse` hook for the shell tools (Bash, and PowerShell where it is used), running `python -m hilclaw.merge_guard` from the project directory. The driver and the executor may not edit that file (DRIVER §1-5). Register it only **after** T-0003 has landed: with no CI on `main`, PRs have no checks and the guard refuses every merge by design. At registration, confirm from a real session that the hook fires under Bypass permissions and that exit code 2 blocks the call.
- (doc mode, with the registration) CLAUDE.md "CI 미구축" note, dev-item-address step 13 and DRIVER §1-5: once the guard is active, "local rerun instead of CI" can no longer end in a merge; state what the executor does when the guard refuses (BLOCKED reason).
- (separate task; test question for the owner) Forbidden-command guard for `git push --force*` / `rm -rf *` / `gh repo delete *` under Bypass permissions (D13 follow-up): the D12 exceptions name exactly two tested tools, so whether this guard gets tests needs the owner's word.
- (decision to revisit with data) "All successful" = at least one `pass`, others `pass`/`skipping`; the stricter "only `pass`" and a `--required`-only variant were not chosen (there are no required checks without branch protection, D10).
- (known limits) A line inside a here-document body that reads like `gh pr merge` is treated as a merge (false positive → refusal); PowerShell quoting differs from POSIX tokenisation; `gh` aliases and merges through `gh api` are not recognised.
- (P0.5-2) The module-to-test mapping: `hilclaw/merge_guard.py` → `tests/test_merge_guard.py`.
- (P0.5-3 / CI) First coverage measurement and the CPython 3.11 run happen once CI exists.

## Result
