"""Generate data/employees.csv, a deliberately imperfect HR dataset (no sales columns)."""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 900
dept = rng.choice(["Engineering", "Sales", "Marketing", "Finance", "Operations", "People"], n, p=[.33, .22, .1, .1, .15, .1])
level = rng.choice(["Junior", "Mid", "Senior", "Lead"], n, p=[.3, .35, .25, .1])
city = rng.choice(["Pune", "Bengaluru", "Delhi", "Mumbai", "Hyderabad"], n, p=[.2, .3, .15, .2, .15])
exp = np.round(np.array([max(0.2, rng.normal({"Junior": 1.5, "Mid": 5, "Senior": 9, "Lead": 14}[l], 1.5)) for l in level]), 1)
base = np.array([{"Junior": 4.5, "Mid": 8, "Senior": 14, "Lead": 22}[l] for l in level]) * 100000
bump = np.array([{"Engineering": 1.15, "Sales": 1.0, "Marketing": 0.95, "Finance": 1.05, "Operations": 0.9, "People": 0.92}[d] for d in dept])
salary = np.round(base * bump * rng.normal(1, 0.08, n), -2)
rating = np.clip(np.round(rng.normal(3.4, 0.9, n)), 1, 5).astype(int)
left = (rng.random(n) < (0.28 - 0.04 * rating)).astype(int)
hire = pd.Timestamp("2025-12-31") - pd.to_timedelta((exp * 365 + rng.integers(0, 200, n)).astype(int), unit="D")
df = pd.DataFrame({
    "Employee ID": [f"E{1000 + i}" for i in range(n)], "Department": dept, "Job Level": level, "Location": city,
    "Hire Date": hire, "Years Experience": exp, "Annual Salary": salary, "Performance Rating": rating,
    "Training Hours": np.round(rng.gamma(3, 8, n), 1), "Remote Worker": rng.choice(["Yes", "No"], n, p=[.4, .6]),
    "Left Company": left,
})
fmt = rng.choice(["%Y-%m-%d", "%d %b %Y", "%m/%d/%Y"], n, p=[.7, .2, .1])
df["Hire Date"] = [d.strftime(f) for d, f in zip(df["Hire Date"], fmt)]
df.loc[rng.choice(n, 40, replace=False), "Department"] = "engineering "
df.loc[rng.choice(n, 20, replace=False), "Location"] = np.nan
df.loc[rng.choice(n, 25, replace=False), "Annual Salary"] = np.nan
df.loc[rng.choice(n, 15, replace=False), "Training Hours"] = np.nan
df["Annual Salary"] = df["Annual Salary"].astype(object)
for j in rng.choice(n, 5, replace=False):
    if pd.notna(df.at[j, "Annual Salary"]):
        df.at[j, "Annual Salary"] = f"{df.at[j, 'Annual Salary']:,.0f}"
df = pd.concat([df, df.sample(10, random_state=3)]).sample(frac=1, random_state=4).reset_index(drop=True)
out = Path(__file__).resolve().parents[1] / "data" / "employees.csv"
df.to_csv(out, index=False)
print(f"Wrote {len(df)} rows to {out}")
