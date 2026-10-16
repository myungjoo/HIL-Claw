---
id: T-0220
title: Add the verdicts file of a round as a file - its text form, its final name and its write (ADR-0071 decisions 1 and 2, by ADR-0029 decisions 2 to 7) - as `hilclaw/verdicts_file.py`
phase: P1
status: DONE
commitMode: code
coversReq: [FR-17, FR-11, OD-30, OD-8]
dependsOn: [T-0218, T-0219]
touchesFiles: [hilclaw/verdicts_file.py, tests/test_verdicts_file.py]
estimatedSize: {loc: 260, files: 1}   # excluding tests: one new module of about 230-280 lines, most of it docstring as in hypotheses_file.py; one test file besides
hq: []
---
## Why

PLAN P2-6 ("가설 레코드와 판정 ... evaluate가 가설마다 판정·원인을 기록 ... 2층의 스키마 검증·쓰기 ...") is open. ADR-0071 (landed `5ab4767` by T-0218) fixes the verdicts file of a round, `runs/<run_id>/rounds/<RRRR>/eval/verdicts.json`, and its Consequences cut a code slice: "a reader and validator of the bytes of this file by decisions 2, 3 and the file-local checks of decision 4, a writer by the steps of ADR-0029 decision 4 with this final name, and the path in `hilclaw/layout.py` beside `hypothesis_record`, in the manner of `hilclaw/hypotheses.py` and `hilclaw/hypotheses_file.py`".

T-0219 (PR #145, squash-merged as `86e5e9f`) landed the first half: the pure validator `hilclaw.verdicts.validate(document)` with `InvalidVerdictRecordError` and `SCHEMA_VERSION = 1`, and the path `hilclaw.layout.verdict_record(data_root, run_id, round)`, which refuses round 0. Its `## Follow-ups` names this task: "`hilclaw/verdicts_file.py` (suggested) with `parse` (ADR-0029 decision 2 text form, set apart a `schema_version` other than 1), `final_name` (path from `run_id` and `round` through the path function of this task) and `write` (ADR-0029 decisions 4 to 7 with `verdicts.json` and temporary `verdicts.json.<token>.tmp`, via `hilclaw.once_write`), on the model of `hilclaw/hypotheses_file.py`." With it the 2층 file-local part of ADR-0071's code slice is complete (the cross-file check stays a separate follow-up).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `33b37a3`). The first unchecked PLAN items are not takeable: P0.5-4 waits on the owner's hook registration (PLAN header, D15); P1-1's remaining run-tool contract rests on T-0210, BLOCKED on HQ-0021, and `profiler.collect` is tied to #5 A-4 (owner-only); P1-8 needs a fresh design decision. HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. This task needs neither the run tools nor HQ-0021's answer. It implements a landed record and changes no data-plane file, member, value or version (ADR-0071 Consequences, "A-13 reading"), so the A-13 "data-plane schema change" reason does not apply. The 7-day objection window of ADR-0071 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125, ends 2026-10-23) is still open; as with T-0186 after ADR-0059, code may follow an accepted record inside the window, and an objection reverts both. DRIVER §6 allows an item whose `dependsOn` is met to be taken across the phase boundary. Nothing here needs a real `claude`, a logged-in CLI, hardware or an API key (D16).

## Required Reading

Line numbers are those of `main` at `33b37a3`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, **the test rules ① to ⑤ at line 113**, the language line at 112).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md** (160 lines): **decision 1 (lines 24-31: place, name, "written once and never replaced", line 29 the write by ADR-0029 decisions 4 to 7 with the temporary file `verdicts.json.<token>.tmp` in `eval/`, "The write reads no other file")**, **decision 2 (33-47: line 35 the text form; line 45 `run_id`/`round` against the path; line 46 the open top level and closed entries; line 47 "another *integer* `schema_version` is set apart (OD-11); an empty file is invalid")**, decision 6 (81-83), the Example (85-111), Consequences (132-138), Boundaries (140-152).
- **ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md decisions 2 to 7** (lines 30-91): the text form (30-39), the `id` and the path (40-47), the steps and a taken name (48-57), the directories (58-63), the temporary file and a leftover (64-73), what the rule promises (74-91).
- ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md decisions 1 and 2 (lines 24-50) - ADR-0071 cites them for this file.
- ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md decision 2 (lines 28-41): the open top level; of the members a validator does not know it checks "only the rules for the whole text".
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (the *integer* convention: decimal digits, 0 to 2**53 - 1).
- **hilclaw/hypotheses_file.py, the whole file (260 lines)** - the model of form and behaviour: the module docstring, the four exception classes, `parse` (lines 122-170: the order of checks, the version set apart before validation, the `-0` rule over the defined top-level members through `_DEFINED` at line 90), `final_name` (173-190), `write` (193-233), and the private helpers `_object`, `_nan`, `_literal`, `_unsigned` (236-260). **tests/test_hypotheses_file.py** (868 lines) - the model of the tests (bytes cases, `-0`, duplicate member names, BOM, written form, taken name, failure injection on the file-system steps, temporary-file cleanup, skip conditions).
- **hilclaw/verdicts.py, the whole file (232 lines)** - `validate`, `InvalidVerdictRecordError`, `SCHEMA_VERSION`, `_TOP` at line 55 (the defined top-level members; private, not to be imported); and **tests/test_verdicts.py** for the valid documents (the ADR-0071 Example copied from the record).
- hilclaw/layout.py lines 104-126 (`hypothesis_record`, `verdict_record`).
- hilclaw/once_write.py lines 47-86 (`write_once(path, content)`: returns `None` or the `FileExistsError` of a taken name).
- hilclaw/keys.py line 30 (`MAX_INTEGER`).

