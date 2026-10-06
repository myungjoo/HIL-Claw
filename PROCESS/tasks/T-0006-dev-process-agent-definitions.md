---
id: T-0006
title: Add the development-process subagent definitions dev-planner, dev-executor and dev-reviewer
phase: P0
status: DONE
commitMode: doc
coversReq: ["#5 D5", "#5 A-13", "DRIVER §7"]
dependsOn: []
touchesFiles: [.claude/agents/dev-planner.md, .claude/agents/dev-executor.md, .claude/agents/dev-reviewer.md]
estimatedSize: {loc: 150, files: 3}
hq: []   # no owner-only decision and no OD closure: D5 confirmed creating the three agents; names and tool restrictions are an integrator proposal that this task confirms by review (DRIVER §7)
---
## Why
DRIVER §7 assigns three of the driver's roles to context-isolated sub-agents: the planner (§6), the executor (runs the `dev-item-address` skill) and the reviewer (runs the `dev-code-review` skill, spawned by the executor). Today each driver session writes those three briefs by hand in its spawn prompt, so the role boundaries (what a planner may write, that a reviewer never edits, which actions are forbidden under Bypass permissions — §1-5) are restated differently every iteration and enforced by nothing. D5 (DRIVER §7 and §11, 2026-10-03) decided to put the roles into `.claude/agents/*.md` during MVP development. PLAN P0-6 asks for exactly that: three subagent definitions with the allowed tools fixed in the frontmatter, no hard-coded model names, wrapping the two existing skills. `.claude/agents/` does not exist yet.

The agent files are thin role wrappers, not a second source of truth: CLAUDE.md stays canonical for rules, `PROCESS/DRIVER.md` for the driver procedure, the two `SKILL.md` files for the work and review procedures. An agent file states the role, its inputs and outputs, its tool boundary and its prohibitions, and links to the rest.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, naming and trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §7 (lines 122-132: role table and the D5 paragraph — the specification this task implements), §6 (lines 115-120: planner input, output, rules), §1-5 and §1-6 (lines 28-29: Bypass permissions, forbidden actions kept by discipline, dedicated clone), §2 (lines 44-45: document mode; a planner-created task file is committed by the driver without review), §3 step 3 (line 69), the "BLOCKED 사유" paragraph (line 75), §8 (lines 136-138), §9 (lines 144-147), §11 row D5
- CLAUDE.md — whole file (26 lines). In particular "코멘트 최소화", "미결은 발명하지 않는다", "세션 진입 점검", "세 층 모델" (agent definitions are layer 1), "브랜치·merge 절차" (`.claude/` is a document-mode path), "테스트 규칙" ⑤, "모델 배정 원칙" (no hard-coded model names)
- PROCESS/PLAN.md line 14 (P0-6) and line 21 (P0.5-4: guard hooks are a later item)
- .claude/skills/dev-item-address/SKILL.md — whole file (48 lines): the procedure `dev-executor` wraps and the procedure you follow for this task (line 10 document mode; steps 9, 10-12, 15)
- .claude/skills/dev-code-review/SKILL.md — whole file (20 lines): the procedure `dev-reviewer` wraps; lines 19-20 (code mode: PR comment; document mode: verdict and findings returned to the caller; `SECURITY` first line)
- .claude/settings.json — read only (allow/deny lists of the CLI path; lines 42-49 are the deny list the agents restate as discipline)
- PROCESS/tasks/T-0005-readme-three-layer-pointers.md — `## Result` only: how a document-mode task was landed and recorded, and the follow-up "(after P0-6) mention `.claude/agents/` in README"
- The current Claude Code subagent documentation (official docs, "subagents" page) — to verify the file format; see "Format verification" below. Use whatever documentation access your session has; do not rely on this file's recollection.

## Acceptance Criteria
DRIVER §7 fixes the three names and two properties (`dev-reviewer` has no write tools; models follow the CLAUDE.md principle). Everything else — the exact tool lists, the wording and section layout of the agent files, their language — is an **integrator proposal confirmed by the review of this task** (DRIVER §7), not an owner decision or a registered OD. Follow the criteria below, state each choice with one line of reason in the commit body and in `## Result`, and do not present them as requirements.

