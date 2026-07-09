# Tasks: Foundation — Structure & Boundaries

**Input**: Design documents from `/specs/000-foundation-structure/`

**Prerequisites**: plan.md(승인 완료), spec.md(승인 완료), research.md, data-model.md,
contracts/(boundary-contract.md·public-service-interface.md), quickstart.md

## Review & Approval

- **Reviewer** (separate session/model): Codex GPT-5 (분리된 리뷰 세션)
- **Reviewed at**: 2026-07-08
- **Review evidence**: 지적 8건(HIGH 4·MEDIUM 3·LOW 1)을 재현 실험으로 검증해 7건
  수용·1건 부분 수정 반영 — (1) RED 정의 교정(tach.toml 부재 시 exit 1 재현 →
  exit code 단독 단언 금지·위반 리포트 단언 필수, 선행 RED/완료 GREEN 조건 분리),
  (2) CI 계약 고정(잡 id `quality-gate`·trigger·스텝 순서·continue-on-error/조건부
  skip 금지), (3) `.github/CODEOWNERS` 작성 태스크 T013b 신설, (4) 비-앱 코드
  forbid 정책 확정(config 등록·tests exclude·과잉 exclude 방지 대조), (5) expose
  regex 이스케이프(비이스케이프 `services.*`가 `services_private`를 통과함을 재현
  확인 → `services\..*`, AC-9 신설), (6) 내부 모듈 위반-샘플 표적 `internal.py`
  추가, (7) 등록 대조 범위를 `apps/` 직계 자식 전수로 확정 — 리뷰어 제안(apps.py
  보유 패키지 한정)은 미등록 패키지 간 상호 import 구멍을 재개방해 기각, (8)
  T016→T017 순차화.
- **Approval** (final approver MUST be a human — Principle XIX): [x] Approved to proceed to implement — _(cray.j, 2026-07-08)_

**Tests**: 테스트는 필수이며 구현에 선행한다(원칙 I·XVII). 새 동작 테스트는 구현 전
실패(RED)해야 하고, 제약을 고정하는 특성화 테스트(T012)는 처음부터 통과 상태로
시작할 수 있다(XVII). 경계 계약은 "구성이 곧 구현"이므로 RED = "알려진 위반 샘플이
아직 **리포트되지 않는** 상태"의 실패를 뜻한다(FR-007). 설정 파일 부재로 인한 도구
에러는 RED가 아니다 — `tach check`는 tach.toml이 없어도 exit 1이므로(재현 확인
2026-07-08) exit code 단독 단언은 설정 부재 에러를 위반 차단으로 오인한다. 위반
테스트는 반드시 "해당 위반이 리포트에 식별됨"을 함께 단언한다. 각 t-테스트는
**작성+RED 증거가 target의 선행 조건**이고 **target 완료 후 GREEN이 완료 조건**이다
(GREEN은 착수 조건이 아니다). 순수 스캐폴딩(Phase 1·2)만 test-first 예외.

**Organization**: User Story 단위로 그룹화 — US1(경계 기계 강제, P1) / US2(ADR·문서
소유 규칙, P2). 각 스토리는 독립 구현·독립 검증 가능.

> **Branch note**: plan.md의 Note(branch)대로, 첫 구현 커밋 전에 feature 브랜치 분리
> 여부를 사람이 결정한다(지금까지는 main 진행).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능(다른 파일, 미완료 태스크 의존 없음)
- **[Story]**: US1/US2 (스토리 Phase 태스크에만)
- 테스트 태스크 ID는 target 태스크 ID + `t` 접미(예: T010t → T010). t 테스트와 그
  target은 서로 [P]가 아니다(target이 테스트에 의존).

## Path Conventions

Django Modular Monolith (plan.md Structure Decision): `config/`(설정),
`apps/<domain>/`(도메인 계층 — 이 스펙에선 픽스처 앱만), `shared_kernel/`(빈 커널),
`tests/`(boundary·conformance·ci·docs), `docs/adr/`, 저장소 루트에 `tach.toml`·
`pyproject.toml`·`manage.py`·`.github/workflows/ci.yml`.

