---
id: T-0517
title: Let a cpu_standin kernel use OpenMP on every C-7 system, as the owner answered HQ-0034 (a) - an ADR and its first code slice
phase: P2
status: DONE
commitMode: code
coversReq: [FR-4, NFR-4, C-7, OD-18, "#5 A-7", HQ-0034]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - hilclaw/standin_settings.py
  - hilclaw/standin_run.py
  - hilclaw/standin_check.py
  - hilclaw/nightly.py
  - PROCESS/NIGHTLY.md
  - .github/workflows/ci.yml
  - tests/test_standin_settings.py
  - tests/test_standin_run.py
  - tests/test_standin_check.py
  - tests/test_nightly.py
  - tests/harness/test_timing_waiter.py
  - tests/test_attempt_kernel.py
  - tests/test_model_forward.py
estimatedSize: {loc: 420, files: 8}
hq: []
---
## Why

The owner answered HQ-0034 (T-0325) with (a) on 2026-10-25: "모든 C-7 시스템에서 stand-in 커널이 OpenMP를 쓸 수 있게 한다. 고정 빌드 설정에 OpenMP 플래그와 런타임을 넣고, 런타임이 없으면 2026-10-15 승인 규칙에 따라 사용자 승인을 받아 설치한다(컨테이너는 그 이미지에)." The answer was held by D18 because the first case and PLAN P2-14 run without OpenMP. It is the line "HQ-0034 답(T-0325 ...)" of the PLAN hold section. P2-14 is checked, so PLAN's hold header makes that line due for a judgement, and the planner judged that it becomes a task: the owner has decided it, and a kernel cannot use threads through OpenMP today, although #5 A-7 ② allows them and ADR-0008 decision 7 lets a kernel include `<omp.h>`.

`hilclaw/standin_settings.py` still has `FLAGS = ("-std=gnu11", "-O2", "-ffp-contract=off")` and `TRAILING_FLAGS = ("-lm",)`, and its docstring names OpenMP as open under ADR-0116 decision 6.

ADR-0116 weighed the macOS default clang and its separate flag spelling. ADR-0144 decision 5 and ADR-0186 have since made the image's `clang` the compiler of these builds, so one spelling may now serve every C-7 system. The ADR must check that reading and say so. It is not assumed here.

This task follows DRIVER §6 "task 단위" ①: the ADR and its first code slice land in one code-mode PR.