Format verification (do this first, record the outcome in `## Result`):
- Check against the current Claude Code subagent documentation: (a) the location `.claude/agents/<name>.md` and the frontmatter fields (`name`, `description`, `tools`, `model`, and any field you use beyond these); (b) the syntax of `tools` and the current name of the tool that spawns a sub-agent; (c) what happens when `model` is omitted and whether `inherit` is an accepted value; (d) whether a subagent can spawn another subagent; (e) whether `tools` can restrict Bash to specific commands or only grant Bash as a whole; (f) whether a skill can be preloaded through frontmatter.
- The planner's recollection, to be checked and not trusted: `tools` is a comma-separated list of tool names and omitting it inherits every tool; `model` accepts an alias or `inherit`; the documentation has stated that subagents cannot spawn other subagents; `tools` grants Bash as a whole.
- If the documentation and this file disagree on a format detail, follow the documentation and note the difference in `## Result`.
- If you cannot reach the documentation, write the files from the criteria below, mark the format as unverified in `## Result` and add a follow-up; this alone is not BLOCKED.

Files (exactly three, all new):
- `.claude/agents/dev-planner.md`, `.claude/agents/dev-executor.md`, `.claude/agents/dev-reviewer.md`. The `name` field equals the file name without `.md`.
- Each file has YAML frontmatter with `name`, `description` and `tools`, followed by a Markdown body.
- `description` says when the driver should use the agent, in one or two sentences, and names the DRIVER section or skill it implements.

Model (CLAUDE.md "모델 배정 원칙"):
- No file contains a specific model name or a model-tier alias, in the frontmatter or in the body. Either omit `model` or set `model: inherit` — choose the one that the documentation says makes the agent use the caller's model, use the same choice in all three files, and record which and why. Reason: the routine fixes the model in its own settings (DRIVER §1-5), and all three roles are judgement roles under the CLAUDE.md principle.
- The body of `dev-executor` may say that mechanical steps can be delegated to a lighter model as `dev-item-address` allows, without naming one.

Tools (explicit list in every file; do not leave `tools` out, because DRIVER §7 says the allowed tools are fixed in the frontmatter):
- `dev-reviewer`: read and search tools plus Bash only. It must **not** list Write, Edit, NotebookEdit or the sub-agent spawn tool. Bash is needed for `git diff` / `git log` / `gh pr view` / `gh pr diff` and, in code mode, `gh pr comment` or `gh pr review --comment`. If verification item (e) shows that Bash cannot be narrowed in the frontmatter, the body states the limit as discipline: Bash is used only for read-only git/gh commands and for posting the review comment; the reviewer never changes the working tree, never commits, pushes, merges, or edits labels.
- `dev-planner`: read and search tools, Bash (for `git log`, `gh pr list`, `gh issue view`), and Write for the single task file it creates. No Edit and no sub-agent spawn tool unless you find a concrete need and record it.
- `dev-executor`: read, search, Write, Edit, Bash, and the sub-agent spawn tool (needed for step 10 of `dev-item-address`). Do not add web or MCP tools by default; a task that needs documentation access says so in its own Required Reading and that gap is recorded as a follow-up, not solved here by widening the list — unless verification shows the executor cannot do its normal work without one, in which case add it and record why.

Sub-agent nesting (verification item (d)) — record the finding, do not invent a resolution:
- DRIVER §7 has the executor spawn the reviewer. The journal shows that executor sub-agents did spawn reviewer sub-agents in earlier iterations (T-0005: one review round by a fresh-context reviewer), while the documentation has stated a no-nesting rule. Report in `## Result` what the documentation says now and what you observe in your own session (you are a sub-agent: is a spawn tool available to you, and did your own reviewer spawn for this task work).
- Write `dev-executor` according to DRIVER §7 as it stands (the executor spawns the reviewer), and have its body say that if the spawn tool is unavailable or the spawn is denied, the executor returns BLOCKED and does not review its own change.
- If nesting turns out to be impossible for a custom agent, that requires changing who spawns the reviewer (DRIVER §3-5 and §7), which is outside this task: land the three files as specified, describe the conflict in `## Result` and in Follow-ups, and say so in your returned summary. Do not edit DRIVER.md and do not restructure the roles here.

