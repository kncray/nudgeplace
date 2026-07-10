# Contract: 멱등 실행 프로토콜 (Idempotency Protocol)

**Spec**: [../spec.md](../spec.md) | **Date**: 2026-07-09

멱등 실행 primitive의 동시성·복구 프로토콜이다. 스펙 BR-4·FR-005의 계약을 DB
유니크 제약 기반 **2단계 클레임**으로 구현한다(plan Architecture Decisions,
research R4).

## 프로토콜

```
run_idempotent(namespace, scope, key, request, operation, *,
               fingerprint_version, canonicalize=canonical_json,
               in_progress_ttl=60s, now=system_clock):   # TTL·시계 주입점(테스트 주입 가능)

⓪ 진입 조건
   호출 시점에 이미 열린 DB transaction.atomic 블록이 있으면
   TransactionManagementError (클레임·operation 실행 없음)
   # ①은 다른 연결에 즉시 보여야 하는 독립 커밋이다. Django의 중첩 atomic은
   # 커밋이 아니라 savepoint이므로 외부 atomic 안에서는 이 계약을 구현할 수 없다.

① 클레임 트랜잭션 (짧게, 독립 커밋)
   fingerprint = SHA256(canonicalize(request))
     # canonicalizer·버전은 네임스페이스 소유(BR-4) — 커널은 기본 canonical_json
     # (키 정렬 직렬화)을 제공하고, 네임스페이스가 자기 스키마의 canonicalizer를
     # 주입한다. 추적 메타데이터(correlation·시각)는 포함 금지(FR-005).
   claim_token = uuid4()
   INSERT IdempotencyRecord(IN_PROGRESS, claim_token, expires_at=now+TTL)
   ├─ 성공 → ②로
   └─ 유니크 충돌 → 기존 레코드 판독:
       ├─ (fingerprint_version, fingerprint) 쌍 불일치 → IdempotencyConflict
       │    (같은 키·다른 요청 — 실행 없음. 버전만 달라도 충돌: 스키마가 바뀐
       │     요청이 이전 결과를 돌려받는 결함 방지 — 새 스키마는 새 키를 쓴다)
       ├─ COMPLETED        → 저장된 result 반환 (효과 없음)
       ├─ UNKNOWN          → UnknownOutcome 신호 (자동 재실행 금지)
       ├─ DEFINITE_FAILURE → 원자적 새 클레임(결과 캐시 반환 없음)
       └─ IN_PROGRESS:
           ├─ 미만료 → InProgress 신호 (이중 실행 없음, 대기 강제 없음)
           └─ 만료   → claim_token fencing 아래 원자적 재클레임:
                        new_claim_token = uuid4()
                        UPDATE ... SET claim_token=new_claim_token,
                                       claimed_at=now, expires_at=now+TTL
                        WHERE pk=? AND status IN ('IN_PROGRESS', 'DEFINITE_FAILURE')
                          AND (status='DEFINITE_FAILURE' OR expires_at<now)
                        (영향 행 1 → ②로 / 0 → InProgress 신호)

② 비즈니스 트랜잭션 (원자)
   result = operation()                       # 순수 내부 효과 (이 스펙 범위)
   UPDATE record SET status=COMPLETED, result=..., completed_at=now
     WHERE pk=? AND status='IN_PROGRESS' AND claim_token=<내 claim_token>
                                                # fencing 조건 — 영향 행 검사
   COMMIT  → result 반환
   완료 UPDATE 영향 행 0 → LostClaimError 발생 → 비즈니스 트랜잭션 전체 롤백
   실패(예외) → 트랜잭션 롤백(효과 없음 = 확정 실패)
             → 후속 정리 트랜잭션에서 **fenced tombstone 전이** (삭제 금지):
                UPDATE ... SET status='DEFINITE_FAILURE', resolved_at=now,
                               resolution_evidence_ref='internal:rolled-back'
                WHERE pk=? AND status='IN_PROGRESS' AND claim_token=<내 claim_token>
                (영향 행 0 → 이미 재클레임됨 — 아무것도 하지 않는다)
             → 지문이 보존되므로 "같은 키·다른 요청 거부"(BR-4)는 실패 후에도
               유지되고, 같은 지문의 재시도만 ①의 DEFINITE_FAILURE 분기에서
               원자적으로 새 클레임이 된다

③ UNKNOWN 해소 API (외부 흐름 P6+가 소유) — 전 전이 fenced·조건부
   mark_unknown(namespace, scope, key, claim_token, unknown_evidence_ref)
     → UPDATE ... SET status='UNKNOWN', unknown_marked_at=now, ...
       WHERE status='IN_PROGRESS' AND claim_token=<호출자 claim_token>
       (영향 행 0 → 전이 거부 — 완료·재클레임된 레코드를 되돌릴 수 없다)
   resolve_unknown_as_completed(..., result, resolution_evidence_ref)
     → UPDATE ... WHERE status='UNKNOWN' (영향 행 검사)
   resolve_unknown_as_definite_failure(..., resolution_evidence_ref)
     → UPDATE ... WHERE status='UNKNOWN' (영향 행 검사)
        (다음 같은 지문 재시도는 결과 캐시 없이 새 claim으로 전환)

불변식: COMPLETED는 종결 상태 — 어떤 API·주체도 COMPLETED를 다른 상태로
바꿀 수 없다(stale watchdog·이전 claim 소유자의 mark_unknown 포함).
```