---

## Phase 1: Setup (프로젝트 초기화 — 순수 스캐폴딩, test-first 예외)

**Purpose**: uv 프로젝트·Django 설정 골격. 관찰 가능한 동작 없음(FR-007 예외).

- [X] T001 uv 프로젝트 초기화 — `pyproject.toml`(project: Python 3.12; deps: Django 5.2 LTS; dev-deps: tach·pytest·pytest-django·ruff), `.python-version`(3.12), `uv.lock` 생성(`uv sync`), `.gitignore`(Python/Django/uv 표준)
- [X] T002 pyproject.toml에 도구 설정 추가 — ruff(`E,F,B,C4,W,I,DJ`, line-length 100), pytest(`DJANGO_SETTINGS_MODULE=config.settings.ci`, testpaths=`tests`) (T001과 같은 파일 — T001 이후)
- [X] T003 Django config 스캐폴딩 — `manage.py`, `config/__init__.py`, `config/settings/{__init__,base,local,ci}.py`(base→환경별 계층; prod/sandbox 생성 금지 — YAGNI), `config/urls.py`(빈 라우팅 골격), `config/wsgi.py`, `config/asgi.py`

**Checkpoint**: `uv run python -c "import django"` 성공.

---

## Phase 2: Foundational (픽스처·커널 골격 — 순수 스캐폴딩, test-first 예외)

**Purpose**: US1·US2가 올라설 최소 구조. 도메인 모델·primitive 정의 0(BR-4).

- [X] T004 [P] 경계 적합성 픽스처 앱 A·B 스캐폴딩 — `apps/__init__.py`, `apps/conformance_a/{__init__.py,apps.py,services.py}`, `apps/conformance_b/{__init__.py,apps.py,services.py,internal.py}`. 각 `services.py`는 자명한 공개 함수 1개(자기완결 — cross-app 호출 구현은 T011). `internal.py`는 자명한 비공개 함수 1개 — 경계 테스트의 **내부 모듈 위반-샘플 표적**(Django 구성 파일 `apps.py`를 내부 모듈 샘플로 쓰지 않는다). `models.py`·`migrations/` 만들지 않음(SC-003)
- [X] T005 [P] 공유 커널 빈 패키지 — `shared_kernel/__init__.py` (public symbol 0, SC-003; 내용물은 Spec 001)
- [X] T006 `config/settings/base.py` INSTALLED_APPS에 픽스처 앱 등록 (T003·T004 이후)

**Checkpoint**: `uv run python manage.py check` 통과 — user story 착수 가능.

---

## Phase 3: User Story 1 — 도메인 경계가 기계적으로 강제된다 (Priority: P1) 🎯 MVP

**Goal**: 정적 import 경계(명시적 dependency edge + services-only 공개 표면 + 커널
단방향 + 미등록 앱 봉쇄)를 Tach로 기계 강제하고, CI에서 생략 불가능하게 만든다.

**Independent Test**: quickstart 시나리오 1~5·8~10 — 위반 커밋이 차단되고 위반 제거
시 통과하며, 검사기 자체가 메타 테스트로 검증됨을 다른 어떤 스토리 없이 확인 가능.

### Tests for User Story 1 (write FIRST — RED 확인 후 구현) ⚠️

