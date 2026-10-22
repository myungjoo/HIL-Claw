---
id: T-0413
title: Add the four first-case technique catalog entries under catalog/cpu_standin/ and their reader hilclaw/catalog.py with its test file (ADR-0150 code slice 1; part of OD-22, FR-8; for PLAN P2-5)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-7, FR-8, OD-22, "PLAN P2-5"]
dependsOn: [T-0412]
touchesFiles: [catalog/cpu_standin/loop_order_ikj.md, catalog/cpu_standin/cache_blocking.md, catalog/cpu_standin/register_blocking.md, catalog/cpu_standin/simd_baseline_intrinsics.md, hilclaw/catalog.py, tests/test_catalog.py]
estimatedSize: {loc: 260, files: 5}   # non-test: four entry files (~30 lines each) and hilclaw/catalog.py (new, ~140 with docstrings); tests/test_catalog.py is excluded from the cap (D4)
hq: []
---
## Why

ADR-0150 landed on `main` as `ec3dc28` (T-0412). It decides the first technique catalog of the runs of ADR-0120 decision 1 (`cpu_standin` × `gemm` fp32 `row_major`, in C):
- a top-level directory `catalog/` of the code repository, with the stand-in's directory `catalog/cpu_standin/` and one `<id>.md` file per entry;
- the form of an entry: `# <id>`, `## Applies to` (four list lines), `## When`, `## Guidance`;
- an entry gives a spec exactly `{"id": <id>, "text": <Guidance section>}` (the `guidance.techniques[]` member of ADR-0002 decision 2);
- four first entries: `loop_order_ikj`, `cache_blocking`, `register_blocking`, `simd_baseline_intrinsics`. Their full texts are left to the code slice and are reviewed against decision 5.

ADR-0150 Consequences names **one code slice**: the four entry files and a reader module `hilclaw/catalog.py` with `tests/test_catalog.py`. This task is that slice. T-0412's Result names it as the next planner item.

**Priority (D18, DRIVER §6).** This is a follow-up of T-0412, not a PLAN checklist line, so the planner judged whether P2-5 needs it. It does: P2-5 covers S0 and S1, and S1 step 4 selects techniques "from the catalog" for rounds ≥ 1. ADR-0150 was written for those rounds, and without this slice the catalog it defines holds nothing a later record could give a spec. The selection side (HQ-0048, open) and round ≥ 1 spec composition (rest of OD-6) still decide who reads it; this slice does not depend on them, because the reader is not a registry tool and nothing calls it yet (ADR-0150 Consequences).

**No open HQ holds this slice.** HQ-0048 (selection side) and HQ-0034 (OpenMP) are open but bound nothing here: ADR-0150 decision 5 already excludes OpenMP and threads from the first set, and leaves the selection side to its own record. ADR-0150 names no runtime acceptance item.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED) touches `hilclaw/start_instance.py` and three test files only. `catalog/` does not exist yet on `main`.

**Mode.** Code mode: `catalog/` is not among the document-mode paths of CLAUDE.md A-13 (ADR-0150 decision 2, "an entry is added or changed in code mode").

**Test rule.** Rules ① to ④ of CLAUDE.md "테스트 규칙" apply to `hilclaw/catalog.py` (a layer-2 module; the CI job `Test presence (hilclaw)` requires its test file). The entry files are not modules. Rule ⑤ does not arise: nothing tested is a test, CI, hook or driver script (ADR-0150 Consequences).

