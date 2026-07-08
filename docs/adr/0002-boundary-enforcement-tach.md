# ADR 0002: 정적 import 경계의 기계 강제(Tach) + 문서 소유 규칙

- **Status**: Accepted
- **Date**: 2026-07-08
- **근거 원칙**: 헌장 VIII(명확한 도메인 경계) · XX(설명 가능) · **Spec**: `specs/000-foundation-structure/`

## 맥락

경계 규율이 관례(리뷰·기억)에만 의존하면 "모듈화된" 모놀리스는 강결합으로
퇴화한다(원칙 VIII — ADR 0001의 전제). 강제는 기계적이어야 하고, 검사기 자체의
유효성과 "검사가 안 도는" 실패 모드(silent skip)까지 설계 대상이다(FR-003).

## 결정

**Tach**로 정적 import 경계를 기계 강제한다(`tach.toml`이 계약의 코드 표현).

1. **명시적 dependency edge**: 도메인 간 import는 `[[modules]].depends_on`에 선언된
   edge에서만 허용(R-BC-1).
2. **services-only 공개 표면**: `[[interfaces]]`로 각 앱은 `services`만 노출.
   expose 패턴은 regex이므로 **점을 이스케이프**한다 — 비이스케이프 `services.*`는
   `services_private` 같은 near-miss를 통과시킨다(재현 확인 2026-07-08, AC-9).
3. **미등록 코드 봉쇄 — 두 겹(R-BC-4)**: Tach는 미등록 코드를 `<root>`로 취급해
   기본 설정에서 경계 밖으로 흘린다(재현 확인). `root_module = "forbid"`가
   `<root>`↔등록 모듈 import를 양방향 차단하지만, **미등록 패키지 간 상호
   import는 못 잡으므로**(재현 확인) `apps/` 직계 자식 전수 등록을 파일시스템과
   대조하는 테스트를 병행한다 — 하나만으로는 불충분하다.
4. **CI 강제**: `tach check`는 required status check로 지정되는 필수 잡
   `quality-gate`에서 항상 실행되고, repo-local CI 계약 테스트가 잡 id·trigger·
   스텝 순서·continue-on-error/조건부 skip 부재를 고정하며, 워크플로 변경은
   CODEOWNERS + code-owner review 게이트로 보호한다(C-1~C-5).

## 보장 범위 (정직한 한정)

기계 강제 대상은 **정적 import 경계**다. 우회 경로 — 동적 모델 조회
(`apps.get_model`), 문자열 참조 FK, raw SQL, 공유 DB 직접 쿼리 — 는 Tach 범위
밖이며 ID-참조 규약(SHOULD)과 코드 리뷰로 다룬다. 실제 도메인 간 참조가 처음
생기는 P1에서 우회 경로용 추가 검사 도입 여부를 판단한다(FR-002).

## 검토한 대안

- **import-linter**(헌장 예시): 성숙하나 "services만 공개"를 forbidden 계약 나열로
  우회 표현해야 한다. Tach의 `[[interfaces]]`가 이 스펙 의도를 더 직접 선언. 기각.
- **커스텀 AST 검사**: 재발명 + 유지보수 부담. 기각.
- **리뷰 관례만**: 원칙 VIII "관례에 의존 금지" 위반. 기각.

## 트레이드오프

- Tach의 보장 범위가 정적 import로 한정됨을 수용한다(위 한정 참조).
- required status check가 잡 이름 단위 보증이라는 플랫폼 한계를 수용하고, repo
  테스트(실수 삭제)·거버넌스 게이트(의도적 변조)로 위협별 분리 방어한다.
- 도구 종속(비교적 신생 도구)을 수용한다 — 계약 자체는 선언적 TOML이라 동류
  도구(import-linter 등)로의 이식 비용이 낮다.

## 문서 소유 규칙 (FR-006)

표준 상태 모델과 도메인 용어집의 **정식 경로**는 다음과 같다:

- `docs/domain/state-model.md` — 주문·배송·클레임 등 상태와 전이의 단일 표준 문서
- `docs/domain/glossary.md` — 도메인 용어집

두 문서는 **이 단계에서 선제 생성하지 않는다**(BR-5 — 빈 거버넌스 문서 금지).
**최초 생성 주체**: state-model은 첫 상태 머신을 도입하는 기능이, glossary는 첫
도메인 용어가 생기는 기능이 최초 생성한다 — 로드맵상 P1(벤더 생명주기 상태·첫
도메인 용어)이다. 이후 모든 스펙은 이를 참조·확장하고, 상태의 추가·변경은 그
문서 개정으로만 한다(헌장 거버넌스 "표준 상태 모델").

## 진화 경로

- P1: 실제 도메인 등장 — 우회 경로 추가 검사(커스텀 체크 등) 도입 여부 판단.
- 도메인 이벤트 도입(Spec 001~) 시 공개 표면에 `events` 모듈 추가
  (`expose = ["services", "services\\..*", "events", "events\\..*"]`).
