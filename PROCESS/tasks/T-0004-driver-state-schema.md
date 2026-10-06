---
id: T-0004
title: Add the JSON Schema for PROCESS/STATE.json and a standard-library validator
phase: P0
status: IN_PROGRESS
commitMode: code
coversReq: ["DRIVER §2·§4·§8", "#5 D12"]
dependsOn: [T-0002]
touchesFiles: [PROCESS/STATE.schema.json, hilclaw/driver_state.py, tests/test_driver_state.py]
estimatedSize: {loc: 250, files: 2}   # non-test: schema + validator; the test file is excluded from the cap (D4)
hq: []   # standard library only, so no "new external dependency"; the D12 test exception ① makes tests mandatory here
---
## Why
`PROCESS/STATE.json` is the driver's only entry point (DRIVER §2) and every iteration rewrites it at least twice (lock commit §3-4, wrap-up §3-6), without review (D8). Its shape is defined only by the §2 field table in prose ("until the P0-4 JSON Schema exists, this table defines it"), so nothing catches a malformed lock, a missing `issueComment`, a misspelled field or a bad timestamp before it lands on `main` and confuses the next iteration (lock validity §4, HQ answer detection §3-2). PLAN P0-4 asks for the table to be mechanised as a JSON Schema plus a validator. D12 (CLAUDE.md test rule ⑤) names this validator as one of the two tool-code exceptions whose tests are **mandatory**.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §2 (lines 33-60: modes, the `PROCESS/STATE.json` field table — the specification this task encodes), §4 (lock: owner format `<hostname>:<session-id or pid>`, `acquiredAt` + `ttlMinutes`), §8 (humanQuestions fields, `issueComment` may be null until the mirror URL is filled, §3-2 / §3-4), §3 "BLOCKED 사유" paragraph
- CLAUDE.md — 상시 규칙: "세 층 모델" and "도구 계층 언어 정책" (this is 2nd-layer code: "스키마 검증"), "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성"), "테스트 규칙" ①-⑤ (⑤ names this validator as a mandatory-test exception), "코멘트 최소화", "미결은 발명하지 않는다"; "현재 프로젝트 상태 주의사항: CI 미구축"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow (steps 4, 9, 13, 15)
- .claude/skills/dev-code-review/SKILL.md — line 13 (test rules, mandatory-test exceptions), line 17 (no invented decisions)
- PROCESS/PLAN.md — P0-4, and P0.5-2 / P0.5-3 (test-existence check and coverage gate, deliberately left to later items)
- PROCESS/tasks/T-0002-python-project-config.md — `## Result`: conventions already chosen (no build backend, `pythonpath = ["."]`, ruff defaults with `target-version = "py311"`, tests at repository root `tests/`, `requires-python >= 3.11`, the three local verification commands)
- PROCESS/tasks/T-0003-ci-skeleton.md — status BLOCKED (HQ-0001): CI is still not built, so verification stays local
- Existing files: `PROCESS/STATE.json` (the live instance; read it, never edit it), `pyproject.toml`, `hilclaw/__init__.py`, `tests/test_version.py` (style reference), `.editorconfig` (2-space indent for `*.json`, 4 for `*.py`), `.gitattributes`, `.claude/settings.json` (allowlist)

## Acceptance Criteria
Nothing in the repository fixes the schema file location, the module name, the validation approach, the public API, the CLI shape or the timestamp form. None of these is an owner-only decision (DRIVER §9) or a registered OD. They are **conventions chosen by this task, provisional**: follow the criteria below and state each choice with one line of reason in the commit body and in `## Result`. Do not present them as requirements. Where the §2 table is silent (see "Not encoded" below), do not invent a rule.

Dependency constraint:
- **Standard library only.** The `jsonschema` package is not installed, and adding any third-party package (runtime or dev group) is the BLOCKED reason "new external dependency" (CLAUDE.md A-13), which the driver cannot decide. Do not add it to `pyproject.toml`, do not `pip install` it. If the task turns out to be impossible without a new package, return BLOCKED with the exact question for the owner.
- Code must run on CPython 3.11 (the `requires-python` floor): no 3.12+ syntax or stdlib features. It is verified locally on 3.14 only (CI is blocked); say so in `## Result`.

