# Quickstart 실행 증거 — Spec 001 (Foundation: Shared Kernel Primitives)

**Date**: 2026-07-10 | **Branch**: `001-shared-kernel-primitives` | **원칙 XVII 근거 기록**

quickstart.md 시나리오 1~11의 실제 실행 결과와 각 t-테스트의 RED→GREEN 증거,
Success Criteria 대조를 남긴다. 완료·통과 주장은 실제 실행 관측으로 뒷받침한다.

## 환경

- Python 3.12, Django 5.2, psycopg 3.3, PostgreSQL 16 (docker compose, healthy)
- `uv run python manage.py migrate` → `0001_idempotency`, `0002_audit`(append-only
  트리거 포함) 적용 OK (프로젝트 최초 마이그레이션).

## RED→GREEN 증거 (test-first, 원칙 I·XVII·FR-009)

각 t-테스트는 target 구현 전 **옳은 이유의 RED**(미구현 모듈 ImportError·미충족
단언)를 관측한 뒤 구현으로 GREEN 전환했다. 순수 스캐폴딩(T001~T004)만 예외.

| 테스트 | RED 관측(구현 전) | GREEN(구현 후) |
|---|---|---|
| T005t (CI 계약) | `AssertionError: quality-gate 잡에 postgres 서비스 부재` 외 1건 (기존 6건 불변 통과) | 8 passed |
| T010t (correlation) | `ModuleNotFoundError: shared_kernel.correlation` | 6 passed |
| T020t·T021t (money) | `ModuleNotFoundError: shared_kernel.money` | 40 passed |
| T030t (events) | `ModuleNotFoundError: shared_kernel.events` | 14 passed |
| T040t (idempotency) | `ModuleNotFoundError: shared_kernel.idempotency` | 22 passed |
| T050t·T051t (actors·audit) | `ModuleNotFoundError: shared_kernel.actors` | 18 passed |
| T060t (관통 통합) | 의존 primitive(US2·3·4)가 이미 GREEN — 통합 케이스는 그 조합을 실증(작성 시 GREEN, 정직한 한정) | 8 passed |
| T070t (공개 표면) | `AttributeError: module 'shared_kernel' has no attribute '__all__'` (3 failed / 검증④는 이미 통과 — models.py 애그리게이터로 신규 프로세스 모델 발견됨, BLOCKER 방어 독립 확인) | 4 passed |

## 시나리오 실행 결과

| 시나리오 | 명령 | 결과 |
|---|---|---|
| 1·2 Money 표현·연산·반올림 | `pytest tests/kernel/test_money.py` | **24 passed** |
| 3 안분(합계 보존·끝전) | `pytest tests/kernel/test_money_allocation.py` | **16 passed** |
| 4 이벤트 봉투·디스패치 | `pytest tests/kernel/test_events.py` | **14 passed** |
| 5·6 멱등(재시도·동시성·고착·불확정) | `pytest tests/kernel/test_idempotency.py` | **22 passed** |
| 7 감사 사실(필수·불변·원자성) | `pytest tests/kernel/test_audit.py` | **15 passed** |
| 8 행위자 역할 | `pytest tests/kernel/test_actors.py` | **3 passed** |
| 9 관통 추적 | `pytest tests/kernel/test_correlation.py` | **8 passed** |
| 10 공개 표면·경계 | `pytest tests/kernel/test_public_surface.py tests/conformance/ tests/boundary/` | **31 passed** |
| 11 전체 게이트 | `tach check && ruff check . && pytest` | tach ✅ / ruff ✅ / **147 passed** |

## Success Criteria 대조

