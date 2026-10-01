# StandardScenarios 문헌 검토 및 보강·추가 제안 (2026-09-03)

[StandardScenarios.md](../StandardScenarios.md)의 S0~S6을 2025~2026년 LLM 기반 커널 생성/최적화 문헌과 대조하여, 기존 시나리오의 **보강 제안(B1~B8)** 과 **추가 시나리오 제안(S7~S10)** 을 정리한다. 본 문서는 **제안**이며, 사용자 승인 전에는 StandardScenarios/Requirements를 변경하지 않는다(미결 불발명 원칙).

> **처리 결과 (2026-09-03 사용자 확정)**: S0~S6을 **기본(MVP)**, S7~S10을 **추가 사항(확장)** 계층으로 StandardScenarios에 반영. 확장 시나리오는 "설계가 막지 않는가"([확장 호환]) 규칙으로 검사. B1은 최소 조항만 MVP FR-9에 반영하고 전면 하드닝은 OD-13 확장 고려로. B2→OD-1, B4·B5→OD-6, B6→OD-7, B7→OD-14 신설, B8→NFR-4에 "확장 고려" 메모로 등재.
>
> **통합 후 참조 정정 (2026-10-01, #5 A-9)**: 본 문서가 쓰인 시점의 OD 번호는 통합 전 main 기준이다. 현재 번호: 전면 하드닝 = **OD-16**, B7 baseline = **OD-28**, B8 = NFR-4 → OD-16·OD-12. **S8(Best-of-N)은 오너 결정으로 MVP 기본 계층에 승격**(OD-21 확정, 세부 OD-29). 본 문서의 시사점 다수는 Issue #7 S-1(2026-07-31)과 중복되며(#8 M22), 정본은 [Requirements.md](../Requirements.md) OD 등록부와 [OpenDecisionProposals.md](../OpenDecisionProposals.md)다. 본 문서는 2026-09-03 시점 기록으로 보존한다.

---

## 1. 조사한 문헌

| 구분 | 문헌 | HIL-Claw 관련 요점 |
|---|---|---|
| 벤치마크 | [KernelBench](https://arxiv.org/abs/2502.10517) (Stanford, ICML 2025) | `fast_p` = 정확 + baseline 대비 p배 이상. baseline 정의(eager vs `torch.compile`)가 결과를 좌우. 실행 피드백 기반 반복 개선이 유효 |
| 벤치마크 | [MultiKernelBench](https://arxiv.org/abs/2507.17773) | GPU/NPU(Ascend)/TPU 다중 플랫폼. 비주류 플랫폼은 **카테고리별 예시(exemplar) 제공**이 성공률을 크게 올림. 백엔드 추상화 레이어 |
| 벤치마크 | [SOL-ExecBench](https://arxiv.org/abs/2603.19173) | **Speed-of-Light(HW 이론 한계) 대비 달성률**로 평가. 클록 고정·L2 클리어·서브프로세스 격리·정적 검사로 측정 조작 방지 |
| 벤치마크 | [CANN Bench](https://arxiv.org/html/2607.20518) | 실 NPU + 알고리즘 한계 대비 평가(Ascend) |
| 검증 | [Towards Robust Agentic CUDA Kernel Benchmarking, Verification, and Optimization](https://arxiv.org/abs/2509.14279) (Sakana, robust-kbench) | LLM이 검증을 우회한 실제 사례(연산 제거, 입력 패턴 하드코딩, 저정밀도, 출력 캐시 재사용, 스트림 주입, 타이밍 함수 패치)와 대책(다양한 shape/seed, 정밀도 임계, 타이밍 하드닝, 정적 분석, LLM 검증자 3종). 진화 루프: N=8 제안 → 검증자 스크리닝 → 상위 4개만 HW 실행 → 아카이브 갱신 |
| 검증 | [Kernel Contracts](https://arxiv.org/abs/2604.22032) | 이기종 실리콘용 커널 정확성 명세(8요소: scope, pre/postcondition, tolerance, reference oracle, measurement protocol, violation signature). Ascend 정밀도·Sakana·AMD silent-accept 실사고를 계약 위반으로 매핑 |
| 에이전트 시스템 | [CUDA Agent](https://cuda-agent.github.io/) (ByteDance Seed/Tsinghua, [arXiv](https://www.alphaxiv.org/overview/2602.24286v1)) | Skill 문서(SKILL.md) + 프로파일러 + GPU 샌드박스의 **skill-augmented 실행환경**. 보호된 검증/프로파일 스크립트, 금지 fallback 패턴, 5-입력 정확성 검사, 동기화된 warm-up |
| 에이전트 시스템 | [METR: Measuring Automated Kernel Engineering](https://metr.org/blog/2025-02-14-measuring-automated-kernel-engineering/) | 병렬 트리 탐색 + ground-truth 검증, 문제당 300회 시도. best-of-k로 93% 문제에서 >5% 개선. **샘플 수·scaffolding에 성능이 크게 의존** |
| 에이전트 시스템 | [AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) (DeepMind) | 프로그램 DB + 자동 평가기 + 진화 탐색. FlashAttention XLA IR 32% 개선 |
| 에이전트 시스템 | [KernelEvolve](https://arxiv.org/abs/2512.23236) (Meta) | NVIDIA/AMD/Meta 자체 가속기. 그래프 기반 탐색(선택 정책·fitness·종료 규칙) + **retrieval-augmented prompt**. 160 ATen 연산 3개 이기종 플랫폼 100% 정확 |
| 에이전트 시스템 | [AccelOpt](https://arxiv.org/abs/2511.15915) (Trainium) | **optimization memory**: 과거 slow→fast 커널 쌍과 인사이트를 저장·검색해 탐색 공간 축소. peak throughput 49%→61% |
| 에이전트 시스템 | [AscendOptimizer](https://arxiv.org/abs/2603.23566) | Ascend NPU용 **episodic** 에이전트(에피소드 메모리) |
| 에이전트 시스템 | [KForge](https://arxiv.org/abs/2511.13274) (Gimlet Labs) | 다중 에이전트 + 공유 메모리, 크로스 플랫폼(새 가속기 온보딩), 엄격한 정확성 검사 |
| 에이전트 시스템 | [Optimizing CUDA like a Human: Micro-Profiling Tools as Expert Surrogates](https://arxiv.org/pdf/2606.26453) | 프로파일링 도구 출력을 전문가 대리 신호로 코더에 제공 |
| RL 학습형 | [Kevin](https://arxiv.org/html/2507.11948v1), [CUDA-L1](https://arxiv.org/pdf/2507.14111), CUDA Agent RL | 모델 자체를 RL로 학습. MVP 범위 밖(방법 B는 frontier 모델을 CLI로 사용)이나, 축적 데이터의 미래 활용처 |
| 서베이 | [Towards Automated Kernel Generation in the Era of LLMs](https://arxiv.org/pdf/2601.15727) | 생성-검증-프로파일-탐색-메모리의 반복 루프로 분야를 정리 |
| 상용 | [Yasp](https://yasp.ai/product), [Gimlet Labs](https://gimletlabs.ai/) | 실 디바이스 측정 + cost model, 단일 API로 모델→HW 최적화 |

**공통 관찰**: 2025년 이후 모든 시스템이 (1) 검증 우회(reward hacking)를 1급 위협으로 다루고, (2) 라운드당 **다수 후보**를 생성해 저비용 필터로 거른 뒤 소수만 HW에서 측정하며, (3) **프로파일 결과 + 과거 사례 메모리**를 다음 프롬프트에 구조화해 넣고, (4) 평가 기준을 "이전 대비"에서 **"HW 이론 한계 대비"** 로 옮기는 추세다.

---

## 2. S0와 문헌 공통 루프의 대조

| 루프 구성요소 | 문헌의 표준 | S0 현재 | 판정 |
|---|---|---|---|
| 생성 | 라운드당 N개 후보(8~수백) | 1개(단일 궤적) | **차이** → B3/S8 |
| 저비용 필터 | 컴파일·LLM 검증자·정적 검사 후 상위 k만 HW | sim 조기검증(FR-1) | 부분 지원 → B3 |
| 정확성 검증 | 다양 shape/seed, 정밀도, 격리, 타이밍 하드닝 | tolerance 기반(FR-9), 위치 미결(OD-13) | **강건성 요구 부재** → B1/S7 |
| 프로파일 환류 | 프로파일 요약을 다음 프롬프트에 구조화 | S0-8 문서화, OD-6 | 지원(미결) → B4 |
| 메모리 | slow→fast 쌍 + 인사이트, 에피소드, 프로그램 DB | 사례 통계 랭킹(FR-7), OD-7 | 지원(미결) → B6 |
| 목표/정지 | SOL 달성률, budget, fitness 종료규칙 | budget·target·비수렴(FR-3, UC-7) | 지원, 어휘 확장 여지 → B2 |
| 플랫폼 문서 | 문서·예시 검색증강이 비주류 HW 성패 좌우 | HW docs 등록(FR-14) | 코더 spec 전달 경로 미명시 → B5 |
| 격리/보호 | 샌드박스, 검증 스크립트 보호, 금지 패턴 | NFR-4 미결 | 미결 → B8 |

---

## 3. 기존 시나리오 보강 제안 (B)

| # | 대상 | 제안 | 근거 문헌 | 영향 | 판정 |
|---|---|---|---|---|---|
| **B1** | S0-6, S1-6, FR-9 | correctness 검증을 **적대적 강건성** 기준으로 정의: 최적화 중 보지 못한 shape/seed, 정밀도 임계, 격리 프로세스, 타이밍 동기화(warm-up·stream sync·클록 고정), 정적 검사, 검증 하네스 write-protect | Sakana 사고·robust-kbench, SOL-ExecBench, CUDA Agent, Kernel Contracts | FR-9 확장 또는 신규 NFR(검증 강건성), OD-13과 결합 | **갭** |
| **B2** | S0-7, FR-2·3, OD-1 | target/정지 어휘에 **HW 이론 한계(speed-of-light/roofline) 대비 달성률** 추가 검토. "더 이상 개선 불가능" 판정에 원칙적 상한 제공. FR-15 원칙(과거 사례≠목표)과 정합 — 목표는 HW 한계 | SOL-ExecBench, CANN Bench, AccelOpt(peak %) | OD-1 항목 추가 | 미결(OD 보강) |
| **B3** | S0-8·9, S1-4, FR-1 | 라운드 = **N개 후보 병렬 위임 → 저비용 스크리닝 → 상위 k만 board**. board 희소성(C-4)과 정합 | Sakana N=8→4, METR best-of-k, AlphaEvolve, KForge | FR-1 라운드 정의 확장(후보 수 = instance 파라미터), NFR-5 비용 집계 | **갭** → S8 |
| **B4** | S0-6·8, OD-6 | 코더 spec에 넣는 **프로파일 요약의 구조**(병목 유형, 점유율, 메모리/연산 bound 판정)를 OD-6에 명시 | CUDA Agent, Micro-Profiling 논문, robust-kbench 아카이브 | OD-6 보강 | 미결 |
| **B5** | S0-1, FR-14, OD-6 | HW **Documentation 발췌·같은 카테고리 예시 커널**을 코더 spec에 검색증강으로 포함하는 경로 명시. 새 NPU일수록 결정적 | MultiKernelBench, KForge, KernelEvolve, AscendCraft | OD-6에 "HW 문서·exemplar 전달" 항목, OD-11과 연결 | 미결(OD 보강) |
| **B6** | S6, FR-7, OD-7 | 크로스런 저장 단위를 통계에 더해 **"변환 전/후 코드 쌍 + 개선 이유 요약"** 으로 확장. FR-11 결정 로그·FR-6 산출물이 이미 원천이므로 스키마만 보강 | AccelOpt optimization memory, AscendOptimizer, AlphaEvolve DB | OD-7 보강, OD-8 레이아웃 | 미결 |
| **B7** | S0-4, FR-1 라운드 0 | **baseline 선택을 instance 파라미터화**: bring-up 코드 / 벤더 라이브러리 커널 / 기존 best 중 택. baseline에 따라 개선율 의미가 달라짐 | KernelBench(eager vs compile), CUDA Agent(vs torch.compile) | 신규 OD | 미결(OD 신설) |
| **B8** | S2, NFR-4 | 격리 정책에 **검증·프로파일 스크립트 보호(코더 수정 불가), 금지 fallback 패턴, 웹 검색 차단 여부**를 명시 | CUDA Agent, SOL-ExecBench 샌드박스 | NFR-4 보강 | 미결 |

---

## 4. 추가 시나리오 제안 (S7~S10)

아래는 StandardScenarios에 추가할 후보이며, 각 단계에 근거를 태깅하고 검사 규칙을 적용한 결과를 함께 적는다.

### S7. 검증 우회·퇴화 해 탐지 (Adversarial Correctness)

**액터**: 시스템 (autonomous/checkpoint 공통)

1. 코더가 생성한 커널이 기본 검증(고정 입력·tolerance)을 통과한다. (FR-9)
2. 강화 검증 실행: 최적화 중 노출되지 않은 shape/seed, 정밀도 하향 여부, 격리 프로세스, 스트림 동기화 후 타이밍, 정적 검사(금지 패턴). (FR-9 확장 필요, FR-10, NFR-4 — **갭**)
3. 강화 검증 실패 → 해당 라운드를 **실패로 기록**하고 실패 유형(연산 제거/하드코딩/저정밀/캐시 재사용 등)을 태깅. (FR-6·11)
4. 다음 라운드 코더 spec에 해당 금지 패턴을 명시적으로 추가. (FR-5, OD-6)
5. 반복 발생 시 gate/알림으로 에스컬레이션. (FR-4·16, UC-7)

**판정**: ⚠️ 갭 — 2단계의 강건성 요구가 FR-9에 없음(B1과 동일 갭).

### S8. 라운드 내 다중 후보 탐색 (Best-of-N)

**액터**: 배포 엔지니어 / CI

1. instance 파라미터로 라운드당 후보 수 N과 board 승격 수 k를 지정한다. (UC-1; **갭** — FR-1은 단일 후보)
2. 기법 랭킹 상위 N개(또는 같은 기법의 N개 변형)를 N개 코더 인스턴스에 병렬 위임한다. (FR-5·7)
3. compile → sim → (선택) LLM 검증자로 스크리닝, 상위 k개만 board 측정. (FR-1·10, C-4)
4. best 채택, 나머지 후보도 실패/중간 산출물로 저장하여 통계에 반영. (FR-6·7)
5. 토큰·HW 비용을 후보별로 집계한다. (NFR-5)

**판정**: ⚠️ 갭 — FR-1 라운드 정의 확장 필요(B3). C-2(단일 run)와는 별개 개념(하나의 run 안의 다중 후보).

### S9. Board 장애·측정 노이즈 대응

**액터**: 시스템 → 배포 엔지니어

1. board 측정 중 hang/timeout/예약 경합 발생. (C-4, OD-10)
2. 타임아웃 후 재시도 또는 다른 board 예약; 반복 실패 시 sim 결과로 대체하고 "board 미검증" 표시. (FR-10, OD-10)
3. 정상 측정 시 반복 측정·신뢰구간을 계산하고, 노이즈 범위 내 차이는 "개선 아님"으로 판정한다. (NFR-3)
4. 장애 이력을 hw_profile에 기록해 이후 랭킹·스케줄에 반영. (FR-13·14)

**판정**: ✅ 지원(미결) — NFR-3·OD-10 등재됨. 시나리오 추가의 효과는 이 OD들의 확정을 강제하는 것.

### S10. 결과 재현 (Reproduce)

**액터**: 배포 엔지니어 / CI

1. 과거 run의 best를 선택한다. (UC-6, FR-6)
2. instance.json의 source-repo commit + artifacts 해시(CAS)로 코드·바이너리를 복원한다. (NFR-2, A-1/A-2, FR-13)
3. 같은 hw_profile에서 재측정하여 기록값과 대조한다. (FR-10, NFR-3)
4. 차이가 노이즈 범위를 넘으면 환경 변화(드라이버/펌웨어/호스트)를 의심하고 새 hw_profile 키 후보로 표시한다. (FR-14, OD-4)

**판정**: ✅ 지원(미결) — S5(조회)를 "재현 실행"으로 확장. OD-4의 환경 필드 정의를 강제.

---

## 5. 요약 — 승인 요청 항목

| 우선순위 | 항목 | 성격 | 반영 시 변경 |
|---|---|---|---|
| **높음** | B1 + S7 검증 강건성 | 갭 | FR-9 확장(또는 NFR-7 신설), OD-13 보강, S7 추가 |
| **높음** | B3 + S8 다중 후보 | 갭 | FR-1 확장(후보 수·승격 수 파라미터), NFR-5, S8 추가 |
| 중간 | B2 SOL 대비 달성률 | OD 보강 | OD-1 항목 추가 |
| 중간 | B5 HW 문서·exemplar → spec | OD 보강 | OD-6 항목 추가 |
| 중간 | B7 baseline 선택 | OD 신설 | OD-14 |
| 중간 | S9, S10 추가 | 시나리오만 | StandardScenarios 추가(갭 없음) |
| 낮음 | B4, B6, B8 | OD/NFR 문구 보강 | OD-6, OD-7, NFR-4 |

**MVP 범위 밖으로 기록만 할 것**: RL 학습형 접근(Kevin, CUDA-L1, CUDA Agent RL). 단, S6로 축적되는 slow→fast 쌍은 미래 fine-tuning 자산이 될 수 있음(METR: 1,200개 best 솔루션으로 fine-tune 시 격차 대부분 해소).
