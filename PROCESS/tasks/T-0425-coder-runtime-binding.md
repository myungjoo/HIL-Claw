---
id: T-0425
title: Bind coder.run of hilclaw.tools.default_registry to coder_runtime.DockerRuntime in place of NoContainerRuntime, and have hilclaw/turn_loop.py put a non-empty HILCLAW_CODER_IMAGE and the reference ${HILCLAW_CODER_OAUTH_TOKEN} (never the value) into the server entry's env, updating the docstrings that call the runtime "slice (d)'s" (ADR-0137 code slice 2; for PLAN P2-2)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-5, NFR-4, C-7, OD-23, OD-8, "PLAN P2-2"]
dependsOn: [T-0424]
touchesFiles: [hilclaw/tools.py, hilclaw/turn_loop.py, hilclaw/coder_tool.py, hilclaw/coder_call.py, hilclaw/coder_runtime.py, tests/test_coder_tool.py, tests/test_turn_loop.py, tests/test_mcp_front.py, tests/test_tools.py, tests/test___main__.py, tests/test_default_registry_schemas.py, tests/test_coder_runtime.py, tests/conftest.py]
estimatedSize: {loc: 110, files: 5}
hq: []
---
## Why

**Where things stand** (as of `main` `0df8979`):
- PLAN P2 runs in list order (D18): the round loop (P2-1 to P2-4, P2-6, P2-7), then the first run P2-5 (the near goal), then P2-10, then the Llama items P2-11 to P2-14.
- PLAN P2-2 (coder-driver): ADR-0137 (`a1e5c3f`) fixed how the coder's container and `claude -p` are started. Its Consequences name two code slices. T-0424 landed slice 1 (`04ff59f`): `hilclaw/coder_runtime.py` with `DockerRuntime`, bound to nothing.
- **This task is slice 2.** Until it lands, `hilclaw.tools.default_registry` binds `coder.run` to `hilclaw.coder_tool.NoContainerRuntime`. So every coder call of a real run ends with `no_container_runtime`, and P2-5 cannot bring in a kernel on any machine.
- The runtime acceptance items of ADR-0137, (lxix) to (lxxiv), are already recorded as HQ-0068. (lxxiv) is the one about this slice: that the session expands the reference in the `--mcp-config` file. This task closes none of them.

**D18 reading.** This is work of a PLAN checklist item (P2-2, the code of ADR-0137). The D18 hold rule does not apply (DRIVER §6). The docstring updates are part of slice 2 by ADR-0137 Consequences ("the docstrings that call the runtime 'slice (d)'s' are updated with it"). They are not a separate wording clean-up.

**D16.** This task and its tests start no `docker`, no `claude`, and need no token. Binding `DockerRuntime` in the default registry means that a test which reaches the default registry's `coder.run` past the checks before `no_container_runtime` would now run `docker version`. Linux CI runners have Docker installed. Every such test must therefore replace the runtime's process starts (criterion 4). The existing turn-loop tests start only a stub `claude` that the tests write.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md`:
  - Context "Facts of the code" (lines 64-70);
  - decision 4, "How the runtime is told" (lines 119-124);
  - decision 5, the whole section (lines 126-139), in particular "How it reaches the process that runs the function";
  - Consequences, code slice 2 and item (lxxiv) (lines 211-220), and the "Less exact, not edited" bullet on the three code docstrings (line 227).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md` decision 3 (lines 53-58).
- `hilclaw/coder_runtime.py`: the module docstring (lines 1-80 or to its end), `DockerRuntime.__init__` and `available`. Slice 1 is not changed except its docstring sentence "Nothing binds it yet" (lines 7-10).
- `hilclaw/tools.py` lines 200-266 (`default_registry`, its docstring and the binding).
- `hilclaw/coder_tool.py` lines 1-27 (module docstring) and 73-88 (`NoContainerRuntime`).
- `hilclaw/coder_call.py` lines 1-56 (module docstring) and 303-325 (`_run_and_bring_in`).
- `hilclaw/turn_loop.py` lines 107-118 (the docstring bullet "The data root and the image reach the server through the environment"), 309-320 (`_config_text`) and 447-505 (`run`, which builds the configuration once per loop).
- `tests/test_turn_loop.py` lines 370-460: the configuration and image tests, which are the pattern for the new ones.
- `tests/test_coder_tool.py` lines 255-295 and 440-465: the tests of the package runtime and the default registry.

## Acceptance Criteria

1. **The binding** (`hilclaw/tools.py`).
   - `default_registry` registers `coder.run` with `coder_tool.definition(data_root_source, coder_runtime.DockerRuntime())`. The runtime is constructed with its defaults: `environ=None`, so it reads `os.environ` at each call, and `client="docker"`.
   - No option, environment variable, argument or entry point chooses the runtime. `default_registry` keeps its signature (ADR-0141 decision 3).
   - Building the registry starts no process. `DockerRuntime()` construction reads nothing, and nothing is called at build time.
   - The `default_registry` docstring says that `coder.run` is bound to `hilclaw.coder_runtime.DockerRuntime` (ADR-0137). It drops "until slice (d) replaces that binding". It states what a call now does when no runtime answers (`no_container_runtime`) or when the image or token is missing (`coder_not_started`), by citing the kinds and not restating ADR-0137.