| SC | 내용 | 검증(시나리오/테스트) | 상태 |
|---|---|---|---|
| SC-001 | 결정론(반올림·안분 포함) | 1·2·3 — 반복 단언(`test_arithmetic_is_deterministic`, `test_allocation_is_deterministic_on_repeat`) | ✅ |
| SC-002 | 내부 부동소수점 0 | 1·3 — money.py AST 검사(float 리터럴·`float()`·`/` 0건) + 2^60 정확성 | ✅ |
| SC-003 | 봉투 완전성 | 4 — 필수 필드 누락 발행 거부 | ✅ |
| SC-004 | 멱등(동시·스코프) | 5·6 — 스레드 경합 + DB-backed 효과 정확히 1회 | ✅ |
| SC-005 | 감사 불변·완결 | 7 — 모델 계층 + DB 트리거 raw SQL 거부 | ✅ |
| SC-006 | 커널 순수성·공개 표면 | 10 — `__all__` 계약 일치 + tach 경계 불변 | ✅ |
| SC-007 | 관통 추적 | 9 — 세 기록 같은 correlation 연결 | ✅ |
| SC-008 | 합계 보존 | 3 — 다수 입력 몫 합 − 원금 = 0 | ✅ |

## 한정 (정직한 기록)

- **CI `quality-gate`(postgres 서비스)** 는 GitHub Actions에서 PR 시 실행된다 —
  로컬에서는 동일 명령(시나리오 11: tach·ruff·pytest)으로 대표 검증했고 전부
  통과했다. CI 계약 테스트(`test_ci_contract.py`)가 워크플로에 postgres 서비스·
  `POSTGRES_*` env가 존재함을 기계 단언한다.
- 감사 DB 트리거의 방어는 raw SQL UPDATE/DELETE까지다 — DB 슈퍼유저의 트리거
  제거·DDL은 방어 밖이며, 권한 분리는 go-live 전 운영 DB 구성의 몫이다(R5, 헌장 VI).
- 멱등 프로토콜의 operation은 순수 내부(트랜잭션 내)로 한정된다 — 외부 부수 효과
  흐름은 P6+가 이 프로토콜을 확장한다(contracts/idempotency-protocol.md).

## 적대 리뷰 2차(Codex) 반영 (R2 추적성)

구현 완료 후 별도 모델(Codex)의 적대 리뷰에서 계약 경계 결함이 제기되어 이 커밋에
흡수 반영했다(TDD RED→GREEN, 신규 케이스 13건 → 전체 160 passed).

- **수용(반영)**:
  - (HIGH) 멱등 결과 타입 불일치 — 첫 호출 raw vs 재시도 JSON-왕복 → `_normalize`로
    양쪽 JSON 정규화 통일 + 비-JSON 결과 거부(`test_result_type_stable_*`,
    `test_non_json_result_rejected`).
  - (HIGH) 익명 행위자 — `Actor.__post_init__`가 ActorRole·비공백 actor_id 강제
    (`test_empty_actor_id_rejected`·`test_non_actorrole_rejected`).
  - (HIGH→MEDIUM) 이벤트 payload JSON 엄격화 — 최상위 mapping 강제·set/bytes/비문자열
    key 거부·`EventEnvelope.__post_init__`가 직접 생성 경로도 검증·재귀 불변화
    (`test_string_payload_rejected` 등 4건).
  - (MEDIUM) 멱등 입력 검증 — 빈 namespace/scope/key·ttl≤0·version<1·빈 근거 거부
    (빈 scope의 벤더 격리 사고 방지).
  - (MEDIUM) 중복 구독 거부(`test_duplicate_subscription_rejected`).
  - (MEDIUM) 추적 인덱스 추가 — `0003_add_tracing_indexes`(correlation_id·대상).
- **기각(근거)**:
  - (HIGH) "publish의 동일 트랜잭션 강제"는 **스펙 위반이 아니며 반영 시 스펙 위반이
    된다** — FR-004는 동기 실행이 호출자 트랜잭션 안에서 돎을 기술할 뿐 커널의 atomic
    강제를 요구하지 않고, quickstart 시나리오 4는 "이벤트 DB 불필요"를 명시한다. 트랜잭션
    소유는 도메인 서비스(P1+)의 몫이다.
- **연기**: 완료 멱등 기록의 보존·만료 정책은 실거래 전(go-live) 결정 — 현 스펙엔 PII·주문
  데이터가 없어 지금 강제 대상이 아니다(원칙 XV 단계화).
