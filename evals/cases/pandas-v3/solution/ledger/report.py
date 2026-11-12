import pandas as pd


def add_row(df, row):
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)


def total_by_category(df):
    totals = {}
    for category, amount in df.groupby("category")["amount"].sum().items():
        totals[category] = float(amount)
    return totals


def zero_out_refunds(df):
    df.loc[df["kind"] == "refund", "amount"] = 0
    return df