- [X] T010t [US1] 경계 테스트 스위트 작성 + RED 증거(RED 기준은 상단 **Tests** 절 — 위반이 리포트되지 않음/양성 케이스 미통과여야 하며, 설정 부재 에러의 exit ≠ 0은 차단 증거가 아니다):
  (a) `tests/boundary/test_boundary_contract.py` — 허용 edge(`conformance_a → conformance_b.services`) 통과 / A→`conformance_b.internal` 직접 import 위반 차단 / **near-miss 공개 표면 차단**: 임시 복제본에 `apps/conformance_b/services_private.py` 주입 후 A에서 import 시 위반 리포트(expose가 비이스케이프 `services.*`면 통과해버림 — 재현 확인 2026-07-08, AC-9) / `shared_kernel`→픽스처 앱 역의존 차단. 위반 케이스는 전부 임시 복제본에 주입하고 exit code + **위반 경로가 리포트에 식별됨**을 단언(AC-1·AC-2·AC-3);
  (b) `tests/boundary/test_boundary_meta.py` — 임시 복제본에 알려진 위반 주입 후 `tach check` exit ≠ 0 + 해당 위반이 리포트에 존재함을 단언(거짓-통과 방지, AC-4);
  (c) `tests/boundary/test_module_registration.py` — **`apps/` 바로 아래의 모든 패키지·모듈(`__init__.py` 제외)**이 tach 모듈로 등록되었는지 파일시스템 대조(향후 `apps/<domain>/domain/` 같은 중첩 하위 패키지는 부모 모듈 경계 소속이라 대상 아님) + `root_module = "forbid"` 설정 존재 + exclude 목록이 `apps`·`config`·`shared_kernel`(하위 포함)을 건드리지 않음(과잉 exclude로 인한 검사 표면 침식 방지) 대조(R-BC-4, AC-6·AC-7)
- [X] T011t [P] [US1] `tests/conformance/test_public_interface.py` 작성(RED) — 앱 A가 앱 B의 `services` 공개 함수를 경유해 호출 성공 + 픽스처 내 cross-app 내부 import 0건 정적 검사(SC-005, AC-SI-1·AC-SI-2)
- [X] T012 [P] [US1] `tests/conformance/test_fixture_scope.py` 작성 — 픽스처 앱 `models.Model` subclass 0·`migrations` 패키지 0·primitive 정의 0, `shared_kernel` public symbol 0을 기계 단언(SC-003). 제약 고정(특성화) 테스트로 처음부터 통과 가능(XVII)
- [X] T013t [P] [US1] `tests/ci/test_ci_contract.py` 작성 + RED 증거(ci.yml·CODEOWNERS 부재) — `.github/workflows/ci.yml`을 파싱해 (1) trigger에 `pull_request` 포함, (2) 계약 고정 잡 id **`quality-gate`** 존재, (3) 그 잡 안에 `tach check` 스텝 → pytest 스텝 순서, (4) 잡·두 스텝에 `continue-on-error`·조건부 `if:` 부재를 단언하고, (5) `.github/CODEOWNERS`가 존재하며 `/.github/workflows/` 소유 규칙을 포함함을 단언(C-5, AC-8)

### Implementation for User Story 1

- [X] T010 [US1] `tach.toml` 경계 계약 작성 (선행: T010t 작성+RED 증거 / 완료 조건: T010t (a)(b)(c) 전부 GREEN):
  모듈 등록 `apps.conformance_a`(depends_on=`["apps.conformance_b", "shared_kernel"]`)·
  `apps.conformance_b`(depends_on=`["shared_kernel"]`)·`shared_kernel`(depends_on=`[]`,
  BR-3), `[[interfaces]]` expose=`["services", "services\\..*"]`(services-only 공개 표면
  — 점 이스케이프 필수: 비이스케이프 `services.*`는 `services_private`를 통과시킴,
  재현 확인 2026-07-08), `root_module = "forbid"`(미등록 코드 봉쇄, R-BC-4).
  **비-앱 코드 처리(확정)**: `config`는 명시 모듈로 등록(depends_on=`[]` —
  INSTALLED_APPS·settings 경로는 문자열 참조라 정적 import 없음; urls 배선이 생기면
  그때 edge 추가) — composition root를 exclude로 검사 밖에 빼지 않는다. `tests`는
  exclude(경계를 가로질러 검증하는 것이 목적인 비배포 코드 — 과잉 exclude는
  T010t(c)가 차단). `manage.py`는 first-party import가 없어 `<root>` 잔류로 forbid
  위반 없음(research.md R3)
