# Data provenance — *Growing Old in Australia*

FIT3179 Data Visualisation 1 · Ian Leong (34423680) · Monash University

Every number in the visualisation traces back through this document to a named file
from a named government publisher. All source files were downloaded on
**2 September 2026** and are kept unmodified in `raw/`.

---

## 1. Sources

### A. Productivity Commission — *Report on Government Services 2026*
**Part F, Section 14: Aged care services**

- Landing page: <https://www.pc.gov.au/ongoing/report-on-government-services/community-services/aged-care-services/>
- Edition released: **January 2026** · Next edition: January 2027
- Coverage: **2014–15 to 2024–25**

| Downloaded file | Source URL | Size |
|---|---|---|
| `raw/rogs2026_agedcare_dataset.csv` | `https://assets.pc.gov.au/2026-01/rogs-2026-partf-section14-aged-care-dataset.csv` | 3,139,151 B |
| `raw/rogs2026_agedcare_tables.xlsx` | `https://assets.pc.gov.au/2026-01/rogs-2026-partf-section14-aged-care-data-tables.xlsx` | 1,005,342 B |

The CSV is already tidy: 6,660 rows, one row per measure × year × breakdown, with
state columns (`NSW … NT`, `Aust`) holding the values. This is the primary aged care
source — it supplies recipients, rates per 1,000, residential places, occupancy and
government expenditure. Missing values are coded `..` or `na`.

### B. Australian Bureau of Statistics — *National, state and territory population*

- Landing page: <https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release>
- Reference period: **December 2025** · Released: **18 June 2026** · Next release: 17 September 2026
- Table 59 used: *Estimated Resident Population by single year of age, Australia*, **1971–2025**

| Downloaded file | Source URL (base `.../national-state-and-territory-population/dec-2025/`) | Size |
|---|---|---|
| `raw/abs_3101059.xlsx` | `3101059.xlsx` — **Table 59, Australia by single year of age** *(the one used)* | 201,862 B |
| `raw/abs_310104.xlsx` | `310104.xlsx` — ERP, states and territories | 91,015 B |
| `raw/abs_3101051.xlsx` … `abs_3101058.xlsx` | `3101051.xlsx` … `3101058.xlsx` — ERP by age, one file per state | ~180–197 KB each |

### C. Australian Bureau of Statistics — *Population Projections, Australia, 2022 (base) – 2071*

- Landing page: <https://www.abs.gov.au/statistics/people/population/population-projections-australia/latest-release>
- Released: **23 November 2023** · No newer edition (ABS publishes these roughly every five years)
- **Series B** used — the ABS's central assumptions

| Downloaded file | Source URL (base `.../population-projections-australia/2022-base-2071/`) | Size |
|---|---|---|
| `raw/absproj_timeseries_by_age_sex.zip` | `Time-series-population-projections-by-age-and-sex.zip` | 4,475,490 B |
| `raw/absproj/` | 27 files extracted from the above | — |
| `raw/absproj/3222_Table_B9.xlsx` | **Series B, Australia** *(the one used)* | 219,501 B |
| `raw/absproj_3222_Table_A1.xlsx`, `_B1`, `_C1` | Series A/B/C, NSW — downloaded before B9 was identified as the national table | ~192–198 KB |

> Tables numbered 1–8 are individual states; **9 is Australia**. Letters A/B/C are the
> three assumption sets. B9 is therefore Series B, national — confirmed by the absence
> of a state name in its series descriptions.

### D. AIHW / Department of Health, Disability and Ageing — *Aged Care Data Snapshot 2025*

- Landing page: <https://www.gen-agedcaredata.gov.au/resources/access-data/2025/october/aged-care-data-snapshot-2025>
- Released: **October 2025** · Coverage: 2024–25, to 30 June 2025 · No 2026 snapshot published yet

| Downloaded file | Source URL (base `https://www.gen-agedcaredata.gov.au/getmedia/`) | Size |
|---|---|---|
| `raw/snapshot2025_1st.xlsx` | `fbe4394c-b984-49f8-8174-d4bd74221619/Aged-Care-Data-Snapshot-2025-First-release` | 422,830 B |
| `raw/snapshot2025_2nd.xlsx` | `c1761583-40e3-48fa-b58d-89b1882d3902/Aged-Care-Data-Snapshot-2025-Second-release_02` | 552,161 B |
| `raw/snapshot2025_3rd.xlsx` | `4bf74c78-e512-4b23-a46b-47c01b161987/Aged-Care-Data-Snapshot-2025-Third-release` | 620,380 B |
| `raw/snapshot2025_4th.xlsx` | `6e72d4c5-df3a-49e1-806c-6e0bc822fdd3/Aged-Care-Data-Snapshot-2025-Fourth-release` | 640,016 B |

