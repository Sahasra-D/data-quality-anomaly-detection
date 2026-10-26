

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


# --------------------------------------------------
# 1. LOAD AND PREPARE DATA
# --------------------------------------------------

df = pd.read_csv(DATA_FILE).reset_index(drop=True)

required_columns = {
    "transaction_id",
    "customer_id",
    "amount",
    "transaction_date",
    "merchant_category",
}

missing_columns = required_columns - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Input dataset is missing columns: {sorted(missing_columns)}"
    )

df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

df["transaction_date"] = pd.to_datetime(
    df["transaction_date"], errors="coerce"
)

amount = df["amount"]


# --------------------------------------------------
# 2. Z-SCORE DETECTION
# --------------------------------------------------

mean = amount.mean()
std = amount.std()

if pd.notna(std) and std > 0:
    df["z_score"] = (amount - mean) / std
else:
    df["z_score"] = 0.0

for threshold in [2.5, 3.0, 4.0]:
    col = str(threshold).replace(".", "_")
    df[f"z_flag_{col}"] = df["z_score"].abs() > threshold


# --------------------------------------------------
# 3. IQR OUTLIER DETECTION
# Retained for analysis, but not used in the final
# combined prediction until further refinement.
# --------------------------------------------------

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


# --------------------------------------------------
# 4. MERCHANT-CATEGORY GROUP OUTLIERS
# --------------------------------------------------

group = df.groupby("merchant_category")["amount"]

group_mean = group.transform("mean")
group_std = group.transform("std").replace(0, np.nan)

df["group_z"] = (
    (amount - group_mean) / group_std
).fillna(0)

df["group_flag"] = df["group_z"].abs() > 3


# --------------------------------------------------
# 5. TRANSACTION VELOCITY RULE
# Flag transactions when a customer has more than
# five transactions in a rolling 10-minute window.
# --------------------------------------------------

df["velocity_flag"] = False

valid = df[
    df["customer_id"].notna()
    & df["transaction_date"].notna()
].copy()

for _, customer_df in valid.groupby("customer_id"):

    times = customer_df.sort_values("transaction_date").copy()

    rolling_counts = (
        times.assign(_event=1)
        .set_index("transaction_date")["_event"]
        .rolling(
            "10min",
            closed="both",
            min_periods=1
        )
        .sum()
        .to_numpy()
    )

    flagged_indices = times.index[rolling_counts > 5]

    df.loc[flagged_indices, "velocity_flag"] = True


# --------------------------------------------------
# 6. ADDITIONAL BUSINESS RULES
# --------------------------------------------------

# Transactions close to a possible transaction limit.
df["near_limit_flag"] = amount.between(
    9500, 9999, inclusive="both"
)

# Round amounts of 1,000 or more.
df["round_amount_flag"] = (
    amount.ge(1000)
    & np.isclose(amount.fillna(0) % 1000, 0)
)

# Retained for analysis, but excluded from the final
# combined prediction because the time alone is not
# sufficient evidence of an anomaly.
df["late_night_flag"] = (
    df["transaction_date"].dt.hour == 3
)

# First recorded transaction for a customer has an
# unusually high amount relative to the full dataset.
df["first_transaction_flag"] = False

valid = df[
    df["customer_id"].notna()
    & df["transaction_date"].notna()
].sort_values("transaction_date")

first_rows = valid.drop_duplicates(
    subset="customer_id",
    keep="first"
)

large_amount_cutoff = amount.quantile(0.99)

first_large_indices = first_rows.index[
    first_rows["amount"] > large_amount_cutoff
]

df.loc[first_large_indices, "first_transaction_flag"] = True


# --------------------------------------------------
# 7. COMBINE SELECTED NON-Z-SCORE RULES
# IQR and late-night rules are excluded from this
# combined prediction but retained in the output.
# --------------------------------------------------

base_rule_columns = [
    "group_flag",
    "velocity_flag",
    "near_limit_flag",
    "round_amount_flag",
    "first_transaction_flag",
]

df["other_rules_flag"] = df[base_rule_columns].any(axis=1)


# --------------------------------------------------
# 8. LOAD AND VALIDATE GROUND TRUTH
# --------------------------------------------------

truth = pd.read_csv(GROUND_TRUTH_FILE)

if "row_number" not in truth.columns or "issue_type" not in truth.columns:
    raise ValueError(
        "ground_truth.csv must contain row_number and issue_type."
    )

truth["row_number"] = pd.to_numeric(
    truth["row_number"], errors="coerce"
)

truth = truth.dropna(subset=["row_number"]).copy()

if not (
    truth["row_number"] == truth["row_number"].astype(int)
).all():
    raise ValueError(
        "Ground-truth row numbers must be integers."
    )

truth["row_number"] = truth["row_number"].astype(int)

if not truth["row_number"].between(1, len(df)).all():
    raise ValueError(
        "Some ground-truth row numbers are outside the input dataset."
    )

