"""멱등 실행 primitive — DB 유니크 기반 2단계 클레임 + claim token fencing.

contracts/idempotency-protocol.md의 구현. 스코프 멱등키 `(namespace, scope, key)`를
DB 유니크로 직렬화하고, ① 짧은 클레임 트랜잭션(독립 커밋) → ② 비즈니스 트랜잭션
(효과 + 완료 마킹 원자)으로 나눈다. 만료 재클레임은 새 claim_token으로 fencing해
이전 실행의 완료 마킹을 0행으로 만들고, 그 실행의 비즈니스 트랜잭션을 롤백시켜
커밋 효과를 최대 1회로 제한한다. 확정 실패는 삭제가 아니라 지문 보존 tombstone
(DEFINITE_FAILURE)이며 COMPLETED는 종결·불변이다.

`run_idempotent`은 트랜잭션 경계를 소유한다 — 이미 열린 외부 atomic 안에서
호출하면 ①의 독립 커밋이 불가능하므로 실행 전에 거부한다.
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from django.db import connection, models, transaction
from django.db.transaction import TransactionManagementError
from django.db.utils import IntegrityError
from django.utils import timezone

from .correlation import get_correlation_id


class IdempotencyWriteError(Exception):
    """공개 조회 전용 매니저·인스턴스를 통한 직접 쓰기 시도."""


class IdempotencyConflict(Exception):
    """같은 키에 (fingerprint_version, fingerprint) 쌍이 불일치 — 다른 요청(실행 없음)."""


class InProgress(Exception):
    """다른 실행이 진행 중(미만료) — 이중 실행 없음, 대기 강제 없음."""


class UnknownOutcome(Exception):
    """효과 여부 미상(UNKNOWN) — 자동 재실행 금지, 근거 있는 해소 필요(P6+)."""


class LostClaimError(Exception):
    """claim이 stale — 완료 마킹/전이가 0행. 비즈니스 트랜잭션 전체 롤백을 유발."""


class IdempotencyStatus(models.TextChoices):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    UNKNOWN = 'UNKNOWN'
    DEFINITE_FAILURE = 'DEFINITE_FAILURE'


def canonical_json(obj: object) -> str:
    """기본 canonicalizer — 키 정렬 직렬화. 논리 동치의 표기 정규화는 네임스페이스 몫(BR-4)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _fingerprint(request: object, canonicalize: Callable[[object], str]) -> str:
    return hashlib.sha256(canonicalize(request).encode('utf-8')).hexdigest()


def _wrap(value: object) -> dict:
    """result를 JSON 객체로 감싼다 — None 결과도 SQL NULL과 구분(CheckConstraint 정합)."""
    return {'value': value}


def _unwrap(stored: dict) -> object:
    return stored['value']


def _normalize(value: object) -> object:
    """JSON 왕복으로 정규화 — 최초 실행과 재시도가 **동일 타입**을 반환하도록(HIGH-2).

    tuple→list처럼 JSON 표현으로 통일하고, JSON 직렬화 불가한 결과(set·UUID·객체 등)는
    거부한다(주문 응답 계약과 직결 — 재시도가 다른 값을 돌려주는 결함 방지).
    """
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError) as exc:
        raise TypeError(f'멱등 결과는 JSON 직렬화 가능해야 한다: {exc}') from exc


def _require_nonempty(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'멱등 필수 문자열이 비었거나 문자열이 아님: {name}')


class _ReadOnlyQuerySet(models.QuerySet):
    def _blocked(self, *args, **kwargs):
        raise IdempotencyWriteError(
            'IdempotencyRecord 공개 매니저는 조회 전용 — 쓰기는 내부 전이 경로만 허용'
        )

    create = _blocked
    bulk_create = _blocked
    get_or_create = _blocked
    update_or_create = _blocked
    update = _blocked
    bulk_update = _blocked
    delete = _blocked


