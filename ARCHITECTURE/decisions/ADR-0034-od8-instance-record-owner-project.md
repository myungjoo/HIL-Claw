# ADR-0034: The `instance.json` of a run — the two members that state the owner and the project of the run (one more part of the rest of OD-8)

## Status

- **Accepted on 2026-10-09** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two words, kept apart in every sentence below.** "The repository owner" is the owner of DRIVER §9: the person who owns this repository and answers on issue #5. "The owner of a run" and "the project of a run" are what the two members of this record state; `owner` and `project` in code font are those members. The second is no statement about the first, and "project" below never means this repository.
- **Three kinds of content, none of them a decision of the repository owner.** No sentence of the repository owner on issue #5 speaks of an owner or a project of a run. **#4 §2c and the agreed layout of #4** are the agreed part of the body of issue #4 and are cited as #4's, as [ADR-0004](ADR-0004-od8-data-plane-layout.md) cites them. **The choices of earlier records** — [ADR-0001](ADR-0001-od4-key-schema.md) (the *string* form), ADR-0004 (the file, written once; the DB mirror) and [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (the frame of the file and its version rule) — were accepted under §9 and have not been confirmed by the repository owner; they are cited as theirs. **Everything else is this record's own design and has not been confirmed by the repository owner**: that each member states a name and no more, what a reader may and may not conclude, the name `project`, the place and the form of the two members, that a valid file may lack either, what such a file means, that no rule ties a member to anything, and how the members are read.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): of `runs/<run_id>/instance.json`, the two members in which a run states its owner and its project. It **changes no status, no rule and no proposal of OD-25, OD-17, OD-20, OD-23 or OD-27**. The register rows of OD-8 and OD-25 keep their status wording.
- What stays open: what an owner of a run and a project of a run are beyond a stated name, where the start of an instance takes the names from and whether anything checks them, every other member of `instance.json`, what writes the file, the sub-question this record raises, and every item under Boundaries.
- It builds on ADR-0001 (decision 1, the *string* form; objection window until 2026-10-13), on ADR-0004 (decisions 1, 4, 7, 9 and 10) and [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 7 and 8), whose windows run until 2026-10-14, on ADR-0018 (decisions 1, 2, 4 and 6), [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 3), [ADR-0022](ADR-0022-od8-instance-record-source-commit.md) (decision 5), [ADR-0023](ADR-0023-od8-instance-record-n-max.md) (decision 4) and [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) (decision 3), whose windows run until 2026-10-15, and on [ADR-0028](ADR-0028-od8-instance-record-candidates-per-round.md) (decision 4), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 5), [ADR-0032](ADR-0032-od8-instance-record-round-budget.md) (decisions 3 and 4) and [ADR-0033](ADR-0033-od8-instance-record-wall-clock-budget.md) (decisions 3 and 4), whose windows run until 2026-10-16. [ADR-0002](ADR-0002-od6-codegen-spec.md) (window until 2026-10-13) and [ADR-0027](ADR-0027-od8-run-id-form.md) (until 2026-10-16) are cited, not built on. **If one of the records it builds on is reverted, this record is revisited with it** — ADR-0004 and ADR-0018 in particular.
- The repository owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **#4 §2c** ("결정점 2 — owner/project는 경로 레벨이 아니라 메타 필드", agreed), about the originally proposed path `/execution_instance/${username}/${projectname}/${instanceID}/${turn}/`: "`username`을 경로에 박지 않음: P1은 단일 run 전제(C-2)라 과하고, CI/autonomous 액터는 username이 서비스 계정이라 모호. `instance.json`의 `owner` 필드로." and "`projectname`도 메타 필드로(경로 nesting보다 DB 컬럼이 깔끔, NFR-6)."
- **The agreed layout of #4**: "`<run_id>/` # = instanceID. owner/project는 경로 아닌 메타" and "`instance.json` # 불변 입력: hw_profile, model_ref, target, budget, gates, owner, project".
- **#4 gives the two fields a place and a name, and says what they replaced. It does not say what an owner or a project of a run is.** It calls the user name of a CI or autonomous actor ambiguous and does not say what such an actor states. No row of Requirements, no use case and no scenario uses either field: the glossary entry "Loop instance" and UC-1 step 1 list what the user gives at the start, and neither an owner nor a project is in the list; the actors are "배포 엔지니어 / CI" (UC-1) and "CI / 헤드리스 배치" (S2). The comments of issue #4 do not speak of the two fields.
- **Earlier records**: "owner and project are meta fields, not path levels" (ADR-0004 Context; likewise ADR-0001 Context); the file is "What the instance was started with", written by "The start of the instance, once" (ADR-0004 decision 1, the path table); in the DB mirror a run directory would become "one row of a run table (owner and project as columns)" (ADR-0004 decision 9). ADR-0027 refused parts of a `run_id` that name the owner or the project, and an id states nothing (decision 3). The Boundaries of ADR-0012, ADR-0018, ADR-0023, ADR-0028, ADR-0031 and ADR-0032 list owner and project among the members no record defines.
- **Forms that exist**: a *name* matches `[a-z][a-z0-9_]{0,31}` and a *string* is 1 to 255 printable ASCII characters, 0x20 to 0x7E (ADR-0001 decision 1); the attribute `label` of a key record is a *string*, "Free text for humans". A *text* is "a JSON string of at least one character, with no length limit in version 1" (ADR-0002, for the members of a spec).
- ADR-0018 gave `instance.json` its frame and said how the file grows: each later record "chooses between a member that may be absent from a valid file and a new version" (decision 2).
- **Another field of the same name.** #4 §2e proposes `lock{owner, heartbeat}` in `STATE.json` (OD-17, not decided): the holder of a lock, in another file. The `lock.owner` that `hilclaw/driver_state.py` checks through `PROCESS/STATE.schema.json` belongs to `PROCESS/STATE.json` of the development driver. Neither is the member of this record.
- The code: `hilclaw/instance.py` defines `schema_version`, `hw_profile`, `tolerance`, `source_commit`, `n_max`, `candidates_per_round`, `op_signature`, `round_budget` and `wall_clock_budget_s`; a top-level member of any other name in a content the module can read — `owner` and `project` among them — is handed back uninterpreted in `Instance.others`. **No module of `hilclaw/` reads, writes or checks an owner or a project of a run.**
- Fixed and not re-decided: #4 §2c and the agreed layout; ADR-0004 (the file, written once; the tree enforces none of it — decision 10); the frame of the file and its version rule; the members that exist; that an id states nothing (ADR-0027); that no access control exists (ADR-0010 decision 8).
- **Open and not touched**: data governance (OD-25, reserved for the repository owner — "owner-only" in DRIVER §9); what writes the file and what the start of an instance does (OD-8 sub-questions ⑩, ⑰, ㉓, ㉔; OD-23); an index of runs by key (sub-question ②, with OD-20); the lock (OD-17); notifications (OD-27); every member that waits for the repository owner.

