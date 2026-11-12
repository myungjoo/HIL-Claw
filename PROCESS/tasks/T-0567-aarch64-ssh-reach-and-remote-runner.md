---
id: T-0567
title: PLAN P3-17 (1) — record by a §9 ADR how the driver reaches the owner's LAN aarch64 machine over ssh, add a remote process runner and a read-only remote environment check, and judge whether building there with the installed gcc on the host may stand in for the clang image path
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-17", FR-10, C-7, OD-26, ADR-0001]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0204-od26-lan-aarch64-machine-reach.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/remote_run.py
  - hilclaw/toolchain_check.py
  - tests/test_remote_run.py
  - tests/test_toolchain_check.py
estimatedSize: {loc: 480, files: 6}
hq: []
---
## Why

**PLAN P3-17** (D31 ③) asks to show that the C kernel path of `cpu_standin` (build, correctness, measurement) runs remotely on the owner's LAN aarch64 machine (a Raspberry Pi 5), and allows the first task to stop at the means of reaching that machine and its record. The owner answered D31 E6 (2026-11-12, #5 comment 6816955774): "Assessment Agent 과제에서 사용한 인증수단 재사용가능. ssh접속하면 됨." The integrator's read-only check of the same day found aarch64, Debian 12, 4 cores, 8 GB, gcc 12.2.0, make, Python 3.11.2, git, **no clang**, Docker 26.1.3 usable by the account, **no sudo**; the install scope is unanswered, so only what is already there may be used (D31 ③, D29, NFR-4).

This task is the first slice: the §9 ADR for reaching this one machine and its record, the code that reaches it (a remote runner and a read-only remote environment check), and — in the ADR step, before any build code — the judgment PLAN P3-17 asks for: whether building with the machine's gcc and running on its host (instead of the clang image of ADR-0144) is within what the driver may close under §9, or an owner question. The C kernel path itself (build, correctness, measurement, the hw_profile of a kernel built and run on that machine, and the per-key separation of ADR-0001) is the next task; it is not planned now because its content depends on this judgment (DRIVER §6 "task 단위" ④).

**Brake (D31 ②).** This is the PLAN item's own work, not a refinement of the data plane's frame, checks or error paths. Do not add hardening of existing paths beyond what the new runner needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0096 or HQ-0100. If an owner-only part appears (for example installing clang or pulling an image on that machine, a new `toolchain` member, or #5 B-2's general LAN backend), write it in `## Result` as an HQ in the DRIVER §8 structure (Korean, options (a)/(b)…, what it blocks and what it does not), land the rest and return `DONE` (D27 ⑥).

**Size.** About 480 changed lines including the ADR; ADR and code are one task by D20 ①, so it is not split.

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0567-<slug>`, the `Task: T-0567` trailer and the PR body's last line, size D30, tests D12, list assertions D21, storage D29: local temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0567/`); §6 lines **D29** (toolchain, install requests, storage) and **D31** (② brake, ③ machines); §8 (HQ structure); §9 (OD closing by ADR).
- `PROCESS/PLAN.md` P3-17 (line ~81; every sentence binds this task) and the paragraph above P3-15 (line ~77).
- `CLAUDE.md` "개발 드라이버와 런타임의 구분" (the owner-named machines are machines the driver has; never start `claude`).
- `ARCHITECTURE/Requirements.md`: C-7 (⑤ sim/board tools on a LAN machine, ⑥ C + clang), FR-10 (transport-independent tool contract), the OD-4 and OD-26 rows, and the register's **"행 형식"** paragraph (line ~85).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's **"기록 규칙"** (line 8); § OD-26 (line ~527); § OD-18 sub-question ⑫ (the non-native-ISA board, line ~412).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 (the recheck rule).
- ADRs: `ADR-0001-od4-key-schema.md` (key fields, Boundaries); `ADR-0035-od4-cpu-standin-hw-key-values.md` (decisions 2–6, Boundaries — built on one machine and run on another); `ADR-0144-od14-first-case-build-run-container.md` (the build and run container of `cpu_standin`, network off, pull policy `never`); `ADR-0186-od14-standin-toolchain-from-image.md`; `ADR-0016-od18-backend-frame.md`; `ADR-0038-od18-cpu-standin-execution-points.md` (Boundaries ⑫); `ADR-0194-od33-vendor-stack-evaluation-design.md` decision 7 (the read-only environment check).
- Code: `hilclaw/local_run.py` (the result shape the remote runner should mirror), `hilclaw/toolchain_check.py` (`COMPONENTS`, `assemble_probe`/`interpret_probe`, the report and its no-secrets rule), `hilclaw/standin_profile.py` (`local_record`, how `host.cpu`/`host.os` are read), `hilclaw/clang_adapter.py` (probe of a component).
- Tests: `tests/test_local_run.py`, `tests/test_toolchain_check.py`.

## Acceptance Criteria

