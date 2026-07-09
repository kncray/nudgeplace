"""모듈 등록 대조 테스트(R-BC-4, AC-6·AC-7) — 미등록 앱은 경계 밖으로 빠질 수 없다.

`root_module = "forbid"`만으로는 미등록 패키지 간 상호 import를 못 잡으므로(재현
확인 2026-07-08), `apps/` 직계 자식 전수가 tach 모듈로 등록되었는지 파일시스템과
대조한다. 중첩 하위 패키지(예: 향후 apps/<domain>/domain/)는 부모 모듈 경계
소속이라 대상이 아니다. 과잉 exclude로 인한 검사 표면 침식도 함께 차단한다.
"""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROTECTED_PREFIXES = ('apps', 'config', 'shared_kernel')


def load_tach_config() -> dict:
    with open(REPO_ROOT / 'tach.toml', 'rb') as f:
        return tomllib.load(f)


def apps_direct_children() -> set[str]:
    children = set()
    for entry in (REPO_ROOT / 'apps').iterdir():
        if entry.name in ('__init__.py', '__pycache__'):
            continue
        if entry.is_dir():
            children.add(f'apps.{entry.name}')
        elif entry.suffix == '.py':
            children.add(f'apps.{entry.stem}')
    return children


def test_all_apps_direct_children_registered():
    """AC-7: apps/ 직계 자식(패키지·모듈, __init__.py 제외) 전수 등록."""
    registered = {m['path'] for m in load_tach_config().get('modules', [])}
    missing = apps_direct_children() - registered
    assert not missing, f'tach.toml에 등록되지 않은 apps/ 직계 자식: {sorted(missing)}'


def test_root_module_forbid():
    """AC-6: 미등록(<root>) 코드 ↔ 등록 모듈 간 import 양방향 차단 설정."""
    assert load_tach_config().get('root_module') == 'forbid'


def test_exclude_does_not_erode_checked_surface():
    """exclude가 apps·config·shared_kernel(하위 포함)을 건드리면 검사 표면이 침식된다."""
    excludes = load_tach_config().get('exclude', [])
    eroding = [e for e in excludes if any(e.lstrip('./').startswith(p) for p in PROTECTED_PREFIXES)]
    assert not eroding, f'검사 대상을 exclude가 침식: {eroding}'
