---
id: T-0114
title: Pin in the tests of `hilclaw/standin_profile.py` the walk-through lines of ADR-0036 that no test holds yet - above all a macOS product version line left with three or more words - and name ADR-0036 in the docstrings of the module; no change of behaviour
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, FR-13, C-7, OD-4]
dependsOn: [T-0109, T-0111]
touchesFiles: [hilclaw/standin_profile.py, tests/test_standin_profile.py]
estimatedSize: {loc: 15, files: 1}   # non-test: docstring lines of one module, no statement changes; the test file is excluded from the cap (D4)
hq: []   # carries a closed record (ADR-0036) into tests and a docstring; closes no OD, writes no ADR, no dependency, no schema or data-plane file. Independent of HQ-0005, HQ-0006 and HQ-0007
---
## Why
ADR-0036 (T-0111, landed on `main` as `588a6db`, 2026-10-09) settled how the `host.os` of a `cpu_standin` hw_profile is made under macOS when the first line of the output of `sw_vers -productVersion` holds a space or a tab: **the spelt line is kept whole, and no check for a space or a tab is made at any moment**. Its Consequences say of the code:

- "**No test pins a line that is left with three or more words** (the row of the Walk-through that gives `macos 0.0 beta 1`); the code has no branch on the number of words, so such a line takes the path of the pinned two-word line. Whether a test for it is added is left to a later code task and is not asked for here."

That line is the one case where ADR-0036 and a literal reading of the sentence "two or three words" of ADR-0035 decision 4 differ (`macos 0.0 beta 1` has four words), so it is the case a later edit of the module is most likely to break without a test noticing. **This task adds that test**, and with it the other rows of the walk-through that are not pinned as written. It also makes the module say by which record it keeps such a line: `hilclaw/standin_profile.py` and its test file name ADR-0035 only (`git grep ADR-0036 -- hilclaw tests` finds nothing at planning time). It ticks **no PLAN checkbox** (P1-5 stays open: `task.objective` waits on #5 A-4).

Planner's judgements (2026-10-10, from the files at `main` `f780152`; **the reviewer is asked to re-check each**):
- **No decision of a record is taken.** The rule is ADR-0036's; ADR-0036 says the code agrees with it "and no change of the code follows". The task adds tests and docstring sentences only.
- **The weakest point, weigh it first - whether so small a slice is worth a PR.** The planner's reading: yes. It is named as a follow-up by T-0111 `## Result`, by T-0113 `## Follow-ups` and by the journal of 2026-10-10; it pins the one row where two readings of ADR-0035 differ; and a public docstring that lists the unreadable cases of `host.os` should say that a product version with a space is not one of them. CLAUDE.md test rule 5 does not forbid it: the tests target a module of `hilclaw/`, not test, CI, hook or helper code.
- **Second weak point - the docstring edit.** It is not required by ADR-0036 (nothing the docstrings say is untrue). The planner includes it because the module docstring names "ADR-0035 decisions 2 to 6 and 8" as its source and a reader cannot learn from it that a later record reads decision 4. **If a reviewer reads the docstring edit as saying more than ADR-0036, cut the sentence rather than argue it out; the tests alone still satisfy the task.**
- **Why this item now**: no lock, no TODO / INTERRUPTED / IN_PROGRESS task file and no open PR at planning time. T-0088, T-0106 and T-0107 are BLOCKED on HQ-0005, HQ-0006 and HQ-0007, unanswered on #5. Candidates weighed and not taken: a dedicated exception class for the refusal of a 0 in `gemm_contract` (only when that module gets a caller); the shared once-only write helper (not before 2026-10-16); the rest of P1-1 (HQ-0005), of P0.5-4 (HQ-0007), `task.objective` (#5 A-4), the rest of P1-8 (OD-3 and others, re-checked by the planners of T-0105 to T-0113).
- **A-13 reading** (ask the reviewer explicitly): code mode (a file of `hilclaw/` changes); no new dependency, no schema file, no data-plane file, no statement of the module changes. No BLOCKED reason applies.

Known risk, accepted: ADR-0036 and ADR-0035 are inside their objection windows until 2026-10-16, ADR-0001 until 2026-10-13. If ADR-0036 is reverted, this change is reverted with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0036-od4-cpu-standin-host-os-macos-version.md - the whole record (116 lines)**: Status, Context, decision 1 (scope), **decision 2 (the rule, the moment with its steps, "So", "Length", how the two sentences of ADR-0035 are read)**, decision 3 (the shapes), **the Walk-through table (seven rows)**, **Consequences (first bullet: which test pins which line)**, Boundaries
- ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md decision 4 (the sentence above the table, the macOS row) and decision 6 - read only
- **`hilclaw/standin_profile.py`** (280 lines, whole): the module docstring (lines 1-68; the `Darwin` row of the table at lines 21-24, the sentence "The words of `host.os` are joined by single spaces" at line 38), the docstring of `local_record` (lines 101-140; the list of unreadable cases at lines 120-129), the `Darwin` branch (lines 150-155), `_spelling`, `_command_line`
- **`tests/test_standin_profile.py`** (1018 lines): the constants and the `Machine` fake with the `machine` fixture, `example` and `fails` (lines 21-177); `test_macos_branch`, `test_macos_facts_are_spelt_and_later_lines_ignored`, `test_macos_version_of_several_words_is_kept` (lines 245-267); `COMMAND_FAILURES` and `test_macos_command_that_cannot_be_read` (lines 579-614); `test_macos_host_os_length_limit` (lines 648-654); the live case (from line 988) - read only for the last
- `hilclaw/keys.py`: `hw_profile_key` - read only
- PROCESS/tasks/T-0111-adr-od4-cpu-standin-host-os-macos-version.md `## Result` ("The rule as landed, with its moment", "Whether the code agrees", "Follow-ups") and PROCESS/tasks/T-0113-gemm-contract-docstring-adr-0037.md `## Result` (how the sibling slice of the same kind landed: literals copied from a record, docstring sentences, review findings)
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` - read only (six checks at planning time)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6091831907 (the ADR-0037 notice, the last of 70 comments at planning time; `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). **If the repository owner has objected to ADR-0036, ADR-0035 or ADR-0001, do not start: return BLOCKED ("requirement unclear") quoting the comment.** An owner answer to HQ-0005, HQ-0006 or HQ-0007 does not stop this task

