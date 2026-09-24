"""Verify the exact RoGS slices that will become charts 3, 4, 5, 9, 10."""
import pandas as pd

pd.set_option("display.width", 250)
df = pd.read_csv(r"raw\rogs2026_agedcare_dataset.csv", dtype=str, low_memory=False)
out = open(r"docs\series_check.txt", "w", encoding="utf-8")


def w(*a):
    print(*a, file=out)


# ---- A. rate per 1000 people aged 65+, by program, by year -------------------
ppl = df[df["Measure"] == "People receiving aged care services - descriptive data"].copy()
rate = ppl[ppl["Unit"] == "rate"].copy()
w("### DESCRIPTION2/3/4 combos in the rate rows")
for _, r in rate[["Description2", "Description3", "Description4"]].fillna("").drop_duplicates().iterrows():
    w("   *", " || ".join(str(p)[:75] for p in r.tolist() if p))

w("\n### Age values present in rate rows")
for v in sorted(rate["Age"].dropna().unique()):
    w("   ", v[:80])

# the 65+ headline rate, all programs, over time
r65 = rate[rate["Age"] == "65+ years old"]
w("\n### 65+ RATE BY PROGRAM BY YEAR (Aust)")
if len(r65):
    p = r65.pivot_table(index="Description4", columns="Year", values="Aust", aggfunc="first")
    w(p.to_string())
else:
    w("   (none at Age == '65+ years old')")

# by age band, latest year
w("\n### RATE BY AGE BAND x PROGRAM, 2024-25 (Aust)")
bands = ["65-69 years old", "70-74 years old", "75-79 years old",
         "80-84 years old", "85-89 years old", "90+ years old"]
rb = rate[(rate["Year"] == "2024-25") & (rate["Age"].isin(bands))]
w(rb.pivot_table(index="Age", columns="Description4", values="Aust", aggfunc="first").to_string())

w("\n### RATE BY AGE BAND x PROGRAM, ALL YEARS (rows=age, cols=year), per program")
for prog in sorted(rb["Description4"].dropna().unique()):
    sub = rate[(rate["Age"].isin(bands)) & (rate["Description4"] == prog)]
    w("\n--- " + prog + " ---")
    w(sub.pivot_table(index="Age", columns="Year", values="Aust", aggfunc="first").to_string())

# ---- B. government expenditure by program by year ---------------------------
exp = df[(df["Measure"] == "Government expenditure") & (df["Unit"] == "$m")].copy()
tot = exp[exp["Description3"].fillna("") == "Total"]
w("\n\n### REAL RECURRENT EXPENDITURE ($m), Description2 = programme, Description3 = Total")
w(tot.pivot_table(index="Description2", columns="Year", values="Aust", aggfunc="first").to_string())

w("\n### 'Expenditure' rollup rows (Description2 == 'Expenditure')")
ex2 = exp[exp["Description2"].fillna("") == "Expenditure"]
w(ex2.pivot_table(index="Description3", columns="Year", values="Aust", aggfunc="first").to_string())

# ---- C. target population by remoteness by year -----------------------------
tgt = df[df["Measure"] == "Aged care target and planning populations (descriptive information)"]
t65 = tgt[tgt["Age"] == "65+ years old"]
w("\n\n### POPULATION AGED 65+ ('000) BY REMOTENESS BY YEAR (Aust)")
w(t65.pivot_table(index="Remoteness", columns="Year", values="Aust", aggfunc="first").to_string())

w("\n### POPULATION AGED 65+ ('000) BY STATE, 2025 (All areas)")
st = t65[t65["Remoteness"] == "All areas"]
w(st[["Year", "NSW", "Vic", "Qld", "WA", "SA", "Tas", "ACT", "NT", "Aust"]].to_string(index=False))

# ---- D. age-sex specific rate (users pyramid) -------------------------------
use = df[df["Measure"] == "Use by different groups"]
pyr = use[use["Description1"].fillna("").str.contains("Age-sex specific rate", case=False)]
w("\n\n### AGE-SEX SPECIFIC RATE PER 1000, 2025")
p25 = pyr[pyr["Year"] == "2025"]
w(p25.pivot_table(index="Age", columns=["Service_Type", "Sex"], values="Aust", aggfunc="first").to_string())

out.close()
print("written docs\\series_check.txt")
