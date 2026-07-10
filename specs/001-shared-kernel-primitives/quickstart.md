# Quickstart & Validation: Foundation — Shared Kernel Primitives

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-09

Spec 001이 **끝났음을 증명하는 실행 가능한 검증 시나리오**다. 구현 코드는 담지
않는다. 각 시나리오는 User Story·Success Criteria에 매핑된다.

## 전제 (Prerequisites)

```bash
docker compose up -d postgres    # 로컬 PostgreSQL 16 (신규 — research R1)
uv sync                          # psycopg 포함
uv run python manage.py migrate  # 프로젝트 최초 마이그레이션(멱등·감사 테이블 + 감사 append-only 트리거)
```

접속 계약(R1): `POSTGRES_HOST/PORT/DB/USER/PASSWORD` 환경변수 — 미설정 시 로컬
compose 기본값(비밀 아님). CI는 `quality-gate` 잡 env + postgres 서비스
(healthcheck)로 동일 계약을 사용한다.

## 시나리오 1 — Money 표현·연산·통화 안전 (US1 #1~3)

```bash
uv run pytest tests/kernel/test_money.py
```
- **기대**: 생성·덧셈·뺄셈·정수 곱·비교의 결정론(SC-001), float 경로 100% 거부
  (SC-002), 통화 불일치 거부, 미등록 통화 거부.

## 시나리오 2 — 명시적 반올림 (US1 #4)

- **기대**: 정밀도 손실 연산에 정책 인자 누락 → 거부(암묵 기본값 없음, K-3);
  4개 정책 어휘 각각의 결정론적 결과. (시나리오 1과 같은 테스트 파일.)

## 시나리오 3 — 안분: 합계 보존·끝전 결정론 (US1 #5)

```bash
uv run pytest tests/kernel/test_money_allocation.py
```
- **기대**: 다수 입력(원금·가중치·분할 수 조합)에서 몫 합 − 원금 = **0**(SC-008),
  같은 입력 → 같은 분배(귀속 정책별), 경계 입력(빈 목록·합 0 가중치·음수
  가중치)은 정의된 오류. 10,000원 3등분 → 3,334/3,333/3,333 예시 포함.
  구현 전체의 float 리터럴·호출·진수 나눗셈 0건과 2^60원 안분 정확성 포함.

## 시나리오 4 — 이벤트 봉투 강제·디스패치 (US2 #1~5)

```bash
uv run pytest tests/kernel/test_events.py
```
- **기대**: 완전한 봉투의 발행·수신(필드 전수 판독), 불완전 봉투 발행 거부
  (SC-003), payload 원본·중첩 값의 변경 시도에도 발행 사실 불변(K-14), 복수
  핸들러 실행 + 예외 전파(조용한 유실 없음), `subscribe(..., dispatcher=)`로
  구독 대상 명시, `use_dispatcher()` 교체 시 발행 코드 불변, side_effect 등급
  누락 등록 거부, **EXTERNAL 등급 핸들러 등록 거부**(K-6), **호출자 지정
  `occurred_at` 거부**(backdate 불가 — K-13).

## 시나리오 5 — 멱등: 재시도·충돌·스코프 (US3 #1·2·4·5)

```bash
uv run pytest tests/kernel/test_idempotency.py
```
- **기대**: 같은 범위·키 3회 → 효과 1회·동일 결과, 같은 키·다른 지문 → 거부,
  같은 지문이라도 fingerprint_version이 다르면 `IdempotencyConflict`, 다른
  scope·같은 키 문자열 → 독립 처리, 확정 실패 후 재시도 → 재실행, correlation만
  다른 재시도 → 정상 통과(지문에 추적 메타데이터 제외 검증).

## 시나리오 6 — 멱등: 동시성·진행 중·고착·불확정 해소 (US3 #3·6·7·8, SC-004)

