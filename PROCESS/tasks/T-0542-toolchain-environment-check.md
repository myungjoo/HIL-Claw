---
id: T-0542
title: Add the read-only environment check command of ADR-0194 decision 7 that reports host and image toolchain components through the adapters' probe parts
phase: P3
status: TODO
commitMode: code
coversReq: [FR-19, OD-33, NFR-4, NFR-2, "PLAN P3-8"]
dependsOn: [T-0541]
touchesFiles:
  - hilclaw/toolchain_check.py
  - tests/test_toolchain_check.py
  - hilclaw/clang_adapter.py
estimatedSize: {loc: 300, files: 2}
hq: []
---
## Why

**PLAN P3-8**, second of two tasks. T-0541 lands the adapter frame (`hilclaw/vendor_adapter.py`) and the clang reference adapter (`hilclaw/clang_adapter.py`), including its probe pair. This task adds the command PLAN P3-8 asks for. The command reports, without installing anything, the toolchains of the machine and of the images placed on it, plus the presence and versions of the machine's drivers and devices. Driver tasks use it under D29: the executor reads the machine before writing code. The runtime uses it too (S12 step 1). The driver checks PLAN P3-8 once this task and T-0541 are both `DONE`.

**Start check.** First read T-0541's `## Result` for the actual public names and the probe pair's signature. If T-0541 renamed or reshaped them, use what it landed. If T-0541 is not `DONE`, stop and report it.

**Order and open HQs.** These are the same as T-0541's Why (DRIVER §6 D27 ①, ⑥). HQ-0092 to HQ-0097 do not hold up P3-8. The report goes **outside the data plane** (ADR-0194 decision 7). This task decides neither whether the runtime stores the report nor whether the report fills a hw_profile's `toolchain` (OD-26, owner).

**What it probes in this task.** On the host, every component that has an adapter with a probe pair. After T-0541 that is `clang` alone. P3-9 adds `nvcc` and `nvidia-smi` (drivers and devices) and P3-10 adds QNN, each by registering its adapter's probe with this command. No component gets a probe command written here: "No second list of commands" (decision 7). This command also covers each image the caller names. For an image, the same probe runs inside a container started by `standin_container.run_in_container`: no network, no pull, as ADR-0144 starts one. No target names a tool image today (OD-14), so the caller supplies the image names.