**Authority (planner's reading; the reviewer re-checks each).**
- Whether OpenMP is available is the owner's and is answered. The flag, its place in the set, the thread setting and the check of the image are design-level parts of OD-18 ⑱ (라) and ⑲ (라), which DRIVER §9 lets the ADR close.
- **Dependency.** The owner's answer approves an OpenMP runtime in the image. Whether it also covers a package added to the CI runner is this planner's reading. State the reading in the ADR's A-13 paragraph. If the reviewer does not accept it, stop as BLOCKED (new external dependency).
- **Data plane.** No member, file, kind or version may change. ADR-0035 decision 3 decided that `toolchain` has no OpenMP runtime member. If the design turns out to need one, or any other change of the frame, stop as BLOCKED with the question in Korean (CLAUDE.md A-13).
- **The runtime never installs anything.** NFR-4 and FR-4 require the user's permission for a toolchain change, and the image is the user's. When the named image has no usable OpenMP, the runtime reports what is needed and why, and stops. It changes nothing.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (executor procedure, naming, time limit, task format, test rules, D21), §3 "BLOCKED 사유" and "승인된 열린 목록", §9 (the ADR path and the owner notice), §11 row D25.
- `CLAUDE.md`: "브랜치·merge 절차", "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분", "문서 커버리지 재검사".
- `PROCESS/STATE.json`: the `humanQuestions` entry HQ-0034, read whole.
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`: decisions 3 to 6, Limit 4, the walk-through table and Consequences.
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 6 and 7 (threads and headers), and the Completion row of the contract table.
- `ARCHITECTURE/decisions/ADR-0035-*.md`: decision 3, the OpenMP runtime paragraph, and decision 7.
- `ARCHITECTURE/decisions/ADR-0144-*.md`: decisions 2, 3, 5 and 6.
- `ARCHITECTURE/decisions/ADR-0145-*.md`: W0 to W6 and decision 5 (what the waiter protects and why it allocates nothing).
- `ARCHITECTURE/decisions/ADR-0186-od14-standin-toolchain-from-image.md`: whole, the model for reading a fact from the image.
- `ARCHITECTURE/decisions/ADR-0107-*.md`: decision 3 and Limit 3 (one set for the two builds of an attempt).
- `ARCHITECTURE/Requirements.md`: FR-4, NFR-4, C-7, and the register's "행 형식" with the OD-18 row. `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" and § OD-18 sub-questions ⑱ and ⑲.
- `PROCESS/NIGHTLY.md`: §1 (machine preparation), §2 and §7 (environment causes).
- Code: `hilclaw/standin_settings.py`; `hilclaw/standin_run.py` (the two builds, lines about 257-290); `hilclaw/standin_check.py` (lines about 380-400); `hilclaw/attempt_kernel.py` (use of `FLAGS`); `hilclaw/model_build.py` (`LIBRARY_FLAGS`); `hilclaw/nightly.py` (the pre-firing check and `prepare/*`); `hilclaw/standin_profile.py` (the read of ADR-0186); `.github/workflows/ci.yml`.
- Tests: `tests/test_standin_settings.py`; the uses of `-ffp-contract` in `tests/harness/test_timing_waiter.py`, `tests/test_attempt_kernel.py` and `tests/test_model_forward.py`.

## Acceptance Criteria

1. **ADR.** A new `ARCHITECTURE/decisions/ADR-NNNN-*.md` (the next free number; ADR-0188 at planning time), in the format of ADR-0001 "Record format", quotes the owner's answer and decides at least:
   - the flag and where it goes, including whether a separate runtime flag is needed, with the sources checked for that flag on the image's clang (facts from documents are marked verified with their URL; anything else is marked as the record's expectation);
   - which builds take it: the kernel's verification build, its timing build, the verification and timing harness programs, the waiter of ADR-0145, and the kernel libraries and the forward program of the model executor. **The waiter is decided explicitly**: ADR-0145 relies on what it does after the child ends, so state whether it may link an OpenMP runtime and why. ADR-0107's rule of one set for the two builds of an attempt must still hold, or the record must say what changes;
   - the thread setting: which variable, if any, the backend sets, and the value. ADR-0116 decision 5 (an inherited environment, nothing added) is the point to confirm or revise, with the effect on NFR-3 noise and on the time limits stated;
   - what happens when the named image has no usable OpenMP, per the Authority paragraph above: where it is found, what the user reads, and that nothing is installed;
   - that C-7's systems are alike under it, or which difference remains and why it is accepted;
   - an A-13 reading (no data-plane change; the dependency reading of the Authority paragraph); the sentences of earlier records it makes less exact, unedited, in Consequences; and Boundaries naming what stays open. The Boundaries must include which `kernel` techniques or catalog entries use OpenMP (OD-22), a target-specific flag and the list of inherited variables.
2. **Registers.** `Requirements.md` and `OpenDecisionProposals.md` follow their own recording rules: the register's "행 형식" and the header's "기록 규칙" (one link per new ADR, open parts rewritten in place, no restatement of the record, no dated paragraph). Remove OpenMP from the remaining part of OD-18 ⑱ (라) and ⑲ (라) only as far as the ADR answers it. If `ARCHITECTURE/` coverage is affected, run the check of `StandardScenarios.md`; otherwise state in the commit body that no scenario verdict changes.
3. **The set.** `hilclaw/standin_settings.py` carries the ADR's flags and its docstring says so. A build by the two `cpu_standin` operations, and a kernel build through `attempt_kernel`, takes them as the ADR decides. All other values of the set are unchanged.
4. **The image check.** The check the ADR decides is implemented for the nightly entry, as a new `prepare/*` outcome classified as an environment cause. It compiles, links and starts a small OpenMP program in a new container of `HILCLAW_STANDIN_IMAGE` with the ADR-0144 options, through the same container helper as ADR-0186, and removes what it made. `PROCESS/NIGHTLY.md` §1 names the image's new requirement. A check for instance starts outside the nightly entry may be left to a later slice if the ADR names it as one.
5. **CI.** The Python gate can build what the tests build with the new flags. `.github/workflows/ci.yml` installs the runtime only if the tests need it. CI is green before the merge (CLAUDE.md A-13). No test is added for the workflow.
6. **Tests** (CLAUDE.md test rules ① to ④; stubs only, no real `docker` and no real `claude`):
   - **happy**: a kernel using `#pragma omp parallel for` and `omp_get_max_threads` builds with the set and returns the right result, in a test skipped only where no usable clang with the runtime exists (never skipped on the CI gate); a build command of each operation holds the flags as the ADR decides;
   - **error**: a stub image with no OpenMP gives the new `prepare/*` outcome, an environment cause, with the message the ADR decides, and the firing starts no run;
   - **branch**: each failure of the probe (container not started, status other than 0, time limit) is classified as the ADR decides, and the probe's container is removed;
   - **negative**: the waiter's build holds exactly what the ADR says; a kernel without OpenMP builds and runs as before.
