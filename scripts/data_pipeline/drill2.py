"""Focused drill into the exact RoGS slices that feed each chart."""
import pandas as pd

df = pd.read_csv(r"raw\rogs2026_agedcare_dataset.csv", dtype=str, low_memory=False)
out = open(r"docs\rogs_profile.txt", "w", encoding="utf-8")


def w(*a):
    print(*a, file=out)


def show(label, sub, cols=("Year", "Age", "Sex", "Service_Type", "Remoteness", "Unit", "Aust")):
    w("\n" + "=" * 110)
    w("### " + label + "   rows=" + str(len(sub)))
    if not len(sub):
        return
    w("  years: " + ", ".join(sorted(sub["Year"].dropna().unique())))
    w("  units: " + ", ".join(sorted(sub["Unit"].dropna().unique())))
    for c in ("Age", "Sex", "Service_Type", "Remoteness"):
        vals = sorted(sub[c].dropna().unique())
        if vals:
            w("  %-12s: %s" % (c, " | ".join(v[:44] for v in vals[:16])))
    w("  --- sample rows ---")
    w(sub[list(cols)].head(18).to_string(index=False))


# 1. Government expenditure
exp = df[df["Measure"] == "Government expenditure"]
show("GOVERNMENT EXPENDITURE", exp)
w("\n  distinct descriptions:")
for _, r in exp[["Description1", "Description2", "Description3", "Description4"]].fillna("").drop_duplicates().iterrows():
    w("     * " + " || ".join(p[:70] for p in r.tolist() if p))

# 2. People receiving aged care services, counts and rates by age x program
ppl = df[df["Measure"] == "People receiving aged care services - descriptive data"]
show("PEOPLE RECEIVING AGED CARE - counts (no.)", ppl[ppl["Unit"] == "no."])
show("PEOPLE RECEIVING AGED CARE - rates", ppl[ppl["Unit"] == "rate"])
w("\n  distinct descriptions:")
for _, r in ppl[["Description1", "Description2", "Description3", "Description4"]].fillna("").drop_duplicates().iterrows():
    w("     * " + " || ".join(p[:70] for p in r.tolist() if p))

# 3. Age-sex specific rate (the pyramid of USERS)
use = df[df["Measure"] == "Use by different groups"]
pyr = use[use["Description1"].fillna("").str.contains("Age-sex specific rate", case=False)]
show("AGE-SEX SPECIFIC RATE (pyramid source)", pyr)

# 4. Target/planning population (denominators + remoteness widths)
tgt = df[df["Measure"] == "Aged care target and planning populations (descriptive information)"]
show("TARGET / PLANNING POPULATION", tgt)

# 5. Types of care and support
tcs = df[df["Measure"] == "Types of care and support"]
show("TYPES OF CARE AND SUPPORT", tcs)
w("\n  distinct descriptions:")
for _, r in tcs[["Description1", "Description2", "Description3", "Description4"]].fillna("").drop_duplicates().iterrows():
    w("     * " + " || ".join(p[:70] for p in r.tolist() if p))

# 6. Residential care services
res = df[df["Measure"] == "Residential care services"]
show("RESIDENTIAL CARE SERVICES", res)
w("\n  distinct descriptions:")
for _, r in res[["Description1", "Description2", "Description3", "Description4"]].fillna("").drop_duplicates().head(40).iterrows():
    w("     * " + " || ".join(p[:70] for p in r.tolist() if p))

out.close()
print("written docs\\rogs_profile.txt")
