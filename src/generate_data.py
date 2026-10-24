
import os
import pandas as pd
import numpy as np
from faker import Faker

# --------------------------------------------------
# 1. INITIAL SETUP
# --------------------------------------------------

fake = Faker("en_IN")
rng = np.random.default_rng(42)
Faker.seed(42)

os.makedirs("data/raw", exist_ok=True)

N = 50_000

currencies = ["INR", "USD", "EUR", "GBP"]
payment_methods = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet"]
statuses = ["completed", "pending", "failed", "refunded"]
categories = ["Retail", "Food", "Travel", "Electronics", "Healthcare"]
countries = ["India", "USA", "UK", "Canada", "Australia"]

# --------------------------------------------------
# 2. GENERATE 50,000 CLEAN TRANSACTIONS
# --------------------------------------------------

df = pd.DataFrame({
    "transaction_id": [f"TXN{i:06d}" for i in range(1, N + 1)],
    "customer_id": [
        f"CUST{x:05d}" for x in rng.integers(1, 10001, size=N)
    ],
    "transaction_date": (
        pd.Timestamp("2025-01-01")
        + pd.to_timedelta(
            rng.integers(0, 365, size=N), unit="D"
        )
        + pd.to_timedelta(
            rng.integers(0, 86400, size=N), unit="s"
        )
    ),
    "amount": np.round(
        np.clip(rng.lognormal(mean=6.2, sigma=0.8, size=N), 10, 8000),
        2
    ),
    "currency": rng.choice(
        currencies, size=N, p=[0.75, 0.12, 0.08, 0.05]
    ),
    "payment_method": rng.choice(payment_methods, size=N),
    "status": rng.choice(
        statuses, size=N, p=[0.80, 0.10, 0.07, 0.03]
    ),
    "merchant_category": rng.choice(categories, size=N),
    "country": rng.choice(
        countries, size=N, p=[0.75, 0.10, 0.06, 0.05, 0.04]
    ),
    "email": [fake.email() for _ in range(N)]
})

df["transaction_date"] = pd.to_datetime(df["transaction_date"])

print("Clean dataset generated:", df.shape)

# --------------------------------------------------
# 3. CREATE GROUND-TRUTH LOG
# --------------------------------------------------

ground_truth = []

def record_issue(row_index, issue_type, details):
    """Record a deliberately injected problem."""
    ground_truth.append({
        "row_number": int(row_index) + 1,
        "transaction_id": str(df.at[row_index, "transaction_id"]),
        "issue_type": issue_type,
        "details": details
    })

# --------------------------------------------------
# 4. INJECT MISSING VALUES
# --------------------------------------------------

def inject_missing(column, percentage):
    count = int(N * percentage)
    selected = rng.choice(df.index.to_numpy(), size=count, replace=False)

    for idx in selected:
        df.at[idx, column] = np.nan
        record_issue(idx, "missing_value", f"{column} is missing")

inject_missing("amount", 0.05)
inject_missing("customer_id", 0.03)
inject_missing("email", 0.04)

print("Missing values injected.")

# --------------------------------------------------
# 5. INJECT DUPLICATES
# --------------------------------------------------

duplicate_count = int(N * 0.02)
exact_count = duplicate_count // 2
near_count = duplicate_count - exact_count

# Exact duplicate rows: same transaction ID and all same values
exact_sources = rng.choice(
    np.arange(N), size=exact_count, replace=False
)
exact_copies = df.iloc[exact_sources].copy()

df = pd.concat([df, exact_copies], ignore_index=True)

for idx in range(N, N + exact_count):
    record_issue(idx, "exact_duplicate", "Exact copy of an existing row")

# Near duplicates: same customer, date and amount, but new transaction ID
near_sources = rng.choice(
    np.arange(N), size=near_count, replace=False
)
near_copies = df.iloc[near_sources].copy()

start_idx = len(df)
near_copies["transaction_id"] = [
    f"DUP{i:06d}" for i in range(1, near_count + 1)
]

