
import pandas as pd
from pathlib import Path

def check_missing(df, col):
    return df[df[col].isna()]


def check_exact_duplicates(df):
    return df[df.duplicated(keep=False)]


def check_duplicate_transaction_id(df):
    return df[df.duplicated(
        subset="transaction_id", keep=False
    )]


def check_negative_amount(df):
    return df[df["amount"] <= 0]


def check_future_dates(df):
    today = pd.Timestamp.today().normalize()
    return df[df["transaction_date"] > today]


def check_email_format(df):
    pattern = r"^[\w.-]+@[\w.-]+\.\w+$"
    return df[
        ~df["email"].fillna("").str.match(pattern)
    ]


def check_allowed_values(df, col, allowed):
    invalid = df[col].notna() & ~df[col].isin(allowed)
    return df[invalid]

ALLOWED_CURRENCY = ["INR", "USD", "EUR", "GBP"]

ALLOWED_PAYMENT_METHODS = [
    "UPI", "Credit Card", "Debit Card",
    "Net Banking", "Wallet"
]

ALLOWED_STATUSES = [
    "completed", "pending", "failed", "refunded"
]

ALLOWED_MERCHANT_CATEGORIES = [
    "Retail", "Food", "Travel",
    "Electronics", "Healthcare"
]

ALLOWED_COUNTRIES = [
    "India", "USA", "UK", "Canada", "Australia"
]

CHECKS = [
    {
        "name": "Missing transaction ID",
        "dimension": "Completeness",
        "severity": "High",
        "fn": lambda d: check_missing(d, "transaction_id")
    },
    {
        "name": "Missing customer ID",
        "dimension": "Completeness",
        "severity": "Medium",
        "fn": lambda d: check_missing(d, "customer_id")
    },
    {
        "name": "Missing amount",
        "dimension": "Completeness",
        "severity": "High",
        "fn": lambda d: check_missing(d, "amount")
    },
    {
        "name": "Missing email",
        "dimension": "Completeness",
        "severity": "Low",
        "fn": lambda d: check_missing(d, "email")
    },
    {
        "name": "Exact duplicates",
        "dimension": "Uniqueness",
        "severity": "Medium",
        "fn": check_exact_duplicates
    },
    {
        "name": "Duplicate transaction IDs",
        "dimension": "Uniqueness",
        "severity": "High",
        "fn": check_duplicate_transaction_id
    },
    {
        "name": "Non-positive amount",
        "dimension": "Validity",
        "severity": "High",
        "fn": check_negative_amount
    },
    {
        "name": "Future transaction dates",
        "dimension": "Validity",
        "severity": "Medium",
        "fn": check_future_dates
    },
    {
        "name": "Invalid email format",
        "dimension": "Validity",
        "severity": "Low",
        "fn": check_email_format
    },
    {
        "name": "Invalid currency",
        "dimension": "Validity",
        "severity": "Medium",
        "fn": lambda d: check_allowed_values(
            d, "currency", ALLOWED_CURRENCY
        )
    },
    {
        "name": "Invalid payment method",
        "dimension": "Validity",
        "severity": "Medium",
        "fn": lambda d: check_allowed_values(
            d, "payment_method", ALLOWED_PAYMENT_METHODS
        )
    },
    {
        "name": "Invalid status",
        "dimension": "Validity",
        "severity": "Medium",
        "fn": lambda d: check_allowed_values(
            d, "status", ALLOWED_STATUSES
        )
    },
    {
        "name": "Invalid merchant category",
        "dimension": "Validity",
        "severity": "Medium",
        "fn": lambda d: check_allowed_values(
            d, "merchant_category",
            ALLOWED_MERCHANT_CATEGORIES
        )
    },
    {
        "name": "Invalid country",
        "dimension": "Validity",
        "severity": "Low",
        "fn": lambda d: check_allowed_values(
            d, "country", ALLOWED_COUNTRIES
        )
    }
]


# 4. RUN ALL CHECKS AND SAVE RESULTS

def run_checks():
    project_root = Path(__file__).resolve().parent.parent

    input_file = (
        project_root / "data" / "raw"
        / "transactions_messy.csv"
    )

    df = pd.read_csv(input_file)

    df["amount"] = pd.to_numeric(
        df["amount"], errors="coerce"
    )

    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], errors="coerce"
    )

    processed_dir = project_root / "data" / "processed"
    reports_dir = project_root / "reports"

    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for check in CHECKS:
        failed_rows = check["fn"](df)

        total_rows = len(df)
        failed_count = len(failed_rows)
        passed_count = total_rows - failed_count

        results.append({
            "check_name": check["name"],
            "dimension": check["dimension"],
            "severity": check["severity"],
            "total_rows": total_rows,
            "failed_rows": failed_count,
            "pass_rows": passed_count,
            "pass_rate_percent": round(
                passed_count / total_rows * 100, 2
            ) if total_rows else 0
        })

        filename = (
            check["name"].lower().replace(" ", "_") + ".csv"
        )

        failed_rows.to_csv(
            processed_dir / filename,
            index=False
        )

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        reports_dir / "quality_check_summary.csv",
        index=False
    )

    print("\nDATA QUALITY CHECK RESULTS")
    print("=" * 90)
    print(results_df.to_string(index=False))
    print("\nTotal input rows:", len(df))
    print("Checks executed:", len(CHECKS))
    print("Summary saved to:", reports_dir / "quality_check_summary.csv")
    print("Failed rows saved in:", processed_dir)


if __name__ == "__main__":
    run_checks()