**D16.** Nothing here starts `claude` or a container, needs a board or an API key. Tests use fixture directories under `tmp_path` and the committed `catalog/cpu_standin/`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0413-<slug>`, PR title containing `T-0413`, trailer `Task: T-0413`, `Task: T-0413` as the PR body's last line); the D4 size cap; code-task test rules ① to ⑤; the language line in `Result`.
- `CLAUDE.md`, 상시 규칙: "코멘트 최소화", "세 층 모델", "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ① to ⑤, "미결은 발명하지 않는다".
- `ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md`. The binding parts are:
  - Decision §1 to §5 (lines 44-104): scope; place and form of an entry file and of its `text`; the id rules; what an entry gives a spec and to which spec; the four first entries, the table of gists, why each keeps ADR-0008 and ADR-0116, and the **must / must not** rules for each `## Guidance` and `## When` text;
  - the Walk-through (lines 109-119);
  - Consequences slice 1 and "The cost, plainly" (lines 138-139 and 148);
  - Boundaries (lines 150-160): what this slice must not decide.
  Skim Status and Context (lines 3-43).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md` decisions 4, 6 and 7 (the prototype of `hilclaw_gemm`, every `m`, `k`, `n` ≥ 1, `c` written before read, no alignment beyond `float`, allowed headers). The guidance texts must keep them.
- `ARCHITECTURE/decisions/ADR-0116-*.md` decisions 2 and 3 (the fixed build set; no flag, define or library; the x86-64 baseline; explicit FMA allowed). Find the file with `ls ARCHITECTURE/decisions/ADR-0116-*`.
- `hilclaw/turn_definition.py` lines 1-200. It is the model for a module that reads a top-level directory of this repository from outside the package (`SOURCE = Path(__file__).resolve().parent.parent / "orchestration"`), takes `str` or path objects, and refuses symbolic links and junctions (`_kind`, `_JUNCTION_TAG`). You may copy the pattern; do not import its private names.
- `hilclaw/keys.py` lines 1-60 (the *name* form `[a-z][a-z0-9_]{0,31}` of ADR-0001 decision 1).
- `hilclaw/spec.py` lines 60-130 and 265-269 (`validate`, `InvalidSpecError`, `_technique`, `_string`, `_text`): an entry's `{id, text}` must be a valid `guidance.techniques[]` member. Read only.
- `examples/spec/gemm-485b9bc494d477eb.json` (a valid spec; its `guidance.techniques` is empty). Read only.
- `tests/test_turn_definition.py` lines 1-80 (fixtures, the symbolic-link skip pattern). Copy what you need; do not import from another test module.
- `.github/workflows/ci.yml` job `Test presence (hilclaw)` (line 118) and the coverage job (line 148). Read only.

## Acceptance Criteria

### The four entry files (ADR-0150 decisions 2, 3 and 5)
1. Create exactly `catalog/cpu_standin/loop_order_ikj.md`, `cache_blocking.md`, `register_blocking.md` and `simd_baseline_intrinsics.md`. Nothing else goes under `catalog/` (no README, no index).
2. Each file is UTF-8 with LF line ends and has, in this order and with no other heading of level 1 or 2:
   - the line `# <id>`, equal to the file name without `.md`;
   - `## Applies to` with exactly the four list lines `- kind: gemm`, `- dtype: fp32`, `- layout: row_major`, `- language: c`;
   - `## When`: the selection criteria, prose;
   - `## Guidance`: the application guidance, prose, the last section.
3. Each `## Guidance` text keeps every **must** and **must not** of ADR-0150 decision 5. In short:
   - it says what to change in the kernel and how; where the technique touches them, the remainders of every `m`, `k`, `n` ≥ 1, `c` set before it is read, and no alignment beyond `float`;
   - for `simd_baseline_intrinsics`: the `#if defined(__x86_64__)` path (SSE/SSE2 intrinsics from `<immintrin.h>`), the `#elif defined(__aarch64__)` path (Advanced SIMD from `<arm_neon.h>`), the scalar path for other processors and for remainders, and unaligned loads and stores (`_mm_loadu_ps`, `vld1q_f32`); no function attribute, no AVX/AVX2/AVX-512/SVE;
   - it is in English and complete without any other file, entry or link;
   - it claims no measured speed-up, measured or tuned value or ranking (a block or tile size only as a value to start from, so marked);
   - it asks for no compiler flag, define, library or `task.build` member; it does not offer OpenMP, threads or a feature beyond the baseline as something to use;
   - it holds no verification input, seed or expected value, and copies or names no external code or material (nntrainer among them).
