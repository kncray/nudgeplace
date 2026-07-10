"""상관관계 컨텍스트 계약(FR-010, R6, K-11) — US2~US4 기록의 전제 primitive.

관통 통합(세 기록이 같은 correlation으로 연결)은 US5(test_correlation.py의
T060t 케이스)가 검증한다. 여기서는 발급·고정·요청 경계 reset·스레드 전파
경계의 primitive 규약만 고정한다.
"""

import contextvars
import threading
import uuid

import pytest

from shared_kernel.actors import Actor, ActorRole
from shared_kernel.audit import AuditFact, record_audit_fact
from shared_kernel.correlation import (
    bind_correlation_id,
    correlation_context,
    get_correlation_id,
    reset_correlation_id,
)
from shared_kernel.events import SideEffect, SyncDispatcher, publish, subscribe, use_dispatcher
from shared_kernel.idempotency import IdempotencyRecord, run_idempotent


@pytest.fixture(autouse=True)
def _isolate_correlation():
    """각 테스트를 신선한 correlation 스코프로 격리 — 순차 테스트 간 누출 방지."""
    with correlation_context():
        yield


def test_unset_access_issues_and_fixes():
    """미설정 시 첫 접근에서 발급하고, 이후 접근은 같은 값으로 고정된다."""
    first = get_correlation_id()
    second = get_correlation_id()
    assert isinstance(first, uuid.UUID)
    assert first == second


def test_bind_returns_reset_token_and_reset_restores():
    """bind는 reset token을 반환하고, reset은 이전 상태로 되돌린다(누출 없음)."""
    outer = get_correlation_id()
    injected = uuid.uuid4()
    token = bind_correlation_id(injected)
    assert get_correlation_id() == injected
    reset_correlation_id(token)
    assert get_correlation_id() == outer


def test_correlation_context_no_leak_after_exit():
    """요청 경계 context 종료 후 내부 correlation이 밖으로 누출되지 않는다."""
    with correlation_context() as _:
        inner = get_correlation_id()
    outer = get_correlation_id()
    assert inner != outer


def test_correlation_context_binds_given_value():
    """명시 값 주입 시 스코프 내에서 그 값이 흐른다."""
    fixed = uuid.uuid4()
    with correlation_context(fixed):
        assert get_correlation_id() == fixed


def test_new_thread_does_not_inherit_context():
    """새 스레드는 컨텍스트를 상속하지 않는다 — 독립 발급(R6, 누출 없음의 이면)."""
    parent = get_correlation_id()
    captured: dict[str, uuid.UUID] = {}

    def worker():
        captured['child'] = get_correlation_id()

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert captured['child'] != parent


def test_copy_context_handoff_preserves_correlation():
    """copy_context() 래핑 시 스레드 핸드오프에서 동일 correlation 유지(명시 규약)."""
    parent = get_correlation_id()
    captured: dict[str, uuid.UUID] = {}

    def worker():
        captured['child'] = get_correlation_id()

    ctx = contextvars.copy_context()
    t = threading.Thread(target=lambda: ctx.run(worker))
    t.start()
    t.join()
    assert captured['child'] == parent


# --- US5: 관통 추적 통합(FR-010, SC-007, K-11) ---
# 세 primitive(멱등·감사·이벤트)가 같은 correlation으로 연결됨을 커널 수준 통합으로
# 실증한다. 별도 구현 태스크 없음 — 세 primitive의 correlation 기록이 곧 구현이다.


def _run_flow(key: str):
    """run_idempotent가 소유한 operation atomic 안에서 감사 기록 + 이벤트 발행."""
    disp = SyncDispatcher()
    published: list = []
    subscribe(
        'kernel.ProbeRecorded',
        published.append,
        side_effect=SideEffect.INTERNAL,
        dispatcher=disp,
    )

    def operation():
        record_audit_fact(
            Actor(ActorRole.SYSTEM, 'sys'), 'probe', 'p-1', 'probe recorded', 'evidence:flow'
        )
        publish(
            'kernel.ProbeRecorded',
            aggregate_type='kernel.Probe',
            aggregate_id='p-1',
            payload_version=1,
            payload={},
        )
        return 'ok'

    with use_dispatcher(disp):
        run_idempotent('ns', 's', key, {'a': 1}, operation, fingerprint_version=1)

    idem = IdempotencyRecord.objects.get(key=key)
    audit = AuditFact.objects.get()
    return idem, audit, published[0]


@pytest.mark.django_db(transaction=True)
def test_three_records_share_explicit_correlation():
    fixed = uuid.uuid4()
    with correlation_context(fixed):
        idem, audit, event = _run_flow('flow-explicit')
    assert idem.correlation_id == fixed
    assert audit.correlation_id == fixed
    assert event.correlation_id == fixed


@pytest.mark.django_db(transaction=True)
def test_unset_flow_issues_and_shares_correlation():
    # autouse 픽스처가 신선한(미설정) 스코프를 연다 — 첫 접근에서 시스템 발급.
    idem, audit, event = _run_flow('flow-auto')
    assert idem.correlation_id == audit.correlation_id == event.correlation_id
    assert isinstance(idem.correlation_id, uuid.UUID)
