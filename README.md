# cleandata

A small, honest CLI + Python library for cleaning messy CSV/Excel data.

It does five things, and logs every single one of them so the process is
reproducible and auditable — nothing happens silently:

- trims stray whitespace from text columns
- drops exact-duplicate rows
- converts numeric-looking strings (`"$1,200.50"`, `"45%"`) to real numbers
- parses date-looking columns into real datetimes
- flags statistical outliers (IQR method) **without removing them** — that
  decision belongs to whoever understands the data, not to a script

Missing values are reported, not silently guessed at, unless you explicitly
ask for a fill strategy.

## Install

```bash
pip install -e .
```

## Use it as a CLI

```bash
cleandata examples/messy_sales.csv --fill-missing median
```

This writes `examples/messy_sales.clean.csv` and
`examples/messy_sales.report.md` next to the input file. See
[`examples/messy_sales.csv`](examples/messy_sales.csv) for a sample input
and [`examples/messy_sales.report.md`](examples/messy_sales.report.md) for
the report it produces.

## Use it as a library

```python
import pandas as pd
from cleandata import clean_dataframe

df = pd.read_csv("raw.csv")
cleaned, report = clean_dataframe(df, fill_missing="median")

cleaned.to_csv("clean.csv", index=False)
print(report.to_markdown())
```

## Why this exists

This is a real, tested (`pytest tests/`, 10/10 passing) example of the kind
of data-cleaning and automation work I do — built to demonstrate the
approach, not as a client deliverable. Happy to build something like this
tailored to your actual data.

## License

MIT