Used for **one figure only**: the Northern Territory hosts 21 of Australia's 47
National Aboriginal and Torres Strait Islander Flexible Aged Care services
(`Providers and Services` sheet). Kept as a cross-check on the RoGS provider counts.

---

## 2. Why these are the most recent available

The brief requires the most recent available dataset. Checked 2 September 2026 against
each publisher's own "latest release" page:

| Source | Edition used | Released | Next |
|---|---|---|---|
| ABS population | December 2025 | 18 Jun 2026 | 17 Sep 2026 — *after the deadline* |
| ABS projections | 2022 (base) – 2071 | 23 Nov 2023 | None scheduled |
| RoGS | 2026 | Jan 2026 | Jan 2027 |
| AIHW snapshot | 2025 | Oct 2025 | Not yet published |

Three points worth being able to defend:

1. **Aged care data ends 30 June 2025 because that is the newest that exists.** AIHW GEN's
   August 2026 release is still publishing files labelled `2024–25`. The 2025–26 year
   will not appear until late 2026.
2. **A newer ABS quarterly would change nothing.** Table 59 is an *annual* table ending
   30 June 2025. The September release adds headline totals for another quarter, not
   another year of single-year-of-age detail — which is the only thing the pyramid and
   the per-1,000 denominators use.
3. **The 2022 projection base is the only one there is.** The Centre for Population
   publishes more recent projections, but they stop at 2035–36; this story runs to 2045,
   so ABS Series B is the necessary choice rather than the convenient one.

---

## 3. The join

The requirement to combine two sources is met by joining **RoGS aged care counts** to
**ABS population counts** on `year × age band × state`, producing the derived measure the
whole visualisation rests on:

```
rate per 1,000 = care recipients ÷ population of the same age and place × 1,000
```

Without it every chart would restate where Australians happen to live rather than how
they use aged care. RoGS publishes many of these rates directly; the ABS files supply
the population structure, the 1971–2025 history and the projections to 2045, none of
which exist in the RoGS data.

---

## 4. Output files

Eleven CSVs in `out/`, built by `scripts/build_datasets.py`. UTF-8, one header row.

| File | Rows | Chart | Columns |
|---|---:|---|---|
| `pop_bands.csv` | 450 | 1 | `year, age_band, band_type, population, series, population_millions` |
| `pop_pyramid.csv` | 84 | 2 | `age_band, sex, value, year, series, share_pct, signed_population, signed_share_pct, band_sort` |
| `care_rate_program_year.csv` | 40 | 3, 4 | `year, programme, rate_per_1000` |
| `care_rate_age_program.csv` | 30 | 5 | `age_band, programme, rate_per_1000, band_sort, per_100_people` |
| `waffle.csv` | 100 | 6 | `cell, row, col, category, age_group` |
| `remoteness.csv` | 50 | 7, 8 | `year, remoteness, remoteness_sort, population_65plus_000, share_of_places_pct, residential_places, places_per_1000_aged_65plus, occupancy_pct, vacancy_pct, national_occupancy_pct, occupancy_vs_national_pct_pts` |
| `expenditure_waterfall.csv` | 6 | 9 | `step, label, type, amount_m, running_total_m, closing_total_m` |
| `expenditure.csv` | 51 | 10 | `year, programme, real_expenditure_m` |
| `state_year.csv` | 360 | 11 | `year, state, programme, rate_per_1000` |
| `marimekko.csv` | 96 | 12 | `state, programme, point_id, x, y, state_width_pct, programme_share_pct, population_65plus_000, rate_per_1000, year, x_centre` |
| `state_population.csv` | 90 | reference | `pop_year, state, population_65plus_000` |

### Lineage

| Output | Built from |
|---|---|
| `pop_bands.csv`, `pop_pyramid.csv` | ABS `abs_3101059.xlsx` (1971–2025) + `absproj/3222_Table_B9.xlsx` (2026–2045) |
| `care_rate_program_year.csv` | RoGS `Measure = "People receiving aged care services - descriptive data"`, `Unit = rate`, aggregate age definition |
| `care_rate_age_program.csv` | Same measure, `Year = 2024-25`, six single age bands |
| `waffle.csv` | Derived from `care_rate_age_program.csv` — the 90+ residential rate only |
| `remoteness.csv` | RoGS `Measure = "Service overview"` (places, occupancy) + `"Aged care target and planning populations"` (population 65+) |
| `expenditure*.csv` | RoGS `Measure = "Government expenditure"`, `Unit = $m`, `Description2 = "Expenditure"` |
| `state_year.csv`, `state_population.csv` | RoGS state columns from the same two measures |
| `marimekko.csv` | Derived from `state_year.csv` + `state_population.csv` — polygon corners precomputed |

### Transformations applied

Deliberately minimal — the brief states that data wrangling earns no marks.

- Reshaped RoGS state columns from wide to long.
- Renamed programmes to plain English for a general audience:
  `Residential care - permanent` → **Residential aged care**;
  `Home Care levels 1-4` → **Home Care Packages**;
  `Commonwealth Home Support Programme` → **Home support (CHSP)**.
