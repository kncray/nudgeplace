# Implementation Plan: Foundation — Shared Kernel Primitives

**Branch**: `001-shared-kernel-primitives` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-shared-kernel-primitives/spec.md`

> **Note (branch)**: main은 required check(`quality-gate`)로 보호되어 있어 모든
> 반영은 브랜치 → PR → squash 머지로 일어난다(phase당 1커밋 관례 유지).

## Summary

Spec 001은 Spec 000이 세운 빈 `shared_kernel`에 **다섯 primitive + 관통 추적
컨텍스트**를 채운다: Money(최소 단위 정수 표현·명시적 반올림·합계 보존 안분),
도메인 이벤트 계약(확장 봉투 + 발행/디스패치 분리 + 명시 부수 효과 등급), 멱등
실행(스코프 키·2단계 클레임·claim token fencing·확정 실패/불확정 이분), 불변 감사 사실(대상 타입·
근거 참조 필수·원자 기록), 행위자 역할 어휘, 상관관계 식별자.

기술 접근: 멱등 실행 기록과 감사 사실이 **프로젝트 최초의 영속 요구**를
가져오므로 저장소를 **PostgreSQL 16**으로 확정한다(동시성 계약의 프로덕션
대표성 — R1). Money는 부동소수점이 구조적으로 침투할 수 없는 **최소 단위 정수
(minor units)** 표현을 택하고(R2), 안분은 largest-remainder 계열 + 명시적 끝전
귀속 정책으로 합계 보존을 보장한다(R3). 멱등 직렬화는 **DB 유니크 제약 기반
2단계 클레임**(클레임 커밋 → 비즈니스 트랜잭션에서 효과+완료 마킹 원자)으로
스펙의 완료/진행 중/확정 실패/불확정 시나리오를 정확히 구현한다(R4). `UNKNOWN`
해소는 근거 참조를 필수로 갖고, correlation 컨텍스트는 reset 가능한 요청 경계를
제공한다(R6). 모든
검증은 test-first(RED→GREEN)로 진행하고, Spec 000의 빈-커널 특성화 테스트는
공개 표면 특성화로 **의도된 개정**을 거친다(BR-7).

## Technical Context

**Language/Version**: Python 3.12 (기존 — Spec 000)

**Primary Dependencies**: Django 5.2 LTS(기존) · **psycopg[binary] 3.2+**(신규 —
PostgreSQL 드라이버). 그 외 신규 런타임 의존성 없음 — 이벤트·Money·correlation은
표준 라이브러리(dataclasses·decimal·uuid·contextvars)로 구현한다(의존 최소).

**Storage**: **PostgreSQL 16** (신규 확정 — Spec 000이 위임한 결정, research R1).
멱등 실행 기록·감사 사실 두 테이블이 커널 소유로 생긴다(프로젝트 최초
마이그레이션). 로컬은 docker compose, CI는 GitHub Actions postgres 서비스 컨테이너.

**Testing**: pytest + pytest-django(기존). 멱등·감사·관통 DB 테스트는
`django_db(transaction=True)`로 pytest-django의 암묵 atomic 래퍼를 제거하고,
필요한 트랜잭션을 테스트 본문에서 명시한다. 동시성 계약(SC-004)은 스레드 기반
실제 경합과 DB-backed 효과로 검증한다.
멱등 고착 복구는 TTL 경과 후 새 claim token으로 fenced 재클레임하고,
stale claim 완료 마킹 실패 시 전체 DB 트랜잭션을 롤백해 커밋 효과를 최대 1회로
제한한다. **확정 실패 tombstone의 지문 대조
(다른 지문 거부)·COMPLETED 불변(mark_unknown 거부)**을 별도 케이스로 고정한다.
감사는 raw SQL 수정·삭제의 트리거 거부와 backdate 거부를, correlation은 스레드
비상속·copy_context 핸드오프를 케이스로 고정한다. 결정론(SC-001)·합계 보존
(SC-008)은 다수 입력 반복 검증, 공개 표면(SC-006)은 특성화 테스트. Spec 000
테스트 2건(빈 커널·픽스처 allowlist)은 의도된 제약 변경으로 개정한다(spec
Assumptions에 예고됨).

**Target Platform**: Linux 서버(CI: ubuntu-latest + postgres 서비스), 로컬
macOS/Linux(docker compose).

**Project Type**: Django 모듈러 모놀리스 — 공유 커널 확장(도메인 없음).
`shared_kernel`은 마이그레이션을 갖기 위해 Django 앱으로 승격되나 도메인 계층
(`apps/`)이 아니다 — 멱등·감사 테이블은 인프라 기록이지 도메인 모델이 아니다(BR-6).

**Performance Goals**: N/A — 도메인 트래픽이 없는 primitive 계층. 품질 목표는
성능이 아니라 **정확성·결정론·동시성 안전**이며 Success Criteria(SC-001~008)로
관리한다. (감사 기록의 처리량 우려는 스펙 FR-006 용도 한정이 다룬다.)

**Constraints**:
- 금액의 부동소수점 침투 0(SC-002) — 표현·생성·연산 전 경로에서 타입 거부.
- 정밀도 손실 연산·안분의 **암묵 기본 정책 금지**(FR-002·FR-011).
- 멱등키 유일성은 (네임스페이스, 주체 범위, 키) — **DB 유니크 제약**으로 최종
  보장(헌장 동시성 제어 SHOULD → 이 plan에서 채택).
- 멱등 재클레임은 `claim_token` fencing으로 이전 실행의 완료 마킹을 차단해야
  한다. **모든 상태 전이는 상태·token 조건부 UPDATE(fenced)로만** — 확정 실패는
  삭제가 아니라 지문 보존 tombstone(DEFINITE_FAILURE), COMPLETED는 종결·불변.
  2단계 클레임의 독립 커밋을 위해 `run_idempotent`의 외부 atomic 호출은 거부하고,
  공개 모델은 조회 전용·상태별 필드 조합은 DB CheckConstraint로 강제한다.
- 감사 사실은 상태 변경과 **동일 트랜잭션** 기록(FR-006), 공개 모델은 조회 전용,
  삽입은 외부 atomic을 먼저 확인한 전용 API만 허용하며 append-only는 모델 계층
  거부 + **DB 트리거**(raw SQL 경로 봉쇄 — `0002_audit`에 포함, R5).
  호출자 지정 시각(backdate)은 이벤트·감사 모두 거부(K-13).
- Money 스칼라는 `int`·정확 십진 문자열·`Fraction`만 — `float`·`Decimal`
  인스턴스는 생성·연산 전 경로 거부(R2, 적대 리뷰 반영).
- DB 접속은 `POSTGRES_*` 환경변수 계약으로 고정(로컬 compose 기본값, CI 잡
  env + 서비스 healthcheck — R1).
- correlation의 스레드 핸드오프는 `copy_context()` 명시 규약(R6 — 새 스레드
  비상속).
- 동기 디스패치 핸들러는 부수 효과 등급 선언 필수(기본값 없음), 외부 등급 등록
  거부(FR-004).
- 커널 공개 표면은 명시적 열거로 특성화(BR-7) — Spec 000 경계 검사(tach)는
  변경 없이 유지된다(`shared_kernel` 모듈 등록·depends_on=[] 그대로).
- test-first(RED→GREEN). 반영 관례: 브랜치 → PR → quality-gate → squash.

**Scale/Scope**: 커널 모듈 ~8개, 영속 테이블 2개, 테스트 파일 ~8개, ADR 2건,
Spec 000 테스트 개정 2건, ci.yml services 추가 1건. 도메인 스케일 없음.

## Constitution Check

*GATE: The Initial Check MUST pass before Phase 0 research; the Post-Design Re-check MUST pass after Phase 1 design. Record both separately so each gate is auditable.*

코어 7개(I·III·IV·V·VI·VII·VIII)는 항상 평가, 조건부는 트리거 매트릭스대로.
**이 스펙의 트리거**(spec Architectural Considerations 판정 승계): 도메인 이벤트
계약 → XII + XIII 공통 이벤트 계약; 멱등 primitive → XIII(단 동기 한정 — 신뢰
전달 계약은 비트리거); 감사 primitive 제공 → XV-감사(부분). 금액(V)·행위자
역할(VI)은 코어에서 직접 평가된다. 비트리거: IX·X·XI·XIV·XV-대사·XVI·XVII.

### Initial Check (before Phase 0)

**Date**: 2026-07-09

| Gate (core + triggered) | Result | Notes / justification; N/A requires rationale |
|---|---|---|
| I 스펙 우선 (core) | **PASS** | 승인된 스펙(적대 리뷰 3회 + 사람 승인 2026-07-09) 위에서 계획. 전 primitive test-first(FR-009). |
| III 마켓플레이스 우선 (core) | **N/A** | 벤더·마켓플레이스 도메인 없음 — 행위자 역할 어휘는 VI 소관이고, 벤더 소유권·생명주기 모델링은 P1. |
| IV 불변 스냅샷 (core) | **N/A** | 주문·스냅샷 없음. 이벤트 페이로드 버전(스키마 진화 제약)은 FR-003이 담당 — Post-Design에서 재확인. |
| V 금액 (core) | **PASS (본체)** | Money·명시적 반올림·통화 정밀도·안분이 본체. 부동소수점 금지를 표현 선택(최소 단위 정수)으로 구조화. |
| VI 벤더 격리·인가 (core) | **PASS (부분)** | 행위자 역할 어휘 제공까지가 스펙 범위. 실제 인가 강제는 P1(Scope boundaries #3). |
| VII 모듈러 모놀리스 (core) | **PASS** | 단일 배포 단위 유지. 커널은 도메인 앱이 아닌 공유 기반 — P1~ 도메인 앱 구조의 전제. |
| VIII 도메인 경계 (core) | **PASS** | 커널 단방향(도메인→커널)은 Spec 000 tach 계약 그대로. 공개 표면은 BR-7 특성화로 명시 관리. |
| XII 이벤트 (conditional) | **PASS** | 확장 봉투 + 발행/디스패치 분리. 동기 시작은 XII의 MAY 경로. |
| XIII 멱등·메시징 (conditional) | **PASS** | 스코프 멱등키 + DB 유니크 강제(SHOULD 채택) + 확정/불확정 이분. 신뢰 전달 계약은 동기 한정으로 비트리거 — 외부 부수 효과 핸들러의 동기 등록 금지(FR-004)가 그 경계를 지킨다. |
| XV-감사 (conditional, 부분) | **PASS** | 감사 대상 상태 변경 없이 primitive 제공. 원자 기록·불변·필수 필드가 XV 요구와 정합. go-live 대사 항목 비대상. |

**조건부 비트리거 확인**: IX(외부 시스템 0 — psycopg는 저장소 드라이버지 외부
연동 아님), X·XI(프로모션·역방향 없음), XIV(자원 선점 없음), XV-대사(외부 금액·
재고 경계 없음), XVI(자동/스케줄 상태 변경 없음 — 멱등 TTL은 재시도 시점의
판정이지 스케줄 배치가 아님), XVII(레거시 재사용 없음).

**Initial Gate 결과: PASS** (위반 없음 → Complexity Tracking 비어 있음).

### Post-Design Re-check (after Phase 1)

**Date**: 2026-07-09

| Gate | Result | What changed since Initial Check; N/A requires rationale |
|---|---|---|
| I 스펙 우선 | **PASS** | 전 primitive에 RED 선행 테스트 설계(quickstart ↔ SC 매핑). |
| III 마켓플레이스 우선 | **N/A** | 변화 없음(벤더 부재). |
| IV 불변 스냅샷 | **N/A** | 설계에 스냅샷 없음. 봉투에 `payload_version` 필드 확정(contracts) — 진화 제약 충족 확인. |
| V 금액 | **PASS** | data-model: 최소 단위 정수, float 거부 경로, 정책 어휘 4종, largest-remainder 안분 — FR-001·002·011 전부 설계 매핑. |
| VI 벤더 격리·인가 | **PASS** | ActorRole 4종 + Actor 값 객체로 구체화. 변화 없음. |
| VII 모듈러 모놀리스 | **PASS** | 설계가 `shared_kernel/` 단일 앱 + `tests/kernel/`로 구체화. 도메인 구조 불변. |
| VIII 도메인 경계 | **PASS** | tach.toml 변경 불필요 확인. 공개 표면 열거는 `__init__` re-export + 특성화 테스트로 설계(contracts/kernel-public-surface.md). |
| XII 이벤트 | **PASS** | Envelope 필드·발행 API·SyncDispatcher·핸들러 등급 선언이 contracts로 고정. 강화됨. |
| XIII 멱등·메시징 | **PASS** | 2단계 클레임 프로토콜(상태 전이·동시성)이 claim token fencing과 UNKNOWN 해소 근거까지 설계로 구체화(contracts/idempotency-protocol.md). |
| XV-감사 | **PASS** | AuditFact 스키마(대상 타입+ID·근거 참조·상관관계 필수) + 동일 트랜잭션 기록 계약 확정. |

**Post-Design Gate 결과: PASS** — 새 원칙 트리거 없음, 일탈 없음.

## Project Structure

### Documentation (this feature)

```text
specs/001-shared-kernel-primitives/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── kernel-public-surface.md
│   └── idempotency-protocol.md
├── checklists/
│   └── requirements.md  # (spec 단계 산출)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
shared_kernel/                   # 공유 커널 — Django 앱으로 승격(마이그레이션 보유)
├── __init__.py                  # 공개 표면 열거(BR-7 특성화 대상) — ORM 심볼은 PEP 562 지연 re-export(앱 로딩 안전)
├── apps.py                      # SharedKernelConfig
├── models.py                    # 모델 애그리게이터 — Django의 <app>.models 자동 탐색 경로(idempotency·audit import)
├── money.py                     # Money(minor units int) · Currency.of/register(KRW) · RoundingPolicy · allocate
├── events.py                    # 불변 EventEnvelope · publish() · dispatch-only 프로토콜 · 명시 대상 subscribe · use_dispatcher
├── idempotency.py               # 조회 전용 Record · run_idempotent(외부 atomic 거부·TTL/clock 주입) · 내부 fenced 전이
├── audit.py                     # 조회 전용 AuditFact · 외부 atomic 필수 record_audit_fact() · 내부 insert 경로
├── actors.py                    # ActorRole(operator/vendor/customer/system) · Actor
├── correlation.py               # correlation context(contextvars) · 발급/전파/reset
└── migrations/
    ├── 0001_idempotency.py      # 멱등 테이블(US3)
    └── 0002_audit.py            # 감사 테이블 + append-only 트리거(US4 — 0001에 그래프 의존)

