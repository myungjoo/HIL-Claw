# ADR-0205: The given-code evaluation of `cpu_standin` on the owner's LAN aarch64 machine — the owner's answer to HQ-0101, an arm64 image built there and kept as a tool image, the package run there with the host's Python, `host.cpu` from `lscpu` where `/proc/cpuinfo` has no `model name` line, and the records of that machine kept apart by key (part of OD-26 and of OD-4, for this one machine only)

## Status

- **Accepted on 2026-11-14** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor in task T-0568 and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the code landed with it.
- **It serves an owner-approved item**: PLAN P3-17 (cited: PLAN, the paragraph above P3-15; DRIVER §6 D31 ③).
- **Two kinds of content.** What an owner sentence, an accepted record or a requirement says is **cited**, with its source named. **Everything else is this record's own**: the image's recipe and tag, where the package runs, the `host.cpu` rule for a Linux machine without a `model name` line, the comparison of the two machines' records and every weighing.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `f163e8dd`): HQ-0096 and HQ-0100. Neither is touched.
- **No file, member, value or version of the data plane changes** (decision 9). No `claude` process was started for it (D16).
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0204 decision 9** asked the owner whether that machine may build `cpu_standin` kernels with the host's gcc; the driver recorded the question as HQ-0101 with the options (a) clang installed on the host by the owner, (b) a `cpu_standin` image (arm64, with clang) built or pulled on the machine, (c) gcc on the host with a `gcc` member in `toolchain`.
- **The read-only check of this task** (2026-11-14, by the means of ADR-0204 decision 2; nothing was written there): `uname -m` `aarch64`, `uname -r` `6.6.28+rpt-rpi-2712`; `/etc/os-release` `ID=debian`, `VERSION_ID="12"`; **`/proc/cpuinfo` has no `model name` line** (its processor lines carry `CPU implementer` `0x41` and `CPU part` `0xd0b`); `lscpu` is present and reports `Model name: Cortex-A76`; Python 3.11.2 with **`numpy` 1.24.2 importable**; git 2.39.5; Docker client and server 26.1.3, `arm64`; four cores; load average about 1.5 to 2.6; governor `ondemand`; about 250 GB free under the account's home. The image store held 16 images of other services and of distributions, none of `clang`, of this repository or of `debian`; they were not touched.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. The owner's answer to HQ-0101