1. **Before writing code — reach the machine read-only.** Use only the ssh client already on the development PC and the authentication the owner said to reuse (no new key, account, agent setup or other means; no option that weakens host-key checking; never type or store a password or passphrase). If the machine cannot be reached non-interactively, stop: land nothing, write in `## Result` what failed (without address, account or key path) and an HQ asking the owner to fix it, and return `BLOCKED`. Confirm, read-only, the facts the judgment of criterion 3 needs: `uname -m`/`-s`/`-r`, the gcc and make versions, that `clang` is absent, `docker version` usable by the account, and whether any image of ADR-0144's name (or any image at all usable for it) is already on that machine. Touch no other service's container or file there.
2. **ADR-0204** (§9; title and slug may be adjusted, number checked against `ARCHITECTURE/decisions/` at start), closing a part of OD-26 for **this one machine only**:
   - where the name of the destination is read from outside the repository (proposed: one environment variable naming an ssh destination that the owner's own ssh configuration resolves, e.g. an alias; the ADR decides the name and what happens when it is unset — tools that need it say it is not configured, tests skip);
   - the remote runner's contract: an argument list run without an interpreting remote shell surprise (each argument quoted for the remote POSIX shell), non-interactive (`BatchMode`), a required time limit, and how an ssh failure (exit 255, connection refused, host-key mismatch) is told apart from the remote program's own exit status;
   - the remote working directory: one directory per task under the account's home (`hilclaw-driver/T-NNNN/` or as the ADR decides), created and removed by the task (D29 applied to that machine, PLAN P3-17), and how files are copied there and back with the same means (`scp`/`ssh` already installed);
   - what the record of a remote run says about the machine without naming it: no address, account, key path or alias value in any return value, message, log, report, test output, ADR, task file or PR (PLAN P3-17); the only place the address may appear is a quotation of the owner;
   - the measurement note: values from that machine are noisy (other services, `ondemand` governor) and are not presented as stable numbers;
   - **Boundaries**: #5 B-2 (the general LAN backend and `board.run` remote), the rest of OD-26 (registration), OD-18 ⑫ (emulated sim of a non-native board), and the hw_profile of a kernel built and run on that machine (next task) are not decided.
   Register edits follow the recording rules exactly: the OD-26 row of `Requirements.md` gets one link in `**확정분**:` and its `**잔여**:` rewritten in place (행 형식); § OD-26 of `OpenDecisionProposals.md` gets one `- **채택분**` line and the affected sub-question's status rewritten in place (기록 규칙); no restatement of the ADR and no dated paragraph. Recheck coverage by StandardScenarios' rule and update § 검사 결과 only as that paragraph says (CLAUDE.md "문서 커버리지 재검사").
3. **The judgment PLAN P3-17 asks for**, written as an ADR section before any build code: may the next task build `cpu_standin` kernels on that machine with its gcc and run them on its host, instead of clang in the ADR-0144 image? Weigh at least C-7 ⑥ and #5 A-7 ("C + clang"), ADR-0035 decision 3 (`toolchain` has the one member `clang`), ADR-0144/ADR-0186 (build and run in the image), and D23 (a new `toolchain` member or value meaning is a frame change). Do not substitute in this task. If the substitution is not the driver's to close, write an HQ in `## Result` that states the concrete options — at least: (a) the owner installs clang on that machine (the account has no sudo); (b) the owner approves building or pulling the `cpu_standin` image there (a download, D29); (c) gcc on the host with the exact `toolchain` member and value form proposed — and what each blocks; the ADR records that the question is open and the next task waits on it.
4. **`hilclaw/remote_run.py`** (new; Python unless the commit body gives another reason): run one argument list on the configured destination with a required time limit, returning a result that mirrors `hilclaw.local_run.run`'s fields where they apply (exit status, timed out, stdout/stderr bytes, wall-clock time) plus a field or kind that marks an ssh-level failure; the reported command omits the destination (a fixed placeholder). Also: create and remove the per-task remote directory, copy a file there and back. Bad input (empty argument list, non-text argument, non-positive limit, a task id not of the form `T-NNNN`, a remote path escaping the task directory) is refused before ssh is started. Removal is `rm -r` of the one task directory only — never `rm -rf`, never a path outside it.
5. **Remote environment check** in `hilclaw/toolchain_check.py` (or a new module if the ADR says so, with the same component table — no second list of commands): read the host components of `COMPONENTS` and the kernel name/machine on the configured destination through the remote runner, with the same report entry form and the same no-secrets rule; an unconfigured or unreachable destination is a report state, not a crash. No install, no pull, no container start on the remote.
6. **Tests** (D12): `tests/test_remote_run.py` (new) and the touched part of `tests/test_toolchain_check.py`, with no real network in the default run: the ssh program is replaced by a stub the test writes (a stub is allowed; it is not `claude`), covering happy path, remote non-zero exit, ssh failure (255), timeout, quoting of arguments with spaces and quotes, unset destination, every refused input of criterion 4, and that no destination text reaches any result, message or report. One test that reaches the real machine runs only when the destination variable is set (skipped otherwise, including in CI); the executor runs it locally and states the outcome in the PR body without the address. Existing tests stay unchanged except list assertions under D21 — foreseen: the public names or `COMPONENTS`-related lists pinned in `tests/test_toolchain_check.py`; list every such edit in the PR body. Full suite passes; `hilclaw/` line and function coverage ≥ 80%.
7. **Real check recorded**: `## Result` states, without address, account or key path: the facts of criterion 1, the outcome of the real-machine test, that the remote task directory was created and removed, and the ADR's judgment of criterion 3 (or the HQ). Runtime acceptance items, if any, are listed for `PROCESS/RuntimeAcceptance.md` (D22), not as HQs.
8. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28; the review prompt names the no-secrets check of criterion 2), CI green, self squash-merge with the PR body's last line `Task: T-0567`. Local task directory removed at the end.

