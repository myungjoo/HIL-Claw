---
id: T-0530
title: Write the six bf16 instance documents from the owner's values and state the P2-15 steps in the README
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [OD-31, C-6, FR-1, FR-5, "PLAN P2-15", D26]
dependsOn: [T-0528, T-0529]
touchesFiles:
  - hilclaw/model_instances.py
  - tests/test_model_instances.py
  - README.md
estimatedSize: {loc: 250, files: 2}   # test code is outside the cap
hq: []
---
## Why

**State.** For P2-15 the owner must first run one instance per kind on the runtime machine: `gemm`, `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and `sdpa_kv_cache` at `bf16`. `python -m hilclaw.new_run <file>` takes a complete `instance.json` document, which holds the `hw_profile` and `op_signature` records and their derived key names. A person cannot write those keys by hand. `hilclaw.nightly.document` builds such a document for the one fp32 `gemm` configuration only, and `tests/test_bf16_end_to_end.py` builds the bf16 ones only for tests. Nothing says in one place what to run, in what order, or what must be on the machine.

**Why now (D26).** Without this, the commands T-0528 and T-0529 give the owner cannot be reached: the owner needs these steps to run P2-15 and see the system work. It is off-checklist work judged under D26; no decision has to be taken first.

**What the owner's values are.** The tolerance of each instance (owner, HQ-0066 (2), no default), the shapes, `n_max` and `round_budget` are inputs here. Neither the code nor the README chooses them as defaults. The B-4 exclusion of an lm_head instance (ADR-0152 decision 4) stands: a `gemm` run is named for `lm_head` by the mapping of `hilclaw.model_check`, as T-0518's Result says.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `f35826ae`. If that has changed when this task runs, DRIVER §6 applies to the new item.

**D16.** Verification writes documents and passes them to the instance start's own checks with the stand-in record the tests supply. No real `claude`, Docker daemon or weights is used.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0530-<slug>`, the `Task: T-0530` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D26 and §8 (D22).
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation and the language policy.
- `PROCESS/PLAN.md` P2-15. `PROCESS/RuntimeAcceptance.md`: RA-0035, RA-0050, RA-0056 to RA-0058, and RA-0061. `PROCESS/NIGHTLY.md` §1 (what the runtime machine holds).
- `PROCESS/tasks/T-0516-bf16-instances-to-generation-end-to-end.md`, `## Result` (the kinds and small shapes). `PROCESS/tasks/T-0518-model-binding-from-run-incumbents.md`, `## Result` (call sites to `shapes`; what the P2-15 run lacks). `PROCESS/tasks/T-0528-read-hugging-face-model-files.md` and `PROCESS/tasks/T-0529-p2-15-model-check-command.md`, `## Result` (the command and an example document).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decisions 2 and 4 (kinds, shapes).
- Code: `hilclaw/nightly.py` (`document`, `_profile`, how the two entries are driven and the environment each needs), `hilclaw/new_run.py`, `hilclaw/turn_start.py` (its command line), `hilclaw/start_instance.py`, `hilclaw/instance_start.py` (`prepare`), `hilclaw/keys.py`, `hilclaw/standin_profile.py` (`local_record`), `hilclaw/contract_table.py` (`TABLE`, `checked`, `timed`), each `hilclaw/*_bf16_contract.py` (`op_signature_record`, `covers`).
- Tests: `tests/test_bf16_end_to_end.py` (how a bf16 document is built), `tests/test_standin_profile.py` (it pins who may name that module).
- `README.md`: "현재 상태와 MVP 범위" (including "instance의 선행조건") and "저장소 구성".

## Acceptance Criteria

1. **`hilclaw/model_instances.py`**: `python -m hilclaw.model_instances <values file> <output directory>`, in Python, with the command-line form of `hilclaw/new_run.py`.
   - **Input:** a JSON file giving, for each of the six kinds, its shape members and its `rtol` and `atol`, and for all of them `n_max`, `draws`, `round_budget` and any other value the document needs from a person. All are required, and none has a default. A missing or unknown kind or member is a named refusal, and so is a shape the kind's `covers` refuses.
   - **Output:** one file per kind named for the kind, each a document that `hilclaw.new_run` accepts: `candidates_per_round` 1, the objective `latency_minimisation` with no constraint (ADR-0189 refuses others), the `hw_profile` from `standin_profile.local_record` as `hilclaw.nightly` obtains it, and the `op_signature` from that contract's `op_signature_record`, with keys from `hilclaw.keys`.
   - **Refusals:** an output file already there is refused and nothing is overwritten. If any kind is refused, no file is written. It starts no run, container other than what obtaining the profile needs, or `claude`, and is registered as no tool.
   - **Shared code:** reuse what `hilclaw.nightly` has rather than copying it; moving a helper to a public name is allowed if behaviour stays the same. Any pinning assertion this touches is edited as D21 allows. Foreseen: `tests/test_standin_profile.py`'s list of who names that module, and any public-name assertion for `hilclaw/nightly.py`. List each one in the PR body.
2. **Tests**, in `tests/test_model_instances.py`:
   - **Happy:** each of the six kinds gives a document `hilclaw.instance_start.prepare` accepts, with a stubbed profile.
   - **Branch:** two shapes for one kind give different key names.
   - **Error and negative:** an unreadable file; malformed JSON; a missing and an unknown kind; a missing member; each value out of range; a refused shape; an existing output file; an output directory that is absent; a failing profile. After each refusal no file is written.
   - Every public function is covered. Existing tests keep passing, and their assertions change only as D21 allows.
3. **`README.md`** gains one short section, in the language of the file's surrounding text, stating the P2-15 steps in order:
   - what the machine needs (Docker, the images and token variables of `PROCESS/NIGHTLY.md` §1, a logged-in `claude`, and `pip install` of the optional packages T-0529 names, none of them a dependency of CI or of the driver);
   - obtaining the model files as the runtime user, under the licence, into a path of their choice, not under the checkout or the data root;
   - `hilclaw.model_instances`, then `hilclaw.new_run` and `hilclaw.turn_start` once per document, and how a run is known to have ended;
   - the mapping from the fifteen call sites to the six run ids, including `lm_head`;
   - `hilclaw.model_check`, with an example document in which every value the owner must give is an obvious placeholder, not a suggested value;
   - how to read `match` and `no_match`, and that the owner records the result in RA-0056 by hand (`PROCESS/RuntimeAcceptance.md`).

   Each command in this section is one the executor has checked against the landed code's usage and, where it can run without the runtime's requirements, by running it with a test value in a scratch directory. The section cites records instead of restating them and chooses no owner value. Add the new module to "저장소 구성" only if that list names modules at this level.
4. **Result** records: the language and the reason; any edited assertion; runtime acceptance items for the driver to add (expected: none beyond RA-0056, which the steps serve); and what, if anything, the owner still cannot do from the README alone.

## Out of Scope

- Running any instance or the check (D16, RA-0056); changing the status of an RA item.
- A helper that starts all six runs itself, or a change to the nightly configuration (D17 (가), HQ-0076).
- Catalog entries for bf16 (OD-22), an lm_head instance (ADR-0152 decision 4), fp16 (HQ-0083) and a new scenario (OD-31 ⑩).
- Choosing any tolerance, shape, N or budget.

## Follow-ups

## Result
