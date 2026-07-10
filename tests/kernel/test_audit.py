"""불변 감사 사실 계약(US4 #1~3, FR-006, SC-005, K-10·13).

2층 강제(모델 계층 + DB 트리거)와 원자 기록을 검증한다. DB 테스트는
`django_db(transaction=True)`이고 성공 경로만 본문에서 명시적 atomic을 연다
(record_audit_fact는 호출자의 열린 트랜잭션에 참여 — FR-006).
"""

import uuid

import pytest
from django.db import Error, connection, transaction

from shared_kernel.actors import Actor, ActorRole
from shared_kernel.audit import (
    AuditError,
    AuditFact,
    AuditWriteError,
    record_audit_fact,
)

pytestmark = pytest.mark.django_db(transaction=True)


def _actor() -> Actor:
    return Actor(ActorRole.OPERATOR, 'op-1')


def _record(**over):
    kwargs = {
        'actor': _actor(),
        'target_type': 'order',
        'target_id': 'order-1',
        'reason_text': 'manual refund',
        'evidence_ref': 'ticket:123',
    }
    kwargs.update(over)
    return record_audit_fact(**kwargs)


# --- 기록·조회 (US4 #1, SC-005) ---


def test_records_all_required_fields():
    with transaction.atomic():
        _record(reason_code='REFUND')
    fact = AuditFact.objects.get()
    assert fact.actor_role == ActorRole.OPERATOR.value
    assert fact.actor_id == 'op-1'
    assert fact.target_type == 'order'
    assert fact.target_id == 'order-1'
    assert fact.reason_text == 'manual refund'
    assert fact.reason_code == 'REFUND'
    assert fact.evidence_ref == 'ticket:123'
    assert isinstance(fact.correlation_id, uuid.UUID)
    assert fact.recorded_at is not None


def test_reason_code_is_optional():
    with transaction.atomic():
        _record()
    assert AuditFact.objects.get().reason_code in (None, '')


# --- 필수 필드 누락 거부 (US4 #3) ---


@pytest.mark.parametrize('field', ['target_type', 'target_id', 'evidence_ref', 'reason_text'])
def test_missing_required_field_rejected(field):
    with transaction.atomic():
        with pytest.raises((ValueError, TypeError)):
            _record(**{field: ''})


def test_missing_actor_rejected():
    with transaction.atomic():
        with pytest.raises((ValueError, TypeError)):
            _record(actor=None)


# --- backdate 거부 (K-13) ---


def test_caller_supplied_recorded_at_rejected():
    with transaction.atomic():
        with pytest.raises(TypeError):
            _record(recorded_at='2020-01-01T00:00:00Z')


# --- 원자성 강제 (FR-006) ---


def test_record_outside_atomic_rejected():
    """열린 atomic 밖(autocommit)에서 기록 시도 → 거부 — ORM 호출 전에 검사."""
    with pytest.raises(AuditError):
        _record()
    assert AuditFact.objects.count() == 0


def test_caller_transaction_rollback_rolls_back_audit():
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            _record()
            raise RuntimeError('caller failed')
    assert AuditFact.objects.count() == 0


# --- 공개 ORM 조회 전용 (K-10) ---


def test_public_manager_write_methods_rejected():
    with transaction.atomic():
        _record()
    fact = AuditFact.objects.get()
    with pytest.raises(AuditWriteError):
        AuditFact.objects.create(actor_role='OPERATOR', actor_id='x')
    with pytest.raises(AuditWriteError):
        AuditFact.objects.get_or_create(actor_id='x')
    with pytest.raises(AuditWriteError):
        AuditFact.objects.update_or_create(actor_id='x')
    with pytest.raises(AuditWriteError):
        AuditFact.objects.filter(pk=fact.pk).update(reason_text='tampered')
    with pytest.raises(AuditWriteError):
        AuditFact.objects.filter(pk=fact.pk).delete()
    with pytest.raises(AuditWriteError):
        fact.save()
    with pytest.raises(AuditWriteError):
        fact.delete()


def test_public_manager_write_rejected_even_inside_atomic():
    with transaction.atomic():
        _record()
    with transaction.atomic():
        with pytest.raises(AuditWriteError):
            AuditFact.objects.create(actor_role='OPERATOR', actor_id='x')


# --- DB 트리거: raw SQL 수정·삭제 거부 (K-10, R5, SC-005 100% 거부) ---


def test_raw_sql_update_denied_by_trigger():
    with transaction.atomic():
        _record()
    pk = AuditFact.objects.get().pk
    with pytest.raises(Error):
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute("UPDATE shared_kernel_auditfact SET reason_text='x' WHERE id=%s", [pk])
    assert AuditFact.objects.get(pk=pk).reason_text == 'manual refund'


def test_raw_sql_delete_denied_by_trigger():
    with transaction.atomic():
        _record()
    pk = AuditFact.objects.get().pk
    with pytest.raises(Error):
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('DELETE FROM shared_kernel_auditfact WHERE id=%s', [pk])
    assert AuditFact.objects.filter(pk=pk).exists()


# --- 앱 레지스트리 모델 집합 ---


def test_app_registry_model_set_exact():
    from django.apps import apps

    models = {m.__name__ for m in apps.get_app_config('shared_kernel').get_models()}
    assert models == {'IdempotencyRecord', 'AuditFact'}
