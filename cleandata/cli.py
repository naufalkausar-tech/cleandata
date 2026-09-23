"""Command-line interface: cleandata input.csv -o clean.csv -r report.md"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .core import clean_dataframe


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def _write_any(df: pd.DataFrame, path: Path) -> None:
    if path.suffix.lower() in (".xlsx", ".xls"):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cleandata",
        description="Clean a CSV/Excel file: trim whitespace, fix types, "
        "drop duplicates, flag outliers, report missing values.",
    )
    parser.add_argument("input", type=Path, help="input CSV or Excel file")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output file (default: <input>.clean.csv)",
    )
    parser.add_argument(
        "-r", "--report", type=Path, default=None,
        help="markdown report path (default: <input>.report.md)",
    )
    parser.add_argument(
        "--fill-missing", choices=["median", "mean", "mode", "ffill"],
        default=None, help="how to fill missing values (default: leave as-is)",
    )
    parser.add_argument(
        "--keep-duplicates", action="store_true",
        help="do not drop exact-duplicate rows",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: {args.input} not found", file=sys.stderr)
        return 1

    df = _read_any(args.input)
    cleaned, report = clean_dataframe(
        df,
        fill_missing=args.fill_missing,
        drop_duplicates=not args.keep_duplicates,
    )

    out_path = args.output or args.input.with_suffix("").with_name(
        args.input.stem + ".clean.csv"
    )
    report_path = args.report or args.input.with_suffix("").with_name(
        args.input.stem + ".report.md"
    )

    _write_any(cleaned, out_path)
    report_path.write_text(report.to_markdown(), encoding="utf-8")

    print(f"rows: {report.rows_in} -> {report.rows_out}")
    print(f"duplicates removed: {report.duplicate_rows_removed}")
    print(f"cleaned data -> {out_path}")
    print(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
