from decimal import Decimal

import pytest

from shared.money import Money


@pytest.mark.parametrize("amount", [1.0, 250000.0, True, Decimal(1), "1000"])
def test_rejects_non_int_amount(amount: object) -> None:
    with pytest.raises(TypeError):
        Money(amount)  # type: ignore[arg-type]


def test_rejects_unsupported_currency() -> None:
    with pytest.raises(ValueError, match="USD"):
        Money(1, "USD")


def test_arithmetic_keeps_currency() -> None:
    assert Money(300) + Money(200) == Money(500)
    assert Money(300) - Money(500) == Money(-200)
    assert Money(250) * 3 == Money(750)
    assert 3 * Money(250) == Money(750)
    assert -Money(100) == Money(-100)


def test_sum_of_money_list() -> None:
    assert sum([Money(100), Money(200), Money(-50)]) == Money(250)


def test_rejects_adding_non_zero_int() -> None:
    with pytest.raises(TypeError):
        5 + Money(100)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Money(100) + 0  # type: ignore[operator]


def test_rejects_multiplying_by_float() -> None:
    with pytest.raises(TypeError):
        Money(100) * 1.5  # type: ignore[operator]


def test_compares_amounts() -> None:
    assert Money(100) < Money(200)
    assert Money(200) >= Money(200)
    assert max(Money(1), Money(3), Money(2)) == Money(3)


def test_is_immutable() -> None:
    money = Money(100)

    with pytest.raises(AttributeError):
        money.amount = 200  # type: ignore[misc]
