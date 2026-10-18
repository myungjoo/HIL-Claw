---
id: T-0309
title: Add the request check, input schema and descriptions of sim.run and board.run (code slice of ADR-0106)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0308]
touchesFiles: [hilclaw/run_definition.py, hilclaw/run_identity.py, tests/test_run_definition.py, tests/test_run_identity.py]
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

ADR-0106 (landed as 28cd947 by T-0308) closes the request member list of `sim.run` and `board.run` at the five members of ADR-0062 decision 4 (`run_id`, `round`, `candidate`, `attempt`, `execution`), says that any other member is refused as `invalid_request` in moment ①, fixes one input schema for both tools, and fixes what each description must tell. Its Consequences name the code slice this task is: "the refusal of a member no record names in ① and the two input schemas and descriptions, with tests for each row of the Walk-through, at both tools". `correctness.check` landed the same item as `hilclaw/check_identity.py` (`MEMBERS`, `check`) and `hilclaw/check_definition.py` (`input_schema`, `DESCRIPTION`); this task does the same for the run tools in one new module, without registering either tool (registration stays open: ADR-0106 Boundaries). This is a step of PLAN P1-1.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention, size cap, D12 test rules).
- `CLAUDE.md` (standing rules: comment minimisation, layer-2 language policy, test rules, branch/merge procedure for code mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md` — all of it; decisions 2 to 5, the Walk-through table and the Consequences items "The code slice this record makes possible" and "Docstring sentences that become less exact" are the specification.
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md` decisions 3, 4 and 6 (the five members, the `step` values, the order of moments ① to ⑦).
- `hilclaw/check_identity.py` (whole; the pattern for `MEMBERS`, `check`, the message of a member no record names, the treatment of non-`str` keys and non-`dict` requests).
- `hilclaw/check_definition.py` lines 1-115 (the pattern for `input_schema` and `DESCRIPTION`; the definition/table/registry part is NOT to be copied).
- `hilclaw/run_identity.py` (whole) and `tests/test_run_identity.py` (whole).
- `hilclaw/journaled_tool.py` lines 1-110 and 139-330 (`tool_function`, the frame check `_checked`, where `check(request)` is called relative to the data-root source).
- `tests/test_check_definition.py` lines 1-170 and `tests/test_check_identity.py` (test patterns), `tests/test_journaled_tool.py` lines 60-260 (helpers for a data root with a run, `store`, `new_root`, `root`).
- `tests/test_default_registry_schemas.py` lines 1-60 (the eight keywords of ADR-0077 decision 4; read only, do not edit).
- `hilclaw/keys.py` (`MAX_INTEGER`), `hilclaw/tools.py` lines 1-110 (`ToolFailure`, `KIND_INVALID_REQUEST`).

## Acceptance Criteria

1. **New module `hilclaw/run_definition.py`** (Python, the language of the rest of `hilclaw/`), with a module docstring in the style of `check_definition.py` citing ADR-0106 and stating which choices are the module's own. Public names, exactly:
   - `MEMBERS`: the tuple `("run_id", "round", "candidate", "attempt", "execution")` (ADR-0106 decision 2), built from `hilclaw.run_identity.NUMBERS`.
   - `check(request)`: returns `None` for a `dict` whose keys are all exactly members of `MEMBERS` (type exactly `str`, compared as is, case-sensitive); otherwise raises `tools.ToolFailure` of kind `invalid_request`. It refuses a key not in `MEMBERS` whatever its value (`None` included), a key that is not exactly `str` (a `str` subclass included) without calling any code of it, and a `request` that is not exactly a `dict`. It does not look at any value and does not modify the request. Its message names the refused member by the name the request gave it when that name is 1-32 characters of `[A-Za-z0-9_.-]`, else a fixed text such as `(a name not shown)`; it goes on to name the five members; it shows nothing of the value of the member, not even its type; it is at most 160 characters. Of several members no record names, the first in request order is named.
   - `input_schema()`: returns a new `dict` at each call, equal to the schema of ADR-0106 decision 4, with `hilclaw.keys.MAX_INTEGER` as the bound, `required` equal to `list(MEMBERS)` and `"additionalProperties": False`; one JSON object in the strict sense of `hilclaw.tools.check_json_object`. It uses only keywords of ADR-0077 decision 4.
   - `SIM_DESCRIPTION`, `BOARD_DESCRIPTION`: non-blank texts that each tell (ADR-0106 decision 5) (i) the point the tool times (sim / board) and that no member states it; (ii) that the tool is journaled — an ended identity is answered with the stored outcome, an open one gets `step_open`, a new timing run of the same attempt at the same point uses a higher `execution`; (iii) that the run's own `instance.json` supplies the dimensions, `n_max`, the objective and the bound, and that the seed and the settings are no members of the request; (iv) that the request has exactly the five members and any other, `point` among them, is refused as `invalid_request`; (v) that a number of `round`, `candidate`, `attempt` or `execution` written with a fraction or an exponent (`1.0`, `1e0`) is refused although the schema admits it. They differ in (i). They state no dimension, `n_max`, bound, seed or setting as a value and no rule of who may raise `execution` or which execution counts.
   - The module registers nothing, builds no tool definition, binds no backend, seed source or tool function, reads no file and imports only from `hilclaw` (e.g. `keys`, `run_identity`, `tools`) and `re` if needed.
2. **`hilclaw/run_identity.py`**: only the module docstring sentence "It does not close the member list of a request, and what is done with a member no record names, a member ``point`` among them, is a later slice's (decision 4)." is rewritten in place so that it is true: the member list and the refusal of other members are ADR-0106's and live in `hilclaw.run_definition`. No code of `run_identity.py` changes; its public names stay as they are.
3. **New `tests/test_run_definition.py`** (D12: happy, error, branch and negative cases; every public name):
   - `MEMBERS` value and type; `check` accepts the Walk-through request `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1}` and returns `None` without modifying it.
   - `check` refuses, as `invalid_request`, each name listed in ADR-0106 decision 3 (`point` with `"sim"`, `"board"` and other values, `seed`, `n_max`, `bound`, `objective`, `sample_form`, `m`, `k`, `n`, `shape`, `op_signature`, `step`, `hw_profile`, `data_root`, `Execution`, `run-id`), with values including `None`; a non-`dict` request; a non-`str` key, a `str`-subclass key and a hostile key/value object whose `__eq__`/`__hash__`/`__str__`/`__repr__` raise (none called). Messages: name shown or the fixed text for a long or control-character name, the five members named, no value or type shown (marker string test), length ≤ 160; first unnamed member in order is the one named.
   - Each row of the ADR-0106 Walk-through, **at both tools**: build `hilclaw.journaled_tool.tool_function(step=run_identity.STEP_SIM_RUN or STEP_BOARD_RUN, numbers=run_identity.NUMBERS, source=<counting source>, check=run_definition.check, perform=<stub>)`. A refused row yields `invalid_request` with the source asked zero times and `perform` not called (nothing asked, read or appended); `"execution": 1.0` is refused in ①; `"Execution": 1` in place of `"execution"` is refused; the accepted request passes ① (the source is asked). The rows "again after the first call ended" use a real data root via the helpers of `tests/test_journaled_tool.py` (import or replicate them in the test file): the plain request returns the stored result, and the same request with `"seed": 7` added is `invalid_request`, not the stored result, with no line appended.
   - For each Walk-through request, assert whether the schema admits or refuses it as the table's "Schema" column says (a small in-test evaluator of the seven keywords used is enough; do not edit `tests/test_default_registry_schemas.py`).
   - `input_schema()` equals the literal schema of ADR-0106 decision 4; a fresh object each call (mutating one does not change the next); takes no argument; passes `tools.check_json_object`; uses only the keywords of ADR-0077 decision 4; is accepted by `tools.ToolRegistry().register(...)` together with each description (on a throwaway registry, not the default one).
   - Descriptions: assert terms for each of (i)-(v) (e.g. `sim`/`board` respectively, `step_open`, `execution`, `instance.json`, `seed`, every name of `MEMBERS`, `point`, `invalid_request`, `fraction`, `exponent`) and that the two texts differ.
   - The module imports only what it names, has exactly the public names above, and `hilclaw.tools.default_registry` still holds neither `sim.run` nor `board.run`.
4. `tests/test_run_identity.py` is edited only if a test there breaks because of criterion 2 (it should not: its string checks look at code strings, not the docstring).
5. `pytest`, `ruff check` and `ruff format --check` pass; line and function coverage of `hilclaw/` stay ≥ 80%. No new dependency, no data-plane schema change, no change to any `ARCHITECTURE/` file, to `hilclaw/tools.py`, to `hilclaw/journaled_tool.py`, to `hilclaw/hw_tool.py` or to CI.
6. Code-mode flow per CLAUDE.md A-13: branch `claude/T-0309-run-tools-request-check-and-schemas`, Draft PR whose title contains `T-0309` and whose body ends with `Task: T-0309`, reviewer cycle, CI green, squash-merge with `--body`, branch deleted. The commit body records the language choice in one line.

## Out of Scope

- Registering `sim.run` or `board.run` in `default_registry`, any `ToolDefinition`/`definition()` function, a backend table, a seed source binding, or the tool function that joins the run tools' modules (ADR-0106 Consequences, "What still stands between that slice and two registered tools").
- Adding the run tools to `tests/test_default_registry_schemas.py` (that happens with registration, ADR-0077 decision 3).
- Any answer to OD-18 sub-questions ⑤ (second half), ⑧, ⑲ (나)-(라), ⑳; any reduced schema.
- Editing the "less exact" sentences of earlier ADRs listed in ADR-0106 Consequences (a separate doc task).
- `hilclaw/clang_build.py` and `tests/test_clang_build.py` (open PR #179).

## Follow-ups

- Doc task: the "Not edited and now less exact" sentences of ADR-0062, ADR-0061, ADR-0063 to ADR-0067, ADR-0069 and ADR-0070 listed in ADR-0106 Consequences, if the integrator decides to touch them.
- The joining tool function of the run tools and their registration (needs ⑲ (나) and the backend/seed binding records).

## Result