`IdempotencyRecord`의 공개 `objects` manager는 **조회 전용**이다. `save()`와
`create/update/delete/bulk_*` 계열을 통한 직접 쓰기는 거부되며, 위 프로토콜의
모듈 내부 전이 manager/repository만 레코드를 변경한다. 마이그레이션은 상태별
필수 필드 조합을 DB `CheckConstraint`로도 강제한다. 이는 FR-005의 "직접 상태
덮어쓰기 금지"를 호출 규약이 아니라 실행 경로로 고정한다.

## 보장 (스펙 시나리오 매핑)

| 보장 | 근거 메커니즘 | 스펙 |
|---|---|---|
| 동시 도착 효과 1회 | `(namespace, scope, key)` DB 유니크 — 한쪽만 INSERT 성공 | US3 #3, SC-004 |
| 완료 재시도 = 결과 반환, 효과 0 | ①의 COMPLETED 분기 | US3 #1 |
| 같은 키·다른 요청 거부 — **확정 실패 후 포함** | 지문 불일치 → 실행 전 거부. tombstone이 지문을 보존하므로 실패 후의 다른-내용 재사용도 거부 | US3 #2, BR-4 |
| scope 간 독립 | 유일성 범위에 scope 포함 | US3 #4 |
| 확정 실패 재실행 | ②가 원자라 실패 = 효과 없음 보장 → fenced DEFINITE_FAILURE tombstone → 같은 지문만 원자 재클레임 | US3 #5 |
| COMPLETED 불변 | 모든 전이가 상태·token 조건부 UPDATE — 종결 상태로의 역전이 경로 없음 | FR-005, BR-5 유추 |
| 진행 중 응답(비블로킹) | 클레임이 ①에서 선커밋되어 즉시 가시 | US3 #6 |
| 고착 복구의 안전성 | TTL은 재클레임 시점, claim_token fencing은 stale 실행의 완료 마킹 차단·전체 DB 트랜잭션 롤백을 보장 | US3 Edge, FR-005 |
| 불확정 자동 재실행 금지 | UNKNOWN 분기는 신호만 반환 — 해소는 근거가 있는 흐름 소유 복구 검증(P6+) | US3 #7·8, BR-4 |
| 재클레임/완료 마킹의 경합 안전 | 새 claim_token + 완료 시 token 조건부 UPDATE + 영향 행 수 검사(헌장 XIV 원자 전이 패턴 준용). 이전 claim은 완료 마킹 실패 시 전체 롤백 | FR-005 |
| 클레임 독립 가시성 | 외부 atomic 진입 거부 — ①은 savepoint가 아닌 독립 커밋 | US3 #6, FR-005 |
| 직접 상태 덮어쓰기 차단 | 공개 ORM 쓰기 경로 거부 + 내부 fenced 전이 경로 + 상태별 DB CheckConstraint | FR-005 |

## 한정과 위임

- **이 스펙 범위의 operation은 순수 내부(트랜잭션 내)다** — 외부 부수 효과를
  가진 operation을 이 프로토콜에 그대로 넣는 것은 계약 위반이다(②의 롤백이
  외부 효과를 되돌리지 못해 "확정 실패 = 무효과 보장"이 깨진다). 외부 흐름은
  P6+에서 의도 기록·UNKNOWN 전이·복구 검증과 함께 이 프로토콜을 확장한다
  (헌장 트랜잭션 경계).
- `run_idempotent`는 트랜잭션 경계를 소유한다. 호출자가 바깥에서
  `transaction.atomic()`으로 감싸면 ①의 독립 커밋이 불가능하므로 실행 전에
  거부한다. 원자적으로 묶어야 하는 상태 변경·감사 기록·내부 이벤트 처리는
  `operation` 안에서 수행한다.
- TTL은 "오래 걸림"과 "죽음"을 구분하지 못하며 **구분할 필요도 없다** — 그것이
  fencing의 요점이다. TTL 경과 후 재클레임은 이전 실행의 생존 여부와 무관하게
  안전하다: 살아 있던 이전 실행이 커밋을 시도하면 token 불일치로 완료 마킹이
  0행이 되고 `LostClaimError`가 비즈니스 트랜잭션 전체를 롤백시켜 그 효과는
  존재한 적이 없게 된다(느린 정당한 작업이 폐기되는 비용은 있으나 정확성은
  유지 — 효과 최대 1회). TTL 값·시계는 `run_idempotent` 주입점(기본 60초)으로
  테스트가 제어한다.
- 지문 스키마·버전은 네임스페이스 소유(BR-4) — 커널은 기본 canonicalizer
  (`canonical_json`: 키 정렬 직렬화)와 해시를 제공하고, `run_idempotent`가
  `canonicalize`·`fingerprint_version` 주입을 받는다. 단순 JSON 정렬만으로 같은
  논리 입력이 다른 지문이 되는 경우(예: 생략된 필드 vs null)는 네임스페이스
  canonicalizer가 정규화할 책임이다.