- Parsed ABS time-series workbooks (Index sheet maps Series ID → description; Data
  sheets hold values) into long format; aggregated single years of age into bands.
- Computed three derived measures, each documented below.
- `..` and `na` converted to null. No values imputed, smoothed or filled.

### Derived measures

| Measure | Formula | Where |
|---|---|---|
| Residential places by remoteness | `total places × share_of_places_pct ÷ 100` | `remoteness.csv` |
| Places per 1,000 aged 65+ | `places ÷ population_65plus_000` | `remoteness.csv` |
| National occupancy | occupancy weighted by each area's **share of places**, not a plain mean | `remoteness.csv` |
| Programme share (Marimekko) | `rate_i ÷ Σrate` — valid because all rates share one denominator | `marimekko.csv` |
| Spending change | `value(2024-25) − value(2014-15)` per programme | `expenditure_waterfall.csv` |

---

## 5. Verification

Every headline figure was reconciled against a published total before use.

| Check | Computed | Published | Difference |
|---|---|---|---|
| Waterfall: 2014–15 total + all programme changes | $39,799.3 m | $39,799.4 m | $0.1 m — rounding in source |
| Constant-rate model applied to 2025 (residential) | 256,419 | 260,772 | −1.7% |
| Constant-rate model applied to 2025 (Home Care Packages) | 345,684 | 353,771 | −2.3% |
| Expenditure shares, 2024–25 | 63.9% residential / 32.4% home care | — | sums to 100% with the three small programmes |

The constant-rate check is the important one: the same method that projects 533,000
residential care recipients for 2045 reproduces the actual 2025 count to within 2%,
which is what makes the projection safe to publish.

One error found and corrected during the build: an early annotation claimed women
outnumber men "two to one" above 85. The actual 2025 ratio is **1.46:1**; it only
reaches 2:1 above age 95. The annotation was rewritten.

---

## 6. Caveats

These are stated on the visualisation itself, not buried here.

1. **People, services and places are three different units.** 224,493 is a count of
   residential *places*; 260,772 is a count of *people*. They never share an axis.
2. **The programmes overlap.** A person can hold a Home Care Package and use home
   support in the same year, or move from respite into permanent care. This is why
   chart 3 uses unstacked lines and why the waffle has only two categories — stacking
   overlapping populations would double-count people.
3. **Financial and calendar years both appear.** RoGS aged care data is financial year
   (2024–25); ABS population is at 30 June. Every axis states which.
4. **Expenditure is real, not nominal.** RoGS deflates to constant dollars, so the rise
   from $20.3bn to $39.8bn is a real increase, not inflation.
5. **The 2045 figures are projections, not forecasts** — ABS Series B assumptions, marked
   as a shaded band on chart 1.
6. **The Northern Territory's low residential rate is not simply a shortage.** It hosts 21
   of Australia's 47 Indigenous-specific flexible aged care services, counted outside
   these figures.
7. **Marimekko shares describe aged care *use*, not *people*** — a person can appear in
   more than one programme within a year.

---

## 7. Reproducing this

```
scripts/abs_parse.py        parses any ABS time-series workbook into long format
scripts/build_datasets.py   builds all 11 output CSVs from raw/
scripts/inspect_xlsx.py     lists sheets and previews cells in any workbook
scripts/profile_rogs.py     profiles the RoGS dataset's measures and breakdowns
scripts/drill_rogs.py       drills into the measures feeding each chart
scripts/drill2.py           writes docs/rogs_profile.txt
scripts/verify_series.py    writes docs/series_check.txt
scripts/verify2.py          writes docs/series_check2.txt
```

Run `python scripts/build_datasets.py` from anywhere; it anchors on the project root.
Requires `pandas` and `openpyxl`. The build log, including every reconciliation check,
is written to `docs/build_report.txt`.

---

## 8. Citation for the visualisation footer

> **Data sources.**
> Productivity Commission, *Report on Government Services 2026*, Part F Section 14: Aged
> care services — pc.gov.au/ongoing/report-on-government-services/community-services/aged-care-services
> Australian Bureau of Statistics, *National, state and territory population*, December
> 2025, Table 59 — abs.gov.au/statistics/people/population/national-state-and-territory-population
> Australian Bureau of Statistics, *Population Projections, Australia, 2022 (base) – 2071*,
> Series B, Table B9 — abs.gov.au/statistics/people/population/population-projections-australia
> AIHW / Department of Health, Disability and Ageing, *Aged Care Data Snapshot 2025* —
> gen-agedcaredata.gov.au
>
> **Use of generative AI.** Generative AI (Claude) was used to help locate and reshape the
> source data, to draft and edit the narrative text, and to review the visual design. All
> charts were designed and built by the author.