Approach (provisional, chosen by the planner): **(a) a minimal interpreter of exactly the JSON Schema keyword subset the schema uses.** Reason: the schema file is the single source of truth, so the schema and the validator cannot drift (approach (b), hand-coded checks plus a drift test, duplicates the field table in Python); the same schema file can later be fed unchanged to the `jsonschema` package if the owner adopts it (Follow-ups). The interpreter must **reject** any keyword it does not implement instead of silently ignoring it.

Schema (new, `PROCESS/STATE.schema.json`, next to the instance it describes):
- JSON Schema draft 2020-12 (`"$schema": "https://json-schema.org/draft/2020-12/schema"`), with `$id` or `title`/`description` as annotations only. 2-space indent, LF, final newline (`.editorconfig`).
- Top level: `type: object`, `required` = all nine §2 fields, `additionalProperties: false`, and exactly these `properties`:
  - `schema_version`: `const: 1` (integer).
  - `phase`: `enum: ["P0", "P0.5", "P1", "P2", "P3"]`.
  - `currentTask`, `nextTask`: `type: ["string", "null"]`, `pattern: "^T-\\d{4}$"`.
  - `lock`: `type: ["object", "null"]`; when an object: required `owner` (string, `pattern: "^[^:]+:.+$"` — §4 `<hostname>:<id>`), `acquiredAt` (timestamp, below), `ttlMinutes` (integer, `minimum: 1`); `additionalProperties: false`.
  - `humanQuestions`: `type: array`, `items` = object with required `id` (`pattern: "^HQ-\\d{4}$"`), `taskId` (`pattern: "^T-\\d{4}$"`), `reason` (string), `question` (string), `askedAt` (timestamp), `issueComment` (`type: ["string", "null"]`); optional `resolvedAt` (timestamp) and `decision` (string); `additionalProperties: false`.
  - `counters`: object, required `iterations`, `tasksDone`, `tasksBlocked`, `reviewRoundsTotal`, each integer `minimum: 0`; `additionalProperties: false`.
  - `lastIteration`: `type: ["object", "null"]`; when an object: required `at` (timestamp), `owner` (same pattern as `lock.owner`), `taskId` (`pattern: "^T-\\d{4}$"`), `outcome` (string); `additionalProperties: false`.
  - `notes`: string.
- Timestamps (`lock.acquiredAt`, `askedAt`, `resolvedAt`, `lastIteration.at`): `type: string`, `format: "date-time"`, and `pattern: "Z$"`. Provisional: §2 says "ISO-8601 UTC"; every value the driver writes uses the `Z` suffix, and one canonical form keeps string comparison and grepping simple. `+00:00` is therefore rejected; record this choice.
- **`"$schema"` key inside `PROCESS/STATE.json`: out of scope, and the schema does not allow it.** Reason: the §2 table does not list it, the top level stays `additionalProperties: false` so a stray key is caught, and the validator is always invoked with an explicit schema, so no in-file discovery is needed. Adding it would be a DRIVER §2 (doc-mode) change plus a schema change (Follow-ups).
- Not encoded (the §2 table is silent; do not invent): an `enum` for `humanQuestions[].reason` (the live value `permission-denied` is not one of the A-13 reasons verbatim) or for `lastIteration.outcome`; `minLength` on free-text strings; uniqueness of HQ ids; and cross-field invariants (e.g. `currentTask` non-null ⇔ `lock` non-null, `resolvedAt` ⇔ `decision`). These go to Follow-ups for a DRIVER §2 decision.

Validator (new, `hilclaw/driver_state.py`; Python because it uses the stdlib `json`/`re`/`datetime` and the rest of the tool package is Python — one line in the commit body and `## Result`):
- Module docstring and short docstrings on the public functions (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names):
  - `SchemaError(ValueError)` — raised for a defect in the **schema** (unsupported keyword, unsupported `format` value, unknown `type` name), never for a defect in the instance.
  - `load_schema(path=None) -> dict` — reads the schema; default path `PROCESS/STATE.schema.json` resolved relative to the repository root (`Path(__file__).resolve().parent.parent`), not the current working directory. Provisional coupling to the repo layout; acceptable because the package is not installable (T-0002).
  - `validate(instance, schema=None) -> list[str]` — returns **all** problems, empty list if valid; each message names the location as a JSON path (e.g. `$.lock.ttlMinutes`, `$.humanQuestions[0].askedAt`) and the violated keyword. Does not mutate `instance`. `schema=None` uses `load_schema()`.
  - `main(argv=None) -> int` — CLI behind `python -m hilclaw.driver_state [PATH]`; `PATH` defaults to `PROCESS/STATE.json` at the repository root. Exit 0 and a one-line OK message on stdout when valid; exit 1 with one problem per line on stderr when invalid, and also exit 1 (one-line message, no traceback) when the file is missing or is not valid JSON. Use `argparse` (its own usage error exit 2 is fine). Ends with `if __name__ == "__main__": raise SystemExit(main())`.
