"""Text reports with dependency-free ASCII charts."""

from __future__ import annotations

from .ledger import Ledger
from .money import Money

BAR_WIDTH = 28


def sparkline(values: list[int]) -> str:
    blocks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return blocks[0] * len(values)
    return "".join(blocks[int((v - lo) / (hi - lo) * (len(blocks) - 1))] for v in values)


def bar(label: str, value: int, peak: int, width: int = BAR_WIDTH) -> str:
    filled = int(abs(value) / peak * width) if peak else 0
    return f"{label:<14}{'█' * filled:<{width}} {value / 100:>9,.2f}"


def category_report(ledger: Ledger, *, month: str | None = None) -> str:
    totals = ledger.by_category(month=month)
    if not totals:
        return "no entries yet"
    peak = max(abs(v) for v in totals.values())
    lines = [f"categories{' for ' + month if month else ''}"]
    for category, minor in totals.items():
        lines.append(bar(category, -minor, peak))
    return "\n".join(lines)


def monthly_report(ledger: Ledger) -> str:
    totals = ledger.monthly_totals()
    if not totals:
        return "no entries yet"
    savings = [inc - exp for inc, exp in totals.values()]
    lines = ["month        income     expenses      saved", "-" * 48]
    for month, (inc, exp) in totals.items():
        lines.append(f"{month:<10}{inc / 100:>10,.2f}{exp / 100:>13,.2f}{(inc - exp) / 100:>11,.2f}")
    lines.append("-" * 48)
    lines.append(f"trend (savings): {sparkline(savings)}")
    return "\n".join(lines)


def alerts(ledger: Ledger, *, month: str | None = None) -> str:
    over = ledger.overspent(month=month)
    if not over:
        return "all categories within budget"
    return "\n".join(
        f"OVER BUDGET: {category} spent {spent} of {limit}" for category, spent, limit in over
    )


def summary(ledger: Ledger) -> str:
    balance: Money = ledger.balance()
    status = "surplus" if balance.minor >= 0 else "deficit"
    return f"total balance: {balance} ({status})"
