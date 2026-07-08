# Contract: 도메인 경계 계약 (Boundary Contract)

**Spec**: [../spec.md](../spec.md) | **Date**: 2026-07-08

이 프로젝트가 **개발자·CI에게 노출하는 계약**이다. 사람 관례가 아니라 기계(Tach)로
강제되며(원칙 VIII), GitHub Actions job과 branch protection required status check로
실행 누락을 막는다(FR-003).

## 계약 대상 모듈 (레이어)

| 레이어 | 모듈 | 역할 |
|---|---|---|
| domain | `apps.conformance_a`, `apps.conformance_b` | 도메인 앱(픽스처). A→B 공개 서비스 호출은 양성 사례, 내부 접근은 음성 사례. |
| kernel | `shared_kernel` | 횡단 공유 위치. **어떤 도메인도 import하지 않는다**. |

> 실제 도메인 앱은 P1~에서 `apps.<domain>`으로 추가되며 동일 규칙을 상속한다.
> 상속은 사람 기억이 아니라 **R-BC-4의 기계 강제**로 담보된다 — 등록을 잊은 앱은
> CI가 차단한다.

## 규칙 (기계 강제)

1. **R-BC-1 (명시적 의존 + services-only 공개 표면)**: 도메인 앱 사이의 import는
   `tach.toml`에 명시된 dependency edge가 있을 때만 허용한다. 허용된 edge에서도 대상 앱의
   **`services`**(향후 `events`) 모듈만 공개 표면이며, `models`·기타 내부 모듈로의
   cross-app import는 **차단**된다. → Tach `[[modules]].depends_on`으로 허용 edge를
   열거하고, `[[interfaces]]`로 각 앱의 공개 표면을 `services`로 제한한다.
2. **R-BC-2 (커널 단방향)**: `shared_kernel`은 어떤 `apps.*`도 import할 수 없다
   (도메인→커널만 허용). 커널→도메인 역의존은 **차단**된다(BR-3).
3. **R-BC-3 (ID 참조 규약, SHOULD)**: 도메인 간 참조는 기본적으로 식별자(ID)로 하고
   다른 도메인 모델로의 직접 FK는 지양한다(원칙 VIII). **정적 import로 강제되지 않는
   규약**이며 실증은 실제 도메인이 생기는 P1.
4. **R-BC-4 (전수 등록 강제)**: Tach는 모듈로 선언되지 않은 코드를 `<root>`로 취급하며,
   **기본 설정에서는 미등록 앱이 등록 앱의 내부 모듈을 import해도 통과한다**(재현 확인,
   2026-07-08). 따라서 두 겹으로 막는다 — 하나만으로는 불충분하다:
   - `root_module = "forbid"`: 미등록(`<root>`) 코드와 등록 모듈 사이의 정적 import를
     **양방향 차단**(미등록 앱→등록 앱 내부, 등록 앱→미등록 앱 모두 실패. 재현 확인).
   - **등록 대조 테스트**: `apps/*` 하위 모든 패키지가 `tach.toml` 모듈로 등록되었는지
     파일시스템과 대조해 기계 검증. `forbid`만으로는 **미등록 앱 간 상호 import**(둘 다
     `<root>` 소속이라 같은 모듈 내부로 취급됨)를 잡지 못하므로(재현 확인) 이 테스트가
     필수다.

## 강제 범위 (정직한 한정)

- **강제됨(MUST, 기계적)**: 정적 import 경계 — R-BC-1·R-BC-2.
- **강제 안 됨(규약·리뷰)**: 정적 import를 우회하는 접근 — 동적 모델 조회
  (`apps.get_model(...)`), 문자열 참조 FK(`ForeignKey('other_app.Model')`), raw SQL,
  공유 DB 직접 쿼리. 이는 Tach 범위 밖이며 R-BC-3 규약 + 코드 리뷰로 다룬다. P1에서
  우회 경로용 추가 검사(예: 커스텀 체크) 도입 여부를 판단한다(FR-002).

## CI 강제 계약 (silent-skip 금지, FR-003)

- **C-1**: `tach check`는 항상 실행되는 CI 스텝에 포함된다.
- **C-2**: 이 검사는 브랜치 보호의 **required status check**로 지정된다 — 잡이 성공으로
  보고되지 않으면(누락·optional 처리 포함) 머지가 차단된다.
- **C-3**: 브랜치 보호/Ruleset은 저장소 파일이 아니라 GitHub 설정이므로, 완료 증거
  (예: `gh api` 결과 또는 설정 화면 캡처/링크)를 tasks 완료 시 기록한다.
