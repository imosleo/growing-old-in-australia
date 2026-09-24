"""Build the Tableau-ready datasets for 'Growing Old in Australia' (FIT3179 DV1).

Sources
  A. ABS 3101.0 Table 59  - Estimated Resident Population by single year of age & sex,
                            Australia, 1971-2025.
  B. ABS 3222.0 Table B9  - Population projections (Series B), by age & sex,
                            Australia, 2022-2071.
  C. RoGS 2026 Part F s14 - Aged care services dataset (Productivity Commission),
                            aged care recipients, rates, expenditure, 2014-15 to 2024-25.

Everything is written to out/ as UTF-8 CSV with a single header row, which is what
Tableau connects to most cleanly.
"""
import os
import sys

import pandas as pd

# Run from anywhere: anchor on the project root, and make abs_parse importable.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(ROOT)

from abs_parse import load_abs

os.makedirs("docs", exist_ok=True)
OUT = "out"
os.makedirs(OUT, exist_ok=True)
report = open(os.path.join("docs", "build_report.txt"), "w", encoding="utf-8")


def log(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    print(line, file=report)


def save(df, name, note=""):
    path = os.path.join(OUT, name)
    df.to_csv(path, index=False, encoding="utf-8")
    log("  wrote %-28s %5d rows  %s" % (name, len(df), note))


STATES = ["NSW", "Vic", "Qld", "WA", "SA", "Tas", "ACT", "NT"]

# Plain-English programme names for a general audience.
PROGRAMME = {
    "Residential care - permanent": "Residential aged care",
    "Residential care - respite": "Residential respite",
    "Home Care levels 1-4": "Home Care Packages",
    "Commonwealth Home Support Programme": "Home support (CHSP)",
    "Transition Care": "Transition care",
}
# The three main, non-overlapping programmes used for composition charts.
MAIN3 = ["Residential aged care", "Home Care Packages", "Home support (CHSP)"]

EXPENDITURE = {
    "Residential and Flexible Care Services": "Residential & flexible care",
    "Home Care and Support Services": "Home care & support",
    "Assessment and Information Services": "Assessment & information",
    "Workforce and Quality; and Ageing and Service Improvement": "Workforce & quality",
    "Aged Care Quality and Safety Commission": "Quality & Safety Commission",
}

AGG_AGE = ("50+ years old (Aboriginal and Torres Strait Islander people) "
           "and 65+ years old (non-Indigenous people)")


def to_num(s):
    """RoGS uses '..' and 'na' for missing."""
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")


def band_5yr(age):
    if age >= 100:
        return "100+"
    lo = (age // 5) * 5
    return "%d-%d" % (lo, lo + 4)


# =============================================================================
# ABS population
# =============================================================================
log("=" * 78)
log("ABS population")
log("=" * 78)

erp = load_abs(os.path.join("raw", "abs_3101059.xlsx"))
parts = erp["description"].str.split(";", expand=True)
erp["sex"] = parts[1].str.strip()
erp["age_raw"] = parts[2].str.strip()
erp["age"] = erp["age_raw"].str.replace(" and over", "", regex=False).astype(int)
erp["value"] = pd.to_numeric(erp["value"], errors="coerce")
erp = erp.dropna(subset=["value"])
log("ERP parsed: %d rows, %d-%d, sexes=%s" %
    (len(erp), erp["year"].min(), erp["year"].max(), sorted(erp["sex"].unique())))

proj = load_abs(os.path.join("raw", "absproj", "3222_Table_B9.xlsx"))
pparts = proj["description"].str.split(";", expand=True)
proj["sex"] = pparts[1].str.strip()
proj["age_raw"] = pparts[2].str.strip()
proj["age"] = proj["age_raw"].str.replace(" and over", "", regex=False).astype(int)
proj["value"] = pd.to_numeric(proj["value"], errors="coerce")
proj = proj.dropna(subset=["value"])
log("Projections parsed: %d rows, %d-%d" % (len(proj), proj["year"].min(), proj["year"].max()))

# ---- 1. population age bands over time (chart 1) ----------------------------
def bands_over_time(df, label):
    """Exclusive age bands only.

    65+, 75+ and 85+ are nested (85+ sits inside 75+ sits inside 65+), so they can
    never be stacked. 65-74 / 75-84 / 85+ are mutually exclusive and sum to 65+,
    which is what chart 1 stacks.
    """
    persons = df[df["sex"] == "Persons"]
    rows = []
    bands = (("65-74", 65, 74), ("75-84", 75, 84), ("85 and over", 85, 200))
    for band, lo, hi in bands:
        sel = persons[(persons["age"] >= lo) & (persons["age"] <= hi)]
        for yr, val in sel.groupby("year")["value"].sum().items():
            rows.append({"year": int(yr), "age_band": band, "band_type": "Exclusive",
                         "population": float(val), "series": label})
    # cumulative bands kept for reference/annotation only - never stack these
    for band, lo in (("65 and over", 65), ("75 and over", 75), ("85 and over (cum.)", 85)):
        sel = persons[persons["age"] >= lo]
        for yr, val in sel.groupby("year")["value"].sum().items():
            rows.append({"year": int(yr), "age_band": band, "band_type": "Cumulative",
                         "population": float(val), "series": label})
    return pd.DataFrame(rows)


hist = bands_over_time(erp, "Actual")
fut = bands_over_time(proj, "Projected")
fut = fut[fut["year"].between(2026, 2045)]
pop_bands = pd.concat([hist, fut], ignore_index=True).sort_values(["age_band", "year"])
pop_bands["population_millions"] = (pop_bands["population"] / 1_000_000).round(3)
save(pop_bands, "pop_bands.csv", "chart 1 - ageing nation lines")

for band in ("65-74", "75-84", "85 and over", "65 and over"):
    s = (pop_bands[pop_bands["age_band"] == band]
         .drop_duplicates(subset=["year"]).set_index("year")["population"])
    log("    %-18s 1971=%10.0f  2025=%10.0f  2045=%10.0f  (x%.2f 2025->2045)"
        % (band, s.get(1971, float("nan")), s.get(2025, float("nan")),
           s.get(2045, float("nan")), s.get(2045, float("nan")) / s.get(2025, float("nan"))))

# ---- 2. population pyramid, 2025 vs 2045 (chart 2) --------------------------
def pyramid(df, year, label):
    sub = df[(df["year"] == year) & (df["sex"].isin(["Male", "Female"]))].copy()
    sub["age_band"] = sub["age"].apply(band_5yr)
    g = sub.groupby(["age_band", "sex"], as_index=False)["value"].sum()
    g["year"] = year
    g["series"] = label
    total = g["value"].sum()
    g["share_pct"] = (g["value"] / total * 100).round(3)
    # males drawn to the left of the axis
    g["signed_population"] = g.apply(
        lambda r: -r["value"] if r["sex"] == "Male" else r["value"], axis=1)
    g["signed_share_pct"] = g.apply(
        lambda r: -r["share_pct"] if r["sex"] == "Male" else r["share_pct"], axis=1)
    return g


pyr = pd.concat([pyramid(erp, 2025, "2025 (actual)"),
                 pyramid(proj, 2045, "2045 (projected)")], ignore_index=True)
band_order = ["%d-%d" % (i, i + 4) for i in range(0, 100, 5)] + ["100+"]
pyr["band_sort"] = pyr["age_band"].map({b: i for i, b in enumerate(band_order)})
pyr = pyr.sort_values(["series", "sex", "band_sort"])
save(pyr, "pop_pyramid.csv", "chart 2 - population pyramid")

p25 = pyr[(pyr["series"] == "2025 (actual)")]
p45 = pyr[(pyr["series"] == "2045 (projected)")]
old25 = p25[p25["band_sort"] >= 17]["value"].sum() / p25["value"].sum() * 100
old45 = p45[p45["band_sort"] >= 17]["value"].sum() / p45["value"].sum() * 100
log("    share of population aged 85+: 2025 = %.2f%%   2045 = %.2f%%" % (old25, old45))

# =============================================================================
# RoGS aged care
# =============================================================================
log("")
log("=" * 78)
log("RoGS aged care")
log("=" * 78)

rogs = pd.read_csv(os.path.join("raw", "rogs2026_agedcare_dataset.csv"),
                   dtype=str, low_memory=False)

ppl = rogs[rogs["Measure"] == "People receiving aged care services - descriptive data"]
rate = ppl[ppl["Unit"] == "rate"].copy()

# ---- 3/4. rate per 1,000 older people, by programme, by year ----------------
tr = rate[(rate["Age"] == AGG_AGE) & (rate["Description4"].isin(PROGRAMME))].copy()
tr["programme"] = tr["Description4"].map(PROGRAMME)
tr["rate_per_1000"] = to_num(tr["Aust"])
trend = (tr[["Year", "programme", "rate_per_1000"]]
         .dropna()
         .drop_duplicates(subset=["Year", "programme"])
         .rename(columns={"Year": "year"})
         .sort_values(["programme", "year"]))
save(trend, "care_rate_program_year.csv", "charts 3 & 4 - stacked area + slope")

piv = trend.pivot(index="year", columns="programme", values="rate_per_1000")
log(piv.to_string())
first, last = piv.index.min(), piv.index.max()
log("")
for prog in piv.columns:
    a, b = piv.loc[first, prog], piv.loc[last, prog]
    log("    %-24s %s = %6.1f  ->  %s = %6.1f   (%+.0f%%)"
        % (prog, first, a, last, b, (b / a - 1) * 100))

# ---- 5. rate per 1,000 by age band x programme (chart 5) --------------------
BANDS = ["65-69 years old", "70-74 years old", "75-79 years old",
         "80-84 years old", "85-89 years old", "90+ years old"]
ab = rate[(rate["Year"] == "2024-25") & (rate["Age"].isin(BANDS))
          & (rate["Description4"].isin(PROGRAMME))].copy()
ab["programme"] = ab["Description4"].map(PROGRAMME)
ab["age_band"] = ab["Age"].str.replace(" years old", "", regex=False)
ab["rate_per_1000"] = to_num(ab["Aust"])
heat = (ab[["age_band", "programme", "rate_per_1000"]]
        .dropna().drop_duplicates(subset=["age_band", "programme"]))
heat["band_sort"] = heat["age_band"].map(
    {b: i for i, b in enumerate(["65-69", "70-74", "75-79", "80-84", "85-89", "90+"])})
heat["per_100_people"] = (heat["rate_per_1000"] / 10).round(1)
heat = heat.sort_values(["programme", "band_sort"])
save(heat, "care_rate_age_program.csv", "chart 5 - heatmap")
log(heat.pivot(index="age_band", columns="programme", values="rate_per_1000").to_string())

# ---- 6. waffle: of 100 people aged 90+, how many use each programme ---------
# Only two categories. A person can use more than one programme during a year, so
# residential / home care / home support counts overlap and must not be stacked into
# one 100-cell grid. Permanent residential care against everyone else is exact.
w = heat[heat["age_band"] == "90+"].set_index("programme")["rate_per_1000"]
res90 = float(w.get("Residential aged care"))
in_res = round(res90 / 10)
community = 100 - in_res
log("")
log("    Of 100 Australians aged 90+, %d spent time in permanent residential aged care "
    "during 2024-25; the other %d did not." % (in_res, community))
log("    (For reference, at 90+ the Home Care Package rate is %.1f and home support %.1f "
    "per 1,000 - these overlap with each other and are NOT stackable.)"
    % (float(w.get("Home Care Packages")), float(w.get("Home support (CHSP)"))))

waffle_cats = ([("In permanent residential aged care", in_res)]
               + [("Not in residential aged care", community)])
cells = []
i = 0
for label, n in waffle_cats:
    for _ in range(n):
        cells.append({"cell": i + 1,
                      "row": 9 - (i // 10),      # row 9 at top so it fills bottom-up
                      "col": i % 10,
                      "category": label})
        i += 1
waffle = pd.DataFrame(cells)
waffle["age_group"] = "90 and over"
save(waffle, "waffle.csv", "chart 6 - waffle, 10x10 grid")

# ---- 7/8. remoteness: places per 1,000 and occupancy (charts 7 & 8) ---------
so = rogs[rogs["Measure"] == "Service overview"]
places_total = so[(so["Description2"] == "Number of operational places at 30 June")
                  & (so["Description1"] == "Residential care")]
places_total = (places_total.assign(places=to_num(places_total["Aust"]))
                .dropna(subset=["places"])
                .drop_duplicates(subset=["Year"])
                .set_index("Year")["places"])

prop = so[so["Description2"] == "Proportion of operational places at 30 June"]
prop = prop[prop["Description3"] == "Remoteness area"].copy()
prop["pct"] = to_num(prop["Aust"])

occ = so[so["Description2"] == "Occupancy rate at 30 June"].copy()
occ["occupancy_pct"] = to_num(occ["Aust"])

tgt = rogs[rogs["Measure"] ==
           "Aged care target and planning populations (descriptive information)"]
t65 = tgt[tgt["Age"] == "65+ years old"].copy()
t65["pop65_000"] = to_num(t65["Aust"])

REM_ORDER = ["Major cities", "Inner regional", "Outer regional", "Remote", "Very remote"]
rows = []
for year in sorted(places_total.index):
    tot = places_total[year]
    for rem in REM_ORDER:
        pr = prop[(prop["Year"] == year) & (prop["Remoteness"] == rem)]["pct"]
        oc = occ[(occ["Year"] == year) & (occ["Remoteness"] == rem)]["occupancy_pct"]
        pp = t65[(t65["Year"] == year) & (t65["Remoteness"] == rem)]["pop65_000"]
        if not len(pr) or not len(pp):
            continue
        places = tot * float(pr.iloc[0]) / 100.0
        pop000 = float(pp.iloc[0])
        rows.append({
            "year": int(year),
            "remoteness": rem,
            "remoteness_sort": REM_ORDER.index(rem),
            "population_65plus_000": pop000,
            "share_of_places_pct": float(pr.iloc[0]),
            "residential_places": round(places),
            "places_per_1000_aged_65plus": round(places / pop000, 1),
            "occupancy_pct": float(oc.iloc[0]) if len(oc) else None,
            "vacancy_pct": round(100 - float(oc.iloc[0]), 1) if len(oc) else None,
        })
remote = pd.DataFrame(rows)
# National occupancy for the bullet chart's reference line, weighted by each area's
# share of places. An unweighted mean of the five areas would be badly wrong, since
# major cities hold ~71% of all places.
nat = (remote.groupby("year")
       .apply(lambda g: (g["occupancy_pct"] * g["share_of_places_pct"]).sum()
              / g["share_of_places_pct"].sum(), include_groups=False)
       .round(1).rename("national_occupancy_pct").reset_index())
remote = remote.merge(nat, on="year", how="left")
remote["occupancy_vs_national_pct_pts"] = (
    remote["occupancy_pct"] - remote["national_occupancy_pct"]).round(1)
save(remote, "remoteness.csv", "charts 7 & 8 - remoteness bar + bullet")
log(remote[remote["year"] == remote["year"].max()]
    [["remoteness", "population_65plus_000", "residential_places",
      "places_per_1000_aged_65plus", "occupancy_pct"]].to_string(index=False))

# ---- 9/10. government expenditure (charts 9 & 10) ---------------------------
exp = rogs[(rogs["Measure"] == "Government expenditure") & (rogs["Unit"] == "$m")].copy()
exp = exp[exp["Description2"] == "Expenditure"]
exp["programme"] = exp["Description3"].map(EXPENDITURE)
exp["real_expenditure_m"] = to_num(exp["Aust"])

total = exp[exp["Description3"] == "All Aged Care Services"][["Year", "real_expenditure_m"]]
total = total.drop_duplicates(subset=["Year"]).rename(
    columns={"Year": "year", "real_expenditure_m": "total_m"})

spend = (exp[exp["programme"].notna()][["Year", "programme", "real_expenditure_m"]]
         .dropna(subset=["real_expenditure_m"])
         .drop_duplicates(subset=["Year", "programme"])
         .rename(columns={"Year": "year"})
         .sort_values(["programme", "year"]))
save(spend, "expenditure.csv", "chart 10 - treemap + trend")
sp = spend.pivot(index="year", columns="programme", values="real_expenditure_m")
log(sp.to_string())

# waterfall: 2014-15 -> 2024-25 decomposed by programme
y0, y1 = sp.index.min(), sp.index.max()
start_total = float(total[total["year"] == y0]["total_m"].iloc[0])
end_total = float(total[total["year"] == y1]["total_m"].iloc[0])
# Structured for Tableau's Gantt-bar waterfall: one opening total, then the change
# in each programme. RUNNING_SUM(SUM([amount_m])) lands on the closing total at the
# last bar, so no trailing zero-height "total" bar is needed (it would be invisible).
wf = [{"step": 0, "label": "%s total" % y0, "type": "Total",
       "amount_m": round(start_total, 1), "running_total_m": round(start_total, 1)}]
running = start_total
deltas = {}
for prog in sp.columns:
    a = sp.loc[y0, prog]
    b = sp.loc[y1, prog]
    deltas[prog] = (0.0 if pd.isna(b) else float(b)) - (0.0 if pd.isna(a) else float(a))
for i, prog in enumerate(sorted(deltas, key=deltas.get, reverse=True), start=1):
    delta = deltas[prog]
    running += delta
    wf.append({"step": i, "label": prog,
               "type": "Increase" if delta >= 0 else "Decrease",
               "amount_m": round(delta, 1), "running_total_m": round(running, 1)})
waterfall = pd.DataFrame(waterfall_rows := wf)
waterfall["closing_total_m"] = round(end_total, 1)
save(waterfall, "expenditure_waterfall.csv", "chart 9 - waterfall")
log(waterfall.to_string(index=False))
log("    waterfall reconciliation: start %.1f + changes = %.1f  vs published total %.1f"
    % (start_total, running, end_total))

# ---- 11/12. states (charts 11 & 12) ----------------------------------------
sr = rate[(rate["Age"] == AGG_AGE) & (rate["Description4"].isin(PROGRAMME))].copy()
sr["programme"] = sr["Description4"].map(PROGRAMME)
long_rows = []
for _, r in sr.iterrows():
    for st in STATES + ["Aust"]:
        v = pd.to_numeric(str(r[st]).replace(",", ""), errors="coerce")
        if pd.notna(v):
            long_rows.append({"year": r["Year"], "state": st,
                              "programme": r["programme"], "rate_per_1000": float(v)})
state_year = (pd.DataFrame(long_rows)
              .drop_duplicates(subset=["year", "state", "programme"])
              .sort_values(["programme", "state", "year"]))

pop_state = []
st65 = t65[t65["Remoteness"] == "All areas"]
for _, r in st65.iterrows():
    for st in STATES + ["Aust"]:
        v = pd.to_numeric(str(r[st]).replace(",", ""), errors="coerce")
        if pd.notna(v):
            pop_state.append({"pop_year": int(r["Year"]), "state": st,
                              "population_65plus_000": float(v)})
pop_state = pd.DataFrame(pop_state).drop_duplicates(subset=["pop_year", "state"])
save(state_year, "state_year.csv", "chart 11 - grouped bar by state")
save(pop_state, "state_population.csv", "denominators / marimekko widths")

# ---- marimekko polygons (chart 12) -----------------------------------------
LATEST = state_year["year"].max()
mk_src = state_year[(state_year["year"] == LATEST)
                    & (state_year["state"] != "Aust")
                    & (state_year["programme"].isin(MAIN3))]
widths = (pop_state[pop_state["pop_year"] == pop_state["pop_year"].max()]
          .set_index("state")["population_65plus_000"])
widths = widths[[s for s in STATES]]
widths = widths.sort_values(ascending=False)
grand = widths.sum()

poly = []
x = 0.0
for st in widths.index:
    wpct = widths[st] / grand * 100.0
    sub = mk_src[mk_src["state"] == st].set_index("programme")["rate_per_1000"]
    tot = sub.sum()
    y = 0.0
    for prog in MAIN3:
        share = float(sub.get(prog, 0)) / tot * 100.0
        corners = [(x, y), (x + wpct, y), (x + wpct, y + share), (x, y + share)]
        for pid, (px, py) in enumerate(corners, start=1):
            poly.append({"state": st, "programme": prog, "point_id": pid,
                         "x": round(px, 4), "y": round(py, 4),
                         "state_width_pct": round(wpct, 3),
                         "programme_share_pct": round(share, 2),
                         "population_65plus_000": float(widths[st]),
                         "rate_per_1000": float(sub.get(prog, 0)),
                         "year": LATEST,
                         "x_centre": round(x + wpct / 2, 4)})
        y += share
    x += wpct
marimekko = pd.DataFrame(poly)
save(marimekko, "marimekko.csv", "chart 12 - marimekko polygons")
log("    marimekko widths (%% of Australia's 65+ population, %s):" % LATEST)
for st in widths.index:
    log("      %-5s %6.1f k  %5.1f%%" % (st, widths[st], widths[st] / grand * 100))

report.close()
print("\nAll datasets written to out/. Report: docs/build_report.txt")
