import numpy as np
import pandas as pd
import pytest

from cleandata.core import clean_dataframe


def test_trims_whitespace():
    df = pd.DataFrame({"name": [" Alice ", "Bob", "  Carol"]})
    out, report = clean_dataframe(df)
    assert list(out["name"]) == ["Alice", "Bob", "Carol"]
    assert any(a.action == "trim_whitespace" for a in report.actions)


def test_drops_exact_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    out, report = clean_dataframe(df)
    assert len(out) == 2
    assert report.duplicate_rows_removed == 1


def test_keep_duplicates_flag():
    df = pd.DataFrame({"a": [1, 1, 2]})
    out, report = clean_dataframe(df, drop_duplicates=False)
    assert len(out) == 3
    assert report.duplicate_rows_removed == 0


def test_numeric_string_conversion():
    df = pd.DataFrame({"price": ["$1,200.50", "$3,000", "$45.00"]})
    out, report = clean_dataframe(df)
    assert pd.api.types.is_numeric_dtype(out["price"])
    assert out["price"].iloc[0] == pytest.approx(1200.50)
    assert any(a.action == "type_conversion" for a in report.actions)


def test_date_column_parsed():
    df = pd.DataFrame({"order_date": ["2026-01-05", "2026-02-14", "2026-03-01"]})
    out, report = clean_dataframe(df)
    assert pd.api.types.is_datetime64_any_dtype(out["order_date"])


def test_missing_value_counts_reported():
    df = pd.DataFrame({"id": [1, 2, 3, 4], "a": [1, None, 3, None]})
    _, report = clean_dataframe(df)
    assert report.missing_before["a"] == 2
    assert report.missing_after["a"] == 2  # no fill requested


def test_fill_missing_median():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0]})
    out, report = clean_dataframe(df, fill_missing="median")
    assert out["a"].isna().sum() == 0
    assert report.missing_after["a"] == 0


def test_outliers_flagged_not_removed():
    df = pd.DataFrame({
        "id": range(8),
        "value": [10, 11, 9, 10, 12, 11, 10, 500],
    })
    out, report = clean_dataframe(df)
    assert len(out) == 8  # nothing dropped
    assert "value" in report.outliers_flagged
    assert report.outliers_flagged["value"] == 1
    assert out["value__outlier"].sum() == 1


def test_report_to_markdown_contains_summary():
    df = pd.DataFrame({"a": [1, 1, None]})
    _, report = clean_dataframe(df)
    md = report.to_markdown()
    assert "# Data Cleaning Report" in md
    assert "Duplicate rows removed" in md


def test_empty_dataframe_does_not_crash():
    df = pd.DataFrame({"a": [], "b": []})
    out, report = clean_dataframe(df)
    assert len(out) == 0
    assert report.rows_in == 0
