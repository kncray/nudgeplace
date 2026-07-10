"""멱등 실행 프로토콜 계약(US3 #1~8, FR-005, BR-4, SC-004, K-7·8·9).

contracts/idempotency-protocol.md와 1:1. 파일의 DB 테스트는 전부
`django_db(transaction=True)` — pytest-django의 암묵 atomic 래퍼가 "외부 atomic
거부"를 오탐하지 않게 하고, 2단계 클레임의 독립 커밋을 실제로 커밋시킨다.
operation 효과는 DB-backed(트랜잭션 참여)로 검증한다.
"""

import hashlib
import threading
import uuid
from datetime import timedelta

import pytest
from django.db import connection, transaction
from django.db.transaction import TransactionManagementError
from django.db.utils import IntegrityError
from django.utils import timezone

from shared_kernel.correlation import correlation_context
from shared_kernel.idempotency import (
    IdempotencyConflict,
    IdempotencyRecord,
    IdempotencyStatus,
    IdempotencyWriteError,
    InProgress,
    LostClaimError,
    UnknownOutcome,
    canonical_json,
    mark_unknown,
    resolve_unknown_as_completed,
    resolve_unknown_as_definite_failure,
    run_idempotent,
)

pytestmark = pytest.mark.django_db(transaction=True)

EFFECT_TABLE = 'kernel_probe_effect'


@pytest.fixture(autouse=True)
def _effect_table():
    """DB-backed 효과 카운터 — 비즈니스 트랜잭션에 참여(롤백 시 함께 사라짐)."""
    with connection.cursor() as c:
        c.execute(f'DROP TABLE IF EXISTS {EFFECT_TABLE}')
        c.execute(f'CREATE TABLE {EFFECT_TABLE} (id serial PRIMARY KEY, tag text)')
    yield
    with connection.cursor() as c:
        c.execute(f'DROP TABLE IF EXISTS {EFFECT_TABLE}')


def effect_count() -> int:
    with connection.cursor() as c:
        c.execute(f'SELECT count(*) FROM {EFFECT_TABLE}')
        return c.fetchone()[0]


def make_op(result_value, tag='x'):
    def op():
        with connection.cursor() as c:
            c.execute(f'INSERT INTO {EFFECT_TABLE}(tag) VALUES (%s)', [tag])
        return result_value

    return op


def fingerprint_of(request, canonicalize=canonical_json) -> str:
    return hashlib.sha256(canonicalize(request).encode()).hexdigest()


def run(key='k', *, namespace='ns', scope='s', request=None, op=None, **kw):
    if request is None:
        request = {'a': 1}
    if op is None:
        op = make_op('RESULT')
    return run_idempotent(namespace, scope, key, request, op, fingerprint_version=1, **kw)


def _seed_in_progress(
    key, *, namespace='ns', scope='s', request=None, claim_token=None, expired=False
):
    request = request if request is not None else {'a': 1}
    now = timezone.now()
    expires = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    rec = IdempotencyRecord(
        namespace=namespace,
        scope=scope,
        key=key,
        fingerprint=fingerprint_of(request),
        fingerprint_version=1,
        status=IdempotencyStatus.IN_PROGRESS.value,
        claim_token=claim_token or uuid.uuid4(),
        claimed_at=now,
        in_progress_expires_at=expires,
        correlation_id=uuid.uuid4(),
    )
    IdempotencyRecord._writer.bulk_create([rec])
    return IdempotencyRecord.objects.get(namespace=namespace, scope=scope, key=key)


# --- ⓪ 외부 atomic 거부 ---


def test_reject_when_called_inside_outer_atomic():
    with transaction.atomic():
        with pytest.raises(TransactionManagementError):
            run('outer-atomic')
    assert effect_count() == 0
    assert not IdempotencyRecord.objects.filter(key='outer-atomic').exists()


# --- ① 완료 재시도 = 결과 반환, 효과 1회 (US3 #1) ---