- Supported keywords, exactly: annotations `$schema`, `$id`, `title`, `description` (ignored); `type` (a name or an array of names among `object`, `array`, `string`, `integer`, `null`; `integer` means a Python `int` that is **not** `bool`); `properties`; `required`; `additionalProperties` (boolean only); `items` (a single schema); `enum`; `const` (compare type-strictly so `true` does not equal `1`); `pattern` (`re.search`, i.e. unanchored, as JSON Schema specifies — the schema anchors its own patterns); `format` (only `"date-time"`: RFC 3339 shape `YYYY-MM-DDTHH:MM:SS[.fff](Z|±HH:MM)` checked by regex, then calendar validity via `datetime.fromisoformat`, so `2026-13-01T00:00:00Z` fails); `minimum`. Any other keyword anywhere in the schema → `SchemaError`.
- When `type` fails, do not report the keywords that only apply to the other type (one message per real problem).
- Size: non-test code ≤ 300 LOC across ≤ 5 files; expected about 120 lines of schema JSON + about 130 lines of Python, 2 files. If the schema alone threatens the cap, use `$defs`/`$ref` only if you also implement them in the interpreter and test them; otherwise propose a split in Follow-ups.

Tests (new, `tests/test_driver_state.py`; mandatory per D12 exception ①; tests are excluded from the size cap):
- happy:
  - the **committed** `PROCESS/STATE.json`, located relative to the test file, validates with no problems. It must pass in every driver state — note that while this task runs, `main` has `lock` set, `currentTask: "T-0004"` and possibly a filled `issueComment`.
  - an in-test valid instance that exercises every optional branch: `lock` object, non-null `currentTask`/`nextTask`, a resolved HQ with `resolvedAt` and `decision`, an HQ with `issueComment: null`, `lastIteration: null`, empty `humanQuestions`, fractional-second timestamp.
  - the schema's top-level `properties` keys and `required` both equal the nine §2 field names hard-coded in the test (guards against a field added to one place only).
- negative, each asserting the returned messages name the right path (one test per bullet or a parametrised table):
  - wrong type (e.g. `counters.iterations` as `"3"`, `ttlMinutes` as `true`, `notes` as `null`, top level not an object)
  - missing required field (top level, inside `lock`, inside an HQ — e.g. `issueComment` absent)
  - bad enum (`phase: "P4"`) and bad const (`schema_version: 2`)
  - bad id pattern (`currentTask: "T-4"`, HQ `id: "HQ-1"`, `lock.owner` without `:`)
  - bad timestamp (not a date, invalid calendar date, missing timezone, `+00:00` instead of `Z`, date only)
  - `minimum` violation (`tasksDone: -1`, `ttlMinutes: 0`)
  - extra property (top level, e.g. a `"$schema"` key; inside `lock`; inside an HQ)
  - several problems at once → all are reported (length ≥ the number injected)
  - `validate` does not mutate its input
- schema errors (`SchemaError`): an unsupported keyword (e.g. `oneOf`), an unsupported `format` (e.g. `email`), an unknown `type` name — using small in-test schemas.
- `load_schema`: default path loads a dict with the draft 2020-12 `$schema`; an explicit path works; a missing path raises.
- `main`: valid file → 0; invalid file → 1 with problems on stderr (`capsys`); missing file → 1; non-JSON file → 1 (use `tmp_path`); no argument → validates the committed `PROCESS/STATE.json` → 0. One `subprocess` run of `python -m hilclaw.driver_state` (with `sys.executable`, `cwd` at the repository root) to cover the `__main__` entry.
- Coverage is not measured in this task (`pytest-cov` belongs to P0.5-3 and would be a new dependency); the tests must still reach every keyword handler and every `main` exit path — say in `## Result` how you checked (e.g. by reading, or the stdlib `python -m trace --count`, optional).
- Do not add tests for `tests/test_version.py`, for `pyproject.toml` or for any CI file (test rule ⑤).

