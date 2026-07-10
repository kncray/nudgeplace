# Phase 1 Data Model: Foundation — Shared Kernel Primitives

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-09

프로젝트 **최초의 영속 엔티티 2개**(멱등 실행 기록·감사 사실)와 비영속 값
객체들을 정의한다. 두 테이블은 커널 소유의 **인프라 기록**이며 비즈니스 도메인
모델이 아니다(BR-6) — Spec 000의 "픽스처 앱 모델 0" 제약과 충돌하지 않는다.

## 영속 엔티티

### 1. IdempotencyRecord (멱등 실행 기록)

| 필드 | 타입 | 제약 | 근거 |
|---|---|---|---|
| `namespace` | 문자열 | 필수 | 연산 네임스페이스 — 지문 스키마의 소유 단위(BR-4) |
| `scope` | 문자열 | 필수 | 요청 주체 범위(예: `"vendor:42"`, `"system"`) |
| `key` | 문자열 | 필수 | 호출자가 부여한 멱등키 |
| `fingerprint` | 문자열(SHA-256 hex) | 필수 | 안정적 작업 입력의 정규화 지문 — 추적 메타데이터 제외(FR-005) |
| `fingerprint_version` | 정수 | 필수 | 네임스페이스 소유 지문 스키마의 버전(BR-4) — **재시도 대조는 (version, fingerprint) 쌍**: 버전 불일치도 `IdempotencyConflict`(스키마 변경 요청이 이전 결과를 받는 결함 방지) |
| `status` | enum | 필수 | `IN_PROGRESS` / `COMPLETED` / `UNKNOWN` / `DEFINITE_FAILURE` (아래 상태 전이) |
| `result` | JSON | COMPLETED에서 필수 | 최초 실행의 반환값(재시도에 그대로 반환) |
| `correlation_id` | UUID | 필수 | 관통 추적(FR-010) |
| `claim_token` | UUID | IN_PROGRESS에서 필수 | 현재 실행 lease의 fencing token — 만료 재클레임 후 이전 실행의 완료 마킹 차단 |
| `claimed_at` | timestamptz | 필수, 시스템 부여 | 클레임 시각 |
| `in_progress_expires_at` | timestamptz | IN_PROGRESS에서 필수 | 고착 복구 시한(FR-005 — 기본 60초, 호출별 주입 가능) |
| `completed_at` | timestamptz | COMPLETED에서 필수 | |
| `unknown_marked_at` | timestamptz | UNKNOWN에서 필수 | 효과 여부 미상 판정 시각 |
| `unknown_evidence_ref` | 문자열 | UNKNOWN에서 필수 | 불확정 판정 근거(외부 요청/응답·복구 티켓 등) |
| `resolved_at` | timestamptz | UNKNOWN 해소 시 필수 | 복구 검증 완료 시각 |
| `resolution_evidence_ref` | 문자열 | UNKNOWN 해소 시 필수 | 복구 검증 결과 근거 |

- **유니크 제약**: `(namespace, scope, key)` — 동시성 직렬화의 최종 보장
  (헌장 동시성 제어, DB 수준).
- **상태별 DB 제약**: 마이그레이션의 `CheckConstraint`가 IN_PROGRESS의
  claim token·만료 시각, COMPLETED의 결과·완료 시각, UNKNOWN의 판정 시각·근거,
  DEFINITE_FAILURE의 해소 시각·근거 등 상태별 필수 필드 조합을 강제한다.
- **조회 전용 공개 모델**: 공개 `objects` manager와 인스턴스 `save/delete`는
  생성·상태 수정·삭제·bulk 쓰기를 거부한다. 쓰기는 idempotency 모듈 내부의
  전이 manager/repository만 수행하고, 모든 전이는 아래 fenced 규칙을 따른다.
- **확정 실패 표현 — 삭제 금지, 지문 보존 tombstone**: 확정 실패(내부 트랜잭션
  롤백 = 효과 없음 보장, 또는 UNKNOWN을 복구 검증으로 "효과 없음"으로 해소)는
  `DEFINITE_FAILURE` tombstone으로 남긴다. 레코드를 삭제하면 지문이 사라져
  "같은 키·다른 요청 거부"(BR-4·FR-005)가 실패 후에 뚫린다 — tombstone이 지문을
  보존해 다른-내용 재사용은 실패 후에도 항상 거부된다. 재시도는 tombstone을
  결과 캐시로 반환하지 않고(BR-4) **같은 지문일 때만** 원자적으로 새
  `IN_PROGRESS` claim으로 전환한다. `resolution_evidence_ref`가 실패 근거를
  보존한다(내부 롤백은 `internal:rolled-back` 계열 표기).
