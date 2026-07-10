# Phase 0 Research: Foundation — Shared Kernel Primitives

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-09

스펙이 계약(WHAT)을 3회의 적대 리뷰로 확정했으므로, 리서치는 **그 계약을 배반하지
않는 구현 선택(HOW)의 근거 확정**이다. Technical Context에 남은
`NEEDS CLARIFICATION`은 없다.

---

## R1. 저장소 — PostgreSQL 16 (+psycopg 3)

- **Decision**: PostgreSQL 16, 드라이버 psycopg[binary] 3.2+. 로컬은
  `docker-compose.yml`, CI는 GitHub Actions `services:` postgres 컨테이너
  (healthcheck 포함). **접속 계약 고정**: `POSTGRES_HOST/PORT/DB/USER/PASSWORD`
  환경변수 — 코드 기본값은 로컬 compose 값(비밀 아님), CI는 `quality-gate` 잡
  env로 동일 변수를 주입한다. CI 계약 테스트에 postgres 서비스·env 존재 단언을
  추가한다(tasks에서 — 누락 시 pytest가 접속 실패로 조용히가 아니라 시끄럽게
  죽지만, 계약으로 고정해 드리프트를 막는다).
- **Rationale**: 이 스펙이 프로젝트 최초의 영속 요구(멱등 기록·감사 사실)를
  가져오며, 스펙의 동시성 계약(SC-004: 동시 도착 효과 1회)은 **DB 유니크 제약의
  동시 INSERT 대기·충돌 의미론**으로 구현된다. SQLite는 단일 작성자 잠금이라
  이 의미론의 프로덕션 대표성이 없다 — "테스트는 통과했지만 운영 DB에서 다른
  거동"은 원칙 XVII(근거 기반 검증)가 금지하는 상황이다. Django 생태 1순위
  지원이며 운영 이행(매니지드 PG) 경로가 직선이다.
- **Alternatives considered**:
  - SQLite(지금) → PostgreSQL(배포 시): 동시성 의미 상이 + 이중 전환 비용, 탈락.
  - MySQL: 사내 레거시 관례이나 Django 정합성·기능(트랜잭션 DDL 등) 열위, 탈락.
- **CI 영향**: `quality-gate` 잡에 `services: postgres` 블록 추가. CI 계약
  테스트가 고정한 필드(잡 id·trigger·스텝 순서·continue-on-error/if 부재)는
  불변 — services 추가는 계약 위반이 아님(테스트로 확인하며 진행).

## R2. Money 내부 표현 — 통화 최소 단위 정수(minor units)

- **Decision**: 액수를 **통화 최소 단위의 int**로 저장하는 불변 값 객체
  (`@dataclass(frozen=True, slots=True)`). 통화는 정밀도 레지스트리(초기 KRW,
  소수부 0)에 등록된 것만 허용. Money 생성의 기본 경로는 minor-unit `int`이고,
  `float` 직접 입력은 생성·연산 전 경로에서 즉시 거부한다. `Decimal` 값이
  바이너리 float에서 만들어졌는지는 객체만으로 기계 판별할 수 없으므로,
  **생성·연산 어느 경로에서도 `Decimal` 인스턴스를 받지 않는다**(동일 근거의
  일관 적용 — 생성만 막고 곱셈에서 받으면 `Decimal(0.1)` 오염 경로가 열려
  SC-002를 증명할 수 없다, 적대 리뷰 반영). 비정수 스칼라 곱·비율은 **정확
  십진 문자열**(내부에서 `Decimal(str)`로 정확 변환) 또는
  `fractions.Fraction`으로 받고 **반올림 정책 인자 필수**다.
- **Rationale**: 부동소수점 금지(BR-1)를 런타임 검사가 아니라 **표현 구조**로
  강제 — int에는 반올림 오차 자체가 없다. 정수 연산은 결정론(SC-001)이 자명하고,
  안분(R3)이 정수 나눗셈·나머지로 정확해진다.
- **Alternatives considered**:
  - `Decimal` 저장: 표현력은 있으나 `Decimal(0.1)` 같은 float 유래 생성 함정을
    객체 수신 시점에 판별할 수 없고, 스케일 정규화 관리가 필요하다. 탈락.
  - float: 헌장 V가 금지. 탈락.
- **반올림 정책 어휘**: `ROUND_DOWN`(절사)·`ROUND_UP`(올림)·`ROUND_HALF_UP`
  (사사오입)·`ROUND_HALF_EVEN`(은행가) 4종을 표준 어휘로 제공 — stdlib
  `decimal`의 검증된 상수에 대응시킨다. **기본값은 없다**(FR-002).