2. **`NoContainerRuntime` stays** in `hilclaw/coder_tool.py`, with the same behaviour, as a runtime that starts nothing. It is no longer the package's binding. Its class docstring and the module docstring's "Decision 3" paragraph say so: ADR-0141 decision 3 held while slice (d) was absent, and ADR-0137 slice 2 replaced the binding. No other code change in `coder_tool.py`.
3. **The turn loop** (`hilclaw/turn_loop.py`, `_config_text` and the docstring bullet at lines 107-118).
   - **Image.** When the calling process's environment holds `HILCLAW_CODER_IMAGE` (`coder_runtime.ENV_IMAGE`) with a non-empty value, the server entry's `env` holds that variable with that value unchanged and unchecked, as it does for `HILCLAW_STANDIN_IMAGE`. The front's `DockerRuntime` refuses a bad one.
   - **Token reference.** When the calling process's environment holds `HILCLAW_CODER_OAUTH_TOKEN` (`coder_runtime.ENV_TOKEN`) with a non-empty value, the entry's `env` holds the member `HILCLAW_CODER_OAUTH_TOKEN` with the exact text `${HILCLAW_CODER_OAUTH_TOKEN}`. **The value is never written** to the configuration file, any other file, any argument or any exception text.
   - Unset or empty: the member is absent (each variable on its own).
   - Both are read once, when `run` builds the configuration, as the stand-in image is today. Every turn of one loop has the same entry.
   - **Nothing else** of the environment is copied. In particular `CLAUDE_CODE_OAUTH_TOKEN` is not copied, and neither are `DOCKER_HOST`/`DOCKER_CONTEXT` or any other variable.
   - The turn session's own environment is unchanged by this task. It still gets the calling process's environment with only the three changes of ADR-0141 decision 4. It therefore holds `HILCLAW_CODER_OAUTH_TOKEN` and can expand the reference (ADR-0137 decision 5; runtime acceptance item (lxxiv), not verified here).
   - The docstring bullet names the two new members and ADR-0137 decisions 4 and 5. It keeps "Nothing else of the environment is copied there" true. It states that the reference relies on the session expanding `${...}` in the `--mcp-config` file, which is (lxxiv) and not verified.
   - The data-root placeholder check (`_PLACEHOLDERS`) is not changed. The reference written into the configuration is not a hook-settings placeholder.
4. **Docstrings of the seam.** These sentences are rewritten so that they are true of the code after this task:
   - `hilclaw/coder_call.py` module docstring: "How it reaches that process is slice (d)'s"; "the package's runtime (`NoContainerRuntime`) … until slice (d) replaces it"; "the prompt is slice (d)'s and `runtime.run` takes none yet"; "What this module is not: slice (d), the real runtime with its image, flags and prompt".
   - The seam description "returns the exit status of the coder process". It now also covers the fixed non-zero status `coder_runtime.NOT_GONE_STATUS` that `DockerRuntime.run` returns when the container cannot be shown gone (ADR-0137 decision 7).
   - `hilclaw/coder_runtime.py` module docstring: "Nothing binds it yet …" becomes the fact of the binding.
   - The rewrites cite ADR-0137 and do not restate its decisions.
   - No behaviour of `coder_call.py` or `coder_runtime.py` changes, and no public name is added, renamed or removed there.
5. **Tests.** No real `docker`, no real `claude`, no network, and no token is needed. The tests cover:
   - **binding, happy**: the default registry's `coder.run` reaches a `DockerRuntime`. One way: monkeypatch `hilclaw.coder_runtime.shutil.which` (or the start functions as seen from `hilclaw.coder_runtime`) with a recorder, call `coder.run` through `tools.default_registry` with a request that passes the checks before `no_container_runtime`, and assert that the version check of the configured client was requested. Then assert the kind when it answers false (`no_container_runtime`). With `available()` made true and `HILCLAW_CODER_IMAGE` unset, assert the kind `coder_not_started` and that no `docker run` was started.
   - **no real process**: every existing test that calls `coder.run` of `tools.default_registry` (or of the MCP front or command-line front over it) past the checks before `no_container_runtime` is updated so that no `docker` process can start. Examples: `tests/test_coder_tool.py` "the default registry gives no container runtime" and "the mcp front lists and calls coder_run of the default registry". Search `tests/` for `default_registry` and `coder_run`/`coder.run` to find all of them. The executor states in Result how it made sure no test starts `docker`. A suite-wide autouse guard in `tests/conftest.py` is acceptable if it does not hide the runtime's own tests in `tests/test_coder_runtime.py`.
   - **building the registry** starts no process (recorder sees no call).
   - **turn loop, image**: forwarded unchanged and unchecked (including a value like `--privileged`); absent when unset or empty; read once per loop. Follow the pattern of the existing stand-in image tests.
   - **turn loop, token**: with a sentinel value set, the entry's `env` member is exactly `${HILCLAW_CODER_OAUTH_TOKEN}`. The sentinel appears nowhere in the written configuration text, in the hook settings text, or in the stub `claude`'s arguments. The member is absent when unset or empty. It is read once per loop.
   - **turn loop, nothing else**: with `CLAUDE_CODE_OAUTH_TOKEN`, `DOCKER_HOST` and an unrelated variable set, none reaches the entry's `env`.
   - **turn loop, all three together**: the entry's `env` is exactly data root, stand-in image, coder image and token reference.
   - Existing configuration tests that assert the exact `env` remove both new variables from their environment first, so they stay independent of the machine's environment.
   - **negative**: tests that the default registry still refuses a non-callable data-root source; a turn-loop configuration with the token variable set to the literal text `${HILCLAW_CODER_OAUTH_TOKEN}` writes the reference and no other text (no recursion, no expansion).
   - Every public function and class that the touched modules expose stays covered.
