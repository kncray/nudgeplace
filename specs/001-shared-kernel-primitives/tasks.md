# Tasks: Foundation — Shared Kernel Primitives

**Input**: Design documents from `/specs/001-shared-kernel-primitives/`

**Prerequisites**: plan.md(적대 리뷰 완료, **tasks-stage 설계 역전파 후 사람 재승인
대기**), spec.md(승인 완료 — 적대 리뷰 3회), research.md, data-model.md,
contracts/(kernel-public-surface.md·idempotency-protocol.md), quickstart.md

## Review & Approval

- **Reviewer** (separate session/model): Codex(별도 모델·컨텍스트) 적대 리뷰 2회
- **Reviewed at**: 2026-07-10 (2회)
- **Review evidence**: 승인 보류(BLOCKER 1·HIGH 5·MEDIUM 4) → 9건 수용·1건
  부분 수용 —
  (1·BLOCKER) Django 앱 로딩과 루트 re-export 충돌(AppRegistryNotReady 재현,
  `<app>.models`만 자동 탐색) → models.py 애그리게이터(T004) + ORM 심볼 PEP 562
  지연 re-export(T070) + 신규 프로세스 `manage.py check` 검증(T070t),
  (2·부분) "TTL 재클레임 구현 불가" 주장은 **반박** — fencing의 요점이 생존
  판별 불요(살아 있던 실행의 커밋은 LostClaimError 롤백으로 무효과)이며 구현
  가능. 단 모순되게 읽히는 문구·TTL 값·주입점 미정은 수용 → 의미론 재서술 +
  `in_progress_ttl`/`now` 주입점(기본 60초, 프로토콜 동기화),
  (3) T060 GREEN-시작이 test-first 위반(특성화 예외는 레거시 한정 — 헌장 문언)
  → T060t로 재구성: Phase 2 직후 작성·RED, US2~4 완료 후 GREEN,
  (4) 감사 원자성이 확인만 되고 강제 안 됨 → save() 관문에서 atomic 블록 필수
  (autocommit 거부 — record_audit_fact·직접 create 모두), 테스트 추가,
  (5) US3/US4 "독립" 선언이 마이그레이션 그래프(0002→0001)와 모순 + plan의
  0001_initial 단일 표기 불일치 → US4의 US3 의존 선언 + plan 구조 정정,
  (6) SC-002 내부 float 0건의 기계 검증 부재 → money.py AST 검사(float
  리터럴·호출·truediv 금지) + 2^53 초과 정확성 케이스,
  (7) 표면 개수 오기(29→**31**: canonical 30 + use_dispatcher 추가) + 검사
  4중화(계약 파싱·getattr 실재·초과 공개 금지·신규 프로세스 check),
  (8) fingerprint_version 충돌 의미 미검증 → 대조 단위를 (version, fingerprint)
  쌍으로 확정 + 버전 불일치 충돌 테스트,
  (9) Dispatcher 주입·격리 미정 → 인스턴스 소유 레지스트리 + contextvar
  `use_dispatcher()` 확정(발행 코드 불변·테스트 격리),
  (10) Currency 사용 API 불명확 → `Currency.of/register` + 위조 인스턴스
  레지스트리 대조 + 교차 통화 테스트용 등록 확정.
  **재리뷰** 승인 보류(HIGH 4·MEDIUM 6) → 10건 전건 수용 —
  (1) T020t가 T021의 안분 구현을 선행 요구하던 순서 모순 → 대형 안분 검증을
  T021t로 이동하고 T021 완료 시 Money 전 테스트 재검증,
  (2) 외부 atomic 안에서는 클레임 독립 커밋이 불가능 → `run_idempotent` 진입
  시 거부 + 효과/클레임 0건 테스트,
  (3) 공개 ORM 경로의 멱등 상태 직접 덮어쓰기 → 조회 전용 공개 manager·내부
  전이 경로 분리 + 상태별 DB 제약·직접 변경 거부 테스트,
  (4) 감사 `save()` 관문을 bulk/get-or-create가 우회 → 공개 manager를 완전 조회
  전용으로 만들고 `record_audit_fact`만 내부 삽입 경로 사용,
  (5) `manage.py check`가 빈 models.py를 탐지하지 못함 → 신규 프로세스 앱
  레지스트리의 모델 집합 정확 일치 검증,
  (6) frozen envelope 안의 mutable payload → JSON-like 페이로드 재귀 불변화와
  원본·핸들러 변경 거부 테스트,
  (7) `subscribe`와 dispatch-only 프로토콜의 모순 → 등록 대상 dispatcher를
  명시 인자로 받도록 확정,
  (8) `ConflictError` 명칭·quickstart TTL 기대 불일치 → `IdempotencyConflict`로
  통일하고 항상 fenced 재클레임 의미론으로 동기화,
  (9) tasks 리뷰가 plan 설계를 바꿨으나 과거 승인 유지 → plan 재승인 대기로
  되돌리고 변경 근거 기록,
  (10) 초과 공개 검사에서 모든 서브모듈을 제외하던 구멍 → 내부 모듈 정확
  allowlist 대조로 교체.