class IdempotencyRecord(models.Model):
    """멱등 실행 기록 — 인프라 기록(BR-6). 공개 `objects`는 조회 전용."""

    namespace = models.CharField(max_length=255)
    scope = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    fingerprint = models.CharField(max_length=64)
    fingerprint_version = models.IntegerField()
    status = models.CharField(max_length=20, choices=IdempotencyStatus.choices)
    result = models.JSONField(null=True, blank=True, default=None)
    correlation_id = models.UUIDField()
    claim_token = models.UUIDField(null=True, blank=True, default=None)
    claimed_at = models.DateTimeField()
    in_progress_expires_at = models.DateTimeField(null=True, blank=True, default=None)
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    unknown_marked_at = models.DateTimeField(null=True, blank=True, default=None)
    # 근거 필드는 상태별 필수 여부를 CheckConstraint가 NULL 여부로 구분하므로 null=True가
    # 필요하다(빈 문자열 "미설정"과 실제 값을 혼동하지 않기 위함).
    unknown_evidence_ref = models.CharField(max_length=255, null=True, blank=True, default=None)  # noqa: DJ001
    resolved_at = models.DateTimeField(null=True, blank=True, default=None)
    resolution_evidence_ref = models.CharField(max_length=255, null=True, blank=True, default=None)  # noqa: DJ001

    # 이중 매니저: 공개 objects는 조회 전용, _writer는 모듈 내부 전이 전용.
    # DJ012는 from_queryset 매니저를 오분류하므로 억제한다(의도된 패턴).
    objects = models.Manager.from_queryset(_ReadOnlyQuerySet)()  # noqa: DJ012
    _writer = models.Manager()  # noqa: DJ012

    class Meta:
        app_label = 'shared_kernel'
        indexes = [models.Index(fields=['correlation_id'])]  # 관통 추적 조회 전체 스캔 방지
        constraints = [
            models.UniqueConstraint(
                fields=['namespace', 'scope', 'key'], name='idem_uniq_ns_scope_key'
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in IdempotencyStatus]),
                name='idem_status_valid',
            ),
            models.CheckConstraint(
                condition=~models.Q(status=IdempotencyStatus.IN_PROGRESS.value)
                | (
                    models.Q(claim_token__isnull=False)
                    & models.Q(in_progress_expires_at__isnull=False)
                ),
                name='idem_in_progress_fields',
            ),
            models.CheckConstraint(
                condition=~models.Q(status=IdempotencyStatus.COMPLETED.value)
                | (models.Q(result__isnull=False) & models.Q(completed_at__isnull=False)),
                name='idem_completed_fields',
            ),
            models.CheckConstraint(
                condition=~models.Q(status=IdempotencyStatus.UNKNOWN.value)
                | (
                    models.Q(unknown_marked_at__isnull=False)
                    & models.Q(unknown_evidence_ref__isnull=False)
                ),
                name='idem_unknown_fields',
            ),
            models.CheckConstraint(
                condition=~models.Q(status=IdempotencyStatus.DEFINITE_FAILURE.value)
                | (
                    models.Q(resolved_at__isnull=False)
                    & models.Q(resolution_evidence_ref__isnull=False)
                ),
                name='idem_definite_failure_fields',
            ),
        ]

    def __str__(self) -> str:
        return f'IdempotencyRecord({self.namespace}/{self.scope}/{self.key}: {self.status})'

    def save(self, *args, **kwargs):
        raise IdempotencyWriteError('직접 save 금지 — run_idempotent 등 내부 전이 경로만 허용')

    def delete(self, *args, **kwargs):
        raise IdempotencyWriteError('직접 delete 금지 — 멱등 기록은 삭제하지 않는다')