- **전이 불변식**: 모든 상태 전이는 현재 상태·`claim_token` 조건부 UPDATE로만
  일어난다(fenced, 영향 행 검사). **COMPLETED는 종결·불변** — stale watchdog·
  이전 claim 소유자를 포함해 어떤 경로도 COMPLETED를 되돌릴 수 없다.

**상태 전이** (계약 상세: [contracts/idempotency-protocol.md](./contracts/idempotency-protocol.md)):

```
(없음) ──클레임 INSERT(트랜잭션 ①, claim_token 발급)──▶ IN_PROGRESS
IN_PROGRESS ──비즈니스 트랜잭션 ② 성공(효과+마킹 원자, claim_token 일치)──▶ COMPLETED   [종결·불변]
IN_PROGRESS ──② 확정 실패(fenced: status+claim_token 조건부)──▶ DEFINITE_FAILURE (지문 보존)
IN_PROGRESS ──시한 경과 + 새 claim_token fenced 재클레임──▶ IN_PROGRESS
IN_PROGRESS ──외부 흐름의 결과 미상 판정(P6+, fenced: claim_token 일치) + 근거──▶ UNKNOWN
UNKNOWN ──흐름 소유 복구 검증(P6+, WHERE status='UNKNOWN') + 근거──▶ COMPLETED 또는 DEFINITE_FAILURE
DEFINITE_FAILURE ──**같은 지문** 재시도──▶ IN_PROGRESS (새 claim_token, 결과 캐시 반환 없음)
DEFINITE_FAILURE ──다른 지문 요청──▶ IdempotencyConflict (지문 보존이 이를 가능하게 함)
```

> 이 스펙 범위의 연산(내부·트랜잭션 내)은 UNKNOWN을 만들지 않는다 — 상태·전이는
> 스키마와 API 계약에 존재하며 설정·해소 주체는 외부 부수 효과 흐름(P6+)이다.
> `UNKNOWN` 해소에는 `resolution_evidence_ref`가 필수다. 도메인 상태 모델이
> 아니므로 `docs/domain/state-model.md` 대상이 아니다(스펙 Architectural
> Considerations 판정).

### 2. AuditFact (감사 사실)

| 필드 | 타입 | 제약 | 근거 |
|---|---|---|---|
| `actor_role` | enum | 필수 | `OPERATOR` / `VENDOR` / `CUSTOMER` / `SYSTEM` (FR-007) |
| `actor_id` | 문자열 | 필수 | 주체 식별자(행위자 없는 기록 거부 — FR-006) |
| `target_type` | 문자열 | 필수 | 대상 타입(타입 없는 식별자 거부 — FR-006) |
| `target_id` | 문자열 | 필수 | 대상 식별자 |
| `reason_text` | 문자열 | 필수 | 사유(자유 텍스트) |
| `reason_code` | 문자열 | 선택 | 구조화 사유 코드(체계는 소비 스펙 — SHOULD) |
| `evidence_ref` | 문자열 | 필수 | 근거 참조(시스템=유발 참조, 사람=판단 근거 — FR-006) |
| `correlation_id` | UUID | 필수 | 관통 추적(FR-010) |
| `recorded_at` | timestamptz | 필수, 시스템 부여 | 호출자 임의 지정 금지 |

- **append-only·조회 전용 공개 모델**: 공개 `objects` manager와 인스턴스
  `save/delete`는 create/get-or-create/update-or-create/bulk create·update/delete를
  모두 거부한다. 삽입은 `record_audit_fact`의 모듈 내부 manager/repository만
  수행하고, 정정은 새 사실의 추가로만 한다.
- **원자성 — 강제됨**: 기록 API는 호출자의 열린 트랜잭션에 참여한다 — 상태
  변경과 감사 기록이 함께 커밋되거나 함께 롤백된다(FR-006). 열린 atomic 블록
  밖(autocommit)에서의 기록 시도는 **거부**된다. 검사는 ORM 호출 전에
  `record_audit_fact`가 수행하므로 `get_or_create`처럼 ORM이 내부 atomic을 여는
  우회가 없고, 직접 ORM 생성은 위 조회 전용 manager가 항상 차단한다.
- **용도 한정**: 상태 변경·운영 개입의 감사 기록 전용 — 고빈도 관측 로깅 싱크
  아님(FR-006).

## 비영속 값 객체 / 계약

### Money
- `amount_minor: int`(통화 최소 단위) + `currency: Currency` — 불변(frozen).
- 통화 레지스트리: 획득은 `Currency.of(code)`(미등록 코드 거부 — BR-2), 등록은
  `Currency.register(code, exponent)`(같은 값 재등록 무해, 다른 값 거부). 초기
  KRW(지수 0). 직접 생성한 위조 인스턴스(`Currency("KRW", 다른 지수)`)는 연산
  시 레지스트리 대조로 거부된다.
