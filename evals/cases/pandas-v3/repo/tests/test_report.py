import pandas as pd

from ledger.report import add_row, total_by_category, zero_out_refunds


def sample():
    return pd.DataFrame(
        {
            "category": ["food", "rent", "food"],
            "kind": ["sale", "sale", "refund"],
            "amount": [10.0, 500.0, 4.0],
        }
    )


def test_add_row():
    df = add_row(sample(), {"category": "fuel", "kind": "sale", "amount": 30.0})
    assert len(df) == 4
    assert df.iloc[-1]["category"] == "fuel"
    assert list(df.index) == [0, 1, 2, 3]


def test_total_by_category():
    assert total_by_category(sample()) == {"food": 14.0, "rent": 500.0}


def test_zero_out_refunds():
    df = zero_out_refunds(sample())
    assert df["amount"].tolist() == [10.0, 500.0, 0.0]
