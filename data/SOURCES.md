# Data Visualisation 1 - Aged Care in Australia - Data Sources

Downloaded 1 September 2026. All data is public and unmodified.

## Source 1: ABS - Estimated Resident Population by age (historical)

Files: `ABS_3101051..3101059_ERP_by_age_*.xlsx` (one per state/territory plus Australia)

- Publication: National, state and territory population, December 2025 release (published 18 June 2026)
- Publisher: Australian Bureau of Statistics
- URL: https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release
- Content: Estimated resident population by sex and single year of age, quarterly from 1971
- Use: population pyramid, 65+/85+ share over time, state x year heatmap, rate denominators

## Source 2: ABS - Population Projections

File: `ABS_3222_Table_B1_projections_Australia_medium.xlsx`

- Publication: Population Projections, Australia, 2022 (base) to 2071, Table B1 (medium series)
- Publisher: Australian Bureau of Statistics
- URL: https://www.abs.gov.au/statistics/people/population/population-projections-australia/latest-release
- Content: Projected population of Australia by age, medium assumptions, 2022 to 2071
- Use: future 65+/85+ share, "1 in X Australians" waffle/ISOTYPE projection

## Source 3: AIHW GEN - Aged care data snapshot 2025

Files: `GEN_Aged_Care_Snapshot_2025_1st..4th_release.xlsx` (4th release is cumulative and has everything)

- Publisher: Australian Institute of Health and Welfare, GEN Aged Care Data
- URL: https://www.gen-agedcaredata.gov.au/resources/access-data/2025/october/aged-care-data-snapshot-2025
- Content: Clients at 30 June 2025 by state x program (residential permanent/respite, Home Care Packages by level 1-4, transition care, STRC), sex by age group, providers, expenditure
- Use: treemap of program composition, home care level breakdowns, sex/age structure of residents

## Source 4: Productivity Commission - Report on Government Services 2026, Aged care (section 14)

Files: `ROGS_2026_aged_care_dataset.csv` (tidy long format, best for Tableau), `ROGS_2026_aged_care_data_tables.xlsx` (formatted tables with footnotes)

- Publisher: Productivity Commission, Report on Government Services 2026, Part F section 14
- URL: https://www.pc.gov.au/ongoing/report-on-government-services/community-services/aged-care-services/
- Content: long-format CSV, columns Year / Measure / Service_Type / descriptors / NSW..NT / Aust
  - "People receiving aged care services": 2017-18 to 2024-25, by state, for Home Care, Home Support, Residential Care, Transition Care
  - "Elapsed time" (approval to entering care): 2015-16 to 2024-25 - the wait-time story
  - Also expenditure, workforce, quality indicators
- Use: streamgraph of recipients by program over time, bump chart of states, slope chart home care vs residential, wait-time chart

## Tableau notes (per Week 4 tutorial)

- ROGS CSV is one-row-per-observation with state columns: pivot NSW..NT into a State column inside Tableau (select columns > Pivot) to get tidy State/Value rows.
- Do NOT join ABS population onto ROGS rows on Year alone: ROGS has multiple rows per state-year, population values would duplicate (the STORE1 trap from the Week 4 tutorial). Blend instead, or pre-compute per-1,000 rates.
- ABS financial-year alignment: ROGS years are financial (2024-25 = at 30 June 2025); use ABS June quarter ERP for matching.