def run_idempotent(
    namespace: str,
    scope: str,
    key: str,
    request: object,
    operation: Callable[[], object],
    *,
    fingerprint_version: int,
    canonicalize: Callable[[object], str] = canonical_json,
    in_progress_ttl: float = 60,
    now: Callable[[], datetime] = timezone.now,
) -> object:
    """멱등 실행 — 재시도해도 커밋 효과는 최대 1회.

    이 스펙 범위의 operation은 **순수 내부(트랜잭션 내 효과)**여야 한다 — 외부
    부수 효과는 ②의 롤백이 되돌리지 못해 "확정 실패=무효과 보장"이 깨진다(P6+ 확장).
    """
    _require_nonempty(namespace, 'namespace')
    _require_nonempty(scope, 'scope')  # 빈 scope는 벤더 간 멱등 영역 충돌을 유발(원칙 VI)
    _require_nonempty(key, 'key')
    if (
        isinstance(fingerprint_version, bool)
        or not isinstance(fingerprint_version, int)
        or fingerprint_version < 1
    ):
        raise ValueError('fingerprint_version은 1 이상의 정수여야 한다')
    if in_progress_ttl <= 0:
        raise ValueError('in_progress_ttl은 0보다 커야 한다')
    if connection.in_atomic_block:
        raise TransactionManagementError(
            'run_idempotent는 외부 atomic 안에서 호출할 수 없다 — ①의 독립 커밋 보장'
        )

    fingerprint = _fingerprint(request, canonicalize)
    claim_token = uuid.uuid4()
    claimed_at = now()
    expires_at = claimed_at + timedelta(seconds=in_progress_ttl)

    record = IdempotencyRecord(
        namespace=namespace,
        scope=scope,
        key=key,
        fingerprint=fingerprint,
        fingerprint_version=fingerprint_version,
        status=IdempotencyStatus.IN_PROGRESS.value,
        claim_token=claim_token,
        claimed_at=claimed_at,
        in_progress_expires_at=expires_at,
        correlation_id=get_correlation_id(),
    )

    # ① 클레임 트랜잭션(독립 커밋)
    try:
        with transaction.atomic():
            IdempotencyRecord._writer.bulk_create([record])
    except IntegrityError:
        outcome = _resolve_existing(
            namespace, scope, key, fingerprint, fingerprint_version, claimed_at, expires_at, now
        )
        if outcome[0] == 'cached':
            return outcome[1]
        record_pk, claim_token = outcome[1], outcome[2]
    else:
        record_pk = record.pk

    # ② 비즈니스 트랜잭션(효과 + 완료 마킹 원자)
    return _execute(record_pk, claim_token, operation, now)


def _resolve_existing(
    namespace, scope, key, fingerprint, fingerprint_version, claimed_at, expires_at, now
) -> tuple:
    existing = IdempotencyRecord.objects.get(namespace=namespace, scope=scope, key=key)

    if (existing.fingerprint_version, existing.fingerprint) != (fingerprint_version, fingerprint):
        raise IdempotencyConflict(f'같은 키·다른 요청(또는 버전): {namespace}/{scope}/{key}')

    status = existing.status
    if status == IdempotencyStatus.COMPLETED.value:
        return ('cached', _unwrap(existing.result))
    if status == IdempotencyStatus.UNKNOWN.value:
        raise UnknownOutcome(f'불확정 결과 — 근거 있는 해소 필요: {namespace}/{scope}/{key}')

    new_token = uuid.uuid4()
    if status == IdempotencyStatus.DEFINITE_FAILURE.value:
        affected = IdempotencyRecord._writer.filter(
            pk=existing.pk, status=IdempotencyStatus.DEFINITE_FAILURE.value
        ).update(
            status=IdempotencyStatus.IN_PROGRESS.value,
            claim_token=new_token,
            claimed_at=claimed_at,
            in_progress_expires_at=expires_at,
            result=None,
            completed_at=None,
            unknown_marked_at=None,
            unknown_evidence_ref=None,
            resolved_at=None,
            resolution_evidence_ref=None,
        )
        if affected == 1:
            return ('claimed', existing.pk, new_token)
        raise InProgress('재클레임 경합 — 다른 실행이 선점')

    # IN_PROGRESS
    if existing.in_progress_expires_at is not None and existing.in_progress_expires_at > now():
        raise InProgress(f'진행 중(미만료): {namespace}/{scope}/{key}')

    # 만료 → fenced 재클레임
    affected = IdempotencyRecord._writer.filter(
        pk=existing.pk,
        status=IdempotencyStatus.IN_PROGRESS.value,
        in_progress_expires_at__lt=now(),
    ).update(
        status=IdempotencyStatus.IN_PROGRESS.value,
        claim_token=new_token,
        claimed_at=claimed_at,
        in_progress_expires_at=expires_at,
    )
    if affected == 1:
        return ('claimed', existing.pk, new_token)
    raise InProgress('재클레임 경합 — 다른 실행이 선점')


