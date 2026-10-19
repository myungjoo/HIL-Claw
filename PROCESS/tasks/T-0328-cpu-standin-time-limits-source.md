---
id: T-0328
title: Add the `cpu_standin` time limits of ADR-0117 (60 s per build; the per-process rule over the handed shape and `draws` or `n_max`, capped at 1500 s) to the one settings source `hilclaw/standin_settings.py`, with tests
phase: P1
status: DONE
commitMode: code
coversReq: [NFR-4, FR-10, FR-9, OD-14, OD-18, C-7]
dependsOn: [T-0326, T-0327]
touchesFiles:
  - hilclaw/standin_settings.py
  - tests/test_standin_settings.py
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5 (the near goal) is a run on `cpu_standin` × GEMM. The `cpu_standin` operations of those tools do not exist yet. Two of their inputs are now recorded:
- ADR-0116 (build flags, trailing flags, environment), put in the package by T-0326 as `hilclaw/standin_settings.py`;
- ADR-0117 (T-0327, main a4b07b5), the four time limits of one call: each build 60 s; each process `min(1500, 10 + c·(1 + 2mkn / 2e8))` s, with `c = draws` for the verification process and `c = n_max + 1` for the timing run.

ADR-0117 Consequences name this code slice: "the constants of decisions 3 and 4 and the rule, beside the settings of `hilclaw/standin_settings.py`, applied by the three operations, with tests — among them the two counts, the cap, and that the rule never gives a value the functions refuse." This task adds the constants and the rule only. Wiring them into operations is out of scope, as it was for T-0326.

D18: this is a stop of the `cpu_standin` operations that P1-1's criterion and P2-5 need, so the priority rule does not set it aside.

No open HQ is needed:
- HQ-0021 (T-0210) and HQ-0026 (T-0243) block the operations, not this source.
- HQ-0034 (OpenMP) does not touch time limits.
- HQ-0033 is a runtime acceptance notice for C-7 systems.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0328` trailer (also the last line of the PR body), size cap, test rules ①-⑤.
- `CLAUDE.md`, these rules: "도구 계층 언어 정책" (record the language choice), "테스트 규칙", "코멘트 최소화", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md`:
  - decisions 1 to 4 (lines 25-62): scope, source, the build value, the process rule and its terms, the stated worst case;
  - decision 7 (lines 77-81): no new answer; the values are always positive, finite and at most 1500;
  - the Walk-through (lines 83-92);
  - Consequences, the "Code slice" bullet and the `standin_settings.py` docstring sentence (lines 118 and 123), and the "Runtime acceptance items" bullet (line 125).
- `ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md`, decision 3 (lines 63-67): `draws` is an integer, at least 1.
- `ARCHITECTURE/decisions/ADR-0023-od8-instance-record-n-max.md`, decision 3 (lines 36-41): `n_max` is an integer, at least 5, at most 2^53 − 1.
- `hilclaw/standin_settings.py` (the whole file, 41 lines) and `tests/test_standin_settings.py` (lines 1-75).
- `hilclaw/clang_build.py`, `_check_timeout` (lines 520-530), and the `timeout_s` paragraph of the `build` docstring (lines 217-226); `hilclaw/local_run.py`, the `run` docstring (lines 79-150), for the `timeout_s` values those functions refuse.

## Acceptance Criteria

1. **Session entry check.** Run `gh pr list`. Draft PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. If any open PR touches a file of this task's touchesFiles, stop and report it.
2. **The constants and the rule**, added to `hilclaw/standin_settings.py` in Python (record the reason in the commit body):
   - `BUILD_TIME_LIMIT_S = 60`: the limit of the verification build and of the timing build alike (ADR-0117 decision 3). A single constant is acceptable because the record gives both builds the same value. If you choose two names, keep them equal and test that.
   - `PROCESS_TIME_LIMIT_CAP_S = 1500` (decision 4).
   - `verification_process_time_limit_s(m, k, n, draws)` returns `min(1500, 10 + draws·(1 + 2·m·k·n / (2·10^8)))` seconds.
   - `timing_process_time_limit_s(m, k, n, n_max)` returns the same rule with `c = n_max + 1`.
   - Both return a `float`. Compute exactly, with integers or `fractions.Fraction`, and convert once at the end. A very large argument, such as `2**53 - 1` for every input or a Python int far above it, must return `1500.0` and must not raise `OverflowError`.
   - **Inputs.** Each argument must be an `int` and not a `bool`, otherwise `TypeError`. Each must be at least 1, otherwise `ValueError`. Do not add the `n_max ≥ 5` bound of ADR-0023: validating the instance record is not this module's job, and the rule is defined for any positive count. Keep the private helper count to what the rule needs.
   - Keep names close to the ones above. If you rename, say so in Result.
3. **The module docstring.** Rewrite it in place so that:
   - it cites ADR-0117 next to ADR-0116 and names the new constants and functions in the bullet list;
   - the sentence "The set holds no compiler and no time limit (OD-14)." no longer claims there is no time limit. It still says the set holds no compiler (OD-14 ①).
   Keep the docstring style of the file. Add no other comment (CLAUDE.md "코멘트 최소화").