- **Approval** (final approver MUST be a human — Principle XIX): [x] Approved to proceed to implement — _(cray.j, 2026-07-10; plan 재승인과 동시)_

**Tests**: 테스트는 필수이며 구현에 선행한다(원칙 I·XVII, FR-009). 새 동작
테스트는 구현 전 실패(RED)해야 하고, RED는 **옳은 이유**여야 한다 — 미구현
모듈의 ImportError·미정의 심볼·미충족 단언이 RED이며, 환경 문제(DB 미기동 등)로
인한 에러는 RED 증거가 아니다. 각 t-테스트는 **작성+RED 증거가 target의 선행
조건**, **target 완료 후 GREEN이 완료 조건**이다(GREEN은 착수 조건이 아니다).
순수 스캐폴딩(Phase 1의 T001~T004)만 test-first 예외.

**Organization**: User Story 단위 — US1(Money, P1) / US2(이벤트, P2) /
US3(멱등, P3) / US4(감사·역할, P4) / US5(관통 추적, P5). correlation 컨텍스트는
US2~US4 전부의 전제라 Foundational에 배치한다(스토리 독립성 유지 장치).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능(다른 파일, 미완료 태스크 의존 없음)
- 테스트 태스크 ID는 target 태스크 ID + `t` 접미. t 테스트와 그 target은 서로
  [P]가 아니다(target이 테스트에 의존).

## Path Conventions

plan.md Structure Decision: `shared_kernel/`(Django 앱 승격 — models 애그리게이터 +
money·events·idempotency·audit·actors·correlation + migrations/), `tests/kernel/`(신규),
`config/settings/`(DB 접속), 루트에 `docker-compose.yml`,
`.github/workflows/ci.yml`(postgres 서비스).

---

## Phase 1: Setup (인프라 스캐폴딩)

**Purpose**: PostgreSQL 구동·접속과 커널의 Django 앱 승격. T001~T004는 관찰
가능한 동작이 없는 순수 스캐폴딩(test-first 예외), T005는 CI 계약 변경이므로
test-first.

- [ ] T001 [P] `docker-compose.yml` 작성 — postgres:16 서비스, `POSTGRES_DB/USER/PASSWORD` 로컬 기본값(비밀 아님), healthcheck, 5432 포트 (research R1)
- [ ] T002 [P] `pyproject.toml` deps에 `psycopg[binary]>=3.2` 추가 + `uv sync`(uv.lock 갱신)
- [ ] T003 `config/settings/base.py` DATABASES를 PostgreSQL로 — `POSTGRES_HOST/PORT/DB/USER/PASSWORD` 환경변수(기본값 = compose 값), `config/settings/ci.py`는 base 상속 확인 (T002 이후)
- [ ] T004 `shared_kernel`의 Django 앱 승격 — `shared_kernel/apps.py`(SharedKernelConfig), `shared_kernel/migrations/__init__.py`, **`shared_kernel/models.py`(모델 애그리게이터 — Django는 `<app>.models`만 자동 탐색하므로 T040·T051이 여기서 각자의 모델 모듈을 import 등록한다)**, `config/settings/base.py` INSTALLED_APPS 등록. 도메인 계층(`apps/`) 아님 — tach.toml 변경 없음(plan Structure Decision). **주의(리뷰 BLOCKER 반영)**: 패키지 `__init__.py`는 앱 로딩 시점에 실행되므로 ORM 심볼의 eager import 금지 — 공개 표면 re-export는 T070의 지연(lazy) 전략을 따른다
- [ ] T005t `tests/ci/test_ci_contract.py` 확장 + RED 증거 — `quality-gate` 잡에 (6) `services.postgres`(이미지·healthcheck) 존재, (7) 잡 env에 `POSTGRES_*` 접속 변수 존재 단언 추가. 기존 고정 필드(잡 id·trigger·스텝 순서·skip 금지) 단언은 불변 (research R1)
- [ ] T005 `.github/workflows/ci.yml`에 postgres 서비스 컨테이너 + 잡 env 추가 (선행: T005t 작성+RED / 완료 조건: T005t GREEN — 기존 계약 필드 불변. `.github/workflows/`는 CODEOWNERS 소유 경로)

