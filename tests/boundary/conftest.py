"""경계 테스트 공용 헬퍼.

위반 샘플은 작업 트리가 아니라 임시 복제본에 주입한다(작업 트리 오염 금지).
tach.toml이 아직 없으면 복제본에도 없으므로, 위반 리포트 단언이 옳은 이유로
실패한다(RED — 설정 부재 에러의 exit 1을 차단 증거로 오인하지 않는다).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLONE_TARGETS = ('tach.toml', 'apps', 'shared_kernel', 'config')


@pytest.fixture(scope='session')
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope='session')
def run_tach():
    def _run(cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ['tach', 'check'], cwd=cwd, capture_output=True, text=True, check=False
        )

    return _run


@pytest.fixture
def project_clone(tmp_path: Path) -> Path:
    for name in CLONE_TARGETS:
        src = REPO_ROOT / name
        if src.is_dir():
            shutil.copytree(src, tmp_path / name, ignore=shutil.ignore_patterns('__pycache__'))
        elif src.is_file():
            shutil.copy2(src, tmp_path / name)
    return tmp_path