**(b)** (cited: HQ-0101 `decision` in `PROCESS/STATE.json`; the owner's answer "허용" to the question "aarch64 머신에서 Docker 이미지 내려받기·빌드를 허용할까요?", [#5 comment](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6858780049)). The permission covers pulling and building on that one machine the container images this demonstration needs, including the base image a build pulls and the packages put into the image; host packages and any other download stay on D29's request path (cited: the same `decision`; PLAN P3-17). (a) and (c) were not taken: #5 A-7, ADR-0035 decision 3 and ADR-0144 decisions 4 and 5 stay as they are.

### 2. The image

- **Recipe** (two lines, built in `hilclaw-driver/T-0568/image/` on that machine):

  ```
  FROM debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc
  RUN apt-get update && apt-get install -y --no-install-recommends clang libomp-dev libc6-dev && rm -rf /var/lib/apt/lists/*
  ```

  The base is Debian 12, the machine's own release, pinned by digest. It gives `clang` as `clang` (Debian `clang-14` 14.0.6), the C and mathematics libraries (`libc6-dev`), and `<omp.h>` with the OpenMP runtime (`libomp-14-dev`), as ADR-0144 decision 5 and ADR-0188 require. It is native `arm64`, sets no `USER` and no entrypoint, and runs as any numeric user with no capability (ADR-0144 decision 6, unchanged).
- **Build**: `DOCKER_BUILDKIT=0 docker build --force-rm --pull=false -t <tag> .`. The classic builder removes each intermediate container itself and leaves no BuildKit cache records, so nothing of the build stays outside the image, and no prune is needed. Only `docker pull` of the base and the package download inside `docker build` use the network. Every container of the evaluation keeps ADR-0144 decision 6 (`--network none`, `--pull never` and the rest).
- **Kept as a tool image**, tag **`clang:14.0.6`** (D29; the `<tool>:<version>` form of ADR-0195 decision 10). The image holds a tool and was built only with the owner's permission. Building it again for each task would download the same packages again. Later P3-17 tasks reuse it. Its retirement follows P3-14's rule (ADR-0195 decision 10, with the owner's approval). The task's work tag is removed at the end, and so is the base image's reference, which no other image on the machine used (DRIVER §5, D29).
- **The recipe is not committed as a file.** It is kept in the remote task directory while the task runs (then removed) and quoted here and in the task's `Result`. A Dockerfile in the repository would read as the runtime's image, which ADR-0144 decision 5 leaves unadopted ("No concrete image is adopted"; OD-14 ① (나)). A quotation in a record of one demonstration adopts nothing.

### 3. Where the package runs

**On that machine, with the host's `python3`**: a snapshot of the checkout (`git archive` of `hilclaw/`, `catalog/` and `hilclaw.config.json`, no `.git`) is unpacked into `hilclaw-driver/T-NNNN/package/`, and `python3 -m hilclaw.given_eval` runs there against a fresh data root `hilclaw-driver/T-NNNN/data/` (`git init` with a repository-local commit identity — no global git configuration on that machine). `HILCLAW_STANDIN_IMAGE` names the image of decision 2, so every build and process of the four runs in a container of that image on that machine (ADR-0144 decision 4, no host build or process). Weighed:

- **(i) host `python3`, chosen.** The machine's Python 3.11.2 meets `requires-python`, and its `numpy` 1.24.2 is already there, so nothing is installed. `pyproject.toml` pins `numpy` 2.4.6 for an install of the package, and no install is made here. The correctness reference is computed with 1.24.2; a difference that mattered would show as a failed check, and the reference check passed (decision 7).
- **(ii) the package in a container that holds Python and `numpy`.** HQ-0101 (b) would cover the image. But that container must start the build and process containers of ADR-0144 itself: it would need the machine's Docker socket, which gives root-equivalent control of every container of the other services there, and the same build-directory path inside and outside. Not taken.
- **(iii) an HQ for a host `numpy`.** Not needed: (i) needs no install.

**Why this is not #5 B-2's "`board.run` or `sim.run` over the network"** (cited: ADR-0204 Boundaries): ssh carries files and starts one command, as a person at that machine would. The run, its tools and its data root are all on that machine, as on any C-7 machine. No tool of a run calls another machine, no backend reaches across the network, and no run on the development PC uses that machine. The code is `hilclaw/remote_eval.py`. It reaches the machine only through `hilclaw.remote_run` (ADR-0204 decisions 4 to 6) and is no FR-10 tool and no backend entry.

### 4. The hw_profile of the demonstration

`accelerator` `cpu_standin`, `revision` `host`, `toolchain.clang` the first line of `clang --version` in a container of the image (ADR-0186): `Debian clang version 14.0.6`. `host` is read on that machine by ADR-0035 decisions 4 and 6 with decision 5 below: `{"cpu": "Cortex-A76", "os": "linux debian 12"}`. `hw_source` is stated by the caller (ADR-0035 decision 8): `external`. The kernel is built and run on that one machine, so ADR-0035 decision 2's "built on one machine and run on another" stays out of scope. `hilclaw.remote_eval.hw_profile` reads the record there with `hilclaw.standin_profile.local_record`.

### 5. `host.cpu` on Linux without a `model name` line

- **Rule** (extends ADR-0035 decision 4 for the case where its rule gives no value): under Linux and WSL, when `/proc/cpuinfo` has no `model name` line, `host.cpu` is the text after the first colon of the first line of the output of `lscpu`, started with `LC_ALL=C`, whose text before that colon, without spaces and tabs at both ends, is `Model name`. It is spelt by ADR-0035 decision 6 unchanged. A missing `lscpu`, a status other than 0, a time-out, no such line, or a value decision 6 refuses is a fact that cannot be read, and nothing is substituted. **A machine that has a `model name` line never starts `lscpu`**, so every value the old rule gave stays the same.
- **Why it is the driver's (§9) and not a frame change (D23)**: the member `host.cpu` and its meaning, "the model name the operating system reports for the processor" (ADR-0035 decision 4), stay as they are. `lscpu` is the operating system's own report: util-linux names the processor from its identification registers (`0x41`/`0xd0b` is Cortex-A76 here). No existing value changes its meaning or goes away, no member is added and no version changes. What changes is a source rule of ADR-0035, a §9 record of the driver, for a case it left without a value and expected (its decision 6, "Linux on a CPU whose `/proc/cpuinfo` has no `model name` line (reported for some ARM systems)"). The owner's answers it builds on (#5 A-7, B-4 ⑤, B-6) say nothing on the source of `host.cpu`.
- **Limits**: the value names the core, not the chip or the board. Two boards with the same core, but a different cache, memory or clock, share a key, in the same way as two x86 machines with one model name do (ADR-0035 decision 7). A machine with cores of two kinds is described by its first `Model name` line (ADR-0035 decision 7, "the first one").
- **Alternatives**: the board model of `/proc/device-tree/model` (`Raspberry Pi 5 Model B Rev 1.0`) names a board, not the processor, so it would change the member's meaning. Giving no `cpu_standin` hw_profile on such machines would leave PLAN P3-17 without a key to show.

### 6. The records of two machines kept apart by key

The remote data root comes back as one `git bundle` (`git bundle create --all` there, then `hilclaw.remote_run.get` into the local task directory). A clone of it is the data root of the development PC's evaluation of the same kernel and shape, run with that PC's own hw_profile and its own image. The two hw keys are then compared under `db/` of that clone (ADR-0001 decision 4: exact match; ADR-0004 decision 5). Nothing is merged into the data repository by hand, and the clone is removed with the task directory.

### 7. The demonstration (task T-0568)

One fp32 `gemm` kernel of the first case, the plain triple loop of `tests/test_given_eval.py`, shape `m`=`k`=`n`=32, tolerance `rtol` 1e-4 and `atol` 1e-5:

- **That machine**: exit status 0, `outcome` `measured`, `sim` and `board` `pass`/`verified`, `timing` `not_converged`, median 87694.5 ns. hw key `cpu_standin-68c4095051183d94`.
- **The development PC** (WSL 2, x64, image `hilclaw-standin:local`, clang 18.1.3): exit status 0, `measured`, both points `verified`, `timing` `converged`, median 5714 ns. hw key `cpu_standin-22128bf435888071`.
- **Per-key separation**: `db/` of the shared data root holds two key directories, one for each hw key, each with its own `hw_profile.json` and the same op_signature directory. The second run's commit touches neither the first key's directory nor the first run's files.
- **Measurement note** (ADR-0204 decision 7): the values from that machine are noisy. Other services run there, its governor is `ondemand`, and its load average was about 1.6 during the run. They are not compared with the development PC's values as numbers.

### 8. Storage on that machine

Files live only in `hilclaw-driver/T-NNNN/` under the account's home and are removed with `rm -r` of that one directory when the task ends (ADR-0204 decision 5). The tool image of decision 2 is the one exception (cited: PLAN P3-17). Work tags and named containers are removed one by one by tag or name. Nothing is pruned, and no other service's image, container or file is touched.

### 9. A-13 reading

No data-plane file, member, value or version changes (decision 5 says why the `host.cpu` rule is no frame change). No new external dependency: `numpy` and `lscpu` are already on that machine, and the image's packages are covered by the owner's answer (decision 1). The code uses the Python standard library and `git`.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | A work image tagged with the task id, removed at the end | Downloads and builds it again for every later P3-17 task; D29 keeps tool images. |
| 2 | BuildKit (`docker build` default) | Leaves build-cache records that only a prune removes. |
| 3 | The recipe as a committed Dockerfile | Reads as the runtime's image (ADR-0144 decision 5). |
| 4 | The package in a container with the Docker socket (decision 3 (ii)) | Root-equivalent control of other services' containers. |
| 5 | `host.cpu` from `/proc/device-tree/model`, or no record on such machines | Changes the member's meaning, or leaves no key to show (decision 5). |
| 6 | The two runs' data merged by hand into one repository | Error-prone and not needed; a clone of the bundle holds both. |

## Consequences

- A driver task with `HILCLAW_AARCH64_SSH` set can evaluate given code on that machine (`hilclaw.remote_eval`) and bring the data root back.
- `cpu_standin` hw_profiles can be read on Linux machines whose `/proc/cpuinfo` has no `model name` line. Machines that have one are unchanged.
- The image `clang:14.0.6` stays in that machine's image store.

## Boundaries (not decided here)

- **#5 B-2** (owner): the general LAN backend, endpoints, transport, quota and reservation, and a `board.run` or `sim.run` over the network.
- **The rest of OD-26**: registration and its schema, who registers and how; **OD-18 ⑫**: the emulated `sim.run` of a non-native board.
- **The runtime's image**: its adoption and acquisition (OD-14 ① (나), OD-8 ㉝ (가)).
- **Host installs** on that machine or any other (D29's request path).
- A kernel built on one machine and run on another (ADR-0035 decision 2); any other machine or accelerator.

## References

- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decisions 2 to 8), [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) (decisions 4 to 6), [ADR-0186](ADR-0186-od14-standin-toolchain-from-image.md), [ADR-0188](ADR-0188-od18-standin-openmp-in-the-build-set.md), [ADR-0195](ADR-0195-p3-14-storage-cleanup-and-cas-gc.md) (decision 10), [ADR-0200](ADR-0200-od33-given-code-evaluation.md) (decision 5), [ADR-0204](ADR-0204-od26-lan-aarch64-machine-reach.md).
- Requirements: C-7, FR-10, OD-4, OD-26; PLAN P3-17; DRIVER §6 D29, D31, §9; HQ-0101.
- Code: `hilclaw/remote_eval.py`, `hilclaw/standin_profile.py`.