**Checkpoint**: `docker compose up -d postgres` + `uv run python manage.py migrate`(no-op) + `uv run python manage.py check` 통과.

---

## Phase 2: Foundational — 상관관계 컨텍스트 (전 스토리의 전제)

**Purpose**: correlation은 멱등·감사·이벤트(US2~US4)가 모두 기록 시점에 읽는
전제 primitive다(FR-010). 관통 통합 검증은 US5가 수행한다.

- [ ] T010t 상관관계 컨텍스트 테스트 작성 + RED 증거 — `tests/kernel/test_correlation.py`: 미설정 시 접근에서 발급·흐름 고정 / `bind_correlation_id` reset token / `reset_correlation_id`·`correlation_context()`로 요청 경계 종료 후 누출 없음 / **새 스레드 비상속(독립 발급) + `copy_context()` 래핑 시 동일 correlation 유지**(R6 규약, K-11)
- [ ] T010 `shared_kernel/correlation.py` 구현 — contextvars 기반 `get_correlation_id`/`bind_correlation_id`/`reset_correlation_id`/`correlation_context` (선행: T010t 작성+RED / 완료 조건: T010t GREEN)

**Checkpoint**: correlation 단독 GREEN — user story 착수 가능.

---

## Phase 3: User Story 1 — 금액을 안전하게 표현·연산한다 (Priority: P1) 🎯 MVP

**Goal**: 부동소수점이 구조적으로 침투할 수 없는 Money(최소 단위 정수) +
명시적 반올림 + 합계 보존 안분.

**Independent Test**: quickstart 시나리오 1~3 — 다른 primitive 없이 Money
단독으로 생성·연산·반올림·안분·오류 케이스 전부 검증(DB 불필요).

### Tests for User Story 1 (write FIRST — RED 확인 후 구현) ⚠️

