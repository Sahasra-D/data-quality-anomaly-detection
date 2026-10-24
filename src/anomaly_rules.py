
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "raw" / "transactions_messy.csv"
GROUND_TRUTH_FILE = ROOT / "data" / "raw" / "ground_truth.csv"
OUTPUT_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE).reset_index(drop=True)

df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
df["transaction_date"] = pd.to_datetime(
    df["transaction_date"], errors="coerce"
)

amount = df["amount"]

mean = amount.mean()
std = amount.std()

if pd.notna(std) and std > 0:
    df["z_score"] = (amount - mean) / std
else:
    df["z_score"] = 0.0

for threshold in [2.5, 3.0, 4.0]:
    col = str(threshold).replace(".", "_")
    df[f"z_flag_{col}"] = df["z_score"].abs() > threshold

q1 = amount.quantile(0.25)
q3 = amount.quantile(0.75)
iqr = q3 - q1

if pd.notna(iqr) and iqr > 0:
    df["iqr_flag"] = (
        (amount < q1 - 1.5 * iqr)
        | (amount > q3 + 1.5 * iqr)
    )
else:
    df["iqr_flag"] = False

group = df.groupby("merchant_category")["amount"]
group_mean = group.transform("mean")
group_std = group.transform("std").replace(0, np.nan)

df["group_z"] = (
    (amount - group_mean) / group_std
).fillna(0)

df["group_flag"] = df["group_z"].abs() > 3

df["velocity_flag"] = False

valid = df[
    df["customer_id"].notna()
    & df["transaction_date"].notna()
].copy()

for _, customer_df in valid.groupby("customer_id"):
    times = customer_df.set_index("transaction_date").sort_index()

    counts = times["transaction_id"].rolling(
        "10min", min_periods=1
    ).count()

    flagged_times = counts.index[counts > 5]

    if len(flagged_times):
        flagged_rows = customer_df.index[
            customer_df["transaction_date"].isin(flagged_times)
        ]
        df.loc[flagged_rows, "velocity_flag"] = True

df["near_limit_flag"] = amount.between(
    9500, 9999, inclusive="both"
)

df["round_amount_flag"] = (
    amount.ge(1000)
    & np.isclose(amount.fillna(0) % 1000, 0)
)

df["late_night_flag"] = (
    df["transaction_date"].dt.hour == 3
)

df["first_transaction_flag"] = False

valid = df[
    df["customer_id"].notna()
    & df["transaction_date"].notna()
].sort_values("transaction_date")

first_rows = valid.drop_duplicates(
    subset="customer_id", keep="first"
)

large_amount_cutoff = amount.quantile(0.99)

first_large_indices = first_rows.index[
    first_rows["amount"] > large_amount_cutoff
]

df.loc[first_large_indices, "first_transaction_flag"] = True

base_rule_columns = [
    "iqr_flag",
    "group_flag",
    "velocity_flag",
    "near_limit_flag",
    "round_amount_flag",
    "late_night_flag",
    "first_transaction_flag",
]

df["other_rules_flag"] = df[base_rule_columns].any(axis=1)

truth = pd.read_csv(GROUND_TRUTH_FILE)

if "row_number" not in truth.columns:
    raise ValueError("ground_truth.csv must contain row_number.")

truth_rows = pd.to_numeric(
    truth["row_number"], errors="coerce"
).dropna()

if not np.all(truth_rows == np.floor(truth_rows)):
    raise ValueError("Ground-truth row numbers must be integers.")

truth_rows = truth_rows.astype(int)

if not truth_rows.between(1, len(df)).all():
    raise ValueError(
        "Some ground-truth row numbers are outside the input dataset."
    )

df["ground_truth_flag"] = False
df.loc[truth_rows.unique() - 1, "ground_truth_flag"] = True


def calculate_metrics(predicted, actual):
    predicted = np.asarray(predicted, dtype=bool)
    actual = np.asarray(actual, dtype=bool)

    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    return tp, fp, fn, precision, recall


metrics = []

for threshold in [2.5, 3.0, 4.0]:
    col = str(threshold).replace(".", "_")

    predicted = (
        df[f"z_flag_{col}"] | df["other_rules_flag"]
    )

    tp, fp, fn, precision, recall = calculate_metrics(
        predicted, df["ground_truth_flag"]
    )

    metrics.append({
        "z_threshold": threshold,
        "flagged_rows": int(predicted.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision_percent": round(precision * 100, 2),
        "recall_percent": round(recall * 100, 2),
    })

metrics_df = pd.DataFrame(metrics)

df["anomaly_flag"] = (
    df["z_flag_3_0"] | df["other_rules_flag"]
)

df.to_csv(
    OUTPUT_DIR / "transactions_anomaly_flagged.csv",
    index=False
)

metrics_df.to_csv(
    REPORT_DIR / "anomaly_threshold_comparison.csv",
    index=False
)

rule_columns = [
    "z_flag_3_0",
    "iqr_flag",
    "group_flag",
    "velocity_flag",
    "near_limit_flag",
    "round_amount_flag",
    "late_night_flag",
    "first_transaction_flag",
]

with open(
    REPORT_DIR / "anomaly_detection_summary.txt",
    "w",
    encoding="utf-8"
) as file:
    file.write("ANOMALY DETECTION SUMMARY\n")
    file.write("=" * 35 + "\n\n")
    file.write(f"Total rows analyzed: {len(df)}\n")
    file.write(
        f"Rows flagged at threshold 3.0: "
        f"{int(df['anomaly_flag'].sum())}\n\n"
    )

    file.write("FLAGS BY RULE\n")

    for column in rule_columns:
        file.write(f"{column}: {int(df[column].sum())}\n")

    file.write("\nTHRESHOLD COMPARISON\n")
    file.write(metrics_df.to_string(index=False))
    file.write("\n")

print("Phase 5 anomaly detection completed.")
print(f"Rows analyzed: {len(df)}")
print(f"Rows flagged: {int(df['anomaly_flag'].sum())}")
print("\nThreshold comparison:")
print(metrics_df.to_string(index=False))
print("\nSaved files:")
print(OUTPUT_DIR / "transactions_anomaly_flagged.csv")
print(REPORT_DIR / "anomaly_threshold_comparison.csv")
print(REPORT_DIR / "anomaly_detection_summary.txt")