## Decision

No sentence below renders a decision of the repository owner. A value is **cited** when a source is named with it. Every other value is **this record's own** choice — among them that each member states a name and nothing more, the lists of what a reader may and may not conclude, the name `project`, that the two are top-level members, the *string* form for both, that either may be absent, that an absent member means "not stated" and that nothing stands in for it, that a present and invalid member makes the file invalid, that no rule ties a member to the other, to another member, to another file or to another run, and the list of limits.

### 1. Scope

This record fixes one thing of `runs/<run_id>/instance.json`: the two members in which a run states its owner and its project. Nothing else of the file is fixed and nothing of any other file. **A file that holds what ADR-0018, ADR-0020, ADR-0022, ADR-0023, ADR-0024, ADR-0028, ADR-0031, ADR-0032, ADR-0033 and this record define is still not a complete instance record, and no run can be started from it alone** (ADR-0018 decision 1).

### 2. What each member states

- **`owner` states the owner the instance was started with, as a name. `project` states the project the instance was started with, as a name.** That the file holds the two is cited (#4 §2c: the `owner` field of `instance.json`; the agreed layout: `owner` and `project` among the immutable inputs of the file), and so is that the file holds what the instance was started with (ADR-0004 decision 1). That each is a name follows #4's own words for what the fields replaced, `username` and `projectname`.
- **This record reads no more into either word.** #4 says where the name goes that the proposed path would have held as `${username}`: into the field `owner`. It says that `projectname` is a meta field as well. It defines neither an owner nor a project, and neither does this record: **each member holds the name it was given at the start, uninterpreted.**
- **What a reader of this record may conclude** from a file that states `owner`: that the run states this name as its owner. From a file that states `project`: that the run states this name as its project. No more.
- **What it may not conclude.**
  - **No identity.** The value is not thereby the name of a person, of an account or of a service account, and not a user name of an operating system, an author or a committer of a git commit, a GitHub account or the account of a Claude Code session. Nothing checks the value against any of them, and this record names no source the value is taken from.
  - **No right.** No right to read, write, resume, branch, share or promote anything follows from either value. No access control exists (cited: ADR-0010 decision 8), and what is shared or promoted is OD-25, which this record does not enter.
  - **No path and no id.** Neither value is a path level (cited: #4 §2c) or a part of a `run_id` (cited: ADR-0027 decision 3 — no fact of a run is read from its id).
  - **No relation between runs.** Two runs whose files state equal values are not thereby related by any rule of this record, and it does not say that they belong to one person or to one project. Two values that differ in any character are two values (decision 3).
  - **Nothing about the run itself.** Neither value says which hardware, model, kernel or source the run is about; `project` is not the name of this repository, of the data repository or of a directory.
- **What an owner and a project are beyond a stated name is not decided here.** The inputs do **not** carry, and this record does not decide: whether an owner of a run is a person or an account; what a CI or an autonomous actor states as the owner (#4 §2c calls the user name of such an actor ambiguous and gives no rule); what a project of a run is and what it groups; where the start of an instance takes either name from; and whether anything checks either. They are registered (sub-question ㉛ (i) and (ii)). **Each member has its meaning without them**: it records what the instance was started with (cited: ADR-0004), as the `label` of a key record is "Free text for humans" (cited: ADR-0001) without a rule about what a human writes there. The cost, plainly: until such a rule exists, a reader cannot tell from the two values who or what they name, and this record does not help it.
- **One value of each per run.** The file is written once (cited: ADR-0004 decision 4) and each member is one string.

### 3. The members

- **The members are `owner` and `project`**, two top-level members. **Each is a *string* of ADR-0001: 1 to 255 printable ASCII characters (0x20 to 0x7E).** The two are valid independently of each other.
- **Nothing else is a value**: the empty string, a string longer than 255 characters, a string that holds a character outside 0x20 to 0x7E (a line feed, a tab, a letter of another script), `null`, `true`, `false`, a number, an array and an object.
- **A value — the string after JSON decoding — is compared character for character.** `Example-Owner`, `example-owner` and `example-owner ` (with a final space) are three values. This record folds no case and removes no space, and a reader of this record does neither.
- **The names.** `owner` is #4's name for the field (cited: §2c). `project` is the word of #4's agreed layout and of the heading of §2c; §2c's sentence about the field says `projectname`, the level of the proposed path. Taking `project` is this record's choice: it is the word the layout puts beside `owner`. Weighed against it:
  - `username`, `projectname` — the names of the path levels #4 removed; `username` says that the value is a user name, which decision 2 does not say.
  - `owner_name`, `project_name`, `user`, `account`, `started_by` — each says more than #4 does, or says the same in a name #4 does not use.
- **Why two top-level members and not one object** (`meta`, or `owner` and `project` inside another member). #4 calls the two "메타 필드" as opposed to path levels: the word says where they are not, and names no object. The agreed layout lists `owner` and `project` in one row with `hw_profile` and `budget`, whose members stand at the top level (ADR-0018; ADR-0032 decision 3 and ADR-0033 decision 3 on an object for the budget). An enclosing object would need a name no input gives, would say which other members are "meta" — a judgement about members that are not this record's —, and the DB mirror asks for none: it has the two as columns of the row of a run (cited: ADR-0004 decision 9). **This record fixes no object for any other member**, and two members side by side are no rule for a third.
- **Why the *string* form.**
  - *A name* (`[a-z][a-z0-9_]{0,31}`): it would refuse `Example-Owner`, `example.owner` and every value with a capital letter, a hyphen, a dot or a space. That is the syntax of an identifier, and no input says that an owner or a project is named by one.
  - *A text* of ADR-0002, or any wider JSON string: it has no upper length and admits line feeds and every script, in which one visible name can have several spellings (composed and decomposed forms). No input asks for such a value, and a rule that makes those spellings one is a rule this record would have to invent.
  - *An object* (`{"name": …, "kind": "person"}`) or *an array of names*: a kind is a statement about what an owner is, which decision 2 leaves open; #4 names one field, not a list.
  - **The *string* is the form of `label`, the free text of the key records**, and of their string key fields such as `revision`; it has an upper length, and it has no composed and decomposed forms. Of the two forms that exist for free text it is the narrower one: a later record that widens it makes no file invalid that is valid by this one, while a narrowing of a wider form would. **What it cannot state: a name written in another script, and a name longer than 255 characters.** That is a cost of this choice and no statement that an owner or a project has an ASCII name; a record that widens the form changes the form of a member and applies the version rule (cited: ADR-0018 decision 2).
  - **The form carries no meaning.** It is not the syntax of an account, of an e-mail address or of a path component: `a b`, `x/y` and `user@example.invalid` are values, and none of them says thereby what it names. A value that consists of spaces only is valid as well (decision 6).

### 4. A file without a member; the version

- **Each member may be absent from a valid file, independently of the other, and `schema_version` stays `1`** — the first of the two choices ADR-0018 decision 2 leaves to the record of a member ("A later record that defines a top-level member which may be absent and may be passed over does not raise it"), as ADR-0020 decision 3, ADR-0022 decision 5, ADR-0023 decision 4, ADR-0028 decision 4, ADR-0031 decision 5, ADR-0032 decision 4 and ADR-0033 decision 4 chose for their members. A version 1 reader may pass over both: no fixed rule makes anything a reader of today does depend on either, and a reader that needs the owner or the project of a run is one that knows the members.
- **A member that is present must be valid.** A file whose `owner` or whose `project` breaks decision 3 is **invalid** in the sense of ADR-0018 decision 2: a reader of this record reports it, uses no member of it — not its `hw_profile`, not the other of the two — and repairs nothing. This follows the same decisions of the seven records named above.
- **A valid file without `owner` states no owner; a valid file without `project` states no project.** A reader of this record that is asked for the owner or the project of such a run finds that none is stated. **"Not stated" is no default and no anonymous or shared value**: the reader **never substitutes a value** — not the user name of the process that reads or that wrote the file, not the author or the committer of a commit of the data repository, not a GitHub account, not the name of a directory, of the data repository or of the source repository, not a part of the `run_id`, and not the value of another run — and it does not conclude that the run has no owner or belongs to no project, only that the file states none.
- **No path yields an owner or a project the run did not state.** A reader of this record has the owner of a run only when the file of that run is valid, is of version 1 and holds `owner`; likewise for `project`. A missing file, a file that cannot be read, an invalid file, a file of another version and a valid file without the member each leave it without one.
- **What this record does not say**: whether the start of an instance refuses to begin without an owner or without a project, and what follows for a run whose valid file states none (sub-question ㉛ (iii)). A valid file is "not thereby enough to start a run" (cited: ADR-0018 decision 2).
- **Why not required members and version 2.** #4's layout lists seven inputs of the file, and three of them have no form yet (`model_ref`, `target`, `gates`): the list says what the file is for and is not read by any record as a rule of validity. No input says that a run cannot be had without an owner or a project — UC-1 step 1 does not list either among what the user gives. Every file and every reader of today would be of another version before a first run exists, the record would have to say which layout version the new `schema_version` states (ADR-0024 decision 3), and reading another version is OD-11.
- **The cost**: validity does not show that an owner or a project is stated. A file without a member and a file whose member name is misspelt look alike to a version 1 reader — both state none (decision 6).

### 5. The members and everything else; how they are read

- **This record adds no rule between `owner` and `project`.** A file may state either, both or neither; no value of one restricts the other, and no pair of values is refused.
- **No rule between either member and another member of the file.** The `hw_source` and the `label` of the hw_profile record are about the hardware (cited: ADR-0001 decision 1); `source_commit` names a commit and no author (ADR-0022). Nothing is compared with either.
- **No rule between either member and another file or another run**: none with `STATE.json` (and none with a lock, which no record defines — OD-17), with `events.ndjson`, with a spec, with `db/` or with the file of another run. Nothing is looked up, grouped, counted, ordered, refused or notified by either value, and no file is invalid because of the values other files hold.
- **The owner and the project a run states are those in these members of the file of that run**, `runs/<run_id>/instance.json` below the data root in use. A reader of this record reads the file as a whole, which must be valid (ADR-0018 decision 2), and **nothing is kept between calls** (cited: ADR-0010 decision 7; ADR-0018 decision 4): a later call reads the file again.
- **Today nothing reads, writes or checks either member**: no tool, registry, backend, hook or module does, and `hilclaw/instance.py` passes both over. **Not said here**: which component reads them, at which moment, and what follows when none is stated (Boundaries).

### 6. Limits

- **Whoever can write the file states any owner and any project.** No access control exists and the tree does not enforce the single writer (cited: ADR-0004 decision 10; ADR-0018 decision 6); nothing checks a value against an identity (decision 2). The members are a statement and no proof.
- **A file written once cannot change its owner or its project.** A run handed over to another owner, and a project that is renamed, have no form in this file; a file changed after the start is read as it is at that read (cited: ADR-0018 decision 6).
- **A name committed to the data repository stays in its history.** The repository "is pushed at the owner's decision and its history is the audit log and is not rewritten" (cited: ADR-0004 decision 7, which says it of secrets; "the owner" there is the repository owner). An `owner` that is the name of a person is then readable by whoever can read the repository, for as long as the history exists. Who that is, and what is shared, is OD-25; this record decides nothing of it and states the limit only.
- **A misspelt name.** A top-level member that is not spelt `owner` or `project` (`Owner`, `user`, `username`, `projectname`, `Project`) is passed over (cited: ADR-0018 decision 2, the cost), and the file states no owner or no project.
- **Without a rule of spelling, equal names need not name the same thing and different names need not name different things.** `Example-Owner` and `example-owner` are two values; two persons can be given one name. A value of spaces only, or one that differs from another in a final space, is valid and looks empty or equal to a human.
- **A name in another script cannot be stated** (decision 3).
- **Two processes, two sources** (cited: ADR-0010 decision 7; ADR-0018 decision 6): a source older than the code of this record passes over the members and takes as valid a file whose `owner` or `project` a newer source refuses.
- The name `owner` stands near the `lock{owner, heartbeat}` of #4 §2e and near the word for the repository owner; it is neither (Status; Context).

### Example

The placeholders of the Example of ADR-0033 with the two new members, so this is the shape of the members and **not a valid file** (`NOT-DECIDED-HERE` is no valid `hw_source`), and not a complete instance. **The values of `owner` and `project` are placeholders: they name no person, no account and no project that exists, and no reader supplies either for a file that lacks the member.**

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
  "op_signature": {
    "key": "gemm-485b9bc494d477eb",
    "record": {
      "schema_version": 1,
      "kind": "gemm",
      "shape": {"m": 1, "k": 2048, "n": 8192},
      "dtype": "fp32",
      "layout": "row_major"
    }
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10,
  "candidates_per_round": 2,
  "round_budget": 8,
  "wall_clock_budget_s": 5400,
  "owner": "example-owner",
  "project": "example-project"
}
```

### Walk-through

What a reader of this record finds when it is asked for the owner and the project of the run `r1`.

| `runs/r1/instance.json` | What the reader finds |
|---|---|
| Valid, version 1, with `"owner": "example-owner"` and `"project": "example-project"` | The owner `r1` states: `example-owner`. The project `r1` states: `example-project`. Asked again in a later call, it reads the file again |
| Valid, version 1, with `"owner": "example-owner"` and without `project` | The owner `r1` states: `example-owner`. No project is stated for `r1`, and no value is substituted |
| Valid, version 1, with neither member | No owner and no project are stated for `r1`. No value is substituted for either. The other members of the run can still be had |
| `"owner": ""`, `null`, `7`, `true`, `["example-owner"]`, `{"name": "example-owner"}`, a string of 256 characters or a string that holds a line feed or a letter outside ASCII; or the same for `project` | The file is invalid: no member of it is used, neither the owner nor the project, the `hw_profile` or any other |
| Valid, version 1, with `"Owner": "example-owner"`, `"user": "example-owner"` or `"projectname": "example-project"` | As the third row: the member of a nearby name is passed over, and no owner or no project is stated |
| `r1` and another run `r2` both state `"owner": "example-owner"` | The owner each states: `example-owner`. **By this record nothing follows**: the two runs are not related by it, nothing is grouped or allowed, and whether the two values name one person or one account is not said (sub-question ㉛ (i)) |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The record defines an owner (the person who started the instance; the account of the session; the user name of the operating system) | No input carries one, and #4 itself calls the user name of a CI or autonomous actor ambiguous. A definition would bind what starts an instance, which no record has named (sub-question ⑰; OD-23), and a definition by an account would lean on an identity nothing establishes. |
| 2 | The record defines a project (a model, a hardware target, a team, a set of runs that share knowledge) | No input says what a project groups; a grouping that shares anything is OD-25, and a grouping by hardware or operation is what the two keys of ADR-0001 already do. |
| 2 | No member until an owner and a project are defined | #4 put the two into the file as agreed architecture; the values given at the start would be recorded nowhere, and a later definition would have nothing to apply to. The `label` of ADR-0001 is a member of the same kind. |
| 2 | Only `owner` is given a member, `project` is left to a later record | The inputs carry the same for both — a place, a name and what the field replaced — so the argument that settles one settles the other. |
| 3 | One object `meta` with both; `owner` and `project` inside another member | See decision 3. |
| 3 | `username`, `projectname`, `owner_name`, `project_name`, `user`, `account`, `started_by` | See decision 3. |
| 3 | A *name*; a *text* or a wider string; an object with a kind; an array | See decision 3. |
| 3 | The form folds case or removes outer spaces; a value of spaces only is refused | A rule of spelling no input gives, and a second form of free text beside the *string* of ADR-0001. The cost is named in decision 6. |
| 3 | A value for "nobody" or "anonymous" (`null`, an empty string, a reserved word) | A statement #4 does not have: a run that states no owner is the file without the member. |
| 4 | An absent member means a default (the user of the process, the committer, the name of the data repository) | It would derive an identity from an account or a path, which decision 2 does not do; a misspelt name would then read as that default. |
| 4 | Required, with `schema_version` 2; required without raising the version | See decision 4; the second is against ADR-0018 decision 2. |
| 4 | A present and invalid member leaves the file valid and counts as "not stated" | Two notions of validity for one file (ADR-0020 decision 3, Alternatives), and a damaged statement would pass unreported. |
| 5 | A rule that the two are stated together, or that runs with one owner or one project are listed, grouped or checked against each other | No input gives one. An index of runs is open even by key (OD-8 sub-question ②, with OD-20); a rule keyed on an owner or a project is OD-25. |

## Consequences

- **The code slice that can now be cut** (within the size cap, code mode): in `hilclaw/instance.py`, the validity of the two members by decision 3 and readers of the owner and of the project of a run beside `wall_clock_budget_s_of`, with tests in `tests/test_instance.py`. The names and the return form of the readers and how "not stated" is told from a value are the code task's. **Binding a reader to a tool, to a hook, to `db/`, to `STATE.json` or to anything that lists, groups or allows is not part of that slice**, and neither is writing the file. `hilclaw/instance_file.py` takes the validity of a content from `hilclaw.instance.parse`, so it refuses a content with an invalid member once the slice lands, without a change of its own.
- **Sentences of the code that then change**: in the docstring of `hilclaw/instance.py`, the list of the records in its first line and first paragraphs, the sentences that count the records ("the nine records"), the order of the checks, and the descriptions of `Instance.others` in `parse` and of the records in `validate`. No case of `tests/test_instance.py` holds a top-level `owner` or `project` today, so none asserts a content valid that this record makes invalid; the assertion on `Instance._fields` and every case that builds an `Instance` positionally change only if the slice adds fields to that tuple.
- **Not edited and now less exact** (follow-ups for the integrator): the Boundaries of ADR-0012 ("all of `instance.json` (target, budget, gates, tolerance, owner, project, …)"), ADR-0018 ("owner and project (ADR-0004 decision 9)"), ADR-0023, ADR-0028, ADR-0031 and ADR-0032, which list owner and project among the members no record defines; the lists of what makes `instance.json` invalid in ADR-0018 decisions 2 and 4 and in ADR-0019 decision 3, which an `owner` or a `project` that breaks this record joins; ADR-0025 decision 2, where the members a valid content may lack now have two more. ADR-0004 and ADR-0027 stay exact. No sentence of UsageCases became false: the glossary entry "Loop instance" and UC-1 step 1 do not name an owner or a project among what the user gives, and this record does not say that the user gives them.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The record adds two members that may be absent to a file whose frame says how later records add members (ADR-0018 decision 2), along the D6 route as ADR-0020, ADR-0022, ADR-0023, ADR-0028, ADR-0031, ADR-0032 and ADR-0033 did; by that frame's own rule the version stays `1`. **The set of valid version 1 files becomes narrower without a new version**: a file that holds an `owner` or a `project` breaking this record was valid before and is invalid now — the case ADR-0018 decision 6 named; no such file exists in a data plane, since nothing starts an instance yet. No member, value list or validity rule of the members that exist, of the key records or of `STATE.json`, `spec.json`, `artifacts.json` or `events.ndjson` changes.

## Boundaries (not decided here)

- **Identity and its check**: who or what counts as an owner of a run, a person against an account, what a CI or an autonomous actor states, where the start of an instance takes the names from and whether anything verifies them (sub-question ㉛ below; OD-8 sub-question ⑰; OD-23).
- **Access, sharing and governance — reserved for the repository owner (DRIVER §9, "owner-only")**: any right or policy keyed on an owner or a project of a run; what is shared or promoted; the physical form of the data plane (OD-25). Access control of tools (ADR-0010 decision 8; OD-23). No proposal of OD-25 is adopted or rejected.
- **Looking up runs by owner or by project**: an index, a listing, a query. No record defines one; the registered question about an index of runs is OD-8 sub-question ② (by key; with OD-20), and the database is P2. ADR-0004 decision 9 has the two as columns of a run table; this record defines no table, no column type and no key.
- **Notifications addressed to an owner** (FR-16, OD-27), and **the lock** of #4 §2e with its `owner` (OD-17) — a different field of a different file, of which nothing is defined here.
- **Every other member of `instance.json`** (PLAN P1-8), none of which is named here, and what waits for the repository owner: the objective (#5 A-4, OD-1), gates and the autonomy mode (#5 A-5, OD-3), the coder model and the token budget (#5 A-8), the model input (#5 B-5, OD-9), datasets (#5 B-8).
- **The writer and the start of an instance**: what writes `instance.json`, what offers a user the choice of a name, and whether the start refuses to begin without an owner or a project (OD-8 sub-questions ⑩, ⑰, ㉓, ㉔ and ㉛ below; OD-23; UC-1).
- **Any tool's contract** (OD-18): no tool, moment of a call, request or result member or tool-failure kind is given here, and nothing HQ-0005 asks.
- **Any member of `STATE.json`**, any event kind, any result file; reading or migrating a file of another version (OD-11).
- **Sub-question this record raises** (registered under OD-8): ㉛ Three parts. (i) What the start of an instance states as the owner of a run: whether an owner of a run is a person or an account; what a CI or an autonomous actor states as the owner; where the start takes the name from; and whether anything checks it (with ⑰, OD-23). (ii) What a project of a run is and what it groups; where the start takes the name from; and whether anything checks it (with ⑰, OD-23). (iii) Whether the start of an instance refuses to begin without an owner or without a project, and what follows for a run whose valid file states none (with ⑰, OD-23).
- Any change to a member that exists (`schema_version`, `hw_profile`, `tolerance`, `source_commit`, `n_max`, `candidates_per_round`, `op_signature`, `round_budget`, `wall_clock_budget_s`), to `STATE.json`, to the spec schema, to another data-plane file; any change to ADR-0001 to ADR-0033, to `hilclaw/`, to tests, to CI, to `pyproject.toml`, to any settings file, or to the `HIL-Claw-data` repository; a JSON Schema file; any new external dependency.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-13, FR-16, NFR-2, NFR-6, C-2; register rows OD-8, OD-11, OD-17, OD-20, OD-23, OD-25, OD-27.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-25](../OpenDecisionProposals.md#od-25); [UsageCases](../UsageCases.md) glossary "Loop instance", UC-1, UC-3, UC-6; [StandardScenarios](../StandardScenarios.md) S1, S2, S5.
- Issue #4 (body): §2c, §2e, the agreed layout — https://github.com/myungjoo/HIL-Claw/issues/4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (the *text* form); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (Context; decisions 1, 4, 7, 9, 10); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 7, 8); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (Boundaries); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 1, 2, 4, 6; Boundaries); [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decision 3); [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 3); [ADR-0022](ADR-0022-od8-instance-record-source-commit.md) (decision 5); [ADR-0023](ADR-0023-od8-instance-record-n-max.md) (decision 4; Boundaries); [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) (decision 3); [ADR-0025](ADR-0025-od8-instance-file-write.md) (decision 2); [ADR-0027](ADR-0027-od8-run-id-form.md) (decision 3; Alternatives); [ADR-0028](ADR-0028-od8-instance-record-candidates-per-round.md) (decision 4; Boundaries); [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 5; Boundaries); [ADR-0032](ADR-0032-od8-instance-record-round-budget.md) (decisions 3, 4; Boundaries); [ADR-0033](ADR-0033-od8-instance-record-wall-clock-budget.md) (decisions 3, 4; Example).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, A-5, A-8, B-5, B-8.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-8; `hilclaw/instance.py`, `hilclaw/instance_file.py`, `hilclaw/keys.py`, `hilclaw/driver_state.py`, `tests/test_instance.py`; tasks T-0015, T-0021, T-0066, T-0102.
