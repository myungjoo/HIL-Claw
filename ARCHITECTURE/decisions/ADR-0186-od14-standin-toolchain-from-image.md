# ADR-0186: When the `cpu_standin` builds of a run use the image of ADR-0144, the hw_profile's `toolchain.clang` is the first line of `clang --version` run in a new container of that image, not the host's clang; which machine `host` describes stays open (part of OD-14 sub-question ① (마), with OD-4)

## Status

- **Accepted on 2026-10-30** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9: written by the owner's integrator session after the owner asked in chat on 2026-10-30 to fix it ("Fix F4"), and accepted by the approval of a context-isolated reviewer. The owner has not confirmed the content of this record (§9: seven days for an objection from the owner's notice).
- **Two kinds of content.** What an accepted record says is **cited**, with its source named. **Everything else is this record's own**: the reading of ADR-0035 decision 3 for these runs, the way the line is read, and every weighing.
- **Why now** (observation, the owner-run test runs of 2026-10-30 under DRIVER D25): the nightly entry `hilclaw.nightly` read `clang --version` on the host (`Ubuntu clang version 14.0.0-1ubuntu1.1`), while every kernel of those runs was built by the image's clang (`Ubuntu clang version 18.1.3 (1ubuntu1)`). The cases those runs wrote are keyed by a compiler that built none of their kernels.
- **Answers** the `toolchain` part of OD-14 sub-question ① (마), "which machine the `cpu_standin` hw key values describe", for the runs of decision 1. The rest of ① (마) stays open (decision 3).
- **No member, file, kind or version of the data plane is added or changed, and no admitted value or meaning of a value changes.** The record keeps the members of ADR-0035 and the meaning of `toolchain.clang`; only where the stored line is read changes, and with it the line and the key of these runs.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0035 decision 3** (cited): the value of `toolchain.clang` is "the first line that the command `<compiler> --version` writes to standard output", "where `<compiler>` is the clang with which the kernels of the profile are built".
- **ADR-0144** (cited): decision 5, for the first-case builds and processes: "The compiler is the image's `clang`", found by the image's own environment "under the name `clang`"; the user names the image in one environment variable (same decision; `HILCLAW_STANDIN_IMAGE`). It leaves open "Whether it must agree with the `toolchain` of the hw_profile" (ADR-0060 sub-question ⑱ (가) and OD-14 ① (마)).
- **The code before this record**: `standin_profile.local_record` ran `<compiler> --version` on the host, `clang` on `PATH` by default, and `hilclaw.nightly` required a host `clang` for that read alone.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

hw_profile records with `accelerator` `cpu_standin` made for a run whose `cpu_standin` builds and processes use the container of ADR-0144, with the image the maker of the record is given. Today the one such maker is `hilclaw.nightly`, which gives the image of `HILCLAW_STANDIN_IMAGE`.

### 2. `toolchain.clang` is read from the image

- **The value is the first line of standard output of `clang --version`, run as the program of one new container of the image** with the container options of ADR-0144 (`standin_container.run_in_container`: no network, `--pull never`, the caller's numeric user, no capabilities, an empty entrypoint), a new empty temporary directory as its build directory, and the time limit and the forced-removal limit of the record's other commands. The spelling of ADR-0035 decision 6 applies unchanged.
- **A container that cannot be started or fails after its start, a status other than 0 (the client's 125 for an image that is not there among them) or no end within the limit** is a fact that cannot be read (cited: ADR-0035 decision 6): no record is made. In `hilclaw.nightly` that ends the firing as `prepare/hw_profile`, an environment cause.
- **The host's `clang` is not read.** `hilclaw.nightly` no longer requires a host `clang` on `PATH`.
- **Why.** ADR-0035 decision 3 names the clang that builds the kernels, and ADR-0144 makes that the image's `clang` under that name. Reading the line in the same image under the same name names that compiler, with no rule of its own about which compiler is meant.

### 3. What this does not settle

- **A moved tag.** A reference can name another image between the read and a build (cited: ADR-0144 decision 5, "One reference is not always one image"). The record then names the compiler of the image at the read. Recording the image's identity is ① (나).
- **No check at build time.** Nothing checks that a build used the compiler the record names. ADR-0060 sub-question ⑱ (가) stays open.
- **`host.cpu` and `host.os`** are still read from the machine that runs the process, as before. Whether they describe the container (its `/etc/os-release` is the image's) or the machine stays open as the rest of ① (마), with OD-4, as do the timings and memory of ① (마), beyond what ADR-0145 settled.
- Records made without an image (the `compiler` argument, for any other caller) are unchanged.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | Keep the host's clang | It names a compiler that builds nothing in these runs (Status, observation), against ADR-0035 decision 3. |
| 2 | Add the image reference to `toolchain` | A new member of the hw_profile record is a data-plane change (CLAUDE.md A-13), and the image's identity is ① (나). |
| 3 | Pass a `docker run … clang` prefix as the `compiler` of `local_record` | It would copy the container options outside `standin_container`, and a timed-out read would leave a container with no name to remove. |

## Consequences

- The hw_profile key of a nightly run now changes with the image's clang, not the host's. The cases written on 2026-10-30 under `<base>/data` are keyed by the host clang, and later runs do not read them: a cold start once.
- Reading the profile starts one container (about a second).
- A nightly machine needs no host `clang` ([PROCESS/NIGHTLY.md](../../PROCESS/NIGHTLY.md) §1).

## Boundaries (not decided here)

- The rest of OD-14 sub-question ① (마): which machine `host.cpu` and `host.os` describe, and the timings and memory beyond ADR-0145.
- Recording the image's identity (① (나)); a check that a build used the recorded compiler (ADR-0060 ⑱ (가)).
- Records for any other accelerator, and for runs whose builds do not use the ADR-0144 container.

## References

- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decisions 3 and 6), [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (sub-question ⑱ (가)), [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) (decision 5), [ADR-0145](ADR-0145-od14-first-case-container-measurement.md).
- Code: `hilclaw/standin_profile.py` (`local_record`, `image`), `hilclaw/nightly.py`.