def _execute(record_pk, claim_token, operation, now) -> object:
    try:
        with transaction.atomic():
            result = operation()  # 순수 내부 효과(같은 트랜잭션)
            stored = _wrap(_normalize(result))  # JSON 정규화 — 최초/재시도 결과 타입 일치(HIGH-2)
            affected = IdempotencyRecord._writer.filter(
                pk=record_pk,
                status=IdempotencyStatus.IN_PROGRESS.value,
                claim_token=claim_token,
            ).update(
                status=IdempotencyStatus.COMPLETED.value,
                result=stored,
                completed_at=now(),
                claim_token=None,
                in_progress_expires_at=None,
            )
            if affected != 1:
                raise LostClaimError('완료 마킹 0행 — claim이 재클레임됨(stale)')
        return _unwrap(stored)
    except LostClaimError:
        raise  # 롤백 완료 — 재클레임된 레코드는 새 소유자의 몫(아무것도 하지 않는다)
    except Exception:
        # 확정 실패 → fenced tombstone(삭제 금지, 지문 보존)
        IdempotencyRecord._writer.filter(
            pk=record_pk,
            status=IdempotencyStatus.IN_PROGRESS.value,
            claim_token=claim_token,
        ).update(
            status=IdempotencyStatus.DEFINITE_FAILURE.value,
            resolved_at=now(),
            resolution_evidence_ref='internal:rolled-back',
            claim_token=None,
            in_progress_expires_at=None,
        )
        raise


def mark_unknown(
    namespace: str, scope: str, key: str, claim_token: uuid.UUID, unknown_evidence_ref: str
) -> None:
    """IN_PROGRESS를 UNKNOWN으로 전이(P6+ 외부 흐름 소유) — claim_token·근거 필수."""
    _require_nonempty(unknown_evidence_ref, 'unknown_evidence_ref')
    affected = IdempotencyRecord._writer.filter(
        namespace=namespace,
        scope=scope,
        key=key,
        status=IdempotencyStatus.IN_PROGRESS.value,
        claim_token=claim_token,
    ).update(
        status=IdempotencyStatus.UNKNOWN.value,
        unknown_marked_at=timezone.now(),
        unknown_evidence_ref=unknown_evidence_ref,
        claim_token=None,
        in_progress_expires_at=None,
    )
    if affected != 1:
        raise LostClaimError('mark_unknown 거부 — IN_PROGRESS·claim_token 불일치(COMPLETED 불변)')


def resolve_unknown_as_completed(
    namespace: str, scope: str, key: str, result: object, resolution_evidence_ref: str
) -> None:
    """UNKNOWN을 COMPLETED로 해소 — 근거 필수. 이후 재시도는 결과 캐시를 반환."""
    _require_nonempty(resolution_evidence_ref, 'resolution_evidence_ref')
    affected = IdempotencyRecord._writer.filter(
        namespace=namespace, scope=scope, key=key, status=IdempotencyStatus.UNKNOWN.value
    ).update(
        status=IdempotencyStatus.COMPLETED.value,
        result=_wrap(_normalize(result)),
        completed_at=timezone.now(),
        resolved_at=timezone.now(),
        resolution_evidence_ref=resolution_evidence_ref,
    )
    if affected != 1:
        raise LostClaimError('resolve 거부 — UNKNOWN 상태 아님')


def resolve_unknown_as_definite_failure(
    namespace: str, scope: str, key: str, resolution_evidence_ref: str
) -> None:
    """UNKNOWN을 DEFINITE_FAILURE로 해소 — 근거 필수. 같은 지문 재시도는 결과 캐시 없이 재실행."""
    _require_nonempty(resolution_evidence_ref, 'resolution_evidence_ref')
    affected = IdempotencyRecord._writer.filter(
        namespace=namespace, scope=scope, key=key, status=IdempotencyStatus.UNKNOWN.value
    ).update(
        status=IdempotencyStatus.DEFINITE_FAILURE.value,
        resolved_at=timezone.now(),
        resolution_evidence_ref=resolution_evidence_ref,
    )
    if affected != 1:
        raise LostClaimError('resolve 거부 — UNKNOWN 상태 아님')
