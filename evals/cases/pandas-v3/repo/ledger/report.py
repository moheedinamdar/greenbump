import pandas as pd


def add_row(df, row):
    return df.append(row, ignore_index=True)


def total_by_category(df):
    totals = {}
    for category, amount in df.groupby("category")["amount"].sum().iteritems():
        totals[category] = float(amount)
    return totals


def zero_out_refunds(df):
    df["amount"][df["kind"] == "refund"] = 0
    return df
