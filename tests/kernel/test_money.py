"""Money 표현·연산 계약(US1 #1~4, FR-001·002·011, K-1·2·3, SC-001·002).

부동소수점이 **구조적으로** 침투할 수 없음을 표현(최소 단위 정수)과 API 경계
타입 거부로 강제하고, SC-002는 money.py 소스의 AST 검사로 기계 증명한다.
DB 불필요 — Money 단독으로 검증(Independent Test).
"""

import ast
import pathlib
from fractions import Fraction

import pytest

from shared_kernel.money import (
    Currency,
    CurrencyError,
    Money,
    RoundingPolicy,
)

MONEY_PY = pathlib.Path(__file__).resolve().parents[2] / 'shared_kernel' / 'money.py'


@pytest.fixture(autouse=True)
def _register_usd():
    """교차 통화 검증용 제2통화(USD, 지수 2) 등록 — 같은 값 재등록은 무해(멱등)."""
    Currency.register('USD', 2)


def krw(minor: int) -> Money:
    return Money(minor, Currency.of('KRW'))


# --- 생성: minor-unit int만 (K-1, R2) ---


def test_krw_registered_with_exponent_zero():
    assert Currency.of('KRW').exponent == 0


def test_construct_with_int_ok():
    m = krw(1000)
    assert m.amount_minor == 1000


def test_construct_with_float_rejected():
    with pytest.raises(TypeError):
        Money(1.0, Currency.of('KRW'))


def test_construct_with_decimal_instance_rejected():
    """Decimal이 float 유래인지 객체만으로 판별 불가 — 생성 경로에서 일관 거부(R2)."""
    from decimal import Decimal

    with pytest.raises(TypeError):
        Money(Decimal('1'), Currency.of('KRW'))


# --- 통화 레지스트리 (BR-2) ---


def test_currency_of_unregistered_rejected():
    with pytest.raises(CurrencyError):
        Currency.of('XXX')


def test_currency_register_same_value_idempotent():
    Currency.register('USD', 2)  # 이미 fixture가 등록 — 같은 값 재등록 무해
    assert Currency.of('USD').exponent == 2


def test_currency_register_conflicting_value_rejected():
    with pytest.raises(CurrencyError):
        Currency.register('USD', 3)  # 지수 불일치


def test_forged_currency_instance_rejected():
    """직접 생성한 위조 인스턴스(다른 지수)는 연산 전 레지스트리 대조로 거부."""
    forged = Currency('KRW', 5)
    with pytest.raises(CurrencyError):
        Money(100, forged)


# --- 같은 통화 산술·비교 결정론 (SC-001) ---


def test_addition_subtraction_multiplication_int():
    assert krw(1000) + krw(500) == krw(1500)
    assert krw(1000) - krw(300) == krw(700)
    assert krw(1000) * 3 == krw(3000)


def test_arithmetic_is_deterministic():
    for _ in range(5):
        assert krw(333) + krw(667) == krw(1000)
        assert krw(1000) * 7 == krw(7000)


def test_ordering_comparison_same_currency():
    assert krw(100) < krw(200)
    assert krw(200) >= krw(200)


# --- 통화 불일치 거부 (K-2) ---


def test_cross_currency_arithmetic_rejected():
    with pytest.raises(CurrencyError):
        _ = krw(100) + Money(100, Currency.of('USD'))


def test_cross_currency_ordering_rejected():
    with pytest.raises(CurrencyError):
        _ = krw(100) < Money(100, Currency.of('USD'))


def test_cross_currency_equality_is_false_not_raise():
    """== 는 값 기반(다른 통화 → not equal) — 컨테이너 안전. 거부는 순서 비교 몫."""
    assert (krw(100) == Money(100, Currency.of('USD'))) is False


# --- multiply: 스칼라 타입 제한 + 반올림 정책 필수 (K-3) ---


def test_multiply_requires_rounding_policy():
    with pytest.raises(TypeError):
        krw(100).multiply('1.5')  # rounding 누락 → 필수 인자 거부


def test_multiply_rejects_float_scalar():
    with pytest.raises(TypeError):
        krw(100).multiply(1.5, rounding=RoundingPolicy.ROUND_HALF_UP)


def test_multiply_rejects_decimal_scalar():
    from decimal import Decimal

    with pytest.raises(TypeError):
        krw(100).multiply(Decimal('1.5'), rounding=RoundingPolicy.ROUND_HALF_UP)


def test_multiply_accepts_exact_decimal_string():
    assert krw(100).multiply('1.5', rounding=RoundingPolicy.ROUND_HALF_UP) == krw(150)


def test_multiply_accepts_fraction():
    assert krw(100).multiply(Fraction(3, 2), rounding=RoundingPolicy.ROUND_HALF_UP) == krw(150)


def test_multiply_rounding_policies_are_deterministic():
    """101 * 1.005 = 101.505 → 정책별 결정론 결과(minor unit 정수)."""
    base = krw(101)
    scalar = '1.005'  # 101.505
    assert base.multiply(scalar, rounding=RoundingPolicy.ROUND_DOWN) == krw(101)
    assert base.multiply(scalar, rounding=RoundingPolicy.ROUND_UP) == krw(102)
    assert base.multiply(scalar, rounding=RoundingPolicy.ROUND_HALF_UP) == krw(102)
    # 101.505 의 0.505 > 0.5 → HALF_EVEN 도 올림
    assert base.multiply(scalar, rounding=RoundingPolicy.ROUND_HALF_EVEN) == krw(102)


def test_multiply_half_even_ties_to_even():
    """정확히 절반인 경우 HALF_EVEN은 짝수로: 2.5→2, 3.5→4 (minor unit)."""
    assert krw(5).multiply('0.5', rounding=RoundingPolicy.ROUND_HALF_EVEN) == krw(2)
    assert krw(7).multiply('0.5', rounding=RoundingPolicy.ROUND_HALF_EVEN) == krw(4)
    # HALF_UP은 절반을 0에서 먼 쪽으로: 2.5→3
    assert krw(5).multiply('0.5', rounding=RoundingPolicy.ROUND_HALF_UP) == krw(3)


def test_negative_rounding_toward_and_away_from_zero():
    """음수: ROUND_DOWN=0 방향(절사), ROUND_UP=0에서 먼 방향."""
    assert krw(-101).multiply('1.005', rounding=RoundingPolicy.ROUND_DOWN) == krw(-101)
    assert krw(-101).multiply('1.005', rounding=RoundingPolicy.ROUND_UP) == krw(-102)


# --- SC-002: 내부 float 부재의 기계 검증 (AST) ---


def test_money_source_has_no_float_literals_calls_or_truediv():
    tree = ast.parse(MONEY_PY.read_text())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            offenders.append(f'float 리터럴 @L{node.lineno}')
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'float'
        ):
            offenders.append(f'float() 호출 @L{node.lineno}')
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            offenders.append(f'진수 나눗셈(/) @L{node.lineno}')
    assert offenders == [], f'money.py에 float 경로 존재: {offenders}'


def test_large_amounts_beyond_2_pow_53_are_exact():
    """2^60원: float 경유 시 정밀도 손실이 날 액수 — int/Fraction 경로는 정확."""
    big = 2**60
    assert krw(big).amount_minor == big
    assert (krw(big) + krw(1)).amount_minor == big + 1
    assert krw(big).multiply('2', rounding=RoundingPolicy.ROUND_DOWN) == krw(big * 2)
    # 홀수 배 + 반올림도 정확
    assert krw(big + 1).multiply('1.5', rounding=RoundingPolicy.ROUND_HALF_UP) == krw(
        (3 * (big + 1) + 1) // 2
    )