## Out of Scope

- Building, checking or measuring a kernel on that machine; the hw_profile of a remote run and the per-key separation (next task of P3-17).
- Installing anything or downloading anything (packages, clang, container images) on that machine or the development PC; creating keys or accounts; editing ssh configuration or `known_hosts`.
- #5 B-2's general LAN backend, a `board.run` over the network, OD-18 ⑫, registration (rest of OD-26).
- P3-16 (waits on HQ-0096 ②) and anything of HQ-0100.
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

## Result
- **DONE.** PR #381, squash-merged as `7f97399c`; branch deleted. Review: 2 rounds. Round 1 was Request changes: the real-machine test could print the destination value in pytest's assertion output, and the OD-26 status date was stale. Round 2 was Approve. One wording Nit was fixed after Approve under the D20 exception: ADR-0204 decision 3 now names the real-machine test's second variable. CI green on head `234897db`. Local full suite: 39924 passed, 2218 skipped. Coverage: `hilclaw/remote_run.py` 100%, `hilclaw/toolchain_check.py` 99%. §9 notice posted: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6824784024
- **Resume** (§3-5): at start there was no landed commit, PR or branch for T-0567, and the dead run had left no local or remote task directory. Started from scratch.
- **Criterion 1, read-only facts** (2026-11-12). Means: the ssh client already on the development PC with the authentication already set up for the owner's other project, `BatchMode=yes`, no option that weakens host-key checking.
  - `uname -m` aarch64, `uname -s` Linux, `uname -r` 6.6.28+rpt-rpi-2712; Debian 12.15
  - gcc (Debian 12.2.0-14+deb12u1) 12.2.0; GNU Make 4.3; Python 3.11.2; `clang` absent
  - `docker version` client and server 26.1.3, usable by the account
  - 4 cores; load average about 1.4 to 1.5; governor `ondemand`
  - No image of this repository, of `cpu_standin` or of ADR-0144 is in the machine's image store. The 16 images there belong to other services or are base distribution and toolchain images. Their contents were not checked and no container was started.
  - Nothing else on the machine was touched.
- **Real-machine test** (`test_the_real_machine_round_trip`, run locally with `HILCLAW_AARCH64_SSH` and `HILCLAW_REMOTE_TEST_TASK=T-0567` set; skipped in CI): passed twice.
  - `remote_check` returned state `read`: kernel `Linux`, machine `aarch64`; clang, nvcc, nvidia-smi and qnn-net-run `absent`.
  - The remote task directory `hilclaw-driver/T-0567/` was created, a binary file was copied there and back byte-equal, and the directory was removed with `rm -r` and confirmed gone.
  - The empty shared parent `hilclaw-driver/` stays on the machine, as ADR-0204 decision 5 says, in the same way as the local `${TMPDIR:-/tmp}/hilclaw-driver/`.
- **ADR-0204 decision 9** (criterion 3): building `cpu_standin` kernels on that machine with the host's gcc and running them on its host, instead of clang in the ADR-0144 image, is not the driver's to close. The reasons are #5 A-7 "clang as the single toolchain" and C-7 ⑥, ADR-0035 decision 3 (`toolchain` has the one member `clang`), ADR-0144 decisions 4 and 5 with ADR-0186 (build and run in the image, no host fallback), and D23 (a frame change). Nothing was substituted. The question goes to the owner as an HQ (HQ-0101, recorded by the driver), and the next P3-17 task waits on it.
- **Runtime acceptance items**: none. The machine is driver-usable under D31 ③, and nothing here needs a live `claude` session.
- **D21**: no existing assertion was changed. The import list of `tests/test_toolchain_check.py` gained `remote_run` and `vendor_adapter` for the new tests.
- **Language**: Python, the same as the rest of the 2nd-layer package and `local_run`, which the runner wraps.
- **Size**: about 300 non-test lines (ADR, code, registers) in 6 non-test files plus 2 test files; within D30.
- No install or download on this PC or the remote machine, no work image, no test run, no `claude` started. The local task directory `${TMPDIR:-/tmp}/hilclaw-driver/T-0567/` was removed.