def test_same_key_thrice_effect_once_same_result():
    results = [run('dup', op=make_op('R')) for _ in range(3)]
    assert results == ['R', 'R', 'R']
    assert effect_count() == 1


# --- ① 지문/버전 대조 (US3 #2, K-8) ---


def test_same_key_different_fingerprint_conflict():
    run('conf', request={'a': 1})
    with pytest.raises(IdempotencyConflict):
        run('conf', request={'a': 2})  # 같은 키·다른 요청


def test_version_mismatch_is_conflict():
    run_idempotent('ns', 's', 'ver', {'a': 1}, make_op('R'), fingerprint_version=1)
    with pytest.raises(IdempotencyConflict):
        run_idempotent('ns', 's', 'ver', {'a': 1}, make_op('R'), fingerprint_version=2)


def test_correlation_only_difference_passes():
    """지문에 추적 메타데이터 제외(FR-005) — correlation만 다른 재시도는 통과."""
    with correlation_context():
        r1 = run('corr', request={'a': 1})
    with correlation_context():
        r2 = run('corr', request={'a': 1})
    assert r1 == r2
    assert effect_count() == 1


def test_different_scope_same_key_independent():
    run('shared-key', scope='vendor:1', op=make_op('A'))
    r = run('shared-key', scope='vendor:2', op=make_op('B'))
    assert r == 'B'
    assert effect_count() == 2


# --- ① 동시 도착 효과 1회 (US3 #3, SC-004) ---


def test_concurrent_arrival_effect_once():
    n = 8
    barrier = threading.Barrier(n)
    outcomes: list = []
    lock = threading.Lock()

    def worker():
        barrier.wait()
        try:
            r = run('race', op=make_op('R', tag='race'))
            with lock:
                outcomes.append(('ok', r))
        except InProgress:
            with lock:
                outcomes.append(('in_progress', None))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert effect_count() == 1  # 커밋 효과 정확히 1회
    assert any(kind == 'ok' for kind, _ in outcomes)


# --- ⓪ 진행 중 신호 (US3 #6) ---


def test_in_progress_not_expired_signals_in_progress():
    _seed_in_progress('busy', expired=False)
    with pytest.raises(InProgress):
        run('busy')
    assert effect_count() == 0


# --- 고착 복구: 만료 재클레임 + fenced 완료 마킹 (FR-005) ---


def test_expired_in_progress_is_reclaimed():
    _seed_in_progress('stuck', expired=True)
    r = run('stuck', op=make_op('RECLAIMED'))
    assert r == 'RECLAIMED'
    assert effect_count() == 1
    rec = IdempotencyRecord.objects.get(key='stuck')
    assert rec.status == IdempotencyStatus.COMPLETED.value


def test_stale_claim_completion_rolls_back_effect():
    """재클레임된 뒤 이전 claim의 완료 마킹은 0행 → LostClaimError → 전체 롤백.

    operation 내부에서 claim_token을 가로채(만료 스위퍼의 재클레임 모사) ②의
    완료 UPDATE를 stale하게 만든다. 효과는 롤백되어 커밋 최대 1회를 지킨다.
    """

    def preempting_op():
        # 만료 스위퍼가 이 레코드를 새 token으로 재클레임했다고 모사
        IdempotencyRecord._writer.filter(
            key='preempt', status=IdempotencyStatus.IN_PROGRESS.value
        ).update(claim_token=uuid.uuid4())
        with connection.cursor() as c:
            c.execute(f"INSERT INTO {EFFECT_TABLE}(tag) VALUES ('preempt')")
        return 'SHOULD_ROLL_BACK'

    with pytest.raises(LostClaimError):
        run('preempt', op=preempting_op)
    assert effect_count() == 0  # 효과 롤백 — 커밋 최대 1회


# --- 확정 실패 tombstone (US3 #5, K-8·9) ---


