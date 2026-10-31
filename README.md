# HIL-Claw

> 2층 도구 패키지와 검증 하네스의 일부가 구현되어 테스트되고 있으며, 최적화 run을 수행하는 런타임은 아직 없다. 현재 상태·저장소 구성·개발 절차는 [현재 상태와 MVP 범위](#현재-상태와-mvp-범위) 이하의 절에 있다.

## Objectives

- 특정 AI 가속기에 대해 주어진 AI 모델을 최적화 하여 실행하는 (속도 향상 및 동시 서빙 용량 증대) 산출물 — 개별 최적화 compute kernel 및/또는 모델 Binary — 을 만들어내는 자동화된 Agent System. (MVP는 단일 compute kernel 최적화부터 시작한다.)
- 대상 가속기는 외부 타사 HW를 가져와 시험하는 경우와 자사의 개발 중 HW인 경우가 모두 있다.
- Hardware 혹은 Simulator/Emulator In The Loop 방식으로 실험과 실증을 하면서 점진적으로 최적화를 해 나간다.
- 기존의 성공/실패 사례를 저장하여, 점점 더 최적화를 잘 하고 빠르게 최적화 할 수 있도록 한다. 이 정보 저장은 주요 자산이므로 Local Database에 영구 저장해야 한다.
- AI 가속기 마다 특성이 매우 다르고, 같은 가속기라도 (e.g., CPU type, DRAM Size) 주어진 HW환경이나 실행 환경에 따라 성능 특성이 달라질 수 있음이 반영될 수 있어야 한다.
- 최적화 기법 적용 후보군도 Database에 저장되어 Agent가 Try해볼 수 있어야 한다. 단, 어떤 기법이 적절하고 가능성이 높은지 판단하기 위한 정보도 함께 저장되어 Exhaustive Search를 피해야 한다. 이러한 기법은 Skill 형대로 저장되어 있어 고를 수 있도록 하는 것도 괜찮을지 검토해 보아야 한다. (어떨때 쓰면 좋을지는 Skill을 고르는 선택 기준이 되도록 표현되면 된다.)
- 최적화 과정에서 중간 결과물들도 최종 결과물과 마찬가지로 Database에 저장되어 중간지점부터 다시 시작해 볼 수 있어야 한다. 완료된 이후에도 완료지점에서 다시 시작하여 더 최적화를 해보거나 다른 방법을 적용하여 추가 최적화를 수행할 수 있어야 한다.
- 최적화 과정 전반에 Log를 남겨 두어야 한다.
- 외부 연구 논문과 코드를 이해하고, 그 내용을 반영할 수 있도록 하여야 한다. "AI for Science"-like.

## Agent 실행 시 참고 사항

- 모델 내 연산자들은 Merge해서 더 큰 연산을 한번에 하는 것이 더 빠를때도 있다. (아닐 때도 있다.)
- 외부 LLM 실행 최적화 논문을 참고하여 최적과 기법 적용 후보군을 지속적으로 추가/삭제할 수 있어야 한다.

## 현재 상태와 MVP 범위

- MVP는 "방법 B"(Claude Code Orchestrator)로 단일 compute kernel 최적화를 다룬다. 개발의 도달 목표는 Llama 3.2 1B를 연산별 커널로 bf16/fp16 end-to-end 실행하는 것이다(오너 2026-10-19 — Requirements C-6 개정·OD-31; 이 목표를 MVP 범위 안에 둔 것은 통합자 독해). Phase 1에서는 Objectives의 Database를 Git 디렉토리 트리가 대신한다. ([CLAUDE.md](CLAUDE.md) "현재 프로젝트 상태 주의사항", [Requirements.md](ARCHITECTURE/Requirements.md) §0·FR-13)
- run 데이터와 산출물은 별도 저장소 `HIL-Claw-data`에 둔다(#5 A-1). 바이너리·대용량 산출물은 git에 넣지 않는다(#5 A-2: CAS `blobs/` + 해시 참조, Requirements C-3).
- 2층 도구 패키지와 검증 하네스의 일부가 구현되어 테스트되고 있다. 최적화 run을 수행하는 런타임(1층의 런타임 오케스트레이션)은 아직 없다. 계획은 [PROCESS/PLAN.md](PROCESS/PLAN.md)에, 현재 phase는 [PROCESS/STATE.json](PROCESS/STATE.json)에 있다.
- instance의 선행조건: instance를 실행하는 머신에서 런타임 사용자의 Claude Code 명령줄(`claude`)이 로그인되어 있어야 한다(Requirements C-7 ②·③의 파생 — [오너 답변 HQ-0006](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), [ADR-0054](ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md) 결정 8, [UsageCases.md UC-1](ARCHITECTURE/UsageCases.md#uc-1-loop-instance-정의실행) "선행조건"). instance 시작 때 이 조건을 관찰할 런타임 자체 점검은 ADR-0054에 설계 기록만 있고 코드는 아직 없다([PROCESS/PLAN.md](PROCESS/PLAN.md) P1-9). 첫 사례의 코더 호출에는 [ADR-0137](ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md) 결정 4·5의 이미지와 토큰도 필요하다. 이 선행조건들은 개발 머신에 대한 요구가 아니다([CLAUDE.md](CLAUDE.md) "개발 드라이버와 런타임의 구분").

## 세 층 모델

저장소는 세 층으로 나뉜다(#5 A-12). 정의와 언어 정책의 정본은 [CLAUDE.md](CLAUDE.md)의 "세 층 모델"·"도구 계층 언어 정책"이다.

| 층 | 정의 | 현재 저장소에 있는 것 |
|---|---|---|
| 1층 | Claude Code 오케스트레이션(CLAUDE.md·스킬·`.claude/agents` 정의·기법 Skill, Markdown) | `CLAUDE.md`, `.claude/skills/`(개발 절차 스킬 2개), `.claude/agents/`(개발 절차 에이전트 `dev-planner`·`dev-executor`·`dev-reviewer`, [PROCESS/DRIVER.md](PROCESS/DRIVER.md) §7). 이들은 모두 HIL-Claw를 만드는 개발 절차를 위한 것이다. 런타임의 에이전트 정의·프롬프트와 기법 Skill은 아직 없다. |
| 2층 | 1층 에이전트가 호출하는 결정적 도구 패키지(FR-10 도구·백엔드·CAS·스키마 검증·hook 진입점·검증 하네스) | Python 패키지 `hilclaw/`(가칭)이며, 하네스의 C 소스는 `hilclaw/harness/`에, 테스트는 `tests/`에 있다. 지금 들어 있는 것은 주로 데이터 저장소 설정(`hilclaw.config.json`)의 로더, 데이터 plane의 경로와 파일(검증기·쓰기 절차), 키 스키마, 내용 주소 blob 저장소(CAS), 도구를 정의하고 노출하는 틀(명령줄과 stdio MCP 서버)과 mock 백엔드, `cpu_standin`의 로컬 빌드·실행 래퍼, 타이밍·검증 하네스, 그리고 개발 도구 두 개(`PROCESS/STATE.json` 검증기, `gh pr merge` 가드)이다. 일부만 구현된 상태이다: FR-10 도구는 아직 하나도 등록되어 있지 않고(도구 레지스트리의 기본 집합이 비어 있다), `gh pr merge` 가드는 hook으로 등록되어 있지 않다. |
| 3층 | 코더(`claude -p`)가 산출하는 C 커널 | 소스 저장소에 없다. 코더 호출의 산출물은 데이터 plane에 속하며, run 트리의 attempt 디렉토리 아래 `output/`에 놓인다([ADR-0004](ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md)). `output/`의 파일 구성과 형식(Requirements OD-23), 그리고 산출물이 그 자리에 오는 방법(OD-8의 격리 수단)은 미결이다. `tests/harness/calibration/`의 커널은 하네스 테스트의 fixture이며 3층 산출물이 아니다. |

언어 정책은 2층에만 해당한다. 허용 언어는 {Python, POSIX sh, C}이며, 집합 밖 언어는 ADR 없이 쓰지 않는다.

## 저장소 구성

| 경로 | 내용 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 모든 Claude Code 세션이 따르는 개발 규칙(정본) |
| [ARCHITECTURE/](ARCHITECTURE/) | 설계 문서: [Requirements.md](ARCHITECTURE/Requirements.md)(요구사항·Open Decisions), [UsageCases.md](ARCHITECTURE/UsageCases.md)(유스케이스), [StandardScenarios.md](ARCHITECTURE/StandardScenarios.md)(표준 시나리오·커버리지 검사), [OpenDecisionProposals.md](ARCHITECTURE/OpenDecisionProposals.md)(OD 제안 본문), [EventKinds.md](ARCHITECTURE/EventKinds.md)(events.ndjson 이벤트 종류 목록), [StepValues.md](ARCHITECTURE/StepValues.md)(기록 단계의 step 값 목록), [SpendAxes.md](ARCHITECTURE/SpendAxes.md)(spend 축 이름 목록), [BlobTypes.md](ARCHITECTURE/BlobTypes.md)(artifacts.json blob type 값 목록), [reviews/](ARCHITECTURE/reviews/)(검토 기록) |
| [ARCHITECTURE/decisions/](ARCHITECTURE/decisions/) | 결정 기록(ADR). 설계 수준 Open Decision은 [PROCESS/DRIVER.md §9](PROCESS/DRIVER.md#9-od-종결-권한-d6-확정-2026-10-05)의 경로로 여기에서 종결된다 |
| [PROCESS/](PROCESS/) | 개발 드라이버: [DRIVER.md](PROCESS/DRIVER.md)(절차), [PLAN.md](PROCESS/PLAN.md)(phase별 체크리스트), [STATE.json](PROCESS/STATE.json)(드라이버 상태)과 [STATE.schema.json](PROCESS/STATE.schema.json)(그 스키마), [tasks/](PROCESS/tasks/)(task 파일), [journal/](PROCESS/journal/)(iteration 기록), [proposals/](PROCESS/proposals/)(결정 요청의 제안 본문) |
| [.claude/skills/](.claude/skills/) | 개발 절차 스킬 `dev-item-address`·`dev-code-review` |
| [.claude/agents/](.claude/agents/) | 개발 절차 에이전트 정의 `dev-planner`·`dev-executor`·`dev-reviewer` |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | CI 워크플로([로컬 검사](#로컬-검사) 참조) |
| [pyproject.toml](pyproject.toml) | Python 프로젝트 설정: 최소 Python 버전, 런타임 의존성, 개발 도구 그룹, pytest·ruff 설정 |
| [hilclaw.config.json](hilclaw.config.json) | 이 소스 저장소를 데이터 저장소 `HIL-Claw-data`에 묶는 설정(#5 A-1) |
| [hilclaw/](hilclaw/) | 2층 도구 패키지(가칭) |
| [tests/](tests/) | `hilclaw/`의 테스트 |

## 개발 절차

- [CLAUDE.md](CLAUDE.md)가 모든 Claude Code 세션의 규칙 정본이다. 변경 작업은 [dev-item-address](.claude/skills/dev-item-address/SKILL.md) 스킬 절차를 따르고, 리뷰는 [dev-code-review](.claude/skills/dev-code-review/SKILL.md) 스킬 지침으로 한다.
- [PROCESS/DRIVER.md](PROCESS/DRIVER.md)는 자동 개발 드라이버를 기술한다(1 iteration = [PROCESS/PLAN.md](PROCESS/PLAN.md)에서 나온 task 1개). 이것은 HIL-Claw를 **만드는** 프로세스이며, HIL-Claw가 실행할 런타임 오케스트레이터와는 별개다.
- 변경 모드는 둘이다. 문서 모드(문서·프로세스 파일만 변경)는 리뷰어 사이클을 통과하면 PR 없이 `main`에 직접 push한다. 코드 모드(그 외)는 Draft PR, 리뷰 사이클, 테스트 통과를 거쳐 squash-merge한다. 세부는 [CLAUDE.md](CLAUDE.md)의 "브랜치·merge 절차"(#5 A-13)에 있다.
- 미결 사항은 [Requirements.md](ARCHITECTURE/Requirements.md)의 Open Decisions에 등재한다. 결정과 논의는 GitHub Issue [#4](https://github.com/myungjoo/HIL-Claw/issues/4)(아키텍처 결정 스레드·작업 항목), [#5](https://github.com/myungjoo/HIL-Claw/issues/5)(사용자 결정 대기), [#7](https://github.com/myungjoo/HIL-Claw/issues/7)(외부 조사), [#8](https://github.com/myungjoo/HIL-Claw/issues/8)(모순 트래커)에 있다.

## 로컬 검사

CI는 [.github/workflows/ci.yml](.github/workflows/ci.yml)이며, pull request와 `main`으로의 push에서 실행된다. 그 job들은 Python 게이트(ruff와 pytest), sh 게이트(shellcheck), C 게이트(C 소스의 clang 빌드와 하네스 캘리브레이션 테스트), `hilclaw/`의 모듈마다 테스트 파일이 있는지의 검사, `hilclaw/`의 line·function 커버리지 검사이다. 커버리지 임계를 포함한 테스트 규칙의 정본은 [CLAUDE.md](CLAUDE.md)의 "테스트 규칙"이다.

아래 명령은 Python 게이트와 같은 검사를 로컬에서 실행한다. Python >= 3.11이 필요하고([pyproject.toml](pyproject.toml)), 개발 도구 그룹의 설치에는 pip >= 25.1이 필요하다. 둘째 명령은 `pyproject.toml`의 `dependencies`에 적힌 런타임 의존성을 설치한다. C를 빌드하는 테스트는 PATH의 `clang`이 필요하고 그 일부는 POSIX 시스템도 필요하며, 로컬 실행에서는 조건이 맞지 않으면 skip된다.

```sh
python -m pip install --group dev
python -m pip install --only-binary=:all: $(python -c "import tomllib; print(*tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies'])")
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## P2-15 확인 절차

실제 Llama 3.2 1B 가중치로 end-to-end가 reference와 맞는지를 오너가 런타임 머신에서 손으로 확인하는 순서다([PROCESS/PLAN.md](PROCESS/PLAN.md) P2-15, [RuntimeAcceptance.md](PROCESS/RuntimeAcceptance.md) RA-0056). 아래의 `<...>`는 모두 오너가 정할 값이며 저장소는 그 값을 고르지 않는다. 그대로 두면 명령이 거절한다.

1. **머신**: [PROCESS/NIGHTLY.md](PROCESS/NIGHTLY.md) §1의 "머신 준비"(POSIX 호스트 또는 WSL 2, 로그인된 `claude`, Docker, 코더·stand-in 이미지, `HILCLAW_CODER_IMAGE`·`HILCLAW_STANDIN_IMAGE`·`HILCLAW_CODER_OAUTH_TOKEN`)와 `python -m pip install transformers torch`([ADR-0192](ARCHITECTURE/decisions/ADR-0192-od31-model-check-command.md) 결정 3). 이 패키지들은 CI와 개발 드라이버의 의존성이 아니다. 데이터 저장소는 이미 있는 git 저장소여야 하며 [hilclaw.config.json](hilclaw.config.json)의 `local_path`나 환경 변수 `HILCLAW_DATA_REPO_LOCAL_PATH`로 가리킨다. 명령은 Claude Code 세션 밖의 셸에서 저장소 루트에서 실행한다.
2. **모델 파일**: 런타임 사용자가 라이선스에 동의해 Hugging Face의 base 변형(`config.json`, safetensors, 토크나이저 파일 — [ADR-0191](ARCHITECTURE/decisions/ADR-0191-od31-hugging-face-model-files.md) 결정 1)을 직접 받아, 체크아웃과 데이터 저장소 밖의 경로에 둔다.
3. **instance 문서**: 아래 값 파일을 쓰고 빈 디렉토리를 만든 뒤 실행한다. 종류마다 `<출력 디렉토리>/<kind>.json`이 생긴다. shape는 [ADR-0152](ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md) 결정 5, 값의 규칙은 [hilclaw/model_instances.py](hilclaw/model_instances.py)에 있다.

   ```sh
   python -m hilclaw.model_instances <값 파일> <출력 디렉토리>
   ```

   ```json
   {
     "n_max": "<n_max>", "draws": "<draws>", "round_budget": "<round_budget>",
     "kinds": {
       "gemm": {"m": "<m>", "k": "<k>", "n": "<n>", "rtol": "<rtol>", "atol": "<atol>"},
       "rmsnorm": {"m": "<m>", "n": "<n>", "rtol": "<rtol>", "atol": "<atol>"},
       "elementwise_add": {"m": "<m>", "n": "<n>", "rtol": "<rtol>", "atol": "<atol>"},
       "swiglu": {"m": "<m>", "n": "<n>", "rtol": "<rtol>", "atol": "<atol>"},
       "rope": {"m": "<m>", "h": "<h>", "d": "<d>", "rtol": "<rtol>", "atol": "<atol>"},
       "sdpa_kv_cache": {"m": "<m>", "l": "<l>", "h": "<h>", "h_kv": "<h_kv>", "d": "<d>", "rtol": "<rtol>", "atol": "<atol>"}
     }
   }
   ```

4. **run**: 문서마다 한 번씩 실행하며, 아직 돌고 있을 수 있는 run에 `turn_start`를 다시 시작하지 않는다(ADR-0122). `new_run`의 출력 `{"outcome":"started","run_id":"..."}`에서 run id를 읽는다. run이 끝나면 `turn_start`가 표준 출력에 `{"outcome":"run_over"}`를 쓰고 상태 0으로 끝난다. 그 밖의 줄과 상태는 멈춘 이유이며 [hilclaw/turn_start.py](hilclaw/turn_start.py)의 표에 있다. turn 세션의 출력은 표준 오류로 간다.

   ```sh
   python -m hilclaw.new_run <출력 디렉토리>/<kind>.json
   python -m hilclaw.turn_start <run id>
   ```

5. **확인**: 아래 문서를 쓰고 실행한다. 호출 지점 15개가 6개 run을 가리킨다. `lm_head`는 그 자체의 instance 없이 `gemm` run을 쓴다(ADR-0152 결정 4, [ADR-0189](ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md)).

   | run | 호출 지점 |
   |---|---|
   | `gemm` | `qkv`, `o`, `gate`, `up`, `down`, `lm_head` |
   | `rmsnorm` | `attention_norm`, `ffn_norm`, `norm` |
   | `elementwise_add` | `attention_residual`, `ffn_residual` |
   | `swiglu` | `ffn_activation` |
   | `rope` | `rope_q`, `rope_k` |
   | `sdpa_kv_cache` | `sdpa` |

   ```sh
   python -m hilclaw.model_check <확인 문서>
   ```

   ```json
   {
     "model_directory": "<모델 파일 경로>",
     "runs": {
       "qkv": "<gemm run id>", "o": "<gemm run id>", "gate": "<gemm run id>", "up": "<gemm run id>", "down": "<gemm run id>", "lm_head": "<gemm run id>",
       "attention_norm": "<rmsnorm run id>", "ffn_norm": "<rmsnorm run id>", "norm": "<rmsnorm run id>",
       "attention_residual": "<elementwise_add run id>", "ffn_residual": "<elementwise_add run id>",
       "ffn_activation": "<swiglu run id>",
       "rope_q": "<rope run id>", "rope_k": "<rope run id>",
       "sdpa": "<sdpa_kv_cache run id>"
     },
     "flags": ["<그 run들의 빌드 설정>"],
     "prompt": "<프롬프트>",
     "n": "<greedy 토큰 수>",
     "rtol": "<rtol>",
     "atol": "<atol>",
     "build_timeout_s": "<초>",
     "run_timeout_s": "<초>",
     "program_flags": ["<forward program 빌드 플래그>"],
     "program_trailing_flags": ["<뒤쪽 플래그>"]
   }
   ```

   `flags`는 run을 돌린 커밋의 `hilclaw.standin_settings.FLAGS`다(ADR-0189 결정 6). `program_flags`와 `program_trailing_flags`는 forward program 빌드의 인자이고([hilclaw/model_build.py](hilclaw/model_build.py)의 `build_forward_program`) C 라이브러리가 요구하면 뒤쪽에 `-ldl`을 넣는다. `parent`는 선택 멤버로, 빌드 디렉토리를 만들 곳이다. 멤버의 정의는 [hilclaw/model_check.py](hilclaw/model_check.py)에 있다.
6. **결과**: `match`(상태 0)는 행마다의 logit이 `rtol`·`atol` 안이고 처음 `n`개 greedy 토큰이 reference와 같다는 뜻이다. `no_match`(상태 10)는 둘 중 하나가 아니라는 뜻이며, 줄의 `logits`와 `first_differing_token`이 어느 쪽인지 말한다. 다른 `outcome`은 판정이 아니라 확인이 그 앞에서 멈춘 것이다. 결과는 어디에도 저장되지 않으므로 오너가 [RuntimeAcceptance.md](PROCESS/RuntimeAcceptance.md)의 RA-0056 `상태`에 손으로 적는다. RA-0035, RA-0050, RA-0057, RA-0058, RA-0061, RA-0065~RA-0067도 이 확인에서 드러나므로 각각 본다.



## References

- CUDA Agent (ByteDance)
- Gimlet Labs
- YASP
- Modular.AI
- ...
- 

# License
License to be determined later