7. **Existing tests.** These pin the values this task changes and may be edited as far as the change requires: `tests/test_standin_settings.py` lines 53-57 (`FLAGS`, `TRAILING_FLAGS`), `test_no_flag_is_a_setting_the_record_leaves_out` (the prefix table) and the `-lomp`/`-lgomp` parametrised test beside it; any literal of the flag set in `tests/harness/test_timing_waiter.py`, `tests/test_attempt_kernel.py`, `tests/test_model_forward.py`, `tests/test_standin_run.py` and `tests/test_standin_check.py`. DRIVER §5 (D21) also allows the edit of an assertion that pins public names, imports, fields or binders. List every edited assertion in the PR body. No other existing assertion changes.
8. **Runtime acceptance.** The ADR says it hands its items to `PROCESS/RuntimeAcceptance.md`, and `## Result` lists them. They include at least: the image's clang accepts the flags on each C-7 system's Docker; a kernel using OpenMP completes a check and a timing run in the container under the ADR's limits; the thread count the runtime picks there; the waiter still reports `waiter_max_rss_kib`. None is closed by this task.
9. **Owner notice.** After the landing, the §9 notice is posted on #5 with the driver's tail line (DRIVER §8), and `## Result` tells the owner plainly that the stand-in image must hold the OpenMP runtime before the next nightly firing, or the firing ends with the new environment outcome.
10. Language of any new layer-2 file and the reason are one line in `## Result` and in the commit body.

## Out of Scope

- Installing anything on any machine, and editing or publishing an image.
- Starting a real `claude`. A D25 partial test of the single new build step is the executor's own option and is only supplementary; a full loop is not run.
- A new member of the hw_profile, `instance.json`, spec or result.
- Catalog entries or prompt text that tell the coder to use OpenMP (OD-22).
- Moving the fp32 `model_execute` path into containers (a separate hold line, ADR-0182 slice 3).
- Any other line of the PLAN hold section. Do not edit `PROCESS/PLAN.md`.
- `.claude/settings.json` and `.claude/settings.local.json`.

## Follow-ups

## Result

DONE. PR #336, squash-merged as 4740de79 after 2 review rounds (round 2 Approve; a wording Nit fixed after it under D20). CI green on all gates at the last commit.

**Owner must act.** The stand-in image (`HILCLAW_STANDIN_IMAGE`) must hold the OpenMP runtime and `<omp.h>` before the next nightly firing, or the firing ends as `prepare/no_openmp`, an environment cause. Observation: on the driver's machine `hilclaw-standin:2026-10-29` (clang 18.1.3, `libomp-dev`) holds it, and the new check returned `None` against it.

**Landed.** ADR-0188; `FLAGS` with `-fopenmp`, new `WAITER_FLAGS`, `TRAILING_FLAGS` and `ENV` unchanged; `hilclaw/standin_openmp.py`; the check in `hilclaw/nightly.py`; `PROCESS/NIGHTLY.md`; `libomp-dev` in the Python and coverage gates; the registers.

**Language.** `hilclaw/standin_openmp.py`: Python, because it only drives the container client from the nightly entry.

**Readings and limits.**
- The reviewer accepted the ADR's reading that HQ-0034 covers `libomp-dev` on the CI runner, on the condition that the §9 notice states it as the record's own and states that "install after approval" is not implemented. The notice on #5 does both.
- `test_a_kernel_outside_the_set_is_a_failed_build` lost its `openmp-runtime-call` parameter, which criterion 7 does not name: criteria 3 and 6 reverse what it pinned. The reviewer accepted this; it is listed in the PR body.
- Local tests ran on WSL with the runtime copied from the image to a temporary directory: full suite 38765 passed with 2 failures, both test helper calls then fixed and rerun. No test run (D25) with `claude` was started; the only real container use was `docker run` of the image for the check.

**Runtime acceptance items for `PROCESS/RuntimeAcceptance.md`** (ADR-0188): (i) the image's clang accepts `-std=gnu11 -O2 -ffp-contract=off -fopenmp` and `-lm` under each C-7 system's Docker: Linux, macOS Docker Desktop and WSL; (ii) a kernel using OpenMP completes a check and a timing run in the container under the options of ADR-0144 and the limits of ADR-0117; (iii) the thread count the runtime picks in that container, and whether it fits the processors the machine gives; (iv) the waiter still reports `waiter_max_rss_kib` for such a kernel in a container; (v) a kernel with no OpenMP is measured as before within noise.

**Follow-ups (not task files).** A check at instance starts outside the nightly entry (ADR-0188 decision 4, later slice); what asks the user for permission (OD-8 ㉝ (가)).