def test_operation_failure_creates_definite_failure_tombstone():
    def boom():
        with connection.cursor() as c:
            c.execute(f"INSERT INTO {EFFECT_TABLE}(tag) VALUES ('boom')")
        raise RuntimeError('operation failed')

    with pytest.raises(RuntimeError, match='operation failed'):
        run('fail', op=boom)
    assert effect_count() == 0  # ②가 원자 → 효과 없음
    rec = IdempotencyRecord.objects.get(key='fail')
    assert rec.status == IdempotencyStatus.DEFINITE_FAILURE.value


def test_definite_failure_same_fingerprint_reclaims_other_rejected():
    def boom():
        raise RuntimeError('x')

    with pytest.raises(RuntimeError):
        run('df', request={'a': 1}, op=boom)
    # 다른 지문 → tombstone 지문 보존이 거부(BR-4)
    with pytest.raises(IdempotencyConflict):
        run('df', request={'a': 99}, op=make_op('R'))
    # 같은 지문 → 원자적 재클레임(결과 캐시 반환 없음)
    r = run('df', request={'a': 1}, op=make_op('RETRIED'))
    assert r == 'RETRIED'
    assert effect_count() == 1


# --- COMPLETED 불변 (K-9) ---


def test_completed_is_immutable_against_mark_unknown():
    run('done', op=make_op('R'))
    rec = IdempotencyRecord.objects.get(key='done')
    with pytest.raises(LostClaimError):
        mark_unknown('ns', 's', 'done', uuid.uuid4(), 'evidence:x')
    rec.refresh_from_db()
    assert rec.status == IdempotencyStatus.COMPLETED.value


# --- UNKNOWN 해소 흐름 (US3 #7·8) ---


def test_mark_unknown_requires_in_progress_and_claim_token():
    seeded = _seed_in_progress('unk', expired=False)
    # 틀린 token → 거부
    with pytest.raises(LostClaimError):
        mark_unknown('ns', 's', 'unk', uuid.uuid4(), 'evidence:req')
    # 올바른 token → UNKNOWN 전이
    mark_unknown('ns', 's', 'unk', seeded.claim_token, 'evidence:req')
    seeded.refresh_from_db()
    assert seeded.status == IdempotencyStatus.UNKNOWN.value
    assert seeded.unknown_evidence_ref == 'evidence:req'


def test_resolve_unknown_as_completed_returns_result_on_retry():
    seeded = _seed_in_progress('unk2', expired=False, request={'a': 1})
    mark_unknown('ns', 's', 'unk2', seeded.claim_token, 'evidence:req')
    resolve_unknown_as_completed('ns', 's', 'unk2', {'ok': True}, 'evidence:recovered')
    r = run('unk2', request={'a': 1}, op=make_op('SHOULD_NOT_RUN'))
    assert r == {'ok': True}
    assert effect_count() == 0  # 재실행 없음


def test_resolve_unknown_as_definite_failure_reexecutes_same_fingerprint():
    seeded = _seed_in_progress('unk3', expired=False, request={'a': 1})
    mark_unknown('ns', 's', 'unk3', seeded.claim_token, 'evidence:req')
    resolve_unknown_as_definite_failure('ns', 's', 'unk3', 'evidence:no-effect')
    r = run('unk3', request={'a': 1}, op=make_op('RERUN'))
    assert r == 'RERUN'
    assert effect_count() == 1


def test_resolve_requires_unknown_state():
    _seed_in_progress('unk4', expired=False)
    with pytest.raises(LostClaimError):
        resolve_unknown_as_completed('ns', 's', 'unk4', {'x': 1}, 'evidence:y')


def test_unknown_signal_on_retry():
    seeded = _seed_in_progress('unk5', expired=False)
    mark_unknown('ns', 's', 'unk5', seeded.claim_token, 'evidence:req')
    with pytest.raises(UnknownOutcome):
        run('unk5')


# --- 공개 ORM 조회 전용 (K-9, FR-005) ---


def test_public_manager_is_read_only():
    run('ro', op=make_op('R'))
    rec = IdempotencyRecord.objects.get(key='ro')
    with pytest.raises(IdempotencyWriteError):
        IdempotencyRecord.objects.create(namespace='x', scope='y', key='z')
    with pytest.raises(IdempotencyWriteError):
        IdempotencyRecord.objects.filter(key='ro').update(status='UNKNOWN')
    with pytest.raises(IdempotencyWriteError):
        IdempotencyRecord.objects.filter(key='ro').delete()
    with pytest.raises(IdempotencyWriteError):
        rec.save()
    with pytest.raises(IdempotencyWriteError):
        rec.delete()


# --- 상태별 DB CheckConstraint ---


def test_check_constraint_rejects_completed_without_result():
    """COMPLETED인데 result·completed_at 누락 → DB 거부."""
    bad = IdempotencyRecord(
        namespace='ns',
        scope='s',
        key='badcompleted',
        fingerprint='f' * 64,
        fingerprint_version=1,
        status=IdempotencyStatus.COMPLETED.value,
        claimed_at=timezone.now(),
        correlation_id=uuid.uuid4(),
        # result·completed_at 누락
    )
    with pytest.raises(IntegrityError):
        IdempotencyRecord._writer.bulk_create([bad])


# --- canonicalizer 주입 (BR-4) ---


def test_canonicalizer_injection():
    """네임스페이스 canonicalizer가 논리적으로 같은 입력을 같은 지문으로 정규화."""

    def canon(req):
        # 순서 무관 정규화: 키 정렬 + 값 정규화
        return canonical_json({k: req[k] for k in sorted(req)})

    run('canon', request={'a': 1, 'b': 2}, canonicalize=canon, op=make_op('R'))
    r = run('canon', request={'b': 2, 'a': 1}, canonicalize=canon, op=make_op('R2'))
    assert r == 'R'  # 같은 지문 → 캐시 결과
    assert effect_count() == 1


# --- 모델 앱 레지스트리 등록 ---


def test_record_registered_in_app_registry():
    from django.apps import apps

    models = {m.__name__ for m in apps.get_app_config('shared_kernel').get_models()}
    assert 'IdempotencyRecord' in models


# --- 적대 리뷰 반영: 결과 타입 안정성·JSON 강제·입력 검증 ---


def test_result_type_stable_across_first_and_retry():
    """첫 호출과 재시도가 동일 타입을 반환한다(JSON 정규화 — tuple→list)."""

    def op():
        with connection.cursor() as c:
            c.execute(f"INSERT INTO {EFFECT_TABLE}(tag) VALUES ('rt')")
        return ('ok', 1)

    first = run('rt', op=op)
    second = run('rt', op=op)
    assert first == second == ['ok', 1]
    assert effect_count() == 1


def test_non_json_result_rejected():
    with pytest.raises(TypeError):
        run('nonjson', op=lambda: {1, 2, 3})


def test_empty_identifiers_rejected():
    with pytest.raises(ValueError):
        run('')  # 빈 key
    with pytest.raises(ValueError):
        run('k', scope='')  # 빈 scope → 벤더 격리 사고 방지
    with pytest.raises(ValueError):
        run('k', namespace='')


def test_nonpositive_ttl_rejected():
    with pytest.raises(ValueError):
        run('ttl0', in_progress_ttl=0)


def test_nonpositive_version_rejected():
    with pytest.raises(ValueError):
        run_idempotent('ns', 's', 'ver0', {'a': 1}, make_op('R'), fingerprint_version=0)


def test_transition_apis_require_evidence():
    seeded = _seed_in_progress('ev', expired=False)
    with pytest.raises(ValueError):
        mark_unknown('ns', 's', 'ev', seeded.claim_token, '')
    mark_unknown('ns', 's', 'ev', seeded.claim_token, 'evidence:x')
    with pytest.raises(ValueError):
        resolve_unknown_as_completed('ns', 's', 'ev', {'r': 1}, '')
    with pytest.raises(ValueError):
        resolve_unknown_as_definite_failure('ns', 's', 'ev', '')
