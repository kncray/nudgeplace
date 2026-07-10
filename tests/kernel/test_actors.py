"""행위자 역할 어휘(US4 #4, FR-007). DB 불필요 — 값 객체."""

from shared_kernel.actors import Actor, ActorRole


def test_four_roles_provided():
    assert {r.name for r in ActorRole} == {'OPERATOR', 'VENDOR', 'CUSTOMER', 'SYSTEM'}


def test_actor_holds_role_and_id():
    actor = Actor(ActorRole.OPERATOR, 'op-42')
    assert actor.role is ActorRole.OPERATOR
    assert actor.actor_id == 'op-42'


def test_actor_is_immutable():
    import dataclasses

    actor = Actor(ActorRole.VENDOR, 'vendor-1')
    with __import__('pytest').raises(dataclasses.FrozenInstanceError):
        actor.actor_id = 'x'


# --- 적대 리뷰 반영: 익명/무효 행위자 거부(FR-006·007) ---


def test_empty_actor_id_rejected():
    import pytest

    with pytest.raises(ValueError):
        Actor(ActorRole.OPERATOR, '')
    with pytest.raises(ValueError):
        Actor(ActorRole.OPERATOR, '   ')


def test_non_actorrole_rejected():
    import pytest

    with pytest.raises(ValueError):
        Actor('operator', 'op-1')
