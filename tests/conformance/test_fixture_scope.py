"""픽스처 범위 특성화 테스트(SC-003) — 도메인·primitive 선점 금지를 기계 단언.

제약을 고정하는 특성화 테스트로 처음부터 통과 상태로 시작할 수 있다(원칙 XVII).
파일 허용 목록(allowlist)이 "primitive 정의 0"을 기계적으로 근사한다 — 픽스처에
새 파일이 생기면 이 테스트가 실패해 사람 판단을 강제한다.
"""

import ast
from pathlib import Path

import pytest
from django.apps import apps as django_apps

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_APPS = ('conformance_a', 'conformance_b')
ALLOWED_FILES = {
    'conformance_a': {'__init__.py', 'apps.py', 'services.py'},
    'conformance_b': {'__init__.py', 'apps.py', 'services.py', 'internal.py'},
}


@pytest.mark.parametrize('app', FIXTURE_APPS)
def test_no_models(app):
    """models.Model subclass 0 — Django 앱 레지스트리 기준."""
    assert list(django_apps.get_app_config(app).get_models()) == []


@pytest.mark.parametrize('app', FIXTURE_APPS)
def test_no_migrations_package(app):
    assert not (REPO_ROOT / 'apps' / app / 'migrations').exists()


@pytest.mark.parametrize('app', FIXTURE_APPS)
def test_fixture_file_allowlist(app):
    files = {
        p.name for p in (REPO_ROOT / 'apps' / app).rglob('*.py') if '__pycache__' not in p.parts
    }
    unexpected = files - ALLOWED_FILES[app]
    assert not unexpected, f'픽스처 범위 밖 파일(도메인/primitive 선점 의심): {sorted(unexpected)}'


@pytest.mark.parametrize('app', FIXTURE_APPS)
def test_fixture_init_exports_nothing(app):
    """픽스처 `__init__`은 어떤 이름도 export하지 않는다(docstring만 허용).

    패키지 루트 import(`import apps.b`)의 노출 범위가 `__init__` export에
    한정된다는 AC-10 방어의 전제를 특성화로 고정한다 — `__init__` re-export가
    생기면 이 테스트가 사람 판단을 강제한다.
    """
    tree = ast.parse((REPO_ROOT / 'apps' / app / '__init__.py').read_text())
    non_docstring = [
        n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    ]
    assert non_docstring == [], (
        f'apps.{app}/__init__.py에 export 가능 구문 존재: '
        f'{[type(n).__name__ for n in non_docstring]}'
    )


# Spec 000의 `test_shared_kernel_is_empty`(커널 public symbol 0)는 Spec 001에서
# 예고된 제약 변경(BR-7)에 따라 제거되었다 — 커널은 이제 다섯 primitive를 노출한다.
# 후계 계약은 tests/kernel/test_public_surface.py의 공개 표면 특성화(K-12, SC-006)가
# `__all__`·내부 모듈 정확 집합·신규 프로세스 모델 발견을 네 겹으로 강제한다.
# 픽스처 앱(conformance_*)의 "models 0·파일 allowlist" 단언은 위에서 그대로 유지된다.
