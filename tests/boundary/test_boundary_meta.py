"""거짓-통과 방지 메타 테스트(AC-4, US1 #4) — 검사기가 위반을 실제로 잡는가.

경계 계약은 "구성이 곧 구현"이므로, 알려진 위반 샘플을 임시 복제본에 주입해
검사기 자체의 유효성을 검증한다(SC-001). 주입 전 통과를 먼저 단언해, 검사기가
무관한 이유(설정 에러 등)로 실패하는 경우를 차단 증거에서 배제한다.
"""


def test_checker_catches_known_violation(project_clone, run_tach):
    baseline = run_tach(project_clone)
    assert baseline.returncode == 0, (
        f"주입 전 복제본이 이미 실패 — 위반 차단 증거로 무효:\n"
        f"{baseline.stdout}\n{baseline.stderr}"
    )

    violation = project_clone / "apps" / "conformance_a" / "violation_sample.py"
    violation.write_text(
        '"""알려진 위반 샘플 — 메타 테스트 전용."""\n'
        "from apps.conformance_b.internal import internal_detail  # noqa: F401\n"
    )

    result = run_tach(project_clone)
    report = result.stdout + result.stderr
    assert result.returncode != 0, "알려진 위반이 통과됨 — 거짓 통과(AC-4 위반)"
    assert "conformance_b.internal" in report, (
        f"위반이 리포트에 존재하지 않음(exit≠0이지만 다른 이유로 실패):\n{report}"
    )