Line numbers are those of `main` at `f780152`; if they moved, find the sentence by its words.

## Acceptance Criteria
ADR-0036 fixes the rule. Where a criterion below and the record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/standin_profile.py` (docstrings only) and `tests/test_standin_profile.py`. **Nothing else**: every other module and test, every ADR, the OD register, `pyproject.toml`, `.github/` stay as they are.
- Language: Python (the module exists in Python; no choice arises). One line in the commit body and `## Result`.

### The module - docstrings only
- **No statement changes.** Check: `git diff origin/main -- hilclaw/standin_profile.py` touches only lines inside docstrings; the statement count that coverage reports for the module is the same before and after (measure it on `origin/main` first and record both).
- **Module docstring**: name `ARCHITECTURE/decisions/ADR-0036-od4-cpu-standin-host-os-macos-version.md` where the rule for the kernel name `Darwin` or for the words of `host.os` is given, in one or two sentences: under macOS the first line of the output of `sw_vers -productVersion` is kept whole in the spelling of decision 6, so `host.os` has two or more words there (ADR-0036 decisions 2 and 3), and two or three under Linux and WSL.
- **`local_record`**: one sentence next to the list of cases that a product version line that holds a space or a tab is **not** a fact that cannot be read (ADR-0036 decision 2); the existing sentence on `ID` and `VERSION_ID` stays as it is.
- **Say no more than the record.** No fact about what macOS prints or whether such a line occurs; no reason attributed to ADR-0035 (it states none for the `ID` / `VERSION_ID` rule); nothing about a reader of a part of `host.os`, a tool, onboarding or the repository owner. Before the first review, check every sentence you wrote against ADR-0036 decision 2 and decision 3 word by word (most review rounds of T-0110 to T-0113 went to single sentences that said more than their source).
- CLAUDE.md "코멘트 최소화": no new comment in the module; keep the addition short (about 5-12 docstring lines in all).

### Tests (`tests/test_standin_profile.py`, excluded from the size cap)
Every existing case stays and passes unchanged; none is deleted or renamed. Use the `machine` fixture with `machine.kernel = DARWIN` and `machine.sw_vers`; every value is fictitious, as in the record. Helpers, if any, live in the test file and get no tests of their own (test rule 5). Add, under one comment line naming the record (in the manner of the ADR-0037 literals of `tests/test_gemm_contract.py`):
- **The walk-through of ADR-0036 as literals copied from the record**, each as the bytes of the first line and the expected `host.os`: `0.0` gives `macos 0.0`; a tab, `0.0`, two spaces gives `macos 0.0`; `0.0 beta` (one space) gives `macos 0.0 beta`; `0.0`, a tab, `beta` gives `macos 0.0 beta`; `0.0`, a space, a tab, a space, `beta`, two spaces, `1` gives `macos 0.0 beta 1`. Rows that an existing test already pins byte for byte may be left to that test; say in `## Result` which row is pinned by which test.
- happy (the case the task exists for): for the line of the fifth row the whole record equals `example(os="macos 0.0 beta 1")`, `host.os` has exactly four words, `hilclaw.keys.hw_profile_key` accepts the record, and only the kernel name and the three commands were asked (`machine.asked`).
- branch: the one-space line and the tab line of rows three and four give records with equal `host.os` and equal key names; the key name of the fifth row differs from that of the third; a line with several runs and with spaces or tabs at both ends gives the same value as the same words joined by single spaces.
- negative (failure paths of a line of several words; each through `fails(machine, "host.os")`, so that no record is returned and nothing stands in):
  - a line of several words that holds a character outside 0x20 to 0x7E between or inside its words (for example a form feed or a byte above 0x7E between `beta` and `1`) cannot be read;
  - **length after the spelling** (ADR-0036 decision 2, "Length"): a line of several words whose spelt form has exactly 249 characters gives a record whose `host.os` has 255 characters and which `hw_profile_key` accepts; one whose spelt form has 250 characters gives none; and a line whose raw form is longer than 249 bytes only because of the length of its runs of spaces and tabs, with a spelt form of at most 249 characters, gives a record. Count each constructed length in the test with an assertion on `len(...)` rather than by hand (the planner of T-0111 miscounted a worked example by one word);
  - the message of each failure holds no text of the line (the manner of `test_messages_hold_no_text_read_from_the_machine`).
