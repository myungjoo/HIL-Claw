# ADR-0003: Three-state calibration as the acceptance criterion of the verification harness (P1 minimum of OD-16)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes the **P1 minimum** of OD-16 (Open Decisions register in [Requirements](../Requirements.md)): when the verification harness of FR-9 counts as done. Everything else of OD-16 — which defences beyond the minimum clause of FR-9 are adopted — stays open (see Boundaries), and the register row keeps its status.
- It uses the `kind` of ADR-0001 and the fact that a spec exposes the shape of its op_signature (ADR-0002). The objection windows of both records run until 2026-10-13; if either is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- FR-9 makes correctness a hard floor and gives the MVP one robustness clause: a result is re-verified on inputs (shape / seed) that were not exposed to the coder, in an isolated verification harness the coder cannot modify; a result that fails enters neither best nor the statistics. Nothing says when that harness itself is done.
- Confirmed part of OD-16 (#5 A-12): the harness — input generation, reference, tolerance comparison, timing, profile, eval / event recording — is one sub-module of the tool package, outside the coder's scratch.
- Principle of OD-16 (2026-07-31 revision; owner premises in #4): unforgeability, not concealment. Reads are not restricted; a defence must hold when everything is read; only the seeds and input values of a run do not exist as files. Hard-coding is stopped in the measurement layer.
- Survey item #7 S-2 N8 proposes to adopt the *three-state calibration* of Kernel Contracts (arXiv 2604.22032) as the completion condition of the harness. As #7 summarises it, a contract is presented together with one conforming implementation and one implementation that passes the functional test but violates the contract, which proves that the contract catches the violation. This record relies on that summary; the paper was not read for it.
- The proposal was absorbed into OD-16 as "adoption under consideration" ([OpenDecisionProposals OD-16](../OpenDecisionProposals.md#od-16), bullet "하네스 자체의 수용 기준"). PLAN P1-4 names three kernels — passing, failing, "functional pass, contract violation" — and waits for this closure.
- [ADR-0002](ADR-0002-od6-codegen-spec.md): a spec carries no seed, no verification input and no expected value. It does carry the shape of its op_signature.
- Not available as inputs, and not needed below: the reference oracle of `cpu_standin` (#5 A-7, recommendation awaiting the owner) and the tolerance vocabulary (#5 B-7).

## Decision

### 1. Adoption and unit

- Three-state calibration **is adopted as an acceptance criterion of the verification harness**: for an operation kind, the harness is not done until its tests show the three outcomes of decision 4 on the kernels of decisions 2 and 3.
- The unit is the **operation kind** the harness can verify (`kind` of the op_signature, ADR-0001; the first is `gemm`), and within a kind every required violation class (decision 3). The harness is done for a kind, never "as a whole".
- The shapes at which a kind is calibrated are the choice of the tests; any shape of the kind will do. Whether calibration is repeated for each `dtype` and `layout` of a kind is not decided here (Boundaries).

### 2. The three states

Two words first, both taken from FR-9 and S7 steps 1-2:

- **The functional test** is the basic check of S7 step 1: the kernel's outputs agree with expected outputs within a tolerance on **inputs fixed in advance**, that is, inputs the author of a kernel can know. In this record it is run by the calibration tests; the record neither makes it a step of a round nor excludes one. Calibration does not require the harness to have a fixed-input mode; whether it has one is the harness design (P1-3).
- **The contract** is the obligation of the FR-9 clause: the kernel computes the operation of its op_signature within the tolerance on **inputs it could not know**, those a verification run of the harness draws.

| State | The kernel | Functional test | Contract |
|---|---|---|---|
| **Conforming** | computes the operation | passes | holds |
| **Failing** | computes something else on every input | fails | violated |
| **Violating** | is right on the fixed inputs of the functional test and wrong elsewhere | **passes** | violated |

- The third state is what separates the harness from a weaker check, so the calibration tests **show both halves**: the violating kernel passes the functional test, and the harness rejects it. Without the first half the third state is a second failing kernel.
- The conforming kernel shows that the harness does not reject everything, the failing one that it does not accept everything.

### 3. Violation classes required in P1

One class is required: **V1, output that is right only on inputs known in advance** (threat B ⑴). The FR-9 words that oblige the harness to catch it are "코더에 노출되지 않은 입력(shape/seed)으로 … 재검증". A kind therefore has at least three kernels, the three of PLAN P1-4.

| Class of the OD-16 proposal | Required in P1 | Reason |
|---|---|---|
| B ⑴ hard-coded output | **yes (V1)** | Caught by inputs drawn at run time, which is the FR-9 minimum clause. |
| B ⑵ omitted computation | no separate kernel | Where the omission shows as a wrong output on drawn inputs it is the failing or the violating state already. The strengthened oracle of the proposal (fuzzing, corner cases, per-(op, dtype) tolerance) is not adopted. |
| B ⑶ dispatch to a vendor library | no | Its output is correct. Static checks and profiler confirmation are not adopted. |
| B ⑷ evasion to another queue or thread, B ⑸ caching in the timing loop | no | They forge the timing, not the output. Barrier, wall-clock cross-check, roofline bound, reallocation, cache flush and drop detection are not adopted (rest of OD-16, OD-13). |
| B ⑹ order dependence | no | The order-dependence test is not adopted. |
| A: buffer theft, harness or timer patching, score or log tampering | no | Removed by process separation and write isolation, which are OD-8 and OD-14 and open. That the coder cannot modify the harness is a property of where it lives, not a verdict on a kernel. |
| S7 / B1: precision downgrade | no | A lower-precision kernel outside the tolerance is the failing state; inside it FR-9 admits it. A separate precision check is not adopted. |
| S7 / B1 / B8: timing hardening, static checks and forbidden patterns, LLM verifier, script protection, forbidden fallbacks, web search block | no | Extensions (S7), not adopted; B8 is registered under NFR-4, OD-16 and OD-12. |
| Early-stop re-verification (FR-3 ④) | no kernel | A rule on when verification runs again, not a kind of kernel. |

"Not adopted" states the present status of a registered proposal. This record adopts none of these defences and rejects none.

### 4. What "caught" means

- A verification run ends in a correctness verdict, **pass** or **fail** (FR-9: a floor, not a score). Expected: conforming → pass; failing → fail; violating → fail.
- Calibration asserts **the verdict only**. It does not require the harness to name the cause of a rejection or to tell the failing from the violating state; the tests tell them apart through the functional test. Failure-type tagging is S7 step 3 and stays an extension.
- Only the correctness verdict counts. The calibration kernels build and run to completion, so a rejection for another reason (build error, crash, timeout) does not show that a violation was caught.
- The expected verdicts must **not depend on a draw that suits a kernel**. The kernels are written without knowledge of the drawn values, and a calibration test does not select inputs so that a kernel fits them. A draw on which a wrong output happens to agree with the operation (all-zero inputs, for example) is a negligible exception, not a guarantee of this record. How a test is made reproducible, including whether a seed can be supplied, is the harness API (P1-3) and the code task.

### 5. Nature and place of the calibration kernels

- They are **test data of the harness's tests**: written by hand, small, deliberately unoptimised, in the kernel language of the backend the harness verifies — C for `cpu_standin` (#5 A-7 ②), a language of the layer-2 set.
- They are **not coder output**, not catalog entries, not references (FR-15) and not baselines (OD-28). They live with the tests in the source repository, never enter the data plane, the catalog or a spec, and no tool hands them to a coder. Nothing depends on hiding them: the violating kernel documents what is caught.
- Reading against CLAUDE.md test rule ⑤, which this record does not change: the verification harness is layer-2 product code (FR-10 package), not the repository's test tooling, so its calibration tests are ordinary product tests under rules ①-④; the failing and violating states are their negative cases. Showing that the violating kernel passes the functional test is a precondition asserted inside a harness test. No test is added whose target is a kernel fixture or a test helper.

### 6. When the criterion must hold

- The calibration tests are **part of the ordinary test suite** of the tool package. They are run whenever that suite is run, so every change of the harness is checked against them.
- The calibration set is extended **in the same change** that (a) makes the harness able to verify a new operation kind — its three kernels — or (b) implements a defence that a later record adopts and that changes the correctness verdict — the violating kernel of the class it catches — or (c) makes a verification run draw shapes other than those of the op_signature (Boundaries) — a kernel that is right only at known shapes.
- A skipped calibration test is no evidence. Calibration is a candidate content of the C gate of PLAN P0.5-1 ("clang build + harness pass"); the workflow is designed there.
- Calibration is a criterion on the development of the harness. It is not run per Loop instance or per round. How a run is tied to the evidence for the harness version it pins is OD-11.

### 7. Independence from the oracle and the tolerance

- The criterion is stated for **any** reference oracle and **any** tolerance under which the conforming kernel passes and the wrong outputs of the other two kernels lie outside the tolerance. Those kernels are built to make this easy: their wrong outputs do not depend on the inputs the way the operation does, so they are far from every oracle of the operation.
- A calibration test **passes its tolerance explicitly**, as an instance does (FR-9), and uses it for the functional test as well. It never relies on a default of the harness, and this record names no value and no vocabulary.
- Where the functional test takes its expected outputs from (the harness's reference, or constants in the test) is left to the code task; either holds for any oracle.

### 8. Limits

- Passing calibration shows that the listed violations **are caught on the kernels written for them**. It does not show that no loophole exists, and it says nothing about the classes decision 3 does not require, about timing, or about properties that are not a verdict on a kernel: that drawn values differ from run to run and exist in no file, and that the coder cannot modify the harness.
- The hacker-fixer loop (#7 body §7) is the complement: it searches for unknown loopholes, calibration keeps known ones closed. Whether it is run stays open.
- The strength of the adversarial re-verification before promotion stays open; calibration is about a single verification run being right.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | No acceptance criterion; the harness is done when its own unit tests pass | Tests of the parts do not show that a kernel which games a fixed check is rejected, and a loophole in the harness pollutes best and the statistics silently (FR-9, OD-16). |
| 1 | One calibration for the harness as a whole | Input generation and the reference differ per kind; a calibrated `gemm` says nothing about the next kind. |
| 1 | One calibration per rule the harness enforces | Beyond the minimum clause no rule is adopted, and the unit would follow the internal design of the harness (P1-3). |
| 2 | "The functional test" = a fixed-input mode of the harness | No source gives the harness such a mode, and the criterion must not depend on one. |
| 2 | Two states only (conforming, failing) | Shows that the comparison works, not that inputs drawn at run time add anything over a fixed check — the very point of the FR-9 clause. |
| 3 | A violating kernel for every class of the proposal | Needs defences that are extensions or open ODs; it would pull them into the MVP. |
| 4 | The harness must report the kind of violation | That is failure-type tagging (S7 step 3), an extension. |
| 4 | Inputs chosen by the test to fit the kernels | The test would calibrate a path with known inputs, not the one a verification run takes. |
| 5 | Violating kernels produced by a coder, or kept as catalog entries | Coder output is not reproducible, and a catalog entry is something to apply (FR-8). |
| 6 | Calibration at the start of every run | A run uses a fixed tool set (FR-10); the harness version is pinned by the source commit (OD-11), whose suite contains the calibration. |
| 7 | A default tolerance for calibration | Defaults are #5 B-7; a test parameter needs none. |

## Consequences

- The P1-4 code task writes, for `gemm`, three C kernels and tests that assert: conforming → functional test passes, harness passes; failing → harness fails; violating → functional test passes, harness fails; all with a tolerance passed by the test.
- The harness is not accepted for a kind until the P1-4 tests exist. This does not change the PLAN items: P1-3 lands first, and P1-4 depends on the verification entry of the harness, its verdict and the kernel prototype, all of which P1-3 defines.
- The required set is small on purpose: one class. Each defence that is adopted later and changes the correctness verdict grows it by one kernel per kind (decision 6).
- The fixtures are readable by anyone who reads the repository, including a coder; this is intended (Context, principle of OD-16).

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: the reference oracle of `cpu_standin` (NumPy float64 is the #5 A-7 recommendation, awaiting the owner; possibly a new external dependency, CLAUDE.md A-13); the tolerance vocabulary and default values (#5 B-7, rest of OD-5); datasets (#5 B-8); OD-3, including any escalation gate of S7 step 5; OD-25; C-6; whether the coder may search the web (OD-12, B8).
- **The design of the harness (PLAN P1-3)**: its API, the kernel calling convention and prototype (ADR-0002 `task.contract` carries the values and does not define them), how many inputs a verification run draws, seed derivation, the layout and operand order of the first GEMM, and its outcomes other than the correctness verdict.
- **Sub-questions this record raises** (registered under OD-16): whether a verification run also draws shapes other than those of the op_signature — FR-9 says "shape/seed", while a spec exposes the op_signature shape (ADR-0002); if it does, V1 needs a kernel that is right only at known shapes. Whether calibration is repeated per `dtype` and `layout` of a kind, per backend or execution point (sim, board) and per kernel language. Whether the measurement side (timing) gets a calibration of its own (with OD-13). How a run is tied to the calibration evidence of the harness version it pins (OD-11).
- **Rest of OD-16**: static checks and forbidden patterns, precision-downgrade checks, the roofline bound and its model, the order-dependence test, per-trial reallocation, cache flush and detection of timing caching, profiler confirmation of execution, the LLM verifier, hacker-fixer pre-hardening, the strength of the adversarial re-verification before promotion, the definition of `private_metrics` (with OD-20). They stay registered proposals.
- **OD-13** (measurement and noise), **OD-14 / NFR-4** and **OD-8** (process separation, write isolation, layout — threat A), **OD-11** (measurement-contract pin, re-measurement), **OD-15** (promotion), **OD-18** (hooks), **OD-23** and PLAN P2-3 (the evaluator agent and its contract; P2-3 has its own OD-16 closure).
- Code, tests, fixtures, directory names, CI workflows and schema files: later code tasks (PLAN P1-3, P1-4, P0.5-1).

## References

- [Requirements](../Requirements.md): FR-3 ④, FR-8, FR-9, FR-10, FR-15, NFR-4; register rows OD-5, OD-8, OD-11, OD-12, OD-13, OD-14, OD-15, OD-16, OD-18, OD-20, OD-23, OD-28.
- [OpenDecisionProposals OD-16](../OpenDecisionProposals.md#od-16) (registered proposal: principle, threats A and B ⑴-⑹, extensions, "하네스 자체의 수용 기준"); [StandardScenarios](../StandardScenarios.md) S7 steps 1-3, S8 step 3; [UsageCases](../UsageCases.md) glossary "검증 하네스", UC-E1.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format, `kind`); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 2 "No field carries verification inputs", `task.contract`).
- #7 S-2 https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5566900982 (survey row "Kernel Contracts", item N8, "기각/보류한 아이디어"); #7 body §5 G1, §7. Kernel Contracts (arXiv 2604.22032) is cited through #7 only.
- #4 https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 (owner premises: reads are not restricted; hard-coding is stopped in the measurement layer).
- #5 A-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items B-7, B-8.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P0.5-1, P1-3, P1-4, P2-3; CLAUDE.md (three-layer model, language policy, test rule ⑤); task T-0020.