6. **CLAUDE.md test rules hold.**
   - Package line and function coverage stay ≥ 80%.
   - `ruff check .` and `ruff format --check .` are clean.
   - Local `pytest` passes, and CI is green before the self squash-merge.
   - DRIVER §5 naming applies: branch `claude/T-0425-<slug>`, PR title with `T-0425`, and `Task: T-0425` as the last line of the PR body.
   - The language line in Result and in the commit body: Python, for the existing modules.

## Out of Scope

- **Any behaviour change** of `hilclaw/coder_runtime.py`, `hilclaw/coder_call.py` or `coder.run`'s contract (ADR-0137 slice 2: "keep their contracts"). Only the docstring sentences of criterion 4 change in those two files.
- **The open points of ADR-0137 Boundaries**:
  - a time limit on the call (OD-14);
  - the coder's output stream;
  - the token record;
  - leftovers of a dead process;
  - Podman and WSL;
  - asking the user;
  - any image, Dockerfile or registry.
  No new external dependency.
- **The less-exact ADR, UsageCases, README and OpenDecisionProposals sentences** listed in ADR-0137 Consequences "Less exact, not edited", other than the three code docstrings of criterion 4. No edit to `ARCHITECTURE/`, `README.md`, `orchestration/` or `.claude/`.
- The turn session's credential (O8; OD-18 ⑯ (다)). Do not copy or remove `CLAUDE_CODE_OAUTH_TOKEN` or any credential variable in the session environment.
- `hilclaw/scratch.py`'s "no container (slice (d))" stays true of that module and is not edited.
- Any check that needs a real Docker daemon, a real `claude` or a token. Those are runtime acceptance items (lxix) to (lxxiv), already HQ-0068 (D16).

## Follow-ups

- The joining task of ADR-0153 slice 1 (P2-13; T-0423 Follow-ups) stays a candidate, after the P2 round-loop items in PLAN order.
- If the executor finds a test outside the listed files that reaches the default registry's runtime, it updates that test in this task (tests are outside the size cap) and names it in Result.

## Result

- **PR/commit**: PR #249 squash-merged into `main` as `7468959`; branch `claude/T-0425-coder-runtime-binding` deleted. CI green (3.11, 3.14; coverage, C, sh and test-presence gates).
- **Review**: 2 rounds. Round 1 requested changes (clear the two new variables before the exact `env` comparison in `test_settings_file_beside_the_configuration`; replace a hard-coded timeout with `VERSION_TIMEOUT_S`); both fixed. Round 2 approved with no findings.
- **Change**: `default_registry` binds `coder.run` to `coder_runtime.DockerRuntime()`; `NoContainerRuntime` stays as a runtime that starts nothing. `turn_loop._config_text` copies a non-empty `HILCLAW_CODER_IMAGE` into the server entry's `env` and, when `HILCLAW_CODER_OAUTH_TOKEN` is non-empty, writes the reference `${HILCLAW_CODER_OAUTH_TOKEN}` (never the value). Seam docstrings in `coder_call`, `coder_tool`, `coder_runtime`, `tools`, `turn_loop` rewritten.
- **Language**: Python, for the existing modules.
- **No test starts `docker`**: an autouse guard in `tests/conftest.py` (all tests outside `tests/test_coder_runtime.py`) replaces `hilclaw.coder_runtime`'s `local_run` and `subprocess.Popen` with `pytest.fail`; default-registry tests in `tests/test_coder_tool.py` use a recorder. Full suite 27363 passed.
- **Local checks**: ruff check/format clean; `hilclaw/` coverage 99%, touched modules 100%.
- **Follow-ups**: none new. Runtime acceptance items (lxix)–(lxxiv) stay under HQ-0068.
