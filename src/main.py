import logging
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
LOG_FILE = ROOT / "reports" / "pipeline.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
PIPELINE = [
    ("Data profiling", SRC / "profile.py"),
    ("Data quality checks", SRC / "quality_checks.py"),
    ("Anomaly detection", SRC / "anomaly_rules.py"),
    ("SQLite loading", SRC / "load_sqlite.py"),
    ("SQL validation", SRC / "run_sql_checks.py"),
    ("Report generation", SRC / "report.py"),
]


def main():
    logging.info("Starting transaction data quality pipeline")

    for step_name, script_path in PIPELINE:
        if not script_path.exists():
            logging.error("Script not found: %s", script_path)
            raise SystemExit(1)

        logging.info("Starting: %s", step_name)

        try:
            subprocess.run(
                [sys.executable, str(script_path)],
                cwd=ROOT,
                check=True
            )
        except subprocess.CalledProcessError as error:
            logging.error(
                "%s failed with exit code %s",
                step_name,
                error.returncode
            )
            raise SystemExit(error.returncode)

        logging.info("Completed: %s", step_name)

    logging.info("Pipeline completed successfully")
    logging.info("Log saved to: %s", LOG_FILE)


if __name__ == "__main__":
    main()