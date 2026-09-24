"""Find the best multi-year, by-programme series for the stacked area and slope charts."""
import pandas as pd

pd.set_option("display.width", 260)
df = pd.read_csv(r"raw\rogs2026_agedcare_dataset.csv", dtype=str, low_memory=False)
out = open(r"docs\series_check2.txt", "w", encoding="utf-8")


def w(*a):
    print(*a, file=out)


ppl = df[df["Measure"] == "People receiving aged care services - descriptive data"]

w("### ALL 'People receiving' rows: Unit x Year counts")
w(ppl.pivot_table(index="Unit", columns="Year", values="Aust", aggfunc="size").to_string())

w("\n### RATE rows at the aggregate age definition, by programme x year")
agg_age = "50+ years old (Aboriginal and Torres Strait Islander people) and 65+ years old (non-Indigenous people)"
sub = ppl[(ppl["Unit"] == "rate") & (ppl["Age"] == agg_age)]
w(sub.pivot_table(index="Description4", columns="Year", values="Aust", aggfunc="first").to_string())

w("\n### Same, but Age == '50+ years old'")
sub2 = ppl[(ppl["Unit"] == "rate") & (ppl["Age"] == "50+ years old")]
w(sub2.pivot_table(index="Description4", columns="Year", values="Aust", aggfunc="first").to_string())

# --- multi-year COUNTS from 'Use by different groups' ---
use = df[df["Measure"] == "Use by different groups"]
w("\n\n### 'Use by different groups' : Description1 values and year spans")
g = use.groupby("Description1").agg(rows=("Year", "size"), y_min=("Year", "min"),
                                    y_max=("Year", "max"), n=("Year", "nunique"))
for name, r in g.sort_values("rows", ascending=False).iterrows():
    w("  [%3d rows | %s-%s | %2d yrs] %s" % (r["rows"], r["y_min"], r["y_max"], r["n"], str(name)[:95]))

# --- Service overview: home care recipients + residential places over 10 yrs ---
so = df[df["Measure"] == "Service overview"]
w("\n\n### SERVICE OVERVIEW - counts by year (Aust)")
cnt = so[so["Unit"] == "no."]
w(cnt.pivot_table(index=["Description1", "Description2", "Description3"],
                  columns="Year", values="Aust", aggfunc="first").to_string())

w("\n### SERVICE OVERVIEW - occupancy rate")
occ = so[so["Description2"].fillna("").str.contains("Occupancy", case=False)]
w(occ.pivot_table(index=["Description2", "Description3"], columns="Year",
                  values="Aust", aggfunc="first").to_string())

out.close()
print("written docs\\series_check2.txt")