4. Each `## When` text states, in terms of the op_signature's shape and of what an earlier attempt shows, when the technique is worth trying, and claims no measured effect.
5. The texts contain no C code longer than a short illustrative fragment; the guidance describes the change rather than handing a finished kernel (this planner's reading of "say what to change in the kernel and how"; record it in `Result` for the reviewer).

### `hilclaw/catalog.py` (new; ADR-0150 decision 2 and Consequences slice 1)
6. **Not a registry tool.** The module is added to no registry, no MCP front and no `orchestration/` file. It calls no model, starts no process and writes nothing.
7. **Source.** A public constant names the default catalog root `Path(__file__).resolve().parent.parent / "catalog"`, as `turn_definition.SOURCE` does. Public functions take an optional keyword `source` (a `str` or path object; `None`: the constant) so tests can use fixture directories.
8. **The check of an accelerator's directory.** A public function reads `<source>/<accelerator>/` and checks the form of decision 2, refusing with one module exception (a subclass of `ValueError`, suggested) when:
   - `accelerator` is not exactly a `str` matching the *name* form (`TypeError` for a non-`str` is acceptable; record the choice);
   - the directory does not exist (`FileNotFoundError`, suggested) or is not a directory;
   - the directory holds a symbolic link, a junction, a subdirectory, or any file whose name is not `<name>.md` with `<name>` of the *name* form;
   - a file is not strict UTF-8, holds a BOM (suggested; record), or holds a `\r`;
   - the first line is not `# <id>` with `<id>` equal to the file name stem;
   - the level-1/level-2 headings are not exactly `# <id>`, `## Applies to`, `## When`, `## Guidance` in that order (a `###` heading inside a section is allowed);
   - `## Applies to` does not hold exactly the four lines of criterion 2 (blank lines around them allowed; record the choice);
   - `## When` is empty after stripping (suggested; record), or the `text` is empty.

   The `text` is the content of `## Guidance` from the line after the heading to the end of the file, with leading and trailing line feeds removed and nothing else changed (decision 2).
9. **What an entry gives.** A public function returns, for an accelerator and an id, exactly `{"id": <id>, "text": <text>}` (a new `dict` with those two keys, `str` values) after the whole directory passed the check of criterion 8. An id that is not of the *name* form, or names no entry, is refused (a `LookupError`/`KeyError` for a well-formed unknown id, suggested; record). It does not check the rule of decision 4 against a spec (that is the composition's, Boundaries); it does not return `## Applies to` or `## When` in that dict. A further public function or return value that exposes the applies-to values and the `When` text for the selection side is allowed but not required; if added, it must not be wired to anything.
10. **Docstrings** follow the style of `hilclaw/turn_definition.py`: a module docstring that says what ADR-0150 decided and what is only applied, the choices of this module, and that nothing calls it yet (HQ-0048; rest of OD-6). Public functions get Doxygen-like docstrings. No multi-line comments.

### Tests (test rules ① to ④; the file is excluded from the size cap)
11. `tests/test_catalog.py` (new):
    - **Committed catalog**: the committed `catalog/cpu_standin/` passes the check; it holds exactly the four ids of criterion 1; `catalog/` holds only `cpu_standin/`; for each id, the returned `{id, text}` placed into a copy of `examples/spec/gemm-485b9bc494d477eb.json`'s `guidance.techniques` passes `hilclaw.spec.validate`; for `simd_baseline_intrinsics`, the text contains `__x86_64__`, `__aarch64__`, `_mm_loadu_ps` and `vld1q_f32`; no text contains `omp`, `pthread`, `-f`/`-D` flags, `__attribute__`, `avx` (case-insensitive) or `nntrainer` (adjust the word list if a legitimate sentence trips it, and say why in `Result`).
    - **Happy cases** on fixture directories: one and several valid entries; a `###` heading inside `## Guidance` kept in `text`; leading and trailing line feeds of the section removed and inner text unchanged.
    - **Error, branch and negative cases**: one fixture per refusal of criterion 8 and of criterion 9 (non-name accelerator, non-`str` accelerator, missing directory, a file where a directory is expected, a subdirectory, an extra non-`.md` file, an upper-case or over-long file name, a symbolic link (skip with a reason where the platform cannot make one), non-UTF-8 bytes, a BOM, a `\r`, wrong first line, id differing from the stem, missing/reordered/extra level-2 sections, an extra level-1 heading, wrong or extra `Applies to` lines, an empty `When`, an empty `Guidance`, an unknown id, a non-name id).
12. Package coverage stays ≥ 80 % lines and ≥ 80 % functions (rule ①). Record both figures of the final head from the coverage job. Every public function of the new module has tests (rule ③), and the module has its test file (rule ④). Rule ⑤: add no test of a test helper, CI workflow or script.
13. Python, standard library only: no new dependency (A-13). Record the language line in `Result` (DRIVER §5). Tests pass on Linux (CI) and on Windows (the driver's clone); path handling must not assume POSIX separators.

### Process checks
14. Before each commit and before the merge, run from the repository root and make sure each exits 0: `python -m pytest`, `python -m ruff check .` and `python -m ruff format --check .`. Record the pytest pass and skip counts on `origin/main` and on the final head. Install nothing.
15. Check the diff against `origin/main`:
    - `git diff origin/main --stat` lists only files from `touchesFiles`, plus this task file's `Result` if the executor prompt has it written on the branch;
    - `git diff origin/main -- .claude .github orchestration ARCHITECTURE pyproject.toml` is empty;
    - `git ls-files --eol` shows `i/lf` for the new files.

    Record the non-test diff line count (cap: 300 LOC, 5 non-test files — the four entries and the module). If it is exceeded, finish the module with its fixture tests first and propose the entries (with the committed-catalog test) as a split in `Follow-ups` (ADR-0150 Consequences; DRIVER §5).
16. Open a Draft PR and run the reviewer cycle with a fresh-context `dev-reviewer` running dev-code-review, for at most 7 rounds. Ask the reviewer explicitly to:
    - (a) check every `## Guidance` and `## When` text against each **must** and **must not** of ADR-0150 decision 5, and against ADR-0008 decisions 4, 6 and 7 and ADR-0116 decisions 2 and 3, on Linux, macOS and WSL, x86-64 and arm64;
    - (b) find an entry file that the check accepts but decision 2 forbids, or the reverse;
    - (c) confirm the returned `text` is exactly the `## Guidance` content with only leading and trailing line feeds removed;
    - (d) confirm the module is wired to no registry, front, prompt or setting, and decides nothing ADR-0150 Boundaries leaves open (selection, round ≥ 1 composition, statistics, provenance);
    - (e) re-check the test-rule reading in Why and each provisional choice recorded in `Result`.

    A finding that starts with `SECURITY` is BLOCKED. After the review, get CI green on the final head with `gh pr checks <PR> --watch`, and record the check names and the run URL. Then squash-merge with `gh pr merge --squash --body`, using the PR body whose last line is `Task: T-0413`, and delete the branch.

## Out of Scope

- Any selection-side code, `Skill`, sub-agent or prompt that reads the catalog (HQ-0048; OD-23; FR-8 "트리거"); any change to `orchestration/`.
- Round ≥ 1 spec composition, `spec.write` changes, or a check of decision 4's rule when a spec is composed (rest of OD-6; PLAN P2-1).
- Statistics, ranking, `technique_stats.json`, entry criteria, curation flow, cold-start methods (OD-7, OD-22 rest, UC-5).
- OpenMP, threads, AVX/AVX2 paths, packing of `b`, any further entry (ADR-0150 decision 5 "Weighed and not in the first set"; HQ-0034).
- Catalogs for the mock or any other accelerator, kind, dtype, layout or language.
- Any edit of `ARCHITECTURE/` (including ADR-0150's title wording, a held follow-up), `PROCESS/` other than this task's `Result`, `.claude/`, `.github/`, `pyproject.toml`, settings files or the `HIL-Claw-data` repository; any new dependency.

## Follow-ups

- (executor fills)

## Result

- (executor fills)
