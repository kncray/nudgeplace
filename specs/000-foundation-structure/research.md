# Phase 0 Research: Foundation — Structure & Boundaries

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-08

이 스펙은 아키텍처가 *주제*이므로 리서치는 "도메인 미지수 해소"가 아니라 **도구·구조
선택의 근거 확정**이다. Technical Context에 남은 `NEEDS CLARIFICATION`은 없다(모든
선택이 아래에서 결정됨).

---

## R1. 프레임워크 버전 — Django 5.2 LTS

- **Decision**: Django 5.2 LTS + Python 3.12.
- **Rationale**: 신규 그린필드 프로젝트다. 회사 다수 서비스가 쓰는 Django 4.2 LTS는
  **2026-04 EOL**로 이미 수명이 끝나 신규 채택 대상이 아니다. 5.2가 현행 LTS다.
  Python은 3.12(회사 표준, 안정)로 고정한다 — 최신 마이너 버전을 추종할 이득이 없다.
- **Alternatives considered**:
  - Django 4.2 (회사 관례) → EOL로 탈락.
  - Django 5.1(비-LTS) → LTS 아님, 유지보수 창이 짧아 탈락.
- **헌장 정합성**: 원칙 II(도메인 우선) — 프레임워크 버전은 도메인 설계를 좌우하지
  않는 인프라 선택이므로 plan 재량(헌장 "구체 버전은 plan.md"). 회사 관례 이탈은
  EOL 근거로 정당하며 Complexity Tracking 대상 아님(원칙 위반이 아니라 관례 이탈).

## R2. 패키징·의존성 — uv + pyproject.toml

- **Decision**: uv로 의존성·가상환경 관리, 단일 `pyproject.toml`.
- **Rationale**: 회사 신규 프로젝트 방향(pyproject)과 일치하고, uv는 설치·잠금이 빨라
  CI 시간이 짧다. Tach·ruff·pytest도 전부 dev 의존성으로 한곳에서 관리.
- **Alternatives considered**: pip + `requirements/*.txt`(레거시) → 잠금·속도·일원화
  측면에서 열위, 탈락. Poetry → uv 대비 느리고 최근 생태계 모멘텀이 uv로 이동.

## R3. 경계 강제 도구 — Tach (정적 import 계약 검사)

- **Decision**: **Tach**로 정적 import 경계를 강제. `tach.toml`에 (1) 허용된 모듈
  dependency edge와 (2) `[[interfaces]]`로 "각 앱은 `services`만 공개"를 선언.
- **Rationale**:
  - 헌장·스펙이 든 import-linter는 **예시("예:")**이며, MUST는 "정적 import 경계의
    기계적 강제"다. Tach는 같은 범주(정적 import 계약 검사 계열)에 속해 원칙 VIII와
    spec Assumptions("import-linter 계열의 정적 계약 검사")를 그대로 충족한다.
  - Tach의 `depends_on`은 허용된 cross-domain import edge를 명시하고, `[[interfaces]]`는
    공개 표면을 선언적으로 제한할 수 있어, 우리 "명시적 edge + services-only" 규약을
    import-linter의 forbidden 나열보다 직접적으로 표현한다.
  - Rust 기반이나 pip/uv로 설치되는 wheel이라 **CI에 별도 Rust 툴체인이 필요 없다**.
- **보장 범위(정직한 한정)**: Tach가 잡는 것은 **정적 import**다. 동적 모델 조회
  (`apps.get_model`), 문자열 참조 FK, raw SQL 같은 우회 경로는 이 도구의 강제 범위
  밖이며(스펙 FR-002가 명시), 규약(SHOULD)+리뷰로 다룬다. 실제 도메인 간 참조가 처음
  생기는 P1에서 우회 경로용 추가 검사 도입 여부를 판단한다.
