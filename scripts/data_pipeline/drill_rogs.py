"""Drill into the RoGS measures that feed the 12 charts."""
import pandas as pd

df = pd.read_csv(r"raw\rogs2026_agedcare_dataset.csv", dtype=str, low_memory=False)

TARGETS = [
    "Service overview",
    "People receiving aged care services - descriptive data",
    "Government expenditure",
    "Use by different groups",
    "Aged care target and planning populations (descriptive information)",
    "Types of care and support",
]

DESC = ["Description1", "Description2", "Description3", "Description4"]

for measure in TARGETS:
    sub = df[df["Measure"] == measure]
    print("\n" + "=" * 100)
    print("MEASURE:", measure, " | rows:", len(sub))
    print("  years:", sorted(sub["Year"].dropna().unique()))
    print("  units:", sorted(sub["Unit"].dropna().unique()))
    print("  service types:", sorted(sub["Service_Type"].dropna().unique()))
    print("  ages:", sorted(sub["Age"].dropna().unique())[:14])
    print("  remoteness:", sorted(sub["Remoteness"].dropna().unique()))
    print("  --- distinct description combos (max 30) ---")
    combos = sub[DESC].fillna("").drop_duplicates()
    for _, row in combos.head(30).iterrows():
        parts = [p for p in row.tolist() if p]
        print("     *", " || ".join(p[:58] for p in parts))
    if len(combos) > 30:
        print("     ... and", len(combos) - 30, "more combos")
