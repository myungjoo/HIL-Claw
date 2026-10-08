# ADR-0022: The `instance.json` of a run — the member that states the commit of the source repository the instance was started with (one more part of the rest of OD-8)

## Status

- **Accepted on 2026-10-08** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two kinds of content.** The **owner's decisions** are #5 A-1 detail 3 (2026-07-22) and #5 A-12 point 4 (2026-10-02): `instance.json` records the commit hash of the source repository as the tool version, and in P1 the version of the harness is that hash — the P1 implementation of the measurement-contract pin of OD-11. They are quoted, marked **owner**, and are not subject to the objection window below. **Everything else is this record's own design and has not been confirmed by the owner**: the name, the place and the form of the member, what it can express for a source that is not exactly a commit, that a valid file may lack it, and how it is read.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): of `runs/<run_id>/instance.json`, the one member in which a run states that commit. It gives the confirmed part of OD-11 the member that part refers to and **changes nothing of OD-11**: its register row keeps `제안됨`, and none of its proposals is taken. The register row of OD-8 keeps its status wording.
- What stays open: every other member of `instance.json` — the layout version stamp among them —, what writes the file, everything of OD-11 beyond its confirmed part, the sub-question this record raises, and every item under Boundaries.
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4 and 10) and [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7), whose objection windows run until 2026-10-14, and on [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 2 and 6) and [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 3), whose windows run until 2026-10-15. If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. For the record's own choices the owner may object within 7 days of that notice; an objection creates a task that reverts them and the edits made with them.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Owner** (#5 A-1 detail 3): "재현성: submodule 핀 대신 **메타 기록** — `instance.json`에 소스 repo commit hash(도구 버전)를 기록하여 '이 run은 어떤 도구 버전으로 만들어졌나'를 보존." **Owner** (#5 A-12 point 4): the harness "in P1 its version **is** the source-repo commit hash already recorded in `instance.json` (A-1 detail 3) — this is the P1 implementation of OD-11's measurement-contract pin."
- The requirements rest on it: the data plane and the source are two repositories, "어느 한쪽 history만으로는 감사 로그가 성립하지 않는다 — 둘을 잇는 고리(`instance.json`에 소스 commit 기록 …)가 필수다" (NFR-2); NFR-7 ③; the last sentence of FR-9.
- The fact has no member. ADR-0004 named it in the purpose of the file ("What the instance was started with; source commit (#5 A-1); layout version") and fixed no field. ADR-0018 gave the file its frame and handed this member on: "the source commit raises which repository, which form and what a tree with local changes means" (Boundaries). ADR-0003, ADR-0007, ADR-0009, ADR-0010 and ADR-0017 lean on "the source commit" without a member to point at (decision 6).
- The code: `hilclaw/instance.py` defines `schema_version`, `hw_profile` and `tolerance`; a top-level `source_commit` is handed back uninterpreted, whatever its value. No module of `hilclaw/` runs `git`, and `hilclaw.config.json` binds the data repository only. The package version (`0.0.0` in `pyproject.toml` and `hilclaw/__init__.py`) is not a commit and is not used as a pin by any record.
- Fixed and not re-decided: the two owner decisions; NFR-2; NFR-7 ① (components can be replaced at a round boundary) and FR-6 with NFR-7 ② (a resume holds after the system version changed) as they stand; ADR-0004 (the file is "What the instance was started with", written by "The start of the instance, once", and the tree enforces none of it — decision 10); the frame of the file and its version rule (ADR-0018 decision 2); that nothing is kept between calls (ADR-0010 decision 7). Of OD-11 only its confirmed part is fixed.

## Decision

A sentence marked **owner** renders one of the two owner decisions, both quoted in Context. A value is **cited** when another source is named with it. Every other value is **this record's own** choice — among them the name `source_commit`, the string form and its two lengths, the meaning "exactly that commit", that the member has no form for a source that is not exactly a commit, that the member may be absent, that a present and invalid member makes the file invalid, and the list of limits.

### 1. Scope