## R3. 안분 알고리즘 — largest remainder + 명시적 끝전 귀속

- **Decision**: 비율/가중치 안분은 (1) 각 몫을 내림(floor)으로 산출, (2) 잔여
  최소 단위 n개를 **끝전 귀속 정책**에 따라 분배하는 largest-remainder 계열로
  구현한다. 귀속 정책 어휘: `LARGEST_REMAINDER`(잔여가 큰 몫 우선, 동률은 앞
  순서)·`FIRST`(앞에서부터)·`LAST`(뒤에서부터) — 정책 인자는 필수(암묵 기본값
  금지, FR-011).
- **Rationale**: floor 합계는 항상 원금 이하이고 잔여는 분할 수 미만의 정수이므로
  **합계 보존(SC-008)이 구성적으로 보장**된다. 귀속 순서를 정책으로 분리하면
  "누가 1원을 더 받는가"라는 재무 결정이 소비 스펙의 명시적 선택으로 남는다(BR-8).
- **Alternatives considered**: 몫별 독립 반올림(합계 미보존 — BR-8이 금지하는
  바로 그 형태), 확률적 배분(비결정론 — SC-001 위반). 모두 탈락.
- **경계 입력 거동(FR-011)**: 빈 목록 → 정의된 오류; 가중치 합 0 → 정의된 오류;
  분할 수 1 → 원금 그대로; 음수 원금 → 허용(부호 유지 분배 — Money가 부호를
  허용하므로), 음수 가중치 → 정의된 오류.

## R4. 멱등 직렬화 — DB 유니크 기반 2단계 클레임 프로토콜

- **Decision**: `IdempotencyRecord`에 `(namespace, scope, key)` 복합 유니크
  제약과 `claim_token` fencing을 둔다. 실행 절차: **① 클레임 트랜잭션** —
  `claim_token`을 가진 IN_PROGRESS 레코드 INSERT 후 즉시 커밋(유니크 충돌 시:
  기존 레코드를 읽어 COMPLETED면 저장된 결과 반환, IN_PROGRESS면 "진행 중"
  응답, UNKNOWN이면 "불확정" 응답, DEFINITE_FAILURE면 결과 캐시 없이 새 claim,
  만료된 IN_PROGRESS는 새 token fencing 아래 원자적 재클레임)
  → **② 비즈니스 트랜잭션** — 연산 실행 + 같은 트랜잭션에서
  `claim_token`이 일치할 때만 레코드를 COMPLETED(결과 저장)로 갱신 → 커밋.
  완료 갱신 영향 행이 0이면 stale claim이므로 전체 비즈니스 트랜잭션을 롤백한다.
  비즈니스 트랜잭션 실패(확정 실패) 시 **fenced 조건부 UPDATE**로
  `DEFINITE_FAILURE` tombstone을 남긴다(삭제 금지 — 지문을 보존해 "같은 키·다른
  요청 거부"가 실패 후에도 유지되고, stale cleanup이 남의 활성 클레임을 지우는
  경합도 구조적으로 차단된다). 같은 지문의 재시도만 원자적으로 재클레임된다.
  `run_idempotent`는 ①의 독립 커밋을 보장하기 위해 이미 열린 외부
  `transaction.atomic()` 안에서의 호출을 실행 전에 거부한다. Django의 중첩
  atomic은 커밋이 아니라 savepoint라 다른 연결에 IN_PROGRESS가 보이지 않기
  때문이다. 공개 `IdempotencyRecord.objects`는 조회 전용이고, 쓰기는 모듈 내부
  전이 경로만 사용하며 상태별 필수 필드 조합은 DB CheckConstraint로 고정한다.
- **Rationale**: 스펙의 네 상태 시나리오가 이 프로토콜의 자연 귀결이다 —
  완료 재시도=결과 반환(①의 충돌 분기), 진행 중=클레임 가시성(①이 선커밋이라
  관측 가능), 확정 실패=지문 보존 tombstone에서 같은 지문만 재클레임. COMPLETED는
  종결·불변이며 mark_unknown을 포함한 모든 전이가 상태·token 조건부다. TTL은
  재클레임 시점만 정하고, 안전성은 새 `claim_token`이 이전 실행의 완료 마킹을
  차단해 stale claim의 전체 DB 트랜잭션을 롤백하는 fencing이 제공한다. 따라서
  이전 실행의 생존 여부를 판별하지 않아도 커밋 효과는 최대 1회다. 동시 도착은
  유니크 제약이 직렬화(헌장 동시성 제어 SHOULD 채택).
  재클레임·상태 전이는 `UPDATE ... WHERE status=... AND claim_token=...` 계열의
  조건부 갱신으로 원자화한다(영향 행 수 검사 — 헌장 XIV 패턴 준용).
