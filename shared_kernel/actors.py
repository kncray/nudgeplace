"""행위자 역할 어휘(FR-007) — 감사 사실의 행위자 표현.

실제 벤더 범위 인가 강제는 도메인 계층(P1)의 몫이며, 커널은 역할 어휘와
행위자 값 객체만 제공한다(원칙 VI 부분).
"""

import enum
from dataclasses import dataclass


class ActorRole(enum.Enum):
    OPERATOR = 'OPERATOR'  # 플랫폼 운영자
    VENDOR = 'VENDOR'  # 벤더
    CUSTOMER = 'CUSTOMER'  # 고객
    SYSTEM = 'SYSTEM'  # 시스템(자동 처리)


@dataclass(frozen=True, slots=True)
class Actor:
    """행위자 — 역할 + 식별자. 불변.

    역할과 비어 있지 않은 식별자를 강제한다 — 익명 행위자는 감사 로그의 목적
    (운영자 환불·벤더 제재·정산 보류의 주체 특정)을 무너뜨린다(FR-006·FR-007).
    """

    role: ActorRole
    actor_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, ActorRole):
            raise ValueError('actor role은 ActorRole이어야 한다')
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValueError('actor_id는 비어 있지 않은 문자열이어야 한다')
