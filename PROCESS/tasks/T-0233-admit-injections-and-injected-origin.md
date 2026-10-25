---
id: T-0233
title: Validate the optional `instance.json` member `injections` (ADR-0075 decisions 1 and 2) in `hilclaw/instance.py` and admit `origin` `injected` with its member `injection` (ADR-0075 decision 3, in-file rules) in `hilclaw/hypotheses.py`; no cross-file check
phase: P1
status: TODO
commitMode: code
coversReq: [FR-15, FR-17, FR-11, OD-30, "ADR-0075", "ADR-0059", "ADR-0018"]
dependsOn: [T-0232, T-0227]
touchesFiles: [hilclaw/instance.py, hilclaw/hypotheses.py, hilclaw/hypotheses_file.py, hilclaw/instance_file.py, tests/test_instance.py, tests/test_hypotheses.py, tests/test_hypotheses_file.py, tests/test_cases.py, tests/test_instance_file.py]
estimatedSize: {loc: 170, files: 4}   # non-test: about 60-80 lines in instance.py (validator, NamedTuple field, docstrings), 30-40 in hypotheses.py, docstring sentences in hypotheses_file.py and instance_file.py; tests outside the cap (D4)
hq: [HQ-0024]
---
## Why

PLAN P2-6 is open. ADR-0075 (landed `b0b0431` by T-0232) settles injection at instance start: an optional top-level member `injections` of `runs/<run_id>/instance.json` (decisions 1 and 2) and the admission of the `origin` value `injected` in `hypotheses.json` together with one member `injection` that only such entries carry (decision 3). Its Consequences (line 130) cut the code slice: "a validator of `injections` by decisions 1 and 2 beside the other members of `instance.json`; the admission of `injected` with `injection` by decision 3 in `hilclaw/hypotheses.py`; a check of the rules between `hypotheses.json` and `instance.json` of decision 3 … after the model of `hilclaw/hypotheses_cases.py`." This task does the **first two** (the in-file rules of both files). The cross-file check is the next task (Follow-ups). This task ticks **no PLAN checkbox** (P2-6 continues).

Today `hilclaw/instance.py` passes over `injections` as an undefined member (it lands in `others`), and `hilclaw/hypotheses.py` refuses `injected` (`_ORIGINS = ("system",)`). ADR-0075 decision 2 makes a present but invalid `injections` make the whole file invalid, so a reader must now check it.

ADR-0075's objection window runs until 2026-10-23 (§9 notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6215084032). Code built on it inside the window is reverted with it if the owner objects, as T-0227 was built on ADR-0073 inside its window.

Relation to the BLOCKED tasks: T-0225 (HQ-0022) moves the private JSON-text helpers of `hilclaw/hypotheses_file.py`. This task touches only the docstring of that module: do not change `_object`, `_nan`, `_literal`, `_unsigned`, `_MINUS_ZERO`, `_DEFINED`, its imports or public names. `injection` is a *name*, not an integer place, so the `-0` text rule needs no new entry. T-0210 and T-0231 touch no file of this task.