- No test asserts the wording of a docstring, and no test asserts anything about what a real macOS prints. The live case is not changed.

Test rules of CLAUDE.md / DRIVER §5 (D12): 1 the package total of `hilclaw/` stays at or above 80 % lines and functions (record the two figures of the final head from the CI log); 2 happy, error, branch and negative cases as above; 3 the public function of the touched module (`local_record`) and its public exception have tests (they do; the new cases call `local_record`); 4 the module has its test file; 5 no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (measure the pass and skip counts on `origin/main` first; record before and after), `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
- `git diff origin/main --stat` lists only the two files of `touchesFiles`; `git ls-files --eol` shows `i/lf` for both; `git diff --check` is clean. Record the line count of the non-test diff (cap 300 LOC / 5 files).
- CI on the PR: `gh pr checks <PR> --watch` ends with **every check of the final head successful** - six at planning time: `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. Record the run URL and the two coverage lines. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0114'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0114 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0114-standin-profile-macos-several-words-adr-0036` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0114`; executor commits end with the trailer `Task: T-0114`.
- **If a new test fails against the unchanged module**, the code and ADR-0036 disagree, against what the record states: do not change a statement of the module and do not bend the test - return BLOCKED ("requirement unclear") quoting the line, the expected value and the actual outcome.
- After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; past the cap without a final Approve is BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, BLOCKED - no self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`**: that the slice is worth a PR (the weakest point), that the docstring edit says no more than ADR-0036, that the item is selectable without the repository owner, and the A-13 reading; (b) compare every new docstring sentence with ADR-0036 decisions 2 and 3 word by word; (c) confirm that no statement of the module changed; (d) compare each line and each expected `host.os` of the new tests with the Walk-through table of the record byte by byte, and re-count the constructed lengths of the length cases.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0114`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph; that no statement of the module changed; the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **Do not put a fenced code block into `## Result`** (`ruff format --check .` reads Markdown); use inline code. Record: PR and commit, review rounds and findings, the docstring sentences as landed (quoted inline), the test cases added and which walk-through row each pins, the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 15 non-test lines in one file; the cap is 300 LOC / 5 files (tests excluded).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any change of behaviour of `hilclaw/standin_profile.py`: a statement, a message, a constant, a new function or class; any check on the number of words of `host.os`.
- The live case of the test file and its "two or three words" assertion (Linux only; it agrees with ADR-0036 decision 3).
- Checking anything on a macOS machine; any statement about real macOS versions; another source of the macOS version; another way of recognising WSL, WSL 1 against WSL 2 (ADR-0036 Boundaries).
- `hilclaw/clang_build.py` (`compiler_version`), `hilclaw/keys.py`, `hilclaw/gemm_contract.py` and every other module; a caller of `local_record`; onboarding, registration, storage (OD-26, rest of OD-4).
- Any edit of an ADR (ADR-0035 and ADR-0036 included), the OD register, OpenDecisionProposals, StandardScenarios, UsageCases, CLAUDE.md, DRIVER.md, PLAN.md, `.claude/`, `README.md`.
- Anything HQ-0005, HQ-0006 or HQ-0007 asks.

## Follow-ups
- (planner, when a caller binds the values of `gemm_contract`) Whether the refusal of a 0 gets an exception class of its own (T-0113 `## Result`).
- (planner, when a caller exists) Whether `clang_build.compiler_version` is kept, changed to the rule of ADR-0035 or removed (T-0109 `## Result`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`).
- (planner / integrator, a later record) Another way of recognising WSL, WSL 1 against WSL 2, and the macOS statements once a macOS machine is at hand (T-0111 `## Result`).
- (driver / owner) HQ-0005 (T-0088), HQ-0006 (T-0106), HQ-0007 (T-0107). PLAN P1-5: `task.objective` (#5 A-4); the place and form of a committed example.

## Result
