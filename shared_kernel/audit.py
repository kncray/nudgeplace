"""불변 감사 사실 primitive(원칙 XV-감사, FR-006).

"왜 이 값이 지금 이 값인지"를 답하는 append-only 사실 기록. 2층으로 불변을
강제한다 — (1) 모델 계층: 공개 `objects`는 조회 전용, 삽입은 `record_audit_fact`의
내부 경로만, (2) DB 계층: 0002_audit의 트리거가 UPDATE·DELETE를 거부(raw SQL
봉쇄 — SC-005의 "100% 거부"를 문자 그대로 충족, R5). 기록은 호출자의 열린
트랜잭션에 참여한다 — 상태 변경과 감사 기록이 함께 커밋되거나 함께 롤백된다.
시각은 시스템이 부여한다(backdate 불가 — K-13).
"""

from django.db import connection, models
from django.utils import timezone

from .actors import Actor
from .correlation import get_correlation_id


class AuditError(Exception):
    """감사 기록 계약 위반(원자성 등)."""


class AuditWriteError(AuditError):
    """공개 조회 전용 경로를 통한 직접 쓰기 시도."""


class _ReadOnlyQuerySet(models.QuerySet):
    def _blocked(self, *args, **kwargs):
        raise AuditWriteError(
            'AuditFact는 append-only·조회 전용 — 삽입은 record_audit_fact만, 수정·삭제 불가'
        )

    create = _blocked
    bulk_create = _blocked
    get_or_create = _blocked
    update_or_create = _blocked
    update = _blocked
    bulk_update = _blocked
    delete = _blocked


class AuditFact(models.Model):
    """감사 사실 — append-only 인프라 기록(BR-6). 공개 `objects`는 조회 전용."""

    actor_role = models.CharField(max_length=20)
    actor_id = models.CharField(max_length=255)
    target_type = models.CharField(max_length=255)
    target_id = models.CharField(max_length=255)
    reason_text = models.TextField()
    reason_code = models.CharField(max_length=100, null=True, blank=True, default=None)  # noqa: DJ001
    evidence_ref = models.CharField(max_length=255)
    correlation_id = models.UUIDField()
    recorded_at = models.DateTimeField()

    objects = models.Manager.from_queryset(_ReadOnlyQuerySet)()  # noqa: DJ012
    _writer = models.Manager()  # noqa: DJ012

    class Meta:
        app_label = 'shared_kernel'
        # 관통 추적 조회(사고 조사)와 대상 기준 조회의 전체 스캔 방지.
        indexes = [
            models.Index(fields=['correlation_id']),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self) -> str:
        return f'AuditFact({self.actor_role}:{self.actor_id} → {self.target_type}:{self.target_id})'

    def save(self, *args, **kwargs):
        raise AuditWriteError('직접 save 금지 — record_audit_fact 내부 경로만 삽입 허용')

    def delete(self, *args, **kwargs):
        raise AuditWriteError('직접 delete 금지 — 감사 사실은 append-only')


def _require(value: object, name: str) -> None:
    if not value:
        raise ValueError(f'감사 필수 필드 누락: {name}')


def record_audit_fact(
    actor: Actor,
    target_type: str,
    target_id: str,
    reason_text: str,
    evidence_ref: str,
    *,
    reason_code: str | None = None,
) -> None:
    """감사 사실을 기록한다 — 호출자의 열린 트랜잭션에 참여(FR-006).

    ORM 호출 **전에** autocommit(열린 atomic 없음)을 거부한다 — get_or_create처럼
    ORM이 자체 atomic을 여는 우회를 차단한다. recorded_at·correlation은 시스템 부여.
    """
    if not connection.in_atomic_block:
        raise AuditError(
            'record_audit_fact는 열린 트랜잭션 안에서 호출해야 한다(원자 기록 — FR-006)'
        )
    if not isinstance(actor, Actor):
        raise ValueError('행위자(Actor) 필수')
    _require(target_type, 'target_type')
    _require(target_id, 'target_id')
    _require(reason_text, 'reason_text')
    _require(evidence_ref, 'evidence_ref')

    AuditFact._writer.bulk_create(
        [
            AuditFact(
                actor_role=actor.role.value,
                actor_id=actor.actor_id,
                target_type=target_type,
                target_id=target_id,
                reason_text=reason_text,
                reason_code=reason_code,
                evidence_ref=evidence_ref,
                correlation_id=get_correlation_id(),
                recorded_at=timezone.now(),
            )
        ]
    )
