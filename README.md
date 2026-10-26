# Data Quality & Anomaly Detection

## Project Overview

A Python-based data quality and anomaly detection project that identifies missing values, duplicate records, invalid data, and unusual transactions. It combines data profiling, rule-based validation, anomaly detection, SQL analysis, and automated reporting to improve data reliability.

## Objectives

- Profile and understand transaction data.
- Identify data quality issues across multiple dimensions.
- Detect unusual transactions using statistical and rule-based methods.
- Evaluate anomaly detection performance using labelled examples.
- Generate Excel and Markdown reports for analysis and review.

## Tech Stack

- **Language:** Python
- **Data Analysis:** Pandas, NumPy
- **Visualization:** Matplotlib
- **Database:** SQLite, SQL
- **Reporting:** OpenPyXL, Markdown
- **Development Tools:** VS Code, Git, GitHub

## Dataset

- **Records:** 51,000 transactions
- **Format:** CSV
- **Location:** `data/raw/transactions_messy.csv`

The dataset contains transaction-related fields such as transaction ID, customer ID, transaction date, amount, currency, and email. It includes labelled data quality issues and anomaly examples for validation and evaluation.

## Project Workflow

### Phase 1: Project Setup
Created the project structure, Python environment, dependencies, and version control setup.

### Phase 2: Dataset Preparation
Prepared the transaction dataset and supporting data for the subsequent analysis pipeline.

### Phase 3: Data Profiling
Analysed dataset structure, data types, missing values, duplicates, numerical distributions, categorical values, and date-related issues.

**Output:** `reports/data_profile.txt`

### Phase 4: Data Quality Validation
Implemented data quality checks across dimensions including completeness, uniqueness, and validity. Generated a summary of failed checks, severity levels, and pass rates.

Examples of identified issues:
- 2,545 records with missing amounts
- 2,143 records with invalid email formats
- 1,535 records with missing customer IDs
- 1,000 records flagged for duplicate transaction IDs

These counts represent individual checks; the same transaction may appear in multiple categories.

**Output:** `reports/quality_check_summary.csv`

### Phase 5: Anomaly Detection
Implemented and evaluated statistical and rule-based anomaly detection methods, including Z-score, IQR, transaction velocity, near-limit amounts, and other transaction patterns.

The combined detector flagged 210 records. Against the 125 labelled anomaly cases used for evaluation, it achieved:

- **Precision:** 57.14%
- **Recall:** 96.00%
- **True positives:** 120
- **False positives:** 90
- **False negatives:** 5

The results demonstrate high recall, while the false positives indicate that flagged records require further review.

### Phase 6: SQL Analysis
Loaded transaction data into SQLite and executed SQL queries to validate data quality, inspect missing values, identify duplicates, and analyse transaction records.

### Phase 7: Automated Reporting
Developed a Python reporting script to generate a formatted Excel workbook, a Markdown report, and a data quality chart.

Generated outputs:

- `reports/data_quality_report.xlsx` — Summary, Missing, Duplicates, Invalid, and Anomalies worksheets.
- `reports/data_quality_report.md` — Overview, quality score, dimension results, top issues, anomaly highlights, recommendations, and limitations.
- `reports/dq_dimension_chart.png` — Data quality failures by dimension.

## Project Structure

```text
Data-Quality-Anomaly-Detection_Project/
├── data/
│   ├── raw/
│   │   └── transactions_messy.csv
│   └── processed/
│       └── transactions_anomaly_flagged.csv
├── src/
│   ├── generate_data.py
│   ├── profile.py
│   ├── dq_checks.py
│   ├── anomaly_rules.py
│   ├── report.py
│   └── main.py
├── sql/
├── reports/
│   ├── data_profile.txt
│   ├── quality_check_summary.csv
│   ├── data_quality_report.xlsx
│   ├── data_quality_report.md
│   └── dq_dimension_chart.png
├── tests/
├── requirements.txt
└── README.md
```

## Installation and Execution

Clone the repository and navigate to the project directory.

Create and activate a virtual environment on Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the final report generator from the project root:

```powershell
.\venv\Scripts\python.exe src\report.py
```

The script reads the existing dataset and outputs from previous phases. Ensure these input files are available before running it.

## Key Outcomes

- Built a multi-stage data quality analysis workflow.
- Identified missing, duplicate, and invalid transaction records.
- Compared anomaly detection methods using labelled examples.
- Used SQL to support data validation and analysis.
- Automated the generation of formatted Excel and Markdown reports.

## Limitations

- Statistical thresholds and anomaly detection rules may require further tuning.
- False positives and false negatives are possible.
- Detected anomalies are not automatically confirmed errors or fraudulent transactions.
- The overall data quality score depends on the checks and calculation method used.

## Future Improvements

- Integrate all row-level validation results into a unified quality score.
- Add an interactive dashboard for exploring data quality metrics.
- Improve anomaly detection through threshold optimisation and additional evaluation.
- Automate report generation and validation through scheduled execution.

## Author

**D. Sahasra**

GitHub: [Sahasra-D](https://github.com/Sahasra-D)

