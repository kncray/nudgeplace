# Feature Specification: Foundation — Structure & Boundaries

**Feature Branch**: `000-foundation-structure`

**Phase**: 0 — Foundation | **Spec Sequence**: 000 (Foundation Step 1 / 2)

**Created**: 2026-07-08

**Status**: Approved <!-- Draft → In Review → Approved -->

**Input**: 로드맵 Phase 0(Foundation)을 학습 단위로 2개 스펙으로 분할한 첫 번째
스펙. 이 스펙은 **프로젝트 구조와 기계적 도메인 경계, 그리고 문서(ADR·소유 규칙)**에
한정한다. 공유 커널 primitive(Money·이벤트·멱등·감사·역할)는 Spec 001로, ACL 골격은
P6로 이관(슬림화)하며, 도메인 계층 관통 실증은 P1 첫 도메인 기능이 겸한다.

## Review & Approval *(mandatory before plan)*

<!--
  Constitution Governance ("승인 주체"): approval means an adversarial review by a
  session/model SEPARATE from the author, with the result recorded here, followed
  by explicit approval. Self-approval within the same session does not satisfy this.
-->

- **Reviewer** (separate session/model — Fable 5, GPT-5.5): 별도 세션 적대적 리뷰 에이전트(분리된 컨텍스트)
- **Reviewed at**: 2026-07-08
- **Review evidence**: 조건부 통과(HIGH 0건). 지적 9건(MEDIUM 5·LOW 4)을 반영 —
  (1) 문서는 빈 골격을 선제 생성하지 않고 소유 규칙만 ADR로 확립(state-model·
  glossary 파일은 첫 상태/도메인 기능이 생성), (2) FR-002의 ID 참조를 SHOULD 규약
  으로 분리하고 실증은 P1로, (3) 픽스처 앱을 도메인 계층으로 등록해 빈 커널 역의존
  메타테스트가 vacuous하지 않게 명시, (4) SC-003을 측정 가능 형태(모델·심볼 수 0,
  개방 열거 없음)로 재기술, (5) 로드맵의 "첫날부터 MUST" 서술 완화, (6) FR-002·
  SC-001의 "기계적 강제"를 정적 import 경계로 한정하고 우회 경로(동적 모델 조회·
  문자열 FK·raw SQL)의 취급(규약·리뷰, P1에서 추가 검사 판단)을 명시, (7) 경계
  검사의 CI 무성 미실행(silent skip)을 FR-003 필수 실행 요건과 Edge Case로 추가,
  (8) FR-007에 경계 검사 RED의 의미 부연. (반영은 리뷰어 권고 remedy의 기계적
  적용으로 새 설계 도입 없음.)
- **Approval** (final approver MUST be a human — Principle XIX): [x] Approved for planning — _(cray.j, 2026-07-08)_

## Business Context *(mandatory)*

**학습 목표 (프로젝트 맥락)**: Nudgeplace는 잘 알려진 커머스 패턴을 기반으로 실제
운영 가능한 멀티벤더 커머스 플랫폼을 **한 단계씩(step-by-step) 구축하며 학습**하는
프로젝트다(원칙 XVIII: 저장소는 프로덕션 소프트웨어인 동시에 장기 학습 자료).
따라서 각 단계는 "실행 가능한 최소 슬라이스"로 유지하고 과잉 구현을 피한다.
Foundation(Phase 0)은 이 원칙에 따라 두 개의 학습 단계(Step)로 나눈다:

- **Step 1 (Spec 000, 이 스펙) — 구조·경계**: 모듈러 모놀리스 골격과 기계적 도메인 경계, 문서 소유 규칙(ADR).
- **Step 2 (Spec 001) — 공유 커널 primitive**: Money·도메인 이벤트 계약·멱등키·감사·행위자 역할(커널 내부 관통 검증 포함).

별도의 walking-skeleton 단계는 두지 않는다 — 도메인 계층에서의 primitive 관통
실증은 P1 첫 도메인 기능이 겸한다(로드맵 "관통 실증의 배치").

