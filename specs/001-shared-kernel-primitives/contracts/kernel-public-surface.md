# Contract: 커널 공개 표면 (Kernel Public Surface)

**Spec**: [../spec.md](../spec.md) | **Date**: 2026-07-09

공유 커널이 도메인(및 미래 코드)에게 노출하는 **유일한 계약 표면**이다. 이
열거가 BR-7·FR-008의 특성화 대상이며, Spec 000의 "커널 public symbol 0" 특성화
테스트를 대체하는 후계 계약이다.

## 표면 열거 (다섯 primitive + 관통 추적 컨텍스트)

| # | Primitive | 노출 계약 | 스펙 근거 |
|---|---|---|---|
| 1 | **Money** | `Money`, `Currency`(획득은 `Currency.of(code)`·등록은 `Currency.register(code, exponent)` — 클래스메서드, 위조 인스턴스는 레지스트리 대조 거부), `RoundingPolicy`, `RemainderPolicy` (`Money.allocate()`는 Money 메서드 — 표면 별항 아님; 스칼라는 `int`·정확 십진 문자열·`Fraction`만 — `float`·`Decimal` 인스턴스 거부) | FR-001·002·011, BR-1·2·8 |
| 2 | **도메인 이벤트** | `EventEnvelope`(payload 재귀 불변), `publish`, `subscribe(..., dispatcher=)`(등록 대상 명시), `Dispatcher`(dispatch-only), `SyncDispatcher`(구독 레지스트리를 인스턴스로 소유), `use_dispatcher`(contextvar 기반 발행 디스패처 교체), `SideEffect`, `HandlerRegistrationError` | FR-003·004, BR-3 |
| 3 | **멱등 실행** | `run_idempotent`(외부 atomic 거부·canonicalizer·`fingerprint_version`·TTL/clock 주입), `canonical_json`, `IdempotencyRecord`(조회 전용), `IdempotencyStatus`, `IdempotencyConflict`, `InProgress`, `UnknownOutcome`, `LostClaimError`, `mark_unknown`(claim_token 필수·fenced), `resolve_unknown_as_completed`, `resolve_unknown_as_definite_failure` | FR-005, BR-4 |
| 4 | **감사 사실** | `record_audit_fact()`(외부 atomic 필수), `AuditFact`(조회 전용) | FR-006, BR-5 |
| 5 | **행위자 역할** | `ActorRole`, `Actor` | FR-007 |
| + | **상관관계 컨텍스트** | `get_correlation_id`, `bind_correlation_id`, `reset_correlation_id`, `correlation_context` | FR-010 |

- 위 목록에 없는 이름은 공개 표면이 아니다 — `shared_kernel/__init__.py`의
  re-export 목록(`__all__`)이 아래 canonical list와 1:1이어야 하며,
  **공개 표면 특성화 테스트**(`tests/kernel/test_public_surface.py`)가 이 일치를
  기계 단언한다.
- 표면 추가·변경은 이 문서 개정 + 특성화 테스트 갱신을 동반해야 한다(사람
  판단 강제 — Spec 000의 특성화 관례 계승).

```python
EXPECTED_PUBLIC_SURFACE = (
    "Actor",
    "ActorRole",
    "AuditFact",
    "Currency",
    "Dispatcher",
    "EventEnvelope",
    "HandlerRegistrationError",
    "IdempotencyConflict",
    "IdempotencyRecord",
    "IdempotencyStatus",
    "InProgress",
    "LostClaimError",
    "Money",
    "RemainderPolicy",
    "RoundingPolicy",
    "SideEffect",
    "SyncDispatcher",
    "UnknownOutcome",
    "bind_correlation_id",
    "canonical_json",
    "correlation_context",
    "get_correlation_id",
    "mark_unknown",
    "publish",
    "record_audit_fact",
    "reset_correlation_id",
    "resolve_unknown_as_completed",
    "resolve_unknown_as_definite_failure",
    "run_idempotent",
    "subscribe",
    "use_dispatcher",
)
```

특성화 테스트(K-12)는 네 겹으로 단언한다: ① 이 코드 블록 파싱 == `__all__`
정확 일치, ② 각 심볼 `getattr` 실재(유령 심볼 차단), ③ `__all__` 밖 초과 공개
이름 0건 + 내부 모듈 정확 집합
`{actors, apps, audit, correlation, events, idempotency, migrations, models, money}`
대조(모든 서브모듈을 포괄 제외하지 않음), ④ **신규 프로세스에서
`django.setup()` 직후 앱 모델 집합이 `{IdempotencyRecord, AuditFact}`와 정확히
일치하고 `manage.py check` 성공** — 빈 models.py와 조기 re-export를 함께 방어한다.

## 계약 요약 (수용 기준 매핑)

| ID | 계약 | 검증 |
|---|---|---|
| K-1 | float로 Money 생성·연산 시도 → 거부 | US1 #2, SC-002 |
| K-2 | 통화 불일치 산술·비교 → 거부 | US1 #3 |
| K-3 | 정밀도 손실 연산에 정책 인자 누락 → 거부(암묵 기본값 없음) | US1 #4, FR-002 |
| K-4 | `allocate` 몫 합 = 원금(모든 입력) + 귀속 결정론 | US1 #5, SC-008 |
| K-5 | 봉투 필수 필드 누락 이벤트 → 발행 거부 | US2 #2, SC-003 |
| K-6 | side effect 등급 누락 또는 `EXTERNAL` 등급 핸들러의 동기 등록 → 거부 | US2 #5, FR-004 |
| K-7 | 같은 (namespace, scope, key) 재시도 → 효과 1회·결과 반환 | US3 #1·3, SC-004 |
| K-8 | 같은 키에서 `(fingerprint_version, fingerprint)` 쌍 불일치 → `IdempotencyConflict`(**확정 실패 tombstone 이후 포함**) / 다른 scope·같은 키 → 독립 | US3 #2·4, BR-4 |
| K-9 | 확정 실패(지문 보존 tombstone) 후 **같은 지문만** 재실행 / 불확정 자동 재실행 금지·근거 있는 해소 / 진행 중 응답 / stale claim 롤백 / **COMPLETED 불변** / 공개 ORM 직접 상태 변경 거부 / 외부 atomic에서 run_idempotent 거부 | US3 #5·6·7·8 |
| K-10 | 필수 필드 없는 감사 기록 거부, 외부 atomic 없는 기록 거부, 공개 ORM은 조회 전용, 기록 후 수정·삭제는 모델 계층 **및 DB 트리거**가 거부(raw SQL UPDATE/DELETE 포함) | US4 #1~3, SC-005 |
| K-11 | 세 기록(멱등·감사·이벤트)이 같은 correlation으로 연결되고 요청 경계 종료 후 reset — 스레드 핸드오프는 `copy_context()` 명시 규약 | US5 #1~2, SC-007 |
| K-12 | `__all__` == 이 문서의 표면 열거 | SC-006 |
| K-13 | 호출자 지정 `occurred_at`/`recorded_at` → 거부(시각은 시스템 부여 — backdate 불가) | FR-003·006 |
| K-14 | 이벤트 payload는 방어 복사 후 재귀 불변 — 원본·핸들러 변경 시도에 발행 사실 불변 | US2 #1, FR-003 |