## Acceptance Criteria

### `hilclaw/verdicts_file.py` (new; Python, as the rest of the package)

Public names are the executor's; the suggested ones mirror `hilclaw.hypotheses_file` so that a reader of both finds the same shape. The reasons for any departure go into the commit body.

- **Exceptions**: `InvalidVerdictFileError(ValueError)` (a content breaks the text form or a rule of ADR-0071 decisions 2, 3, the file-local part of 4, or 6; message "field path: rule"; what `hilclaw.verdicts.validate` raises is wrapped with its message unchanged), `UnsupportedVersionError(Exception)` (no `ValueError`), `WrittenFormError(ValueError)` (no `InvalidVerdictFileError`), `NameTakenError(Exception)` (no `OSError`). Import nothing private from `hilclaw.hypotheses_file`, `hilclaw.spec_file` or `hilclaw.verdicts`: small private helpers of its own (the duplicates of `_object`, `_nan`, `_literal`, `_unsigned` and of the defined top-level names are a few lines each). A shared helper module is **out of scope** (it would touch `spec_file.py` and `hypotheses_file.py`); it stays the follow-up T-0186 already named.
- **`parse(content)`** returns the document of `content`, the bytes of a verdicts file, as `json.loads` gives it (a new `dict`, nothing added, defaulted or repaired; `content` not kept or modified). In this order, as `hypotheses_file.parse`:
  - `TypeError` for a `content` that is not exactly `bytes`;
  - `InvalidVerdictFileError` for a UTF-8 byte order mark; for a content that is not UTF-8 or not exactly one JSON text (`NaN`, `Infinity`, `-Infinity` refused; an empty content is invalid, ADR-0071 decision 2); for a member name twice **in any object, unknown top-level members included** (a rule for the whole text, ADR-0018 decision 2); for nesting too deep or an integer literal this interpreter cannot read (a limit of the reader, said so in the docstring); for a text that is no object;
  - `UnsupportedVersionError`, before any other member is looked at, when `schema_version` is an `int` from 0 to `hilclaw.keys.MAX_INTEGER` other than 1 and is not written `-0` (ADR-0071 decision 2; OD-11). Nothing else of such a content is interpreted;
  - `InvalidVerdictFileError` for a document `hilclaw.verdicts.validate` refuses;
  - `InvalidVerdictFileError` for `-0` at an *integer* place below a defined top-level member (`schema_version`, `run_id`, `round`, `verdicts`). The top level is open and ADR-0071 sets no rule for a number below a member it does not define, so a sign, a fraction, an exponent or a large integer there is accepted and returned as parsed (state this in the docstring, as `hypotheses_file` does). Note that `-0` matters: a `check` `ref.round` or an `against.round` written `-0` would otherwise parse to a valid 0.
