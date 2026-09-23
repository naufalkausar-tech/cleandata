"""Core cleaning engine.

Every transformation is logged to a CleaningReport so the process is
reproducible and auditable - nothing happens silently. Outliers are
flagged, never dropped automatically, since that decision belongs to
the person who understands the data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_NUMERIC_CLEAN_RE = re.compile(r"[,$€£%\s]")
_DATE_HINT_RE = re.compile(r"(date|_dt$|^dt_|time)", re.IGNORECASE)


@dataclass
class ColumnAction:
    column: str
    action: str
    detail: str


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    duplicate_rows_removed: int = 0
    missing_before: dict[str, int] = field(default_factory=dict)
    missing_after: dict[str, int] = field(default_factory=dict)
    outliers_flagged: dict[str, int] = field(default_factory=dict)
    actions: list[ColumnAction] = field(default_factory=list)

    def log(self, column: str, action: str, detail: str) -> None:
        self.actions.append(ColumnAction(column, action, detail))

    def to_markdown(self) -> str:
        lines = [
            "# Data Cleaning Report",
            "",
            f"- Rows in: **{self.rows_in}**",
            f"- Rows out: **{self.rows_out}**",
            f"- Duplicate rows removed: **{self.duplicate_rows_removed}**",
            "",
            "## Missing values (before -> after)",
        ]
        cols = sorted(set(self.missing_before) | set(self.missing_after))
        if cols:
            for c in cols:
                lines.append(
                    f"- `{c}`: {self.missing_before.get(c, 0)} -> "
                    f"{self.missing_after.get(c, 0)}"
                )
        else:
            lines.append("- (no columns had missing values)")

        lines.append("")
        lines.append("## Outliers flagged (IQR method, not removed)")
        if self.outliers_flagged:
            for c, n in self.outliers_flagged.items():
                lines.append(f"- `{c}`: {n} row(s) flagged")
        else:
            lines.append("- (none flagged)")

        lines.append("")
        lines.append("## Actions taken")
        if self.actions:
            for a in self.actions:
                lines.append(f"- **{a.column}** — {a.action}: {a.detail}")
        else:
            lines.append("- (no column-level actions were needed)")
        return "\n".join(lines) + "\n"


def _looks_numeric(series: pd.Series, sample: int = 50) -> bool:
    values = series.dropna().astype(str).head(sample)
    if values.empty:
        return False
    cleaned = values.str.replace(_NUMERIC_CLEAN_RE, "", regex=True)
    hits = cleaned.str.match(r"^-?\d+(\.\d+)?$")
    return hits.mean() >= 0.8


def _looks_like_date(col_name: str, series: pd.Series, sample: int = 50) -> bool:
    if not _DATE_HINT_RE.search(col_name):
        return False
    values = series.dropna().astype(str).head(sample)
    if values.empty:
        return False
    parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    return parsed.notna().mean() >= 0.8


def clean_dataframe(
    df: pd.DataFrame,
    *,
    fill_missing: str | None = None,
    drop_duplicates: bool = True,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a DataFrame and return (cleaned_df, report).

    fill_missing: None (leave as-is, just report), "median", "mean",
        "mode", or "ffill". Applied per-column only where it makes sense
        (numeric columns for median/mean, any column for mode/ffill).
    drop_duplicates: remove exact-duplicate rows.
    """
    report = CleaningReport(rows_in=len(df))
    out = df.copy()

    for col in out.select_dtypes(include=["object"]).columns:
        trimmed = out[col].astype(str).str.strip()
        # only touch it if trimming actually changes something and the
        # column isn't entirely NaN dressed up as the string "nan"
        changed = (trimmed != out[col].astype(str)) & out[col].notna()
        if changed.any():
            out[col] = out[col].where(out[col].isna(), trimmed)
            report.log(col, "trim_whitespace", f"{int(changed.sum())} value(s) trimmed")

    if drop_duplicates:
        before = len(out)
        out = out.drop_duplicates()
        removed = before - len(out)
        report.duplicate_rows_removed = removed
        if removed:
            report.log("*", "drop_duplicates", f"{removed} duplicate row(s) removed")

    for col in list(out.columns):
        if out[col].dtype == object and _looks_numeric(out[col]):
            cleaned = (
                out[col]
                .astype(str)
                .str.replace(_NUMERIC_CLEAN_RE, "", regex=True)
            )
            converted = pd.to_numeric(cleaned, errors="coerce")
            newly_null = converted.isna() & out[col].notna()
            out[col] = converted
            detail = "converted to numeric"
            if newly_null.any():
                detail += f" ({int(newly_null.sum())} value(s) could not convert -> NaN)"
            report.log(col, "type_conversion", detail)
        elif out[col].dtype == object and _looks_like_date(col, out[col]):
            converted = pd.to_datetime(out[col], errors="coerce", format="mixed")
            newly_null = converted.isna() & out[col].notna()
            out[col] = converted
            detail = "parsed as datetime"
            if newly_null.any():
                detail += f" ({int(newly_null.sum())} value(s) could not parse -> NaT)"
            report.log(col, "type_conversion", detail)

    for col in out.columns:
        report.missing_before[col] = int(df[col].isna().sum()) if col in df.columns else int(out[col].isna().sum())

    if fill_missing:
        for col in out.columns:
            n_missing = out[col].isna().sum()
            if not n_missing:
                continue
            if fill_missing in ("median", "mean") and pd.api.types.is_numeric_dtype(out[col]):
                value = out[col].median() if fill_missing == "median" else out[col].mean()
                out[col] = out[col].fillna(value)
                report.log(col, "fill_missing", f"{fill_missing}={value:.4g}, {int(n_missing)} value(s) filled")
            elif fill_missing == "mode" and not out[col].mode().empty:
                value = out[col].mode().iloc[0]
                out[col] = out[col].fillna(value)
                report.log(col, "fill_missing", f"mode={value!r}, {int(n_missing)} value(s) filled")
            elif fill_missing == "ffill":
                out[col] = out[col].ffill()
                filled = int(n_missing - out[col].isna().sum())
                report.log(col, "fill_missing", f"forward-fill, {filled} value(s) filled")

    for col in out.columns:
        report.missing_after[col] = int(out[col].isna().sum())

    for col in out.select_dtypes(include=[np.number]).columns:
        series = out[col].dropna()
        if len(series) < 8:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flagged = out[col].apply(lambda v: pd.notna(v) and (v < lower or v > upper))
        n_flagged = int(flagged.sum())
        if n_flagged:
            report.outliers_flagged[col] = n_flagged
            out[f"{col}__outlier"] = flagged

    report.rows_out = len(out)
    return out, report