- [ ] T020t [US1] `tests/kernel/test_money.py` 작성 + RED 증거 — 생성은 minor-unit `int`만(K-1: `float` **및 `Decimal` 인스턴스** 생성·연산 전 경로 거부 — R2) / 통화 획득은 `Currency.of(code)`(미등록 코드 거부 — BR-2), `Currency.register(code, exponent)`로 테스트용 제2통화(USD) 등록 후 교차 검증, **위조 인스턴스**(`Currency("KRW", 다른 지수)` 직접 생성)는 레지스트리 대조로 거부 / 같은 통화 덧셈·뺄셈·`* int`·비교 결정론(SC-001, 동일 입력 반복 단언) / 통화 불일치 산술·비교 거부(K-2) / `multiply` 스칼라는 `int`·정확 십진 문자열·`Fraction`만 + **반올림 정책 인자 필수**(K-3 — 누락 시 거부, 4개 정책 어휘 각각의 결정론 결과) / **내부 float 부재의 기계 검증(SC-002)**: `money.py` AST 검사 — float 리터럴·`float()` 호출·진수 나눗셈(`/`) 0건(`//`·`divmod` 허용) + 2^53 초과 액수(예: 2^60원)의 생성·산술·multiply 정확성 케이스(float 경유 시 정밀도 손실로 탐지) (US1 #1~4)
- [ ] T021t [P] [US1] `tests/kernel/test_money_allocation.py` 작성 + RED 증거 — 다수 입력(원금×가중치×분할 수)에서 몫 합 − 원금 = 0(SC-008) / 귀속 정책(LARGEST_REMAINDER·FIRST·LAST) 각각 결정론 + **정책 인자 필수** / 10,000원 3등분 → 3,334/3,333/3,333(US1 #5) / 경계 입력: 빈 목록·가중치 합 0·음수 가중치 → 정의된 오류, 분할 수 1 → 원금, 음수 원금 → 부호 유지 분배 / **T021 구현 후 내부 float 부재 재검증**: T020t의 AST 검사를 전체 `money.py`에 다시 적용 + 2^60원 안분 정확성(R3, K-4, SC-002)

### Implementation for User Story 1

- [ ] T020 [US1] `shared_kernel/money.py` 구현 — `Currency`(frozen, 획득은 `Currency.of(code)` 클래스메서드가 유일 정상 경로, `Currency.register(code, exponent)` 등록 — 같은 값 재등록은 무해·다른 값은 거부, 직접 생성 인스턴스는 연산 시 레지스트리 대조)·초기 KRW(지수 0)·`Money`(frozen dataclass, `amount_minor: int`)·`RoundingPolicy` 4종(stdlib decimal 상수 대응)·산술/비교/`multiply`(스칼라 타입 검증, 문자열은 `Decimal(str)` 정확 변환 — 내부에 float 경로 없음) (선행: T020t 작성+RED / 완료 조건: T020t GREEN)
- [ ] T021 [US1] `shared_kernel/money.py`에 `allocate(weights, remainder_policy)` — floor 분배 + largest-remainder 계열 끝전 귀속, `RemainderPolicy` 어휘 (선행: T021t 작성+RED, T020 완료(같은 파일) / 완료 조건: **T020t·T021t 모두 GREEN**)

**Checkpoint**: US1 완결 — quickstart 시나리오 1~3 GREEN (BR-8: 스칼라 곱+반올림 조합의 안분 흉내는 이후 리뷰 규약 — 커널은 allocate만 제공).

---

## Phase 4: User Story 2 — 도메인 이벤트를 계약대로 발행한다 (Priority: P2)

**Goal**: 확장 봉투 강제 + 발행/디스패치 분리 + 부수 효과 등급 선언.

**Independent Test**: quickstart 시나리오 4 — 시험용 이벤트 정의 → 발행 → 봉투
검증 → 핸들러 수신까지 커널 안에서 단독 검증(DB 불필요, correlation은 Phase 2 산출).

### Tests for User Story 2 (write FIRST — RED 확인 후 구현) ⚠️

- [ ] T030t [US2] `tests/kernel/test_events.py` 작성 + RED 증거 — 완전한 봉투의 발행·수신(event_id·event_type·occurred_at·aggregate_type+id·payload_version·correlation_id·causation_id 전수 판독, US2 #1) / **payload 재귀 불변성**: 생성 후 원본 dict/list 변경이 봉투에 영향 없음 + 핸들러의 중첩 payload 변경 시도 거부(K-14) / 필수 필드 누락 발행 거부(K-5, SC-003) / **호출자 지정 `occurred_at` 거부**(K-13 — backdate 불가) / 복수 핸들러 실행 + 예외 전파(US2 #3) / **디스패처 교체는 `use_dispatcher()` 컨텍스트로 — 발행 코드 불변 확인**(US2 #4, 기록용 시험 디스패처) + **구독은 `subscribe(..., dispatcher=target)`로 등록 대상을 명시**(생략 시 기본 SyncDispatcher) + 구독 레지스트리는 디스패처 인스턴스 소유 — 새 SyncDispatcher 주입으로 테스트 간 전역 누출 없음 단언 / **등급 누락 등록 거부 + EXTERNAL 등급 동기 등록 거부**(K-6, US2 #5)

### Implementation for User Story 2

- [ ] T030 [US2] `shared_kernel/events.py` 구현 — `EventEnvelope`(frozen, occurred_at·event_id 시스템 부여, correlation은 컨텍스트에서, **JSON-like payload를 방어 복사 후 mapping/list를 재귀 불변화**)·`publish()`·`subscribe(event_type, handler, *, side_effect, dispatcher=None)`(**등록 대상 명시**, `None`이면 기본 SyncDispatcher)·`Dispatcher` 프로토콜(`dispatch`만 요구)·`SyncDispatcher`(**구독 레지스트리를 인스턴스로 소유**, EXTERNAL 거부)·**현재 발행 디스패처는 contextvar — `use_dispatcher(dispatcher)` 컨텍스트 매니저로 교체**(발행 코드 불변 + 테스트 격리, 기본값은 모듈 기본 SyncDispatcher)·`SideEffect`·`HandlerRegistrationError` (선행: T030t 작성+RED / 완료 조건: T030t GREEN)

**Checkpoint**: US2 완결 — quickstart 시나리오 4 GREEN.

---

## Phase 5: User Story 3 — 재시도해도 효과는 한 번이다 (Priority: P3)

**Goal**: 스코프 멱등키 + DB 유니크 2단계 클레임 + fenced 전이(지문 보존
tombstone·COMPLETED 불변) — contracts/idempotency-protocol.md가 계약.

**Independent Test**: quickstart 시나리오 5~6 — 시험용 부수 효과(카운터)를
보호해 재시도·충돌·동시성·상태 전이를 커널 안에서 단독 검증(PostgreSQL 필요).

### Tests for User Story 3 (write FIRST — RED 확인 후 구현) ⚠️

- [ ] T040t [US3] `tests/kernel/test_idempotency.py` 작성 + RED 증거 — **파일의 DB 테스트는 전부 `django_db(transaction=True)`**(pytest-django 기본 atomic 래퍼가 외부 atomic 거부를 오탐하지 않게 함) / 같은 범위·키 3회 → 효과 1회·동일 결과(US3 #1) / 같은 키·다른 지문 → `IdempotencyConflict`(US3 #2) + **버전 불일치도 충돌**(같은 canonical 결과라도 `fingerprint_version`이 다르면 `IdempotencyConflict` — 비교 단위는 (version, fingerprint) 쌍) + **correlation만 다른 재시도는 통과**(지문에 추적 메타데이터 제외 — FR-005) / 다른 scope·같은 키 문자열 → 독립(US3 #4) / 동시 도착(스레드 경합, **DB-backed 카운터**) → 커밋 효과 정확히 1회(US3 #3, SC-004) / **테스트 본문에서 연 `transaction.atomic()` 안에서 호출 → 실행·클레임 없이 `TransactionManagementError`**(클레임 독립 커밋 보장) / 진행 중(미만료) 재시도 → InProgress 신호·재클레임 없음(US3 #6) / **TTL 경과 재시도 → fenced 재클레임(이전 실행 생존 여부와 무관하게 안전)**: 새 claim_token 발급 후, 아직 살아 있던 이전 실행의 완료 마킹이 LostClaimError로 비즈니스 트랜잭션 전체 롤백됨 → **DB 커밋 효과는 항상 최대 1회**(FR-005 — 짧은 TTL 주입으로 검증) / **확정 실패 → 지문 보존 tombstone**: 같은 지문 재시도만 원자 재클레임(US3 #5), 다른 지문은 실패 후에도 거부(K-8) / UNKNOWN → 자동 재실행 금지 신호(US3 #7), `mark_unknown`은 claim_token·판정 근거 필수·IN_PROGRESS에서만, 해소는 근거 참조 필수·UNKNOWN에서만(US3 #8), 해소 후 COMPLETED는 결과 반환·DEFINITE_FAILURE는 같은 지문만 재실행 / **COMPLETED 불변** — mark_unknown 시도 및 공개 ORM의 `save/create/update/delete/bulk_*` 직접 상태 변경 거부(K-9) / 상태별 필수 필드 DB CheckConstraint 거부 / canonicalizer 주입 동작(BR-4) / **신규 프로세스에서 django.setup 직후 앱 레지스트리에 IdempotencyRecord가 존재**(`models.py` 자동 발견; 최종 정확 집합은 T051t/T070t가 소유)

### Implementation for User Story 3

- [ ] T040 [US3] `shared_kernel/idempotency.py` + `shared_kernel/migrations/0001_idempotency.py` 구현 — `IdempotencyRecord` 모델(`(namespace, scope, key)` 유니크·4상태·claim_token·TTL·근거 필드, **공개 `objects`는 조회 전용**이고 생성·수정·삭제·bulk 경로 전부 거부, 쓰기는 모듈 내부 전이 manager/repository만 사용, **상태별 필수 필드 DB CheckConstraint**, **`shared_kernel/models.py`에 import 등록** — T004) · `canonical_json` · `run_idempotent(..., fingerprint_version, canonicalize=, in_progress_ttl=기본 60초, now=)`(**진입 시 `connection.in_atomic_block`이면 `TransactionManagementError`** — ①의 독립 커밋 보장, TTL·시계 주입점, 지문 비교는 (version, fingerprint) 쌍, 2단계 클레임, 전 전이 fenced 조건부 UPDATE + 영향 행 검사) · `mark_unknown`/`resolve_unknown_as_*` · 신호 타입(`IdempotencyConflict`·`InProgress`·`UnknownOutcome`·`LostClaimError`). operation의 "순수 내부(DB 트랜잭션 내 효과)" 한정은 기계 검증 불가 — 계약 문서·리뷰 소관이며 테스트 효과는 DB-backed로 검증 (선행: T040t 작성+RED / 완료 조건: T040t GREEN — 프로토콜 문서와 1:1)

**Checkpoint**: US3 완결 — quickstart 시나리오 5~6 GREEN.

---

## Phase 6: User Story 4 — 모든 개입은 불변 감사 사실을 남긴다 (Priority: P4)

**Goal**: 불변 감사 사실(대상 타입·근거 참조 필수, 모델 계층 + DB 트리거
2층 강제) + 행위자 역할 어휘.

**Independent Test**: quickstart 시나리오 7~8 — 시험 대상에 기록·조회·불변성을
커널 안에서 단독 검증(PostgreSQL 필요).

### Tests for User Story 4 (write FIRST — RED 확인 후 구현) ⚠️

- [ ] T050t [P] [US4] `tests/kernel/test_actors.py` 작성 + RED 증거 — OPERATOR·VENDOR·CUSTOMER·SYSTEM 구분 제공, `Actor(role, actor_id)` (US4 #4, FR-007)
- [ ] T051t [P] [US4] `tests/kernel/test_audit.py` 작성 + RED 증거 — **파일의 DB 테스트는 전부 `django_db(transaction=True)`이고 성공 경로만 본문에서 명시적 atomic을 연다** / 전 필수 필드(행위자·역할·대상 **타입+ID**·사유·근거 참조·correlation) 기록·조회(US4 #1, SC-005) / 행위자·근거 참조·대상 타입 누락 → 거부(US4 #3) / 기록 후 수정·삭제 → 모델·queryset 경로 거부(US4 #2) + **raw SQL UPDATE/DELETE → DB 트리거가 거부**(K-10, R5) / **호출자 지정 `recorded_at` 거부**(K-13) / **열린 atomic 블록 밖(autocommit)에서 `record_audit_fact` → 거부**(FR-006 원자성 강제) / 공개 `AuditFact.objects`의 `create/get_or_create/update_or_create/bulk_create/update/bulk_update/delete`는 atomic 내부·외부와 무관하게 전부 거부(조회 전용 모델) / 호출자 트랜잭션 롤백 시 감사 기록 동반 롤백 / reason_code 선택 필드(SHOULD) / **신규 프로세스에서 django.setup 직후 앱 레지스트리 모델 집합 = {IdempotencyRecord, AuditFact}**(`models.py` 자동 발견)

### Implementation for User Story 4

- [ ] T050 [US4] `shared_kernel/actors.py` 구현 — `ActorRole` enum·`Actor` (선행: T050t 작성+RED / 완료 조건: T050t GREEN)
- [ ] T051 [US4] `shared_kernel/audit.py` + `shared_kernel/migrations/0002_audit.py` 구현 — `AuditFact` 모델(append-only, recorded_at 시스템 부여, **공개 `objects`는 조회 전용** — save/create/get-or-create/update-or-create/bulk create·update/delete 전부 거부, **`shared_kernel/models.py`에 import 등록** — T004)·`record_audit_fact()`(**ORM 호출 전에** `connection.in_atomic_block` 검사로 호출자 autocommit 거부 후 모듈 내부 insert manager/repository 사용 — ORM이 자체 atomic을 여는 우회 차단, 호출자 트랜잭션 참여) + 마이그레이션에 **append-only 트리거 RunSQL**(UPDATE·DELETE 시 예외) (선행: T051t 작성+RED, T050 완료(Actor 사용), **T040 완료(마이그레이션 0002가 0001에 의존 — 아래 Dependencies)** / 완료 조건: T051t GREEN)

**Checkpoint**: US4 완결 — quickstart 시나리오 7~8 GREEN.

---

## Phase 7: User Story 5 — 하나의 요청 흐름을 관통 추적한다 (Priority: P5)

**Goal**: 멱등 기록·감사 사실·이벤트가 같은 correlation으로 연결됨을 커널 수준
통합으로 실증(FR-010·SC-007). correlation primitive 자체는 Phase 2 산출 —
GREEN은 US2~US4 완료 후에만 가능하지만, **테스트 작성은 구현 전에 한다**
(신규 동작이므로 test-first — 헌장의 GREEN-시작 허용은 레거시 특성화 한정,
리뷰 반영).

- [ ] T060t [US5] `tests/kernel/test_correlation.py`에 관통 통합 케이스 작성 + RED 증거 — **Phase 2 완료 직후 작성**(미구현 primitive의 ImportError로 옳은 이유의 RED), DB 통합 케이스는 `django_db(transaction=True)` 사용: 하나의 흐름(`run_idempotent`가 소유한 operation atomic 안에서 감사 기록 + 이벤트 발행)에서 세 기록이 같은 correlation으로 연결 조회(US5 #1, SC-007) / 미설정 흐름 → 시스템 발급 후 세 기록 공유(US5 #2) (선행: T010 완료 + 작성·RED 증거 / 완료 조건: **T030·T040·T051 완료 후 GREEN 확인** — 별도 구현 태스크 없음, 세 primitive의 correlation 기록이 구현이다)

**Checkpoint**: US5 완결 — quickstart 시나리오 9 GREEN.

---

## Phase 8: 공개 표면 확정 & Spec 000 개정 (cross-cutting)

**Purpose**: BR-7·FR-008 — 커널 공개 표면을 contracts 열거와 1:1로 특성화하고,
Spec 000의 빈-커널 특성화를 예고된 대로 대체한다.

- [ ] T070t 공개 표면 특성화 테스트 작성 + RED 증거 — `tests/kernel/test_public_surface.py`: (1) **계약 문서 파싱** — contracts/kernel-public-surface.md의 `EXPECTED_PUBLIC_SURFACE` 코드 블록을 파싱해 `shared_kernel.__all__`과 정렬 포함 정확 일치, (2) **각 심볼 실재** — `getattr(shared_kernel, name)` 전수 성공(문자열만 맞는 유령 심볼 차단), (3) **초과 공개 금지** — `dir()`의 공개 이름 중 `__all__`·정확한 내부 모듈 allowlist(`actors`, `apps`, `audit`, `correlation`, `events`, `idempotency`, `migrations`, `models`, `money`) 밖 항목 0건 + `pkgutil.iter_modules(shared_kernel.__path__)` 결과가 이 정확 집합과 일치(모든 서브모듈을 포괄 제외하는 구멍 금지), (4) **신규 프로세스 기동·모델 발견 검증** — subprocess에서 `django.setup()` 직후(루트 lazy `getattr` 호출 전) shared_kernel 앱의 모델 집합이 `{IdempotencyRecord, AuditFact}`와 정확 일치하고 `manage.py check` 성공(BLOCKER 반영: 조기 import와 빈 models.py 양쪽 방어) (K-12, SC-006)
- [ ] T070 `shared_kernel/__init__.py` 공개 표면 re-export — **31개 심볼** `__all__` 열거. **ORM 의존 심볼(멱등·감사 계열)은 PEP 562 모듈 `__getattr__`로 지연(lazy) re-export**(앱 로딩 시점의 eager 모델 import 금지 — BLOCKER 반영), 순수 심볼(Money·이벤트·correlation·actors)은 eager 가능 (선행: T070t 작성+RED, T010~T060t 완료 / 완료 조건: T070t GREEN)
- [ ] T071 `tests/conformance/test_fixture_scope.py` 개정 — `test_shared_kernel_is_empty` 제거(T070t가 공개 이름+내부 모듈 정확 집합 검사의 후계 — BR-7 예고된 제약 변경, 특성화 개정 의도를 커밋에 기록) + 이제 쓰지 않는 `pkgutil` import 제거. 픽스처 allowlist·models 0 단언은 불변 (선행: T070 완료)

**Checkpoint**: `uv run pytest` 전체 GREEN + `uv run tach check` 통과(커널 경계 불변 — SC-006).

---

## Phase 9: Polish & Cross-Cutting

- [ ] T080 quickstart.md 시나리오 1~11 전체 실행, 결과(명령·출력 요약·RED→GREEN 증거)를 `specs/001-shared-kernel-primitives/evidence/quickstart-run.md`에 기록 (원칙 XVII)
- [ ] T081 품질 마감 (T080 이후 — SC 매핑이 실행 증거를 참조) — `uv run ruff check .` 0건, `uv run tach check` 통과, `uv run python manage.py check` 통과, CI `quality-gate`(postgres 포함) GREEN, SC-001~008 최종 대조(각 SC ↔ 통과 테스트/`evidence/quickstart-run.md` 매핑)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1(Setup)** → Phase 2 → US 착수. T005t→T005는 Phase 1 내 test-first 쌍.
- **US1(P1)**: Phase 2와 독립(DB·correlation 불필요) — 실질적으로 Phase 1의
  T002(의존성)만 필요. T020t·T021t → T020 → T021.
- **US2(P2)**: Phase 2(correlation) 이후. T030t → T030.
- **US3(P3)**: Phase 1(DB)·Phase 2 이후. T040t → T040.
- **US4(P4)**: Phase 1(DB)·Phase 2 이후, **그리고 T040(US3 구현) 이후** —
  마이그레이션 0002_audit이 0001_idempotency에 그래프상 의존하므로 US4는
  US3에 의존한다(리뷰 반영: "독립·병렬" 선언 철회. 테스트 작성 T050t·T051t는
  병렬 가능, 구현 T051만 순차). T050t·T051t → T050 → T051.
- **US5(P5)**: T060t 작성·RED는 Phase 2 직후 가능, GREEN 확인은 US2·US3·US4
  완료 후.
- **Phase 8**: 전 스토리 완료 후(표면이 완성되어야 열거 일치). **Phase 9**: 마지막.

### Parallel Opportunities

- Phase 1: T001 ∥ T002 (다른 파일)
- 테스트 작성: T020t ∥ T021t ∥ T030t ∥ T040t ∥ T050t ∥ T051t (모두 다른 파일 —
  단 각 target 구현 전 RED 확인은 스토리별로. T060t는 같은 파일인 T010t 이후)
- 스토리 간: US1 ∥ US2 ∥ US3는 서로 다른 파일이라 병렬 가능. US4 구현(T051)은
  US3 구현(T040) 이후(마이그레이션 그래프 의존)
- Phase 9: T080 → T081 (순차 — 증거 참조)

---

## Implementation Strategy

### MVP First (US1만)

1. Phase 1의 T002 → US1(T020t~T021) 완료 — **DB 없이도 Money 단독 가치 성립**
2. STOP & VALIDATE: quickstart 시나리오 1~3으로 US1 단독 검증

### Incremental Delivery

1. Setup + Foundational → correlation 준비
2. US1(Money) → 독립 검증 (MVP)
3. US2(이벤트) → US3(멱등) → US4(감사·역할) → 각각 독립 검증
4. US5(관통) → Phase 8(표면 확정·Spec 000 개정) → Polish → Spec 001 완료
5. 커밋 관례: phase당 1커밋(`Spec 001 impl: ...`로 최종 통합) — 반영은
   브랜치 → PR → quality-gate → squash

---

## Notes

- RED 확인은 실행 증거로 남긴다(원칙 XVII) — T080에서 최종 취합.
- US3·US4 테스트는 PostgreSQL 의미론이 전제(R1) — SQLite 폴백 금지.
- `.github/workflows/ci.yml` 변경(T005)은 CODEOWNERS 소유 경로 — 리뷰 게이트
  유예 중이나 PR 경유는 동일.
- Spec 000 특성화 개정(T071)은 예고된 제약 변경(spec Assumptions) — 개정
  의도를 커밋 메시지에 남겨 "몰래 완화"와 구분한다.

---

## Constitution Gate & Traceability

*구현 시작 전 tasks 수준 Constitution Check. 코어 게이트 7개는 항상 기재하며,
plan.md Constitution Check에서 트리거된 조건부 원칙(XII·XIII·XV-감사)을 함께
기재한다.*

| Principle (core always; conditional if triggered) | Disposition | Task IDs / evidence link / N/A rationale |
|---|---|---|
| I — Tests precede implementation (core) | **Task** | T005t→T005, T010t→T010, T020t·T021t→T020·T021, T030t→T030, T040t→T040, T050t·T051t→T050·T051, T060t(작성·RED는 구현 전 — GREEN은 US2~4 완료 시), T070t→T070. 스캐폴딩 예외: T001~T004(FR-009 예외 경로) |
| III — Marketplace first (core) | **N/A** | 벤더·마켓플레이스 도메인 없음 — 역할 어휘(VI 소관)만 제공, 벤더 모델링은 P1 |
| IV — Immutable snapshots (core) | **N/A** | 주문·스냅샷 없음 — 이벤트 payload_version은 T030(FR-003), 스냅샷 버전은 P5 |
| V — Money type & rounding (core) | **Task** | T020t·T020(표현·정책), T021t·T021(안분 합계 보존), ADR 0005 |
| VI — Vendor isolation & authorization (core) | **Task(부분)** | T050t·T050(역할 어휘) — 실제 인가 강제는 P1(spec Scope #3) |
| VII — Modular monolith (core) | **Task** | T004(커널 앱 승격 — 도메인 계층 아님), tach 계약 불변(T081에서 확인) |
| VIII — Domain boundaries (core) | **Task** | T070t·T070·T071(공개 표면 특성화 — BR-7), 커널 단방향은 Spec 000 기계 강제 상시(T081 tach check) |
| XII — Domain events (triggered) | **Task** | T030t·T030(확장 봉투·발행/디스패치 분리·동기 MAY 경로) |
| XIII — Idempotency & messaging (triggered) | **Task** | T040t·T040(스코프 키·DB 유니크·fenced 전이·tombstone — 신뢰 전달 계약은 동기 한정 비트리거, T030의 EXTERNAL 등급 거부가 경계 유지) |
| XV-감사 (triggered, 부분) | **Task** | T050t·T051t·T051(불변 감사 사실 primitive — 2층 강제·원자 기록) |

- **조건부 비트리거 확인**(plan Constitution Check 승계): IX(외부 시스템 0 —
  psycopg는 저장소 드라이버)·X(프로모션)·XI(역방향)·XIV(자원 선점)·XV-대사(외부
  금액·재고 경계)·XVI(자동/스케줄 상태 변경)·XVII(레거시 재사용)는 현 스펙
  범위에서 트리거되지 않는다.
- 모든 코어 게이트에 Disposition 기재 완료(Waiver 없음, Complexity Tracking 비어
  있음). **Constitution Check 결과: PASS**(위반 없음). tasks-stage 변경이
  역전파된 plan의 사람 재승인과 이 문서의 최종 사람 승인 완료(cray.j, 2026-07-10)
  — 구현 착수 가능.

---

## Go-live Enablement & Readiness

**N/A** — XV-대사(외부 금액·재고 경계)·XVI(자동/스케줄 상태 변경) 모두
비트리거(plan Constitution Check). 멱등 TTL은 재시도 시점 판정이지 스케줄
배치가 아니며, 외부 연동이 없다. go-live 게이트 항목은 해당 원칙이 트리거되는
P3·P6 이후 Phase에서 생성된다.