**왜 구조·경계가 먼저인가**: 도메인 경계가 기계적으로 강제되지 않으면 "모듈화된"
모놀리스가 강결합 모놀리스로 퇴화한다(원칙 VIII). 이 규율은 이후 모든 Phase(그리고
Spec 001 자신)가 그 위에 놓이는 토대이므로, 어떤 primitive나 도메인보다 먼저
서야 한다. 이 단계의 수혜자는 최종 소비자·벤더·운영자가 아니라, 이 골격 위에
primitive와 도메인을 올리는 **개발자·유지보수자**와 경계를 강제하는 **CI·거버넌스**다.

**영향 도메인**: 없음(도메인 없음). 이 기능은 모든 미래 primitive·도메인이 놓일
앱 구조와 경계 규율, 그리고 문서 단일 출처의 소유 규칙을 확립한다(원칙 VII·VIII·XVIII·XX).

**이 스펙의 성격**: 이것은 커머스 **도메인 모델**도, 완성된 **공유 커널**도
아니다. 여기서 확립하는 것은 (1) Django 모듈러 모놀리스 **구조**, (2) 기계적으로
강제되는 **도메인 경계**와 공개 서비스 인터페이스 패턴, (3) primitive가 채워질
**공유 커널 패키지의 위치와 단방향 의존 규율**(내용물인 Money 등은 Spec 001), (4) 문서
소유 규칙(핵심 결정 ADR + 상태모델·용어집의 정식 경로·소유 규칙)이다. "공유 커널"은 DDD의 bounded context 간 공유 *도메인 모델*이 아니라 이
프로젝트 내부의 플랫폼 기반 용어다(Spec 001에서 그 내용을 채운다). 실제 도메인 불변식·
primitive·외부 연동은 이 스펙 범위 밖이다.

## Domain Concepts *(mandatory)*

- **도메인 경계 (Domain Boundary)**: 각 비즈니스 도메인이 자신의 데이터·규칙을
  배타적으로 소유하고 다른 도메인의 내부에 직접 접근하지 못하도록 하는 선.
  관례가 아니라 기계적으로 강제된다(원칙 VIII).
- **공개 서비스 인터페이스 (Public Service Interface)**: 한 도메인/모듈이 외부에
  노출하는 유일한 진입점. 도메인 간 호출은 이를 통해서만 이루어지고, 참조는
  기본적으로 식별자(ID)로 한다.
- **공유 커널 패키지 (Shared Kernel Package)**: 특정 도메인에 속하지 않고 모든
  도메인이 의존할 횡단 위치. 이 스펙은 그 **위치와 단방향 의존 규율**만 세우며,
  내용(Money·이벤트·멱등·감사·역할)은 Spec 001에서 채운다. *(DDD의 bounded-context
  공유 도메인 모델이 아니라 스펙 내부 용어.)*
- **경계 적합성 픽스처 (Boundary Conformance Fixture)**: 경계 강제가 실제로
  작동함을 시험하기 위한 최소 샘플 앱 한 쌍. **도메인 모델도 커널 primitive도
  담지 않으며**, 오직 경계 검사(허용/차단)를 시험할 목적의 자명한 공개 인터페이스만
  갖는다. (커널이 채워진 뒤에는 픽스처가 primitive를 사용할 수 있고, 도메인 계층
  관통 실증은 P1 첫 도메인 기능이 수행한다.)
- **문서 소유 규칙 (Documentation Ownership)**: 이후 모든 Phase가 참조·확장할
  단일 출처의 규칙 — 핵심 결정은 ADR로 기록하고, 표준 상태 모델·용어집의 정식
  경로와 "첫 상태/도메인 도입 기능이 최초 생성한다"는 소유 규칙을 확립한다(빈
  문서를 선제 생성하지 않음).

## Business Rules *(mandatory)*

- **BR-1**: 도메인 경계를 위반하는 코드(다른 도메인/모듈 내부에 직접 접근하는
  import)는 병합되어서는 안 되며, 위반은 **기계적으로 차단**된다(원칙 VIII).
- **BR-2**: 도메인 간 호출은 공개 서비스 인터페이스를 통해서만 이루어지고, 참조는
  기본적으로 ID로 한다. 다른 도메인 모델에 대한 직접 FK는 지양한다(원칙 VIII).
- **BR-3**: 공유 커널 패키지는 **단방향 의존**을 가진다 — 도메인은 커널에
  의존할 수 있으나 커널이 도메인에 역의존해서는 안 되며, 이 역시 기계적으로
  강제된다(원칙 VIII). 커널의 *내용물*은 이 스펙 범위 밖(Spec 001)이다.