**Editing existing tests is allowed here, but only as stated in criterion 12.** Adding a field to `Instance` changes `Instance._fields` and every positional `Instance(...)` built in `tests/test_instance.py`. Admitting `injected` changes the tests in `tests/test_hypotheses.py` that use it as an unadmitted value. ADR-0075 Consequences line 132 says the code slice changes those tests ("`injected` occurs … in tests that refuse it, which the code slice changes").

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time cap) and §5 (task format, naming convention, size cap, test rules D12).
- `ARCHITECTURE/decisions/ADR-0075-od30-injection-at-instance-start.md`: line 21 (what is cited), decision 1 (lines 23-36), decision 2 (lines 38-45), decision 3 (lines 47-59; the in-file rules are line 50, and lines 51-55 are the cross-file rules this task does **not** implement), decision 5 (lines 67-69), Example (lines 71-109), Consequences (lines 128-133).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: decision 2 (lines 32-50) and decision 3 (lines 51-75).
- `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`: decision 2 (lines 28-41) and decision 4 (lines 57-63). `ARCHITECTURE/decisions/ADR-0020-od8-instance-record-tolerance.md` decision 3 (lines 44-52; a present member must be valid).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` line 34 (*name*, *string*).
- `hilclaw/instance.py`: lines 1-130 (module docstring and conventions), 569-681 (constants, errors, `Instance`), 682-847 (`parse`, `validate` docstrings), 848-885 (`read`), 1185-1243 (`_checked`), 1330-1375 (`_objective`, `_closed`, `_string`).
- `hilclaw/hypotheses.py` (whole file, 279 lines).
- `hilclaw/hypotheses_file.py` lines 1-100 (docstring); `hilclaw/instance_file.py` lines 60-80 (docstring member list).
- `tests/test_instance.py` lines 60-170 (helpers `record`, `doc`, `raw`, `text`) and 225-260 (`__all__` and `_fields` tests); search `*[None] * 11` and `Instance(` for the positional constructions.
- `tests/test_hypotheses.py` lines 1-80 (helpers) and the tests that use `injected` (search `injected`: the parametrized tests at about lines 298 (a `basis` kind, unchanged) and 458 (an `origin`), and `test_injected_origin_is_still_rejected_with_cases_read` at about line 774). `tests/test_hypotheses_file.py` lines 345-365. `tests/test_cases.py` lines 1-140 (examples and helpers).

## Acceptance Criteria

### `hilclaw/instance.py`

1. `validate` and `parse` accept an optional top-level member `injections` (ADR-0075 decisions 1 and 2). When present it is exactly a `list` with **at least one** entry. An empty array is invalid. Each entry is exactly a `dict` with a member `kind` that is `"hypothesis"` or `"material"`. The entry then has exactly that kind's members, no more and no fewer:
   - `hypothesis`: `id`, `kind` and `statement`. `statement` is a *text*: exactly a `str` of at least one character, of any content (ADR-0002 decision 2, as `hilclaw.hypotheses` checks it).
   - `material`: `id`, `kind` and `source`. `source` is a *string* (the module's existing `_string` rule: 1 to 255 printable ASCII characters).
   - `id` is a *name* (`[a-z][a-z0-9_]{0,31}`, exactly a `str`, ADR-0001). It is unique within `injections`. The order of the entries is not checked.
2. Order of checks, so that the first broken rule is deterministic: `injections` comes **after** `objective` in `_checked`, the order in which the records defined the members (extend the "Conventions" bullet). Within the member: the array form, then entry by entry in index order (object, `kind` present, `kind` value, the closed member set of that kind, `id`, then `statement` or `source`), then the uniqueness of `id`. Every error is an `InvalidInstanceError` naming the place in the module's style (`injections`, `injections[<i>]`, `injections[<i>].kind`, `injections[<i>].id`, `injections[<i>].statement`, `injections[<i>].source`). A present but invalid member makes the whole content invalid (ADR-0075 decision 2). So `read` and every `*_of` reader raise for such a file, as they do for any invalid file. No reader repairs it or passes it over.
3. `injections` is added to `_DEFINED`, so it no longer appears in `others`. `Instance` gains a field `injections` placed **directly before `others`**. Its value is the parsed `list` of the member, or `None` for a content without it. `None` says only that the content records no injected input (ADR-0075 decision 2, "Absent"). No default is substituted. `others` stays the last field. No `injections_of` reader is added: ADR-0075 names no reader, and the reader that needs the member is built later (decision 2, "Versions").
4. `SCHEMA_VERSION` stays 1, and so does the layout version stated through it (ADR-0075 decision 2, "Versions"). Nothing between files is checked: the hypothesis records of the run are not opened.
5. Docstrings: the module docstring adds ADR-0075 to the title list and the list of records, with one short paragraph on the member written in the style of the others. The "twelve records" and "eleven records" counts and the member lists in `validate`/`parse`/`Instance` include the new member. Public names other than the new `Instance` field do not change.

### `hilclaw/hypotheses.py`

6. `_ORIGINS` admits `"injected"` (ADR-0075 decision 3). An entry whose `origin` is `injected` has exactly the six members of ADR-0059 decision 3 **and** `injection`, a *name* (the existing `_name` rule). An entry whose `origin` is `system` has no `injection`: the existing "unknown member" refusal reports it. An `injected` entry without `injection` is refused with `hypotheses[<h>].injection: required member is missing`. Every other rule binds an `injected` entry as it binds a `system` one: `basis`, `expected`, `tested_by` and `id` uniqueness. The member set is chosen from `origin` only when `origin` is present and is one of the admitted values. Otherwise the check proceeds so that the existing error for a missing or not admitted `origin` is still reported at `hypotheses[<h>].origin` or as a missing member. The messages of every existing refusal of a `system` entry stay as they are.
7. Nothing between files is checked (ADR-0075 decision 3, "Checked by no write"). That covers whether `injection` names an entry of the run's `injections`, the equality of `statement` with a written hypothesis, the `external` basis matching a material's `source`, and that no two entries name the same written hypothesis. Several entries of one file may carry the same `injection`. `SCHEMA_VERSION` stays 1 (ADR-0075 decision 3, "Version").
8. Docstrings: the module docstring states the admission with a pointer to ADR-0075 and drops the sentence that refuses `injected`. Its "Not checked" paragraph gains the rules between files of ADR-0075 decision 3. `validate`'s docstring names the `injection` member. The class docstring of `InvalidHypothesisRecordError` names ADR-0075 among the rules. Public names do not change.

### Docstring-only modules

9. `hilclaw/hypotheses_file.py`: where the docstring says what makes the document valid (around lines 18-20 and 81-85), include ADR-0075's in-file rules for `injected`, and name its rules between files among those not checked. No code change, and nothing of the T-0225 helpers changes.
10. `hilclaw/instance_file.py`: the docstring sentence that lists the members a valid content may lack (lines 66-72) includes `injections` (ADR-0075) and its count. No code change. A valid content with `injections` is written as it is (no member put in or taken out).

### Tests (D12: happy, error, branch and negative cases; every public function touched)

11. New tests:
    - `tests/test_instance.py`:
      - Happy: the `injections` member of the ADR-0075 Example placed in the module's valid test document parses, and `Instance.injections` equals it. Do not use the Example's `hw_profile`, which is a placeholder and is not valid. One entry of each kind alone is valid. Ids that differ only in a later character are valid.
      - Absence: a content without the member gives `injections` `None` and validates as before.
      - Negative: `injections` not an array (reuse the module's non-array values), an empty array, an entry that is not an object, a missing `kind`, `kind` of another value (`"case"`, `"Hypothesis"`, `""`, `None`, `1`), a missing member per kind, an unknown member per kind (including `source` on a `hypothesis` entry and `statement` on a `material` entry), a bad `id` (empty, uppercase, leading digit, hyphen, 33 characters, non-`str`), a bad `statement` (empty, non-`str`), a bad `source` (empty, 256 characters, a non-ASCII character, a control character, non-`str`), and a duplicate `id` across kinds. Each is refused with its place.
      - Through `read`: a file with an invalid `injections` makes `read` and one `*_of` reader (for example `hw_profile_of`) raise `InvalidInstanceError`.
      - Branch: the order of criterion 2. A document breaking `objective` and `injections` reports `objective`. An entry breaking its member set and its `id` reports the member set. A duplicate `id` is reported after every entry's form is valid.
    - `tests/test_hypotheses.py`:
      - Happy: the round-1 `hypotheses.json` of the ADR-0075 Example, copied verbatim from the record as `ADR_EXAMPLE` copies ADR-0059's, is valid. An `injected` entry with an `external` or a `case` basis is valid, the latter with `cases_read`. Two entries with the same `injection` are valid.
      - Negative: `injected` without `injection`, a `system` entry with `injection`, and a bad `injection` value (reuse `BAD_NAMES`).
      - Branch: an `injected` entry that also breaks `basis` reports the error in the module's existing order.
    - `tests/test_hypotheses_file.py`: a valid file holding an `injected` entry parses to its document, and the refusal cases keep their message parity with `validate`.
    - `tests/test_cases.py`: a case whose hypothesis copy holds an `injected` entry with `injection` is valid (ADR-0075 decision 3, "What reaches the case file"). A copy holding an `injected` entry without `injection` is refused with the `hypothesis_record.` prefix.
    - `tests/test_instance_file.py`: a valid content holding `injections` is written byte for byte. A content holding an invalid `injections` is refused before anything is written.
12. Allowed edits of existing tests (no other existing test is weakened or removed):
    - In `tests/test_instance.py`, `Instance._fields` gains `injections` before `others`, and every positional `Instance(...)` gains the extra `None` (for example `*[None] * 11` becomes `*[None] * 12`).
    - In `tests/test_hypotheses.py`:
      - Drop `"injected"` from the parameters of `test_origin_not_admitted_is_rejected` (about line 458). The `basis` kind test at about line 298 keeps its `"injected"` parameter: no `basis` kind of that name is admitted.
      - Rewrite `test_injected_origin_is_still_rejected_with_cases_read` into a test that an `injected` entry without `injection` is refused under `cases_read`.
    - In `tests/test_hypotheses_file.py`, the parameter `(("hypotheses", 0, "origin"), "injected")` (line 353) may stay: it is still refused, for the missing `injection`. Change it only if its parity check fails.
13. `ruff check`, `ruff format --check` and the whole `pytest` suite pass locally and in CI. Line and function coverage of `hilclaw/` stay ≥ 80%.
14. `Result` names the language (Python, as the modules) with one line of reason.

## Out of Scope

- The rules between `hypotheses.json` and `instance.json` of ADR-0075 decision 3 (lines 51-55), and any new module for them. That is the next task.
- Any reader `injections_of`, any user-facing input form, and anything that writes `instance.json` with injections (OD-8 ⑰, OD-23).
- Any rule of order, share or distribution of injected and system hypotheses (ADR-0075 decision 4, Boundaries), and injection at a gate or during a run.
- Any `schema_version` change. Any change to `verdicts.py`, `verdicts_file.py`, `cases.py`, `cases_file.py`, `case_lookup.py`, `hypotheses_cases.py`, `layout.py`, or to the private JSON-text helpers and imports of any `*_file.py` module (T-0225, HQ-0022).
- Any edit under `ARCHITECTURE/`. The "not edited and now less exact" list of ADR-0075 Consequences and its R7 nits are a separate doc follow-up.
- Starting `claude` in any form (D16).

## Follow-ups

- Cross-file check of ADR-0075 decision 3 (code), modelled on `hilclaw/hypotheses_cases.py`, for a reader that holds a round's `hypotheses.json` and the run's `instance.json`. It checks:
  - `injection` names an entry of `injections`;
  - a `hypothesis`-kind input gives an entry an equal `statement`, and no other entry of the same file names it;
  - a `material`-kind input gives an entry at least one `external` basis whose `source` equals the material's.
- ADR-0075 "not edited and now less exact" list and R7 nits (doc). The register row for the reference input at start is an integrator follow-up.

## Result

**BLOCKED** (requirement unclear: the allowed test edits of criterion 12 are insufficient). No PR, no review round, nothing landed.

- Work so far is on branch `claude/T-0233-admit-injections-and-injected-origin` (commit `5a3d147`, pushed; no PR): the code and docstrings of criteria 1-10 in `hilclaw/instance.py`, `hilclaw/hypotheses.py`, `hilclaw/hypotheses_file.py` and `hilclaw/instance_file.py`, and the criterion-12 edits of `tests/test_instance.py` (`_fields`, the extra `None` in all 41 positional `Instance(...)`). The new tests of criterion 11 and the two `tests/test_hypotheses.py` edits of criterion 12 are not written yet. `ruff check` and `ruff format --check` pass.
- The block: with the new field, the whole suite has 15 failures. 2 are the `tests/test_hypotheses.py` tests that criterion 12 allows to change. The other 13 are `test_any_place_of_the_objective_among_the_twelve_other_members[0-12]` in `tests/test_instance.py` (about line 8163): it builds `expected = Instance(*STATED_BESIDE_THE_OBJECTIVE, OBJECTIVE, None, {})` (the allowed extra `None`) and then asserts `assert None not in expected`, which now fails because `injections` is `None` for a content without the member (criterion 3). Making it pass needs an edit that criterion 12 does not list, e.g. `assert None not in expected[:13]` (the same form as `assert None not in expected[:12]` at about line 7445), which keeps the check that every stated member is not `None`. The executor stopped rather than exceed criterion 12.
- Question for the owner: may criterion 12 also allow that assertion to be limited to the fields before `injections` (`expected[:13]`)? If yes, the task resumes on the existing branch.
- Language: Python, as the modules extended (recorded in the branch commit body).