- **미등록 코드 처리(재현 실험, 2026-07-08)**: Tach는 모듈로 선언되지 않은 코드를
  `<root>`로 취급하고, **기본 설정에서는 미등록 앱이 등록 앱의 내부 모듈을 import해도
  `tach check`가 통과한다**(임시 프로젝트에서 exit 0 재현). 대응 두 겹(R-BC-4):
  1. `root_module = "forbid"` — `<root>` ↔ 등록 모듈 간 import를 양방향 차단(재현 확인).
  2. **등록 대조 테스트** — `apps/*` 전수가 tach 모듈로 등록되었는지 파일시스템 대조.
     `forbid`만으로는 **미등록 앱 두 개가 서로 import하는 경우**(둘 다 `<root>` 소속)를
     잡지 못함을 재현으로 확인 — 하나만으로는 불충분해 병행이 필수다.
  `forbid` 하에서 `config`·`tests` 등 앱이 아닌 코드가 등록 모듈을 import해야 하면
  (P1의 urls 배선 등) 해당 패키지를 명시적 모듈로 등록하거나 Tach `exclude`로 다룬다 —
  구체 처리는 tasks/구현에서 확정하고 메타 테스트로 검증한다.
- **Alternatives considered**:
  - import-linter → 성숙하고 헌장의 예시이나, "services만 공개" 같은 공개 표면 제한을
    forbidden 계약 나열로 우회 표현해야 해서 `[[interfaces]]`로 직접 선언하는 Tach
    대비 이 스펙 의도의 표현력이 낮아 탈락.
  - 커스텀 AST 검사 → 유지보수 부담·재발명, 탈락.
  - 리뷰 관례만 → 원칙 VIII "관례에 의존 금지" 위반, 탈락.

## R4. CI & silent-skip 방지 — GitHub Actions + required status check

- **Decision**: GitHub Actions에서 경계 검사(`tach check`)와 pytest를 실행하고,
  브랜치 보호의 **required status check**로 지정해 잡 누락·optional 처리를 막는다.
- **Rationale**: 스펙 FR-003·Edge Case는 "검사가 틀림"보다 흔한 실패 모드인 "검사가
  안 돎(silent skip)"을 요구사항으로 못박았다. 위협별로 층을 나눠 방어한다:
  1. **플랫폼 층**: required status check — 검사 잡이 성공으로 보고되지 않으면 머지
     불가(잡을 빼거나 optional로 돌리면 게이트가 열리지 않음). **한계(정직한 한정)**:
     required check는 잡 이름 단위 보증이라, PR이 워크플로 내용을 같은 잡 이름의
     no-op으로 바꾸면 막지 못한다.
  2. **repo 층(실수 삭제 방어)**: CI 계약 테스트가 `.github/workflows/ci.yml`의
     계약 고정 잡 id(`quality-gate`)·trigger·스텝 순서·continue-on-error/조건부 skip
     부재와 `.github/CODEOWNERS` 소유 규칙 존재를 검증한다(C-5). 이 테스트는 CI 안에서 돌므로
     의도적 워크플로 변조에는 순환적(무력)이고, 실수로 스텝이 빠지는 흔한 실패 모드만
     담당한다.
  3. **거버넌스 층(의도적 변조 방어)**: 워크플로 파일 변경에 대한 리뷰 게이트(GitHub
     Ruleset / CODEOWNERS 등 플랫폼 설정)로 다룬다.
  4. **테스트 층**: 거짓-통과 방지 메타 테스트(R5)가 로컬·CI 어디서든 검사기 유효성을
     확인.
  브랜치 보호/Ruleset·워크플로 리뷰 게이트는 저장소 파일이 아니라 GitHub 설정이므로, 구현
  tasks에는 해당 설정의 완료 증거(예: `gh api` 결과 또는 설정 화면 캡처/링크)를 남기는
  작업을 포함한다.
- **Alternatives considered**: 경계 검사를 pre-commit 훅에만 두기 → 우회 가능(로컬
  훅 미설치), CI 필수화가 아니므로 탈락(보조로는 가능).

## R5. 테스트 — pytest + pytest-django, 메타 테스트는 `tach check` CLI

- **Decision**: pytest + pytest-django. 거짓-통과 방지 메타 테스트는 **알려진 위반
  픽스처**에 `tach check`를 서브프로세스로 실행해 **exit code ≠ 0 및 해당 위반이
  리포트에 식별됨**을 단언한다(`tach check`는 tach.toml 부재 같은 설정 에러도 exit
  1이므로 exit code 단독 단언은 공허 통과 위험 — 재현 확인 2026-07-08).
