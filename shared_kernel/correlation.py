"""상관관계 컨텍스트 — 관통 추적 primitive(FR-010, R6).

멱등 기록·감사 사실·이벤트 봉투가 기록 시점에 여기서 correlation_id를 읽어
하나의 요청 흐름을 관통 추적한다(SC-007). `contextvars` 기반이라 동시 흐름 간
누출이 없고 async task에는 자동 전파되지만 **새 스레드는 상속하지 않는다** —
스레드 핸드오프가 필요하면 `contextvars.copy_context()`가 명시 규약이다.
"""

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

_correlation_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    'correlation_id', default=None
)


def get_correlation_id() -> uuid.UUID:
    """현재 흐름의 correlation_id를 반환한다.

    미설정 시 시스템이 발급(uuid4)해 그 흐름에 고정한다 — 이후 접근은 같은 값을
    돌려준다(FR-010).
    """
    cid = _correlation_id.get()
    if cid is None:
        cid = uuid.uuid4()
        _correlation_id.set(cid)
    return cid


def bind_correlation_id(value: uuid.UUID) -> contextvars.Token:
    """요청 경계에서 correlation_id를 명시적으로 바인딩하고 reset token을 반환한다."""
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token) -> None:
    """`bind_correlation_id`가 반환한 token으로 이전 상태를 복원한다(요청 경계 종료)."""
    _correlation_id.reset(token)


@contextmanager
def correlation_context(value: uuid.UUID | None = None) -> Iterator[uuid.UUID]:
    """요청/테스트 경계용 context manager.

    `value`가 주어지면 그 값을, 없으면 신선한 스코프를 연다(스코프 내 첫 접근이
    새 id를 발급). 종료 시 진입 이전 상태로 복원해 흐름 간 누출을 막는다.
    """
    token = _correlation_id.set(value)
    try:
        yield get_correlation_id()
    finally:
        _correlation_id.reset(token)
