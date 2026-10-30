# ADR-0188: Every `cpu_standin` kernel build takes `-fopenmp`, with no trailing runtime flag and no thread variable; the waiter of ADR-0145 stays without OpenMP; an image without a usable OpenMP ends a nightly firing as `prepare/no_openmp`, and nothing is installed (the OpenMP parts of OD-18 sub-questions ⑱ (라) and ⑲ (라), after the owner's answer to HQ-0034)

## Status

- **Accepted on 2026-10-30** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9: written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed the design parts of this record** (seven days for an objection from the owner's notice on #5; an objection creates a task that reverts this record and the edits made with it).
- **Whose content.** The owner's answer below is quoted, marked **owner**, and is not re-decided. A sentence is **cited** when a record or a requirement is named with it. **Everything else is this record's own**: the flag and its place, which builds take it, the thread setting, the check and its message.
- **Answers** the OpenMP parts of OD-18 sub-questions ⑱ (라) and ⑲ (라) for the builds of decision 2: the flag, its runtime and the thread setting that goes with it, which [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md) decision 6 left open. A target-specific flag and a list of inherited variables stay open.
- **Its first code slice lands with it** (DRIVER §6 "task 단위" ①): `hilclaw/standin_settings.py`, `hilclaw/standin_run.py`, `hilclaw/standin_openmp.py`, `hilclaw/nightly.py`, [PROCESS/NIGHTLY.md](../../PROCESS/NIGHTLY.md) §1, the CI workflow and the tests.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Owner**, the answer (a) to HQ-0034 (T-0325), chat of 2026-10-25, as recorded in `PROCESS/STATE.json`: "모든 C-7 시스템에서 stand-in 커널이 OpenMP를 쓸 수 있게 한다. 고정 빌드 설정에 OpenMP 플래그와 런타임을 넣고, 런타임이 없으면 2026-10-15 승인 규칙에 따라 사용자 승인을 받아 설치한다(컨테이너는 그 이미지에)."
- **Cited.** #5 A-7 ②: OpenMP is allowed in stand-in kernels. [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) decisions 6 and 7: "Threads are allowed"; a kernel may include `<omp.h>`; the Completion row: a kernel has "finished all its work on the operands when it returns, including the work of any thread it started". [ADR-0107](ADR-0107-od16-verification-and-timing-build-relation.md) decision 3: "one compiler, one list of flags, one list of trailing flags and one environment" for the two kernel builds of an attempt, and one environment for their processes; each harness program is compiled in one call with the kernel. [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) decision 5: "The compiler is the image's `clang`"; the environment inside is the image's and no variable is handed in; the runtime never pulls or updates an image. [ADR-0145](ADR-0145-od14-first-case-container-measurement.md): the waiter is process 1 of the timing container, not dumpable, compiled alone, and from W3 to W5 it allocates nothing. [ADR-0186](ADR-0186-od14-standin-toolchain-from-image.md): a fact of the image's clang is read in a new container of that image. [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) decision 3: `toolchain` has no member for an OpenMP runtime. Requirements NFR-4 and FR-4: a change of toolchain or environment only with the user's permission; without it nothing changes.
- **What ADR-0116 decision 6 weighed has moved.** It kept OpenMP open because "the clang macOS has by default" refuses `-fopenmp` and needs another spelling. Under ADR-0144 decision 5 and ADR-0186 the compiler of these builds is the image's `clang` on every C-7 system, also under Docker Desktop on macOS. So the macOS default clang compiles none of these builds and one spelling serves. This was read from those records and from the code (`standin_check.COMPILER`, `standin_container.run_in_container`); it was not tried on macOS (runtime acceptance).

**Sources for the flag.**

| Fact | Source | Status |
|---|---|---|
| "`-fopenmp`, `-fno-openmp`: Parse OpenMP pragmas and generate parallel code." | https://releases.llvm.org/18.1.0/tools/clang/docs/ClangCommandLineReference.html | Verified on 2026-10-30, the document of clang 18 |
| "Use `-fopenmp` to enable OpenMP"; "`-fopenmp-simd` to enable OpenMP simd features only, without linking the runtime library" | https://clang.llvm.org/docs/UsersManual.html | Verified on 2026-10-30; the document names linking only by that contrast |
| `OMP_NUM_THREADS`: "the maximum number of threads to use for OpenMP parallel regions if no other value is specified"; `KMP_BLOCKTIME`: time a thread waits after a parallel region before sleeping, "Default: 200 milliseconds" | https://openmp.llvm.org/design/Runtimes.html | Verified on 2026-10-30 |
| The list of tools of the CI runner names clang 16 to 18 and no OpenMP runtime package | https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md | Verified on 2026-10-30 |
| With `-fopenmp` and no other flag, the image's `clang` links the runtime, also for a shared library, also when `-fopenmp` comes before the sources | The local image `hilclaw-standin:2026-10-29` (`Ubuntu clang version 18.1.3`, holds `libomp-dev`), one run on 2026-10-30 with the options of ADR-0144, and the tests of this slice on CI | Observation on one machine and on CI; on every other image **this record's expectation** |
| How many threads a run gets by default (the processors the container sees) | None read | **This record's expectation**, a runtime acceptance item |
| A kernel that uses no OpenMP starts no thread at load | None read | **This record's expectation** |

## Decision

### 1. The flag: `-fopenmp` at the end of the flags, and no runtime flag

- **`hilclaw.standin_settings.FLAGS` is `-std=gnu11 -O2 -ffp-contract=off -fopenmp`.** It stands before the sources, as ADR-0116 decision 3's flags do. `TRAILING_FLAGS` stays `-lm`: the driver links the runtime for this one flag, so no `-lomp` or `-lgomp` is named, and the set stays free of a runtime's name.
- **Why not `-fopenmp=libomp` or `-lomp`.** Either names one runtime, and an image whose clang defaults to another would be refused for no reason a kernel can see. **Its cost**: the runtime is the image's choice, and no commit names it (the cost of ADR-0144 decision 5, which holds for the C library too).
- **Why not `-fopenmp-simd`.** It leaves the runtime out, which the owner's answer puts in.
- All other values of the set are unchanged.

### 2. Which builds take it

| Build | Takes `-fopenmp` | Why |
|---|---|---|
| The kernel's verification build and timing build (with their harness programs) | Yes | ADR-0107 decision 3 holds: one list of flags in both. Each harness program is compiled in the same call with the kernel, so it takes the flag too; it has no pragma and calls no runtime function (observation). |
| The kernel libraries of the model executor | Yes, as far as the caller passes `FLAGS` as the kernel reference's flags (`attempt_kernel.kernel_reference`; ADR-0153 decision 3) | They are kernels. The library names the runtime it needs. |
| The model program and the forward program | No | They hold no kernel code and no pragma; the runtime reaches the process through the library they load. |
| **The waiter of ADR-0145** | **No**: `standin_settings.WAITER_FLAGS`, the flags of ADR-0116 decision 3 alone | See below. |

- **The waiter links no OpenMP runtime.** ADR-0145 relies on what the waiter does around the child's end: W1 makes it not dumpable, W3 to W5 allocate nothing and use no stdio, and decision 5 says the figure is "written by a program the kernel's code is not part of". A runtime linked into process 1 would bring its own initialisation, its fork handlers and whatever else it registers into the process that must stay small enough to reason about, and it would run before W0 and W1. The waiter has no pragma, so it gains nothing from the flag. ADR-0145's sentence "with the flags of ADR-0116 decision 3" stays exact as written.
- **ADR-0107's rule still holds**: it binds the two kernel builds of an attempt, and the waiter compiles no kernel source, and ADR-0170 decision 4 already reads that sameness as binding "the builds of the kernel sources only" (cited: its Consequences).

### 3. The thread setting: none; ADR-0116 decision 5 is confirmed

- **The backend sets no thread variable.** `standin_settings.ENV` stays `None`, and the container gets no variable (cited: ADR-0144 decision 5). `OMP_NUM_THREADS` and its neighbours are read from the image's environment if the image sets them; otherwise the runtime picks.
- **Alternatives.** `OMP_NUM_THREADS=1` would keep every kernel on one thread and answer the owner's "쓸 수 있게" in name only. A fixed number above 1 is a per-machine value in a set that may hold none (ADR-0116 decision 2). A number read from the machine at run time is a setting no commit names, handed in against ADR-0144 decision 6's "no variable handed in".
- **ADR-0107 decision 3 holds**: the verification process and the timing process of an attempt run with one environment, so an OpenMP kernel is verified and timed at the same default on one machine. A race that shows only under some thread timings can still pass one check; nothing here finds it.
- **The effect on NFR-3.** A kernel that uses threads shares more processors with whatever else runs, so its samples can vary more; workers of the LLVM runtime spin for up to 200 ms after a region, which also keeps processors busy between repeats. ADR-0007's rules and the warnings of NFR-3 stay as they are, and the imprecise-timing mark of ADR-0103 is unchanged. A kernel that uses no OpenMP should be measured as before: the runtime may be mapped, but no region runs (expectation).
- **The effect on the time limits.** ADR-0117's values are unchanged. They are figured from work, not threads, so a kernel that scales only has more room. A kernel that oversubscribes and overruns gets the limit's existing answer. `-fopenmp` adds no compile step that matters against the 60 s of a build (expectation). No limit depends on the thread count.
- **The memory figure** of a kernel that uses threads includes what its threads touch, which is what ADR-0052 means for one process. A kernel that uses no OpenMP may show the mapped pages of the runtime. The figure stays a measurement, not a bound.

### 4. An image with no usable OpenMP

- **Where it is found.** At the start of a nightly firing, right after the hw_profile record is read (ADR-0186) and before any run exists: `hilclaw.standin_openmp.check` writes a small OpenMP program into a new temporary directory, builds it in one new container of `HILCLAW_STANDIN_IMAGE` with `FLAGS` and `TRAILING_FLAGS`, starts it in a second new container, and removes the directory. Both use `standin_container.run_in_container`, so both have the options of ADR-0144 and one container per build and per process (cited: decision 3). Each has the 60 s of a build and the forced-removal limit of ADR-0169.
- **The outcome**: the firing ends with signature `prepare/no_openmp`, cause `environment` (PROCESS/NIGHTLY.md §5), and no run is started. Every failure of the probe has this one outcome, told apart in the detail: the container could not be started, a status other than 0 (the client's 125 to 127 among them), no end within the limit, or a failure after the start. Since the hw_profile read comes first, a missing image still ends as `prepare/hw_profile`.
- **What the user reads** (`result.json`'s `detail` and the issue body): that the named image cannot build and start an OpenMP program and which step failed; that every kernel build takes `-fopenmp`, so no kernel of a run would build; what is needed in the image; and "Nothing was installed or changed; add them to the image, or name another image, and start again." No text from the image or from a container's output is quoted.
- **Nothing is installed.** The owner's answer has the runtime installed "사용자 승인을 받아"; NFR-4 and FR-4 say that without permission nothing changes. This slice has no way to ask, so it reports and stops, and the user changes the image. What part of the runtime would ask, and how it would then obtain an image, stays open (cited: ADR-0144 decision 5; OD-8 ㉝ (가)).
- **Later slice.** Instance starts outside the nightly entry have no such check yet. Until that slice lands, a run started another way on such an image answers each kernel build as a failed build, `build_exit_status` with the compiler's log (cited: ADR-0060, ADR-0169).

### 5. C-7

- **The three systems are alike in the set**: one flag string, read by one compiler role, the image's `clang`, on Linux, macOS and WSL.
- **Differences that remain, and why they are accepted.**
  - **The thread count follows the processors the container sees**, which under Docker Desktop are the VM's. A key does not name it (cited: ADR-0035 decision 7; ADR-0001 decision 5), and a thread count of its own would be a per-machine value (decision 3).
  - **The runtime and its version are the image's**, and may differ between images and platforms. No member records it (A-13 reading below). The owner's answer asks that a kernel can use OpenMP, not that one build of the runtime is used.
  - **The host path of fp32 `model_execute`** builds on the host (cited: ADR-0182, its slice 3 is held in PLAN). A caller that passes `FLAGS` there needs OpenMP from the host's clang, which macOS's default clang lacks (cited: ADR-0116 decision 6). This goes away when that path moves into containers, and no run depends on it today (observation).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | `-fopenmp=libomp`, `-lomp` | Names one runtime; see decision 1. |
| 1 | `-fopenmp-simd` | No runtime; against the owner's answer. |
| 2 | The waiter with the flag too | It gains nothing, and a runtime in process 1 is what ADR-0145's reasoning cannot cover. |
| 2 | A flag per kernel, set by the coder | Against ADR-0116 decision 2 and ADR-0107 decision 3. |
| 3 | `OMP_NUM_THREADS` fixed by the backend | See decision 3. |
| 4 | No check; let the first build fail | The whole firing would run coders against an image that can build nothing, at the cost of usage, and the failure would look like the kernels'. |
| 4 | Read the installed packages of the image | Names a distribution's packages; a program built and started shows what a kernel will meet. |
| 4 | A member for the runtime in `toolchain` | A data-plane change, and refused by ADR-0035 decision 3. |

## Consequences

- **What an owner must do.** The stand-in image must hold what `-fopenmp` needs before the next nightly firing, or the firing ends as `prepare/no_openmp`. On the machine used for this record, `hilclaw-standin:2026-10-29` holds it (observation).
- **Kernels may now use OpenMP**, and a `#pragma omp` that was ignored before now takes effect. A kernel that called the runtime was a failed build and now links.
- **Sentences of earlier records this makes less exact, left unedited**: ADR-0116 decision 3 ("and nothing else"; the OpenMP item of "Not in the set"), decision 4 ("No OpenMP runtime"), decision 5 ("No OpenMP runtime is linked by the set", the part on `<threads.h>` as the only way to start a thread, and the walk-through row on `OMP_NUM_THREADS`), decision 6 (OpenMP), the walk-through row on macOS, Limits 4 and the follow-up in Consequences, the Alternatives rows on OpenMP and the Boundaries item; ADR-0035 decision 3 ("a runtime exists only for a build whose flags ask for one" and "that part of the kernels measured under the key never use": every kernel build now asks; the decision that `toolchain` has no such member stands); ADR-0144 decision 5 ("OpenMP is neither required nor forbidden", now required of the image) and decision 6's list of what the image must hold; ADR-0008 decision 6 ("how many is a build or run setting": no setting of this backend gives a number); `timing_waiter.c` and ADR-0170 decision 4 stay exact, since they read the waiter's flags as those of ADR-0116 decision 3 alone.
- **A-13 reading.** Code mode. **No data-plane change**: no member, file, kind, `step` value or version is added or changed, the hw_profile keeps its members, and `prepare/no_openmp` is a signature of the nightly routine's own record and issue title, which are outside the data plane (PROCESS/NIGHTLY.md §3). **No approved open list is used** (DRIVER §3). **The dependency reading**: the owner's answer approves an OpenMP runtime as part of the toolchain on every C-7 system. This record reads that as covering the same component, the distribution's `libomp-dev`, on the CI runner, since the CI gate has to build what the tests build; it adds no dependency to the package, and it is only in `.github/workflows/ci.yml`. That reading is this record's, and the owner may object to it. The image's content is the user's; the runtime installs nothing.
- **Runtime acceptance items** go to [PROCESS/RuntimeAcceptance.md](../../PROCESS/RuntimeAcceptance.md) (DRIVER §8, D22), none closed by this record: (i) the image's clang accepts `FLAGS` and `TRAILING_FLAGS` under each C-7 system's Docker, Linux, macOS Docker Desktop and WSL; (ii) a kernel using OpenMP completes a check and a timing run in the container under the options of ADR-0144 and the limits of ADR-0117; (iii) the thread count the runtime picks in that container, and whether it fits the processors the machine gives; (iv) the waiter still reports `waiter_max_rss_kib` for such a kernel in a container; (v) a kernel with no OpenMP is measured as before within noise.

## Boundaries (not decided here)

- **Which `kernel` techniques or catalog entries use OpenMP, and any prompt text that tells a coder to** (OD-22).
- **A target-specific flag and the list of inherited variables to remove or set** (ADR-0116 decision 6).
- **A check at instance starts outside the nightly entry**, and what asks the user for permission and how an image is then obtained (OD-8 ㉝ (가); OD-14 ① (나)).
- **Recording the runtime, its version or the thread count** with a run or a build (OD-14 ① (나), ⑰ (다)); any new member.
- **Moving the fp32 `model_execute` path into containers** (ADR-0182 slice 3).
- Other backends, a board, the mock.

## References

- [Requirements](../Requirements.md): FR-4, NFR-3, NFR-4, C-7; register row OD-18. [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18), sub-questions ⑱ and ⑲.
- ADR-0001; ADR-0007; ADR-0008 (decisions 6, 7); ADR-0035 (decisions 3, 7); ADR-0052; ADR-0060; ADR-0103; ADR-0107 (decision 3); ADR-0116; ADR-0117; ADR-0144; ADR-0145; ADR-0153; ADR-0169; ADR-0170; ADR-0182; ADR-0186.
- HQ-0034 in `PROCESS/STATE.json`; task T-0517.
- Code: `hilclaw/standin_settings.py`, `hilclaw/standin_run.py`, `hilclaw/standin_openmp.py`, `hilclaw/nightly.py`.
