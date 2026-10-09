# ADR-0036: The `host.os` of a `cpu_standin` hw_profile under macOS when the product version line holds a space or a tab (one point inside the part of OD-4 that ADR-0035 closed)

## Status

- **Accepted on 2026-10-09** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **No content of this record is a decision of the repository owner, and the repository owner has not confirmed it.**
- **Settles one point inside the part of the rest of OD-4 that [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) closed, and closes nothing further.** The register row of OD-4 keeps its status wording, and OD-26 keeps its status `미착수`. ADR-0035 is not edited: this record states how two of its sentences are read together.
- **Made without a macOS machine.** It states no fact about what macOS prints. It gives a rule for the case that a line holds a space or a tab, whether or not a system ever prints such a line.
- It builds on ADR-0035 (decisions 4, 6 and 7; objection window until 2026-10-16) and on [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1, as ADR-0035 does; decision 4 is cited directly; until 2026-10-13). **If ADR-0035 is reverted, this record falls with it**; if ADR-0001 is reverted, it is revisited with ADR-0035.
- The repository owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

Three places of ADR-0035 speak of the `host.os` of a `cpu_standin` hw_profile under macOS (all cited):

- **Decision 4, the sentence above the table**: "**`host.os`** is two or three words joined by single spaces: **the environment word, then what identifies the release of the operating system**."
- **Decision 4, the macOS row**: "`macos`, then the first line of the output of `sw_vers -productVersion`". Its bullet "macOS" says: "the whole product version, since this record knows no shorter part with one meaning across versions".
- **Decision 6**: a line is its text without the line end; the spelling is "each run of space and tab characters becomes one space; spaces at both ends are removed; nothing else is changed — no case is folded, no character is replaced or removed, nothing is cut". Its list of the facts that cannot be read names an `ID` or a `VERSION_ID` that "is empty or holds a space or a tab" and **names no product version that holds one**.

**The tension.** For a first line that the spelling of decision 6 leaves with three or more words — the fictitious `0.0 beta 1` — the macOS row and decision 6 give `macos 0.0 beta 1`: four words, and more for a line with more such places. The sentence above the table allows "two or three". Read as a rule, the sentence would make that value impossible; read as written, the row and decision 6 make it a value. Two followers of ADR-0035 can therefore differ on a machine with such a line — one makes a record, one reports a fact that cannot be read — which is what "The property meant" of decision 6 exists to prevent: "two programs, or a program and a person, that follow this record on the same machine in the same state arrive at byte-equal canonical forms". **A line left with two words** — the fictitious `0.0 beta`, which gives `macos 0.0 beta` — **does not contradict the count**: three words are allowed. What a follower can hesitate over there is only that the one shape decision 4 lists for macOS is `macos 0.0`, and that the same decision makes an `ID` or a `VERSION_ID` that holds a space or a tab unreadable while saying nothing of a product version that holds one. The rule below covers both lines.

**Where it was found.** The reviews of the code slice that carried ADR-0035 into the package (task T-0109) read this as a tension inside the record and filed it under the heading "For a later record (not decided here)". Facts of the code, none changed here: `hilclaw/standin_profile.py` follows the row — for the kernel name `Darwin` it spells the first line of the output of `sw_vers -productVersion`, puts `macos` and one space before it, and makes no check for a space or a tab in that line. `tests/test_standin_profile.py::test_macos_version_of_several_words_is_kept` pins `macos 0.0 beta`.

**Not at hand.** ADR-0035 decision 6 marks "everything about macOS (`uname -s`, `sysctl -n machdep.cpu.brand_string`, `sw_vers -productVersion`)" as taken from documentation and not checked on a machine. That is unchanged.

## Decision

A sentence below is **cited** when a source is named with it; every other sentence is **this record's own**.

### 1. Scope

- The `host.os` of a hw_profile whose `accelerator` is `cpu_standin`, on a machine whose kernel name is `Darwin`, **in the one case that the first line of the output of `sw_vers -productVersion` holds a space or a tab**.
- Nothing else of ADR-0035 is re-opened: the machine described, `toolchain`, `host.cpu`, the environment words and how an environment is recognised, the Linux and WSL rows, the rule for `ID` and `VERSION_ID`, `revision`, the line and the spelling of decision 6, "Nothing is substituted" and `hw_source` stand as they are.
- No field, type, value form or rule of ADR-0001 changes.

### 2. The rule: the spelt line is kept whole

