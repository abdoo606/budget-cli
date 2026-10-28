from __future__ import annotations

import pytest

from budget.ledger import Ledger
from budget.money import Money
from budget.report import alerts, category_report, monthly_report, sparkline, summary


# ------------------------------------------------------------------ money
def test_parse_rounds_half_up():
    assert Money.parse("10.005").minor == 1001
    assert Money.parse("1,234.50").minor == 123450


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        Money.parse("twelve")


def test_addition_and_subtraction():
    assert Money(1000) + Money(250) == Money(1250)
    assert Money(1000) - Money(250) == Money(750)


def test_currency_mismatch_raises():
    with pytest.raises(ValueError, match="currency mismatch"):
        Money(100, "USD") + Money(100, "EUR")


def test_formatting():
    assert str(Money(123456, "USD")) == "$1,234.56"
    assert str(Money(-500, "EUR")) == "-€5.00"


# ----------------------------------------------------------------- ledger
@pytest.fixture()
def ledger():
    with Ledger(":memory:") as lg:
        yield lg


def test_add_and_balance(ledger):
    ledger.add(Money(300000), "salary")
    ledger.add(Money(-120050), "rent")
    assert ledger.balance() == Money(179950)


def test_invalid_date_rejected(ledger):
    with pytest.raises(ValueError, match="invalid date"):
        ledger.add(Money(-100), "food", day="2024-13-40")


def test_by_category_sorted_by_amount(ledger):
    ledger.add(Money(-5000), "food", day="2024-12-01")
    ledger.add(Money(-2000), "food", day="2024-12-02")
    ledger.add(Money(-90000), "rent", day="2024-12-01")
    totals = ledger.by_category(month="2024-12")
    assert list(totals) == ["rent", "food"]
    assert totals["food"] == -7000


def test_month_filter(ledger):
    ledger.add(Money(-100), "a", day="2024-11-30")
    ledger.add(Money(-100), "a", day="2024-12-01")
    assert len(ledger.entries(month="2024-12")) == 1


def test_overspent_detection(ledger):
    ledger.set_limit("food", Money(10000))
    ledger.add(Money(-12000), "food")
    over = ledger.overspent()
    assert over and over[0][0] == "food"
    assert over[0][1] == Money(12000)


def test_limits_upsert(ledger):
    ledger.set_limit("food", Money(10000))
    ledger.set_limit("food", Money(20000))
    assert ledger.limits() == {"food": 20000}


def test_monthly_totals(ledger):
    ledger.add(Money(500000), "salary", day="2024-12-01")
    ledger.add(Money(-200000), "rent", day="2024-12-02")
    assert ledger.monthly_totals() == {"2024-12": (500000, 200000)}


# ---------------------------------------------------------------- reports
def test_sparkline_handles_flat_series():
    assert sparkline([5, 5, 5]) == "▁▁▁"


def test_sparkline_uses_full_range():
    line = sparkline([1, 2, 3, 4, 5, 6, 7, 8])
    assert line[0] == "▁" and line[-1] == "█"


def test_reports_on_empty_ledger(ledger):
    assert "no entries" in category_report(ledger)
    assert "no entries" in monthly_report(ledger)
    assert "within budget" in alerts(ledger)


def test_summary_reports_deficit(ledger):
    ledger.add(Money(-100), "x")
    assert "deficit" in summary(ledger)


def test_category_report_contains_bar_chart(ledger):
    ledger.add(Money(-100), "food", day="2024-12-01")
    assert "█" in category_report(ledger, month="2024-12")