4. **Nothing else changes.** Do not wire the module into any other module: not `check_definition`, the run tools, `clang_build`, `local_run`, `harness/`, `mcp_front` or `tools`. Do not change `FLAGS`, `TRAILING_FLAGS` or `ENV`. The module still reads no file, no environment variable, no configuration and no hw_profile, and it starts no process.
5. **Tests**, in `tests/test_standin_settings.py`, following DRIVER §5 test rules ①-④:
   - **Update** `test_the_module_exposes_only_the_three_settings` to the new public set. Do not weaken any other existing test.
   - **Happy: values of the record.** `BUILD_TIME_LIMIT_S == 60` and `PROCESS_TIME_LIMIT_CAP_S == 1500`. Check the rule against exact `Fraction` expectations, and against the figures of ADR-0117 to the precision the record states:
     - timing, gate/up at M = 512 (`m=512, k=2048, n=8192`), `n_max=10`: ≈ 966 s;
     - timing, O at M = 1 (`m=1, k=2048, n=2048`), `n_max=10`: ≈ 21.5 s;
     - verification, O at M = 1, `draws=1`: ≈ 11 s.
   - **Branch: the two counts.** For the same shape, `timing_process_time_limit_s(..., n_max=x)` equals `verification_process_time_limit_s(..., draws=x+1)`.
   - **Branch: the cap.** At gate/up M = 512, verification with `draws=17` is below 1500 and `draws=18` gives exactly `1500.0`. Timing gives `1500.0` from `n_max=17`, and is below 1500 at `n_max=16`.
   - **Never a refused value.** For the smallest inputs (all 1), for `2**53 - 1` in every position and for an int far above it, the result is a `float` with `0 < value <= 1500`, finite. It is also within the `timeout_s` bound of `hilclaw.clang_build.build` (`(2**31 - 1) / 1000`). `BUILD_TIME_LIMIT_S` meets the same conditions. Use the public bound or restate the number; do not import a private name of `clang_build`.
   - **Negative.** For each argument of each function: `True`, `1.0`, `"1"` and `None` raise `TypeError`; `0` and `-1` raise `ValueError`.
   - Do not add tests of tests, CI or scripts (rule ⑤).
6. **Gates.** Run locally `pytest`, the repository's ruff gate (`ruff check` and `ruff format --check`, or what `pyproject.toml` and CI use), and the coverage gate (`hilclaw/` line ≥ 80%, function ≥ 80%). CI must be green before merge.
7. **Scope and size.**
   - `git diff --stat origin/main` lists only the touchesFiles, plus this task file's Result if the driver asks for it.
   - Non-test lines changed ≤ 300 (expected under 80).
   - No new dependency. No change to `pyproject.toml`, CI, `.claude/` or any settings file.
   - No data-plane schema change: no member, file, kind, `condition` value, `step` value or version.
   - No edit under `ARCHITECTURE/`.
8. **D16.** No `claude` program is started, and no board, accelerator or API key is required. Do not claim ADR-0117's runtime acceptance items: that the values suffice on each C-7 system and in the container, and the bound in draws and `n_max` of the tool function's own work.
9. **Merge.** Code mode under CLAUDE.md A-13:
   - Draft PR on branch `claude/T-0328-cpu-standin-time-limits-source`, with `T-0328` in the title;
   - reviewer cycle (dev-code-review, at most 7 rounds) and CI green;
   - `gh pr merge --squash --body` with a body whose last line is `Task: T-0328`, then delete the branch.

## Out of Scope

- The `cpu_standin` operations of `correctness.check`, `sim.run` and `board.run`, their registration, and passing these limits as `timeout_s`. These still wait on OD-14 ① (compiler installation), HQ-0021 (T-0210) and HQ-0026 (T-0243).
- Any limit of a whole call, of a round or of a run (OD-14 rest; ADR-0032, ADR-0033; OD-18 ③).
- Any edit to an ADR or to `Requirements.md`, `OpenDecisionProposals.md` or `StandardScenarios.md`. This includes the two ADR-0117 round-7 wording nits, which are held under D18.
- Any edit to `hilclaw/standin_profile.py` or to any file of PR #186.

## Follow-ups

- The next stop on the path of the `cpu_standin` operations is not plannable from here: the operations wait on HQ-0021, HQ-0026 and the compiler installation (OD-14 ①). The planner should next look at the other open stops of P1-1 or P1-8, or at P2-1.

## Result
- Landed: PR #188, squash-merged as 87f8f544de7ad39866f7f98b78cef9c55d5ceed2; branch claude/T-0328-cpu-standin-time-limits-source deleted.
- Review: 2 rounds (dev-reviewer). Round 1 Approve with one Low and one Nit, both fixed (refusal tests match `^<name> must`; public-set test renamed). Round 2 Approve.
- CI green on f024d84 (Python 3.11/3.14, coverage, C, sh, test presence). Local: 23479 passed; hilclaw/ line coverage 99%, standin_settings.py 100%.
- Added: BUILD_TIME_LIMIT_S=60, PROCESS_TIME_LIMIT_CAP_S=1500, verification_process_time_limit_s(m,k,n,draws), timing_process_time_limit_s(m,k,n,n_max); exact integer arithmetic scaled by 2e8, capped, one final division. Nothing wired into any operation.
- Language: Python, because the module belongs to the Python tool package that the Python operations read.
- ADR-0117 runtime acceptance items are not claimed. No follow-ups.