Local verification (CI not built — run before the commit and again before the merge, paste the summary lines into `## Result`):
- `python -m pytest` exits 0 (all tests, including the existing 2), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0.
- `python -m hilclaw.driver_state` exits 0 on the live file.
- `git ls-files --eol PROCESS/STATE.schema.json hilclaw/driver_state.py tests/test_driver_state.py` shows `i/lf` for all three.
- `git diff origin/main --stat` lists only the three files in `touchesFiles`; in particular `PROCESS/STATE.json` is **unchanged** (the driver owns it) and `hilclaw/__init__.py` / `pyproject.toml` are unchanged.

Process:
- Code mode although `PROCESS/STATE.schema.json` is a `PROCESS/` file: it ships together with `hilclaw/` code and tests, and a mixed change is code mode (CLAUDE.md A-13, dev-item-address step 9).
- Branch `claude/T-0004-driver-state-schema`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0004`; executor commits end with the trailer `Task: T-0004`.
- Reviewer cycle via a fresh-context sub-agent running dev-code-review (≤ 7 rounds); CI step = the local reruns above (`gh pr checks` will report no checks — that is expected while T-0003 is blocked).
- Squash-merge per A-13 with `Task: T-0004` as the last line of the PR body, using `gh pr merge --squash --body "<that body>"`; delete the branch.
- Commit body: the provisional choices (schema location, approach (a), keyword subset, `Z`-only timestamps, `$schema` key not allowed in the instance, module name / API / CLI exit codes, default paths relative to the repository root) with one line of reason each, and the language line.
- Allowlist notes (`.claude/settings.json`; do not edit it): `Edit(hilclaw/**)`, `Edit(tests/**)`, `Edit(PROCESS/**)` cover the three files; `python *`, `pytest *`, `ruff *`, `gh pr *`, `gh api *` and the listed `git` verbs cover the rest. `git revert` and `gh run *` are not allowlisted. If any needed call is denied in a non-interactive session, return BLOCKED rather than working around it through another shell command.

## Out of Scope
- Editing `PROCESS/STATE.json` (driver-owned), DRIVER.md, PLAN.md, CLAUDE.md or the skills (document mode, separate changes — see Follow-ups).
- Wiring the validator into the driver procedure (§3-4 / §3-6), a git hook, or CI (T-0003 / P0.5).
- Any third-party package (`jsonschema`, `fastjsonschema`, `pydantic`, …), `pytest-cov`, a build backend or console-script entry point.
- JSON Schema keywords beyond the subset above (`$ref`/`$defs` unless needed for the size cap, `oneOf`/`anyOf`/`if`, `minLength`, `uniqueItems`, …), cross-field invariants, enums the §2 table does not give.
- Rejecting duplicate keys in the JSON file (`json.load` keeps the last one) — Follow-ups.
- The runtime `runs/<run_id>/STATE.json` schema (P1-8, OD-8).

## Follow-ups
- (owner option) Adopt the `jsonschema` package (new external dependency → owner decision) and replace the subset interpreter; `PROCESS/STATE.schema.json` is written to be reusable unchanged.
- (doc mode, after this lands) DRIVER §2: the table text says it defines the fields "until the P0-4 JSON Schema exists"; point it at `PROCESS/STATE.schema.json` as the canonical definition and state that a field change edits both in the same change.
- (doc mode, separate task) DRIVER §3-4 / §3-6 / §4 lock extension: run `python -m hilclaw.driver_state` before every state commit and refuse to push an invalid state; decide what the driver does on failure (BLOCKED reason or abort).
- (DRIVER §2 decision) Whether to encode: an enum for `humanQuestions[].reason` and `lastIteration.outcome`, HQ id uniqueness, `currentTask` ⇔ `lock`, `resolvedAt` ⇔ `decision`, accepting `+00:00`, and an in-file `"$schema"` key.
- (P0.5-2) The module-to-test mapping: this task uses `hilclaw/driver_state.py` → `tests/test_driver_state.py`.
- (P0.5-3) The coverage gate will measure this module for the first time; the tests here should already reach ≥ 80% line/function.
- (later) Duplicate-key rejection via `object_pairs_hook`; packaging the schema inside `hilclaw/` once the package becomes installable.

## Result
- (to be filled by the executor)
