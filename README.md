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

- MVP는 "방법 B"(Claude Code Orchestrator)로 단일 compute kernel 최적화를 다룬다. Phase 1에서는 Objectives의 Database를 Git 디렉토리 트리가 대신한다. ([CLAUDE.md](CLAUDE.md) "현재 프로젝트 상태 주의사항", [Requirements.md](ARCHITECTURE/Requirements.md) §0·FR-13)
- run 데이터와 산출물은 별도 저장소 `HIL-Claw-data`에 둔다(#5 A-1). 바이너리·대용량 산출물은 git에 넣지 않는다(#5 A-2: CAS `blobs/` + 해시 참조, Requirements C-3).
- 2층 도구 패키지와 검증 하네스의 일부가 구현되어 테스트되고 있다. 최적화 run을 수행하는 런타임(1층의 런타임 오케스트레이션)은 아직 없다. 계획은 [PROCESS/PLAN.md](PROCESS/PLAN.md)에, 현재 phase는 [PROCESS/STATE.json](PROCESS/STATE.json)에 있다.
- instance의 선행조건: instance를 실행하는 머신에서 런타임 사용자의 Claude Code 명령줄(`claude`)이 로그인되어 있어야 한다(Requirements C-7 ②·③의 파생 — [오너 답변 HQ-0006](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), [ADR-0054](ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md) 결정 8, [UsageCases.md UC-1](ARCHITECTURE/UsageCases.md#uc-1-loop-instance-정의실행) "선행조건"). instance 시작 때 이 조건을 관찰할 런타임 자체 점검은 ADR-0054에 설계 기록만 있고 코드는 아직 없다([PROCESS/PLAN.md](PROCESS/PLAN.md) P1-9). 이 선행조건은 개발 머신에 대한 요구가 아니다([CLAUDE.md](CLAUDE.md) "개발 드라이버와 런타임의 구분").

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
| [ARCHITECTURE/](ARCHITECTURE/) | 설계 문서: [Requirements.md](ARCHITECTURE/Requirements.md)(요구사항·Open Decisions), [UsageCases.md](ARCHITECTURE/UsageCases.md)(유스케이스), [StandardScenarios.md](ARCHITECTURE/StandardScenarios.md)(표준 시나리오·커버리지 검사), [OpenDecisionProposals.md](ARCHITECTURE/OpenDecisionProposals.md)(OD 제안 본문), [reviews/](ARCHITECTURE/reviews/)(검토 기록) |
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



## References

- CUDA Agent (ByteDance)
- Gimlet Labs
- YASP
- Modular.AI
- ...
- 

# License
License to be determined later


