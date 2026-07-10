# 공유 커널 공개 표면(BR-7·FR-008 특성화 대상 — contracts/kernel-public-surface.md).
# 단방향 의존: 도메인(apps.*)→커널만 허용, 커널→도메인 역의존 금지(BR-3).
#
# 순수 심볼(Money·이벤트·correlation·actors)은 eager re-export한다 — 모델을 import하지
# 않으므로 앱 로딩 시점에 안전하다. ORM 의존 심볼(멱등·감사)은 PEP 562 모듈
# `__getattr__`로 **지연(lazy)** re-export한다 — `__init__`이 앱 로딩 시점에 모델을
# eager import하면 AppRegistryNotReady를 유발하기 때문이다(BLOCKER 반영). 모델의
# 유일한 자동 발견 경로는 `shared_kernel/models.py` 애그리게이터다.

from .actors import Actor, ActorRole
from .correlation import (
    bind_correlation_id,
    correlation_context,
    get_correlation_id,
    reset_correlation_id,
)
from .events import (
    Dispatcher,
    EventEnvelope,
    HandlerRegistrationError,
    SideEffect,
    SyncDispatcher,
    publish,
    subscribe,
    use_dispatcher,
)
from .money import Currency, Money, RemainderPolicy, RoundingPolicy

# ORM 의존 심볼 — 지연 re-export 대상(이름 → (모듈, 속성)).
_LAZY = {
    'AuditFact': ('audit', 'AuditFact'),
    'record_audit_fact': ('audit', 'record_audit_fact'),
    'IdempotencyRecord': ('idempotency', 'IdempotencyRecord'),
    'IdempotencyStatus': ('idempotency', 'IdempotencyStatus'),
    'IdempotencyConflict': ('idempotency', 'IdempotencyConflict'),
    'InProgress': ('idempotency', 'InProgress'),
    'UnknownOutcome': ('idempotency', 'UnknownOutcome'),
    'LostClaimError': ('idempotency', 'LostClaimError'),
    'run_idempotent': ('idempotency', 'run_idempotent'),
    'canonical_json': ('idempotency', 'canonical_json'),
    'mark_unknown': ('idempotency', 'mark_unknown'),
    'resolve_unknown_as_completed': ('idempotency', 'resolve_unknown_as_completed'),
    'resolve_unknown_as_definite_failure': ('idempotency', 'resolve_unknown_as_definite_failure'),
}

__all__ = [
    'Actor',
    'ActorRole',
    'AuditFact',
    'Currency',
    'Dispatcher',
    'EventEnvelope',
    'HandlerRegistrationError',
    'IdempotencyConflict',
    'IdempotencyRecord',
    'IdempotencyStatus',
    'InProgress',
    'LostClaimError',
    'Money',
    'RemainderPolicy',
    'RoundingPolicy',
    'SideEffect',
    'SyncDispatcher',
    'UnknownOutcome',
    'bind_correlation_id',
    'canonical_json',
    'correlation_context',
    'get_correlation_id',
    'mark_unknown',
    'publish',
    'record_audit_fact',
    'reset_correlation_id',
    'resolve_unknown_as_completed',
    'resolve_unknown_as_definite_failure',
    'run_idempotent',
    'subscribe',
    'use_dispatcher',
]


def __getattr__(name: str):
    """PEP 562 지연 re-export — ORM 의존 심볼을 접근 시점에 import한다."""
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    import importlib

    module = importlib.import_module(f'.{target[0]}', __name__)
    return getattr(module, target[1])


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))
