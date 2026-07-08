# Phase 1 Data Model: Foundation — Structure & Boundaries

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-08

## 영속 도메인 엔티티: 없음 (0)

이 스펙은 어떤 비즈니스 도메인 데이터도 모델링하지 않는다. 이는 절제가 아니라 **강제
요건**이다:

- **SC-003**: 경계 적합성 픽스처 앱의 `models.py` 엔티티 수 = **0**, 공유 커널의
  public symbol = **0**.
- **BR-4**: 실제 도메인·커널 primitive를 구현하지 않는다.
- **Storage**: N/A — DB 테이블·마이그레이션을 만들지 않는다. 저장소 선택은 Spec 001/이후.

따라서 아래는 데이터베이스 엔티티가 아니라, 이 스펙이 확립하는 **구조적 개념(structural
concepts)** 이다(spec의 Key Entities에 대응). 영속화되지 않으며 코드·구성·문서로 존재한다.

## 구조적 개념 (structural concepts)

### 1. 도메인 경계 계약 (Boundary Contract)
- **형태**: `tach.toml`의 명시적 모듈 의존 edge + `[[interfaces]]` 선언 (기계 강제 규칙 집합).
- **불변식**:
  - 도메인 앱은 다른 도메인 앱의 내부 모듈을 import할 수 없다(공개 표면만 허용).
  - `shared_kernel ← apps` 단방향 — 커널은 어떤 도메인 앱도 import하지 않는다(BR-3).
  - **모든 `apps/*` 패키지는 계약에 모듈로 등록된다**(R-BC-4) — 미등록 코드는
    `root_module = "forbid"` + 등록 대조 테스트로 차단되어, 미래 도메인 앱이 경계
    밖으로 빠질 수 없다.
- **검증**: `tach check`(허용/차단) + 거짓-통과 방지 메타 테스트(US1 #4) + 모듈 등록
  대조 테스트(R-BC-4).
- **계약 상세**: [contracts/boundary-contract.md](./contracts/boundary-contract.md).

### 2. 공개 서비스 인터페이스 (Public Service Interface)
- **형태**: 각 앱의 `services` 모듈(향후 `events` 추가). 도메인의 **유일한 외부 진입점**.
- **불변식**: cross-app 참조는 명시된 dependency edge 안에서만 가능하고,
  `apps.<domain>.services`만 허용한다. `models`·내부 모듈은 금지. 참조는 기본적으로
  ID(직접 FK 지양, SHOULD — 실증은 P1).
- **검증**: `tests/conformance/test_public_interface.py`(SC-005: 내부 직접 import 0건).
- **계약 상세**: [contracts/public-service-interface.md](./contracts/public-service-interface.md).

### 3. 공유 커널 패키지 (Shared Kernel Package)
- **형태**: `shared_kernel/` 패키지 — **빈 위치**(public symbol 0). 내용물(Money·이벤트·
  멱등·감사·역할)은 Spec 001.
- **불변식**: 단방향 의존(도메인→커널 허용, 커널→도메인 금지).
- **검증**: 커널이 픽스처 앱(도메인 계층)을 import하는 알려진 위반이 차단됨(SC-002).

### 4. 경계 적합성 픽스처 앱 A/B (Boundary Conformance Fixture)
- **형태**: `apps/conformance_a`·`apps/conformance_b` — 자명한 `services`를 갖는 최소
  앱. B는 경계 테스트의 내부 모듈 위반-샘플 표적인 `internal.py`(비공개, 공개 표면
  아님)를 추가로 갖는다.
- **양성(허용) 사례**: `conformance_a → conformance_b.services` 단방향 호출이 경계
  계약에 선언된 유일한 도메인 간 edge다(허용 경로가 실제로 통과함을 실증).
- **불변식(정의/사용 분리)**: 픽스처 앱은 도메인 모델과 primitive를 **정의하지
  않는다**(정의 0 — SC-003, `test_fixture_scope.py`로 기계 검증). `apps`(도메인)
  계층으로 등록되어 커널 단방향 계약의 대상이 된다(FR-005 — 빈 커널에서도 역의존
  규칙이 vacuous하지 않게).
- **수명**: 커널이 채워진 뒤(Spec 001~) 픽스처는 `shared_kernel` primitive를
  **사용**할 수 있다 — 모델·primitive **정의** 금지는 그대로 유지된다(불변식과
  충돌 없음). 도메인 계층 관통 실증은 P1 첫 도메인 기능이 수행한다.

### 5. 문서 산출물 (ADR)
- **형태**: `docs/adr/0001~0003` — 모듈러 모놀리스 채택 / 경계 기계 강제(Tach) / 커널
  단방향. 근거·대안·트레이드오프 포함(원칙 XX). state-model·glossary의 정식 경로·소유
  규칙을 ADR 0002에 기록.
- **불변식(MUST NOT)**: `docs/domain/state-model.md`·`glossary.md`를 **선제 생성하지
  않는다**(BR-5, SC-004) — 첫 상태/도메인 도입 기능이 최초 생성(로드맵상 P1).

## 상태 전이

해당 없음 — 이 스펙에는 상태 머신을 갖는 도메인 개념이 없다(벤더/주문/결제/배송
상태는 각 도입 Phase에서). 표준 상태 모델 문서는 이 스펙에서 생성하지 않고 **소유
규칙만** 확립한다.
