from decimal import Decimal

import pytest

from nautilus_core.objects import USD, EUR, BTC, AccountBalance, Currency, Money, Price, Quantity


class TestPrice:
    def test_creation(self):
        p = Price("100.50", 2)
        assert p.value == Decimal("100.50")
        assert p.precision == 2

    def test_rounding(self):
        p = Price("100.555", 2)
        assert p.value == Decimal("100.56")

    def test_add(self):
        p1 = Price("100.00", 2)
        p2 = Price("50.25", 2)
        result = p1 + p2
        assert result.value == Decimal("150.25")

    def test_sub(self):
        p1 = Price("100.00", 2)
        p2 = Price("50.25", 2)
        result = p1 - p2
        assert result.value == Decimal("49.75")

    def test_mul(self):
        p = Price("100.00", 2)
        result = p * 2
        assert result.value == Decimal("200.00")

    def test_comparison(self):
        p1 = Price("100.00", 2)
        p2 = Price("200.00", 2)
        assert p1 < p2
        assert p2 > p1
        assert p1 <= p1
        assert p1 >= p1

    def test_neg(self):
        p = Price("100.00", 2)
        result = -p
        assert result.value == Decimal("-100.00")

    def test_equality(self):
        p1 = Price("100.00", 2)
        p2 = Price("100.00", 2)
        assert p1 == p2

    def test_as_double(self):
        p = Price("100.50", 2)
        assert p.as_double() == 100.50


class TestQuantity:
    def test_creation(self):
        q = Quantity("10.5", 1)
        assert q.value == Decimal("10.5")

    def test_non_negative(self):
        with pytest.raises(ValueError):
            Quantity("-1", 0)

    def test_add(self):
        q1 = Quantity("10", 0)
        q2 = Quantity("5", 0)
        result = q1 + q2
        assert result.value == Decimal("15")

    def test_sub(self):
        q1 = Quantity("10", 0)
        q2 = Quantity("5", 0)
        result = q1 - q2
        assert result.value == Decimal("5")

    def test_bool_nonzero(self):
        assert bool(Quantity("10", 0)) is True
        assert bool(Quantity("0", 0)) is False

    def test_comparison(self):
        q1 = Quantity("10", 0)
        q2 = Quantity("20", 0)
        assert q1 < q2
        assert q2 > q1


class TestMoney:
    def test_creation(self):
        m = Money("1000.00", USD)
        assert m.amount == Decimal("1000.00")
        assert m.currency == USD

    def test_add_same_currency(self):
        m1 = Money("100.00", USD)
        m2 = Money("50.00", USD)
        result = m1 + m2
        assert result.amount == Decimal("150.00")

    def test_add_different_currency_raises(self):
        m1 = Money("100.00", USD)
        m2 = Money("50.00", EUR)
        with pytest.raises(ValueError):
            m1 + m2

    def test_sub(self):
        m1 = Money("100.00", USD)
        m2 = Money("30.00", USD)
        result = m1 - m2
        assert result.amount == Decimal("70.00")

    def test_neg(self):
        m = Money("100.00", USD)
        result = -m
        assert result.amount == Decimal("-100.00")

    def test_repr(self):
        m = Money("100.00", USD)
        assert "100.00" in repr(m)
        assert "USD" in repr(m)


class TestAccountBalance:
    def test_creation(self):
        total = Money("1000.00", USD)
        locked = Money("200.00", USD)
        free = Money("800.00", USD)
        bal = AccountBalance(total=total, locked=locked, free=free)
        assert bal.total.amount == Decimal("1000.00")
        assert bal.locked.amount == Decimal("200.00")
        assert bal.free.amount == Decimal("800.00")

    def test_mismatched_currency_raises(self):
        with pytest.raises(ValueError):
            AccountBalance(
                total=Money("1000.00", USD),
                locked=Money("200.00", EUR),
                free=Money("800.00", USD),
            )
