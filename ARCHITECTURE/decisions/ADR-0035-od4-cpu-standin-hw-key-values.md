# ADR-0035: How the hw key-field values of a `cpu_standin` hw_profile are obtained on the machine that builds and runs the kernel (one more part of the rest of OD-4)

## Status

- **Accepted on 2026-10-09** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Three kinds of content.** **Answers of the repository owner on issue #5** (A-7, B-4 ⑤, B-6), and the two values of `hw_source`, which FR-14 ④ records as confirmed by the owner on 2026-09-03, are cited as the owner's and rendered as what they say. **The choices of earlier records** — [ADR-0001](ADR-0001-od4-key-schema.md) above all — were accepted under §9, have not been confirmed by the repository owner and are cited as theirs. **Everything else is this record's own design and has not been confirmed by the repository owner**: which machine the values describe, the one member of `toolchain` and the form of its string, the facts `host.cpu` and `host.os` are taken from and their spelling, that no further `host` member is carried, the word `revision` holds, what is said about `hw_source`, and the list of limits.
- Closes **one more part of the rest of OD-4** (Open Decisions register in [Requirements](../Requirements.md)): the point ADR-0001 Boundaries handed to "the task that registers `cpu_standin`" — how the values of the hw key fields are obtained — **for a hw_profile whose `accelerator` is `cpu_standin` and for nothing else**. The register row of OD-4 keeps its status wording. **OD-26 keeps its status `미착수`**: no proposal of it is adopted or rejected, and nothing of the onboarding flow is decided.
- What stays open: the similarity layer and the S10 note (rest of OD-4); the `shape` members of the second family; who registers a profile, when and where (OD-26); whether a hw_profile of `cpu_standin` always states one fixed value of `hw_source` whatever its CPU, and which (the question this record files under OD-26); and every item under Boundaries.
- It builds on ADR-0001 (decisions 1, 3, 5 and 6; objection window until 2026-10-13) and on [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decision 2; until 2026-10-14). [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (until 2026-10-14), [ADR-0016](ADR-0016-od18-backend-frame.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) and [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (until 2026-10-15) and [ADR-0002](ADR-0002-od6-codegen-spec.md) (until 2026-10-13) are cited, not built on. **If a record it builds on is reverted — ADR-0001 in particular — this record is revisited with it.**
- The repository owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **ADR-0001 Boundaries** left open, for "onboarding, OD-26, and the task that registers `cpu_standin`": "which components are members of `toolchain` (for example whether an OpenMP runtime is one), the form of version strings, the source and normalisation of the `host.cpu` and `host.os` strings, which optional `host` members a profile carries, what `revision` holds for hardware without a revision of its own, the `hw_source` of a stand-in, and who fills in the record (probing or by hand). Until these are fixed, two tools may derive different keys for the same machine."
- **What that costs today.** Every example of a `cpu_standin` hw_profile in a record carries the placeholder `NOT-DECIDED-HERE` (ADR-0001 decision 7, ADR-0002 decision 8, the Example of ADR-0018), the tests use invented strings, and ADR-0008 lists "the hw-side values and the `hw_profile` key" among what the committed spec example (PLAN P1-5) still lacks.
- **Answers of the repository owner (cited).** #5 A-7: "a general-purpose CPU is registered as the **first "accelerator" backend**"; "C, compiled with clang as the single toolchain"; "OpenMP and SIMD intrinsics are allowed"; placement "local first, then LAN", "run on the orchestrator machine first"; the stand-in "is registered as its own hw_profile (`cpu_standin`)". #5 B-4 ⑤: it "runs on the **owner's current local PC (Windows → WSL, per B-6) first**". #5 B-6: developer PCs are Windows, macOS and Linux, and "On Windows, WSL is the default premise". Requirements C-7 holds these. The two values of `hw_source` — external vendor, in-house under development — are the repository owner's vocabulary of 2026-09-03: this attribution is that of FR-14 ④ ("오너 확정 2026-09-03") and of ADR-0001 Context ("owner 2026-09-03"), not of a comment on #5; the UsageCases glossary dates it without naming the owner.
- **ADR-0001 (cited, not re-decided).** `revision` is a required *string*, "Hardware revision of the accelerator". `toolchain` is a map with at least one member: "Version of every software component between the kernel source and its execution on the accelerator: compiler, and where they exist firmware, driver, runtime". `host` has the members `cpu` ("the host CPU model") and `os` ("the host operating environment"); "Further members (for example the memory size, UC-0) may be added when they are known to change measured performance". A *string* is 1 to 255 printable ASCII characters (0x20-0x7E). `hw_source` is a required attribute and no key field. Decision 5: a change of any key field is a new key, and the key stays the same under a change "of per-candidate build settings such as compiler flags and thread count, which are not key fields in version 1". Decision 6: a new member name in `toolchain` or `host` raises no `schema_version`. Its criterion: "every property that changes measured performance is already a key field". Its Consequences: a new key "costs a cold start, not correctness" (FR-15).
- **How a kernel is built and run at `cpu_standin` (cited).** One call of `clang_build.build` makes one executable, and the kernel runs in a process of its own started through `local_run.run` (ADR-0009 decision 2; ADR-0017 for the verification run). ADR-0009 is "not a mechanism for a simulator, a board or a remote machine".
- **Facts of the code, none of them changed here.** `hilclaw/keys.py` checks a hw_profile record and derives its key (`hw_profile_key`); `HW_SOURCES` is `("external", "in_house")`. `hilclaw/clang_build.py`: `DEFAULT_COMPILER` is `"clang"`, found on the search path when no compiler is given; `compiler_version` returns the first line that `<compiler> --version` writes to standard output with outer whitespace removed, changes nothing inside the line and has no caller in the package; `build` adds no flag, so OpenMP reaches a build only through the caller's flags. `hilclaw/local_run.py` starts a local process and "pins no CPU, sets no priority and no resource limit". `hilclaw/key_records.py` stores and loads a record it is given. **No module of `hilclaw/` reads a property of the host** (no use of `platform`, `uname`, `/proc/cpuinfo` or `sysctl` in `hilclaw/` or `tests/`), and none builds a hw_profile record.
- **Open and not touched**: the onboarding registry and who registers (OD-26); how a backend is reached and a stand-in on another machine (#5 B-2); the target NPU and its toolchain (#5 B-1); the similarity layer (rest of OD-4).

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice. No sentence below renders a decision of the repository owner beyond the cited answers.

### 1. Scope

- This record says **which strings the key fields `revision`, `toolchain` and `host` hold, and what holds for the attribute `hw_source`, in a hw_profile whose `accelerator` is `cpu_standin`**, for a stand-in that builds and runs the kernel on one machine.
- **No rule below is meant for another accelerator.** The values of a real accelerator are OD-26 and #5 B-1, and whether a hw_profile of the mock backend is ever registered, and with which values, is sub-question ⑧ of OD-18. A later record may take a rule over; this one does not offer them as a pattern.
- It changes no field, type, value form or rule of ADR-0001: every value below is a *string* of ADR-0001, and a record made by these rules is a record `hilclaw.keys.hw_profile_key` accepts.
- **It defines values, not an act.** It says what each value **is** — which fact of the machine, in which spelling — so that a program that reads the machine and a person who types the record arrive at the same string. Who makes a record, when, with what, and where it is stored are not decided (Boundaries).

### 2. Which machine the values describe

- **The machine on which the kernel is built and run.** For the stand-in as it exists that is one machine: the build and the run are local processes of the machine the package runs on (cited: ADR-0009 decision 2; `clang_build`, `local_run`), "the orchestrator machine" of #5 A-7 ③.
- "Machine" means the environment those processes see: under WSL it is the Linux environment, not the Windows system around it (decision 4).
- **Not covered**: a kernel built on one machine and run on another, and a stand-in reached on another machine (#5 A-7 ③ "then LAN"; #5 B-2). Which machine's compiler and which machine's host a profile then states is not said here.

### 3. `toolchain`: one member, `clang`

- **`toolchain` has exactly one member, `clang`.** That clang is the toolchain is cited (#5 A-7 ②: "clang as the single toolchain"); that the map holds no second member is this record's choice.
- **Its value is the first line that the command `<compiler> --version` writes to standard output, in the spelling of decision 6**, where `<compiler>` is the clang with which the kernels of the profile are built. For a command that ends with status 0 and an output in printable ASCII this is what `clang_build.compiler_version` returns today, followed by the whitespace rule of decision 6 (the function removes outer whitespace only). For any other output the rule of this record holds, not the behaviour of the function; whether the two differ there is for the code task to check.
- **Why the whole line and not a part of it.**
  - *The dotted number only* (`0.0.0`): the most stable string, but a clang of one vendor and a clang of another with the same number are different compilers, and the number alone does not tell them apart. It also needs a rule that finds the number in the line of every vendor, which this record would have to invent.
  - *Vendor and number*: needs the same parsing rule and a list of vendors.
  - *The line and the target line below it*: the target a kernel is built for follows from the caller's flags as well, and flags are no key fields (cited: ADR-0001 decision 5). The default target is not in the key (decision 7).
  - **The whole first line** needs no parsing, tells vendor builds apart and carries whatever build identification the vendor prints. **Its cost for key stability**: a repackaged compiler whose line changes starts a new key although the generated code may be the same — a cold start, not a wrong result (cited: ADR-0001 Consequences).
- **Why no further member.**
  - *An OpenMP runtime.* OpenMP is allowed (cited: #5 A-7 ②), and a runtime exists only for a build whose flags ask for one. Flags are the caller's and may differ between the candidates of one pair (cited: ADR-0001 decision 5 and Alternatives; `clang_build`). A member of the profile would state the version of a component that part of the kernels measured under the key never use; and this record knows no one command or file that names the runtime a build would use in the same way on Linux, macOS and WSL.
  - *The C library, the linker.* Both lie between the source and the execution in ADR-0001's words. This record knows no one way to name their versions that is the same on the three environments, and a rule per environment would be three rules to keep equal.
  - **The cost, plainly**: a change of the OpenMP runtime, of the C library or of the linker leaves the key unchanged although measured performance may change (decision 7). ADR-0001's sentence "Version of every software component" is thereby met for the compiler only; this record states the gap and does not close it. Firmware and a driver, which that sentence names "where they exist", are no members either: for a stand-in the nearest things are the microcode of the CPU (weighed in decision 5), the BIOS or firmware of the machine and the kernel of the operating system (named in decision 7). A profile registered again with an added member is a different record with a new key and raises no `schema_version` (cited: ADR-0001 decision 6), so a later record can add a member without a schema change.
- **Two clangs on one machine** are two values and two keys. Nothing here checks that the compiler that builds a kernel is the one the profile states (cited: ADR-0016 decision 6, "The target reached is not checked against the key").

### 4. `host`: `cpu` and `os`, and no further member

- **`host.cpu`** is the model name the operating system reports for the processor, in the spelling of decision 6, read from:

| Environment | Fact |
|---|---|
| Linux, WSL | of the first line of `/proc/cpuinfo` whose text before its first colon, with spaces and tabs removed at both ends, is `model name`: the text after that colon |
| macOS | the first line of the output of `sysctl -n machdep.cpu.brand_string` |

- **`host.os`** is two or three words joined by single spaces: **the environment word, then what identifies the release of the operating system**.

| Environment | Recognised by | `host.os` |
|---|---|---|
| macOS | kernel name (`uname -s`) is `Darwin` | `macos`, then the first line of the output of `sw_vers -productVersion` |
| WSL | kernel name is `Linux` and the kernel release (`uname -r`) contains `microsoft` in any case | `wsl`, then the value of `ID` in `/etc/os-release`, then the value of `VERSION_ID` when the file has one |
| Linux | kernel name is `Linux`, otherwise | `linux`, then `ID` and `VERSION_ID` in the same way |

  A value of `/etc/os-release` is the text after `ID=` or `VERSION_ID=` on the first line that starts so, without one pair of double or single quotes around it. **A file without an `ID` line is a fact that cannot be read** (decision 6): the default that `os-release(5)` names for a missing `ID` is not used. So is an `ID` or a `VERSION_ID` that is present and, once the quotes are removed and before the spelling of decision 6 is applied, is empty or holds a space or a tab. A file without a `VERSION_ID` line gives the two-word form. Shapes: `linux exampleos 0.0`, `wsl exampleos 0.0`, `macos 0.0`, `linux exampleos` (a distribution without `VERSION_ID`).
- **What "operating environment" tells apart, and why** (the term is ADR-0001's; the reading is this record's).
  - *The kernel release* (`uname -r`) as the value: it changes with every kernel update and would start a new key each time; and under WSL it names Microsoft's kernel, not the distribution. Not taken as the value; used only to recognise WSL.
  - *The distribution and its release* (`ID`, `VERSION_ID`): the value changes when `VERSION_ID` changes and at no other update. Taken, because it is the one statement of a release that `os-release(5)` gives every distribution in one form. **"Inside a release" below means: while `VERSION_ID` stays the same.** How much of a system one value of `VERSION_ID` covers differs between distributions and is not checked here: where it names a long-lived release, updates of the kernel and of libraries pass inside it; where it carries a point or patch level, an ordinary update changes it. **The cost** on both sides: an update inside a release leaves the key unchanged although performance may change, an update that only moves `VERSION_ID` starts a new key although performance may not, and a distribution without `VERSION_ID` never changes `host.os` (decision 7).
  - *macOS*: the whole product version, since this record knows no shorter part with one meaning across versions. **The cost**: every update of macOS that changes the version starts a new key.
  - *WSL against native Linux*: told apart by the first word. The first host is a PC under WSL (cited: #5 B-4 ⑤), the same distribution can run natively on the same PC, and the two run the kernel under different kernels, one of them inside a virtual machine or a translation layer: a property that can change measured performance (ADR-0001's criterion). **WSL 1 and WSL 2 are not told apart** (decision 7).
  - *The three environments* are those of C-7 (cited). Another kernel name has no rule here: no record is made by this record for such a machine (decision 6).
- **No further `host` member in a profile made by this record.** Weighed, by ADR-0001's "when they are known to change measured performance":
  - *Core count.* It changes the performance of a kernel that runs threads. Part of it is hardware that the model name does not give (the number of sockets), and this record knows no one way to read that on the three environments in one spelling. Part of it is a setting — a virtual machine, WSL with a processor limit, a container, an affinity mask — that can change between two runs with no change of the machine, like the thread count ADR-0001 decision 5 keeps out of the key.
  - *Memory size* (named by UC-0 and ADR-0001), *the frequency policy*, *SMT*: each can change performance; this record knows no one way to read each on the three environments in one spelling, and two of them are settings rather than identity.
  - **None is a member; all are named in decision 7 as outside the key.** A later record can add one without a schema change (cited: ADR-0001 decision 6).

### 5. `revision`: the word `host`

- **`revision` holds the fixed string `host`.** For a stand-in the accelerator is a general-purpose CPU (cited: #5 A-7, "a general-purpose CPU is registered as the first "accelerator" backend"); that it **is** the CPU of the host follows from decision 2 and is this record's reading. That CPU is identified in `host.cpu`. The word says where to look; it is not a revision number, and it is no statement that a CPU has no revision.
- Weighed against it:
  - *Repeating `host.cpu`*: one fact required twice; it adds nothing to what the key tells apart, and any difference of spelling between the two would be an error with no meaning.
  - *Family, model and stepping, or a microcode revision*: facts of the CPU that can matter for performance. This record knows no one source for them on the three environments (an Apple CPU reports no stepping in the form an x86 CPU does — taken from documentation, not checked), and a microcode revision can change with an update of the system. Not taken; **the cost**: two steppings of one model name and two microcode revisions share a key (decision 7).
  - *An empty value, `none`, `n/a`, `0`*: the empty string is no *string* of ADR-0001; the others say that there is no revision, which is not what is meant.
- **This answers ADR-0001's question for `cpu_standin` only.** What `revision` holds for other hardware without a revision of its own is not decided.

### 6. One spelling; a fact that cannot be read

- **A line** — of a file or of the output of a command — is its text without the line end (a line feed, or a carriage return and a line feed); the line end is no part of any fact below. **The spelling of every string this record takes from the machine**: each run of space and tab characters becomes one space; spaces at both ends are removed; nothing else is changed — no case is folded, no character is replaced or removed, nothing is cut. The result must be a *string* of ADR-0001: 1 to 255 characters, each from 0x20 to 0x7E.
- **A fact that cannot be read by these rules yields no value, and then no record is made by this record.** That is the case when the command or the file is missing or gives nothing, when the command ends with a status other than 0, when `/proc/cpuinfo` has no `model name` line, when `/etc/os-release` has no `ID` line or holds an `ID` or a `VERSION_ID` that is empty or holds a space or a tab (decision 4), when the kernel name has no rule, and when the result is empty, longer than 255 characters or holds a character outside 0x20 to 0x7E. **Nothing is substituted**: no `unknown`, no placeholder, no shortened or transliterated text, no value from another source.
- Why nothing is substituted: one placeholder would give one key to machines that differ in the very fact that is missing, and their measurements would enter the same stored knowledge — the mixing that separate keys exist to prevent. A profile for such a machine needs a later record (or a person's decision under OD-26); this one has no value for it.
- **The property meant**: two programs, or a program and a person, that follow this record on the same machine in the same state arrive at byte-equal canonical forms (ADR-0001 decision 3) and so at the same key. `hw_source` and `label` are attributes and do not enter it (cited: ADR-0001 decision 3).
- **What was checked and what was not.** On one WSL installation at hand: the kernel name `Linux`, a kernel release that contains `microsoft`, a `model name` line in `/proc/cpuinfo`, `ID` and `VERSION_ID` in `/etc/os-release` (the second in quotes), a first line of `clang --version` in printable ASCII, and a target line below it. **Taken from documentation and not checked on a machine**: that WSL 2 runs its kernel in a virtual machine and WSL 1 is a translation layer; what a container reports as its `/etc/os-release` and its kernel; everything about macOS (`uname -s`, `sysctl -n machdep.cpu.brand_string`, `sw_vers -productVersion`), native Linux (expected to match WSL in the files named), WSL 1, and Linux on a CPU whose `/proc/cpuinfo` has no `model name` line (reported for some ARM systems). The code task that implements the rules checks them where it can and reports a difference rather than adapting the rule.

### 7. Limits

Named, and none of them decided.

- **The key changes although performance may not**: a repackaged clang with another first line; an update of macOS; a move to another release of a distribution, and an ordinary update of a distribution whose `VERSION_ID` changes with it; a system that reports another spelling of the same CPU.
- **The key stays although performance may change**: an update of the kernel, of the C library, of the linker or of an OpenMP runtime inside one release (while `VERSION_ID` and the clang line stay the same), and any such update of a distribution without `VERSION_ID`; the stepping and the microcode of the CPU; BIOS, firmware and power settings; the frequency policy; SMT; the size and the layout of memory; the number of sockets and the number of processors a process may use; the thermal state; load from other processes; the flags, the target and the thread count of a build (cited for flags and thread count: ADR-0001 decision 5); WSL 1 against WSL 2, and the version and settings of the Windows system around WSL.
- **A virtual machine or a container** may report a CPU name that is not the physical one, and a container reports the `/etc/os-release` of its image over the kernel of its host. The record describes what the processes see.
- **Cores of different kinds**: a machine whose processors report different model names is described by the first one; a CPU with cores of two kinds under one model name is one value.
- **Two machines with equal values share a key** (cited: ADR-0001 decision 5) although they may differ in anything listed above.
- **Nothing re-checks.** A profile states the machine as it was when the values were taken; whether and when anything compares the machine with the profile again is not decided (Boundaries).

### 8. `hw_source`: stated, never read from the machine

- **This record fixes no value of `hw_source` for `cpu_standin`.** The value is **stated by whoever makes the record and is never taken from the machine**: the two values say where the hardware comes from (cited: ADR-0001 decision 1; the vocabulary is the repository owner's), the hardware of a stand-in is the CPU of the machine (decision 5), and whether that CPU is hardware of an external vendor or hardware under in-house development is a fact about an organisation, which no command or file of the machine reports.
- **Not decided**: whether a hw_profile of `cpu_standin` always states one fixed value whatever its CPU — for instance because of what it stands in for — and which. No source says so (ADR-0001 decision 7: "no source says which of the two values a stand-in has"). It is filed under OD-26 with this record. **Why it is a question**: ADR-0001 decision 1 says "The same accelerator cannot differ in `hw_source` only", and this record gives no rule by which two makers of a record of one key state the same value — two records of one key with different values are not excluded by anything here. Whether a stored attribute may be updated is OD-26 (cited: ADR-0018 decision 3), and what follows from such a pair is left there with the question. Nothing waits for it today: the attribute changes no key (cited: ADR-0001 decisions 1 and 3) and no handling per source exists (OD-26).
- No handling per `hw_source` is decided.

### Example

**A plainly fictitious machine — not the first real instance, not the driver machine and not the repository owner's PC.** No such compiler, CPU or distribution exists. `hw_source` is `external` only because a valid record needs one of the two values; with `in_house` the key is the same.

```json
{
  "schema_version": 1,
  "accelerator": "cpu_standin",
  "revision": "host",
  "toolchain": {"clang": "Example clang version 0.0.0 (fictitious-build 1)"},
  "host": {"cpu": "Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz", "os": "linux exampleos 0.0"},
  "hw_source": "external"
}
```

```
{"accelerator":"cpu_standin","host":{"cpu":"Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz","os":"linux exampleos 0.0"},"revision":"host","schema_version":1,"toolchain":{"clang":"Example clang version 0.0.0 (fictitious-build 1)"}}
sha256 = 8c0be275e5925ab01285dc46b6c2b9c8532d5f5b4ab150ccb2167b94a25a8fab  ->  cpu_standin-8c0be275e5925ab0
```

### Walk-through

The fictitious machine above; each row says whether the key is the one of the Example. No row names a tool or a moment.

| Case | Key |
|---|---|
| The same machine in the same state, described twice — by a program and by a person | **The same**: both follow decisions 3 to 6 and arrive at the same canonical form |
| The model name is reported with two spaces before `CPU` | **The same**: the run becomes one space (decision 6) |
| The record states `in_house` instead of `external`, or carries a `label` | **The same**: attributes are not in the key |
| After a clang upgrade: the line reads `Example clang version 0.0.1 (fictitious-build 1)` | **New**: `cpu_standin-d77e9423bfc2a90c` (cited: ADR-0001 decision 5) |
| After packages were updated, `VERSION_ID` is still `0.0` and the clang line did not change | **The same**, although performance may differ (decision 7) |
| After an update, `VERSION_ID` is `0.1` | **New**: `host.os` is `linux exampleos 0.1`, `cpu_standin-9238984cf1643768` |
| A second machine with the same CPU model, the same release and the same clang line | **The same**: two machines with equal values share a key (cited: ADR-0001 decision 5) |
| The same PC, the same distribution and release under WSL | **New**: `host.os` is `wsl exampleos 0.0`, `cpu_standin-d3b1abbab96cb59c` |
| A machine whose `/proc/cpuinfo` has no `model name` line, or whose clang line holds a character outside ASCII | **No key**: no record is made by this record, and nothing is substituted |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | Rules for every accelerator | The values of a real accelerator depend on hardware #5 B-1 has not named, and onboarding is OD-26. |
| 2 | The machine the package runs on, by definition | The same today; it would be wrong the day the build or the run moves to another machine, which this record does not cover. |
| 3 | The dotted number; vendor and number; the line with the target | See decision 3. |
| 3 | Members for an OpenMP runtime, the C library, the linker | See decision 3. |
| 3 | A member only when a component can be named (`toolchain` of varying size) | Two descriptions of one machine could differ in whether they found the component: two keys for one machine. |
| 4 | `host.os` is the kernel release; the pretty name of the distribution; the product name of macOS | The kernel release changes with every update. A pretty name carries point releases and free text. The product name of macOS has changed between versions (taken from documentation), so a fixed word is used. |
| 4 | WSL not told apart from native Linux | Two environments that can differ in measured performance would share stored knowledge. |
| 4 | `host` members for core count, memory size, frequency policy, SMT | See decision 4. |
| 5 | Repeat `host.cpu`; stepping or microcode; `none` | See decision 5. |
| 6 | Fold case; remove `(R)`, `(TM)` and the frequency from a CPU name | Rules of taste with no source; each is a chance for two followers to differ. |
| 6 | A placeholder such as `unknown` for a fact that cannot be read; cut a long value to 255 characters | See decision 6; a cut value can make two different facts equal. |
| 8 | `external`, because a general-purpose CPU comes from a vendor | True of most machines, not of every one, and not readable from the machine; whether a stand-in has a fixed value is not this record's to settle. |
| 8 | A third value for a stand-in | A change of ADR-0001 and of the repository owner's vocabulary. |

## Consequences

- **The code slice that can now be cut** (code mode, within the size cap): a function of the package that returns the hw_profile record of the local `cpu_standin` by decisions 3 to 6, in a new small module with its test file, using `clang_build.compiler_version`; `hw_source` is given by the caller (decision 8). The facts of the machine are passed in or read through a seam the tests replace. **Bound to no tool, no start of an instance and no registration**; storing the record is not part of it. Names and the return form are the code task's.
- **What the committed spec example (PLAN P1-5) still lacks after this record**: `task.objective` (#5 A-4, OD-1) and a technique of the stand-in catalog; and the values of a real machine, which this record does not hold.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0001 decision 7 (the rows "not decided here" for the hw values) and its Boundaries item "How the values of the hw key fields are obtained"; ADR-0002 decision 8 and its Boundaries ("the `hw_source` of `cpu_standin`, its `revision`, host and clang version strings"); ADR-0008 Consequences ("Still missing … the hw-side values"); the Example of ADR-0018 and of the records that copy it. Their placeholders stay what they are: values no record gives **for a real machine**. No sentence of UsageCases became false; UC-0 step 1 ("호스트 환경(CPU type, DRAM 등)") is less exact for `cpu_standin`, whose profile by this record carries no memory member.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. No field, type, value form or rule of ADR-0001 changes and no data-plane file changes: the record says which strings a valid record of one accelerator holds. No record of a `cpu_standin` hw_profile exists in a data plane, so none is made invalid or re-keyed.

## Boundaries (not decided here)

- **Onboarding (OD-26; UC-0)**: the registry, its schema and storage; who registers a profile and when; **whether a registration is read from the machine or typed** (the last clause of ADR-0001's item — this record makes both arrive at one string and chooses neither); a smoke test; the attribution of history between keys; handling per `hw_source`.
- **Question this record files under OD-26**: whether a hw_profile of `cpu_standin` always states one fixed value of `hw_source` whatever its CPU, and which.
- **A stand-in on another machine** and how a backend is reached; checking that the machine reached is the one the key describes (#5 B-2, reserved for the repository owner; OD-26; OD-10).
- **Whether and when a run re-checks** that the machine still matches the hw_profile it states — the S10 note "an environment change as a new key candidate" (rest of OD-4; OD-11).
- **Build settings** — flags, target, thread count — as key fields or as a record (ADR-0001 decision 5 and Alternatives; OD-6); the stand-in catalog and any technique; `task.objective` (#5 A-4, reserved for the repository owner); the committed spec example itself (PLAN P1-5); session hygiene of a measurement (rest of OD-13).
- **Any other accelerator**: the target NPU, its toolchain members and revision (#5 B-1, reserved for the repository owner); the mock backend's hw_profile (OD-18 sub-question ⑧); what `revision` holds in general for hardware without one.
- **Any tool's contract** (OD-18): no tool, moment of a call, request or result member or tool-failure kind is given here, and nothing HQ-0005 asks.
- **The similarity layer** (rest of OD-4).
- Any change to a field, type, value form or rule of ADR-0001, to `instance.json`, to the spec schema or to another data-plane file; any change to ADR-0001 to ADR-0034, to `hilclaw/`, to tests, to CI, to `pyproject.toml`, to any settings file, or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-10, FR-13, FR-14 ④, FR-15, NFR-2, NFR-7, C-7; register rows OD-4, OD-26, OD-6, OD-13, OD-18.
- [OpenDecisionProposals OD-4](../OpenDecisionProposals.md#od-4), [OD-26](../OpenDecisionProposals.md#od-26); [UsageCases](../UsageCases.md) glossary (hw_profile, HW 출처), UC-0, UC-1; [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b, S6, S10.
- #5 A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · B-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944087839 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, B-1, B-2.
- #4 comment (OD-4 row: the hw identification includes firmware, driver and toolchain versions) https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800
- [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3, 5, 6, 7; Alternatives; Consequences; Boundaries; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 8; Boundaries); [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (Consequences); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decisions 1, 2); [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 4, 6); [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decision 3; Example).
- `os-release(5)`, `proc(5)`, `uname(1)`; the macOS manual pages `sysctl(8)` and `sw_vers(1)`; Microsoft's WSL documentation (the kernel release of a WSL system) — sources of the statements marked "taken from documentation".
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-2, P1-5, P2-5; `hilclaw/keys.py`, `hilclaw/clang_build.py`, `hilclaw/local_run.py`, `hilclaw/key_records.py`, `hilclaw/backends.py`; tasks T-0015, T-0108.