- **BR-4**: 이 기능은 어떤 실제 도메인(벤더·카탈로그·주문 등)의 데이터·규칙도,
  어떤 커널 primitive(Money·이벤트·멱등·감사·역할)도 구현하지 않는다. 경계 적합성
  픽스처는 도메인 모델과 primitive를 포함해서는 안 된다.
- **BR-5**: 표준 상태 모델(`docs/domain/state-model.md`)과 용어집
  (`docs/domain/glossary.md`)은 **이 단계에서 선제 생성하지 않는다** — 거버넌스상
  state-model은 첫 상태를 도입하는 기능이, glossary는 첫 도메인 용어가 생기는
  기능이 최초 생성한다. 이 스펙은 이들의 정식 경로와 소유 규칙만 ADR로 확립한다
  (거버넌스 표준 상태 모델, 원칙 XX).

## User Scenarios & Testing *(mandatory)*

> 이 단계의 "사용자"는 이 골격 위에 primitive·도메인을 올리는 **개발자·
> 유지보수자**와 경계를 강제하는 **CI·거버넌스**다.

### User Story 1 - 도메인 경계가 기계적으로 강제된다 (Priority: P1)

개발자가 한 도메인/모듈에서 다른 도메인의 내부 모듈을 직접 import하거나, 공유
커널이 도메인에 역의존하는 코드를 작성하면, 빌드/CI가 그 위반을 감지해 실패시킨다.
개발자는 공개 서비스 인터페이스를 통해서만 도메인 간 호출을 할 수 있다.

**Why this priority**: 경계 강제가 없으면 모듈러 모놀리스가 강결합으로 퇴화하며,
이는 이후 모든 Phase의 지속 가능성을 좌우한다(원칙 VIII). Foundation의 첫 단계로
반드시 서야 한다.

**Independent Test**: 경계를 위반하는 import를 추가한 커밋으로 CI를 돌리면 빌드가
실패하고, 위반을 제거하면 통과함을 확인할 수 있다. 다른 어떤 primitive 없이도
단독으로 가치를 전달한다.

**Acceptance Scenarios**:

1. **Given** 경계 적합성 픽스처(앱 A·B)와 정의된 경계 계약, **When** 앱 A가 앱 B의
   내부 모듈을 직접 import, **Then** CI 경계 검사가 실패한다.
2. **Given** 동일 설정, **When** 앱 A가 앱 B의 공개 서비스 인터페이스만 호출,
   **Then** 경계 검사가 통과한다.
3. **Given** 경계 계약에서 픽스처 앱 A·B가 도메인(`apps`) 계층으로 등록됨,
   **When** 빈 공유 커널이 픽스처 앱(도메인 계층)을 import하는 알려진 위반을 추가,
   **Then** 경계 검사가 실패한다(커널 단방향 의존이 vacuous하지 않음을 실증).
4. **Given** 경계 검사 자체, **When** 알려진 위반 샘플로 검사를 시험, **Then**
   검사가 그 위반을 실제로 잡는다(거짓 통과 방지 메타 테스트).

---

### User Story 2 - 핵심 아키텍처 결정과 문서 소유 규칙이 기록된다 (Priority: P2)

유지보수자가 저장소를 열면, 이 단계의 핵심 아키텍처 결정(모듈러 모놀리스 채택·
경계 강제·커널 단방향 의존)이 ADR로 남아 있고, 표준 상태 모델·용어집의 정식
경로와 "누가 언제 최초 생성하는지"(첫 상태/도메인 도입 기능)가 함께 기록되어
이후 스펙이 그 규칙대로 문서를 키울 수 있다.

**Why this priority**: 문서는 이후 모든 Phase가 참조하는 단일 출처의 시작점이다
(원칙 XVIII·XX, 거버넌스 표준 상태 모델). 다만 내용 없는 거버넌스 문서를 선제
생성하지 않고 **소유 규칙만** 확립한다(거버넌스: state-model은 첫 상태 도입
기능이 생성). 구조·경계(US1)가 먼저이므로 P2.

