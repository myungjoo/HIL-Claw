# ADR-0027: The form of a `run_id` that the system builds, and what the form gives of its uniqueness (the part ADR-0004 decision 8 left open)

## Status

- **Accepted on 2026-10-09** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): the form of a `run_id`, which [ADR-0004](ADR-0004-od8-data-plane-layout.md) decision 8 left open in three points. "How a new id is built" and "whether ids sort by time" are answered for an id the system builds; "how uniqueness is obtained" is answered **as far as the form carries it**. The register row of OD-8 keeps its status wording.
- What stays open: whether anything checks at the start of an instance that an id is not in use, and everything else the start does (sub-questions ⑩, ⑰ to ㉑ and ㉓ (i)); what builds an id and when; a branch or a continuation of a run (sub-question ①); the isolation means; the sub-question this record raises; and every item under Boundaries.
- It builds on ADR-0004 (decisions 1, 3, 8, 9 and 10), whose objection window runs until 2026-10-14, on the *string* of [ADR-0002](ADR-0002-od6-codegen-spec.md) and [ADR-0001](ADR-0001-od4-key-schema.md) (until 2026-10-13), and on [ADR-0025](ADR-0025-od8-instance-file-write.md) (decision 4; until 2026-10-15). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- ADR-0004 decision 8: "Only its constraints as a directory name are fixed: `run_id` matches `[a-z0-9][a-z0-9_-]{0,63}` and is unique within `runs/` of a data repository. … Every such value is a *string* of ADR-0002. **The form stays open**: how a new id is built, how uniqueness is obtained, and whether ids sort by time." Its Alternatives say of a chosen form: "No source gives one (ADR-0002), and the tree needs only a valid directory name."
- #4 §2c: "`instanceID`는 기존 용어 `run_id`로 통일", and owner and project are meta fields, not path levels. #4 §1: one small `STATE.json` is the entry point and no whole-directory scan is allowed. No sentence of #4 or #5 gives a form for the id; none is attributed to the owner here.
- What waits on a form: ADR-0002 lists "the form of a `run_id`" among the values no source gives, and its example carries `"run_id": "NOT-DECIDED-HERE"` (PLAN P1-5). Whatever starts a run needs an id before the first file of `runs/<run_id>/` is written (PLAN P1-8, P2-1).
- Facts of the code, none of them changed here. No module of `hilclaw/` builds a `run_id`; `hilclaw/layout.py` says of itself that it "builds no ``run_id`` and does not know whether one is unique". Where the package takes a `run_id` as the name of a run directory it checks it with `hilclaw.layout.check_run_id` — the pattern of ADR-0004 decision 8 and nothing else — and `hilclaw.spec` checks `id.run_id` as a *string* only. Every test uses a literal (`run-a`, `run-b`, `synthetic-run_01` and the like), and the example request of [ADR-0015](ADR-0015-od18-tool-contract-frame.md) uses `r1`.
- Unchanged inputs: the data plane is one separate git repository (#5 A-1) and the durability boundary is the local commit (#5 A-3); P1 assumes one run (C-2), the tree gives no concurrency control and the lock is the rest of OD-17 (ADR-0004 decision 10); the environments of C-7; "a directory exists only when something was written into it" (ADR-0004 decision 1).
- What is open around the id and is not an input: what starts an instance and in which order it writes the first files (sub-questions ⑩ and ⑰); what a second start with a `run_id` that is in use means (sub-question ㉓); whether a branch or a continuation is a new run (sub-question ①); the physical form of the data plane (OD-25, owner-only).

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice — among them that the form binds a builder and no reader, the two parts, their notation and length, that an id states nothing, what is promised of order, the number of random bits, the properties of the two sources, and every limit that names no source.

### 1. Scope: the form binds what builds an id

- **When a component of the system builds a `run_id`, it builds it by the rule of decision 2.** This record says nothing of which component that is, of when it does so, or of which events call for a new id (a start, a branch, a continuation).
- **The form is not a rule of validity.** What a valid `run_id` is stays what ADR-0004 decision 8 says: a name that matches its pattern. A name that matches the pattern and is not of the form is a valid `run_id`, and by this record nothing refuses a run, or treats it differently, because its id is not of the form. So `hilclaw.layout.check_run_id` and every reader on `main` stay as they are, and no literal of a test or of an example of a record becomes invalid.
- **Whether a run may have an id the system did not build** — a name given by a person or by a caller — **is not decided** (sub-question ㉔). No requirement asks for it or excludes it; this record does neither.
- The pattern of ADR-0004 decision 8 and the layout version (decision 9: version 1) are unchanged: no path, file name or number form changes, and every id of the form matches the pattern.

### 2. The form

An id built by this rule is `<time>-<random>`, **33 characters**:

| Part | Notation | Value |
|---|---|---|
| `<time>` | 16 characters `YYYYMMDDthhmmssz`: digits, with the letters `t` and `z` in lower case | The reading of the clock at the moment the id is built, in UTC, to the second; a year from `0001` to `9999`, `hh` 00-23, `mm` and `ss` 00-59 |
| `-` | one hyphen | |
| `<random>` | 16 characters of `0-9a-f` | 64 bits from the source of decision 6, as lower-case hexadecimal |

Example: `20261009t012331z-9f3a6c1e0b7d4a52`.

- A name is **of the form** when it has this shape, `[0-9]{8}t[0-9]{6}z-[0-9a-f]{16}`. The rule builds names of this shape whose time part is a time of the table; a name of the shape need not hold such a time, and whether a name of this shape was built by the rule cannot be told from the name.
- Why this notation: the time part is the basic date-time notation of ISO 8601 with its two letters in lower case, because the pattern has no upper-case letter (cited: ADR-0004 decision 8); it is fixed in width, so names whose time parts differ compare as those parts do (decision 4). Hexadecimal can be produced in each language of the tool layer without a table of its own. The first character is a digit and the length is 33 of the 64 the pattern allows.

### 3. What an id states

**Nothing.** An id is a name: no component parses one, and no fact of a run is read from its id — not the time the run started, not the machine, not that the id was built by the rule. The time part is the reading of a clock at the moment of the build and is **no record of when the run started**: this record does not say how long before the first write an id is built, and no record defines a member that holds a start time (the time notation of other files is sub-question ⑨, untouched). What a reader may take from a run is in its files, by the records that define them.

### 4. Order

- **What follows from the form**: two names of the form whose time parts differ are in the byte order of their time parts; for two ids built by the rule, that is the order of the two clock readings. Names with equal time parts are ordered by their random parts, which says nothing.
- **For whom**: a person who lists `runs/`. **No component may depend on the order**, for the reason of decision 3; "the latest run" is not defined by any record and is not defined here.
- **Under which premise**: the order is that of clock readings, not of events. Two ids built on two machines are ordered by two clocks; a clock that was set back, or that is wrong, puts a later id before an earlier one. The order is not the order in which runs started, and a name that is not of the form sorts wherever its bytes put it.

### 5. Uniqueness: what the form gives and what it does not

ADR-0004 decision 8 requires that a `run_id` "is unique within `runs/` of a data repository" (cited). That requirement is unchanged. Of "how uniqueness is obtained", this record answers the part a form can carry:

- **What the form gives.** Two builds give the same id only when their clocks read the same second and their 64 random bits are equal. With draws that are uniform and independent (decision 6), that has a probability of at most 2^-64 (about 5 × 10^-20) for two builds, and of less than n² / 2^65 for any two among n ids — about 3 × 10^-8 for a million ids. This bound does not use the time part, so a wrong clock does not weaken it, and it does not use C-2: it holds as well for the ids built on two clones of a data repository taken together. An id of the form is never equal to a name that is not of the form.
- **What the form does not give: it is no check and no reservation.** The rule takes nothing from the tree — an id is built without reading or listing `runs/` — and building an id creates nothing: a directory exists only when something was written into it (cited: ADR-0004 decision 1), so an id that was built and not yet used is not visible in the tree. **Collisions are improbable, not excluded**, and nothing said here notices one.
- **Not decided**: whether anything looks at `runs/<run_id>/` before the first write of a run, by which step an id that is in use is noticed, and what is done then. These belong to the start of an instance (sub-questions ⑩, ⑰ and ㉓ (i)), and this record neither requires nor excludes such a look. The sentence of ADR-0025 decision 4 — the last step of the write of `instance.json` "is not, by this record, the means by which a `run_id` is unique within `runs/`" — stands as it is.
- Whether "a data repository" in ADR-0004 decision 8 means one working tree or every clone of it is not read here. Uniqueness across separate data repositories, forks or a shared tier, and how two clones are brought together, are OD-25 and are not decided.

### 6. The two sources, as properties

- **The time** is the UTC reading of the clock of the machine on which the id is built. It is not compared with anything and **is trusted for nothing**.
- **The random part** comes from the operating system's source of random bits, the one meant for values that must not repeat or be guessed — **never from a generator that a caller seeds or that starts from a fixed or time-derived seed**. The reason is independence, not secrecy: a generator that is given the same seed in a second process or on a second machine repeats its sequence, and the bound of decision 5 rests on draws that do not depend on one another. An id is not used as a secret: it is the name of a directory in a repository.
- These are properties of an id that is built for a run. Whether a function of the package takes the time and the bits as arguments (so that a test can fix them) or obtains them itself is the code task's.

### 7. Limits

- **A clock that is wrong** gives a time part that is wrong and changes nothing else (decisions 3 to 5). A clock reading whose year is outside `0001` to `9999`, or whose second is 60, cannot be written in the form; what a builder does then is the code task's.
- **Two machines or two clones**: nothing on `main` compares the ids of two clones. If two runs were started on two clones under one id, a git merge of the data repository would report a conflict for each path both sides hold with different content and none for a path only one side holds, so the two runs could come to share one directory. This is a limit, not a rule: no record says that clones are merged or how.
- **A source that does not give independent draws** — two machines started from one copied image whose random source begins in the same state, for one — is outside the bound of decision 5: the bound holds as far as the draws are independent, and nothing here checks that.
- **An uncommitted working tree**: a run directory that exists only in a working tree is lost with it (cited: #5 A-3), and its id with it. Nothing remembers an id that was built; the form does not need it to.
- **An id that is not of the form** has none of the properties of decisions 4 and 5, and stays valid (decision 1).
- **Nothing here makes two runs at once safe** (cited: C-2; ADR-0004 decision 10; the lock is the rest of OD-17). Two builds at the same moment give equal ids with no more than the probability of decision 5; that is all the form adds.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | The form is a rule of validity: a reader refuses a `run_id` that is not of the form | It would change what ADR-0004 decision 8 accepts, make every literal of the tests and of ADR-0015 invalid, and decide that a person cannot name a run. Nothing needs it: no reader takes anything from an id (decision 3). |
| 2 | A random part only | Equal in uniqueness. A listing of `runs/` would be in no order a person can use, and the time part costs 17 characters of a name that stays within the pattern. |
| 2 | A running number obtained by listing `runs/` | Listing one directory of known path is allowed (ADR-0004 decision 3), so #4 §1 is not the reason. Two clones give the same number to two runs as a matter of course, not of chance. And the number depends on what is in the tree at the build, where a number that was taken and not yet written is invisible (ADR-0004 decision 1): the rule would need a reservation, which is the start of an instance and the lock (sub-question ㉓, OD-17). |
| 2 | An id derived from the content of the instance (a digest) | No record defines a canonical form of `instance.json` (ADR-0025 decision 4). A second start with an equal content would be given the id in use, which decides what sub-question ㉓ leaves open; and the id would have to be built after the content, which fixes an order at the start. |
| 2 | Parts that name the owner, the project, the hw_profile or the kernel | Owner and project are meta fields, not path levels (#4 §2c); a part of the directory name that states them is a path level by another spelling, and a reader would begin to parse it. The hw_profile key is in `instance.json` (ADR-0018) and is up to 49 characters long (ADR-0001 decision 3); whether one instance covers several values of M is open (ADR-0004 Boundaries). |
| 2 | A standard identifier with a time in it (a UUID of version 7, a ULID in lower case) | Their time is not readable by a person, which is the only use of the time part here (decision 4), and nothing parses an id, so a standard notation buys no reader. |
| 2 | Local time; a finer resolution | Local time repeats an hour at the end of daylight saving and differs between machines. A finer resolution adds length and nothing to uniqueness, which rests on the random part. |
| 3 | A reader takes a fact from the id: the time part as the time the run started | The time part is a clock reading at the build, and this record does not say how long before the first write an id is built. Every id would be bound to the form (point 1), and a clock would become a source of truth about runs. |
| 4 | Components may rely on the order ("the newest run is the last name") | It would make a clock a source of truth about runs and would bind every id to the form (point 1). |
| 5 | 32 random bits; 128 random bits | With 32 bits the bound of decision 5 becomes n² / 2^33: about one in a hundred for ten thousand ids when the time part does not separate them (a clock that stands still). 128 bits lengthen every path for a bound nobody needs. |
| 5 | The build looks at `runs/` and draws again when the name is there | A look is not a reservation (two steps), and it would make the rule a part of the start of an instance (sub-question ㉓ (i)). A later record may add a check at the start; the form does not stand in its way. |
| 6 | A generator seeded by the caller, by the time or by the process number | Two processes or two machines with equal seeds build equal ids: the case the random part is there to exclude. |

## Consequences

- **A code slice can now be cut** (code mode, within the size cap): a function of the package that builds a `run_id` of the form, probably in a new small module with its test file. Where it lives, its name and its call form are that task's. `hilclaw.layout.check_run_id` is unchanged. **Binding the function to a tool, to a start of an instance or to any caller is not part of that slice.**
- **The open value of the example of ADR-0002** (`"run_id": "NOT-DECIDED-HERE"`) can now be an id of the form; that example and PLAN P1-5 are follow-ups and are not edited here.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0004 decision 8, last sentence ("The form stays open …") and the row of its Alternatives on a chosen form; ADR-0002, the row of `id.run_id` ("Its form is not decided here" — still true of that record), the row of its example table ("no source gives a run id form") and its Boundaries ("the form of a `run_id`"); ADR-0012 Status and Boundaries ("the form of `run_id`"); ADR-0025 Context ("the form of a `run_id` and how its uniqueness is obtained"), decision 4 ("ADR-0004 decision 8 leaves open how uniqueness is obtained" — a check at the start is still open) and Boundaries; the Status of ADR-0005, ADR-0006, ADR-0013 and ADR-0014 and the Boundaries of ADR-0018, each of which lists "the form of `run_id`" as open; ADR-0008 Consequences and Boundaries ("the form of a `run_id`" among what the committed example still misses); in `hilclaw/layout.py`, the docstring of `check_run_id` ("the form of a ``run_id`` is open"). These are the places a search of `ARCHITECTURE/decisions/` and `hilclaw/` for the phrase found; the list is not claimed to be complete. The module docstring of `hilclaw/layout.py` ("builds no ``run_id`` and does not know whether one is unique") stays true. No sentence of UsageCases became false: UC-1 says that the system creates `runs/<run_id>/` and nothing of the id.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The pattern of ADR-0004 decision 8 and the layout version are unchanged, no file gains or loses a member, and no file or name changes its validity, so this is not a schema change of the data plane.

## Boundaries (not decided here)

- **Owner-only or waiting for the owner (DRIVER §9)**: OD-3, OD-25, C-6, the #5 A and B items. **Uniqueness beyond one data repository** — across forks, separate repositories or a shared tier — and how two clones are reconciled (OD-25).
- **What builds an id, and when**: the component that starts an instance, whether an agent or a tool of the package does it, and the order of the first files (sub-questions ⑩ and ⑰, first part; OD-23; PLAN P2-1).
- **A second start with a `run_id` in use, a resume, a branch or a continuation**, and whether any of them gets a new id (sub-questions ① and ㉓ (i); FR-6; OD-20). **Nothing here says that a resume keeps or changes the id.**
- **Any check or reservation of an id at the start**; a lock, concurrent runs (rest of OD-17; C-2); the isolation means and the right to create `runs/<run_id>/` (sub-questions ⑭, ⑯ and ㉓ (ii)).
- **Any member of any file**: a start time, an owner, a project or a display name of a run in `instance.json`; anything in `STATE.json` (PLAN P1-8; OD-11); the time notation of other files (sub-question ⑨).
- **Sub-question this record raises** (registered under OD-8): ㉔ whether a run may be started under an id the system did not build — a name given by a person or by a caller — and, if so, what is required of such a name beyond ADR-0004 decision 8 and what checks it (with the first part of ⑰, ㉓ (i), OD-23).
- The contract of any tool, hooks, gates, budgets, the roster.
- Any change to the pattern of ADR-0004 decision 8, to the layout version, to ADR-0001 to ADR-0026, to `hilclaw/`, to tests, to CI, to any settings file, or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-6, FR-13, NFR-1, NFR-2, C-2, C-7; register rows OD-8, OD-17, OD-20, OD-23, OD-25.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8); [StandardScenarios](../StandardScenarios.md) S1, S3, S5, S10; [UsageCases](../UsageCases.md) UC-1.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; decisions 1, 3); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id`; the example; Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 3, 8, 9, 10; Alternatives; Boundaries); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (Status; Boundaries); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (the example request); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (the `hw_profile` member); [ADR-0025](ADR-0025-od8-instance-file-write.md) (decision 4; sub-question ㉓).
- #4 body §1, §2c · #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- ISO 8601 (basic format of a date and time).
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-5, P1-8, P2-1; `hilclaw/layout.py`, `hilclaw/spec.py`; tasks T-0021, T-0082, T-0086.