- **C-4**: 검사기 자체의 유효성은 거짓-통과 방지 메타 테스트로 검증한다(아래 수용 기준).
- **C-5**: required status check는 **잡 이름 단위 보증**이라, 같은 이름의 잡을 no-op으로
  바꾸는 워크플로 변경까지 막지 못한다. 위협별로 방어를 분리한다:
  - *실수로 스텝 삭제*(흔한 실패 모드): repo-local 테스트가 `.github/workflows/ci.yml`에
    `tach check` 실행 스텝이 존재함을 검증한다. required check로 지정되는 잡 이름은 이
    계약의 일부로 고정한다 — **잡 id `quality-gate`**. repo-local 테스트는 잡 id·trigger
    (`pull_request` 포함)·스텝 순서(`tach check` → pytest)·`continue-on-error`/조건부
    `if:` 부재까지 함께 검증한다(조용한 optional화·조건부 skip 방지).
  - *의도적 워크플로 변조*: repo-local 테스트는 순환적이라 방어가 안 된다(워크플로를
    no-op으로 바꾸면 그 테스트 자체가 실행되지 않음). 워크플로 파일 변경에 대한 리뷰
    게이트로 다루며, 게이트는 두 절반이 모두 있어야 성립한다 — **repo 파일**
    `.github/CODEOWNERS`(`/.github/workflows/` 소유 규칙)와 **플랫폼 설정**(code-owner
    review 필수화). 파일만 있으면 무력하고, 설정만 있으면 대상 규칙이 없다. C-3과 같은
    방식으로 설정 증거를 tasks 완료 시 기록한다.

## 수용 기준 (spec 매핑)

| ID | 시나리오 | 기대 | spec 근거 |
|---|---|---|---|
| AC-1 | 앱 A가 앱 B의 **내부 모듈** 직접 import | `tach check` **실패** | US1 #1, FR-003 |
| AC-2 | 명시적 A→B dependency 아래 앱 A가 앱 B의 **`services`만** 호출 | `tach check` **통과** | US1 #2 |
| AC-3 | `shared_kernel`이 픽스처 앱(도메인) import | `tach check` **실패** | US1 #3, SC-002 |
| AC-4 | 알려진 위반 샘플로 검사기 시험 | 검사기가 위반을 **실제로 잡음**(거짓 통과 0) | US1 #4, SC-001 |
| AC-5 | 경계 검사 잡이 CI에서 누락/optional | 머지 **차단**(required check 미충족) | FR-003, Edge Case |
| AC-6 | **미등록** 앱이 등록 앱의 내부 모듈 import | `tach check` **실패**(`root_module = "forbid"`) | R-BC-4, FR-003 |
| AC-7 | `apps/*` 하위에 tach 모듈로 등록되지 않은 패키지 존재 | 등록 대조 테스트 **실패** | R-BC-4 |
| AC-8 | `ci.yml`에서 `tach check` 스텝 제거 | repo-local CI 계약 테스트 **실패** | C-5, FR-003 |
| AC-9 | 앱 A가 앱 B의 `services_private` 같은 **near-miss 유사명 모듈** import | `tach check` **실패**(공개 표면은 `services` 정확 매치 + `services\..*`만) | R-BC-1, US1 #2 |

## 표현 (Tach, 예시 스케치)

> 실제 `tach.toml` 작성은 구현(tasks) 단계. 아래는 계약을 도구로 어떻게 표현하는지의
> 개념 스케치이며 최종 문법은 Tach 버전에 맞춘다.

```toml
# 개념 스케치 — A→B 공개 서비스 호출만 양성 edge로 열고, 각 앱은 services만 공개
root_module = "forbid"            # 미등록 코드 ↔ 등록 모듈 간 import 차단 (R-BC-4)

[[modules]]
path = "apps.conformance_a"
depends_on = [
  "apps.conformance_b",
  "shared_kernel",
]

[[modules]]
path = "apps.conformance_b"
depends_on = [
  "shared_kernel",
]

[[modules]]
path = "shared_kernel"
depends_on = []                 # 커널→도메인 역의존 금지 (BR-3)

# 공개 표면: 앱은 services 인터페이스만 노출
# expose는 regex — 점을 이스케이프하지 않으면("services.*") services_private 같은
# near-miss가 통과한다(재현 확인 2026-07-08). 정확 매치 + 이스케이프 형태만 허용.
[[interfaces]]
expose = ["services", "services\\..*"]
from = ["apps.conformance_a", "apps.conformance_b"]
```