This record fixes one thing of `runs/<run_id>/instance.json`: the member in which a run states the commit of the source repository it was started with. Nothing else of the file is fixed and nothing of any other file. **A file that holds what ADR-0018, ADR-0020 and this record define is still not a complete instance record, and no run can be started from it alone** (ADR-0018 decision 1).

### 2. What the member states

- **The repository** is the source repository of the owner's sentence ("소스 repo"): the one that holds the tool package `hilclaw/` and the layer-1 definitions (cited: Requirements §0; #5 A-12 point 1), which FR-13 keeps apart from the data repository `HIL-Claw-data`. A commit of the data repository — the durability boundary of #5 A-3 — is another commit of another repository and is never a value of this member.
- **The commit** is the one the instance was started with (cited: ADR-0004, "What the instance was started with"; **owner**: "이 run은 어떤 도구 버전으로 만들어졌나").
- **The meaning** (this record's own): the member states that **the source the instance was started with is exactly the content of that commit** — every file of the source repository that took part in the start as source is a file of that commit, with the content the commit gives it. "Exactly" is the point of decision 4.
- **What a reader of this record may conclude** from a file that states the member: that the run makes this statement about its start, and — as far as the statement is true — that the tool package the instance was started with, the harness in it (**owner**: in P1 its version is this hash), is the content of that commit in any repository that holds the commit.
- **What it may not conclude**: that any later result of the run was produced by that source (decision 6); that the commit exists in a repository or was ever pushed (decision 8); and anything about what a commit of the source repository does not determine — the installed dependencies and the interpreter, the Claude Code version and the model of an agent, the compiler and the machine (the `hw_profile` of the run states what ADR-0001 put into that record; the rest has no member).
- **It is a statement about the start, made by whatever writes the file.** Which tree that writer looks at — the checkout a command-line call loads, the source an MCP server process loaded at its own start (cited: ADR-0010 decision 7) — and how it establishes the equality is not decided (sub-question ⑳). This record fixes the meaning a stated member has, not the observation behind it. If the parts that took part in the start were not all of one commit, the source is not exactly a commit (decision 4).

### 3. The member

- **The member is `source_commit`**, a top-level member (the phrase of NFR-2 and of ADR-0004), a JSON string that is **the full object name of a commit of the source repository: exactly 40 or exactly 64 characters, each one of `0`-`9` and `a`-`f`**. The two lengths are those of git's two object formats (SHA-1 and SHA-256); the source repository uses the first today, and the length of a value tells which.
- **Nothing else is a value of the member**: another JSON type, an upper-case hexadecimal digit, an abbreviated object name, the name of a branch or of a tag, the output of `git describe`, a prefix or white space around the name. One spelling per commit makes equality of two values equality of two strings, and a name that can come to mean another commit later — a branch, a tag, an abbreviation — preserves nothing.
- **Why a string and not an object.** The member states one thing. An object would be the place for a second statement, and none has a fixed input: a repository identifier has none (below), and a mark for a tree that differs from the commit is rejected in decision 4.
- **The repository is not identified in the file.** No fixed input names a form for identifying the source repository: `hilclaw.config.json` binds the data repository (#5 A-1 detail 2), and the owner's sentence records "소스 repo commit hash" and no more. An object name identifies the content of a commit in whichever repository holds it; where a reader finds such a repository is not said here (Boundaries).
- **In version 1 a run states at most one source commit**: the member is one string. The file is written once (cited: ADR-0004), and a source that changes later is decision 6.

### 4. A source that is not exactly a commit

- The cases: a tracked file of the source was changed, added or removed against the commit; a file the commit does not hold took part as source; the package was run from a place that is no checkout of the repository; the parts that took part in the start were of more than one commit.
- **The member has no form for any of them.** It holds a commit, and by decision 2 a stated commit means "exactly this content". An instance started from such a source has no commit that identifies its source, so by this record its file cannot state one: **the member is absent**, and the file states no source commit (decision 5). **The member never states a commit that does not identify the source the instance was started with** — the link NFR-2 requires is then missing for that run, visibly, and is not made false by a value that names a neighbouring commit.
- **A validator cannot check this.** The form excludes a statement of the kind "this commit, with differences"; it does not prevent a false statement (decision 8).
- **Which files count as the source** — a file git does not track that no tool loads, a file git ignores, a local settings file — is not drawn here file by file. The test is the meaning of decision 2 (does the commit determine the source the instance was started with); applying it belongs to what writes the file (sub-question ⑳).
- **What the start of an instance does when it meets such a source is not decided**: refusing the start, starting with a file that states no source commit, and stating the difference in a member a later record defines all stay possible. A later record that adds such a member applies the version rule of ADR-0018 decision 2 to it; a record that gave `source_commit` itself another form or meaning would raise the version (cited: the same rule), so a reader of this record never takes anything else for a commit that identifies the source.

### 5. A file without the member; the version

- **The member may be absent from a valid file, and `schema_version` stays `1`** — the first of the two choices ADR-0018 decision 2 leaves to the record of a member ("A later record that defines a top-level member which may be absent and may be passed over does not raise it"). A version 1 reader may pass over the member: no fixed rule makes anything a reader does depend on it, and whether a call compares it with anything is OD-11 (decision 6). A later record that makes a reader depend on it applies the version rule then.
- **A member that is present must be valid.** A file whose `source_commit` breaks decision 3 is **invalid** in the sense of ADR-0018 decision 2: a reader of this record reports it, uses no member of it — not its `hw_profile` or its `tolerance` either — and repairs nothing. This follows ADR-0020 decision 3.
- **A valid file without the member states no source commit.** **Owner**: `instance.json` records the source-repo commit hash. With an absent member allowed, that reads as follows: a valid file is not thereby a complete instance record (ADR-0018 decisions 1 and 2). The owner's sentence is about what the start of an instance records; whether it admits an instance that states none (decision 4) and where that is checked are not decided (sub-question ⑳). A reader of this record that is asked for the source commit of such a run finds that none is stated and **never substitutes a value — in particular never the commit of the source the reader itself runs from**, nor the head of any checkout, a commit of the data repository or the package version.
- **No path yields a commit the instance did not state.** A reader of this record has the source commit of a run only when the file of that run is valid, is of version 1 and holds the member. A missing file, a file that cannot be read, an invalid file, a file of another version and a valid file without the member each leave it without one.
- **Why not a required member and version 2.** Every file and every reader of today would be of another version before a first run exists, and reading another version is OD-11. And with decision 4 a required member would decide that no instance starts from a source that is not exactly a commit — the question this record leaves to the writer.
- **The cost**: validity does not show that a source commit is stated. A file without the member and a file whose member name is misspelt look alike to a version 1 reader — both state none (decision 8).

### 6. What the member is the pin of, and what it is not

- **Owner** (#5 A-12 point 4): in P1 the version of the harness "**is** the source-repo commit hash already recorded in `instance.json`", the P1 implementation of the measurement-contract pin of OD-11. `source_commit` is the member in which that hash is recorded; this record adds nothing to the owner's sentence.
- **The member states the source at the start of the instance and nothing later.** The file is written once (cited: ADR-0004), NFR-7 ① lets components be replaced at a round boundary, and FR-6 with NFR-7 ② lets a run be resumed after the system version changed. After such a change the member still names the source of the start, and **it does not name the source that produces the later results of the run**. A reader of this record that finds the member therefore knows the source of a result of the run only as far as the source has not changed since the start, and the file does not say whether it has.
- **Everything about a later change is OD-11 and is not decided**: whether a result records the commit of the source that produced it, whether a call compares the source it runs from with this member, and what follows from a difference. The proposals there — a hash of the measurement contract in every eval record and a forced re-measurement of the incumbent; at a resume, detecting and reporting a stamp that differs — are cited as proposals ("제안", "제안(미확정)" in OD-11; "OD-11 제안, 확정 전 잠정" in NFR-7 ① and ②), and none is taken. ADR-0010 decision 7 says the same of one of them: "whether a tool checks its own commit against the one a run recorded is OD-11".
- **How earlier sentences read against this** — a reading of this record; none of them is edited. The last sentence of FR-9 and ADR-0007 ("the source commit hash recorded for the instance", Context; "A result is traced to the policy that produced it through the source commit hash of the instance", decision 8) name this member, and hold of a result when the file states the member, the statement is true (decision 8) and the source has not changed since the start. Where a record says that a constant, a generator or an algorithm is "identified by the source commit" (ADR-0007 decision 9; ADR-0009 decision 5; ADR-0017 decision 3), or that the harness version or the package is pinned by it (ADR-0003, Alternatives; ADR-0010 decision 7), the commit meant is that of the source that carried out the step; this member states it for the start, and the two are the same under the same three conditions. ADR-0009 decision 8 and ADR-0017 decision 7 speak of two parts of the harness that are of one source commit and do not depend on this member.

### 7. How the source commit of a run is read

- **The source commit a run states is the one in this member of the file of that run**, `runs/<run_id>/instance.json` below the data root in use. A reader of this record reads the file as a whole, which must be valid (ADR-0018 decision 2), and **nothing is kept between calls** (cited: ADR-0010 decision 7; ADR-0018 decision 4): a later call reads the file again.
- **A value from elsewhere is not what the run states and does not stand in for it**: a member of a request, a value kept from an earlier call, the commit of the source the reader runs from.
- **Today nothing reads or writes the member**: no tool, hook or module does, and `hilclaw/instance.py` passes it over. **Not said here**: which tool or component reads it, at which moment, and what it does with it (Boundaries).

### 8. Limits

- **Whoever can write the file changes what the run claims to have been produced by.** No access control exists and the tree does not enforce the single writer (cited: ADR-0004 decision 10); a file changed after the start is read as it is at that read (cited: ADR-0018 decision 6).
- **The statement is not checked.** Nothing establishes that the stated commit exists in the source repository, that it was ever pushed, or that the source at the start was its content. #5 A-3 puts a durability boundary on the data repository; no fixed input says anything of the kind for a commit of the source repository, so a stated commit may exist in one clone only and can be lost with it.
- **A misspelt name.** A top-level member that is not spelt `source_commit` is passed over (cited: ADR-0018 decision 2, the cost) and the file states no source commit — never a substitute.
- **Two processes, two sources** (cited: ADR-0010 decision 7; ADR-0018 decision 6): an MCP server runs the source it loaded at its start and a command-line call the source as it is now, so one stated commit may not cover both; and a source older than the code of this record passes over the member and takes as valid a file whose `source_commit` a newer source refuses.
- **The commit names the source and nothing around it**: not the installed dependencies or the interpreter, and not what decision 2 lists. Two runs that state the same commit need not have been produced by the same software.
- **A source that changed after the start** is not seen in the file (decision 6).

### Example

The placeholders of the Example of ADR-0020 with the new member, so this is the shape of the member and **not a valid file** (`NOT-DECIDED-HERE` is no valid `hw_source`), and not a complete instance. **The value of `source_commit` is a placeholder in the valid form of 40 characters; it is not a commit of this repository.**

```json
{
  "schema_version": 1,
  "hw_profile": {
    "key": "cpu_standin-b0d8610d8f470856",
    "record": {
      "schema_version": 1,
      "accelerator": "cpu_standin",
      "revision": "NOT-DECIDED-HERE",
      "toolchain": {"clang": "NOT-DECIDED-HERE"},
      "host": {"cpu": "NOT-DECIDED-HERE", "os": "NOT-DECIDED-HERE"},
      "hw_source": "NOT-DECIDED-HERE"
    }
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567"
}
```

### Walk-through

What a reader of this record finds when it is asked for the source commit of the run `r1`.

| `runs/r1/instance.json` | What the reader finds |
|---|---|
| Valid, version 1, with `"source_commit": "0123456789abcdef0123456789abcdef01234567"` | The source commit `r1` states for its start: that value. Asked again in a later call, it reads the file again |
| Valid, version 1, without the member (or with `"source-commit": "…"`) | No source commit is stated for `r1`. No value is substituted, the reader's own included. The `hw_profile` and the `tolerance` of the run can still be had |
| `"source_commit": "0123456"`, `"main"`, `"0123456789ABCDEF0123456789ABCDEF01234567"`, `false` or `{"commit": "…"}` | The file is invalid: no member of it is used, neither the source commit nor the `hw_profile` nor the `tolerance` |
| Missing, unreadable, or of another version | No source commit can be had, as ADR-0018 has it for the `hw_profile` |
| Valid with the member, and the source was replaced after the start of `r1` (NFR-7 ① ②, FR-6) | The same value, which states the source of the start. The file does not show the change, and the source of a later result is not found in it (OD-11) |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 3 | An object (for example with a member for the commit and further members) | See decision 3: no second statement has a fixed input, and the version rule lets a later record add a member of its own. |
| 3 | A member that also identifies the repository (a URL or a name) | No fixed input gives a form; a URL names a place that can move, and the object name already identifies the content. |
| 3 | 40 characters only | It would bind the form to the object format the repository uses today, which no input fixes; a change of that format would then be a new version of this file. |
| 3 | An abbreviated name, or any spelling git resolves (a branch, a tag, upper case) | What it resolves to can change or become ambiguous later, and two spellings of one commit would not compare equal. |
| 3 | The package version of `pyproject.toml`, or a submodule pin | The version is `0.0.0` and names no source; #5 A-1 rejected the submodule. |
| 4 | (b) The commit and a second value saying that the tree differed | A reader that takes the commit takes a neighbour for the source; the mark says that the link is broken and not to what. And it presumes that a start records such a source — the writer's question. |
| 4 | (c) Something other than a commit for that case (a digest of the files, the object name of a tree) | A second form in one member, told apart only by a rule; a digest is no point of the source history NFR-2 links to. |
| 5 | Required, with `schema_version` 2 | See decision 5. |
| 5 | Required without raising the version | Against ADR-0018 decision 2, which makes a further required top-level member a new version. |
| 5 | A present and invalid member leaves the file valid and counts as "not stated" | Two notions of validity for one file (ADR-0020 decision 3, Alternatives), and a damaged statement of the audit link would pass unreported. |
| 5 | A reader fills an absent member with the commit of its own source | It states for the run what the run did not state, and is false whenever the source changed or differs between processes. |
| 6 | Say that a call compares its own source with the member, or that each result records its own commit | Both are proposals of OD-11 that the owner has not confirmed. |

## Consequences

- **The code slice that can now be cut** (within the size cap, code mode): in `hilclaw/instance.py`, the validity of the member by decision 3 and a reader of the source commit of a run beside `hw_profile_of` and `tolerance_of`, with tests. The name and the return form of that reader and how "not stated" is told from a value are the code task's. **Obtaining the commit of the running source — a `git` call or anything else — is not part of that slice**: it belongs with the writer, as writing the file does (ADR-0018 Consequences).
- **Sentences of the code that then change**: in the docstring of `hilclaw/instance.py`, "It defines no member besides the three and interprets no other", the order of the checks, and the description of `Instance.others`, in which a `source_commit` member is handed back today. One case of `tests/test_instance.py` (`test_the_top_level_is_open`) asserts today that a content with `"source_commit": false` is valid; it changes with the slice.
- **Not edited and now less exact** (follow-ups for the integrator): the `instance.json` row of the path table of ADR-0004 ("Fields: PLAN P1-8, OD-11"); ADR-0018 Boundaries ("The source commit member … neither gets a name or a form here") and its Example ("no … source commit"); ADR-0020 Boundaries ("the source commit member … included") and its decision 3, where "not its `hw_profile` either" now has a third member beside it; the list of what makes `instance.json` invalid in ADR-0018 decisions 2 and 4 and in ADR-0019 decision 3, which a `source_commit` that breaks this record joins; the parentheses of FR-9, NFR-2 and NFR-7 ③, which name the fact and could name the member. No sentence of UsageCases became false.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The record adds one member that may be absent to a file whose frame says how later records add members (ADR-0018 decision 2), along the D6 route as ADR-0020 did; by that frame's own rule the version stays `1`. **The set of valid version 1 files becomes narrower without a new version**: a file that holds a `source_commit` breaking this record was valid before and is invalid now — the case ADR-0018 decision 6 named; no such file exists in a data plane, since nothing writes the file yet. No member, value list or validity rule of `hw_profile`, of `tolerance`, of the key records or of `STATE.json`, `spec.json`, `artifacts.json` or `events.ndjson` changes, and no member is added to `hilclaw.config.json`.

## Boundaries (not decided here)

- **Everything of OD-11 beyond its confirmed part**: a pin or a hash in eval records; forced re-measurement of an incumbent; detecting or reporting a difference at a resume or at a call; the P1 / P2 boundary of NFR-7 ② ("오너 확정 없이 NFR-7② 본문에 반영하지 않는다"); reading or migrating a file of another version; comparability across harness versions (ADR-0007 decision 10 stands as it is); how a run is tied to the calibration evidence of the harness version it pins (ADR-0003 Boundaries).
- **The layout version stamp** (ADR-0004 decision 9; ADR-0018 decision 2): it gets no name and no form here, and neither `source_commit` nor `schema_version` is said to serve as it.
- **The writer**: what writes `instance.json`, by which steps, how it obtains the commit, what it does with a source that is not exactly a commit, and when the file is written in relation to `STATE.json` (OD-8 sub-questions ⑩, ⑰ and ⑳; OD-23; UC-1); any `git` call of the package.
- **Any tool's contract** (OD-18): which tool or component reads the member, the moment of a call, request and result members, any tool-failure kind. Whether a result file (`eval.json`) or a line of `events.ndjson` records a source commit (PLAN P1-8, OD-23, OD-11).
- **Every other member of `instance.json`** (PLAN P1-8), none of which is named here: the list of ADR-0018 Boundaries without the tolerance of the first case and without this member. Several wait for the owner (#5 A-4, A-5, A-8, B-5, B-7, B-8).
- **The source repository as a place**: how a tool identifies or locates it, any member of `hilclaw.config.json`, the package version as a pin, a submodule pin (#5 A-1 rejected it); what a change of the operating model would mean for "the source repository" (OD-25).
- **Sub-question this record raises** (registered under OD-8): ⑳ How the start of an instance establishes the commit it states — which tree it looks at when more than one process takes part, which files count as the source, by which means — and what it does when the source is not exactly a commit or it cannot tell: refuse the start, start with a file that states no source commit, or state the difference in a member a later record defines; and where it is checked that an instance states its source commit, as the owner's sentence has it (with ⑰ and OD-23; a source that changes after the start is OD-11).
- Any change to a member that exists (`schema_version`, `hw_profile`, `tolerance`), to another data-plane file; any change to ADR-0001 to ADR-0021, to `hilclaw/`, to tests, to CI, to `pyproject.toml`, to any settings file, or to the `HIL-Claw-data` repository; a JSON Schema file; any new external dependency.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-6, FR-9, FR-13, NFR-2, NFR-7 ① ② ③; register rows OD-8, OD-11, OD-18, OD-23, OD-25.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-11](../OpenDecisionProposals.md#od-11); [UsageCases](../UsageCases.md) UC-1, UC-6, UC-E4; [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b, S2, S3, S5, S6, S8, S10.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decision 6; Alternatives; Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4, 9, 10); [ADR-0007](ADR-0007-od13-measurement-policy.md) (Context; decisions 8, 9, 10); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decisions 5, 8); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7); [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) (decisions 3, 7); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 1, 2, 4, 6; Example; Consequences; Boundaries; sub-question ⑰); [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decision 3); [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 3; Example; Boundaries).
- #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-8; `hilclaw/instance.py`, `hilclaw/config.py`, `hilclaw.config.json`, `pyproject.toml`, `tests/test_instance.py`; tasks T-0066, T-0067, T-0071, T-0072, T-0076.
