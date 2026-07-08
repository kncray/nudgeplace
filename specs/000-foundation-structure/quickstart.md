# Quickstart & Validation: Foundation — Structure & Boundaries

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-07-08

이 문서는 Spec 000이 **끝났음을 증명하는 실행 가능한 검증 시나리오**다. 구현
코드는 담지 않는다(구현은 tasks/implement 단계). 각 시나리오는 Success Criteria·
Acceptance Scenario에 매핑된다.

## 전제 (Prerequisites)

- Python 3.12, [uv](https://docs.astral.sh/uv/) 설치.
- 저장소 루트에서 의존성 동기화:
  ```bash
  uv sync            # pyproject.toml 기반 Django 5.2·Tach·pytest·ruff 설치
  ```

## 시나리오 1 — 깨끗한 트리에서 경계 검사 통과

```bash
uv run tach check
```
- **기대**: 종료 코드 0(위반 없음) — 도메인 간 의존은 선언된 edge
  (`conformance_a → conformance_b.services`)뿐이고 픽스처가 `services`만 경유(SC-005).

## 시나리오 2 — 위반이 실제로 차단된다 (거짓 통과 없음)

앱 A에 앱 B의 **내부 모듈** 직접 import를 일시 추가한 뒤:
```bash
uv run tach check          # 기대: 종료 코드 ≠ 0 + 해당 위반 경로가 리포트에 식별됨
```
- **매핑**: US1 #1, AC-1, SC-001. (확인 후 위반 import 되돌리기.)

## 시나리오 3 — 거짓-통과 방지 메타 테스트

```bash
uv run pytest tests/boundary/test_boundary_meta.py
```
- **동작**: 알려진 위반 픽스처에 `tach check`를 실행해 **종료 코드 ≠ 0 + 해당
  위반이 리포트에 존재함**을 단언(설정 부재 에러의 exit 1과 구분 — 공허 통과 방지).
  "검사기가 위반을 실제로 잡는가"를 검증(검사기 자체의 유효성).
- **매핑**: US1 #4, AC-4, SC-001.

## 시나리오 4 — 커널 단방향 의존 (vacuous 아님)

`shared_kernel`이 픽스처 앱(도메인 계층)을 import하는 알려진 위반을 넣으면:
```bash
uv run tach check          # 기대: 종료 코드 ≠ 0 + 역의존이 위반으로 리포트됨
```
- **매핑**: US1 #3, AC-3, SC-002 — 빈 커널에서도 역의존 규칙이 공허하게 통과하지 않음.

## 시나리오 5 — 공개 인터페이스 경유 호출

```bash
uv run pytest tests/conformance/test_public_interface.py
```
- **기대**: 명시적 A→B dependency 아래 앱 A가 앱 B의 `services`만 호출해 통과.
  cross-app 내부 직접 import 0건. `services_private` 같은 **near-miss 유사명 모듈**은
  공개 표면으로 인정되지 않고 차단된다(임시 주입 검증은
  `tests/boundary/test_boundary_contract.py` 소관, AC-9).
- **매핑**: US1 #2, AC-SI-1·AC-SI-2, AC-9, SC-005.

## 시나리오 6 — 문서 소유 규칙

```bash
uv run pytest tests/docs/test_docs_ownership.py
```
- **기대**:
  - `docs/adr/`에 결정 ADR(모듈러 모놀리스·경계 강제·커널 단방향)과 state-model·
    glossary의 정식 경로·소유 규칙이 **존재**.
  - `docs/domain/state-model.md`·`glossary.md`가 **선제 생성되지 않음**(디렉터리 존재
    여부 무관; 최초 생성 주체는 로드맵상 P1).
- **매핑**: US2 #1·#2, SC-004, BR-5.

## 시나리오 7 — 빈 커널 (구조 확인)

```bash
uv run python -c "import shared_kernel, pkgutil, sys; \
print('public symbols:', [n for n in dir(shared_kernel) if not n.startswith('_')])"
```
- **기대**: public symbol **0개**(빈 위치). → SC-003.

## 시나리오 8 — CI required check (silent-skip 금지)

- **확인 대상(운영/문서)**: `.github/workflows/ci.yml`이 `tach check`+pytest를 항상
  실행하고, 저장소 브랜치 보호/Ruleset에서 계약 고정 잡 **`quality-gate`**가
  **required status check**로 지정됨. 브랜치 보호·code-owner review 필수화는 저장소
  파일만으로 증명되지 않으므로 tasks 완료 시 설정 증거를 남긴다(C-3·C-5).
- **repo-local 검증(실수 삭제 방어)**:
  ```bash
  uv run pytest tests/ci/test_ci_contract.py
  ```
  `ci.yml`의 계약 고정 잡 id `quality-gate`·trigger(`pull_request` 포함)·스텝 순서
  (`tach check` → pytest)·`continue-on-error`/조건부 `if:` 부재, 그리고
  `.github/CODEOWNERS`의 `/.github/workflows/` 소유 규칙 존재를 단언한다. (의도적
  워크플로 변조는 이 테스트로 못 막는다 — 거버넌스 층 소관, C-5.)
- **기대**: 경계 검사 잡이 누락/optional이면 머지가 차단되고, 스텝이 실수로 빠지면
  CI 계약 테스트가 실패한다.
- **매핑**: FR-003, AC-5, AC-8, Edge Case(무성 미실행).

## 시나리오 9 — 미등록 앱도 경계 밖으로 못 빠진다 (R-BC-4)

`apps/` 아래에 `tach.toml`에 등록하지 않은 앱을 일시 추가하면:
```bash
uv run pytest tests/boundary/test_module_registration.py   # 기대: 실패 (등록 대조)
```
추가로 그 미등록 앱이 등록 앱의 내부 모듈을 import하면:
```bash
uv run tach check          # 기대: 종료 코드 ≠ 0 (root_module = "forbid")
```
- **동작**: 도메인 앱 등록을 사람 기억에 맡기지 않음 — 미등록 자체가 기계적으로
  실패한다. (확인 후 임시 앱 제거.)
- **매핑**: R-BC-4, AC-6, AC-7.

## 시나리오 10 — 픽스처 범위 기계 검증 (SC-003)

```bash
uv run pytest tests/conformance/test_fixture_scope.py
```
- **동작**: 픽스처 앱에 `models.Model` subclass **0**·`migrations` **0**·primitive 정의
  **0**, `shared_kernel` public symbol **0**을 기계적으로 단언한다(코드 리뷰 의존 제거).
- **매핑**: SC-003, FR-005(MUST NOT), Edge Case(픽스처의 도메인/primitive 선점).

---

## Success Criteria 커버리지 요약

| SC | 검증 시나리오 |
|---|---|
| SC-001 (등록된 정적 import 위반 차단·거짓통과 방지) | 2, 3, 9 (등록 자체도 기계 강제) |
| SC-002 (커널 역의존 vacuous 아님) | 4 |
| SC-003 (픽스처 모델 0·커널 심볼 0) | 7, 10 (기계 검증 — 코드 리뷰 의존 없음) |
| SC-004 (ADR 존재·state-model/glossary 미선제생성) | 6 |
| SC-005 (내부 직접 import 0) | 1, 5 (near-miss 차단 포함, AC-9) |