- **Alternatives considered**:
  - 동일 트랜잭션 클레임(1단계): 동시 요청이 유니크 대기로 블로킹되고 "진행 중"
    응답이 불가능(커밋 전 비가시) — US3 #6 위반. 탈락.
  - PostgreSQL advisory lock: 크래시 복구·가시성이 불투명하고 기록이 남지 않음.
    탈락.
- **지문(fingerprint)**: 네임스페이스가 소유하는 스키마(BR-4)에 따라 안정적
  작업 입력을 정렬 직렬화(canonical JSON) 후 SHA-256. **canonicalizer와
  `fingerprint_version`은 `run_idempotent`의 명시 파라미터**로 주입된다(커널은
  기본 `canonical_json`만 제공 — 같은 논리 입력의 표기 차이 정규화는
  네임스페이스 canonicalizer의 책임). 추적 메타데이터(correlation·시각)는
  포함 금지(FR-005) — 테스트가 "correlation만 다른 재시도"의 통과를 단언.
- **UNKNOWN**: 이 스펙 범위의 연산(내부·트랜잭션 내)은 UNKNOWN을 만들지 않는다.
  상태·전이(IN_PROGRESS→UNKNOWN, UNKNOWN→해소)는 스키마와 계약에 존재하며,
  설정·해소 주체는 외부 부수 효과 흐름(P6+)이다. UNKNOWN 판정과 해소에는
  각각 근거 참조가 필수이고, 해소는 COMPLETED 또는 DEFINITE_FAILURE로만 가능하다
  — contracts/idempotency-protocol.md.

## R5. 감사 불변 강제 — 조회 전용 공개 모델 + DB 트리거

- **Decision**: 두 층으로 강제한다. **모델 계층** — 공개 `AuditFact.objects`는
  조회 전용으로 create/get-or-create/update-or-create/bulk create·update/delete를
  모두 거부하고, 삽입은 `record_audit_fact`의 모듈 내부 manager/repository만
  수행한다. 기록 API는 ORM 호출 전에 외부 atomic 블록 존재를 확인해 autocommit을
  거부한다(ORM이 자체 atomic을 여는 우회 차단). 필수 필드(행위자·역할·대상
  타입+ID·사유·근거 참조·correlation)는 내부 삽입 전에 검증한다. **DB 계층** —
  감사 테이블을 만드는 `0002_audit`에 PostgreSQL 트리거를 포함해 UPDATE·DELETE를 DB
  수준에서 예외로 거부한다(raw SQL 경로 봉쇄 — SC-005의 "100% 거부"를 문자
  그대로 충족). 기록 API(`record_audit_fact`)는 호출자의 열린 트랜잭션에
  참여한다 — "상태 변경과 원자적 기록"(FR-006)이 구성적으로 성립한다.
- **Rationale**: SC-005는 "수정·삭제 시도 100% 거부"를 요구한다 — 모델 계층만으로는
  raw SQL이 뚫려 스펙을 완화하는 셈이 된다(적대 리뷰 반영). PostgreSQL 확정(R1)으로
  트리거가 마이그레이션 한 조각이 되어 도입 비용이 사라졌다.
- **정직한 한정**: DB 슈퍼유저의 트리거 제거·DDL은 방어 밖이다 — 권한
  분리(REVOKE·별도 롤)는 운영 DB 구성 시점(go-live 전)의 몫으로 위임하며,
  헌장 VI의 "정상 운영에서 DB 직접 수정 금지"가 그 영역을 규율한다.
- **Alternatives considered**: 모델 계층 단독(raw SQL 우회 — SC-005 미충족, 탈락),
  이벤트 소싱(과잉설계, 탈락), 권한 분리 즉시 도입(로컬 단일 사용자 DB에서 검증
  불가 — go-live 전으로 위임).

## R6. 상관관계 식별자 — contextvars 컨텍스트

- **Decision**: `contextvars.ContextVar` 기반 correlation 컨텍스트. 요청 경계
  (지금은 테스트·향후 미들웨어)가 설정하고, 미설정 시 접근 시점에 시스템이
  발급(uuid4)해 그 흐름에 고정한다(FR-010). `bind_correlation_id()`는 reset
  token을 반환하고, `reset_correlation_id()`와 `correlation_context()`가 요청
  종료 시 값을 되돌린다. 멱등 기록·감사 사실·이벤트 봉투가 기록 시점에
  컨텍스트에서 읽는다.