Body content — each file is short and links instead of copying:
- All three: (1) the role in one or two sentences and that it is part of the development driver, not the HIL-Claw runtime (DRIVER line 3); (2) inputs and what it returns; (3) the canonical order CLAUDE.md > `PROCESS/DRIVER.md` > skills, with links; (4) the prohibitions below.
- Prohibitions, restated in every file because Bypass permissions does not stop them (DRIVER §1-5): never run `git push --force*` (including `-f`), `rm -rf *`, or `gh repo delete *`; never edit `.claude/settings.json` or `.claude/settings.local.json`; if a tool call is denied or fails, do not work around it — return BLOCKED with the reason. Work only in the driver's dedicated clone (§1-6).
- `dev-planner`: implements DRIVER §6 — link to it for inputs and rules instead of listing them. States: it writes exactly one file `PROCESS/tasks/T-NNNN-<slug>.md` in the DRIVER §5 format with `status: TODO` and an English body; it does not commit, push, branch, or edit any other file (the driver commits the task file, §3-4); it does not implement the task; when the next item needs an owner-only decision (§9) it creates no task file and returns the HQ question instead; it returns the file path, `touchesFiles`, BLOCKED concerns and an optional next-task candidate.
- `dev-executor`: its only inputs are the task file and that file's Required Reading (§3-5). It follows the `dev-item-address` skill end to end, including the reviewer cycle and the A-13 landing (document mode: `Reviewed-by` trailer, push to `main`; code mode: Draft PR, squash-merge). Link to DRIVER §3-5 for the resume rule, branch contention, and the wall-clock limit, and to §5 for the naming convention and trailers — do not copy them, and do not write the limit's value or the BLOCKED list into the agent file. States: it fills `## Result` in the task file and leaves that edit uncommitted for the driver; it never touches `PROCESS/STATE.json`, the journal, or the PLAN checkbox; it returns a summary of at most 200 characters.
- `dev-reviewer`: follows the `dev-code-review` skill. Input is a PR number (code mode) or a branch name (document mode, diff against `origin/main`). Output is a PR comment in code mode and the verdict plus findings returned to the caller in document mode, with `SECURITY` as the first line when the skill requires it. States that it starts from a fresh context and judges only from the repository, the diff and the task file, not from the executor's account of the change.
- How the skill is attached (reference by link, or frontmatter preload if verification item (f) shows it is supported) is your choice; record it. Either way the skill text is not copied into the agent file.
- Language: write `description` and the body in **English** — the owner's global rule asks for English in documents that enter the repository. The two existing `.claude/skills/*/SKILL.md` files are Korean; do not translate them and do not write a language policy into the agent files. The commit message is English.
- Relative links from `.claude/agents/` use `../../` for repository-root files (for example `../../PROCESS/DRIVER.md`, `../skills/dev-item-address/SKILL.md`).

Do not invent (CLAUDE.md "미결은 발명하지 않는다"):
- Every rule stated in an agent file must be traceable to CLAUDE.md, `PROCESS/DRIVER.md` or one of the two skills. Do not add new process rules, new BLOCKED reasons, new limits, retry counts, or role duties (for example a notifier agent, a reviewer that fixes findings, a planner that updates `STATE.nextTask` itself).
- If a required item above contradicts CLAUDE.md, DRIVER.md or a skill, follow those documents and note the discrepancy in `## Result`; do not edit them in this task. If you cannot write an item without deciding something undecided, return BLOCKED ("요구 불명확·미결 발명 의심") with the exact question.

Size and form:
- Only the three files change. Expected about 30-50 lines each; hard cap 300 changed lines / 5 files (D4). If a file grows beyond roughly 60 lines you are restating DRIVER.md or a skill — cut and link.
- UTF-8, LF, final newline, no trailing whitespace (`.editorconfig`). The committed blobs must be LF even if the Windows working copy shows CRLF.