**Independent Test**: `docs/adr/`에 결정 ADR과 state-model·glossary의 정식 경로·
소유 규칙이 존재하고, `docs/domain/` 디렉터리 존재 여부와 무관하게
`docs/domain/state-model.md`와 `docs/domain/glossary.md` 파일이 선제 생성되지
않았음을 확인할 수 있다.

**Acceptance Scenarios**:

1. **Given** 저장소, **When** `docs/adr/`를 열람, **Then** 모듈러 모놀리스 채택·
   경계 강제·커널 단방향 의존 결정 ADR과 state-model·glossary의 정식 경로·소유
   규칙이 존재한다(근거·대안·트레이드오프 포함).
2. **Given** 저장소, **When** `docs/domain/` 경로를 확인, **Then** 디렉터리 존재
   여부와 무관하게 도메인 상태·용어를 담은 `state-model.md`·`glossary.md` 파일이
   아직 선제 생성되지 않았다(첫 상태/도메인 기능이 생성).

---

### Edge Cases

- 경계 검사가 **거짓 통과**(위반을 놓침)하면? → US1 시나리오 4의 메타 테스트가
  검사 자체의 유효성을 시험한다.
- 경계 검사 잡이 CI에서 **아예 실행되지 않으면**(무성 미실행, silent skip —
  잡 누락·optional 처리 등)? → FR-003이 검사를 생략 불가능한 필수 단계로
  요구한다. 경계 강제의 실제 실패 모드는 "검사가 틀림"보다 "검사가 안 돎"이
  더 흔하다.
- 커널이 도메인에 역의존하면? → US1 시나리오 3이 실패로 처리.
- 경계 적합성 픽스처가 실수로 primitive나 도메인 모델을 끌어들이면? → SC-003이
  이를 0으로 강제(도메인·primitive 선점 금지).
- `state-model`에 도메인 상태를 성급히 적으면? → SC-004가 선점 상태 수 0을 강제.

## Architectural Considerations *(mandatory)*

- **Domain ownership** (Principle VII/VIII): 비즈니스 도메인 없음. 이 기능이 앱
  구조(`apps/<domain>/`)와 경계 규율, 공유 커널 패키지의 **위치와 단방향 의존**을
  세운다(내용물은 Spec 001). 결정은 ADR로 기록.
- **Cross-domain interfaces** (Principle VIII): 이 기능이 **공개 서비스 인터페이스
  패턴**과 ID 기반 참조 규약을 정의하고, 경계 적합성 픽스처가 이를 실증한다. 직접
  FK 없음.
- **Money & correctness** (Principle V): N/A — Money 타입은 Spec 001.
- **Domain events** (Principle XII): N/A — 이벤트 계약은 Spec 001.
- **Idempotency & delivery** (Principle XIII): N/A — 멱등키는 Spec 001. (아웃박스·비동기
  신뢰 전달은 P12.)
- **External systems** (Principle IX): N/A — **ACL 골격은 P0에서 슬림 제거,
  첫 소비자 P6에서 최초 확립.** 이 스펙은 외부 시스템을 다루지 않는다.
- **Vendor isolation** (Principle VI): N/A — 행위자 역할 스캐폴딩은 Spec 001, 실제
  벤더 격리는 P1.
- **Audit trail** (Principle XV-감사): N/A — 감사 primitive는 Spec 001. (이 스펙은
  비즈니스 상태를 바꾸지 않는다.)
- **Immutable snapshots / PII / Promotion / Reverse flows / Operator intervention /
  Vendor lifecycle / Reconciliation / Observability / In-flight reservations /
  Forward exposure** (Principles IV·X·XI·VI·III·XV-대사·XVI·XIV): N/A — 해당
  도메인·연동 없음(각 도입 Phase에서).
- **Evidence & legacy** (Principle XVII): N/A — 레거시 로직 재사용 없음(그린필드
  구조).
- **Standard state model** (Governance): 이 기능은 `state-model.md`를 선제
  생성하지 않는다. 거버넌스대로 **첫 상태를 도입하는 기능(P1~)이 최초 생성**하며,
  이 스펙은 그 정식 경로·소유 규칙만 ADR로 확립한다.
- **Schema & contract evolution** (Principle IV / constraints): N/A — 이 스펙은
  이벤트·스냅샷을 만들지 않는다(이벤트 버저닝은 Spec 001, 스냅샷은 P5).
