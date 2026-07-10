"""CI 계약 테스트(C-5, AC-8) — silent-skip의 '실수 삭제' 실패 모드를 방어.

required status check는 잡 이름 단위 보증이므로, 계약 고정 잡 id(`quality-gate`)·
trigger·스텝 순서·continue-on-error/조건부 skip 부재·CODEOWNERS 소유 규칙을
repo-local로 고정한다. 의도적 워크플로 변조 방어는 플랫폼 층(T014) 소관 —
이 테스트는 CI 안에서 돌므로 그 위협에는 순환적이다.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_YML = REPO_ROOT / '.github' / 'workflows' / 'ci.yml'
CODEOWNERS = REPO_ROOT / '.github' / 'CODEOWNERS'
REQUIRED_JOB_ID = 'quality-gate'


def load_workflow() -> dict:
    return yaml.safe_load(CI_YML.read_text())


def quality_gate_job() -> dict:
    jobs = load_workflow().get('jobs', {})
    assert REQUIRED_JOB_ID in jobs, f"계약 고정 잡 id '{REQUIRED_JOB_ID}' 부재(C-5)"
    return jobs[REQUIRED_JOB_ID]


def find_step(steps: list, needle: str) -> tuple[int, dict]:
    for idx, step in enumerate(steps):
        if needle in step.get('run', ''):
            return idx, step
    raise AssertionError(f"'{needle}' 실행 스텝이 없음")


def test_trigger_includes_pull_request():
    """(1) PR마다 반드시 돈다 — trigger에 pull_request 포함."""
    workflow = load_workflow()
    triggers = workflow.get('on', workflow.get(True))  # YAML 1.1: 'on' 키는 True로 파싱됨
    assert triggers is not None, 'trigger(on:) 부재'
    names = list(triggers) if isinstance(triggers, (dict, list)) else [triggers]
    assert 'pull_request' in names


def test_required_job_runs_tach_then_pytest():
    """(2)(3) 잡 id 고정 + tach check → pytest 스텝 순서."""
    steps = quality_gate_job()['steps']
    tach_idx, _ = find_step(steps, 'tach check')
    pytest_idx, _ = find_step(steps, 'pytest')
    assert tach_idx < pytest_idx


def test_no_silent_skip_escape_hatches():
    """(4) 잡·핵심 스텝에 continue-on-error·조건부 if 금지."""
    job = quality_gate_job()
    assert 'if' not in job, '필수 잡에 조건부 if 금지'
    assert not job.get('continue-on-error'), '필수 잡에 continue-on-error 금지'
    steps = job['steps']
    for needle in ('tach check', 'pytest'):
        _, step = find_step(steps, needle)
        assert 'if' not in step, f"'{needle}' 스텝에 조건부 if 금지"
        assert not step.get('continue-on-error'), f"'{needle}' 스텝에 continue-on-error 금지"


def test_check_context_cannot_drift_or_be_spoofed():
    """required check context(=잡 id)의 표류·위장 금지.

    check run 이름은 잡의 `name:`이 있으면 그것을 따른다 — quality-gate 잡에
    name 오버라이드가 붙으면 required context가 보고되지 않고(표류), 다른 no-op
    잡에 `name: quality-gate`가 붙으면 required check가 no-op 성공으로 충족된다(위장).
    """
    jobs = load_workflow().get('jobs', {})
    gate = jobs[REQUIRED_JOB_ID]
    assert gate.get('name') in (None, REQUIRED_JOB_ID), (
        'quality-gate 잡의 name 오버라이드 금지(required context 표류)'
    )
    impostors = [
        job_id
        for job_id, job in jobs.items()
        if job_id != REQUIRED_JOB_ID and job.get('name') == REQUIRED_JOB_ID
    ]
    assert impostors == [], f'quality-gate 이름을 위장한 잡 존재: {impostors}'


POSTGRES_ENV_VARS = {
    'POSTGRES_HOST',
    'POSTGRES_PORT',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
}


def test_quality_gate_has_postgres_service():
    """(6) quality-gate 잡에 postgres 서비스 컨테이너(이미지·healthcheck) 존재(R1).

    멱등·감사 DB 테스트는 실제 PostgreSQL 의미론이 전제다(SC-004 동시성) —
    서비스 컨테이너 부재 시 pytest가 접속 실패로 죽지만, 드리프트를 계약으로 막는다.
    """
    job = quality_gate_job()
    services = job.get('services', {})
    assert 'postgres' in services, 'quality-gate 잡에 postgres 서비스 부재(R1)'
    pg = services['postgres']
    assert 'postgres' in str(pg.get('image', '')), 'postgres 서비스 이미지 미지정'
    assert '--health-cmd' in pg.get('options', ''), 'postgres 서비스 healthcheck(--health-cmd) 부재'


def test_quality_gate_env_has_postgres_connection_vars():
    """(7) 잡 env에 POSTGRES_* 접속 변수 존재 — base.py 접속 계약과 동기화."""
    job = quality_gate_job()
    env = job.get('env', {})
    missing = POSTGRES_ENV_VARS - set(env)
    assert not missing, f'quality-gate 잡 env에 POSTGRES_* 변수 누락: {sorted(missing)}'


def _codeowners_rules() -> list[list[str]]:
    assert CODEOWNERS.exists(), '.github/CODEOWNERS 부재(C-5)'
    return [
        line.split()
        for line in CODEOWNERS.read_text().splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]


def test_codeowners_covers_workflows():
    """(5) 워크플로 변경 리뷰 게이트의 repo-local 절반 — CODEOWNERS 소유 규칙."""
    rules = _codeowners_rules()
    workflow_rules = [
        r for r in rules if r[0] == '/.github/workflows/' and len(r) >= 2 and r[1].startswith('@')
    ]
    assert workflow_rules, '/.github/workflows/ 소유 규칙 부재'


def test_codeowners_protects_itself():
    """CODEOWNERS 자체가 무소유면 소유 규칙 제거 → 워크플로 변조의 2단계 우회가 성립한다."""
    rules = _codeowners_rules()
    self_rules = [
        r for r in rules if r[0] == '/.github/CODEOWNERS' and len(r) >= 2 and r[1].startswith('@')
    ]
    assert self_rules, '/.github/CODEOWNERS 자기보호 규칙 부재'