Verification (document mode — no tests are added, CLAUDE.md test rule ⑤; paste the outcomes into `## Result`):
- `git diff origin/main --stat` lists exactly the three files in `touchesFiles`.
- Each file starts with a `---` line, has a closing `---`, and its frontmatter contains `name`, `description` and `tools`; `name` matches the file name. Check by reading the files (or a throwaway one-liner — do not add a script to the repository).
- `grep -nE 'Write|Edit' .claude/agents/dev-reviewer.md` shows no tool grant in the frontmatter (mentions in the body that say the reviewer has no such tools are fine).
- A search of the three files for model names and tier aliases finds nothing.
- Every relative link target in the three files exists (`test -e` from the file's directory); section references to DRIVER.md are checked by eye.
- `git ls-files --eol .claude/agents/` shows `i/lf` for all three after staging.
- Loading check, best effort: agent definitions are read when a session starts, so the session that writes them may not see them. If your environment lets you list or invoke project agents from a fresh session, do so and record the result; otherwise record that the loading check was not performed and leave the follow-up below. Do not count an unperformed check as passed.
- `ARCHITECTURE/` is not touched, so the StandardScenarios coverage re-check does not apply; say so in the commit body.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Branch `claude/T-0006-dev-process-agent-definitions` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context sub-agent that follows `.claude/skills/dev-code-review/SKILL.md`, give it the branch name (review target = diff against `origin/main`) and this task file's path, and receive the verdict and findings as its return value. The review is what confirms the names and tool lists (DRIVER §7), so ask the reviewer to check them against §7 explicitly. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED (security). If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). Before pushing, `git show --stat HEAD` must list exactly the three files; if anything else appears, stop and fix. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0006:`; the body explains what was added, lists the choices (model handling, tool lists, skill attachment, language) with one line of reason each, the nesting finding in one line, and the coverage-re-check note; the message ends with the trailers, in this order:
  `Reviewed-by: reviewer agent (N rounds, Approve)`
  `Task: T-0006`
  followed by any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Then delete the remote and local branch and check out `main` at `origin/main`.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to the task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the format-verification outcomes (a)-(f), the nesting finding, the choices, the verification outcomes, and follow-ups.
- Do not edit `.claude/settings.json` or `.claude/settings.local.json`, and do not run `rm -rf` or `gh repo delete`. If writing under `.claude/agents/` is denied, return BLOCKED rather than working around it.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Changing `PROCESS/DRIVER.md` (§3 to invoke the agents by name, §7 to record the confirmed tool lists or a changed reviewer-spawn path), `PROCESS/PLAN.md`, `CLAUDE.md` or `README.md`. `PROCESS/STATE.json`, the journal and the PLAN checkbox are driver-owned.
- `.claude/settings.json` and `.claude/settings.local.json` — never edited, by this task or by any agent it defines.
- Hooks of any kind, including the forbidden-command PreToolUse guard and the `gh pr merge` guard (P0.5-4).
- Any change to the content of the two skills, and any new skill.
- Runtime (HIL-Claw run) agents — Round-Manager, coder-driver, evaluator (P2) — and a notifier agent (the notifier stays in the driver, DRIVER §7).
- Tests, scripts or CI checks for the agent files.
- Deciding the documentation-language policy for `.claude/` files.

## Follow-ups
- (doc mode, after this task) Update DRIVER §3-3 / §3-5 / §7 to invoke `dev-planner`, `dev-executor`, `dev-reviewer` by name and to record the tool lists as confirmed by this task's review; until then the driver may keep writing the briefs by hand.
- (doc mode, only if the nesting finding requires it) Decide who spawns the reviewer when a custom agent cannot spawn sub-agents — a change to DRIVER §3-5 / §7 and to `dev-item-address` step 10. Check DRIVER §9 to see whether it is an owner question before writing the task.
- (next README touch) Mention `.claude/agents/` in the layer-1 row and the repository map (T-0005 follow-up).
- (P0.5-4) The prohibitions restated in the agent files are discipline only; the PreToolUse guard would enforce them.
- (first driver iteration after landing) Confirm from a fresh session that the three agents are listed and can be invoked, if the loading check could not be performed here.
- (owner, non-blocking) Language of `.claude/` prose: the agent files are English per the owner's global rule while the two skills are Korean. A policy line in CLAUDE.md would settle it for skills and agents together.

## Result
- Document mode, no PR. Landed on main as 21f2878 ("T-0006: Add the dev-planner, dev-executor and dev-reviewer agent definitions"), fast-forward from 94206bf on the first push; branch commit 2742531. Change: the three files in `touchesFiles`, +120/-0 (38 / 39 / 43 lines). Remote and local branch `claude/T-0006-dev-process-agent-definitions` deleted; `main` == `origin/main`.
- Review: 1 round by a fresh-context reviewer sub-agent (dev-code-review, document mode; given only the branch name, this file's path and the skill path), verdict Approve, no security concern, no High/Medium/Low/Nit finding, nothing trivially fixable left. Nothing was changed after the review. The reviewer checked the names and tool lists against DRIVER §7 and the frontmatter against the documentation it fetched itself. Two observations, no action in this task:
  - `dev-executor.md` "pass them to every sub-agent you spawn" is not verbatim in a source document; the reviewer judged it a direct consequence of DRIVER §1-5, not a new rule. Kept.
  - DRIVER §6 "phase 전환" does not say who raises `STATE.phase` and writes the journal; the planner file limits the planner to one task file, consistent with §7 (the driver alone handles state and journal). The ambiguity is in DRIVER §6 — added to Follow-ups.
- Format verification (source: https://code.claude.com/docs/en/sub-agents, fetched 2026-10-06 through WebFetch, which returns a model-made digest of the page, not the raw text):
  - (a) Project agents live in `.claude/agents/<name>.md`. `name` and `description` are required; `tools` and `model` are optional. Other fields exist (`disallowedTools`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, and more); none is used here.
  - (b) `tools` is a comma-separated string or a YAML list; omitted, it inherits every tool. The spawn tool is named `Agent` (the older name `Task` is still accepted as an alias); `Agent(type, ...)` restricts which agent types may be spawned.
  - (c) With `model` omitted the order is: per-invocation model parameter, then the frontmatter, then the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, then the main conversation's model. `inherit` is an accepted value and selects the main conversation's model.
  - (d) A subagent can spawn subagents, by default up to three layers below the main conversation (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; at the limit the `Agent` tool is withheld). This differs from the planner's recollection (no nesting).
  - (e) `tools` grants Bash as a whole; it cannot narrow Bash to specific commands. The documented ways to narrow it are a `PreToolUse` hook or `permissions.deny` in settings.
  - (f) A `skills` frontmatter field preloads the full skill content at startup; without it a subagent can still invoke project skills during execution.
  - Loading: agents are registered at session start; a new file in an existing `agents` directory is picked up by a file watcher, but the first file in a new `agents` directory needs a restart.
- Nesting finding: the documentation now allows nesting, and it worked in this session — the executor of this task was itself a sub-agent, had the `Agent` tool, and its reviewer spawn succeeded. driver → executor → reviewer is two layers, inside the default limit. No conflict with DRIVER §7; the conditional nesting follow-up above is not needed.
- Choices (conventions of this task, not requirements):
  - Model: `model: inherit` in all three files, no model name or tier alias anywhere. Reason: per (c) `inherit` selects the caller's model explicitly, while an omitted field can be redirected by an environment variable.
  - Tools: `dev-planner` = `Read, Grep, Glob, Bash, Write`; `dev-executor` = `Read, Grep, Glob, Bash, Write, Edit, Agent`; `dev-reviewer` = `Read, Grep, Glob, Bash`. Reason: the lists in the Acceptance Criteria with the current tool names. `Agent` is left unrestricted in the executor (not `Agent(dev-reviewer)`) because dev-item-address also lets mechanical steps go to a lighter sub-agent. No web or MCP tool was added. The reviewer's Bash limit is stated in its body as discipline, per (e).
  - Skill attachment: relative link to the `SKILL.md`, not the `skills` preload. Reason: no dependency on a field beyond the four verified in use, and whether the preload needs further tools in `tools` was not verified.
  - Language: English description and body; no language policy written.
  - `description` values are double-quoted YAML strings (they contain parentheses and `§`).
- No discrepancy was found between the required items and CLAUDE.md / DRIVER.md / the skills.
- Verification:
  - `git diff --cached --stat origin/main` before the commit and `git show --stat HEAD` on the squashed commit: exactly the three files, 120 insertions.
  - Each file starts with `---`, closes the frontmatter at line 6, and has `name`, `description`, `tools`, `model`; `name` equals the file name (one-liner check).
  - `grep -nE 'Write|Edit' .claude/agents/dev-reviewer.md`: one hit, line 32, the body sentence saying the reviewer has no such tool; none in the frontmatter.
  - Search for model names and tier aliases (`opus|sonnet|haiku|fable|claude-[0-9a-z]|gpt`, case-insensitive): no hit.
  - Relative links: every target exists (`test -e` from `.claude/agents/`); DRIVER section references checked by eye, and again by the reviewer.
  - `git ls-files --eol .claude/agents/`: `i/lf w/lf attr/text=auto eol=lf` for all three; `git diff --cached --check` clean; no trailing whitespace.
  - `claude plugin validate .claude/agents` (Claude Code 2.1.280): "Validation passed" — frontmatter parse check only.
  - Loading check: **not performed**. No fresh session was started, and `.claude/agents/` was a new directory in this session, so the agents could not be listed or invoked here. Follow-up below stands.
  - `ARCHITECTURE/` not touched: the StandardScenarios coverage re-check does not apply.
- Follow-ups (in addition to the list above):
  - The conditional follow-up "decide who spawns the reviewer" is moot per finding (d); it can be dropped.
  - (with the DRIVER §3/§7 follow-up) Say in DRIVER §6 who performs the phase transition (reviewer observation 2).
  - (doc mode, optional) The task-file template could record that documentation access (WebFetch) is not in `dev-executor`'s tool list; a task that needs it, as this one did, must be run by a session that has it or name it in Required Reading.
  - (optional) Windows sessions also expose a PowerShell tool; the agent tool lists grant only Bash. Not needed so far (Git Bash covers git/gh).