**D16.** Tests use the real `clang` on the host and stub container clients (`client=` of `run_in_container`, as the existing `standin_container` tests do). Nothing starts `claude`, real Docker, a board or an accelerator. What the command reads on each C-7 machine kind is a runtime acceptance item (ADR-0194 Consequences), which the executor writes in `## Result`.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0542-<slug>`, the `Task: T-0542` trailer and the PR body's last line, size D30, tests D12, list assertions D21, storage D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0542/`), §6 D27 and **the D29 toolchain paragraph**, §8 (runtime acceptance items, D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/tasks/T-0541-vendor-adapter-frame.md` (whole, including `## Result`).
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`: **decision 7 in full** (the binding text), decision 2 (no adapter starts its own process; no device is given to a container), decision 6 (fault scripts), decision 9 (the machine facts), Consequences ("Runtime acceptance items").
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` (how a container is started: no network, pull policy `never`); `ADR-0001-od4-key-schema.md` decision 6 (the open `toolchain` map; not written here).
- `ARCHITECTURE/StandardScenarios.md` S12 step 1 and `ARCHITECTURE/Requirements.md` FR-19 ③ ⑤, NFR-4 (permission for what is missing is the runtime's, not the check's).
- Code: the two modules of T-0541 (whole); `hilclaw/standin_container.py` lines 1-140 and 280-386; `hilclaw/local_run.py` lines 85-110; `hilclaw/selfcheck.py` lines 1-100 and `main` (the style of a `python -m hilclaw.<module>` command: streams as arguments, a fixed exit-status table, one line on standard output); `hilclaw/json_text.py` (if the report is serialised through it).
- Tests: `tests/test_standin_container.py` (stub client pattern), `tests/test_selfcheck.py` (testing a command's `main` with injected streams).

## Acceptance Criteria

1. **Command.** `python -m hilclaw.toolchain_check [<image> ...]`, implemented by `main(argv=None, *, stdout=None, stderr=None, ...)` in `hilclaw/toolchain_check.py`. The executor may add keyword-only test seams, for example the probe table, the container client and the time limits. Arguments are image references, checked as `standin_container.check_image` checks them. A refused argument writes one line to standard error and returns a usage status before anything starts. Running the module calls `main` and exits with its status.
2. **Report.** Standard output gets exactly one JSON document and one LF; key order and whitespace are the executor's. The document holds:
   - `host`: one entry per registered component, keyed by component name;
   - `images`: one entry per named image, keyed by reference, each holding its own component entries.

   A component entry has `state` set to `present`, `absent` or `unreadable`. `version` is a string when present and `null` otherwise, and `message` is a short text for `absent` and `unreadable`. An image whose container could not be used has the image-level `state` `unreadable` with a message and no component entries. The report holds no path of the checkout, no environment value and no token. The module docstring documents the format; it is no data-plane format and no `schema_version` is introduced.
3. **Read only.** Each probe is assembled and interpreted by its adapter's probe pair from T-0541 and executed by `local_run.run` (host) or `run_in_container` (image), each with a time limit that is a module constant. The command installs, pulls, downloads and updates nothing. It starts no `claude` and sets no environment variable. Apart from its report, it writes nothing, with one exception: if `run_in_container` needs a host directory to mount, the command uses one fresh empty temporary directory per call. It removes that directory before returning, whatever happened, and the executor names this in `## Result` as the reading of decision 7's "writes nothing but its report". Devices are probed on the host only.
4. **Exit statuses.** These are fixed module constants, documented in the docstring:
   - 0 when the report was written and every entry is `present` or `absent`. A missing component is a reported fact, not a failure (decision 7);
   - one distinct non-zero value when the report was written but some entry or image is `unreadable`;
   - a usage value;
   - a fault value for the command's own error or a standard output it cannot write.

   None of the values is 1 or 2, the interpreter's. Standard error gets one fixed line only when no report was written.
5. **Registration for later targets.** Components are found through one table of the module (name to the adapter's probe pair and program). P3-9 and P3-10 add entries to it. In this task it holds `clang` only, from `hilclaw/clang_adapter.py`. If T-0541's probe pair needs a small addition for the command (for example a program argument for the image case), it is made in `hilclaw/clang_adapter.py` with its tests.
6. **Tests.**
   - The real `clang` is reported `present` with the same version line `clang_build.compiler_version` reads.
   - A table entry whose program path does not exist is `absent`.
   - A fault script that hangs or prints no line is `unreadable` (ADR-0194 decision 6 rules for scripts).
   - A stub container client covers each image case: present, absent, unreadable, and a client that cannot be found (image `unreadable`). The test also shows the container arguments carry ADR-0144's no-network and no-pull options, as `run_in_container` gives them.
   - Each exit status is covered, including an unwritable standard output.
   - A refused image argument is covered.
   - The temporary directory is removed, if one is used.

   Every public function is covered with happy, error, branch and negative cases. Package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally.
7. **Nothing else changes.** No `Target`, backend, tool, `step` value, data-plane file or member changes. `cpu_standin` and `virtual_npu` are untouched. Existing tests pass unchanged apart from DRIVER §5 D21 list assertions; none are foreseen, and any edited assertion is listed in the PR body.
8. **Toolchain reading (D29).** Run the new command on the development machine (host only, plus any image already present that the executor chooses to name), and copy its report into `## Result`. Nothing is installed.
9. **`## Result`** states:
   - the language line;
   - the report format and exit statuses as landed;
   - the command's output on the development machine;
   - the temporary-directory reading, if used;
   - in Korean, in the form of `PROCESS/RuntimeAcceptance.md`'s other items (source `P3-8`, basis task T-0542), the runtime acceptance item for the driver to register (D22): on each C-7 machine kind (native Linux, macOS Docker Desktop, Windows WSL), the command reports the host's and a named image's `clang` correctly. It also returns 0 with a component `absent` when that component is missing, and starts no network access or pull for an image.

## Out of Scope

- Probes for `nvcc`, `nvidia-smi`, QNN tools or any device (P3-9, P3-10).
- Storing the report, filling a hw_profile `toolchain` from it, or a runtime step that calls it (OD-26; owner where it changes a frame).
- Asking permission for or installing what is missing (FR-4, NFR-4 — the runtime's).
- Any edit of `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md`.

## Follow-ups

- P3-9 and P3-10 register their adapters' probes in this command's table.

## Result
