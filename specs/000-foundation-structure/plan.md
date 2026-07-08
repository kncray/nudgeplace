# Implementation Plan: Foundation — Structure & Boundaries

**Branch**: `000-foundation-structure` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/000-foundation-structure/spec.md`

> **Note (branch)**: 이 프로젝트는 지금까지 `main`에서 진행되었다(헌장·로드맵·스펙 모두
> main 커밋). SpecKit 관례상 feature 식별자는 `000-foundation-structure`이며, 실제 git
> 브랜치 분리 여부는 첫 구현 커밋 전에 사람이 결정한다(§Review & Approval 참조).

## Summary

Spec 000은 이후 모든 primitive·도메인이 놓일 **Django 모듈러 모놀리스 구조**와
**기계적으로 강제되는 정적 import 도메인 경계**, 그리고 **문서 소유 규칙(ADR)**을
확립한다. 실제 도메인 모델·커널 primitive·외부 연동은 범위 밖(각각 P1~, Spec 001, P6).

기술 접근: Django 5.2 LTS 스캐폴딩 위에 `apps/<domain>/` 도메인 계층과 `shared_kernel/`
빈 커널 패키지를 두고, **Tach**(정적 import 계약 검사)로 (1) 도메인 간 접근은
명시된 dependency edge 안에서만 가능하며 대상 앱의 `apps.<domain>.services`만 허용
(내부 모듈·models 금지), (2) `shared_kernel ← apps` 단방향(커널→도메인 역의존 금지)을
선언적으로 강제한다. Tach는 미등록 코드를 검사 밖(`<root>`)으로 흘리므로,
`root_module = "forbid"` + `apps/*` 전수 등록 대조 테스트로 **미래 도메인 앱이 경계
밖으로 빠지는 것 자체를 차단**한다(R-BC-4). 경계 검사는 **GitHub Actions job + branch
protection required status check**로 실행돼 silent-skip을 막고(FR-003), repo-local CI
계약 테스트가 `ci.yml`에서 검사 스텝이 실수로 빠지는 것을 잡으며, 거짓-통과 방지 메타
테스트가 "검사기가 실제로 위반을 잡는지"를 검증한다(US1 시나리오 4). 문서는 핵심
결정 ADR과 state-model·glossary의 정식 경로·소유 규칙만 남기고 빈 문서는 선제
생성하지 않는다(BR-5).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.2 LTS · Tach(정적 import 경계 강제) · pytest +
pytest-django(테스트) · ruff(린트·포맷) · uv(패키징·의존성, `pyproject.toml`).
레거시 `requirements/*.txt`는 사용하지 않는다.

**Storage**: N/A — 이 스펙은 도메인 모델을 만들지 않는다(SC-003: `models.py` 엔티티
0개). Django 기본 DB 설정은 앱 부팅을 위해 존재할 수 있으나 어떤 모델도 이를
사용하지 않으며, 저장소 선택은 Spec 001/이후로 위임한다.

**Testing**: pytest + pytest-django. 경계 계약 테스트(허용/차단 + near-miss 공개
표면 차단, AC-9), 거짓-통과 방지 메타 테스트(알려진 위반 픽스처에 `tach check`를
CLI로 실행해 exit code ≠ 0 **및 해당 위반이 리포트에 식별됨**을 단언 — 설정 부재
에러의 공허 통과 방지), 모듈 등록 대조 테스트(`apps/` 직계 자식 전수가 tach 모듈로
등록 + 과잉 exclude 방지 — R-BC-4), 공개 인터페이스 경유 호출 테스트, 픽스처 범위
테스트(models·migrations·커널 심볼 0 — SC-003 기계 검증), CI 계약 테스트(잡 id
`quality-gate`·trigger·스텝 순서·continue-on-error/조건부 skip 부재 + CODEOWNERS
존재 — C-5), 문서 소유 규칙 테스트.

**Target Platform**: Linux 서버(CI: GitHub Actions / ubuntu-latest), 로컬 개발
macOS·Linux.

**Project Type**: Django 모듈러 모놀리스 — 플랫폼 기반 스캐폴딩(도메인 없음).

**Performance Goals**: N/A — 런타임 도메인 동작이 없는 구조 스캐폴딩. (품질 목표는
성능이 아니라 "등록된 정적 import 경계 위반 차단·거짓 통과 방지"이며 Success
Criteria로 관리.)

**Constraints**:
- 경계 검사는 CI에서 **생략 불가능한 필수 단계**로 실행된다(silent-skip 금지, FR-003).
  GitHub branch protection/Ruleset required check는 저장소 파일 밖 설정이므로 tasks 완료
  증거로 별도 기록한다. required check는 잡 이름 단위 보증이므로 repo-local CI 계약
  테스트(계약 고정 잡 id `quality-gate`·trigger·스텝 순서·continue-on-error/조건부
  skip 부재 검증)와 워크플로 변경 리뷰 게이트(`.github/CODEOWNERS` repo 파일 +
  code-owner review 필수화 플랫폼 설정의 두 절반)로 보완한다(boundary-contract C-5).
- 모든 `apps/*` 패키지는 `tach.toml` 모듈로 등록되어야 한다 — `root_module = "forbid"`
  + 등록 대조 테스트로 기계 강제(R-BC-4). 미등록 앱이 경계 검사 밖으로 빠지는 것을
  사람 기억에 맡기지 않는다.
- `shared_kernel`는 public symbol **0개**(빈 위치, SC-003).
- 경계 적합성 픽스처 앱은 도메인 모델·primitive **정의 0개**(SC-003 — 기계 검증),
  cross-app 내부 import **0건**(SC-005). 커널이 채워진 뒤(Spec 001~) primitive의
  **사용**은 허용되지만 **정의** 금지는 유지된다(정의/사용 분리).
- `docs/domain/state-model.md`·`glossary.md`를 **선제 생성하지 않는다**(BR-5, SC-004).
- 관찰 가능한 동작은 test-first(RED→GREEN); 순수 스캐폴딩만 예외(FR-007).

**Scale/Scope**: 소규모 — 픽스처 앱 2개, 공유 커널 패키지 1개(빈), 설정 계층 3개
(base/local/ci), ADR 3개, tach.toml 1개, CI 워크플로우 1개. 도메인 스케일 없음.

## Constitution Check

*GATE: The Initial Check MUST pass before Phase 0 research; the Post-Design Re-check MUST pass after Phase 1 design. Record both separately so each gate is auditable.*

Two-tier gate per Constitution governance: (1) CORE gates — I, III, IV, V, VI, VII, VIII — always evaluated; a core gate that genuinely does not apply remains visible and is recorded as N/A with rationale. (2) CONDITIONAL gates use the Constitution's single-source trigger matrix. **이 스펙은 도메인·금액·이벤트·외부연동·자원선점·벤더·레거시 재사용이 전무하므로 조건부 게이트가 하나도 트리거되지 않는다.** 아래 표는 코어 7개만 평가한다(기계적 전수 재평가 방지).

### Initial Check (before Phase 0)

**Date**: 2026-07-08

| Gate (core + triggered) | Result | Notes / justification; N/A requires rationale |
|---|---|---|
| I 스펙 우선 | **PASS** | 승인된 spec(사람 승인 완료) 위에서 계획 작성. 관찰 가능한 동작은 RED→GREEN, 순수 스캐폴딩만 예외. |
| III 마켓플레이스 우선 | **N/A** | 벤더·마켓플레이스 도메인 없음. 벤더 소유권·생명주기 모델링은 P1~. |
| IV 불변 스냅샷 | **N/A** | 재무 값·주문·스냅샷이 없다(도메인 데이터 0). 스냅샷은 P5, 이벤트 버저닝은 Spec 001. |
| V 금액 | **N/A** | 금액 계산·저장 없음. Money 타입은 Spec 001. |
| VI 벤더 격리·인가 | **N/A** | 벤더·행위자 없음. 역할 스캐폴딩은 Spec 001, 벤더 격리는 P1. |
| VII 모듈러 모놀리스 | **PASS** | 이 스펙의 본체 — `apps/<domain>/` 도메인 계층 + 단일 배포 단위 Django 구조를 세운다. |
| VIII 도메인 경계 | **PASS** | 이 스펙의 본체 — 정적 import 경계를 Tach로 기계 강제, 공개 서비스 인터페이스 패턴, 커널 단방향 의존. |

**조건부 게이트**: 트리거 없음(IX·X·XI·XII·XIII·XIV·XV·XVI·XVII 모두 해당 도메인/
연동/이벤트/자원선점/레거시 부재로 미트리거).

**아티팩트로 충족되는 거버넌스·품질 원칙**(트리거 매트릭스 밖이나 산출물 자체로 충족):
XVIII(학습 지향 문서화 — spec에 Business Context·Domain Concepts·Business Rules·Edge
Cases·Architectural Considerations 존재), XIX(AI 설계 파트너 — 별도 세션 적대적 리뷰 후
사람 승인), XX(설명 가능 — 핵심 결정 ADR 3건 산출), 거버넌스 표준 상태 모델(빈 문서
선제 생성 없이 소유 규칙만 확립).

**Initial Gate 결과: PASS** (위반 없음 → Complexity Tracking 비어 있음).

### Post-Design Re-check (after Phase 1)

**Date**: 2026-07-08

| Gate | Result | What changed since Initial Check; N/A requires rationale |
|---|---|---|
| I 스펙 우선 | **PASS** | Phase 1 산출물(contracts·quickstart)이 테스트로 검증되는 형태로 설계됨. 변화 없음. |
| III 마켓플레이스 우선 | **N/A** | 변화 없음(벤더 부재). |
| IV 불변 스냅샷 | **N/A** | 설계에 스냅샷·재무 값 없음(변화 없음). |
| V 금액 | **N/A** | 변화 없음. |
| VI 벤더 격리·인가 | **N/A** | 변화 없음. |
| VII 모듈러 모놀리스 | **PASS** | 설계가 `apps/`·`config/`·`shared_kernel/` 레이아웃으로 구체화됐고 원칙과 일치. 변화 없음. |
| VIII 도메인 경계 | **PASS** | tach.toml 계약(명시적 dependency edge + `[[interfaces]]` services-only) + 커널 단방향 + 메타 테스트로 설계 구체화. 강화됨. |

**Post-Design Gate 결과: PASS** — 설계가 새 원칙을 트리거하지 않았고 코어 게이트 상태
불변. 일탈 없음.

## Project Structure

### Documentation (this feature)

```text
specs/000-foundation-structure/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (구조 개념 — 영속 엔티티 0)
├── quickstart.md        # Phase 1 output (검증 시나리오)
├── contracts/           # Phase 1 output
│   ├── boundary-contract.md
│   └── public-service-interface.md
├── checklists/
│   └── requirements.md  # (already present)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
config/                          # Django 프로젝트 설정
├── __init__.py
├── settings/
│   ├── __init__.py
│   ├── base.py                  # 공통 설정
│   ├── local.py                 # 로컬 개발
│   └── ci.py                    # CI(경계 검사·테스트) — prod/sandbox는 만들지 않음(YAGNI)
├── urls.py                      # 라우팅 골격(순수 스캐폴딩)
├── wsgi.py
└── asgi.py

apps/                            # 도메인 계층 (Tach에서 domain 레이어로 등록)
├── __init__.py
├── conformance_a/               # 경계 적합성 픽스처 앱 A (도메인 모델·primitive 정의 0)
│   ├── __init__.py
│   ├── apps.py
│   └── services.py              # 자명한 공개 서비스 인터페이스(유일한 공개 진입점)
└── conformance_b/               # 경계 적합성 픽스처 앱 B
    ├── __init__.py
    ├── apps.py
    ├── services.py
    └── internal.py              # 내부 모듈 위반-샘플 표적(비공개 — 경계 테스트가 차단 검증)

shared_kernel/                   # 공유 커널 패키지 — 빈 위치(public symbol 0). 내용은 Spec 001.
└── __init__.py

tests/
├── boundary/
│   ├── test_boundary_contract.py   # 허용 통과 / 위반·near-miss 차단 (US1 #1·#2·#3, AC-9)
│   ├── test_boundary_meta.py       # 거짓-통과 방지 메타(tach check on known violation, US1 #4)
│   └── test_module_registration.py # apps/* 전수가 tach 모듈로 등록 (R-BC-4, AC-7)
├── conformance/
│   ├── test_public_interface.py    # cross-app 호출은 services 경유만 (SC-005)
│   └── test_fixture_scope.py       # 픽스처 models.Model subclass 0·migrations 0·커널 심볼 0 (SC-003)
├── ci/
│   └── test_ci_contract.py         # CI 계약 고정(잡 id·trigger·스텝·skip 금지·CODEOWNERS) — 실수 삭제 방어 (C-5, AC-8)
└── docs/
    └── test_docs_ownership.py      # ADR 존재 + state-model/glossary 미선제생성 (US2, SC-004)

docs/
└── adr/
    ├── 0001-modular-monolith.md
    ├── 0002-boundary-enforcement-tach.md   # 정적 import 경계 기계 강제 + 문서 소유 규칙
    └── 0003-shared-kernel-unidirectional.md

tach.toml                        # 경계 계약(명시적 edge + [[interfaces]] services-only + root_module="forbid")
pyproject.toml                   # uv 의존성 + ruff(line 100) + pytest 설정
manage.py
.github/
├── CODEOWNERS                   # /.github/workflows/ 소유 규칙 — 워크플로 리뷰 게이트의 repo-local 절반 (C-5)
└── workflows/
    └── ci.yml                   # repo-side CI: 경계 검사·테스트 실행 (계약 고정 잡 id: quality-gate)
```

**Structure Decision**: Option 1 (Django 모듈러 모놀리스, 원칙 VII/VIII). 단일 배포
단위 안에서 각 도메인이 독립 앱이 되고, 도메인 간 접근은 명시적 dependency edge와
각 앱의 `services` 공개 표면을 통해서만 일어난다.
현 스펙에는 실제 도메인이 없어 `apps/`에는 경계 검사 시험용 픽스처 앱 2개만 존재한다.
Spec 000의 양성 fixture는 `conformance_a → conformance_b.services` 단방향 호출이며,
`tach.toml`에서 이 edge를 명시하고 대상 앱 공개 표면을 `services`로 제한한다.
모놀리스는 시작 상태이며 상한이 아니다 — 안정적 경계 근거 + 측정된 운영 필요가
문서화되면(Structure Decision + ADR) 도메인을 별도 Django 서비스로 추출할 수 있다
(원칙 VII "필요가 입증되기 전까지 도입 금지"). 비-Django 재작성은 프로토타입/스파이크
한정이다.

## Complexity Tracking

> Constitution Check에 정당화가 필요한 위반이 **없다**. 이 표는 비어 있다.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (없음) | — | — |

## Architecture Decisions

> Principle XX: rationale MUST, ADR는 SHOULD 메커니즘. 아래 결정은 `docs/adr/`에 ADR로 남긴다.

| Decision | Rationale | Alternatives considered | Trade-offs accepted | Evolution path | ADR link |
|---|---|---|---|---|---|
| Django 모듈러 모놀리스 채택 | 원칙 VII — 도메인 경계 미검증 상태에서 분산 복잡도 회피, 단일 배포로 운영 단순 | 처음부터 마이크로서비스; 비-Django | 단일 배포 단위의 결합 위험은 VIII의 기계 강제로 상쇄 | 경계 안정·운영 필요 입증 시 도메인별 별도 Django 서비스 추출 | `docs/adr/0001-modular-monolith.md` |
| 정적 import 경계를 Tach로 기계 강제 | 원칙 VIII — 관례 아닌 도구 강제. Tach `depends_on`은 허용 edge를, `[[interfaces]]`는 "services만 공개" 규약을 선언적으로 강제. 미등록 코드가 검사 밖으로 빠지는 Tach 기본 동작은 `root_module="forbid"` + 등록 대조 테스트로 봉쇄(R-BC-4) | import-linter(헌장 예시); 커스텀 AST 검사; 리뷰 관례만 | Tach가 잡는 범위는 **정적 import**로 한정(동적 조회·문자열 FK·raw SQL은 규약·리뷰). `forbid`만으로는 미등록 앱 간 상호 import 미검출 — 등록 대조 테스트 병행 필수. GitHub required check는 repo 파일 밖 설정 증거가 필요 | 실제 도메인 참조가 생기는 P1에서 우회 경로 추가 검사 판단 | `docs/adr/0002-boundary-enforcement-tach.md` |
| 공유 커널 단방향 의존 | 원칙 VIII/BR-3 — 커널→도메인 역의존이 경계를 무너뜨림 | 양방향 허용; 커널에 도메인 편의 코드 유입 | 커널은 지금 비어 있어(원칙 준수 실증) 역의존 계약이 vacuous하지 않도록 픽스처를 도메인 계층으로 등록 | 내용물(Money 등)은 Spec 001에서 커널에 추가 | `docs/adr/0003-shared-kernel-unidirectional.md` |

> **문서 소유 규칙**(state-model·glossary의 정식 경로 + "첫 상태/도메인 도입 기능이
> 최초 생성", 빈 문서 선제 생성 금지)은 ADR 0002에 함께 기록한다(FR-006). 로드맵상
> 최초 생성 주체는 P1이다(벤더 생명주기 상태·첫 도메인 용어 도입).

## Review & Approval

- **Reviewer** (separate session/model — may be an AI model): Codex GPT-5 (분리된 리뷰 세션)
- **Reviewed at**: 2026-07-08
- **Review evidence**: 조건부 통과(HIGH 1건 포함 지적 9건 — 반영 8건·게이트 확인 1건) —
  (1) Tach 계약을 "명시적 dependency edge + services-only interface"로 정정해 양성/음성
  테스트 충돌 제거, (2) **HIGH**: 미등록 앱이 Tach 경계 밖으로 빠짐 — **재현 실험으로
  확인**(기본 설정에서 미등록 앱의 내부 import 통과). `root_module="forbid"` + 등록 대조
  테스트로 봉쇄(R-BC-4); "또는" 처방은 불충분 — forbid만으로는 미등록 앱 간 상호
  import를 못 잡음을 실험으로 확인해 **둘 다** 필수로 강화, (3) CI required status
  check가 저장소 파일 밖 GitHub 설정임을 명시하고 tasks 완료 증거 대상으로 분리,
  (4) required check 과신 — 위협 모델을 실수 삭제(repo-local CI 계약 테스트)와 의도적
  변조(워크플로 리뷰 게이트, 설정 증거)로 분리해 C-5로 계약화, (5) 차단 범위 표현을
  등록된 정적 import 경계로 한정, (6) SC-003 "픽스처 모델 0"을 코드 리뷰에서
  `test_fixture_scope.py` 기계 검증으로 전환, (7) 픽스처 primitive 불변식을 정의/사용
  분리로 정정(정의 금지 유지, 커널이 채워진 후 사용 허용), (8) spec/checklist 승인 상태
  불일치 정리, (9) 승인 게이트 확인: 아래 체크박스는 사람 전용(원칙 XIX) — 승인 전
  tasks 진행 금지 유지.
- **Approval** (final approver MUST be a human — Principle XIX): [x] Approved to proceed to tasks — _(cray.j, 2026-07-08)_