- **`final_name(data_root, document)`** validates the document with `hilclaw.verdicts.validate` (its `InvalidVerdictRecordError` passes through, a document of another `schema_version` included) and returns `hilclaw.layout.verdict_record(data_root, document["run_id"], document["round"])`. A valid document whose `run_id` is no run directory name has no path: `hilclaw.layout.InvalidPathValueError` passes through. This is the rule "`run_id` and `round` against the path" of ADR-0071 decision 2 for whoever holds both: `final_name(data_root, parse(content)) == path`; no function takes a path. Nothing is read, created or resolved; the document is not modified.
- **`write(data_root, content)`** puts `content` under `final_name(data_root, parse(content))` if that name is free and returns `None` - the steps of ADR-0029 decisions 4 to 7 with this final name (ADR-0071 decision 1). In this order, nothing created before the last: what `parse` raises; what `final_name` raises (`InvalidPathValueError`; `TypeError` for a `data_root` that is no path); `WrittenFormError` when the content does not end with a line feed or holds a carriage return byte (no member order, indentation or line count checked); `FileNotFoundError` / `NotADirectoryError` for a `data_root` that is no existing directory (never created). Then every missing directory between `data_root` and the final name is created, and `hilclaw.once_write.write_once(path, content)` gives the name - temporary file `verdicts.json.<token>.tmp` in `eval/`, stable storage, hard link with no fallback to a replacing rename, temporary file removed. A taken name raises `NameTakenError` (equal bytes reported as any other; the entry under the name is never opened, read or compared; nothing retried). Any other failing step raises its `OSError` unchanged; the directories created stay. **The write reads no other file** (ADR-0071 decision 1): not `hypotheses.json`, not a result file, not `instance.json`.
- **Module docstring** in the style of `hilclaw/hypotheses_file.py`, no longer than it needs to be (it may refer to `hilclaw/spec_file.py` or `hilclaw/hypotheses_file.py` for a convention stated there instead of restating it): which record and decisions it implements (ADR-0071 decisions 1 and 2, by ADR-0029 decisions 2 to 7); the rules `parse` holds and their order; the open top level and the number rule below it; the steps `write` holds; the limits of `write` (ADR-0029 decision 7: POSIX systems with hard links; nothing stated for a network file system, WSL on a Windows drive or native Windows; two writers not prevented); and what it does **not** do: no file read, no directory listed, no "same content", no content composed, no lock, no commit; it does not check what one content does not show (one verdict per `id` of the round's `hypotheses.json`, the value against `expected`, `measured.candidate` within `tested_by`, a *ref* naming an attempt that exists, the base of the comparison), it reads no other version (OD-11), it is no tool, and which agent writes the file, when, and what follows a taken name are open (ADR-0071 Boundaries; OD-23, OD-18, OD-17). No comment beyond the docstrings (CLAUDE.md "코멘트 최소화").
- **No change** to `hilclaw/verdicts.py`, `hilclaw/layout.py`, `hilclaw/hypotheses_file.py`, `hilclaw/spec_file.py` or `hilclaw/once_write.py`. If the executor finds one of them must change, it stops and reports why in `## Result` (BLOCKED "requirement-unclear" if the slice cannot stand without it).

### Tests (CLAUDE.md test rule; DRIVER §5 line 113)

- `tests/test_verdicts_file.py` (new), on the model of `tests/test_hypotheses_file.py`, covering every public function and exception class of the module.
- **Happy**: the ADR-0071 Example, **copied from the record** as bytes with a final line feed, parses to the expected document, gives the expected `final_name` (`<data_root>/runs/20261009t012331z-9f3a6c1e0b7d4a52/rounds/0001/eval/verdicts.json`) and is written there byte for byte; missing directories are created; any member order, white space, CRLF line ends and a missing final line feed are accepted by `parse`; an unknown top-level member of any JSON type, including a number written `-0`, `1.5`, `1e400`, `-3` or above 2**53 - 1, is accepted and returned as parsed; a `hypotheses.json` already in `decision/` of the same round is neither required nor read nor touched.
- **Negative and branch**, one case at least for each rule above: non-`bytes` content (`str`, `bytearray`); BOM; invalid UTF-8; empty content; two JSON texts; `NaN`/`Infinity`; a non-object text (array, number, string); duplicate member names at the top level, inside an unknown top-level member, in a verdict, an evidence entry of each kind and a `ref`; nesting too deep; an integer literal too long for the interpreter; `schema_version` 0, 2 and `MAX_INTEGER` set apart (`UnsupportedVersionError`, also when the rest is invalid), `schema_version` `-0`, `-1`, `MAX_INTEGER + 1`, `1.0`, `"1"`, `true` invalid; a document `validate` refuses (message unchanged, field path present), among them round 0 and a `supported` verdict without a counted comparison; `-0` at `round`, at a `check` `ref.round`, `ref.candidate`, `ref.attempt`, at `measured.round` and at `against.round`; `final_name` with an invalid document, another version, a valid document whose `run_id` is no run directory name (`InvalidPathValueError`), and `data_root` of a wrong type; `write` with every class above, in the order stated (for instance an invalid content with a bad `data_root` raises the content's error), the written-form errors, a missing and a non-directory `data_root`, nothing created in each of these cases; a taken name (with equal bytes and with other bytes; the existing file unchanged; no temporary file left); an `OSError` injected at the creation of a directory, of the temporary file, at the write or flush and at the link (monkeypatch, as `tests/test_hypotheses_file.py` does), the temporary file removed and nothing under the final name; a leftover `verdicts.json.<token>.tmp` of another write is not touched.
- The hard-link tests run where `tests/test_hypotheses_file.py`'s do; follow its skip conditions, if any, rather than adding new ones.
- `hilclaw/` line and function coverage stay ≥ 80% (CI gate); the new module's own coverage should be near 100%. ruff check and format clean.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0220'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0220 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 (the ADR-0071 notice). Skip comments ending `— posted by driver`. An owner comment that objects to ADR-0071 or ADR-0059, or speaks to verdicts, hypotheses or OD-30, makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 or HQ-0021 does not stop this task; name it in `## Result`.
- **Guarded exit**: if a behaviour cannot be implemented without choosing something ADR-0071 or ADR-0029 leaves open (ADR-0071 Boundaries: what follows a taken name, a second write for a round, reading another version, the rounds that never reach evaluate), do not choose it: leave it to the caller, say so in the docstring and `## Result`, or - if the module cannot stand without it - return BLOCKED ("requirement-unclear") with the question written for an HQ.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs it. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0220-verdict-record-file` from `origin/main`; Draft PR titled with `T-0220`; reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; if no reviewer can be spawned: BLOCKED, do not review your own work). Ask the reviewer to check `parse`, `final_name` and `write` against ADR-0071 decisions 1 and 2 and ADR-0029 decisions 2 to 7, and against `hilclaw/hypotheses_file.py` for every behaviour not specific to this record - above all: the version set apart before validation, the open top level (duplicate names still refused there, no number rule there), `-0` refused at every *integer* place below a defined member, the order of checks, nothing created before the last check, no replacing rename, no file read and no cross-file check.
- CI green on all jobs before merge; `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0220`; delete the branch.
- Commit messages in English; executor commits end with the trailer `Task: T-0220` and any attribution trailer the session requires; the commit body has one line on the language choice (Python, as the package) and the public names chosen.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **Size**: if the module heads past 300 lines, shorten the docstring first; if it still does not fit, propose a split in `## Follow-ups` and finish the current scope (DRIVER §5).
- **`## Result`**: do **not** commit it on the task branch. Fill it in on `main` after the merge and leave it uncommitted in the working tree for the driver's wrap-up commit (DRIVER §3-6): PR and merge commit, review rounds, CI run, coverage, the public names chosen, the language line, what is left to the caller and why, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any change to `hilclaw/verdicts.py`, `hilclaw/layout.py`, `hilclaw/hypotheses_file.py`, `hilclaw/spec_file.py`, `hilclaw/once_write.py`, or a shared helper module for the JSON text rules.
- The check between `verdicts.json` and `hypotheses.json` of the same round (one verdict per `id`, the value against `expected`, `measured.candidate` within `tested_by`): a separate follow-up.
- Reading a file of another `schema_version` (OD-11); what follows a taken name or a second write for a round; the rounds that never reach evaluate (ADR-0071 Boundaries; OD-17, OD-23).
- Any other check across files: `instance.json`, result files (PLAN P1-8), the existence of a referenced attempt; the base of the comparison (OD-20, OD-28).
- Building the bytes from a document (no serialiser), any MCP tool, CLI entry, hook, prompt or agent binding (OD-23, OD-18, P2-1, P2-3, P2-4).
- A `basis` kind that cites a verdict, cases (P2-7), injected hypotheses, the S6 metric (P2-8).
- Any ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit.

## Follow-ups

- (planner, code mode) The cross-file check between a parsed `verdicts.json` and a parsed `hypotheses.json` of the same round (ADR-0071 decision 1 line 30 and decision 4: one verdict per `id`, the value against `expected`, `measured.candidate` within `tested_by`), both documents assumed valid; not taken by T-0219.
- (planner, code mode, optional) A shared private helper module for the JSON text rules now duplicated in `spec_file.py`, `hypotheses_file.py` and this module (`_object`, `_nan`, `_literal`, `_unsigned`).
- (planner, document mode, §9) What ADR-0071 leaves to a later record of OD-30 (a `basis` kind citing a verdict, the base of comparison with OD-20 / OD-28, rounds that never reach evaluate).
- (integrator) The "not edited and now less exact" sentences listed in ADR-0071 Consequences.

## Result

DONE. PR https://github.com/myungjoo/HIL-Claw/pull/146, squash-merged as `4155d34`; branch `claude/T-0220-verdict-record-file` deleted.

- **Review**: 2 rounds with a fresh-context `dev-reviewer`, both Approve (comments https://github.com/myungjoo/HIL-Claw/pull/146#issuecomment-6207614987, #issuecomment-6207638158). Round 1's non-blocking point (the `InvalidVerdictFileError` docstring should say "the file-local part of 4") was fixed. The optional point was not taken: the per-place `-0` test checks only the class, not the message. At `round`, `ref.candidate`, `ref.attempt`, `measured.*` and `against.attempt`, `validate` refuses the 0 first. The message is pinned where `-0` would otherwise give a valid 0 (`check ref.round`, `against.round`).
- **CI**: run 38847225408 green on all jobs. `hilclaw/` coverage: lines 5701/5720 = 99.66%, functions 569/569 = 100%; `hilclaw/verdicts_file.py` 79/79 = 100%. ruff check and format clean; 174 tests in `tests/test_verdicts_file.py`.
- **Public names** mirror `hilclaw.hypotheses_file`:
  - `InvalidVerdictFileError(ValueError)`
  - `UnsupportedVersionError(Exception)`
  - `WrittenFormError(ValueError)`
  - `NameTakenError(Exception)`
  - `parse(content)`
  - `final_name(data_root, document)`
  - `write(data_root, content)`

  The private helpers and `_DEFINED` are duplicated, not imported.
- **Language**: Python, as the rest of the package (commit body line).
- **No change** to `verdicts.py`, `layout.py`, `hypotheses_file.py`, `spec_file.py` or `once_write.py`.
- **Left to the caller (ADR-0071 Boundaries; OD-23, OD-18, OD-17)**: what follows a taken name or a second write for a round, reading another version (OD-11), and which agent writes the file and when. All cross-file checks (one verdict per `id` of `hypotheses.json`, the value against `expected`, `measured.candidate` within `tested_by`, whether a referenced attempt exists, the base of the comparison) are left too. The module docstring says so.
- **Issue #5**: no comment after the ADR-0071 notice (checked 2026-10-16), so no objection and no HQ answer. No open PR conflicted.
- **D16**: no `claude` process was started; no hardware or API key was needed.

**Follow-ups:**

- The follow-ups listed above stand unchanged: the cross-file check between `verdicts.json` and `hypotheses.json`, and the optional shared helper module, now with three copies of `_object`, `_nan`, `_literal` and `_unsigned`.
