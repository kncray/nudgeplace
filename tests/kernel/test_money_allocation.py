"""안분(allocate) 계약(US1 #5, FR-011, K-4, SC-008).

largest-remainder 계열 + 명시적 끝전 귀속으로 **합계 보존을 구성적으로** 보장.
정책 인자는 필수(암묵 기본값 금지). T021 구현 후 money.py AST 검사를 재적용해
안분 경로에도 float가 없음을 재확인한다(SC-002).
"""

import ast
import pathlib

import pytest

from shared_kernel.money import (
    AllocationError,
    Currency,
    Money,
    RemainderPolicy,
)

MONEY_PY = pathlib.Path(__file__).resolve().parents[2] / 'shared_kernel' / 'money.py'


def krw(minor: int) -> Money:
    return Money(minor, Currency.of('KRW'))


def _minors(parts: list[Money]) -> list[int]:
    return [p.amount_minor for p in parts]


# --- 합계 보존 (SC-008) ---


@pytest.mark.parametrize(
    'principal,weights',
    [
        (10000, [1, 1, 1]),
        (10001, [1, 1, 1]),
        (100, [2, 1, 1]),
        (99999, [3, 5, 7, 11]),
        (1, [1, 1, 1, 1, 1]),
    ],
)
def test_allocation_preserves_total(principal, weights):
    parts = krw(principal).allocate(weights, remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
    assert sum(_minors(parts)) == principal
    assert len(parts) == len(weights)


def test_ten_thousand_split_three_ways():
    """10,000원 3등분 → 3,334 / 3,333 / 3,333 (US1 #5)."""
    parts = krw(10000).allocate([1, 1, 1], remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
    assert _minors(parts) == [3334, 3333, 3333]


# --- 귀속 정책별 결정론 ---


def test_remainder_policies_distribute_extra_deterministically():
    """가중치 [1,2,1], 101원 → floor [25,50,25], 잔여 1 (remainders [1,2,1])."""
    weights = [1, 2, 1]
    lr = krw(101).allocate(weights, remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
    first = krw(101).allocate(weights, remainder_policy=RemainderPolicy.FIRST)
    last = krw(101).allocate(weights, remainder_policy=RemainderPolicy.LAST)
    assert _minors(lr) == [25, 51, 25]  # 잔여 최대(index 1)
    assert _minors(first) == [26, 50, 25]  # 앞에서부터
    assert _minors(last) == [25, 50, 26]  # 뒤에서부터


def test_allocation_is_deterministic_on_repeat():
    for _ in range(5):
        parts = krw(10000).allocate([1, 1, 1], remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
        assert _minors(parts) == [3334, 3333, 3333]


def test_allocate_requires_remainder_policy():
    with pytest.raises(TypeError):
        krw(100).allocate([1, 1])  # 정책 누락 → 필수 인자 거부


# --- 경계 입력 (FR-011) ---


def test_empty_weights_rejected():
    with pytest.raises(AllocationError):
        krw(100).allocate([], remainder_policy=RemainderPolicy.FIRST)


def test_zero_weight_sum_rejected():
    with pytest.raises(AllocationError):
        krw(100).allocate([0, 0], remainder_policy=RemainderPolicy.FIRST)


def test_negative_weight_rejected():
    with pytest.raises(AllocationError):
        krw(100).allocate([-1, 2], remainder_policy=RemainderPolicy.FIRST)


def test_single_split_returns_principal():
    parts = krw(777).allocate([1], remainder_policy=RemainderPolicy.FIRST)
    assert _minors(parts) == [777]


def test_negative_principal_sign_preserving():
    parts = krw(-10000).allocate([1, 1, 1], remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
    assert sum(_minors(parts)) == -10000
    assert _minors(parts) == [-3334, -3333, -3333]


# --- SC-002 재검증(T021 이후 전체 money.py) + 대액 안분 정확성 ---


def test_money_source_still_has_no_float_after_allocation():
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


def test_large_amount_allocation_is_exact():
    """2^60원 3등분 — float 경유 시 정밀도 손실. int 경로는 정확·합계 보존."""
    big = 2**60
    parts = krw(big).allocate([1, 1, 1], remainder_policy=RemainderPolicy.LARGEST_REMAINDER)
    assert sum(_minors(parts)) == big
    q, r = divmod(big, 3)
    assert _minors(parts) == [q + r, q, q]  # 잔여 r개를 앞에서부터(동률 tie)