df = pd.concat([df, near_copies], ignore_index=True)

for idx in range(start_idx, len(df)):
    record_issue(
        idx,
        "near_duplicate",
        "New transaction ID but copied customer, date and amount"
    )

print("Duplicate records injected.")

# --------------------------------------------------
# 6. INJECT INVALID ENTRIES
# --------------------------------------------------

def choose_rows(count):
    return rng.choice(df.index.to_numpy(), size=count, replace=False)

# Negative transaction amounts
for idx in choose_rows(100):
    df.at[idx, "amount"] = -abs(float(rng.uniform(10, 5000)))
    record_issue(idx, "negative_amount", "Amount is below zero")

# Future transaction dates
for idx in choose_rows(100):
    df.at[idx, "transaction_date"] = (
        pd.Timestamp.now().normalize()
        + pd.Timedelta(days=int(rng.integers(1, 91)))
    )
    record_issue(idx, "future_date", "Transaction date is in the future")

# Misspelled statuses
for idx in choose_rows(100):
    df.at[idx, "status"] = "compleeted"
    record_issue(idx, "invalid_status", "Unrecognized status: compleeted")

# Invalid email addresses
for idx in choose_rows(100):
    df.at[idx, "email"] = "invalid-email-address"
    record_issue(idx, "invalid_email", "Email does not contain @")

# Unsupported currency
for idx in choose_rows(100):
    df.at[idx, "currency"] = "XYZ"
    record_issue(idx, "invalid_currency", "Unsupported currency: XYZ")

print("Invalid entries injected.")

# --------------------------------------------------
# 7. INJECT UNUSUALLY LARGE TRANSACTIONS
# --------------------------------------------------

for idx in choose_rows(10):
    df.at[idx, "amount"] = 900000.00
    record_issue(
        idx, "high_amount_anomaly",
        "Unusually large transaction: 900000"
    )

# --------------------------------------------------
# 8. INJECT RAPID TRANSACTIONS FROM ONE CUSTOMER
# --------------------------------------------------

burst_indices = rng.choice(df.index.to_numpy(), size=15, replace=False)

burst_start = pd.Timestamp("2025-06-15 12:00:00")
burst_customer = "CUST_BURST_001"

for position, idx in enumerate(burst_indices):
    df.at[idx, "customer_id"] = burst_customer
    df.at[idx, "transaction_date"] = (
        burst_start + pd.Timedelta(seconds=position * 8)
    )
    record_issue(
        idx, "rapid_transaction_burst",
        "Part of 15 transactions by one customer within 2 minutes"
    )

# --------------------------------------------------
# 9. INJECT REPEATED AMOUNTS JUST BELOW A LIMIT
# --------------------------------------------------

for idx in choose_rows(100):
    df.at[idx, "amount"] = round(
        float(rng.uniform(9990, 9999)), 2
    )
    record_issue(
        idx, "threshold_amount_pattern",
        "Amount is unusually close to the 10000 limit"
    )

# --------------------------------------------------
# 10. SAVE OUTPUT FILES
# --------------------------------------------------

# Save transaction row positions before writing.
df.to_csv("data/raw/transactions_messy.csv", index=False)

ground_truth_df = pd.DataFrame(
    ground_truth,
    columns=["row_number", "transaction_id", "issue_type", "details"]
)

ground_truth_df.to_csv(
    "data/raw/ground_truth.csv", index=False
)

# --------------------------------------------------
# 11. DISPLAY VALIDATION SUMMARY
# --------------------------------------------------

print("\n========== DATA GENERATION SUMMARY ==========")
print("Total rows:", len(df))
print("Total columns:", len(df.columns))
print("Expected columns:", list(df.columns))
print("Ground-truth issue records:", len(ground_truth_df))
print("\nMissing values by column:")
print(df.isnull().sum())
print("\nInjected issues by type:")
print(ground_truth_df["issue_type"].value_counts())
print("\nFiles saved successfully:")
print("1. data/raw/transactions_messy.csv")
print("2. data/raw/ground_truth.csv")
