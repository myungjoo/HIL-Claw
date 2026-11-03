# ADR-0193: The generalization design of PLAN P3 — candidates plug in at the make and evaluate seam of an unchanged round loop with only the C kernel path bound, a target table in the package source beside the backend table, a virtual NPU as a generalization check only, an internal model graph file outside the data plane beside the unchanged forward program, and harness programs generated from the contract table for the kinds of one shape — with the owner's parts stated as questions (part of OD-32 sub-questions ② to ⑤; ①, ⑥, ⑦ not decided)

## Status

- **Accepted on 2026-11-03.** It is the design PLAN P3-1 asks for, under DRIVER §6 D27 ⑤: it leaves the owner's parts undecided and writes the form in which to ask them.
- **Three kinds of content.**
  - **Owner**, cited: D27 (the #5 comment [6567151354](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6567151354)), HQ-0078 ⑤, HQ-0083 (b) and HQ-0085 (b) in `PROCESS/STATE.json`. The owner's answers are **not subject to the objection window** below. Statements of accepted records and of the code are cited with their source.
  - **This record's own**: decisions 1 to 8, every sentence no source is named with. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it**, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
  - **Left open, for the owner**: decision 9. Each part there is a question with concrete options; a recommendation is the executor's and decides nothing.
- **Session entry check** (CLAUDE.md), on 2026-11-02 before any edit of `ARCHITECTURE/`: open PRs: none. No open `nightly-failure` issue. `PROCESS/RuntimeAcceptance.md`: no item whose `상태` is `실패`. Issue #4: last comment 2026-07-31; #7: last comment 2026-09-07; #8: closed; #5: last comment 2026-11-02, the D27 decision. Unresolved HQ: HQ-0081 only (S6), not crossed. Repeated on 2026-11-03 after the last rebase: the same, with on #5 the vendor-stack direction ([6572518011](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6572518011); FR-19, OD-33, PLAN P3-7 to P3-13), the review limit (D28) and the toolchain answer ([6590711662](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6590711662); D29).
- **The search for other owner sentences.** Searched on 2026-11-02: the bodies of #4, #5, #7 and #8 and their comments, 318 in all, of which 73 hold no "posted by driver" marker. Terms: 가상 NPU, virtual NPU, 그래프 파일, graph file, 양자화, quantiz, cycle, 사이클, 측정 단위, 벤더 언어, vendor language, QNN, AIMET, 후보 종류. Found: the D27 comment; the #5 B-3 question and its extension (simulator tiers, unanswered); "kernel language, vendor native or DSL" as a #7 finding filed under B-1 (unanswered); lossy techniques admissible within the tolerance (#5 5933950693; FR-9). The rest are the word "cycle" in other senses. **Conflicts: none.** The vendor-stack direction and the toolchain answer (D29) came after this search and name QNN and real toolchains; they do not conflict: PLAN P3-7 builds on this design, and no decision here rests on a fake toolchain.
- **Not changed**: no code, test, schema, member, version or validator. No package, no `claude` process, Docker daemon, model file, board or API key was used (D16). It builds on the records of References; none is edited. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Owner** (D27): "권장안대로 진행해". C kernels, vendor-language kernels, quantization settings and compile settings are all candidates to try and measure; the search loop stays and only what makes and evaluates a candidate is per kind. A virtual NPU, deliberately unlike the CPU in compiler options, memory limit, data type and measurement unit, comes first. A file of nodes and connections is read and run; Llama is moved to it and must give the same result, and a differently structured model on synthetic weights checks it; external formats (OD-9) wait. Harness code is generated from the contract table ([ADR-0177](ADR-0177-od18-od6-contract-table.md)), and only hard operations are handwritten. All this runs beside P2-15, and a P2-15 failure is fixed first. Parts that change a data format take the owner's approval, as v2 did.
- **Owner** (HQ-0078 ⑤): the measurement carries a unit member whose value for now is `ns`; designating its list as open is the owner's at target design. **Owner** (HQ-0083 (b), HQ-0085 (b)): fp16 and the gates are asked again after P2-15 (D27 ④).

## Decision

### 1. The survey: first-case assumptions and the item that lifts each

| Assumption | Where | Lifted by |
|---|---|---|
| Build flags and time limits are one CPU set of constants | `hilclaw/standin_settings.py`, read at `standin_check.py:385`, `standin_run.py:265`, `standin_run.py:286`, `standin_openmp.py:83` (ADR-0116 decision 2) | P3-2 |
| A model run has one target | `TARGET`, `hilclaw/model_run_binding.py:65` (ADR-0189 decision 1); ADR-0153 decision 1 | P3-2 |
| The accelerators an instance may start on are a hand-kept list | `_ACCELERATORS`, `start_instance.py:64` | P3-2. Not lifted: `_ACCELERATORS`, `s6_metric.py:157`, the scope of an S6 metric (HQ-0081's neighbour), which gets no `virtual_npu` |
| The backend table has two fixed entries | `default_table`, `check_definition.py:155` | P3-3 |
| A contract's coverage does not depend on the target | `contract_table.covers`, `check_covers`, `run_covers`, `start_covers` | P3-3 |
| No memory bound on any container | `standin_container.py`; ADR-0144, ADR-0182 decision 6 | P3-3 |
| The unit is `ns` alone | `UNITS`, `run_result.py:88`; `_UNIT`, `timings_tool.py:172`; ADR-0183 decision 4 | P3-3, on answer O3 only |
| Six kinds, fifteen call sites and one call order are fixed | `run_pass`, `model_forward.c`; `CALL_SITES`, `model_forward_run.py:75`; ADR-0166 decisions 1 and 3 | P3-4 |
| One handwritten C program per kind and per run form | `hilclaw/harness/bf16_timing_*.c`, `bf16_verification_*.c` | P3-5 |
| Each kind's dimensions are listed by hand beside the table | `_DIMENSIONS`, `harness/bf16_timing.py`; `_BF16_DIMENSIONS`, `standin_settings.py:115` | P3-5 |
| A kernel is `.c` and `.h` files | `kernel_source.py:164`; the coder's sentence, `coder_runtime.py:92` (ADR-0055) | P3-6 |
| One table entry per kind, dtype and layout, since a record states no language | ADR-0177 decision 1 | P3-6 |

**Not an assumption to lift**: `orchestration/round-manager.md` and `orchestration/agents/` name no kind, dtype or language; a search for `gemm`, `fp32` and `cpu_standin` finds none. So the loop's text needs no change for P3-2 to P3-5.

### 2. Candidate kinds and the seam (OD-32 ①, ⑥, ⑦)

- **The seam.** A candidate kind plugs in at two points of the unchanged round loop: **make** (from a spec to the attempt's output: today `spec.write` and `coder.run`) and **evaluate** (from an attempt to results: today `correctness.check`, `sim.run` and `board.run`, each through a backend, ADR-0016). **Owner** (D27): the search loop stays and only making and evaluating are per kind. **This record's reading, for the C kernel path of P3-2 to P3-5 only**: hypotheses, verdicts, budget, `STATE.json` and the Round-Manager's order do not change. What another kind needs of them is left to the answers to O1 and O2.
- **The C kernel path is bound: it is that path as it stands.** It adds no value, member or code. Files of today state no kind and keep doing so until O2 is answered. No Python abstraction over the seam is built in P3-2 to P3-5: with one kind it would have nothing to tell apart.
- **The other three: what an answer would plug into**, with nothing chosen.

| Kind | Make would plug into | Evaluate would plug into | Waits on |
|---|---|---|---|
| Vendor-language kernel | A contract whose `language` is not `c`: the table's key has the place (ADR-0177 decision 1), and a new `task.contract.language` value raises no spec version (ADR-0002 decision 7); admitted file names (ADR-0055) | The target's backend; the harness only if the kernel can be called by the contract's prototype | O1; #5 B-1 (which target, so which vendor toolchain; a vendor toolchain is obtained and used as FR-19 item 5 and D29 say, with none faked); who writes the code (⑥) |
| Compile settings | `task.build`, the place for settings prescribed for a candidate (ADR-0002 decision 6 (b)); a new member raises no spec version (decision 7) | The three tools as they are, with ADR-0116's "one fixed set" read per target and per candidate | O1, O2 |
| Quantization settings | No place today: it is a setting over a model, not one kernel | The executor and a quality measure; FR-9 admits a lossy technique within the user's tolerance only, and nothing today says what that is for a model | O1; C-6, #5 A-4 and B-8 (⑦); #5 B-5 |

- **Limit.** This section chooses no record format, coder role, instance unit, quality metric or evaluation data. The concrete formats of O2 are options to ask about.

### 3. The target description (OD-32 ②)

- **The place: a target table in the package source, `hilclaw/targets.py`.** One `Target` per `accelerator` value, with `flags`, `trailing_flags`, `waiter_flags`, `env`, the build time limit and process time-limit cap, `contracts` (the keys of the contract table it serves, so its data types and languages), `memory_limit_bytes` (an integer, or `None` for no bound), `unit`, `model_run` (a boolean: the model executor may take this target's runs) and `instance_start` (a boolean: an instance may start on it). The mock builds nothing and has no `Target`; `start_instance` admits the mock's name and each target with `instance_start` true. The compiler stays where it is (OD-14).
- **How it links.**
  - **To hw_profile (OD-4)**: by `accelerator` alone, the one field that selects (ADR-0016 decision 4). A target's values are no key fields (ADR-0001 decision 5), so changing one keeps the key, the cost ADR-0116 decision 2 states and `source_commit` traces.
  - **To the backend table (OD-26)**: each backend's operations are built with their `Target`, so an operation reads its own target, never the hw_profile handed to it (ADR-0060 decision 3 stands). The table is still built in one step and changed only by a commit (ADR-0016 decision 2).
  - **To a registry**: a later onboarding registry could fill both tables; whether it does stays OD-26.
- **`cpu_standin` keeps its behaviour and results.** Its `Target` reads the constants of `standin_settings.py`, which stay the source of those values (ADR-0116 decision 2 (a), ADR-0188). Its `contracts` are all seven entries, `memory_limit_bytes` is `None`, `unit` is `ns`, and both booleans are true. **Check for P3-2**: the existing tests for the argument lists of its builds and processes pass unchanged, apart from D21 list assertions.
- **The model run** (P3-2): `model_run_binding` takes a run whose target has `model_run` true, only `cpu_standin` at P3-2, and `other_target` otherwise. All call sites of one binding must have one target. `flags` stay the caller's (ADR-0189 decision 6). `hilclaw.model_check` keeps its behaviour for every run it accepts today.
- **Which placement needs no frame change.** This one: no file, member or value of the data plane holds it. A language or data-type value reaches a spec only through a contract's `task.contract`, which is the approved open list of DRIVER §3. The memory limit is applied, not stored (decision 4). The unit stays `ns`.
- **Which would change the frame, and is not taken**: a member of `hw_profile`, `instance.json` or a result (ADR-0116 decision 2 (c); no result member holds a setting today, ADR-0063). Asked only where a use needs it: `unit` (O3) and the settings of a compile-settings candidate (O2).
- **What the table does not settle**: two languages for one kind, dtype and layout at one target (OD-6 ④, OD-18 ⑩), and targets' endpoints (#5 B-2).

### 4. The virtual NPU (OD-32 ③)

**Its values exist to make first-case assumptions fail. No value here is a fact or evidence about any real NPU**, and no result of it is evidence of one. It is a backend `virtual_npu` running on the development machine, in the same ADR-0144 container path and with the same image as `cpu_standin`. Its results are keyed under its own hw key (#5 A-7's reason), so they cannot mix with those of another target.

| Value | `cpu_standin` | `virtual_npu` | What it tests |
|---|---|---|---|
| Flags | `-std=gnu11 -O2 -ffp-contract=off -fopenmp` | `-std=gnu11 -O1 -ffp-contract=off -fno-vectorize -fno-slp-vectorize` | No code assumes one flag set. Without `-fopenmp` clang ignores `#pragma omp` with a warning, so such a kernel runs single-threaded, and one calling `omp_*` fails its link as a broken result. `-ffp-contract=off` stays, as the contracts' rounding rests on it (ADR-0177 decision 3) |
| Trailing and waiter flags | `-lm`; `-std=gnu11 -O2 -ffp-contract=off` | the same | Unchanged: the C library is unchanged, and the waiter compiles no kernel (ADR-0188 decision 2) |
| Memory | no bound | `268435456` bytes, by `--memory` and an equal `--memory-swap` on each process container | The bound path. Over it, the process ends and the result is `broken` with the existing `condition` `exit_status`; a `memory_bytes` that is reported is one taken under the bound (ADR-0144 says a bound changes what ADR-0052 measures). `memory_ceiling` stays not admitted (ADR-0053 decision 4; ADR-0063 decision 7) |
| Data types | fp32 `gemm` and the six bf16 contracts | the six bf16 contracts only | Coverage per target; fp32 `gemm` is refused with the existing `OutOfScopeError` and `op_signature_not_covered` |
| Unit | `ns` | `ns` until O3 is answered | See below |
| Language | `c` | `c` | Not a P3-3 difference (PLAN P3-3) |
| `model_run` | true | false | The executor stays unbounded and at `cpu_standin` (ADR-0182 decision 6), and a model run at `virtual_npu` needs O4 ①. **So the second-target path of P3-2 is tested with a test's own `Target`, not by `virtual_npu`**; a later record can turn it on |
| hw key | ADR-0035 | `revision` `virtual-1`; `toolchain` and `host` read as for `cpu_standin` (ADR-0035, ADR-0186); `hw_source` stated by the caller, as ADR-0035 decision 8 has it | Another key on one machine. The value of `hw_source` stays the caller's (OD-26) |

The time limits, the rule of the environment and the source of the timing seed are `cpu_standin`'s, unchanged (ADR-0117, ADR-0179, ADR-0181, ADR-0116 decision 5, OD-13 ⑦). They are values of the check, which `-O1` without vectorization may slow within the cap. The bytes figure may change by commit in P3-3 if a test needs another boundary; it means nothing else.

- **What this table cannot decide: the oracle and tolerance outside `cpu_standin`.** FR-9 records the system-generated reference as settled for `cpu_standin` by HQ-0004 and not as the general answer of #5 B-7, and OD-31 ③ and the bf16 contract records stop at `cpu_standin`. ADR-0076 decision 1 says of another accelerator that nothing is required and nothing is allowed. So a `virtual_npu` run of a bf16 contract under the same reference and the user's tolerance is put to the owner (O4 ①), not read as following from D27. Until it is answered, `virtual_npu` has `instance_start` false and its backend offers no `correctness.check`, which answers `not_offered` (ADR-0016 decision 3). `contracts` holds the six bf16 entries in any case, since the two answers to O4 ① that use the target both need them for timing, and the rest of P3-3 is built and tested below the start.
- **Data type (fp16 excluded).** P3-3 does not depend on fp16 and does not ask about it again (**owner**, HQ-0083 (b); D27 ④). It can differ from the CPU in *which* types it serves with no new format. It can hold a type the CPU lacks **only through a new numeric format**, so that is an owner part (O4). The gate question of HQ-0085 is equally not asked or touched.
- **Measurement unit.** **P3-3 can go ahead with `ns`**: everything in P3-3 but that one difference is independent of it. `Target.unit` is read where a result is built, and `run_result.UNITS` still refuses anything else. So the assumption that a target has one unit is lifted in code and the frame is unchanged. Values other than `ns` and their open list are the owner's (**owner**, HQ-0078 ⑤): O3.
- **Verification.** Tests with a stub `claude` and a stub Docker client (D16). That the memory option behaves as stated on a real container is a runtime acceptance item P3-3 registers.

### 5. The model graph file (OD-32 ④)

- **Form.** One JSON file decoded under ADR-0155 decision 3's rules, with exactly these members:

| Member | Form |
|---|---|
| `graph_format` | integer `1`: this file's own version |
| `dimensions` | array of names the caller gives values for (`D`, `N`, …). Always available: `T` and `P`, the rows and start position of a pass, and `R`, the rows reported, which is `T` or 1 by the caller's `lm_head_rows` (ADR-0176 decision 5) |
| `weights` | array of `{"name", "shape", "per": null or a dimension name}`: logical weights, one per index of `per` |
| `tables` | array of `{"name", "shape", "source"}`: read-only inputs the host side makes, such as the RoPE table (`source` a name the host side knows; `hilclaw.rope_table`) |
| `scalars` | array of names of non-array arguments the caller gives, such as `eps` |
| `state` | array of `{"name", "shape", "per"}`: buffers kept between passes, such as a KV cache |
| `buffers` | array of `{"name", "shape"}`: buffers of one pass; each `shape` an array of integer expressions over dimensions with `+`, `-`, `*`, parentheses and no other operator |
| `nodes` | ordered array of the nodes below |
| `output` | `{"buffer", "rows"}`: what a pass reports for token selection; `rows` is an expression, `R` for Llama |

- **Nodes and connections.** **A connection is a buffer name**: nodes run in array order over named buffers, as `run_pass` of `model_forward.c` does, so buffer reuse is expressed and no scheduler is needed. There is no fusion (C-6 keeps it later). A node is one of:
  - `{"op": "kernel", "site", "kind", "shape": {member: expression}, "operands": {operand name: reference}, "scalars": {argument: scalar name}}`. `kind`, its operand names and its scalar arguments are the contract's; `site` is a call-site name the binding uses. A reference is the name of a buffer, weight, state or table, or `{"of": name, "start": expression}`, starting that many elements in: so `freqs_cis` is `{"of": "rope", "start": "P*d"}`, and `lm_head` has `m` `R` and its input `{"of": "normed", "start": "(T-R)*D"}`, the two cases of `run_pass`;
  - `{"op": "embed", "weight", "out"}`, the rows of that weight for the token ids of the pass (ADR-0152 decision 3);
  - `{"op": "copy", "from", "from_stride", "from_start", "to", "to_stride", "columns"}`, for each of the `T` rows, the range copy of ADR-0166 decision 3;
  - `{"op": "repeat", "count": dimension, "index": name, "nodes": [...]}`, in which `{index}` in a name selects the entry of a `per` weight or state.
- **Completeness.** This form was walked against every line of `run_pass` for Llama. A need the Llama file shows while P3-4 writes it extends format 1 before its first landing; that is P3-4's, as the file is outside the data plane.
- **Weight references.** A name in `weights` is **logical**. A provider the caller hands maps it to an array: `model_files` for the Llama file (ADR-0191, where the tensor correspondence and the Q and K order stay), or a test's synthetic arrays. So the graph holds no tensor name of an external format, and **external formats stay under OD-9**. This file is not the `model_ref` of #5 B-5.
- **Relation to the executor.** A new program and host module beside the existing ones: `hilclaw/model_graph.py` reads the file, checks it against the contract table and the caller's binding, and encodes a resolved call plan; `hilclaw/model_graph.c` runs that plan through the same library loading, report and token selection rules (ADR-0166 decision 7, ADR-0176 decision 5). **`model_forward.c`, `model_forward_run.py` and `model_check` are not changed** while P2-15 is open. Whether the graph program later replaces them is a later record's. It runs in the ADR-0182 container path at the bf16 dtype only.
- **The checks of P3-4.** The Llama graph file, with the synthetic weights of ADR-0166 decision 8, gives reports equal **byte for byte** to `model_forward.c`'s. A second graph of another structure, a feed-forward stack with no attention and other dimensions, matches a Python re-computation in its test. Both use the six existing kinds. The same check on real weights is a runtime acceptance item P3-4 registers (PLAN P3-4).
- **Outside the data plane: decided here under §9.** It is an input a person or test names to the executor, as the model directory is (ADR-0191) and the command's document is (ADR-0192 decision 1). No tool writes it to `runs/`, `db/` or the CAS, and no member of `instance.json`, a spec, a result or `artifacts.json` names it. `graph_format` is therefore no data-plane version. **The owner part of ④ is not reached**: it arises only when a model-level run is recorded, and no such record exists (ADR-0192 decision 7; OD-31 ⑧).

### 6. Table-based generation (OD-32 ⑤)

- **Generated**, by a pure function of the package from a contract-table entry, at build time into the build directory, then copied as today's sources are (ADR-0144): the `bf16_timing_*.c` and `bf16_verification_*.c` programs of **`gemm`, `rmsnorm`, `elementwise_add` and `swiglu`**. Those eight files differ in names, dimensions, operand lists, draw bits, one scalar and the form of their size-overflow checks, which the generator keeps (observed in `bf16_timing_elementwise_add.c`, `bf16_timing_swiglu.c` and `bf16_timing_rmsnorm.c`; the rest is P3-5's to confirm). The commit names the output, as it names any source (NFR-7 ③).
- **Read from the table, not generated**: the per-kind dimension lists of Python (`_DIMENSIONS`, `_BF16_DIMENSIONS`) become the shape parameters of `task_contract`.
- **What the table must gain**: draw bits per operand and the scalar arguments, today only in C and `bf16_verification_arrays.py`. They are constants of the contract modules. `task_contract` and `op_signature_record` do not change, so **no spec, result or other data-plane content changes**; and they are not new contract entries, so no open list is used.
- **Stays handwritten, with the reason.**

| What | Why |
|---|---|
| `rope` programs | `freqs_cis` arrive on standard input and a start position is part of the run (ADR-0164, ADR-0180) |
| `sdpa_kv_cache` programs | Guard rows, caches filled before the call, two bit-exact `inout` operands (ADR-0165) |
| fp32 `gemm`: `timing_driver.c`, `verification_program.c`; the waiter, `timing_waiter.c` | fp32 `gemm` has another report and generator (ADR-0009, ADR-0017) and shares no header with the bf16 programs, so it is not of the generated shape. **This is a reason other than the difficulty D27 names, listed for the owner to check.** The waiter runs no kernel (ADR-0145) |
| `bf16_timing.h`, `bf16_verification.h` | The shared loop, generator and exits: code generated programs include |
| The references in `bf16_*_arrays.py` and each kind's work measure in `standin_settings.py` | An operation's meaning (ADR-0179 decision 3). A table of shapes cannot derive it |

- **How "existing results unchanged" is verified** (P3-5, CI, clang and no Docker):
  1. With a test kernel of each of the four kinds and fixed arguments, the verification reports of the generated and the handwritten program are **equal byte for byte**.
  2. For timing, where times differ: the same test kernel writes a digest of the operands it is called with to standard error, the two programs' digests are equal, and both reports pass `hilclaw.harness.timing.judge_report`.
  3. The command lines, exit statuses and `PROGRAM` names are equal.
  4. No `step` value and no result definition changes (ADR-0100 decision 4).
- **Order.** The handwritten files stay until those tests pass in one task, and are removed in a later one, which keeps the report digests as test data.

### 7. Limits

- **fp16 and gates**: not depended on and not asked again (decision 4).
- **Not closed** (OD-32 "닫지 않는 것"): real target facts (#5 B-1, B-2, B-3), the open points of the Qualcomm reservation, OD-9. No NPU, SDK, model list, quantization method or quality metric is chosen.
- **P2-15**: nothing here changes what the owner's check runs (decisions 3, 5 and 6). P3 runs beside it, and a P2-15 failure is fixed first (**owner**, D27).
- **C-6 and CLAUDE.md**: the "C 커널" wording and C-6 are not changed (⑥, ⑦).

### 8. Dependencies and rough sizes (input for the planner; no task is created)

Cap: 600 LOC and 10 files per task, tests excluded (DRIVER §5).

| Item | Rests on | Must wait for | Can go ahead without an answer | Rough size |
|---|---|---|---|---|
| P3-2 | Decision 3 | Nothing | All of it | ~350 LOC, 8 files: 1 task |
| P3-3 | Decisions 3, 4 | O4 ① for `correctness.check` and the instance start at `virtual_npu`; O3 for a unit other than `ns`; O4 ② for a type the CPU lacks | Everything else: target entry, backend, flags, memory, coverage per target, `sim.run` and `board.run` below the start, `Target.unit` with `ns`. **The item is not checked before O3 and O4 are answered**; an answer that defers a difference closes that difference for the check | ~500 LOC, 8 files: 1 task, plus 1 small one on answer O3 (~150 LOC + reader changes) |
| P3-4 | Decision 5 | Nothing | All of it | ~1000 LOC with the C program: 2 tasks (format, reader, Llama file; then program, host, second model) |
| P3-5 | Decision 6 | Nothing | All of it | ~500 LOC for the generator and tests' support, ~600 changed for the removal: 2 tasks |
| P3-6 | Decision 2 | O1 and O2 (PLAN: "오너 확정 필요") | Nothing, by PLAN | Not sized: it depends on the answers |

### 9. The owner's parts (not decided here)

Each is a question for `PROCESS/STATE.json`; the full Korean text the driver records is in the task's `## Result`. Recommendations are the executor's.

- **O1, `owner-decision` (OD-32 ⑥, ⑦, with the scope of ①).** Which kind P3-6 takes first: compile settings (recommended: no vendor toolchain, as the existing real compiler serves; no new quality metric; fits a single-kernel instance), quantization settings (a quantization tool it needs follows the same D29 path), a vendor-language kernel (needs a vendor toolchain, D29, and #5 B-1), or none until a real target is chosen. Who makes that kind: the orchestrator's selection role writing `task.build` with no coder call (recommended for compile settings), the coder, or a deterministic tool. When CLAUDE.md's "C 커널" wording changes: when the first other kind lands (recommended), or now. The instance unit, artifact, quality metric and evaluation data of a model-level kind: asked when that kind is chosen (recommended), or now. A scenario for the flow: added with the first kind that lands (recommended), now, or none. **What the answer holds up**: P3-6; and P3-12, which waits on OD-32 ⑦ besides its OD-33 answers, so that answering "asked when that kind is chosen" does not release it.
- **O2, `data-plane-schema-change` (OD-32 ①, the record format; assumes compile settings first). A C kernel run's files are unchanged under every option but the result member below.**
  - `instance.json`: a member `candidate_kind`, a *name*. A reader that passed over it would treat a compile-settings run as a C kernel run, the case ADR-0018 decision 2 raises the version for, so **a file with the member has `schema_version` 2; a C kernel run still writes version 1 without it**, and the reader accepts both. One kind per instance (recommended) or per candidate, then with no `instance.json` member and no version change.
  - `spec.json`: new `task.build` members raise no version (ADR-0002 decision 7), but a spec is the input of one coder call (`id`, ADR-0002; `coder/…/spec.json`, ADR-0004). **So under O1's recommended no-coder answer a spec with no coder call widens `id` to the attempt and adds the selection role as a writer of that file: a meaning change, `schema_version` 3 for such a spec**; C kernel specs stay 2, and the reader accepts both. If the coder makes the candidate, the version stays 2. The kernel of such an attempt is read from the attempt the members name, and its own `output/` stays empty. The `task.build` members: `candidate_kind` (string), `flags` (array of strings: what the candidate adds to the target's flags), and `kernel_round`, `kernel_candidate`, `kernel_attempt` (integers: which attempt of the run gives the C kernel this candidate builds). All required when `candidate_kind` is `compile_settings`.
  - The settings a candidate was built with (this also answers OD-6 ② and OD-18 ⑰ (다) for this kind): (a) the place ADR-0004 already gives them, `build.json` under the attempt's `measure/`, which no code writes yet, written for this kind only: `schema_version` (integer 1), `outcome` (`"built"` or `"broken"`), `condition` (only when broken: the existing `build_time_limit` or `build_exit_status`), `flags` and `trailing_flags` (arrays of strings, the exact arguments); no result or `step` changes (recommended); (b) `artifacts.json`, a record of `type` `build_settings` whose blob holds the argument list; no result or `step` changes, as `type` has an open form (ADR-0005 decision 5), but a second place beside ADR-0004's; (c) a member `build_flags` in results (the `result` of a `step_ended` line in `events.ndjson`) of every kind, C kernels included, which needs four new `step` values `correctness_check_sim_v3`, `correctness_check_board_v3`, `sim_run_timing_v3`, `board_run_timing_v3` (ADR-0100). **If this and O3 (a) are both chosen, `sim_run_timing_v3` and `board_run_timing_v3` are one definition holding both changes**, landing together; a value is not defined twice (ADR-0100 decision 3).
  - `candidate_kind` as an **open list** in DRIVER §3, first values `c_kernel` and `compile_settings`: a value added by an ADR under §9 naming the list, with a value whose content is the owner's still asked (recommended); or a closed list the owner widens each time.
- **O3, `data-plane-schema-change` (OD-32 ② and ③, HQ-0078 ⑤).** Whether `unit`, in the `result` of a `step_ended` line in `events.ndjson`, becomes an open list, first values `ns` and `cycles`, read by `run_result.py` and `timings_tool.py`. (a) Open, with new `step` values `sim_run_timing_v3` and `board_run_timing_v3` under ADR-0100 for all targets, and readers accepting v2 and v3 (recommended); `cpu_standin` still reports `ns`. (b) Open under the v2 values, as an exception to ADR-0100. (c) Not now: `ns` until a real target. A value is added by an ADR naming the list. Under (a) or (b), for `virtual_npu`, `cycles` are its nanoseconds times a fixed factor in its `Target`, for the check only, with two consequences to state: the ADR-0103 coarse-clock test holds only within one unit, and a run's comparison is within its one unit. And whether the list reaches the memory figure, which ADR-0183 Boundaries leaves to the owner: (i) no: it applies to `intervals` and `resolution` and `memory_bytes` keeps its form (recommended); (ii) yes, with the form the owner states. **How far this reaches into OD-33 ⑥**: the answer settles the unit list there too, as one list, including how a value is added. A vendor target's memory figures (GPU, NPU) are answered only as far as the owner states a form under (ii). The rest of ⑥ (the record of given code, measuring points, new failure results) is not answered, and OD-33's wording is not edited.
- **O4, `owner-decision` (OD-32 ③, FR-9, #5 B-7, OD-31 ③).** ① The oracle and tolerance at `virtual_npu`: (a) the bf16 contracts' existing reference and the user's tolerance apply there, for this check backend only, with `instance.json` required as at `cpu_standin`, and this is no general answer to B-7 (recommended); (b) `virtual_npu` is not checked for correctness: only builds and timing below the start; (c) other. ② Whether the virtual NPU holds a type the CPU lacks: (a) no: the type subset of decision 4 is the difference (recommended); (b) yes: a new `dtype` value `int8` for one kind (`elementwise_add`) as one new contract-table entry, served by `virtual_npu` alone, its arithmetic stated by that entry's record, for the check only; (c) later, with the quantization answer.

**Coverage of OD-32's owner-attributed parts.**

| Part | State |
|---|---|
| ① record format and open list | O1 (scope), O2 |
| ② frame-changing part | O3; no other placement changes the frame (decision 3). The registry and real targets are not reached: OD-26 and #5 B-1 and B-2 stay open, and no P3 item needs them |
| ③ new numeric format; `ns`-other values, their list and whether it reaches the memory figure; the oracle outside `cpu_standin` | O4 ②; O3; O4 ①. fp16 is not asked again (D27 ④) |
| ④ inside the data plane | Not reached: decision 5 keeps it outside. It arises with OD-31 ⑧ |
| ⑥ who makes other candidates; the "C 커널" wording | O1 |
| ⑦ instance unit, artifact, quality metric, evaluation data, scenario | O1. For a model-level kind the content waits for its choice; the option to answer now is offered |

No question repeats one in `STATE.json` (D27 ⑦): HQ-0078 ⑤ deferred the unit list to this design, and HQ-0081, HQ-0083 and HQ-0085 are other subjects.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A candidate-kind abstraction in code now | One kind, nothing to tell apart; its form would anticipate O1 and O2 |
| 3 | Target values in a configuration file or in `hw_profile` `ext` | ADR-0116 decision 2 weighed both: no commit names a file's values, and a key member would be a frame change with no use that needs it |
| 3 | Move the constants out of `standin_settings.py` | Churn in accepted records' cited source, and no gain: the `Target` reads them |
| 4 | Make `virtual_npu` differ by a coarse clock now | It tests little beyond ADR-0103 and invents a difference the owner did not name |
| 4 | A memory limit through `memory_ceiling` | Not admitted (ADR-0053 decision 4), and that is a user's constraint, while this is a target's property |
| 5 | Edges between node ids, with a scheduler | A second order to keep bit-equal to `run_pass`; in-place reuse of buffers is then not expressible simply |
| 5 | Generate C per graph | A compiler step per model; an interpreter of a plan fits the existing library table and needs one program |
| 5 | Replace `model_forward.c` at once | It would change what P2-15 runs (criterion of D27) |
| 5 | Keep the graph in the data plane | No use needs it now; it would be an owner question with nothing to decide it on |
| 6 | Generate all six kinds | Rope and SDPA differ in structure; a generator with their cases would be harder to read than the two programs |
| 6 | Check generated C into the repository | Two statements of one fact, needing a test of the tool to keep them equal |

## Consequences

- **A-13 reading.** This record changes no frame. Decisions 3 to 6 change no member's form or meaning: the target table and the graph file are package source and an outside input, generation changes no output, `revision` `virtual-1` is a value of an existing string member, and `memory_bytes` keeps its definition though a bound limits its values (ADR-0052; ADR-0063 decision 6). **A value of an approved open list**: the design adds none. If a later task adds a contract entry under the design it uses the list "커널 계약 표" of DRIVER §3. `virtual_npu` is a new value of the *name* field `accelerator` and of the backend table, neither of which is a closed list or a data-format frame (ADR-0001 decision 1; ADR-0016 decision 2). **The frame changes are all in decision 9** (O2, O3), not made here.
- **Answers**: of OD-32 ②, the place of the target description and its links; of ③, the values other than O3's and O4's; of ④, the form and the place outside the data plane; of ⑤, the scope. Of OD-26, the `virtual_npu` entry and how the target values attach to the backend table, for a check backend only. Of OD-4, `virtual_npu`'s hw key values, among them what `revision` holds for it (ADR-0001 Boundaries; ADR-0035 closed that for `cpu_standin` alone), for this check backend only. Of OD-13 ⑦, the timing seed's source at `virtual_npu`, the rule of `cpu_standin` for this check backend only. Of OD-14 sub-question ①, for `virtual_npu` only, a resource bound (memory) and its call-level time limits; `cpu_standin` and the executor keep no bound. Of OD-31 ①, the six bf16 contracts served at `virtual_npu` unchanged, for this check backend only; the contract values do not change, so OD-6 ① is not answered further. OD-31 ③ is not answered: O4 ① asks it. ①, ⑥ and ⑦ are not answered. OD-32 stays open.
- **Runtime acceptance items**: none from this record. P3-3 and P3-4 register their own after landing (decisions 4 and 5).
- **Readings for the owner to check**, listed in the #5 notice: the target table in source, one set per `accelerator` (decision 3); the C kernel path's reading of the loop (decision 2); `s6_metric` left out of the lifted lists and `instance_start` as the place of the start's admission (decisions 1 and 3); `virtual_npu`'s values, its memory bound and `model_run` false (decision 4); the type subset as the data-type difference (decision 4); the graph file outside the data plane and beside the unchanged forward program (decision 5); four kinds generated, two handwritten, and fp32 `gemm` handwritten for its other form, not for difficulty (decision 6).
- **Less exact, not edited** (search of `ARCHITECTURE/decisions/` and `hilclaw/` for the terms of decision 1; not claimed complete). They become so when the item lands: ADR-0116 decision 2 ("one fixed set": per target from P3-2); ADR-0153 decision 1 ("First and only target") and ADR-0189 decision 1 once a second target gets `model_run`; ADR-0144 Q7, ADR-0052 and ADR-0182 decision 6 (no memory bound: still true of `cpu_standin`, not of `virtual_npu`); ADR-0076 decision 1 (two accelerators); ADR-0163 and ADR-0181 decision 2 (a program per kind in fixed source, for the four generated kinds); the `hilclaw/*_bf16_contract.py` docstrings ("on `cpu_standin`"), and the contract-table docstring's reading of coverage.
- **UsageCases and StandardScenarios** (S0, S1 and S12 re-checked): no use case step changes, and the notes already name OD-32 ①, ②, ④ and ⑦. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **All of decision 9**, with the conditions of `virtual_npu`'s instance start under O4 ①. Real target facts (#5 B-1, B-2, B-3), the Qualcomm reservation, OD-9, OD-26's registry.
- **fp16, gates, catalog entries for bf16, the S6 scale** (HQ-0083, HQ-0085, HQ-0081).
- **The artifact and scenario of the model goal** (OD-31 ⑧, ⑩), and a record of a model-level run.
- **The image for a real target and the compiler's place** (OD-14).
- **PLAN items after P3-6**: P3-7 to P3-13, FR-19, OD-33, DRIVER D29.

## References

- Owner: D27 and D29 in [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §6 and §11; HQ-0078, HQ-0081, HQ-0083, HQ-0085 in `PROCESS/STATE.json`; [Requirements](../Requirements.md) C-6, FR-9, FR-10, FR-14, FR-19, NFR-6, OD-4, OD-9, OD-26, OD-32, OD-33; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-32; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3 and the Qualcomm reservation.
- Records: ADR-0001, [ADR-0002](ADR-0002-od6-codegen-spec.md), ADR-0004, [ADR-0005](ADR-0005-od8-artifacts-record.md), ADR-0009, [ADR-0016](ADR-0016-od18-backend-frame.md), ADR-0017, [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md), [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md), ADR-0052, ADR-0053, ADR-0055, ADR-0060, ADR-0063, ADR-0076, [ADR-0100](ADR-0100-od8-tool-result-change.md), ADR-0103, [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md), ADR-0117, [ADR-0144](ADR-0144-od14-first-case-build-run-container.md), ADR-0145, [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0155, ADR-0163 to ADR-0165, [ADR-0166](ADR-0166-od31-bf16-forward-pass.md), ADR-0176, ADR-0177, ADR-0179, ADR-0180, ADR-0181, [ADR-0182](ADR-0182-od14-model-executor-container.md), [ADR-0183](ADR-0183-od18-tool-result-format-v2.md), ADR-0186, ADR-0188, [ADR-0189](ADR-0189-od31-binding-from-run-incumbents.md), [ADR-0190](ADR-0190-od22-catalog-read-by-contract-and-coder-every-shape.md), ADR-0191, [ADR-0192](ADR-0192-od31-model-check-command.md).
- Code read: the files named in decision 1; `hilclaw/backends.py`, `hilclaw/keys.py`, `hilclaw/contract_table.py`, `hilclaw/standin_profile.py`, `hilclaw/model_program.c`, `hilclaw/harness/bf16_verification.py`, `orchestration/`.