- **A space or a tab in the product version line is no fact that cannot be read.** `host.os` under macOS is the word `macos`, one space, and **the first line of the output of `sw_vers -productVersion` in the spelling of decision 6, whole**. This is what the macOS row and decision 6 of ADR-0035 say; this record adds no case to the list of decision 6.
- **The moment.** **No check for a space or a tab is made at any moment**, neither before nor after the spelling. The steps, each of them ADR-0035's but the one on length (cited: decisions 4 and 6; for the length, the sources of the bullet "Length" below): take the first line of the output without its line end; make each run of space and tab characters one space and remove the spaces at both ends; if the result is empty or holds a character outside 0x20 to 0x7E, the fact cannot be read; if it is longer than 249 characters, no record is made ("Length" below); otherwise put `macos` and one space before it. What decision 6 says of the command itself — missing, giving nothing, ending with a status other than 0 — is unchanged.
- **So**: spaces and tabs at the two ends of the line leave no trace; each run of spaces and tabs between other characters, of whatever length and mixture, is one space of `host.os`; a line with several such runs keeps all its words. Two lines that differ only in the length or the mixture of such runs give one value, as decision 6 has it for every string taken from the machine (cited: the Walk-through of ADR-0035, the row on two spaces before `CPU`).
- **Length, unchanged and not this record's**: the `host.os` of a record is a *string* of ADR-0001, 1 to 255 characters (cited: ADR-0001 decision 1; ADR-0035 decision 1, "a record made by these rules is a record `hilclaw.keys.hw_profile_key` accepts"). With `macos` and the space that leaves 249 characters for the spelt line; for a longer one no record is made.
- **How the two sentences of ADR-0035 are read.** The macOS row and decision 6 are read as written. The sentence "two or three words joined by single spaces" is read **as a statement of the shapes that the Linux and WSL rows give, not as a rule that limits the macOS row or makes a fact unreadable**. Under macOS it holds exactly when the spelt line has one word or two. "Joined by single spaces" and the order "the environment word, then what identifies the release" hold in all three environments.

**Why this reading and not the other.**

- **Three places against one.** The row, its bullet ("the whole product version") and the spelling ("nothing is cut") agree with each other, and the list of decision 6 names its cases one by one. The count of words is said once, in a sentence that introduces the table. Reading the count as a rule would add a case to a list that does not hold it.
- **The rule for `ID` and `VERSION_ID` has a ground that is absent here.** ADR-0035 gives that rule and states no reason for it; **the ground named here is this record's reading, not ADR-0035's words.** Under Linux and WSL two values taken from the machine stand side by side in `host.os`, joined by a space. A space inside one of them would let two different files give one string: an `ID` of `a b` without a `VERSION_ID`, and an `ID` of `a` with a `VERSION_ID` of `b`, would both give `linux a b` — two different facts under one key. Under macOS one value follows a fixed word, so two different spelt lines never give one `host.os`.
- **The rule for `ID` and `VERSION_ID` cannot be carried over as it stands.** It is applied "before the spelling of decision 6 is applied" (cited: decision 4), so a space at the end of such a value makes it unreadable. For the output of a command decision 6 removes spaces and tabs at both ends. An unreadable case for the product version would therefore need a moment of its own — after the spelling, or before it with the ends set aside: a new rule, where keeping the line needs none.
- **What the other reading costs.** A machine whose line holds a space would have no record at all, since nothing is substituted (cited: decision 6), and would wait for a later record — with nothing gained in what a key tells apart.

**The cost of this reading, plainly.** The `host.os` of a macOS profile has no fixed number of words. Whoever wants the release part takes everything after the first space; no word after the first can be told to be "the version" or "the rest". Neither ADR-0001 nor ADR-0035 gives a rule that reads a part of `host.os`: two keys are the same when their canonical forms are byte-equal (cited: ADR-0001 decision 4). And the reading is chosen, not found: which of its sentences ADR-0035 meant as the rule cannot be read from it.

### 3. The shapes that follow

A word is a run of characters other than the space. By ADR-0035 and this record a `host.os` has:

| Environment | Words | Why |
|---|---|---|
| Linux | two or three | cited: the environment word, `ID`, and `VERSION_ID` when the file has one; neither value is empty or holds a space or a tab (ADR-0035 decision 4) |
| WSL | two or three | cited: the same |
| macOS | two or more | `macos`, then the words of the spelt line, at least one; no upper number is given other than by the 255 characters |

### 4. A limit named, and not decided

- ADR-0035 recognises WSL by a kernel name `Linux` and a kernel release that "contains `microsoft` in any case" (cited: decision 4). **A system under WSL whose kernel release does not contain `microsoft`** — for instance one whose kernel was built by its user; whether and when that occurs was not checked — **is described with the word `linux`**, and so shares a key with a native Linux system of equal values. Decision 7 of ADR-0035 does not name this case; it is named here as one more limit.
- **Nothing is decided about it**: no other way of recognising WSL is chosen or rejected.

### Walk-through

A machine whose kernel name is `Darwin` and whose other facts can be read; each row gives the first line of the output of `sw_vers -productVersion` without its line end. Every value is fictitious. No row names a tool or a moment of a call.

