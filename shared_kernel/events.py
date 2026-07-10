"""도메인 이벤트 primitive — 확장 봉투 + 발행/디스패치 분리(원칙 XII·XIII, FR-003·004).

봉투는 불변이고 payload는 방어 복사 후 재귀 불변화한다(원본·핸들러가 발행 사실을
바꿀 수 없음). 발행(`publish`)은 현재 디스패처(contextvar, `use_dispatcher`로 교체)
에 위임하며 — 발행 코드를 바꾸지 않고 아웃박스 디스패처로 이행할 수 있게 한다(BR-3).
구독 레지스트리는 디스패처 **인스턴스**가 소유해 테스트 간 전역 누출이 없다.
시각·식별자는 시스템이 부여한다(호출자 backdate 불가 — K-13).
"""

import enum
import uuid
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from django.utils import timezone

from .correlation import get_correlation_id


class HandlerRegistrationError(Exception):
    """부수 효과 등급 위반 등 잘못된 핸들러 등록."""


class SideEffect(enum.Enum):
    """핸들러 부수 효과 등급 — 등록 시 선언 필수(기본값 없음, FR-004)."""

    INTERNAL = 'INTERNAL'  # 동일 트랜잭션 내 순수 내부 효과
    EXTERNAL = 'EXTERNAL'  # 외부 부수 효과 — 동기 디스패처 등록 거부(P12 아웃박스 소관)


def _freeze(value: object) -> object:
    """JSON-like 값을 재귀 불변화 + 검증한다(방어 복사 — K-14).

    JSON 트리(mapping[str→값]·list·JSON 스칼라)만 허용하고, set·bytes·임의 객체·
    비문자열 key는 거부한다 — P12 아웃박스 직렬화의 지연 실패를 발행 시점에 차단한다.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        frozen: dict = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(f'payload 매핑 key는 문자열이어야 한다: {k!r}')
            frozen[k] = _freeze(v)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise ValueError(f'payload는 JSON-like만 허용 — 거부된 타입: {type(value).__name__}')


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """확장 이벤트 봉투 — 불변. 시각·식별자는 시스템 부여."""

    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload_version: int
    payload: Mapping
    correlation_id: uuid.UUID
    occurred_at: datetime
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    causation_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        """모든 생성 경로(publish·직접 생성)에서 필수 필드·payload JSON 계약을 강제한다."""
        for name in ('event_type', 'aggregate_type', 'aggregate_id'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{name} 필수(비어 있지 않은 문자열)')
        if isinstance(self.payload_version, bool) or not isinstance(self.payload_version, int):
            raise ValueError('payload_version은 int 필수')
        if not isinstance(self.payload, Mapping):
            raise ValueError('payload는 JSON 객체(mapping)여야 한다')
        object.__setattr__(self, 'payload', _freeze(self.payload))


@runtime_checkable
class Dispatcher(Protocol):
    """디스패치 계약 — dispatch만 요구(대체 구현에 구독 능력 강요 안 함)."""

    def dispatch(self, envelope: EventEnvelope) -> None: ...


class SyncDispatcher:
    """동기 디스패처 — 구독 레지스트리를 인스턴스로 소유. EXTERNAL 등록 거부."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[EventEnvelope], None]]] = {}

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[EventEnvelope], None],
        *,
        side_effect: SideEffect,
    ) -> None:
        if not isinstance(side_effect, SideEffect):
            raise HandlerRegistrationError('side_effect 등급은 SideEffect여야 한다')
        if side_effect is SideEffect.EXTERNAL:
            raise HandlerRegistrationError(
                'EXTERNAL 등급 핸들러는 동기 디스패처에 등록할 수 없다(FR-004)'
            )
        handlers = self._handlers.setdefault(event_type, [])
        if handler in handlers:
            raise HandlerRegistrationError(
                f'중복 구독 — 같은 (event_type={event_type!r}, handler)는 한 번만 등록한다'
            )
        handlers.append(handler)

    def dispatch(self, envelope: EventEnvelope) -> None:
        for handler in self._handlers.get(envelope.event_type, []):
            handler(envelope)  # 예외는 전파(조용한 유실 금지)


_default_dispatcher = SyncDispatcher()
_current_dispatcher: ContextVar[Dispatcher] = ContextVar(
    'current_dispatcher', default=_default_dispatcher
)


@contextmanager
def use_dispatcher(dispatcher: Dispatcher):
    """현재 발행 디스패처를 교체한다 — 발행 코드 불변 + 테스트 격리."""
    token = _current_dispatcher.set(dispatcher)
    try:
        yield dispatcher
    finally:
        _current_dispatcher.reset(token)


def subscribe(
    event_type: str,
    handler: Callable[[EventEnvelope], None],
    *,
    side_effect: SideEffect,
    dispatcher: SyncDispatcher | None = None,
) -> None:
    """핸들러를 등록한다 — 등록 대상 dispatcher 명시(생략 시 기본 SyncDispatcher).

    등급(side_effect) 선언은 필수다(기본값 없음 — 누락 시 TypeError).
    """
    target = dispatcher if dispatcher is not None else _default_dispatcher
    target.subscribe(event_type, handler, side_effect=side_effect)


def publish(
    event_type: str,
    *,
    aggregate_type: str,
    aggregate_id: str,
    payload_version: int,
    payload: Mapping | None = None,
    causation_id: uuid.UUID | None = None,
) -> EventEnvelope:
    """봉투를 만들어 현재 디스패처로 발행한다.

    event_id·occurred_at·correlation_id는 시스템이 부여한다 — 호출자는 지정할 수
    없다(K-13). 필수 필드·payload JSON 계약 검증과 재귀 불변화는 EventEnvelope가
    수행한다(K-5·K-14, SC-003).
    """
    envelope = EventEnvelope(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload_version=payload_version,
        payload=payload if payload is not None else {},
        correlation_id=get_correlation_id(),
        occurred_at=timezone.now(),
        causation_id=causation_id,
    )
    _current_dispatcher.get().dispatch(envelope)
    return envelope
