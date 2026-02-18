#!/usr/bin/env python3
"""Build Kakao expiry ±5 trading-day window dataset without third-party packages.

Usage examples:
  python kakao_expiry_window.py --input-csv kakao_daily.csv
  python kakao_expiry_window.py --demo

Input CSV format (`--input-csv`):
  date,close
  2021-01-04,401000
  2021-01-05,408500
  ...
"""

from __future__ import annotations

import argparse
import csv
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


EXPIRY_DATES = [
    "2021-02-10","2021-03-11","2021-04-08","2021-05-13","2021-06-10","2021-07-08","2021-08-12","2021-09-09","2021-10-14","2021-11-11","2021-12-09",
    "2022-01-13","2022-02-10","2022-03-10","2022-04-14","2022-05-12","2022-06-09","2022-07-14","2022-08-11","2022-09-08","2022-10-13","2022-11-10","2022-12-08",
    "2023-01-12","2023-02-09","2023-03-09","2023-04-13","2023-05-11","2023-06-08","2023-07-13","2023-08-10","2023-09-14","2023-10-12","2023-11-09","2023-12-14",
    "2024-01-11","2024-02-08","2024-03-14","2024-04-11","2024-05-09","2024-06-13","2024-07-11","2024-08-08","2024-09-12","2024-10-10","2024-11-14","2024-12-12",
    "2025-01-09","2025-02-13","2025-03-13","2025-04-10","2025-05-08","2025-06-12","2025-07-10","2025-08-14","2025-09-11","2025-10-02","2025-11-13","2025-12-11",
    "2026-01-08","2026-02-12",
]


@dataclass
class PriceRow:
    trading_date: date
    close: float


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_price_rows(csv_path: Path) -> List[PriceRow]:
    rows: List[PriceRow] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing.")

        lower_map = {name.lower(): name for name in reader.fieldnames}
        date_col = lower_map.get("date")
        close_col = lower_map.get("close")
        if not date_col or not close_col:
            raise ValueError("CSV must include 'date' and 'close' columns.")

        for row in reader:
            rows.append(PriceRow(trading_date=parse_date(row[date_col]), close=float(row[close_col])))

    rows.sort(key=lambda x: x.trading_date)
    if not rows:
        raise ValueError("No rows loaded from CSV.")
    return rows


def build_demo_rows() -> List[PriceRow]:
    # Deterministic mini dataset around first two expiry dates for offline demonstration.
    demo = [
        ("2021-02-01", 91100), ("2021-02-02", 90500), ("2021-02-03", 91800), ("2021-02-04", 92400),
        ("2021-02-05", 92000), ("2021-02-08", 91500), ("2021-02-09", 92200), ("2021-02-10", 93000),
        ("2021-02-15", 93200), ("2021-02-16", 92800), ("2021-02-17", 93600),
        ("2021-03-04", 94500), ("2021-03-05", 95000), ("2021-03-08", 95600), ("2021-03-09", 96100),
        ("2021-03-10", 95800), ("2021-03-11", 96300), ("2021-03-12", 96700), ("2021-03-15", 97100),
        ("2021-03-16", 97500), ("2021-03-17", 96900),
    ]
    return [PriceRow(parse_date(d), c) for d, c in demo]


def map_to_prev_trading_day(target: date, trading_days: Sequence[date]) -> date:
    idx = bisect_right(trading_days, target) - 1
    if idx < 0:
        raise ValueError(f"No previous trading day available for {target.isoformat()}")
    return trading_days[idx]


def build_expiry_window_rows(price_rows: Sequence[PriceRow], k: int = 5) -> List[dict]:
    trading_days = [r.trading_date for r in price_rows]
    close_by_day = {r.trading_date: r.close for r in price_rows}
    day_to_index = {d: i for i, d in enumerate(trading_days)}

    output: List[dict] = []

    for expiry_raw in EXPIRY_DATES:
        expiry = parse_date(expiry_raw)
        if expiry < trading_days[0] or expiry > trading_days[-1]:
            continue

        mapped = expiry if expiry in day_to_index else map_to_prev_trading_day(expiry, trading_days)
        center = day_to_index[mapped]

        lo = max(0, center - k)
        hi = min(len(trading_days) - 1, center + k)

        prev_close = None
        for i in range(lo, hi + 1):
            d = trading_days[i]
            close = close_by_day[d]
            ret_1d = None if prev_close is None else (close / prev_close - 1.0)
            output.append(
                {
                    "date": d.isoformat(),
                    "Close": f"{close:.2f}",
                    "expiry": mapped.isoformat(),
                    "t": str(i - center),
                    "ret_1d": "" if ret_1d is None else f"{ret_1d:.8f}",
                }
            )
            prev_close = close

    output.sort(key=lambda row: (row["expiry"], int(row["t"])))
    return output


def write_output(rows: Sequence[dict], output_csv: Path) -> None:
    with output_csv.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["date", "Close", "expiry", "t", "ret_1d"])
        writer.writeheader()
        writer.writerows(rows)


def print_preview(rows: Sequence[dict], n: int = 20) -> None:
    print("\nPreview:")
    for idx, row in enumerate(rows[:n], start=1):
        print(f"{idx:>2}: {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", type=Path, help="Path to daily price CSV with columns: date,close")
    parser.add_argument("--output-csv", type=Path, default=Path("kakao_expiry_window_5d.csv"))
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo data (offline).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.demo:
        price_rows = build_demo_rows()
    elif args.input_csv:
        price_rows = load_price_rows(args.input_csv)
    else:
        raise SystemExit("Provide --input-csv (real data) or --demo (offline demonstration).")

    result = build_expiry_window_rows(price_rows, k=5)
    write_output(result, args.output_csv)
    print_preview(result, n=20)
    print(f"\nsaved: {args.output_csv}")
    print(f"rows: {len(result)}")


if __name__ == "__main__":
    main()