- [X] T011 [US1] `apps/conformance_a/services.py`에 `conformance_b.services` 공개 함수를 경유하는 호출 구현 (선행: T011t 작성+RED 증거, T010 완료 / 완료 조건: T011t GREEN — 선언된 edge 위에서만 동작)
- [X] T013 [US1] `.github/workflows/ci.yml` 작성 (선행: T013t 작성+RED 증거 / 완료 조건: T013t (1)~(4) GREEN): trigger `on: pull_request`(+ `push: branches [main]`), 단일 필수 잡 id **`quality-gate`**(required status check context로 계약 고정, C-5)에 checkout → uv 설치(Python 3.12) → `uv sync` → `uv run tach check` → `uv run pytest` 순서. 잡·스텝에 `continue-on-error`·조건부 `if:` 금지(silent-skip 방지 C-1, FR-003)
- [X] T013b [P] [US1] `.github/CODEOWNERS` 작성 (선행: T013t / 완료 조건: T013t (5) GREEN): `/.github/workflows/ @<저장소 소유자 GitHub 핸들>` — 워크플로 변경 리뷰 게이트의 repo-local 절반(플랫폼 절반인 code-owner review 필수화·핸들 유효성 확인은 T014). C-5 거버넌스 층
- [X] T014 [US1] 저장소 밖 GitHub 설정 + 완료 증거 기록 (T013·T013b 의존): GitHub 원격 저장소 생성·push(현재 remote 없음) → 브랜치 보호/Ruleset에서 **`quality-gate`** context를 **required status check** 지정(C-2) + code-owner review 필수화(T013b의 CODEOWNERS를 바인딩 — 파일만으로는 무력; 소유자 핸들이 실제 계정인지 확인 포함, C-5 거버넌스 층) → 증거(`gh api repos/.../branches/main/protection` 출력 등)를 `specs/000-foundation-structure/evidence/branch-protection.md`에 기록(C-3)
  **✅ 완료(2026-07-09)**: 2026-07-08 부분 보류(Free 플랜 private 제약 403) → public 전환으로 해제. required status check `quality-gate` 적용(strict + enforce_admins — 관리자 포함, 직접 push 거부 실증), 증거는 [evidence/branch-protection.md](./evidence/branch-protection.md). **C-5 플랫폼 절반(code-owner review 필수화)만 조건부 유예** — 솔로 셀프승인 데드락으로 방어 가치 0, 첫 비소유자 협업자 추가 시 기록된 페이로드로 즉시 활성화.

**Checkpoint**: US1 완결 — quickstart 시나리오 1~5·9·10 GREEN, 시나리오 8 증거 존재.

---

## Phase 4: User Story 2 — 핵심 아키텍처 결정과 문서 소유 규칙이 기록된다 (Priority: P2)

**Goal**: 핵심 결정 3건을 MADR 형식 ADR로 남기고, state-model·glossary의 정식 경로·
소유 규칙을 기록하되 파일은 선제 생성하지 않는다(BR-5).

**Independent Test**: quickstart 시나리오 6 — `docs/adr/`에 결정 ADR과 소유 규칙이
존재하고 `docs/domain/state-model.md`·`glossary.md`가 없음을 US1과 무관하게 확인 가능.

### Tests for User Story 2 (write FIRST — RED 확인 후 구현) ⚠️

