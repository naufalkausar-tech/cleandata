# Data Cleaning Report

- Rows in: **8**
- Rows out: **8**
- Duplicate rows removed: **0**

## Missing values (before -> after)
- `amount`: 1 -> 0
- `customer_name`: 0 -> 0
- `order_date`: 0 -> 0
- `order_id`: 0 -> 0
- `region`: 1 -> 1

## Outliers flagged (IQR method, not removed)
- `amount`: 2 row(s) flagged

## Actions taken
- **customer_name** — trim_whitespace: 2 value(s) trimmed
- **order_date** — trim_whitespace: 1 value(s) trimmed
- **order_date** — type_conversion: parsed as datetime
- **amount** — type_conversion: converted to numeric
- **amount** — fill_missing: median=980, 1 value(s) filled