- **Scope boundaries** (Governance / range constraint): **명시적 범위 밖** —
  (1) 공유 커널 primitive: Money·도메인 이벤트 계약·멱등키·감사·행위자 역할 → **Spec 001**;
  (2) 도메인 계층에서의 primitive 관통 실증 → **P1 첫 도메인 기능**;
  (3) ACL 골격·외부 어댑터 → **P6**(P0에서 슬림 제거);
  (4) 모든 실제 비즈니스 도메인(벤더·카탈로그·재고·장바구니·주문·결제·이행·
  프로모션·역방향·정산·벤더 생명주기) → **P1~P11**.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 각 비즈니스 도메인을 독립된 앱으로 담을 수 있는 Django
  모듈러 모놀리스 구조와 설정 계층을 제공해야 한다(MUST).
- **FR-002**: 시스템은 도메인이 외부에 노출하는 **공개 서비스 인터페이스** 패턴을
  제공하고, 도메인 간 호출이 이 인터페이스를 통해서만 이루어지도록 해야 한다
  (MUST). 이 요구의 **기계적 강제 범위는 정적 import 경계**다 — 다른 도메인 내부
  모듈을 import하는 경로는 기계적으로 차단된다(MUST). 정적 import를 우회하는
  접근(동적 모델 조회, 문자열 참조 FK, raw SQL 등)은 이 스펙의 기계 강제 범위
  밖이며, 도메인 간 참조를 기본적으로 식별자(ID)로 하고 직접 FK를 지양하는
  **규약**(SHOULD, 원칙 VIII)과 리뷰로 다룬다; 규약의 실증과 우회 경로에 대한
  추가 검사 도입 여부는 실제 도메인 간 참조가 처음 생기는 Phase 1에서 판단한다
  (이 스펙엔 참조할 도메인 모델이 없음).
- **FR-003**: 시스템은 도메인 경계 위반(다른 도메인 내부 직접 접근)을 **기계적으로
  감지해 빌드/CI를 실패**시켜야 한다(MUST). 경계 검사는 알려진 위반 샘플을 실제로
  잡음이 메타 테스트로 검증되어야 한다(MUST). 또한 경계 검사는 CI에서 **생략
  불가능한 필수 단계**로 실행되어야 하며, 검사가 실행되지 않은 빌드가 통과로
  처리되어서는 안 된다(MUST) — 구체 강제 수단(필수 상태 검사 등)은 plan에서 정한다.
- **FR-004**: 시스템은 primitive가 채워질 **공유 커널 패키지의 위치**를 세우고,
  도메인→커널 단방향 의존(커널→도메인 역의존 금지)을 **기계적으로 강제**해야
  한다(MUST). 커널의 내용물은 이 스펙 범위 밖(Spec 001)이다.
- **FR-005**: 시스템은 경계 강제를 시험하기 위한 **최소 경계 적합성 픽스처**(샘플
  앱 A·B)를 제공해야 하며, 이 픽스처는 **도메인 모델과 커널 primitive를 포함해서는
  안 된다(MUST NOT)** — 오직 자명한 공개 서비스 인터페이스만 갖는다. 경계 계약에서
  이 픽스처 앱은 도메인(`apps`) 계층으로 등록되어, 커널 단방향 의존(FR-004) 메타
  테스트의 대상이 된다(빈 커널에서도 역의존 규칙이 vacuous하지 않게).
- **FR-006**: 시스템(저장소)은 `docs/adr/`와 이 단계의 핵심 결정 ADR(모듈러
  모놀리스 채택·경계 강제·커널 단방향 의존; 근거·대안·트레이드오프 포함)을 포함해야
  한다(MUST, 원칙 XX). 이 ADR은 `docs/domain/glossary.md`와
  `docs/domain/state-model.md`의 **정식 경로와 소유 규칙**(각 문서는 첫 도메인 용어/
  상태를 도입하는 기능이 최초 생성)도 함께 기록한다. **이 단계에서 glossary·
  state-model 파일 자체를 선제 생성하지 않는다(MUST NOT)** — 거버넌스상 state-model은
  첫 상태 도입 기능이, glossary는 첫 도메인 용어가 생기는 기능(P1)이 최초 생성한다.
