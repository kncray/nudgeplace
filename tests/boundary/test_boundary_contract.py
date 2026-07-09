"""경계 계약 테스트 — 허용 edge 통과 / 위반 차단 (AC-1·AC-2·AC-3·AC-9).

exit code 단독 단언 금지: `tach check`는 tach.toml 부재 같은 설정 에러도 exit 1
이므로, 위반 케이스는 반드시 "위반 경로가 리포트에 식별됨"을 함께 단언한다.
"""


def test_allowed_edge_passes(repo_root, run_tach):
    """AC-2: 선언된 edge(A→B.services) 위의 깨끗한 트리는 통과한다."""
    result = run_tach(repo_root)
    assert result.returncode == 0, (
        f'깨끗한 트리에서 경계 검사 실패:\n{result.stdout}\n{result.stderr}'
    )


def test_cross_app_internal_import_blocked(project_clone, run_tach):
    """AC-1: 앱 A가 앱 B의 내부 모듈(internal)을 직접 import하면 차단된다."""
    services = project_clone / 'apps' / 'conformance_a' / 'services.py'
    services.write_text(
        services.read_text()
        + '\nfrom apps.conformance_b.internal import internal_detail  # noqa: F401\n'
    )
    result = run_tach(project_clone)
    report = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'conformance_b.internal' in report, f'위반이 리포트에 식별되지 않음:\n{report}'


def test_near_miss_public_surface_blocked(project_clone, run_tach):
    """AC-9: `services_private` 같은 유사명 모듈은 공개 표면으로 인정되지 않는다.

    expose가 비이스케이프 `services.*`면 이 케이스가 통과해버린다(재현 확인
    2026-07-08) — regex 점 이스케이프를 고정하는 테스트다.
    """
    (project_clone / 'apps' / 'conformance_b' / 'services_private.py').write_text(
        "def secret():\n    return 'near-miss'\n"
    )
    services = project_clone / 'apps' / 'conformance_a' / 'services.py'
    services.write_text(
        services.read_text()
        + '\nfrom apps.conformance_b.services_private import secret  # noqa: F401\n'
    )
    result = run_tach(project_clone)
    report = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'services_private' in report, f'near-miss가 공개 표면으로 오인됨(AC-9):\n{report}'


def test_kernel_reverse_dependency_blocked(project_clone, run_tach):
    """AC-3: 빈 커널이 도메인 계층(픽스처 앱)을 import하면 차단된다(BR-3, vacuous 아님)."""
    kernel = project_clone / 'shared_kernel' / '__init__.py'
    kernel.write_text(
        kernel.read_text() + '\nfrom apps.conformance_a.services import ping  # noqa: F401\n'
    )
    result = run_tach(project_clone)
    report = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'conformance_a' in report, f'커널 역의존이 리포트에 식별되지 않음:\n{report}'