- **기대**: 동시 도착(스레드 경합, `transaction=True`, DB-backed 효과) → 커밋
  효과 정확히 1회 / 외부 atomic 안 호출 → 클레임·실행 없이 거부 / 진행 중 재시도
  → 이중 실행 없이 "진행 중" 신호 / TTL 경과 → 이전 실행 생존 여부와 무관하게
  새 claim token으로 fenced 재클레임 / 살아 있던 stale claim의 완료 마킹 실패는
  비즈니스 트랜잭션 전체 롤백(커밋 효과 최대 1회) /
  **확정 실패는 지문 보존 tombstone** — 같은 지문 재시도만 재클레임, 다른
  지문은 실패 후에도 거부(K-8), stale cleanup은 fenced라 남의 클레임을 지우지
  못함 / UNKNOWN 상태 → 자동 재실행 금지 신호 / UNKNOWN 전이·해소는
  claim_token/상태 조건부 + 근거 참조 필수 / **COMPLETED는 불변** —
  mark_unknown으로 되돌리기 시도 및 공개 ORM 직접 상태 변경 거부 / 상태별 필드
  DB 제약.
  (시나리오 5와 같은 테스트 파일 — PostgreSQL 유니크 의미론이 전제, R1.)

## 시나리오 7 — 감사 사실: 필수 필드·불변·원자성 (US4 #1~3)

```bash
uv run pytest tests/kernel/test_audit.py
```
- **기대**: 전 필수 필드(행위자·역할·대상 타입+ID·사유·근거 참조·correlation)
  기록·조회(SC-005), 행위자/근거/대상 타입 누락 → 거부, 기록 후 수정·삭제 →
  거부(queryset 경로 **및 raw SQL 경로 — DB 트리거가 거부**, R5), 호출자 지정
  `recorded_at` 거부(K-13), 외부 atomic 없는 기록 거부, 공개 ORM의 모든 생성·
  수정·삭제·bulk 경로 거부, 호출자 트랜잭션 롤백 시 감사 기록도 롤백(원자성).

## 시나리오 8 — 행위자 역할 어휘 (US4 #4)

```bash
uv run pytest tests/kernel/test_actors.py
```
- **기대**: OPERATOR·VENDOR·CUSTOMER·SYSTEM 구분 제공(FR-007).

## 시나리오 9 — 관통 추적 (US5 #1~2, SC-007)

```bash
uv run pytest tests/kernel/test_correlation.py
```
- **기대**: 하나의 흐름에서 멱등 연산+감사 기록+이벤트 발행 → 세 기록이 같은
  correlation으로 연결 조회, 미설정 흐름 → 시스템 발급 후 공유, 요청 경계 종료 후
  reset되어 순차 실행되는 다음 흐름으로 correlation이 누출되지 않음, **스레드
  핸드오프 경계** — 새 스레드는 비상속(독립 correlation 발급됨을 확인),
  `copy_context()` 래핑 시 동일 correlation 유지(R6 규약).

## 시나리오 10 — 공개 표면 특성화 (SC-006, K-12)

```bash
uv run pytest tests/kernel/test_public_surface.py tests/conformance/ tests/boundary/
```
- **기대**: `shared_kernel.__all__` == [표면 열거](./contracts/kernel-public-surface.md)
  + 내부 모듈 정확 allowlist + 신규 프로세스의 앱 모델 집합 =
  `{IdempotencyRecord, AuditFact}`(Spec 000 빈-커널 특성화의 후계 — 개정된
  `test_fixture_scope.py` 포함 GREEN), Spec 000 경계 검사(tach·픽스처 적합성)도
  여전히 GREEN(커널 도메인 참조 0).

## 시나리오 11 — 전체 게이트

```bash
uv run tach check && uv run ruff check . && uv run pytest
```
- **기대**: 전부 통과 — CI `quality-gate`(postgres 서비스 추가된)와 동일 결과.

---

## Success Criteria 커버리지 요약

| SC | 검증 시나리오 |
|---|---|
| SC-001 (결정론 — 반올림·안분 포함) | 1, 2, 3 |
| SC-002 (부동소수점 0) | 1 |
| SC-003 (봉투 완전성) | 4 |
| SC-004 (멱등 — 동시·스코프 포함) | 5, 6 |
| SC-005 (감사 불변·완결) | 7 |
| SC-006 (커널 순수성·공개 표면) | 10 |
| SC-007 (관통 추적) | 9 |
| SC-008 (합계 보존) | 3 |
