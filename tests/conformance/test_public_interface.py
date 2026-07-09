"""공개 인터페이스 경유 호출 테스트(SC-005, AC-SI-1·AC-SI-2, AC-10).

앱 간 접근은 대상 앱의 `services`만 허용한다. Tach 인터페이스는 선언된 edge 위의
**패키지 루트 import**(`import apps.b`, `from apps import b`)를 잡지 못하므로
(재현 확인 2026-07-09 — 정적·런타임 노출은 대상 `__init__` export에 한정),
이 AST 검사가 그 형태를 포함한 cross-app 접근 전수를 판정한다. 스캔 대상은
apps/ 직계 자식 전수 — 미래 도메인도 자동 포함된다.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APPS_DIR = REPO_ROOT / 'apps'
PUBLIC_SURFACE = ('services',)


def domain_apps() -> tuple[str, ...]:
    return tuple(
        sorted(p.name for p in APPS_DIR.iterdir() if p.is_dir() and p.name != '__pycache__')
    )


def cross_app_imports(app: str, source: str):
    """소스 내 cross-app import를 전체 접근 경로(모듈+심볼)로 정규화해 산출한다.

    `from apps.b import services`와 `from apps.b.services import ping` 모두
    "apps.b.services(...)"로 정규화되고, `import apps.b`·`from apps import b`는
    "apps.b"(패키지 루트 접근)로 산출된다.
    """
    for node in ast.walk(ast.parse(source)):
        targets = []
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                base = node.module
            elif node.level >= 2:
                # apps/<app>/*.py에서 level 2 상대 import는 apps(.<module>)로 해석
                base = f'apps.{node.module}' if node.module else 'apps'
            else:
                continue
            targets = [f'{base}.{alias.name}' for alias in node.names]
        for target in targets:
            parts = target.split('.')
            if len(parts) >= 2 and parts[0] == 'apps' and parts[1] != app:
                yield target


def is_violation(target: str) -> bool:
    """cross-app 접근 경로가 services 공개 표면 밖이면 위반 — 패키지 루트 접근
    (`apps.b`, 경로 길이 2)도 위반이다(AC-10)."""
    parts = target.split('.')
    return len(parts) < 3 or parts[2] not in PUBLIC_SURFACE


def test_cross_app_call_goes_through_public_service():
    """AC-SI-1: A가 B의 services 공개 함수를 경유해 호출에 성공한다."""
    from apps.conformance_a import services

    assert services.call_b() == 'conformance_b'


def test_no_cross_app_internal_imports():
    """AC-SI-2: apps/ 전수에서 cross-app import는 대상 앱의 `services`만 — 위반 0건."""
    violations = []
    for app in domain_apps():
        for py in sorted((APPS_DIR / app).rglob('*.py')):
            if '__pycache__' in py.parts:
                continue
            for target in cross_app_imports(app, py.read_text()):
                if is_violation(target):
                    violations.append((str(py.relative_to(REPO_ROOT)), target))
    assert violations == [], f'cross-app 내부/루트 import 발견: {violations}'


@pytest.mark.parametrize(
    'sample',
    [
        'import apps.conformance_b',
        'from apps import conformance_b',
        'from apps.conformance_b import internal',
        'from apps.conformance_b.internal import internal_detail',
        'import apps.conformance_b.internal',
        'from ..conformance_b import internal',
    ],
)
def test_detector_flags_non_service_access(sample):
    """AC-10: 패키지 루트·내부 모듈 접근 형태가 위반으로 판정된다(검출기 특성화).

    루트 import 형태는 Tach 인터페이스가 잡지 못함을 재현 확인(2026-07-09) —
    이 검출기가 해당 형태의 유일한 기계 방어층이다.
    """
    targets = list(cross_app_imports('conformance_a', sample))
    assert targets and all(is_violation(t) for t in targets), sample


@pytest.mark.parametrize(
    'sample',
    [
        'from apps.conformance_b import services',
        'from apps.conformance_b.services import ping',
        'import apps.conformance_b.services',
    ],
)
def test_detector_allows_service_surface(sample):
    """services 공개 표면 경유 접근은 허용으로 판정된다(오탐 방지)."""
    targets = list(cross_app_imports('conformance_a', sample))
    assert targets and not any(is_violation(t) for t in targets), sample
