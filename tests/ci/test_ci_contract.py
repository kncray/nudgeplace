"""CI 계약 테스트(C-5, AC-8) — silent-skip의 '실수 삭제' 실패 모드를 방어.

required status check는 잡 이름 단위 보증이므로, 계약 고정 잡 id(`quality-gate`)·
trigger·스텝 순서·continue-on-error/조건부 skip 부재·CODEOWNERS 소유 규칙을
repo-local로 고정한다. 의도적 워크플로 변조 방어는 플랫폼 층(T014) 소관 —
이 테스트는 CI 안에서 돌므로 그 위협에는 순환적이다.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"
REQUIRED_JOB_ID = "quality-gate"


def load_workflow() -> dict:
    return yaml.safe_load(CI_YML.read_text())


def quality_gate_job() -> dict:
    jobs = load_workflow().get("jobs", {})
    assert REQUIRED_JOB_ID in jobs, f"계약 고정 잡 id '{REQUIRED_JOB_ID}' 부재(C-5)"
    return jobs[REQUIRED_JOB_ID]


def find_step(steps: list, needle: str) -> tuple[int, dict]:
    for idx, step in enumerate(steps):
        if needle in step.get("run", ""):
            return idx, step
    raise AssertionError(f"'{needle}' 실행 스텝이 없음")


def test_trigger_includes_pull_request():
    """(1) PR마다 반드시 돈다 — trigger에 pull_request 포함."""
    workflow = load_workflow()
    triggers = workflow.get("on", workflow.get(True))  # YAML 1.1: 'on' 키는 True로 파싱됨
    assert triggers is not None, "trigger(on:) 부재"
    names = list(triggers) if isinstance(triggers, (dict, list)) else [triggers]
    assert "pull_request" in names


def test_required_job_runs_tach_then_pytest():
    """(2)(3) 잡 id 고정 + tach check → pytest 스텝 순서."""
    steps = quality_gate_job()["steps"]
    tach_idx, _ = find_step(steps, "tach check")
    pytest_idx, _ = find_step(steps, "pytest")
    assert tach_idx < pytest_idx


def test_no_silent_skip_escape_hatches():
    """(4) 잡·핵심 스텝에 continue-on-error·조건부 if 금지."""
    job = quality_gate_job()
    assert "if" not in job, "필수 잡에 조건부 if 금지"
    assert not job.get("continue-on-error"), "필수 잡에 continue-on-error 금지"
    steps = job["steps"]
    for needle in ("tach check", "pytest"):
        _, step = find_step(steps, needle)
        assert "if" not in step, f"'{needle}' 스텝에 조건부 if 금지"
        assert not step.get("continue-on-error"), f"'{needle}' 스텝에 continue-on-error 금지"


def test_codeowners_covers_workflows():
    """(5) 워크플로 변경 리뷰 게이트의 repo-local 절반 — CODEOWNERS 소유 규칙."""
    assert CODEOWNERS.exists(), ".github/CODEOWNERS 부재(C-5)"
    rules = [
        line.split()
        for line in CODEOWNERS.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    workflow_rules = [
        r for r in rules if r[0] == "/.github/workflows/" and len(r) >= 2 and r[1].startswith("@")
    ]
    assert workflow_rules, "/.github/workflows/ 소유 규칙 부재"
