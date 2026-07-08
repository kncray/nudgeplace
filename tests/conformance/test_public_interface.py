"""공개 인터페이스 경유 호출 테스트(SC-005, AC-SI-1·AC-SI-2).

앱 A는 앱 B의 `services` 공개 함수만 경유해 호출한다. 픽스처 내 cross-app 내부
import 0건은 AST 정적 검사로 단언한다(기계 강제 본체는 Tach — 이 테스트는 픽스처
적합성 검증).
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_APPS = ("conformance_a", "conformance_b")
PUBLIC_SURFACE = ("services",)


def test_cross_app_call_goes_through_public_service():
    """AC-SI-1: A가 B의 services 공개 함수를 경유해 호출에 성공한다."""
    from apps.conformance_a import services

    assert services.call_b() == "conformance_b"


def _iter_cross_app_imports():
    """cross-app import의 **전체 접근 경로**(모듈 + 심볼)를 산출한다.

    `from apps.b import services`와 `from apps.b.services import ping` 모두
    "apps.b.services(...)"로 정규화되어 services-only 판정이 가능하다.
    """
    for app in FIXTURE_APPS:
        for py in sorted((REPO_ROOT / "apps" / app).rglob("*.py")):
            tree = ast.parse(py.read_text())
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        base = node.module
                    elif node.level >= 2:
                        # apps/<app>/*.py에서 level 2 상대 import는 apps.<module>로 해석
                        base = f"apps.{node.module}" if node.module else "apps"
                    else:
                        continue
                    targets = [f"{base}.{alias.name}" for alias in node.names]
                for target in targets:
                    parts = target.split(".")
                    if len(parts) >= 2 and parts[0] == "apps" and parts[1] != app:
                        yield py, target


def test_no_cross_app_internal_imports():
    """AC-SI-2: cross-app import는 대상 앱의 `services`만 허용 — 내부 import 0건."""
    violations = []
    for py, target in _iter_cross_app_imports():
        parts = target.split(".")
        if len(parts) < 3 or parts[2] not in PUBLIC_SURFACE:
            violations.append((str(py.relative_to(REPO_ROOT)), target))
    assert violations == [], f"cross-app 내부 import 발견: {violations}"
