---
id: T-0576
title: PLAN P3-16 (5a) — ADR-0207 slice 5, first half: install the NVIDIA Container Toolkit and pull the CUDA image on this machine, add the `--gpus all` option to the container start, the `cuda_gpu` image variable and the device check in a probe container, checked on the real GPU
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0095", "HQ-0096", "HQ-0097", FR-10, FR-19, OD-33, OD-14, NFR-4]
dependsOn: []
touchesFiles:
  - hilclaw/standin_container.py
  - hilclaw/cuda_image.py
  - hilclaw/cuda_adapter.py
  - tests/test_standin_container.py
  - tests/test_cuda_image.py
  - tests/test_cuda_adapter.py
estimatedSize: {loc: 260, files: 3}
hq: [HQ-0105]
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that a CUDA `gemm` kernel goes through build, correctness, measurement and record with the real `nvcc` and GPU (D29). **ADR-0207** (T-0572, PR #385) decides how. Slices 1 to 4 have landed (T-0572 to T-0575). This task is the **first half of slice 5** of its decision 9 (the runtime's GPU container, decision 7):

- the NVIDIA Container Toolkit installed and Docker configured on this machine, and the image `nvidia/cuda:13.1.2-devel-ubuntu22.04` pulled by digest and tagged `cuda:13.1.2` (decision 7; pre-allowed NVIDIA tools, D29);
- an option of `hilclaw.standin_container.run_in_container` that adds `--gpus all`;
- the environment variable that names the `cuda_gpu` image, with its reader;
- the device check of decision 6 run in a probe container of that image and device option.

**T-0577** (the second half) moves the `cuda_gpu` operations of `hilclaw/cuda_check.py` and `hilclaw/cuda_run.py` into containers on top of this. The slice is split at that boundary for two reasons. The install and the daemon restart may need the owner (criterion 2) and should not hold the operations' code in one PR. And the two halves together exceed the size recommendation (ADR-0207 estimated ~300 lines for the slice, without the operations' move).

**Slice 6** (default-table entry, run record, given-code bundle) waits on **HQ-0104** and is not planned.