config/settings/
├── base.py                      # INSTALLED_APPS += shared_kernel; DATABASES = PostgreSQL(환경변수 주입)
└── ci.py                        # CI postgres 접속 설정

tests/kernel/                    # 커널 계약 테스트(신규)
├── test_money.py                # US1 #1~4
├── test_money_allocation.py     # US1 #5 · SC-008
├── test_events.py               # US2 #1~5
├── test_idempotency.py          # US3 #1~8 · SC-004(동시성·UNKNOWN 해소)
├── test_audit.py                # US4 #1~3
├── test_actors.py               # US4 #4
├── test_correlation.py          # US5 #1~2 · SC-007
└── test_public_surface.py       # SC-006 (Spec 000 빈-커널 테스트의 후계)

tests/conformance/
└── test_fixture_scope.py        # 개정: 커널 심볼 0 단언 → 공개 표면 특성화로 위임(BR-7 예고)

.github/workflows/ci.yml         # postgres 서비스 컨테이너 추가(quality-gate 계약 필드 불변)
docker-compose.yml               # 로컬 PostgreSQL 16(신규)
docs/adr/
├── 0004-storage-postgresql.md   # 신규
└── 0005-money-minor-units.md    # 신규
```

**Structure Decision**: Django 모듈러 모놀리스 유지(원칙 VII). `shared_kernel`은
마이그레이션을 갖기 위해 Django 앱이 되지만 **도메인 계층(`apps/`)이 아니다** —
멱등·감사 테이블은 인프라 기록이며 도메인 모델이 아니다(BR-6, 스펙 Key Entities).
tach 경계 계약은 변경 없이 유지된다: `shared_kernel` depends_on=[](Django는 외부
의존이라 무관), 도메인→커널 방향만 허용, 미등록 봉쇄·등록 대조도 그대로. ci.yml
변경은 CI 계약 테스트가 고정한 필드(잡 id·trigger·스텝 순서·skip 금지)를 건드리지
않고 services 블록만 추가한다 — `.github/workflows/`는 CODEOWNERS 소유 경로다.

## Complexity Tracking

> Constitution Check에 정당화가 필요한 위반이 **없다**. 이 표는 비어 있다.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (없음) | — | — |

## Architecture Decisions

> Principle XX: rationale MUST, ADR는 SHOULD 메커니즘. 아래 결정은 `docs/adr/`에 ADR로 남긴다.

| Decision | Rationale | Alternatives considered | Trade-offs accepted | Evolution path | ADR link |
|---|---|---|---|---|---|
| 저장소 PostgreSQL 16 채택 | 첫 영속 primitive(멱등·감사)의 동시성 계약(유니크 대기·행 잠금)이 프로덕션과 같은 의미로 검증되어야 함(원칙 XVII — SQLite의 단일-작성자 잠금은 SC-004 동시성 테스트의 대표성을 깨뜨림). Django 생태 표준 | SQLite(동시성 의미 상이·이중 전환 비용), MySQL(사내 관례이나 Django 정합·기능 열위) | 로컬 docker 의존, CI 시간 소폭 증가 | 운영 배포 시 매니지드 PostgreSQL로 그대로 이행 | `docs/adr/0004-storage-postgresql.md` |
| Money 내부 표현 = 통화 최소 단위 정수 | 부동소수점의 구조적 침투 불가(원칙 V를 표현 수준에서 강제) + 정수 연산의 자명한 결정론 + 안분이 정수 나눗셈·나머지로 정확 | Decimal 저장(생성 경로 float 함정·스케일 관리), float(헌장 금지) | 비정수 스칼라 곱은 Decimal 경유 + 명시적 정책이라는 API 마찰 — 의도된 마찰(FR-002) | 다통화는 통화 레지스트리 등록으로 확장 | `docs/adr/0005-money-minor-units.md` |
| 멱등 직렬화 = DB 유니크 기반 2단계 클레임 + claim token fencing | 헌장 동시성 제어(멱등키 DB 유니크 SHOULD) 채택. 클레임 선커밋 → 비즈니스 트랜잭션에서 효과+완료 마킹 원자. claim token이 만료 재클레임 뒤 stale 실행의 완료 마킹을 차단해 TTL 경합의 이중 커밋을 막는다. 독립 커밋을 보장하려 외부 atomic 진입을 거부한다 | 동일 트랜잭션 클레임(진행 중 응답 불가·유니크 대기 블로킹), advisory lock(가시성·크래시 복구 불투명), TTL만으로 비-fenced 재클레임(느린 원본 실행과 이중 커밋 경합) | 클레임/본문 2회 커밋 왕복, 호출자가 바깥 atomic으로 감쌀 수 없음, stale claim은 완료 마킹 실패 시 전체 롤백 필요 | UNKNOWN 상태는 외부 흐름(P6+)이 근거 있는 복구 검증과 함께 사용 | contracts/idempotency-protocol.md (ADR 승격은 P6 재검토) |

## Review & Approval

- **Reviewer** (separate session/model — may be an AI model): Codex plan 적대 리뷰 2회 + tasks 적대 리뷰 2회의 설계 역전파 검토
- **Reviewed at**: 2026-07-10 (plan 2회 + tasks 2회)
- **Review evidence**: **1차** 승인 보류(HIGH 4·MEDIUM 3) → 전건 반영 —
  (1) 멱등 TTL 재클레임에 claim token fencing·stale claim 롤백 계약 추가,
  (2) UNKNOWN 해소 근거·전이·검증 시나리오 복구,
  (3) 이벤트 핸들러 부수 효과 등급 기본값 제거(명시 선언 필수),
  (4) correlation reset/context manager 공개 표면 추가,
  (5) float 유래 Decimal의 기계 판별 불가능성을 인정하고 Money 생성 API에서
  Decimal 경로 제거,
  (6) 공개 표면을 실제 `__all__` 심볼명으로 재열거,
  (7) PostgreSQL·Money ADR 누락 해소.
  **2차** 승인 보류(HIGH 5·MEDIUM 4) → 9건 전건 수용 —
  (1·2) 확정 실패의 "삭제" 표현이 지문 대조를 무력화(같은 키·다른 요청이 실패
  후 통과 — FR-005 위반)하고 unfenced 삭제가 재클레임과 경합 → **지문 보존
  fenced tombstone(DEFINITE_FAILURE)으로 통일**, 삭제 경로 제거,
  (3) mark_unknown이 COMPLETED를 되돌릴 수 있던 구멍 → claim_token 필수 +
  상태 조건부 전이 + **COMPLETED 종결·불변** 불변식 명문화,
  (4) 스칼라 곱의 `Decimal` 인스턴스 수용이 1차 반영(생성 거부)과 자기모순 →
  스칼라 = int·정확 십진 문자열·Fraction으로 제한(연산 경로도 Decimal 거부),
  (5) 감사 불변의 모델 계층 한정이 SC-005 "100% 거부"를 완화 → **DB 트리거
  상향**(감사 테이블 생성 마이그레이션 포함, raw SQL 봉쇄 — 권한 분리만 go-live 위임),
  (6) canonicalizer·fingerprint_version의 API 주입 지점 부재 → run_idempotent
  계약에 명시 + `canonical_json` 표면 추가,
  (7) "contextvars 스레드 자동 보장" 서술 부정확 → 정정(새 스레드 비상속,
  copy_context 명시 규약 + 테스트 케이스),
  (8) backdate 거부가 계약·quickstart에 미고정 → K-13 신설 + 시나리오 반영,
  (9) DB 접속 env·서비스 계약 미고정 → POSTGRES_* 계약·healthcheck·CI 계약
  테스트 확장 명시.
  **Tasks-stage 설계 역전파** — Django 모델 자동 발견·lazy re-export, Currency
  등록 API, dispatcher 주입/구독 분리, TTL·clock 주입, 외부 atomic 진입 거부,
  멱등·감사 공개 모델 조회 전용화, 이벤트 payload 재귀 불변화, 마이그레이션
  0001→0002 의존을 plan/research/data-model/contracts에 반영. 기존 사람 승인은
  이 변경 전 산출물에 대한 것이므로 재승인 전까지 구현 진입 불가.
- **Previous approval**: [x] Approved to proceed to tasks — _(cray.j, 2026-07-10; tasks-stage amendments 이전)_
- **Approval** (final approver MUST be a human — Principle XIX): [ ] Re-approved to proceed to implement — _(pending)_
