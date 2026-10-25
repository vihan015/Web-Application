"""Generate data/retail_orders.csv, a deliberately imperfect retail dataset."""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

CATALOG = {
    "Furniture": {"Chairs": (180, 0.10), "Tables": (420, 0.02), "Bookcases": (260, 0.06), "Furnishings": (60, 0.14)},
    "Office Supplies": {"Paper": (25, 0.30), "Binders": (40, 0.22), "Storage": (90, 0.12), "Art": (18, 0.25)},
    "Technology": {"Phones": (380, 0.17), "Accessories": (55, 0.24), "Machines": (900, 0.08), "Copiers": (1500, 0.28)},
}
REGIONS = ["West", "East", "Central", "South"]
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SHIP = ["Standard Class", "Second Class", "First Class", "Same Day"]

month_w = np.array([0.7, 0.7, 0.9, 0.9, 1.0, 1.0, 0.9, 1.0, 1.3, 1.1, 1.5, 1.7])
days = pd.date_range("2023-01-01", "2025-12-31")
w = np.asarray(month_w[days.month - 1] * (1 + 0.25 * (days.year - 2023)), dtype=float)
days_p = w / w.sum()

rows = []
for i in range(1, 1101):
    oid = f"US-{rng.choice([2023, 2024, 2025])}-{100000 + i}"
    date = rng.choice(days, p=days_p)
    region, segment, ship = rng.choice(REGIONS), rng.choice(SEGMENTS), rng.choice(SHIP, p=[.6, .2, .15, .05])
    customer = f"CU-{rng.integers(1, 450):04d}"
    for _ in range(rng.integers(1, 5)):
        cat = rng.choice(list(CATALOG))
        sub = rng.choice(list(CATALOG[cat]))
        price, margin = CATALOG[cat][sub]
        qty = int(rng.integers(1, 9))
        disc = float(rng.choice([0, 0, 0, 0.1, 0.2, 0.3, 0.4]))
        sales = round(price * rng.uniform(0.8, 1.25) * qty * (1 - disc), 2)
        profit = round(sales * (margin - disc * 0.7 + rng.normal(0, 0.04)), 2)
        rows.append([oid, date, ship, segment, region, customer, cat, sub, sales, qty, disc, profit])

df = pd.DataFrame(rows, columns=["Order ID", "Order Date", "Ship Mode", "Segment", "Region", "Customer ID",
                                 "Category", "Sub-Category", "Sales", "Quantity", "Discount", "Profit"])

# Introduce realistic problems for the cleaning pipeline to handle.
fmt = rng.choice(["%Y-%m-%d", "%d %b %Y", "%m/%d/%Y"], size=len(df), p=[.7, .2, .1])
df["Order Date"] = [pd.Timestamp(d).strftime(f) for d, f in zip(df["Order Date"], fmt)]
idx = rng.choice(len(df), 60, replace=False)
df.loc[idx[:30], "Region"] = df.loc[idx[:30], "Region"].str.lower()
df.loc[idx[30:45], "Region"] = df.loc[idx[30:45], "Region"].str.upper() + " "
df.loc[rng.choice(len(df), 25, replace=False), "Segment"] = np.nan
df.loc[rng.choice(len(df), 20, replace=False), "Discount"] = np.nan
df.loc[rng.choice(len(df), 8, replace=False), "Profit"] = np.nan
df["Sales"] = df["Sales"].astype(object)
for j in rng.choice(len(df), 4, replace=False):
    df.at[j, "Sales"] = f"${df.at[j, 'Sales']:,.2f}"
df = pd.concat([df, df.sample(14, random_state=1)]).sample(frac=1, random_state=2).reset_index(drop=True)

out = Path(__file__).resolve().parents[1] / "data" / "retail_orders.csv"
df.to_csv(out, index=False)
print(f"Wrote {len(df)} rows to {out}")