**Order check (D27 ①)** at planning time (main `00253282`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`. P3-12 waits on HQ-0102 and HQ-0103, so P3-16 goes on (D31 ①).

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0100, HQ-0102, HQ-0103 or **HQ-0104**. Do not ask again HQ-0088 ① (c), HQ-0090 or #5 B-7. Which files of an attempt's `output/` a CUDA kernel is (a `.cu` name) is HQ-0104's question. This task does not touch it.

If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure: Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not. Owner-only parts here are:
- a data-plane frame change under D23;
- an install that is neither pre-allowed nor approved;
- an action that would disturb the owner's other work on this machine (criterion 2).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0576-<slug>`, the `Task: T-0576` trailer and the PR body's last line, size D30, tests D12, list assertions D21, **storage D29**: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0576/`; a tool image is tagged by tool name and version and kept).
- `PROCESS/DRIVER.md` §6 lines **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; NVIDIA tools from NVIDIA's official site are pre-allowed and installed without a request, with the command, version and URL in `Result`; a missing tool lands nothing and returns BLOCKED with an HQ; FR-19 ⑤ test skipping), **D27 ⑥ ⑦**, **D31**, §8 and §9.
- `PROCESS/PLAN.md`: P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0094 (① and ②: images, licences, storage), HQ-0095 (② (a)), HQ-0096 (② (a)), HQ-0097 ((a) (i)), **HQ-0104** and **HQ-0105** (its `decision`: the owner did the install, the configuration and the daemon restart of criterion 2 on 2026-11-15).
- `ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`: **all**, especially decisions 6, 7 and 9 (slice 5), and Consequences ("Readings for the owner to check", "Runtime acceptance items").
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` decisions 2, 5 and 6. `ADR-0168-od18-standin-container-situations.md` decision 3 (how statuses 125 to 127 are read). `ADR-0186-od14-standin-toolchain-from-image.md`. `ADR-0195-p3-14-storage-cleanup-and-cas-gc.md` decision 10 (tool image tags).
- `PROCESS/tasks/T-0572-cuda-target-design-and-device-unavailable.md` `## Result` (the machine facts: Docker Engine 29.1.3 inside WSL2, runtimes `runc` only, no `nvidia-ctk`, no CUDA image) and `PROCESS/tasks/T-0575-cuda-gpu-backend-operations.md` `## Result`.
- `PROCESS/RuntimeAcceptance.md` RA-0086 (the container items ADR-0207 left).
- Code:
  - `hilclaw/standin_container.py` (`run_in_container`, `check_image`, the option order)
  - `hilclaw/standin_image.py` (`read_image`, the model for the new reader)
  - `hilclaw/cuda_adapter.py` (`assemble_device_probe`, `interpret_device_probe`, `device_outcome`, `check_device`, `interpret_container_probe`)
  - `hilclaw/clang_adapter.py` `interpret_container_probe`
  - `hilclaw/cuda_profile.py` (`local_record(..., image=...)`: the toolchain read in an image)
  - `hilclaw/cuda_check.py` `confirm_device`
- Tests: `tests/test_standin_container.py` (the stub client and how options are asserted), `tests/test_standin_image.py`, `tests/test_cuda_adapter.py`.

## Acceptance Criteria

1. **Machine check first** (D29). Before writing, in WSL2 read and record in `Result`:
   - `docker version` and `docker context ls`;
   - `docker info` (runtimes, default runtime, CDI dirs);
   - `docker ps` (running containers and their images);
   - `nvidia-ctk --version` if present, and `nvidia-smi`;
   - whether `sudo -n true` succeeds;
   - the local CUDA images.
2. **The install** (ADR-0207 decision 7; pre-allowed, D29). Install the NVIDIA Container Toolkit from NVIDIA's apt repository as the [installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) gives it. Run `nvidia-ctk runtime configure --runtime=docker` and restart the Docker daemon. Record in `Result`:
   - every command, the toolkit version and the URLs;
   - the `/etc/docker/daemon.json` before and after;
   - the size added.

   **Stop conditions — do not work around.** If any of the following holds, land nothing and return **BLOCKED** (`new-external-dependency`) with an HQ (Korean, DRIVER §8). The HQ gives the exact commands for the owner to run, or asks when a restart is convenient.
   - `sudo` needs a password, or it is refused;
   - `docker ps` shows a running container this task did not start, since a daemon restart would stop it;
   - the repository or the package cannot be had.

   Do not edit any file under `.claude/`.

   **After HQ-0105.** The owner did the install, the `nvidia-ctk runtime configure` and the daemon restart (HQ-0105 `decision`). Do not install again. Read the installed state on the machine and record it with the `decision`'s facts in `Result`; the repository and the version differ from the guide's (the CUDA WSL repository, 1.19.0-1). No restart is left, so a running container this task did not start is no stop condition. `sudo` still needs a password: the stop conditions apply only to a further step that needs it.
3. **The image** (decision 7). Pull `nvidia/cuda:13.1.2-devel-ubuntu22.04@sha256:d8332c008e2ef270e82d286e5245e771f839645683075bba21ad9e4fa59dbcbb`. Tag it `cuda:13.1.2` and keep it as a tool image (D29; ADR-0195 decision 10).
   - Record in `Result` the tag, the digest, the size, the `nvcc --version` and `gcc --version` inside it, and the licence file paths inside the image (HQ-0094 ②).
   - If the digest is no longer listed, record what the registry lists and stop as in criterion 2: an image other than the record's is no pre-decided pull.
   - The image is never pushed or committed.
4. **`--gpus all` on the container start** (decision 7). `standin_container.run_in_container` gains a keyword-only argument, for example `gpus`, exactly a `bool`, default `False`.
   - `False` adds no option, so every existing caller's command stays byte-for-byte the same.
   - `True` adds `--gpus all` before the image, and every other ADR-0144 decision 6 option stays as it is: the one bind mount, `--network none`, `--pull never`, the numeric user, `--cap-drop ALL`, `no-new-privileges`, the entrypoint override, `--rm`, the forced removal.
   - A non-`bool` raises `TypeError` with `parameter` set, before anything starts.
   - Update the module docstring for the amended Q2 reading (decision 7: the build directory is the only host path the operation chooses and the only writable one).
5. **The image variable** (decision 7). A new module, for example `hilclaw/cuda_image.py`, names the `cuda_gpu` image by one environment variable. The name is this slice's choice, for example `HILCLAW_CUDA_IMAGE`.
   - Its reader behaves as `standin_image.read_image`: unset or empty gives `None`, a value `check_image` refuses raises a fixed-text error, and the text never quotes the value.
   - The module names no image. Acquiring the image on a user's machine stays the user's permission (NFR-4; HQ-0094 ①). Say so in its docstring.
6. **The device check in a probe container** (decision 6). Add to `cuda_adapter` a function, for example `check_device_in_container(image, build_dir, *, timeout_s, removal_timeout_s, client="docker")`. It runs the existing device query (`nvidia-smi` with the query arguments of `assemble_device_probe`) through `run_in_container(..., gpus=True)` and returns a `vendor_adapter.Outcome` that `cuda_check.confirm_device`'s caller can turn into the `device_unavailable` tool failure.
   - A GPU line read as `interpret_device_probe` reads it means a usable device.
   - Statuses 125, 126 and 127, a time limit, any other non-zero status and no readable device line all mean `device_unavailable`. Status 125 covers a container that cannot be given the GPU (decision 6) and also an image absent under `--pull never`.
   - An exception `run_in_container` raises before the start (for example no client on `PATH`) is placed as `device_unavailable` too, with the probe's fixed message showing no path, image or name (ADR-0060 decision 5). This is the reading "the operation cannot confirm a usable device".
   - If ADR-0168's reading of these statuses conflicts with this, write the conflict in `Result` and follow ADR-0207 decision 6, which is the later and specific record. If no record covers the case, return BLOCKED under DRIVER §3 rather than inventing.
   - Whether the probe uses the call's build directory or one of its own is your choice; say which in the docstring.
7. **No caller changes.** `cuda_check`, `cuda_run`, `check_definition.default_table`, `cpu_standin`, `virtual_npu` and the mock behave and answer exactly as before (T-0577 wires the operations). A call about `cuda_gpu` through the default registry stays `no_backend`.
8. **The real GPU** (FR-19 ⑤). After the install and pull, tests show three things on this machine:
   - `check_device_in_container("cuda:13.1.2", …)` gives a usable device;
   - a `run_in_container(..., gpus=True)` of the image builds `tests/cuda_fixtures/scale.cu` (or another existing fixture) with `nvcc -O2 -arch=native` in the build directory and runs it;
   - the same run with `gpus=False` does not see the GPU.

   These tests skip with a stated reason where Docker, the image, the toolkit or a usable GPU is absent, so CI skips them. In addition, record by hand in `Result` what you observe inside a `--gpus all` container of the image:
   - no checkout path is visible;
   - the driver mounts are read-only;
   - no writable host path exists but the build directory;
   - the network is none.

   This is evidence for RA-0086 (1), not its closure. It is closed only by the owner.
9. **Tests** (D12): happy, error, branch and negative cases for every new or touched public function, with the stub client of `tests/test_standin_container.py` and a stub `docker` on `PATH`. Cover:
   - the `gpus` option present and absent, and a non-`bool` value;
   - each probe outcome: a GPU line, 125, 126, 127, another status, a time limit, an empty or unreadable output, no client;
   - the image variable unset, empty, valid and refused, and a non-mapping `environ`.

   Existing tests stay unchanged except list assertions under D21. Foreseen: the public-name pins of `cuda_adapter` and `standin_container`. List every edit in the PR body.

   Verification: the full suite passes in WSL2 with the CUDA `bin` on `PATH`; `hilclaw/` line and function coverage is ≥ 80%; `ruff check` and `ruff format --check` pass.
10. **Process**:
    - Follow the dev-item-address steps. Open a Draft PR and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names criteria 2 (stop conditions), 4 (no change for existing callers) and 7 (no caller changes).
    - Once CI is green, self squash-merge with the PR body's last line `Task: T-0576`.
    - No ADR is written, because ADR-0207 decides this slice. If a choice outside it turns out to be a design OD, return BLOCKED under DRIVER §3.
    - In `Result` record:
      - the language and reason;
      - the machine outputs;
      - the install and image records of criteria 2 and 3;
      - the real-GPU results with tool versions;
      - any HQ;
      - any runtime acceptance item (D22). RA-0086 already holds ADR-0207's container items; add one only for a new fact.
    - Remove the task directory with `rm -r` and any work image by its tag (D29). Keep `cuda:13.1.2` and the toolkit.

## Out of Scope

- Moving the `cuda_gpu` operations of `cuda_check` and `cuda_run` into containers, and the waiter build with `nvcc` (T-0577).
- Slice 6 and HQ-0104: `.cu` attempt names, the CUDA given-code bundle, `instance_start` true, the default-table entry, `run.commit` of a CUDA run.
- Any install on a user's machine or any change of the runtime's environment checks beyond the reader above.
- bf16 at CUDA, `model_run`, GPU memory figures (HQ-0090), the coder's CUDA path (HQ-0088 ① (c)), retries (OD-17).
- Starting `claude` in any form (D16); a test run (D25).

## Follow-ups

## Result

DONE — PR #389 squash-merged as `1f4e2faf`; review 1 round (Approve, 3 nits; the message-wording nit applied after Approve under D20, the other two left). No HQ. No new RuntimeAcceptance item.

Earlier attempt (2026-11-14): BLOCKED (`new-external-dependency`) on criterion 2 because `sudo -n true` needed a password; HQ-0105 asked the owner to install the toolkit. Resumed 2026-11-15 after HQ-0105 (a).

**Machine check (criterion 1, WSL2 Ubuntu 22.04.5, kernel 6.18.58.1-microsoft-standard-WSL2, 2026-11-15T10:19Z)**
- Docker Client/Engine 29.1.3; context `default *` (unix:///var/run/docker.sock).
- `docker info`: runtimes `io.containerd.runc.v2 nvidia runc`, default `runc`; CDI spec dirs `/etc/cdi`, `/var/run/cdi` (no CDI spec present, per HQ-0105).
- `docker ps`: no running container (the owner's `g5c`, `j9-x86`, `j9-arm`, `x3-5182` stayed Exited after the owner's restart; not touched).
- `nvidia-ctk --version`: 1.19.0 (commit ec7b4e2f). `nvidia-smi`: NVIDIA GeForce RTX 4070, 12282 MiB, driver 615.78.02 / KMD 617.14, CUDA UMD 13.4.
- `sudo -n true`: "a password is required" (still). No step of this task needed sudo.
- Local CUDA images before the pull: none. 128G free on `/`.

**Install (criterion 2), done by the owner under HQ-0105 (a); not repeated**
- Commands the owner ran: `sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit`; `sudo nvidia-ctk runtime configure --runtime=docker`; `sudo systemctl restart docker` (daemon back at 2026-11-15T10:02:05Z).
- Source: NVIDIA's CUDA WSL apt repository `https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64` (keyring `/usr/share/keyrings/cuda-archive-keyring.gpg`), not the guide's `nvidia.github.io/libnvidia-container` repository; guide: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html (lists 1.20.1-1).
- Re-read on the machine: `apt-cache policy` installed/candidate 1.19.0-1 from that repository; dpkg log 2026-11-15 18:58:41 KST (09:58:41Z) installs `libnvidia-container1`, `libnvidia-container-tools`, `nvidia-container-toolkit-base`, `nvidia-container-toolkit`, all 1.19.0-1; binaries `/usr/bin/nvidia-ctk`, `/usr/bin/nvidia-container-runtime`.
- Size added: Installed-Size 67 + 3725 + 4613 + 25885 = 34290 KiB.
- `/etc/docker/daemon.json` before: absent. After: `{"runtimes": {"nvidia": {"args": [], "path": "nvidia-container-runtime"}}}`.

**Image (criterion 3; tool image, kept)**
- `docker pull nvidia/cuda:13.1.2-devel-ubuntu22.04@sha256:d8332c008e2ef270e82d286e5245e771f839645683075bba21ad9e4fa59dbcbb` (Docker Hub, https://hub.docker.com/r/nvidia/cuda; the pinned digest was still listed and pulled), then `docker tag ... cuda:13.1.2`.
- Tag `cuda:13.1.2`; RepoDigest `nvidia/cuda@sha256:d8332c00...dbcbb`; image id `sha256:1efffc671e20f111753d134230188163113cbf3e263f85df66d55f31b99afc1f`; linux/amd64; size 6954322204 bytes (6.95 GB). The digest reference shows as `nvidia/cuda:<none>` with the same image id (one copy).
- Inside: `nvcc` "Cuda compilation tools, release 13.1, V13.1.115" (Build cuda_13.1.r13.1/compiler.37061995_0); `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- Licence files inside the image: `/NGC-DL-CONTAINER-LICENSE`, `/opt/nvidia/entrypoint.d/30-container-license.txt`, per-package `/usr/share/doc/cuda-*/copyright`, `/usr/share/common-licenses`.
- Never pushed or committed.

**Code (PR #389)**
- `hilclaw/standin_container.py`: `run_in_container(..., gpus=False)`; `True` adds `--gpus all` before the entrypoint override; `False` adds nothing; non-`bool` -> `TypeError`, `parameter="gpus"`, before anything starts; docstring with the amended Q2 reading.
- `hilclaw/cuda_image.py` (new): `ENV_IMAGE = "HILCLAW_CUDA_IMAGE"`, `read_image`, `ImageRefusedError`; names no image.
- `hilclaw/cuda_adapter.py`: `interpret_device_container_probe`, `check_device_in_container(image, build_dir, *, timeout_s, removal_timeout_s, client="docker")`; the probe uses the caller's build directory and writes nothing there. Argument errors (`parameter`) and exceptions it does not place are raised; `ProgramNotFoundError`, `OSError`, `NoNumericUserError` and every container status but a GPU line are `device_unavailable`.
- ADR-0168 decision 3 vs ADR-0207 decision 6: no conflict (the probe runs no attempt code, so 125 to 127 are the runtime's, as for a build container).
- No caller changes (criterion 7). Existing tests changed (D21): none.
- Language: Python (the modules extended and their callers). Size: ~220 non-test lines, 3 files.

**Verification**
- Full suite under `coverage run --source=hilclaw` in a WSL2 clone of the PR head with `/usr/local/cuda/bin` on `PATH`: 42735 passed, 108 skipped (660 s). `hilclaw/` lines 19134/19197 (99.7%), functions 1812/1814; the three touched modules 100%. `ruff check` and `ruff format --check` clean. GitHub CI green on the final head. That full-suite run was on the head before the round-1 wording nit; after it, the CUDA, standin-container, cuda_image, cuda_check and cuda_run test files passed again (431) and ruff was clean.
- Real-GPU tests on this machine (RTX 4070, driver 617.14, toolkit 1.19.0, image `cuda:13.1.2` with nvcc 13.1 V13.1.115 and gcc 11.4.0), all passed: `check_device_in_container("cuda:13.1.2", ...)` -> GO_ON "NVIDIA GeForce RTX 4070 (driver 617.14)"; absent image -> `device_unavailable` (status 125); a `gpus=True` container builds `tests/cuda_fixtures/scale.cu` with `nvcc -O2 -arch=native`, runs it ("built") and `nvidia-smi` names the GPU; the same with `gpus=False`: no `/dev/dxg`, no `nvidia-smi` in the container, nvcc warns "Cannot find valid GPU for '-arch=native', default arch is used".
- Hand observation inside a `--gpus all` container of `cuda:13.1.2` with the ADR-0144 options (evidence for RA-0086 (1), not its closure):
  - no checkout path visible (`/mnt` and `/home` empty; no `/mnt/c` mount);
  - driver mounts read-only: `/usr/bin/nvidia-smi`, `/usr/lib/x86_64-linux-gnu/{libcuda.so.1,libnvidia-ml.so.1,libcudadebugger.so.1,libnvidia-gpucomp.so,libdxcore.so}` and 9 files below `/usr/lib/wsl/drivers/nvmdi.inf_amd64_.../` all `ro,nosuid,nodev`; `/dev/dxg` `ro,nosuid,noexec`;
  - writable for the container user (uid 1000) by a touch test of every mount: `/build` (the bind mount) and the container's own tmpfs `/dev/shm`, `/dev/mqueue`; Docker's per-container `/etc/hosts`, `/etc/hostname`, `/etc/resolv.conf` are rw mounts but not writable by the user and are not host paths the operation chooses;
  - network none: only `lo` in `/sys/class/net`.
- No `claude` was started (D16); no test run (D25).

**Runtime acceptance items (D22).** None new; RA-0086 already holds ADR-0207's container items.

**Storage.** WSL `/tmp/hilclaw-driver/T-0576/` (clone, coverage data, logs, observation dir) and the Git Bash `/tmp/hilclaw-driver/T-0576/` were removed with `rm -r`. No work image was made. Kept: tool image `cuda:13.1.2` (6.95 GB) and the toolkit.

**nextTask hint.** T-0577 (second half of slice 5: the `cuda_gpu` operations of `cuda_check`/`cuda_run` in containers), which now has the toolkit, the image and `check_device_in_container`.