- **Rationale**: 회사 표준 러너와 일치. "검사기가 실제 위반을 잡는가"(US1 #4)를
  검증하려면 검사기 자체를 호출해야 하므로, 실제 사용 형태 그대로 CLI를 돌리는 것이
  가장 충실하다(도구 내부 API 결합 회피). RED/GREEN: 경계 계약은 "구성이 곧 구현"이라
  위반 샘플이 아직 안 걸리는 상태(RED) → tach.toml 계약 작성 후 걸림(GREEN).
- **Alternatives considered**: Tach Python API 직접 호출 → 내부 API 결합·버전 취약,
  CLI exit code가 더 안정적이라 탈락. Django `TestCase`만 사용 → DB 없는 스펙이라
  pytest가 더 가벼움.

## R6. 디렉터리·설정 계층 — config/settings/{base,local,ci}

- **Decision**: `config/settings/base.py → {local,ci}.py`. 지금 필요 없는
  prod/sandbox/cbt 설정은 만들지 않는다(YAGNI). 공유 커널은 `shared_kernel/`, 픽스처
  앱은 `apps/conformance_a`·`apps/conformance_b`.
- **Rationale**: 회사 설정 계층 패턴(base → 환경별)과 정합하되, 스캐폴딩 단계에 불필요한
  환경 파일 선점을 피해 스펙의 절제를 지킨다. `shared_kernel`는 `common`(잡동사니화)·
  `platform`(의미 중복)보다 의도가 분명하다. 픽스처 앱은 `apps` 도메인 계층으로 등록해
  빈 커널의 역의존 계약이 vacuous하지 않게 한다(FR-005, SC-002).
- **Alternatives considered**: 단일 `settings.py` → 환경 분리 관례 이탈. `src/` 레이아웃
  → 회사 Django 관례(`apps/<domain>/`)와 불일치, 탈락.

## R7. 린트·포맷 — ruff (line-length 100)

- **Decision**: ruff, 규칙셋 `E,F,B,C4,W,I,DJ`, line-length **100**.
- **Rationale**: 회사 표준(ruff·동일 규칙셋). line-length는 레거시 관용치 200 대신
  100으로 — 그린필드라 가독성 기준을 처음부터 조인다. 린트·포맷 설정은 순수
  스캐폴딩(관찰 가능한 동작 없음)이라 test-first 예외(FR-007).

## R8. ADR 형식 — MADR, `0001~` 번호

- **Decision**: MADR 스타일 경량 마크다운, `docs/adr/0001-*.md` 번호. 최소 3건 —
  모듈러 모놀리스 채택 / 정적 import 경계 기계 강제(Tach) / 공유 커널 단방향 의존.
  state-model·glossary 소유 규칙은 ADR 0002에 기록.
- **Rationale**: 원칙 XX(왜·대안·트레이드오프·진화). 빈 state-model.md·glossary.md는
  **선제 생성하지 않는다**(BR-5, FR-006) — 소유 규칙만 ADR에 남긴다. 로드맵상 최초
  생성 주체는 P1이다(벤더 생명주기 상태와 첫 도메인 용어를 도입하는 기능).
- **Alternatives considered**: Nygard 원형 ADR → MADR가 대안·트레이드오프 항목을 더
  명시적으로 담아 헌장 XX와 정합. 위키/컨플루언스 → 저장소 단일 출처(원칙 XVIII) 이탈.

---

## Resolved unknowns

| Technical Context 항목 | 상태 |
|---|---|
| Language/Version | RESOLVED (R1) |
| Primary Dependencies | RESOLVED (R2·R3·R5·R7) |
| Storage | RESOLVED — N/A(도메인 모델 0), Spec 001로 위임 |
| Testing | RESOLVED (R5) |
| CI / silent-skip | RESOLVED (R4) |
| 구조·설정 | RESOLVED (R6) |
| 문서·ADR | RESOLVED (R8) |

남은 `NEEDS CLARIFICATION`: **없음**.