- [X] T015t [US2] `tests/docs/test_docs_ownership.py` 작성 + RED 증거(ADR 부재): `docs/adr/0001~0003` 존재 + 각 ADR에 근거·대안·트레이드오프 섹션 존재 + ADR 0002에 state-model·glossary 정식 경로와 소유 규칙(최초 생성 주체 = 첫 상태/도메인 용어 도입 기능, 로드맵상 P1) 기록 + `docs/domain/state-model.md`·`docs/domain/glossary.md` **부존재** 단언(US2 #1·#2, SC-004, BR-5)

### Implementation for User Story 2 (선행: T015t 작성+RED 증거 / 완료 조건: 셋 완료 시 T015t GREEN)

- [X] T015a [P] [US2] `docs/adr/0001-modular-monolith.md` — Django 모듈러 모놀리스 채택(MADR: 맥락/결정/대안: 마이크로서비스·비-Django/트레이드오프/진화: 경계 안정+운영 필요 입증 시 서비스 추출, 원칙 VII)
- [X] T015b [P] [US2] `docs/adr/0002-boundary-enforcement-tach.md` — 정적 import 경계 기계 강제(Tach: 명시적 edge·services-only interface·`root_module="forbid"`+등록 대조 병행 필수 근거(재현 실험), 대안: import-linter·커스텀 AST·리뷰 관례, 보장 범위: 정적 import 한정 — 우회 경로는 규약·리뷰·P1 판단, 원칙 VIII) **+ 문서 소유 규칙**(`docs/domain/state-model.md`·`glossary.md` 정식 경로, 첫 상태/도메인 용어 도입 기능이 최초 생성 — 빈 문서 선제 생성 금지, FR-006)
- [X] T015c [P] [US2] `docs/adr/0003-shared-kernel-unidirectional.md` — 공유 커널 단방향 의존(커널→도메인 역의존 금지, 빈 커널에서 vacuous하지 않도록 픽스처를 도메인 계층으로 등록한 근거, 내용물은 Spec 001, 원칙 VIII/BR-3)

**Checkpoint**: US1·US2 모두 독립 검증 가능 — quickstart 시나리오 6 GREEN.

---

## Phase 5: Polish & Cross-Cutting

**Purpose**: 전 시나리오 실행 증거와 품질 마감.

- [X] T016 quickstart.md 시나리오 1~10 전체 실행, 결과(명령·출력 요약·RED→GREEN 증거)를 `specs/000-foundation-structure/evidence/quickstart-run.md`에 기록 (원칙 XVII: 완료 주장에 관측 근거)
- [X] T017 품질 마감 (T016 이후 — SC 매핑이 quickstart 실행 증거를 참조) — `uv run ruff check .` 0건, `uv run python manage.py check` 통과, Success Criteria SC-001~005 최종 대조(각 SC ↔ 통과 테스트/`evidence/quickstart-run.md` 증거 매핑 확인)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1(Setup)** → **Phase 2(Foundational)** → 이후 US1·US2 착수 가능
- **US1(Phase 3)**: Phase 2 완료 후. 내부 순서 T010t → T010; T011t(T010t와 병렬 가능)
  → T011(T010 이후); T013t → T013·T013b → T014. T012는 Phase 2 완료 직후 언제든.
- **US2(Phase 4)**: Phase 2와 무관하게 Phase 1 이후 가능하나(문서 전용), pytest 실행
  환경(T001·T002)은 필요. T015t → T015a·T015b·T015c(병렬).
- **Polish(Phase 5)**: US1·US2 완료 후.

### User Story Dependencies

- **US1(P1)**: 다른 스토리 의존 없음 — 단독 MVP.
- **US2(P2)**: US1 의존 없음 — 독립 검증 가능(ADR 내용이 US1의 결정을 기술하지만
  파일 존재·내용 검증은 US1 구현과 무관).

### Parallel Opportunities

- Phase 2: T004 ∥ T005
- US1 테스트: T010t ∥ T011t ∥ T012 ∥ T013t (모두 다른 파일)
- US1 구현 후반: T011 ∥ T013 ∥ T013b (다른 파일, 각자 선행 테스트만 의존)
- US2: T015a ∥ T015b ∥ T015c
- Polish: T016 → T017 (SC 매핑이 T016의 quickstart 실행 증거를 참조 — 병렬 아님)
- 인력이 나뉘면 US1(코드·CI)과 US2(문서)는 통째로 병렬 가능

---

## Parallel Example: User Story 1

```bash
# Phase 2 완료 후 — US1 테스트 4개를 동시에 작성 (모두 RED 확인):
Task: "T010t 경계 테스트 스위트 3파일 in tests/boundary/"
Task: "T011t 공개 인터페이스 테스트 in tests/conformance/test_public_interface.py"
Task: "T012 픽스처 범위 특성화 테스트 in tests/conformance/test_fixture_scope.py"
Task: "T013t CI 계약 테스트 in tests/ci/test_ci_contract.py"

# RED 확인 후:
Task: "T010 tach.toml 계약 작성"            # → T010t GREEN
Task: "T013 ci.yml + T013b CODEOWNERS 작성"  # → T013t GREEN (T010과 병렬 가능)
```

---

## Implementation Strategy

### MVP First (US1만)

1. Phase 1 → Phase 2 → Phase 3(US1) 완료
2. **STOP & VALIDATE**: quickstart 시나리오 1~5·9·10으로 US1 단독 검증
3. 이 시점에 "경계가 기계적으로 강제되는 골격"이라는 스펙의 핵심 가치가 성립

### Incremental Delivery

1. Setup+Foundational → 골격 준비
2. US1 → 독립 검증 → 커밋 (MVP)
3. US2 → 독립 검증 → 커밋
4. Polish(증거 기록·품질 마감) → Spec 000 완료 → Spec 001(`/speckit-specify`)로

---

## Notes

- RED 확인은 실행 증거로 남긴다(원칙 XVII) — T016에서 최종 취합.
- 태스크(또는 논리 그룹) 단위로 커밋. 각 checkpoint에서 스토리 독립 검증.
- `docs/domain/` 아래 파일 생성 금지(BR-5) — T015t가 부존재를 단언한다.
- T014는 GitHub 원격·플랫폼 설정이 필요한 유일한 태스크 — 환경 제약 시 나머지를
  먼저 완료하고 T014만 보류 가능(단, Spec 000 완료 선언 전에 증거 필수).

---

## Constitution Gate & Traceability

*구현 시작 전 tasks 수준 Constitution Check. 코어 게이트는 항상 기재하며, plan.md
Constitution Check에서 트리거된 조건부 원칙은 없다(도메인·금액·이벤트·외부연동·자원
선점·벤더·레거시 전무).*

| Principle (core always; conditional if triggered) | Disposition | Task IDs / evidence link / N/A rationale |
|---|---|---|
| VII — Modular monolith / Django app per domain (core) | **Task** | T003·T004·T005·T006(구조), T015a(ADR 0001) |
| IV — Immutable snapshots (core) | **N/A** | 스냅샷·재무 값 없음(도메인 데이터 0) — plan Initial Check 근거. 스냅샷은 P5, 이벤트 버저닝은 Spec 001 |
| VIII — Domain boundaries (core) | **Task** | T010t·T010(계약+메타+등록 대조), T011t·T011(services-only 실증), T013t·T013·T013b·T014(CI 강제·silent-skip 방지·워크플로 리뷰 게이트), T015b·T015c(ADR) |
| I — Tests precede implementation (core) | **Task** | T010t→T010, T011t→T011, T013t→T013·T013b, T015t→T015a/b/c. 스캐폴딩 예외: T001~T006(FR-007). 특성화: T012(XVII) |
| V — Money type & rounding (core) | **N/A** | 금액 계산·저장 없음 — Money는 Spec 001 |
| VI — Vendor isolation & authorization (core) | **N/A** | 벤더·행위자 없음 — 역할 스캐폴딩은 Spec 001, 벤더 격리는 P1 |
| (conditional) | **N/A** | plan.md Constitution Check: 트리거된 조건부 원칙 없음 |

- 모든 코어 게이트에 Disposition 기재 완료 — 구현 착수 가능(Waiver 없음, Complexity
  Tracking 비어 있음).

---

## Go-live Enablement & Readiness

**N/A** — 이 스펙은 XV-대사(외부 금액·재고 경계)도 XVI(자동/스케줄 상태 변경)도
트리거하지 않는다(외부 연동 0, 자동 상태 변경 0, 내부 XV-감사 대상 상태 변경조차
없음 — 도메인 데이터 0). go-live 게이트 항목은 해당 원칙이 트리거되는 P3·P6 이후
Phase에서 생성된다(헌장 "Go-live 게이트" 적용 범위).
