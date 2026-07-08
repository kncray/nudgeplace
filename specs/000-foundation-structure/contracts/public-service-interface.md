# Contract: 공개 서비스 인터페이스 (Public Service Interface)

**Spec**: [../spec.md](../spec.md) | **Date**: 2026-07-08

각 도메인 앱이 **다른 도메인에게 노출하는 유일한 진입점**의 규약이다. 이후 모든 실제
도메인(P1~)이 이 패턴을 상속한다.

## 규약

1. **P-SI-1**: 각 앱은 자신의 공개 진입점을 **`apps.<domain>.services`** 모듈로 노출한다.
   (도메인 이벤트가 생기면 `apps.<domain>.events`도 공개 표면에 추가된다 — Spec 001/이후.)
2. **P-SI-2**: 다른 앱은 `tach.toml`에 명시된 dependency edge가 있을 때만 호출할 수 있고,
   그 경우에도 오직 `services`(및 `events`)만 import·호출한다. `models`·`internal`·
   기타 모듈로의 cross-app 접근은 금지된다(경계 계약 R-BC-1이 기계 강제).
3. **P-SI-3**: `services`가 노출하는 함수/타입은 다른 도메인의 ORM 모델 인스턴스가 아니라
   **식별자(ID)·값(DTO)** 을 주고받는 것을 기본으로 한다(직접 FK 지양, SHOULD). 이
   규약의 실증은 실제 도메인 간 참조가 처음 생기는 P1.

## 이 스펙에서의 형태 (픽스처)

- `apps/conformance_a/services.py`, `apps/conformance_b/services.py`는 **자명한** 공개
  함수 하나 수준으로 유지한다(도메인 로직·모델 없음, BR-4).
- 호출 방향은 `conformance_a → conformance_b.services` — 경계 계약에 선언된 유일한
  도메인 간 edge다(양성 사례).
- 목적은 "경계 검사가 허용/차단을 올바로 판정하는지"를 시험하는 것이지 도메인 기능이
  아니다. Spec 002의 walking skeleton이 이 인터페이스를 확장한다.

## 수용 기준 (spec 매핑)

| ID | 시나리오 | 기대 | spec 근거 |
|---|---|---|---|
| AC-SI-1 | 명시적 A→B dependency 아래 앱 A가 앱 B의 `services` 함수 호출 | 정상 동작, 경계 검사 통과 | US1 #2 |
| AC-SI-2 | 픽스처의 cross-app 내부 직접 import 건수 | **0건** | SC-005 |
| AC-SI-3 | `services` 외 모듈(예: `models`) cross-app import 시도 | 경계 검사 **실패** | US1 #1, R-BC-1 |
