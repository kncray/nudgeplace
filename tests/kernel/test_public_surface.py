"""커널 공개 표면 특성화(BR-7, FR-008, K-12, SC-006).

Spec 000의 "커널 public symbol 0" 특성화를 대체하는 후계 계약. 네 겹으로 단언한다:
(1) 계약 문서의 EXPECTED_PUBLIC_SURFACE == `__all__`(정렬 포함 정확 일치),
(2) 각 심볼 getattr 실재(유령 심볼 차단),
(3) `__all__`·내부 모듈 정확 allowlist 밖 초과 공개 0건 + 서브모듈 정확 집합,
(4) 신규 프로세스 django.setup 직후 앱 모델 집합 == {IdempotencyRecord, AuditFact}
    + manage.py check 성공(조기 import와 빈 models.py 양쪽 방어).
"""

import ast
import os
import pkgutil
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import shared_kernel

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = (
    REPO_ROOT / 'specs' / '001-shared-kernel-primitives' / 'contracts' / 'kernel-public-surface.md'
)
INTERNAL_MODULE_ALLOWLIST = {
    'actors',
    'apps',
    'audit',
    'correlation',
    'events',
    'idempotency',
    'migrations',
    'models',
    'money',
}


def _expected_surface() -> tuple:
    text = CONTRACT.read_text()
    block = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    assert block, '계약 문서에 python 코드 블록 부재'
    tree = ast.parse(block.group(1))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == 'EXPECTED_PUBLIC_SURFACE' for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError('EXPECTED_PUBLIC_SURFACE 정의를 찾지 못함')


def test_all_matches_contract_exactly():
    """(1) 계약 문서 열거 == __all__ (정렬 포함 정확 일치)."""
    expected = _expected_surface()
    assert list(shared_kernel.__all__) == list(expected)


def test_every_declared_symbol_resolves():
    """(2) __all__의 모든 심볼이 실재한다(유령 심볼 차단 — lazy re-export 포함)."""
    for name in shared_kernel.__all__:
        assert getattr(shared_kernel, name) is not None


def test_no_excess_public_names():
    """(3) __all__·내부 모듈 allowlist 밖 공개 이름 0건 + 서브모듈 정확 집합."""
    public = {n for n in dir(shared_kernel) if not n.startswith('_')}
    excess = public - set(shared_kernel.__all__) - INTERNAL_MODULE_ALLOWLIST
    assert excess == set(), f'초과 공개 이름: {sorted(excess)}'

    submodules = {m.name for m in pkgutil.iter_modules(shared_kernel.__path__)}
    assert submodules == INTERNAL_MODULE_ALLOWLIST, f'서브모듈 집합 불일치: {sorted(submodules)}'


def test_fresh_process_discovers_models_and_check_passes():
    """(4) 신규 프로세스 django.setup 직후 모델 집합 정확 + manage.py check 성공."""
    env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings.ci'}

    setup_code = textwrap.dedent(
        """
        import django
        django.setup()
        from django.apps import apps
        names = sorted(m.__name__ for m in apps.get_app_config("shared_kernel").get_models())
        assert names == ["AuditFact", "IdempotencyRecord"], names
        print("MODELS_OK")
        """
    )
    setup = subprocess.run(
        [sys.executable, '-c', setup_code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert setup.returncode == 0, setup.stderr
    assert 'MODELS_OK' in setup.stdout

    check = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr
