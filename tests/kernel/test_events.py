"""도메인 이벤트 계약(US2 #1~5, FR-003·004, K-5·6·13·14).

확장 봉투 강제 + 발행/디스패치 분리 + 부수 효과 등급 선언. DB 불필요 —
correlation은 Phase 2 산출을 컨텍스트에서 읽는다.
"""

import uuid
from datetime import datetime

import pytest

from shared_kernel.correlation import correlation_context
from shared_kernel.events import (
    EventEnvelope,
    HandlerRegistrationError,
    SideEffect,
    SyncDispatcher,
    publish,
    subscribe,
    use_dispatcher,
)


def publish_kwargs(**over):
    base = {
        'event_type': 'kernel.ProbeRecorded',
        'aggregate_type': 'kernel.Probe',
        'aggregate_id': 'probe-1',
        'payload_version': 1,
        'payload': {'amount': 100, 'tags': ['a', 'b'], 'nested': {'k': 'v'}},
    }
    base.update(over)
    return base


# --- 완전한 봉투 발행·수신 (US2 #1) ---


def test_full_envelope_published_and_received():
    disp = SyncDispatcher()
    received: list[EventEnvelope] = []
    subscribe(
        'kernel.ProbeRecorded',
        received.append,
        side_effect=SideEffect.INTERNAL,
        dispatcher=disp,
    )
    with use_dispatcher(disp), correlation_context() as cid:
        env = publish(**publish_kwargs())

    assert len(received) == 1
    e = received[0]
    assert e is env
    assert isinstance(e.event_id, uuid.UUID)
    assert e.event_type == 'kernel.ProbeRecorded'
    assert isinstance(e.occurred_at, datetime) and e.occurred_at.tzinfo is not None
    assert e.aggregate_type == 'kernel.Probe'
    assert e.aggregate_id == 'probe-1'
    assert e.payload_version == 1
    assert e.correlation_id == cid
    assert e.causation_id is None
    assert e.payload['amount'] == 100


def test_causation_id_optional_and_carried():
    disp = SyncDispatcher()
    cause = uuid.uuid4()
    with use_dispatcher(disp):
        env = publish(**publish_kwargs(causation_id=cause))
    assert env.causation_id == cause


# --- payload 재귀 불변성 (K-14, FR-003) ---


def test_payload_is_defensively_copied_from_source():
    disp = SyncDispatcher()
    src = {'amount': 100, 'items': [1, 2]}
    with use_dispatcher(disp):
        env = publish(**publish_kwargs(payload=src))
    src['amount'] = 999
    src['items'].append(3)
    assert env.payload['amount'] == 100
    assert list(env.payload['items']) == [1, 2]


def test_handler_cannot_mutate_nested_payload():
    disp = SyncDispatcher()
    with use_dispatcher(disp):
        env = publish(**publish_kwargs())
    with pytest.raises(TypeError):
        env.payload['nested']['k'] = 'x'  # 재귀 불변 매핑
    with pytest.raises(AttributeError):
        env.payload['tags'].append('c')  # 리스트 → 튜플


# --- 필수 필드 누락 거부 (K-5, SC-003) ---


def test_missing_required_field_rejected():
    disp = SyncDispatcher()
    with use_dispatcher(disp):
        with pytest.raises((ValueError, TypeError)):
            publish(**publish_kwargs(event_type=''))
        with pytest.raises((ValueError, TypeError)):
            publish(**publish_kwargs(aggregate_id=None))


# --- backdate 거부 (K-13) ---


def test_caller_supplied_occurred_at_rejected():
    disp = SyncDispatcher()
    with use_dispatcher(disp):
        with pytest.raises(TypeError):
            publish(occurred_at='2020-01-01T00:00:00Z', **publish_kwargs())


def test_caller_supplied_event_id_rejected():
    disp = SyncDispatcher()
    with use_dispatcher(disp):
        with pytest.raises(TypeError):
            publish(event_id=uuid.uuid4(), **publish_kwargs())


# --- 복수 핸들러 + 예외 전파 (US2 #3) ---


def test_multiple_handlers_run_in_order():
    disp = SyncDispatcher()
    calls: list[str] = []
    subscribe(
        'e.multi', lambda _e: calls.append('h1'), side_effect=SideEffect.INTERNAL, dispatcher=disp
    )
    subscribe(
        'e.multi', lambda _e: calls.append('h2'), side_effect=SideEffect.INTERNAL, dispatcher=disp
    )
    with use_dispatcher(disp):
        publish(**publish_kwargs(event_type='e.multi'))
    assert calls == ['h1', 'h2']


def test_handler_exception_propagates():
    disp = SyncDispatcher()

    def boom(_e):
        raise RuntimeError('handler failed')

    subscribe('e.boom', boom, side_effect=SideEffect.INTERNAL, dispatcher=disp)
    with use_dispatcher(disp):
        with pytest.raises(RuntimeError, match='handler failed'):
            publish(**publish_kwargs(event_type='e.boom'))


# --- 디스패처 교체·격리 (US2 #4) ---


def test_dispatcher_swap_via_use_dispatcher_keeps_publish_code_unchanged():
    """dispatch-only 커스텀 디스패처(subscribe 능력 불요)로 교체 — 발행 코드 불변."""
    received: list[EventEnvelope] = []

    class RecordingDispatcher:
        def dispatch(self, envelope):
            received.append(envelope)

    with use_dispatcher(RecordingDispatcher()):
        env = publish(**publish_kwargs())
    assert received == [env]


def test_subscription_registry_is_instance_owned_no_leak():
    d1, d2 = SyncDispatcher(), SyncDispatcher()
    got1: list = []
    got2: list = []
    subscribe('e.iso', got1.append, side_effect=SideEffect.INTERNAL, dispatcher=d1)
    subscribe('e.iso', got2.append, side_effect=SideEffect.INTERNAL, dispatcher=d2)
    with use_dispatcher(d1):
        publish(**publish_kwargs(event_type='e.iso'))
    assert len(got1) == 1
    assert got2 == []  # 인스턴스 소유 레지스트리 → 전역 누출 없음


def test_default_dispatcher_used_when_omitted():
    got: list = []
    subscribe('e.default-omit', got.append, side_effect=SideEffect.INTERNAL)  # dispatcher 생략
    publish(**publish_kwargs(event_type='e.default-omit'))  # use_dispatcher 없음 → 기본
    assert len(got) == 1


# --- 부수 효과 등급 (K-6, US2 #5) ---


def test_missing_side_effect_grade_rejected():
    with pytest.raises(TypeError):
        subscribe('e.grade', lambda _e: None, dispatcher=SyncDispatcher())  # side_effect 누락


def test_external_side_effect_sync_registration_rejected():
    with pytest.raises(HandlerRegistrationError):
        subscribe(
            'e.external',
            lambda _e: None,
            side_effect=SideEffect.EXTERNAL,
            dispatcher=SyncDispatcher(),
        )


# --- 적대 리뷰 반영: payload JSON 엄격화·직접 생성 검증·중복 구독 ---


def test_string_payload_rejected():
    with use_dispatcher(SyncDispatcher()), pytest.raises(ValueError):
        publish(**publish_kwargs(payload='not-a-map'))


def test_set_payload_value_rejected():
    with use_dispatcher(SyncDispatcher()), pytest.raises(ValueError):
        publish(**publish_kwargs(payload={'tags': {1, 2}}))


def test_non_string_payload_key_rejected():
    with use_dispatcher(SyncDispatcher()), pytest.raises(ValueError):
        publish(**publish_kwargs(payload={1: 'x'}))


def test_duplicate_subscription_rejected():
    disp = SyncDispatcher()

    def handler(_e):
        pass

    subscribe('e.dup', handler, side_effect=SideEffect.INTERNAL, dispatcher=disp)
    with pytest.raises(HandlerRegistrationError):
        subscribe('e.dup', handler, side_effect=SideEffect.INTERNAL, dispatcher=disp)


def test_direct_envelope_construction_validates_and_freezes():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    # 직접 생성도 필수 필드 검증(빈 event_type 거부)
    with pytest.raises(ValueError):
        EventEnvelope(
            event_type='',
            aggregate_type='a',
            aggregate_id='1',
            payload_version=1,
            payload={},
            correlation_id=uuid.uuid4(),
            occurred_at=now,
        )
    # 직접 생성도 payload 재귀 불변화
    env = EventEnvelope(
        event_type='e',
        aggregate_type='a',
        aggregate_id='1',
        payload_version=1,
        payload={'k': {'n': 1}},
        correlation_id=uuid.uuid4(),
        occurred_at=now,
    )
    with pytest.raises(TypeError):
        env.payload['k']['n'] = 2