truth["issue_type"] = (
    truth["issue_type"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# Convert 1-based ground-truth row numbers to zero-based
# DataFrame indices.
all_issue_rows = truth["row_number"].unique() - 1

# Only these three labels count as anomaly-related
# ground truth for the anomaly-detection evaluation.
anomaly_types = {
    "high_amount_anomaly",
    "rapid_transaction_burst",
    "threshold_amount_pattern",
}

anomaly_rows = (
    truth.loc[
        truth["issue_type"].isin(anomaly_types),
        "row_number"
    ].unique() - 1
)

# Target 1: rows with any of the 11 data-quality issue types.
df["ground_truth_issue_flag"] = False
df.loc[all_issue_rows, "ground_truth_issue_flag"] = True

# Target 2: rows with at least one of the three
# anomaly-related issue types.
df["ground_truth_anomaly_flag"] = False
df.loc[anomaly_rows, "ground_truth_anomaly_flag"] = True

# Compatibility alias for older code.
df["ground_truth_flag"] = df["ground_truth_anomaly_flag"]


# --------------------------------------------------
# 9. EVALUATION METRICS
# --------------------------------------------------

def calculate_metrics(predicted, actual):
    predicted = np.asarray(predicted, dtype=bool)
    actual = np.asarray(actual, dtype=bool)

    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    return tp, fp, fn, precision, recall


# Compare Z-score-only detection with the selected
# combined rules at all three Z-score thresholds.
metrics = []

for threshold in [2.5, 3.0, 4.0]:

    col = str(threshold).replace(".", "_")

    z_only = df[f"z_flag_{col}"]
    combined = z_only | df["other_rules_flag"]

    for method, predicted in [
        ("z_score_only", z_only),
        ("combined_rules", combined),
    ]:

        tp, fp, fn, precision, recall = calculate_metrics(
            predicted,
            df["ground_truth_anomaly_flag"]
        )

        metrics.append({
            "z_threshold": threshold,
            "method": method,
            "flagged_rows": int(predicted.sum()),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision_percent": round(precision * 100, 2),
            "recall_percent": round(recall * 100, 2),
        })

metrics_df = pd.DataFrame(metrics)


# Final detector uses Z-score threshold 3.0 plus selected rules.
df["anomaly_flag"] = (
    df["z_flag_3_0"] | df["other_rules_flag"]
)


# --------------------------------------------------
# 10. SAVE OUTPUT DATA AND REPORTS
# --------------------------------------------------

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
        "Rows with any ground-truth data-quality issue: "
        f"{int(df['ground_truth_issue_flag'].sum())}\n"
    )
    file.write(
        "Rows with anomaly-related ground-truth labels: "
        f"{int(df['ground_truth_anomaly_flag'].sum())}\n"
    )
    file.write(
        "Rows flagged by the final detector: "
        f"{int(df['anomaly_flag'].sum())}\n\n"
    )

    file.write("FLAGS BY RULE\n")

    for column in rule_columns:
        file.write(
            f"{column}: {int(df[column].sum())}\n"
        )

    file.write("\nTHRESHOLD COMPARISON\n")
    file.write(metrics_df.to_string(index=False))
    file.write("\n")


# --------------------------------------------------
# 11. PRINT RESULTS
# --------------------------------------------------

print("Phase 5 anomaly detection completed.")
print(f"Rows analyzed: {len(df)}")

print(
    "Rows with any data-quality issue: "
    f"{int(df['ground_truth_issue_flag'].sum())}"
)

print(
    "Rows with anomaly-related ground truth: "
    f"{int(df['ground_truth_anomaly_flag'].sum())}"
)

print(f"Rows flagged by detector: {int(df['anomaly_flag'].sum())}")

print("\nThreshold comparison:")
print(metrics_df.to_string(index=False))

print("\nSaved files:")
print(OUTPUT_DIR / "transactions_anomaly_flagged.csv")
print(REPORT_DIR / "anomaly_threshold_comparison.csv")
print(REPORT_DIR / "anomaly_detection_summary.txt")
print("\nANOMALY LABEL COUNTS")
print(
    truth[truth["issue_type"].isin([
        "high_amount_anomaly",
        "rapid_transaction_burst",
        "threshold_amount_pattern"
    ])]["issue_type"].value_counts().to_string()
)

print("\nTRUE POSITIVES BY RULE")
rule_columns = [
    "z_flag_3_0",
    "group_flag",
    "velocity_flag",
    "near_limit_flag",
    "round_amount_flag",
    "first_transaction_flag"
]

for column in rule_columns:
    true_positives = int(
        (df[column] & df["ground_truth_anomaly_flag"]).sum()
    )
    print(f"{column}: {true_positives}")

print("\nVELOCITY FLAGS:", int(df["velocity_flag"].sum()))
print("FINAL FLAGGED:", int(df["anomaly_flag"].sum()))