- Money 생성 API는 minor-unit `int`를 받는다. `float` 직접 입력은 거부한다.
  `Decimal` 값이 바이너리 float에서 유래했는지는 객체 수신 시점에 기계 판별할
  수 없으므로 **생성·연산 어느 경로에서도 `Decimal` 인스턴스를 받지 않는다**
  (동일 근거의 일관 적용 — SC-002).
- 연산: `+`/`-`(동일 통화만), `* int`(무손실), `multiply(scalar, rounding=)`
  (정책 필수; scalar 허용 타입 = `int` · **정확 십진 문자열**(내부에서
  `Decimal(str)`로 정확 변환) · `Fraction` — `float`·`Decimal` 인스턴스 거부),
  비교(동일 통화만), `allocate(weights, remainder_policy=)`(정책 필수, 합계
  보존 — R3).
- 반올림 정책 어휘: `ROUND_DOWN`/`ROUND_UP`/`ROUND_HALF_UP`/`ROUND_HALF_EVEN`.
- 끝전 귀속 정책 어휘: `LARGEST_REMAINDER`/`FIRST`/`LAST`.

### EventEnvelope
- `event_id: UUID`(자동) · `event_type: str` · `occurred_at`(시스템 부여) ·
  `aggregate_type: str`("도메인.집계") · `aggregate_id: str` ·
  `payload_version: int` · `correlation_id: UUID`(컨텍스트에서) ·
  `causation_id: UUID | None` · `payload`(방어 복사 후 JSON-like mapping/list를
  재귀 불변화한 매핑 — 원본과 핸들러가 발행 사실을 변경할 수 없음).
- 필수 필드 누락 시 발행 거부(BR-3). 영속화 없음(영속 이벤트 저장은 P12 아웃박스).

### Dispatcher / 핸들러 등록
- `SideEffect` 등급: `INTERNAL` / `EXTERNAL`. 등록 시 선언 필수(기본값 없음),
  SyncDispatcher는 `EXTERNAL` 등록 거부(FR-004). 핸들러 예외는 전파.
- `Dispatcher` 프로토콜: `dispatch(envelope)` — 교체 가능(발행 API와 분리, BR-3).
- **주입·격리 설계**: 구독 레지스트리는 디스패처 **인스턴스**가 소유한다(모듈
  전역 레지스트리 금지 — 테스트 누출 방지). `subscribe(..., dispatcher=target)`가
  등록 대상을 명시하며 생략 시 모듈 기본 SyncDispatcher를 사용한다. 현재 **발행**
  디스패처는 contextvar로 결정되고 `use_dispatcher(dispatcher)` 컨텍스트 매니저가
  교체한다 — dispatch-only 대체 구현에 subscribe 능력을 암묵 요구하지 않으며,
  발행 코드는 불변(US2 #4)이고 테스트는 새 SyncDispatcher 주입으로 격리된다.

### Actor / ActorRole
- `ActorRole`: `OPERATOR`/`VENDOR`/`CUSTOMER`/`SYSTEM`(FR-007).
- `Actor(role, actor_id)` — 감사 사실의 행위자 표현.

### Correlation Context
- `contextvars` 기반: `get_correlation_id()`(미설정 시 발급·고정),
  `bind_correlation_id(value)`(요청 경계용, reset token 반환),
  `reset_correlation_id(token)`, `correlation_context(value=None)`(요청/테스트
  경계용 context manager). 세 기록(멱등·감사·이벤트)이 이를 읽는다(FR-010).
- 요청 경계가 끝나면 반드시 reset되어야 한다 — 순차 실행되는 두 흐름이 같은
  correlation을 공유하면 SC-007의 "하나의 요청 흐름" 의미가 깨진다.
- **전파 경계**: async task에는 자동 전파되지만 **새 스레드는 컨텍스트를 상속하지
  않는다**(각 스레드는 독립 컨텍스트 — 그래서 흐름 간 누출도 없다). 스레드
  핸드오프가 필요한 흐름은 `contextvars.copy_context()` 래핑이 명시 규약이며,
  이 경계는 계약·테스트로 고정한다.

## 관계

```
CorrelationContext ──┬─▶ IdempotencyRecord.correlation_id
                     ├─▶ AuditFact.correlation_id
                     └─▶ EventEnvelope.correlation_id     (SC-007: 세 기록 연결)

Actor(role) ─────────▶ AuditFact.actor_role/actor_id
EventEnvelope.causation_id ─▶ (선행 EventEnvelope.event_id — 선택)
```

도메인 FK 없음 — `target_id`·`aggregate_id`·`scope`는 문자열 식별자다(커널이
도메인을 모르는 BR-6의 구조적 표현이자, 헌장 VIII의 ID-참조 규약과 정합).
