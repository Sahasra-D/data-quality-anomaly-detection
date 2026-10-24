
from pathlib import Path
from io import StringIO

import pandas as pd


# --------------------------------------------------
# 1. Locate the project and load the raw dataset
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = PROJECT_ROOT / "data" / "raw" / "transactions_messy.csv"
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_FILE = REPORT_DIR / "data_profile.txt"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_FILE}\n"
        "Run src/generate_data.py first."
    )

df = pd.read_csv(DATA_FILE)

report = []


def add_section(title):
    report.append("\n" + "=" * 60)
    report.append(title)
    report.append("=" * 60)


# --------------------------------------------------
# 2. Basic dataset overview
# --------------------------------------------------

add_section("1. DATASET OVERVIEW")

report.append(f"File: {DATA_FILE.name}")
report.append(f"Number of rows: {df.shape[0]}")
report.append(f"Number of columns: {df.shape[1]}")
report.append(f"Total cells: {df.size}")

report.append("\nColumn names:")
report.append(str(df.columns.tolist()))

report.append("\nFirst five rows:")
report.append(df.head().to_string(index=False))

report.append("\nData types and non-null counts:")

info_buffer = StringIO()
df.info(buf=info_buffer)
report.append(info_buffer.getvalue())


# --------------------------------------------------
# 3. Summary statistics
# --------------------------------------------------

add_section("2. SUMMARY STATISTICS")

report.append(
    df.describe(include="all").to_string()
)


# --------------------------------------------------
# 4. Missing values
# --------------------------------------------------

add_section("3. MISSING VALUE ANALYSIS")

missing = df.isna().sum()

missing_report = pd.DataFrame({
    "missing_count": missing,
    "missing_percentage": (
        missing / len(df) * 100
        if len(df) > 0
        else 0
    )
})

report.append(missing_report.to_string())


# --------------------------------------------------
# 5. Unique values and duplicate rows
# --------------------------------------------------

add_section("4. UNIQUENESS ANALYSIS")

report.append("\nDistinct values per column:")
report.append(df.nunique(dropna=True).to_string())

report.append(
    f"\nFully duplicated rows: {df.duplicated().sum()}"
)

if "transaction_id" in df.columns:
    report.append(
        "\nRepeated transaction_id values, including "
        "all occurrences after the first: "
        f"{df['transaction_id'].duplicated().sum()}"
    )

    report.append(
        "Rows belonging to repeated transaction IDs: "
        f"{df['transaction_id'].duplicated(keep=False).sum()}"
    )


# --------------------------------------------------
# 6. Categorical value distributions
# --------------------------------------------------

add_section("5. CATEGORICAL VALUE DISTRIBUTIONS")

categorical_columns = df.select_dtypes(
    include=["object", "category", "string"]
).columns

for column in categorical_columns:
    report.append(f"\n{column}:")
    report.append(
        df[column].value_counts(
            dropna=False
        ).to_string()
    )


# --------------------------------------------------
# 7. Safe date conversion
# --------------------------------------------------

add_section("6. DATE VALIDATION")

date_columns = [
    column for column in df.columns
    if "date" in column.lower()
]

for column in date_columns:
    original = df[column].copy()

    converted = pd.to_datetime(
        original,
        errors="coerce"
    )

    bad_dates = (
        original.notna()
        & converted.isna()
    )

    report.append(f"\nColumn: {column}")
    report.append(f"Invalid non-null dates: {bad_dates.sum()}")
    report.append(f"Missing dates: {original.isna().sum()}")

    if converted.notna().any():
        report.append(
            f"Earliest valid date: {converted.min()}"
        )
        report.append(
            f"Latest valid date: {converted.max()}"
        )

    # Keep the converted dates in memory for profiling.
    df[column] = converted


# --------------------------------------------------
# 8. Safe numeric conversion
# --------------------------------------------------

add_section("7. NUMERIC VALIDATION")

numeric_candidates = [
    column for column in df.columns
    if any(
        keyword in column.lower()
        for keyword in ["amount", "price", "quantity"]
    )
]

for column in numeric_candidates:
    original = df[column].copy()

    converted = pd.to_numeric(
        original,
        errors="coerce"
    )

    bad_numbers = (
        original.notna()
        & converted.isna()
    )

    report.append(f"\nColumn: {column}")
    report.append(
        f"Invalid non-null numeric values: "
        f"{bad_numbers.sum()}"
    )
    report.append(
        f"Missing numeric values: {original.isna().sum()}"
    )

    # Keep converted numbers in memory for profiling.
    df[column] = converted


# --------------------------------------------------
# 9. Basic data-quality observations
# --------------------------------------------------

add_section("8. INITIAL DATA QUALITY OBSERVATIONS")

report.append(
    "Missing cells across dataset: "
    f"{df.isna().sum().sum()}"
)

report.append(
    "Fully duplicated rows in the original dataset: "
    f"{pd.read_csv(DATA_FILE).duplicated().sum()}"
)

if "amount" in df.columns:
    report.append(
        f"Negative amounts: {(df['amount'] < 0).sum()}"
    )

if "transaction_date" in df.columns:
    future_dates = (
        df["transaction_date"] > pd.Timestamp.today()
    )
    report.append(
        f"Future transaction dates: {future_dates.sum()}"
    )


# --------------------------------------------------
# 10. Print and save the report
# --------------------------------------------------

final_report = "\n".join(report)

print(final_report)

REPORT_FILE.write_text(
    final_report,
    encoding="utf-8"
)

print(f"\n\nProfile saved to: {REPORT_FILE}")
