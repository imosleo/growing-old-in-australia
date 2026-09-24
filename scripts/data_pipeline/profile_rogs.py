"""Profile the RoGS aged care dataset: what measures, years and breakdowns exist."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 95)

df = pd.read_csv(r"raw\rogs2026_agedcare_dataset.csv", dtype=str, low_memory=False)
print("ROWS:", len(df))
print("YEARS:", sorted(df["Year"].dropna().unique()))
print()

print("=== MEASURES (with year span and row count) ===")
g = df.groupby("Measure").agg(
    rows=("Year", "size"),
    y_min=("Year", "min"),
    y_max=("Year", "max"),
    n_years=("Year", "nunique"),
)
for name, r in g.sort_values("rows", ascending=False).iterrows():
    print("  [%4d rows | %s-%s | %2d yrs] %s" % (r["rows"], r["y_min"], r["y_max"], r["n_years"], name[:110]))

print()
print("=== SERVICE TYPES ===")
for v in sorted(df["Service_Type"].dropna().unique()):
    print("  ", v[:100])

print()
print("=== AGE VALUES ===")
for v in sorted(df["Age"].dropna().unique()):
    print("  ", v[:70])

print()
print("=== REMOTENESS ===")
for v in sorted(df["Remoteness"].dropna().unique()):
    print("  ", v[:70])

print()
print("=== SEX ===")
for v in sorted(df["Sex"].dropna().unique()):
    print("  ", v[:70])