- **FR-007**: 관찰 가능한 동작(경계 검사·경계 메타 테스트·공개 인터페이스 경유
  호출)은 구현 전에 실패하는 테스트(RED)를 먼저 갖추고 구현으로 통과(GREEN)시켜야
  한다(MUST, 원칙 I·XVII). 경계 검사처럼 구성(configuration)이 곧 구현인 항목의
  RED는 "알려진 위반 샘플이 아직 차단되지 않는 상태"의 메타 테스트 실패를
  의미한다. 순수 스캐폴딩(디렉터리 구조·설정·라우팅 골격 등 관찰
  가능한 동작이 없는 작업)만 예외.

### Key Entities *(include if feature involves data)*

- **도메인 경계 계약 (Boundary Contract)**: 어떤 모듈이 어떤 모듈을 import할 수
  있는지 규정하는 기계 강제 규칙 집합.
- **공개 서비스 인터페이스 (Public Service Interface)**: 도메인의 유일한 외부
  진입점.
- **공유 커널 패키지 (Shared Kernel Package)**: 단방향 의존이 강제되는 횡단 위치
  (내용은 Spec 001).
- **경계 적합성 픽스처 앱 A/B**: 도메인·primitive를 담지 않는, 경계 검사 시험용
  최소 샘플 앱.
- **문서 산출물**: ADR(핵심 결정 + 상태모델·용어집의 정식 경로·소유 규칙 기록).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **경계 계약에 등록된 규칙을 위반하는 정적 import**를 포함한 커밋은
  CI에서 차단되고, 위반을 제거한 커밋은 통과한다. 검사가 위반을 실제로 잡는다는
  사실은 알려진 위반 샘플 기반 메타 테스트로 검증한다(거짓 통과 방지). *(보장
  범위는 FR-002가 한정한 정적 import 경계다 — 우회 경로는 규약·리뷰 소관.)*
- **SC-002**: 경계 계약에서 픽스처 앱을 도메인 계층으로 등록하고, 빈 커널이 픽스처
  앱을 import하는 알려진 위반이 **기계적으로 차단**됨을 메타 테스트로 확인한다
  (역의존 계약이 vacuous하지 않음).
- **SC-003**: 경계 적합성 픽스처 앱에 정의된 데이터 모델(`models.py` 엔티티) 수가
  **0**이고, 공유 커널 패키지가 노출하는 public symbol이 **0개**다(빈 위치 —
  Money·이벤트·멱등·감사·역할 primitive는 Spec 001에서 채운다).
- **SC-004**: `docs/adr/`에 이 단계의 결정 ADR과 state-model·glossary 소유 규칙이
  존재하고, `docs/domain/` 디렉터리 존재 여부와 무관하게 `state-model.md`와
  `glossary.md` 파일이 **선제 생성되지 않았다**(첫 상태/도메인 기능이 생성).
- **SC-005**: 픽스처의 도메인 간 호출이 공개 서비스 인터페이스만 경유하며 내부
  모듈 직접 import이 **0건**이다.

## Assumptions

- **경계 강제 도구**: 헌장이 예시한 import-linter 계열의 정적 계약 검사로 경계를
  강제하고 CI가 이를 실행한다고 가정한다(구체 도구·CI 플랫폼 선택은 plan.md).
- **경계 적합성 픽스처의 수명**: 픽스처 앱은 도메인·primitive를 담지 않는 아키텍처
  적합성 스모크 테스트로 유지한다. 커널이 채워진 뒤(Spec 001~) 픽스처는 primitive를
  **사용**할 수 있으나 실제 도메인 모델은 여전히 넣지 않는다.
- **저장소**: 이 스펙 단계에는 primitive(멱등·감사)가 없으므로 특정 저장소를
  전제하지 않는다(저장소 선택은 Spec 001/plan.md).
- **구체 언어/프레임워크 버전·테스트 도구**는 plan.md의 Technical Context에서
  결정하며, 헌장의 Django 모듈러 모놀리스 제약과 모순되지 않는다.
- **후속 Foundation 스펙**: Spec 001(공유 커널 primitive — Money·이벤트·멱등·감사·
  역할)은 이 스펙 완료 후 `/speckit-specify`로 작성한다. Foundation은 그것으로
  완료되며, 도메인 계층 관통 실증은 P1 첫 도메인 기능이 겸한다.
