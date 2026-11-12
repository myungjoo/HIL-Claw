# ADR-0204: How the development driver reaches the owner's LAN aarch64 machine — ssh with the authentication already in place, the destination read from one environment variable, a remote runner with a per-task remote directory, and records that do not name the machine; building there with the host's gcc instead of the clang of the ADR-0144 image is left to the owner (part of OD-26, for this one machine only)

## Status

- **Accepted on 2026-11-12** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor in task T-0567 and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the code landed with it.
- **It serves an owner-approved item**: PLAN P3-17, one of the items of the purpose-first reorder the owner accepted on 2026-11-12 (cited: PLAN, the paragraph above P3-15; DRIVER §6 D31). The owner named the machine in the chat quoted in the DRIVER D31 row and answered D31 E6 the same day ([#5 comment](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6816955774)): "Assessment Agent 과제에서 사용한 인증수단 재사용가능. ssh접속하면 됨."
- **Two kinds of content.** What an owner sentence, an accepted record or a requirement says is **cited**, with its source named. **Everything else is this record's own**: the variable, the runner's contract, the remote directory, the copy means, the reading of the machine's facts and every weighing.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `d6f99519`): HQ-0096 and HQ-0100. Neither is touched.
- **No file, member, value or version of the data plane changes**, and no runtime tool reaches the machine (decision 1). No `claude` process was started for it (D16).
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **PLAN P3-17** (the owner accepted the item; its wording is the integrator's): the means of reaching the machine and its record are decided by a §9 record for this one machine; #5 B-2 (the general LAN backend) and OD-26 stay the owner's; files on the machine live only in a per-task directory under the account's home and are removed when the task ends; other services' containers and files are not touched; measurements there are noisy; the address appears nowhere but in a quotation of the owner, and no account or authentication value appears anywhere; "있는 gcc와 host 실행으로 대신할지는 정해지지 않았다 — executor는 대신하지 않는다", and whether that substitution is the driver's to close is judged here first.
- **The read-only check of this task** (2026-11-12, through the means of decision 2; nothing was written there): `uname -m` `aarch64`, `uname -s` `Linux`, `uname -r` `6.6.28+rpt-rpi-2712`; `gcc (Debian 12.2.0-14+deb12u1) 12.2.0`; `GNU Make 4.3`; Python 3.11.2; no `clang` on the account's `PATH`; `docker version` answers client and server 26.1.3 for the account; four cores; load average about 1.4; governor `ondemand`. **No image of this repository or of `cpu_standin` is in the machine's image store**; the images there belong to other services or are base images of distributions and of a language toolchain. Whether any of them holds clang was not checked (no container was started there), and none was built for ADR-0144.
- **ADR-0035 decision 2** (cited): its values describe "the machine on which the kernel is built and run"; "a kernel built on one machine and run on another, and a stand-in reached on another machine" are not covered. **Decision 3**: "`toolchain` has exactly one member, `clang`", whose value is the first line of `<compiler> --version` of "the clang with which the kernels of the profile are built".
- **ADR-0144** (cited): decision 4, "No build or process on the host, ever, for these runs"; decision 5, the compiler "is the image's `clang`", the image is named by one environment variable, pull policy `never`. **ADR-0186** (cited): `toolchain.clang` of those runs is read in a container of that image.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

The one LAN aarch64 machine the owner named for the driver's demonstration (DRIVER §6 D31 ③), reached by the development driver's tasks of PLAN P3-17. It is **no backend of a run**: no tool of FR-10, no `sim.run` or `board.run`, no backend table entry and no hw_profile reaches it through this record. The code is `hilclaw/remote_run.py` and the remote part of `hilclaw/toolchain_check.py`.

### 2. The means

- **The ssh client already on the development PC, with the authentication already set up there for the owner's other project** (cited: E6). No key, account, agent, ssh configuration or `known_hosts` entry is created or edited, and no password or passphrase is typed or stored.
- **Non-interactive, host keys checked as configured**: every call passes `BatchMode=yes` and no option that weakens host-key checking (no `StrictHostKeyChecking=no`, no other known-hosts file). A host whose key is unknown or changed is an ssh failure (decision 4), not a prompt.

### 3. Where the destination is read

- **One environment variable, `HILCLAW_AARCH64_SSH`**, holds one ssh destination as the caller's own ssh client resolves it: an alias of the caller's ssh configuration, or a destination of the form ssh documents. Nothing of the repository holds its value.
- **Unset or empty**: the runner raises its "not configured" error before anything is started; the environment check reports the state `not_configured`; the test that reaches the machine is skipped (so in CI).
- **A value that begins with `-` or holds a character outside 0x21 to 0x7E is refused** before anything is started, since ssh could read it as an option or split it. The refusal's text does not repeat the value.
- **Weighed**: a member of the committed `hilclaw.config.json` or a constant of the package would put the machine's name into every checkout and commit, which PLAN P3-17 forbids; a task file is committed as well. An environment variable is the source ADR-0144 decision 5 (c) chose for the same reason (a machine's value, no committed value).

### 4. The runner's contract

- **An argument list, never a command string.** Each argument is quoted for the remote POSIX shell (single quotes, a single quote written as `'"'"'`) and the quoted words are joined by spaces into the one command ssh hands to the account's shell, so that every argument reaches the remote program as one word with no expansion, globbing or redirection. An argument must be a `str` without a NUL character.
- **ssh options**: `-q`, `-T`, `-o BatchMode=yes`, `-o ConnectTimeout=15`, then `--` and the destination. **A time limit is required** and must be positive and finite; at the limit the local ssh process is killed (`hilclaw.local_run.run`). Whether the remote program then ends is not known to the runner (a stated limit).
- **The result mirrors `hilclaw.local_run.RunResult`** where it applies — exit status, timed out, stdout and stderr bytes, the command, wall-clock time — and adds **`ssh_failed`**. Status **255** is ssh's own failure (OpenSSH documents 255 for an error of ssh itself: a refused connection, a host-key mismatch, a refused authentication): `ssh_failed` is true, the status is `None`, and stdout and stderr are dropped, since ssh's own messages name the host. **A remote program that itself exits with 255 cannot be told apart and is reported as an ssh failure** (a stated limit). Any other status is the remote program's, and its output is passed on unchanged.
- **Refused before ssh is started**: an empty argument list, an argument that is no `str` or holds a NUL character, a time limit that is not a positive finite number, an unset or refused destination, a task id not of the form `T-NNNN`, and a path that leaves the task directory (decision 5).

### 5. The remote working directory and copies

- **One directory per task, `hilclaw-driver/T-NNNN/`, relative to the account's home** (where ssh starts the remote command; no `~` is expanded, since arguments are quoted). The task creates it (`mkdir -p`) and removes it with `rm -r` of that one directory — never `-f`, never another path (D29 applied to this machine, cited: PLAN P3-17). A directory left by a task that died is reused or removed by the same task when it resumes. Their shared parent `hilclaw-driver/` stays, empty between tasks, as the local `${TMPDIR:-/tmp}/hilclaw-driver/` does.
- **A path inside it** is one or more components of letters, digits, `.`, `_` and `-`, separated by `/`, none of them `.` or `..`. Anything else is refused.
- **Copies use the same ssh call**: a file is sent as the standard input of `sh -c 'cat > "$1"'` with the path as `$1`, and fetched as the standard output of `cat <path>`. The bytes are held in memory. `scp` is not used: it would be a second program with its own option and path rules (a local path with a drive letter reads as a host on Windows), for no gain at the sizes of a kernel and its harness.

### 6. What a record says about the machine

- **No address, account, key path or destination value** appears in any return value, error text, report, log, test output, ADR, task file, commit or pull request. The command a result reports holds the fixed placeholder `<destination>` in place of the destination; ssh's own failure text is dropped (decision 4).
- The machine is described only by what it reports about itself: `uname -s`, `uname -m` and the version lines of the components (decision 8). The only place its address may appear is a quotation of the owner.

### 7. Measurements there are noisy

The machine runs other services, and its frequency governor is `ondemand` (this task's check, Context). Timings taken there are **not presented as stable numbers**: a later task that measures there states this note with its values and compares nothing across machines.

### 8. The remote environment check

`hilclaw.toolchain_check.remote_check` reads, through the runner, `uname -s` and `uname -m` and then every component of `COMPONENTS` (the same table and the same adapter `assemble_probe`/`interpret_probe` parts as the host check — no second list of commands; the device query included, since the remote machine is a host). A remote status 126 or 127 (the shell's statuses for a program it cannot run or find) is `absent`, as in a container (cited: ADR-0194 decision 3 via `clang_adapter.interpret_container_probe`); any other status is read by the adapter as on the host. An unset destination is the report state `not_configured`, an ssh failure the state `unreachable`; neither raises. It installs, pulls, starts no container and writes nothing on the machine (cited: ADR-0194 decision 7, "It reads and never changes").

### 9. The judgment PLAN P3-17 asks for: gcc on the host instead of clang in the image

**Question**: may the next task build `cpu_standin` kernels on this machine with its gcc and run them on its host, instead of with clang in the image of ADR-0144? **Answer: no — it is not the driver's to close; it is put to the owner** (task T-0567's `Result`, DRIVER §8). Weighed:

- **#5 A-7 ②, "clang as the single toolchain"** (cited through ADR-0035 decision 3 and ADR-0144 decision 5), and **C-7 ⑥, "C + clang"**: an owner answer of #5, which §9 keeps for the owner. A gcc build of a `cpu_standin` kernel goes against its words.
- **ADR-0035 decision 3**: `toolchain` has the one member `clang`, naming the compiler that builds the kernels. A gcc build would need either a value of `clang` that names gcc (a changed meaning of a member) or a member `gcc` in place of `clang`; under D23 (cited) the first is a change of a value's meaning and so a frame change, and the second leaves the one-member rule that the owner's A-7 grounds. Neither is the driver's.
- **ADR-0144 decisions 4 and 5 and ADR-0186**: the builds and processes of a run are carried out in a container of a named image, never on the host, and `toolchain.clang` is read in that image. A host build is the fallback decision 4 refuses. A demonstration that does not follow them does not show that "the C kernel path of `cpu_standin`" runs there.
- **What the machine offers without an install**: gcc and Docker, no clang and no image of ADR-0144 (Context). Following the records there needs an image built or pulled on the machine, or clang installed on it — each an install that D31 ③ and D29 leave to the owner's approval (cited: PLAN P3-17, "설치나 내려받기(컨테이너 이미지 포함)가 필요해지면 D29의 요청 경로대로 HQ로 올린다").

The question is open and **the next task of PLAN P3-17 (build, correctness and measurement on the machine) waits on the owner's answer**. Nothing is substituted in this task.

### 10. A-13 reading

No data-plane file, member, value or version changes; no runtime tool, backend entry or hw_profile is added. No new external dependency: the ssh client is already on the development PC and its use is the owner's answer (E6); the code uses the Python standard library only. The new environment variable is no data-plane file and no committed value.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | The destination in `hilclaw.config.json` or a package constant | Names the machine in every commit and checkout (PLAN P3-17). |
| 2 | Pass a command string to ssh | The remote shell would expand and split it; an argument list with quoting has no such surprise. |
| 3 | Copy with `scp` | A second program and path syntax (Windows drive letters read as hosts); the ssh call already carries bytes both ways. |
| 4 | Keep ssh's failure text, with the address masked | A mask must know every form ssh prints the host in; dropping the text is complete. |
| 5 | Build with gcc on the host now and record `toolchain` as `clang` | States a compiler that built nothing (ADR-0186's reason) and crosses A-7; the owner's (decision 9). |

## Consequences

- A driver task with `HILCLAW_AARCH64_SSH` set can run commands and keep files in its own directory on the machine, and read its environment with the same component table as the host check.
- A remote program's own exit status 255 is reported as an ssh failure.
- A timed-out remote program may outlive the call on the machine; a task removes its directory at its end either way.
- PLAN P3-17's C kernel path waits on the owner's answer to decision 9.

## Boundaries (not decided here)

- **#5 B-2** (owner): the general LAN backend, endpoints, transport, quota and reservation, and a `board.run` or `sim.run` over the network.
- **The rest of OD-26**: registration, its schema, who registers and how.
- **OD-18 ⑫**: the emulated `sim.run` of a board of a non-native ISA.
- **The hw_profile of a kernel built and run on this machine** and the separation of its records by key (ADR-0001; ADR-0035 decision 2's "not covered"): the next task of PLAN P3-17.
- **Decision 9's question** (owner) and **what may be installed on the machine** (D31 E6's unanswered part).
- Any other machine or accelerator.

## References

- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decisions 2 and 3), [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) (decisions 4 and 5), [ADR-0186](ADR-0186-od14-standin-toolchain-from-image.md), [ADR-0194](ADR-0194-od33-vendor-stack-evaluation-design.md) (decisions 3 and 7).
- Requirements: C-7 (⑤, ⑥), FR-10, OD-26; PLAN P3-17; DRIVER §6 D29, D31, §9.
- Code: `hilclaw/remote_run.py`, `hilclaw/toolchain_check.py` (`remote_check`).
