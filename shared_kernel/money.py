"""Money primitive — 금액의 안전한 표현·연산(원칙 V, FR-001·002·011).

부동소수점을 **표현 구조**로 배제한다: 액수는 통화 최소 단위의 정수(int)로만
저장하며, 생성·연산 어느 경로에서도 float·Decimal 인스턴스를 받지 않는다(R2).
비정수 스칼라 곱은 정확 십진 문자열 또는 Fraction으로만 받고 반올림 정책을
필수로 요구한다. 안분은 largest-remainder 계열로 합계를 구성적으로 보존한다(R3).

이 모듈에는 float 리터럴·`float()` 호출·진수 나눗셈(`/`)이 존재하지 않는다 —
정수 나눗셈(`//`)·`divmod`·`Fraction`만 사용한다(SC-002, AST 검사로 강제).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction


class MoneyError(Exception):
    """Money primitive 계약 위반의 기반 예외."""


class CurrencyError(MoneyError):
    """미등록·위조·불일치 통화."""


class AllocationError(MoneyError):
    """안분 경계 입력 위반(빈 목록·가중치 합 0·음수 가중치)."""


class RoundingPolicy(enum.Enum):
    """반올림 정책 어휘(stdlib decimal 상수 대응). 기본값 없음 — 명시 필수(FR-002)."""

    ROUND_DOWN = 'ROUND_DOWN'  # 0 방향 절사
    ROUND_UP = 'ROUND_UP'  # 0에서 먼 방향
    ROUND_HALF_UP = 'ROUND_HALF_UP'  # 사사오입(절반은 0에서 먼 쪽)
    ROUND_HALF_EVEN = 'ROUND_HALF_EVEN'  # 은행가 반올림(절반은 짝수)


class RemainderPolicy(enum.Enum):
    """끝전 귀속 정책 어휘. 기본값 없음 — 명시 필수(FR-011)."""

    LARGEST_REMAINDER = 'LARGEST_REMAINDER'  # 잔여 큰 몫 우선(동률은 앞 순서)
    FIRST = 'FIRST'  # 앞에서부터
    LAST = 'LAST'  # 뒤에서부터


_CURRENCY_REGISTRY: dict[str, 'Currency'] = {}


@dataclass(frozen=True, slots=True)
class Currency:
    """통화 — 코드와 최소 단위 지수(minor unit exponent).

    정상 획득 경로는 `Currency.of(code)`이며, 등록은 `Currency.register`가 한다.
    직접 생성한 인스턴스는 Money 연산 시 레지스트리 대조로 검증된다.
    """

    code: str
    exponent: int

    @classmethod
    def of(cls, code: str) -> 'Currency':
        """등록된 통화를 반환한다 — 미등록 코드는 거부(BR-2)."""
        try:
            return _CURRENCY_REGISTRY[code]
        except KeyError:
            raise CurrencyError(f'미등록 통화 코드: {code!r}') from None

    @classmethod
    def register(cls, code: str, exponent: int) -> 'Currency':
        """통화를 등록한다 — 같은 값 재등록은 무해, 다른 값 재등록은 거부."""
        existing = _CURRENCY_REGISTRY.get(code)
        candidate = cls(code, exponent)
        if existing is not None and existing != candidate:
            raise CurrencyError(
                f'통화 {code!r} 재등록 충돌: 기존 지수 {existing.exponent} != {exponent}'
            )
        _CURRENCY_REGISTRY[code] = candidate
        return candidate


# 초기 통화: KRW(원 — 최소 단위 지수 0).
Currency.register('KRW', 0)


def _validate_currency(currency: Currency) -> None:
    """레지스트리 대조 — 미등록·위조(다른 지수) 인스턴스를 거부."""
    if not isinstance(currency, Currency):
        raise CurrencyError(f'Currency 아님: {type(currency).__name__}')
    if Currency.of(currency.code) != currency:
        raise CurrencyError(f'레지스트리와 불일치하는 통화 인스턴스: {currency!r}')


def _scalar_to_fraction(scalar: object) -> Fraction:
    """스칼라를 정확한 Fraction으로 — int·정확 십진 문자열·Fraction만 허용(R2).

    float·Decimal 인스턴스는 거부한다(float 유래 오염을 객체 시점에 판별 불가).
    """
    if isinstance(scalar, bool):
        raise TypeError('bool 스칼라 거부')
    if isinstance(scalar, int):
        return Fraction(scalar)
    if isinstance(scalar, Fraction):
        return scalar
    if isinstance(scalar, str):
        try:
            return Fraction(Decimal(scalar))  # 정확 십진 변환(내부 경로 — float 없음)
        except (ArithmeticError, ValueError) as exc:
            raise TypeError(f'정확 십진 문자열이 아님: {scalar!r}') from exc
    raise TypeError(f'허용되지 않는 스칼라 타입: {type(scalar).__name__} (float·Decimal 거부)')


def _round_fraction(value: Fraction, rounding: RoundingPolicy) -> int:
    """Fraction을 정책에 따라 정수로 반올림 — `/` 없이 divmod·비교만 사용."""
    if not isinstance(rounding, RoundingPolicy):
        raise TypeError('rounding은 RoundingPolicy여야 한다')
    negative = value < 0
    magnitude = -value if negative else value
    q, r = divmod(magnitude.numerator, magnitude.denominator)  # q>=0, 0<=r<den
    if r == 0:
        rounded = q
    else:
        twice = 2 * r
        den = magnitude.denominator
        if rounding is RoundingPolicy.ROUND_DOWN:
            rounded = q
        elif rounding is RoundingPolicy.ROUND_UP:
            rounded = q + 1
        elif rounding is RoundingPolicy.ROUND_HALF_UP:
            rounded = q + 1 if twice >= den else q
        else:  # ROUND_HALF_EVEN
            if twice > den:
                rounded = q + 1
            elif twice < den:
                rounded = q
            else:
                rounded = q + 1 if q % 2 == 1 else q
    return -rounded if negative else rounded


@dataclass(frozen=True, slots=True)
class Money:
    """금액 값 객체 — 최소 단위 정수 + 통화. 불변(frozen)."""

    amount_minor: int
    currency: Currency

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError(
                f'amount_minor는 int여야 한다(float·Decimal 거부): '
                f'{type(self.amount_minor).__name__}'
            )
        _validate_currency(self.currency)

    def _check_same_currency(self, other: 'Money') -> None:
        if not isinstance(other, Money):
            raise TypeError(f'Money가 아님: {type(other).__name__}')
        if self.currency != other.currency:
            raise CurrencyError(f'통화 불일치: {self.currency.code} vs {other.currency.code}')

    def __add__(self, other: 'Money') -> 'Money':
        self._check_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        self._check_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def __mul__(self, factor: int) -> 'Money':
        """무손실 정수 배. 비정수 배율은 `multiply`(반올림 정책 필수)를 쓴다."""
        if isinstance(factor, bool) or not isinstance(factor, int):
            raise TypeError('Money * 정수만 허용 — 비정수 배율은 multiply()를 쓴다')
        return Money(self.amount_minor * factor, self.currency)

    __rmul__ = __mul__

    def multiply(self, scalar: object, *, rounding: RoundingPolicy) -> 'Money':
        """비율 곱 + 명시적 반올림. scalar = int·정확 십진 문자열·Fraction(K-3)."""
        product = Fraction(self.amount_minor) * _scalar_to_fraction(scalar)
        return Money(_round_fraction(product, rounding), self.currency)

    # 순서 비교는 통화 불일치를 거부한다(K-2). 동등성은 값 기반(다른 통화 → not equal).
    def __lt__(self, other: 'Money') -> bool:
        self._check_same_currency(other)
        return self.amount_minor < other.amount_minor

    def __le__(self, other: 'Money') -> bool:
        self._check_same_currency(other)
        return self.amount_minor <= other.amount_minor

    def __gt__(self, other: 'Money') -> bool:
        self._check_same_currency(other)
        return self.amount_minor > other.amount_minor

    def __ge__(self, other: 'Money') -> bool:
        self._check_same_currency(other)
        return self.amount_minor >= other.amount_minor

    def allocate(self, weights: list[int], *, remainder_policy: RemainderPolicy) -> list['Money']:
        """가중치 안분 — floor 분배 + 끝전 귀속. 합계 보존(SC-008)."""
        if not isinstance(remainder_policy, RemainderPolicy):
            raise TypeError('remainder_policy는 RemainderPolicy여야 한다')
        if not weights:
            raise AllocationError('빈 가중치 목록')
        if any((isinstance(w, bool) or not isinstance(w, int)) for w in weights):
            raise AllocationError('가중치는 int여야 한다')
        if any(w < 0 for w in weights):
            raise AllocationError('음수 가중치 거부')
        total_weight = sum(weights)
        if total_weight == 0:
            raise AllocationError('가중치 합이 0')

        negative = self.amount_minor < 0
        magnitude = -self.amount_minor if negative else self.amount_minor

        floors = [(magnitude * w) // total_weight for w in weights]
        remainders = [(magnitude * w) % total_weight for w in weights]
        leftover = magnitude - sum(floors)

        recipients = self._remainder_recipients(remainders, leftover, remainder_policy)
        for i in recipients:
            floors[i] += 1

        if negative:
            floors = [-f for f in floors]
        return [Money(f, self.currency) for f in floors]

    @staticmethod
    def _remainder_recipients(
        remainders: list[int], leftover: int, policy: RemainderPolicy
    ) -> list[int]:
        """끝전 minor unit `leftover`개를 받을 인덱스 목록을 정책대로 결정한다."""
        n = len(remainders)
        if policy is RemainderPolicy.FIRST:
            order = list(range(n))
        elif policy is RemainderPolicy.LAST:
            order = list(range(n - 1, -1, -1))
        else:  # LARGEST_REMAINDER: 잔여 큰 순, 동률은 앞 인덱스 우선
            order = sorted(range(n), key=lambda i: (-remainders[i], i))
        return order[:leftover]