- **Rationale**: contextvars는 흐름 지역성의 표준 메커니즘 — 파라미터 관통(모든
  API에 correlation 인자)보다 오염이 적고, 전역 변수와 달리 동시 흐름 간 누출이
  없다. **전파 경계를 정확히**: async task에는 자동 전파되지만 **새 스레드는
  컨텍스트를 상속하지 않는다**(각 스레드 독립 — 누출 없음의 이면). 스레드
  핸드오프가 필요한 흐름은 `contextvars.copy_context()` 래핑이 명시 규약이며
  계약·테스트로 고정한다(적대 리뷰 반영 — "스레드 자동 보장" 서술 정정).
- **Alternatives considered**: 명시 파라미터 관통(모든 시그니처 오염, 누락
  실수 유발), 스레드 로컬(async 비호환), reset 없는 contextvar(순차 요청 간
  correlation 누출 위험). 탈락.

## R7. 이벤트 봉투·디스패처 — 프로세스 내 레지스트리 + 등급 선언

- **Decision**: `EventEnvelope`(frozen dataclass): `event_id`(uuid4)·
  `event_type`(안정적 문자열, 과거형 명명 — 예: `kernel.ProbeRecorded`)·
  `occurred_at`(시스템 부여)·`aggregate_type`("도메인.집계" 문자열)·
  `aggregate_id`·`payload_version`(int)·`correlation_id`·`causation_id`(선택)·
  `payload`(입력 방어 복사 + JSON-like 값 재귀 불변화). `publish(event)`는 모듈
  전역이 아닌 **주입 가능한 Dispatcher**로
  위임(기본: SyncDispatcher) — 주입점은 contextvar 기반 `use_dispatcher()`
  컨텍스트 매니저(발행 코드 불변 + 테스트 격리), 구독 레지스트리는 디스패처
  인스턴스 소유(전역 상태·테스트 누출 방지, 리뷰 반영). 핸들러 등록은
  `subscribe(event_type, handler, *, side_effect, dispatcher=None)` — 등록 대상을
  명시하고 생략 시 기본 SyncDispatcher를 사용한다. `Dispatcher` 프로토콜은
  dispatch만 요구하므로 대체 디스패처에 구독 기능을 암묵 요구하지 않는다.
  등급 선언은 필수이고
  기본값은 없다. 등급 누락은 등록 오류이며, SyncDispatcher는 `EXTERNAL` 등급
  등록을 거부한다(FR-004).
  핸들러 예외는 전파(조용한 유실 금지).
- **Rationale**: 발행/디스패치 분리(BR-3)를 인터페이스로 물화하면 P12의
  아웃박스 디스패처가 발행 코드 변경 없이 끼워진다. 등급 선언은 "외부 부수
  효과 동기 등록 금지"를 검사 가능한 계약으로 만든 스펙 결정의 직접 구현 —
  선언 진실성은 기계 검증 밖(스펙의 정직한 한정 그대로).
- **event_id에 uuid4**: 스펙 요구는 고유성뿐(정렬성 요구 없음) — 표준 라이브러리
  로 충족, 신규 의존(ULID 라이브러리) 회피. 정렬 가능 ID가 필요해지는 시점
  (아웃박스 P12)에 재검토.
- **Alternatives considered**: Django signals(봉투 강제·등급 선언·디스패처
  교체가 어긋나는 프레임워크 결합 — 원칙 II), celery 등 큐 도입(P12 사안). 탈락.

## R8. 시각 부여 — 시스템 단일 경로

- **Decision**: `occurred_at`·`recorded_at`·클레임 시각은 전부
  `django.utils.timezone.now()`(UTC aware)로 기록 시점에 시스템이 부여. 호출자
  시각 인자는 받지 않는다(FR-003·FR-006의 "호출자 임의 지정 금지"의 구현).
  테스트는 시각 주입이 아니라 관측(기록 전후 경계)으로 검증한다.
- **Rationale**: 시각 파라미터를 열어두면 "사후 재구성" 경로가 생긴다 — 스펙이
  금지한 바로 그것.

---

## Resolved unknowns

| Technical Context 항목 | 상태 |
|---|---|
| Storage | RESOLVED (R1 — PostgreSQL 16, Spec 000 위임분 만기 처리) |
| Money 표현·정책 어휘 | RESOLVED (R2) |
| 안분 알고리즘·귀속 정책 | RESOLVED (R3) |
| 멱등 직렬화·상태 전이·지문 | RESOLVED (R4) |
| 감사 불변 강제 수준 | RESOLVED (R5) |
| correlation 전파 | RESOLVED (R6) |
| 이벤트 봉투 ID·디스패처·등급 | RESOLVED (R7) |
| 시각 부여 | RESOLVED (R8) |

남은 `NEEDS CLARIFICATION`: **없음**.
