
import pandas as pd

from src.quality_checks import (
    check_missing,
    check_exact_duplicates,
    check_duplicate_transaction_id,
    check_negative_amount,
)


def test_missing_amount():
    df = pd.DataFrame({
        "transaction_id": [1, 2, 3],
        "amount": [100, None, 200],
    })

    failures = check_missing(df, "amount")
    assert len(failures) == 1


def test_exact_duplicates():
    df = pd.DataFrame({
        "transaction_id": [1, 2, 2],
        "amount": [100, 200, 200],
    })

    failures = check_exact_duplicates(df)
    assert len(failures) == 2


def test_duplicate_transaction_ids():
    df = pd.DataFrame({
        "transaction_id": [1, 2, 2],
        "amount": [100, 200, 300],
    })

    failures = check_duplicate_transaction_id(df)
    assert len(failures) == 2


def test_non_positive_amount():
    df = pd.DataFrame({
        "transaction_id": [1, 2, 3],
        "amount": [100, -50, 200],
    })

    failures = check_negative_amount(df)
    assert len(failures) == 1