| The line | A record is made? | `host.os` |
|---|---|---|
| `0.0` | yes | `macos 0.0` |
| a tab, `0.0`, two spaces | yes | `macos 0.0` — the ends leave no trace |
| `0.0 beta` (one space between) | yes | `macos 0.0 beta` |
| `0.0`, a tab, `beta` | yes | `macos 0.0 beta` — the same value as the row above |
| `0.0`, a space, a tab, a space, `beta`, two spaces, `1` | yes | `macos 0.0 beta 1` |
| empty, or spaces and tabs only | no (cited: decision 6, the result is empty) | none; nothing is substituted |
| 250 characters, each from 0x21 to 0x7E | no (cited: ADR-0001 decision 1 — with `macos` and the space, 256 characters) | none; nothing is cut |

## Alternatives considered

| Alternative | Why not |
|---|---|
| A product version line that holds a space or a tab is a fact that cannot be read, as for `ID` and `VERSION_ID`; "two or three words" stays true of every `host.os` | See decision 2: it adds a case the list of decision 6 does not hold, its ground under Linux is absent under macOS, it needs a moment of its own, and it leaves a machine without a record. |
| Only the first word of the line is taken | Against "nothing is cut" (cited: decision 6); two different lines would give one value, which ADR-0035 rejects for a cut value ("a cut value can make two different facts equal", its Alternatives). |
| A space inside the line is replaced by another character | Against "no character is replaced or removed" (cited: decision 6). |
| Another source for the version under macOS (a build number, the kernel release) | Outside the one point; ADR-0035 chose the source (Boundaries). |
| Wait for a macOS machine | The rule is needed for the case whether or not it occurs: a program that follows ADR-0035 must do one thing or the other with such a line. What a machine could show is whether the case occurs, which this record does not state. |
| Edit the sentence of ADR-0035 | ADR-0035 is inside its objection window and is left as it was accepted; the reading is stated here, where it can be reverted alone. |

## Consequences

- **The code agrees with the rule, and no change of the code follows.** `hilclaw/standin_profile.py` does what decision 2 says (Context). Its tests pin these lines: `0.0` (`test_macos_branch`); a tab before and two spaces after `0.0`, giving `macos 0.0` (`test_macos_facts_are_spelt_and_later_lines_ignored`); a run of a space, a tab and a space between `0.0` and `beta`, giving `macos 0.0 beta` (`test_macos_version_of_several_words_is_kept`); no output, an empty first line and a first line of spaces and tabs only, giving no record (`test_macos_command_that_cannot_be_read`); and a line of 249 characters, which gives a record, against one of 250, which gives none (`test_macos_host_os_length_limit`). **No test pins a line that is left with three or more words** (the row of the Walk-through that gives `macos 0.0 beta 1`); the code has no branch on the number of words, so such a line takes the path of the pinned two-word line. Whether a test for it is added is left to a later code task and is not asked for here. The live case of that file asserts that `host.os` starts with `linux` or `wsl` and has two or three words, which agrees with decision 3.
- **The unchecked statements stay unchecked**: everything ADR-0035 marks as taken from documentation, macOS above all. This record adds none.
- **Not edited and now read with this record**: the sentence of ADR-0035 decision 4 above its table, and its decision 7, which does not name the WSL case of decision 4 here.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. No field, type, value form or rule of ADR-0001 changes and no data-plane file changes. No record of a `cpu_standin` hw_profile exists in a data plane, so none is made invalid or re-keyed.

## Boundaries (not decided here)

- **Any fact about what macOS prints**, and whether the case of decision 1 ever occurs — for the code task or the person that first has a macOS machine (ADR-0035 decision 6, "What was checked and what was not").
- **Any other source for the macOS version** (a build number, `sw_vers -buildVersion`, the kernel release), **telling WSL 1 from WSL 2, and any other way of recognising an environment** — a later record under the rest of OD-4; ADR-0035 decisions 4 and 7 stand.
- **Anything of `toolchain`, `host.cpu`, `revision`, `hw_source` or a further `host` member; the Linux and WSL rows of decision 4** — ADR-0035, unchanged.
- **Onboarding, registration, storage, and a re-check of the machine against its profile** — OD-26 and the rest of OD-4 (ADR-0035 Boundaries).
- **Any tool, call or tool-failure kind** (OD-18), and anything HQ-0005, HQ-0006 or HQ-0007 asks.
- Any change to a field, type, value form or rule of ADR-0001, to a data-plane file or to the spec schema; any change to ADR-0001 to ADR-0035, to `hilclaw/`, to tests or to CI; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-10, FR-13, FR-14 ④, C-7; register rows OD-4, OD-26.
- [OpenDecisionProposals OD-4](../OpenDecisionProposals.md#od-4); [StandardScenarios](../StandardScenarios.md) S0, S1, S10.
- [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decisions 1, 4, 6, 7; Walk-through; Alternatives; Boundaries); [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 4; record format).
- `hilclaw/standin_profile.py`, `tests/test_standin_profile.py`; tasks T-0108, T-0109, T-0111.
- #5 D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · the notice of ADR-0035 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6089042706
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9.
