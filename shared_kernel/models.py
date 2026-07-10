"""shared_kernel 모델 애그리게이터.

Django는 `<app>.models` 경로만 자동 탐색하므로, 커널의 영속 모델은 각자의
모듈(idempotency·audit)에 정의하고 여기서 import해 앱 레지스트리에 등록한다.
이 파일이 앱 로딩 시점의 유일한 ORM import 경로다 — 패키지 `__init__.py`는
ORM 심볼을 eager import하지 않는다(앱 로딩 순서 안전, BLOCKER 반영). 공개
표면 re-export는 `__init__.py`의 PEP 562 지연 전략(T070)이 담당한다.

T040(IdempotencyRecord)·T051(AuditFact)이 아래에 import를 추가한다.
"""

from .audit import AuditFact
from .idempotency import IdempotencyRecord

__all__ = ['AuditFact', 'IdempotencyRecord']
