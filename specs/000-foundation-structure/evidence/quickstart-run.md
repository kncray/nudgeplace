# Evidence: Quickstart 시나리오 실행 기록 (T016)

**실행일**: 2026-07-08 | **환경**: macOS(darwin), Python 3.12, uv 0.11.16,
Django 5.2.16, tach 0.35.0 | **실행자**: Claude(구현 세션) — quickstart.md 시나리오 1~10 전수 실행.

## RED → GREEN 증거 (원칙 XVII, FR-007)

### US1 (T010t·T011t·T013t 작성 직후, 구현 전)

```
13 failed, 8 passed
```

실패는 전부 "옳은 이유"의 RED — 위반이 리포트되지 않음(tach.toml 부재), ci.yml·
CODEOWNERS 파일 부재, `call_b` 함수 부재(AttributeError). 특성화 테스트(T012
fixture_scope 7건)와 cross-app 내부 import 0건 검사 1건은 설계대로 처음부터 통과.

### US1 GREEN (T010 tach.toml + T011 call_b + T013 ci.yml + T013b CODEOWNERS 후)

```
uv run tach check   → ✅ All modules validated! (exit 0)
uv run pytest       → 21 passed
```

과정에서 테스트 버그 1건 수정: `test_no_cross_app_internal_imports`가
`from apps.conformance_b import services`(적법한 services 접근)를 오탐 —
ImportFrom의 전체 접근 경로(모듈+심볼) 정규화로 교정.

### US2 (T015t 작성 직후, ADR 작성 전)

```
4 failed, 2 passed
```

실패 4건 = ADR 3건 부재 + 소유 규칙 미기록(옳은 이유의 RED). 통과 2건 =
state-model·glossary **부존재** 단언(BR-5 — 이미 참인 특성화).

### US2 GREEN (T015a·b·c ADR 작성 후)

```
uv run pytest → 27 passed
```

## 시나리오 실행 결과 (2026-07-08)

| # | 시나리오 | 실행 | 결과 |
|---|---|---|---|
| 1 | 깨끗한 트리 경계 검사 | `uv run tach check` | ✅ exit 0 — "All modules validated!" |
| 2 | 내부 모듈 위반 차단 | A에 `conformance_b.internal` import 주입 → check → 복원 | ✅ exit 1 + 리포트에 위반 경로 식별(`apps.conformance_b.internal.internal_detail ... not part of the public interface`), 복원 후 exit 0 |
| 3 | 거짓-통과 방지 메타 | `pytest tests/boundary/test_boundary_meta.py` | ✅ 1 passed (주입 전 통과 → 주입 후 exit≠0 + 리포트 식별) |
| 4 | 커널 역의존 차단 | `shared_kernel`에 픽스처 import 주입 → check → 복원 | ✅ exit 1 — `Module 'shared_kernel' cannot depend on 'apps.conformance_a'` |
| 5 | 공개 인터페이스 경유 + near-miss | `pytest tests/conformance/test_public_interface.py tests/boundary/test_boundary_contract.py` | ✅ 6 passed (AC-SI-1·AC-SI-2 + AC-9 `services_private` 차단) |
| 6 | 문서 소유 규칙 | `pytest tests/docs/test_docs_ownership.py` | ✅ 6 passed |
| 7 | 빈 커널 | `python -c "...dir(shared_kernel)..."` | ✅ `public symbols: []` |
| 8 | CI required check | repo-local: `pytest tests/ci/test_ci_contract.py` / 플랫폼: 브랜치 보호 | ✅ repo-local 4 passed (잡 id `quality-gate`·trigger·스텝 순서·skip 금지·CODEOWNERS) / 플랫폼 증거: [branch-protection.md](./branch-protection.md) (T014) |
| 9 | 미등록 앱 봉쇄 | `apps/rogue` 주입(등록 없이 내부 import) → 검증 → 제거 | ✅ 등록 대조 테스트 FAILED(AC-7) + `tach check` exit 1 — `Module '<root>' cannot depend on 'apps.conformance_b'`(forbid, AC-6) |
| 10 | 픽스처 범위 | `pytest tests/conformance/test_fixture_scope.py` | ✅ 7 passed (models 0·migrations 0·파일 allowlist·커널 심볼 0) |

## Success Criteria 최종 대조 (T017)

| SC | 판정 근거 (통과 테스트 / 증거) |
|---|---|
| SC-001 위반 차단·거짓 통과 방지 | 시나리오 2·3·9 + `test_boundary_contract`·`test_boundary_meta`(위반 리포트 내용 단언) |
| SC-002 커널 역의존 non-vacuous | 시나리오 4 + `test_kernel_reverse_dependency_blocked`(픽스처 = 도메인 계층) |
| SC-003 모델 0·커널 심볼 0 | 시나리오 7·10 + `test_fixture_scope`(레지스트리·allowlist·pkgutil 기계 단언) |
| SC-004 ADR 존재·미선제생성 | 시나리오 6 + `test_docs_ownership`(부존재 단언 포함) |
| SC-005 내부 직접 import 0 | 시나리오 1·5 + `test_no_cross_app_internal_imports`(전체 접근 경로 AST) + AC-9 |

## 품질 마감 (T017)

```
uv run ruff check .            → All checks passed! (exit 0)
uv run python manage.py check  → System check identified no issues
uv run pytest                  → 27 passed
git status                     → clean (위반 주입 전부 복원 확인)
```
