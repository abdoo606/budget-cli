from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .ledger import Ledger
from .money import Money
from .report import alerts, category_report, monthly_report, summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="budget", description="Track income and expenses.")
    p.add_argument("--db", default="budget.db")
    sub = p.add_subparsers(dest="command", required=True)

    for name, help_text in (("add", "record an entry"), ("income", "record income")):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("amount")
        s.add_argument("category")
        s.add_argument("-n", "--note", default="")
        s.add_argument("-d", "--day")
        s.add_argument("--currency", default="USD")

    lim = sub.add_parser("limit", help="set a monthly cap for a category")
    lim.add_argument("category")
    lim.add_argument("amount")

    r = sub.add_parser("report", help="monthly report")
    r.add_argument("--month", help="YYYY-MM")

    c = sub.add_parser("categories", help="spending by category")
    c.add_argument("--month")

    sub.add_parser("status", help="balance and budget alerts")

    imp = sub.add_parser("import", help="import a CSV (day,category,amount,note)")
    imp.add_argument("csvfile", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with Ledger(args.db) as ledger:
        try:
            if args.command in {"add", "income"}:
                amount = Money.parse(args.amount, args.currency)
                if args.command == "add":
                    amount = -amount
                ledger.add(amount, args.category, note=args.note, day=args.day)
                print(f"recorded {args.command}: {amount} [{args.category}]")

            elif args.command == "limit":
                ledger.set_limit(args.category, Money.parse(args.amount))
                print(f"limit set for {args.category}")

            elif args.command == "report":
                print(monthly_report(ledger))

            elif args.command == "categories":
                print(category_report(ledger, month=args.month))

            elif args.command == "status":
                print(summary(ledger))
                print(alerts(ledger))

            elif args.command == "import":
                with args.csvfile.open(newline="", encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        amount = Money.parse(row["amount"])
                        if amount.minor < 0:
                            amount = -amount
                        ledger.add(amount, row["category"], note=row.get("note", ""), day=row.get("day"))
                print(f"imported {args.csvfile}")
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
