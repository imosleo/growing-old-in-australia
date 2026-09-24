"""Build 'Growing Old in Australia' (FIT3179 DV1) as a Tableau .twbx from the out/ CSVs.

Generates the twb XML directly (12 worksheets + 1 dashboard + highlight action), creates a
.hyper extract per datasource (Tableau Public needs extracts to publish), and zips both a
full twbx and a worksheets-only fallback.
"""
import csv
import os
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as _esc

from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter, SqlType,
                             TableDefinition, TableName, Telemetry)

SRC = os.path.abspath("../../data/out")
OUT_DIR = os.path.abspath("out")
DATA_DIR = os.path.join(OUT_DIR, "data")
WORK = os.path.join(OUT_DIR, "_build")
HYPER_DIR = os.path.join(WORK, "Data", "TableauTemp")
NAME = "Growing Old in Australia"
DASH = NAME

for d in (DATA_DIR, HYPER_DIR):
    os.makedirs(d, exist_ok=True)
for f in os.listdir(SRC):
    if f.endswith(".csv"):
        shutil.copy(os.path.join(SRC, f), os.path.join(DATA_DIR, f))


def esc(s):
    return _esc(str(s), {"'": "&apos;", '"': "&quot;"})


def uid():
    return "{" + str(uuid.uuid4()).upper() + "}"


BR = "<run>\u00c6&#10;</run>"  # Tableau's serialised line break inside formatted-text

# ---------------------------------------------------------------- palette (lowercase hex only!)
RES, HCP, CHSP, RESP, TC = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
PROG = {"Residential aged care": RES, "Home Care Packages": HCP, "Home support (CHSP)": CHSP,
        "Residential respite": RESP, "Transition care": TC}
BANDS = {"65-74": "#9ec5f4", "75-84": "#3987e5", "85 and over": "#184f95"}
SEX = {"Male": RES, "Female": HCP}
WAFFLE = {"In permanent residential aged care": RES, "Not in residential aged care": "#e1e0d9"}
WFALL = {"Total": "#52514e", "Increase": RES, "Decrease": "#e34948"}
INK2, INK3, WS_BG, DASH_BG = "#52514e", "#898781", "#fcfcfb", "#f9f9f7"

# ---------------------------------------------------------------- datasources
# id -> (csv, {col: type override})   types: s / i / d inferred from data unless overridden
DS = {
    "popbands": ("pop_bands.csv", {}),
    "pyramid":  ("pop_pyramid.csv", {}),
    "progyear": ("care_rate_program_year.csv", {}),
    "ageprog":  ("care_rate_age_program.csv", {}),
    "waffle":   ("waffle.csv", {}),
    "remote":   ("remoteness.csv", {"year": "s"}),
    "wfall":    ("expenditure_waterfall.csv", {}),
    "spend":    ("expenditure.csv", {}),
    "stateyr":  ("state_year.csv", {}),
    "mekko":    ("marimekko.csv", {}),
}
DSID = {k: "federated.0" + (k + "0" * 23)[:23] for k in DS}
TWB_TYPE = {"s": "string", "i": "integer", "d": "real"}
HYPER_TYPE = {"s": SqlType.text(), "i": SqlType.big_int(), "d": SqlType.double()}


def infer(vals):
    kinds = set()
    for v in vals:
        if v == "":
            continue
        try:
            int(v); kinds.add("i"); continue
        except ValueError:
            pass
        try:
            float(v); kinds.add("d"); continue
        except ValueError:
            kinds.add("s")
    if "s" in kinds:
        return "s"
    if "d" in kinds:
        return "d"
    return "i"


SCHEMA, ROWS = {}, {}
for key, (csvname, over) in DS.items():
    with open(os.path.join(DATA_DIR, csvname), newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    cols = []
    for c in rows[0]:
        k = over.get(c) or infer([r[c] for r in rows])
        cols.append((c, k))
    SCHEMA[key], ROWS[key] = cols, rows

# extra calculated columns per datasource: key -> [(name, caption, formula)]
CALCS = {"wfall": [("Calculation_wf_size", "Waterfall size", "-[amount_m]")]}

# role/type for a column: dimensions for strings and named sort/id fields
DIM_INTS = {"year", "band_sort", "remoteness_sort", "row", "col", "cell", "point_id", "step", "pop_year"}


def role_type(col, kind):
    if kind == "s":
        return "dimension", "nominal"
    if col in DIM_INTS:
        return "dimension", "quantitative"
    return "measure", "quantitative"


def inst(key, col, kind, agg=None):
    """column-instance name for a field. agg None -> dimension 'none', else sum/avg/attr."""
    role, _ = role_type(col, kind)
    if agg is None and role == "dimension":
        suffix = "nk" if kind == "s" else "qk"
        return f"none:{col}:{suffix}"
    agg = agg or "sum"
    return f"{agg}:{col}:qk"


def kind_of(key, col):
    for c, k in SCHEMA[key]:
        if c == col:
            return k
    for n, cap, _ in CALCS.get(key, []):
        if n == col:
            return "d"
    raise KeyError(col)


def F(key, col, agg=None):
    """Fully qualified field reference [ds].[instance]."""
    return f"[{DSID[key]}].[{inst(key, col, kind_of(key, col), agg)}]"


def palette_xml(key, col, mapping, indent=8):
    pad = " " * indent
    maps = "".join(
        f"\n{pad}    <map to='{color}'>\n{pad}      <bucket>&quot;{esc(val)}&quot;</bucket>\n{pad}    </map>"
        for val, color in mapping.items())
    return (f"{pad}<style-rule element='mark'>\n"
            f"{pad}  <encoding attr='color' field='[{inst(key, col, 's')}]' type='palette'>{maps}\n"
            f"{pad}  </encoding>\n{pad}</style-rule>\n")


PALETTES = {  # key -> (col, mapping)
    "popbands": ("age_band", BANDS), "pyramid": ("sex", SEX), "progyear": ("programme", PROG),
    "waffle": ("category", WAFFLE), "wfall": ("type", WFALL), "stateyr": ("programme", PROG),
    "mekko": ("programme", PROG),
}


def datasource_xml(key):
    ds, (csvname, _) = DSID[key], DS[key]
    conn = ds.replace("federated.", "textscan.")
    caption = csvname[:-4]
    cols = SCHEMA[key]
    rel = "\n".join(f"            <column datatype='{TWB_TYPE[k]}' name='{c}' ordinal='{i}' />"
                    for i, (c, k) in enumerate(cols))
    defs = []
    for c, k in cols:
        role, typ = role_type(c, k)
        defs.append(f"      <column datatype='{TWB_TYPE[k]}' name='[{c}]' role='{role}' type='{typ}' />")
    for n, cap, formula in CALCS.get(key, []):
        defs.append(f"      <column caption='{esc(cap)}' datatype='real' name='[{n}]' role='measure' type='quantitative'>\n"
                    f"        <calculation class='tableau' formula='{esc(formula)}' />\n      </column>")
    hyper = ds.split(".")[1] + ".hyper"
    pal = ""
    if key in PALETTES:
        col, mapping = PALETTES[key]
        pal = "      <style>\n" + palette_xml(key, col, mapping) + "      </style>\n"
    return f"""    <datasource caption='{caption}' inline='true' name='{ds}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{caption}' name='{conn}'>
            <connection class='textscan' directory='{esc(DATA_DIR.replace(os.sep, "/"))}' filename='{csvname}' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='{conn}' name='{csvname}' table='[{caption}#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_AU' separator=','>
{rel}
          </columns>
        </relation>
      </connection>
      <aliases enabled='yes' />
{chr(10).join(defs)}
      <extract count='-1' enabled='true' object-id='' units='records' user-specific='false'>
        <connection access_mode='readonly' author-locale='en_US' class='hyper' dbname='Data/TableauTemp/{hyper}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' update-time='09/02/2026 06:00:00 PM' username='tableau_internal_user'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
      <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
{pal}      <semantic-values>
        <semantic-value key='[Country].[Name]' value='&quot;Australia&quot;' />
      </semantic-values>
    </datasource>
"""


# ---------------------------------------------------------------- worksheet helpers
def dep_xml(key, fields):
    """fields: list of (col, agg-or-None). Emits column defs + column-instances (deduped)."""
    ds = DSID[key]
    cols_seen, lines, inst_seen = set(), [], set()
    for col, agg in fields:
        k = kind_of(key, col)
        role, typ = role_type(col, k)
        if col not in cols_seen:
            cols_seen.add(col)
            calc = [c for c in CALCS.get(key, []) if c[0] == col]
            if calc:
                n, cap, formula = calc[0]
                lines.append(f"            <column caption='{esc(cap)}' datatype='real' name='[{n}]' role='measure' type='quantitative'>\n"
                             f"              <calculation class='tableau' formula='{esc(formula)}' />\n            </column>")
            else:
                lines.append(f"            <column datatype='{TWB_TYPE[k]}' name='[{col}]' role='{role}' type='{typ}' />")
    for col, agg in fields:
        k = kind_of(key, col)
        role, typ = role_type(col, k)
        name = inst(key, col, k, agg)
        if name in inst_seen:
            continue
        inst_seen.add(name)
        if agg is None and role == "dimension":
            deriv, t = "None", ("nominal" if k == "s" else "quantitative")
        else:
            deriv = {"sum": "Sum", "avg": "Avg", "attr": "Attribute", None: "Sum"}[agg]
            t = "quantitative"
        lines.append(f"            <column-instance column='[{col}]' derivation='{deriv}' name='[{name}]' pivot='key' type='{t}' />")
    return "\n".join(lines)


def filter_in(key, col, members):
    f = F(key, col)
    lvl = f"[{inst(key, col, 's')}]"
    if len(members) == 1:
        return (f"          <filter class='categorical' column='{f}'>\n"
                f"            <groupfilter function='member' level='{lvl}' member='&quot;{esc(members[0])}&quot;' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />\n"
                f"          </filter>")
    ms = "\n".join(f"              <groupfilter function='member' level='{lvl}' member='&quot;{esc(m)}&quot;' />" for m in members)
    return (f"          <filter class='categorical' column='{f}'>\n"
            f"            <groupfilter function='union' user:op='manual'>\n{ms}\n            </groupfilter>\n"
            f"          </filter>")


def filter_not(key, col, member):
    f = F(key, col)
    lvl = f"[{inst(key, col, 's')}]"
    return (f"          <filter class='categorical' column='{f}'>\n"
            f"            <groupfilter function='except' user:ui-domain='database' user:ui-enumeration='exclusive' user:ui-marker='enumerate'>\n"
            f"              <groupfilter function='level-members' level='{lvl}' />\n"
            f"              <groupfilter function='member' level='{lvl}' member='&quot;{esc(member)}&quot;' />\n"
            f"            </groupfilter>\n          </filter>")


def sort_by(key, col, using, direction="ASC"):
    return f"          <sort class='computed' column='{F(key, col)}' direction='{direction}' using='{F(key, using, 'sum')}' />"


def title_xml(headline, finding=None):
    runs = f"<run bold='true' fontname='Tableau Medium' fontsize='13'>{esc(headline)}</run>"
    if finding:
        runs += BR + f"<run fontcolor='{INK2}' fontname='Tableau Book' fontsize='10' italic='true'>{esc(finding)}</run>"
    return f"      <layout-options>\n        <title>\n          <formatted-text>\n            {runs}\n          </formatted-text>\n        </title>\n      </layout-options>"


def tooltip_xml(parts):
    """parts: list of str (literal) or ('f', fieldref) or 'BR'."""
    runs = []
    for p in parts:
        if p == "BR":
            runs.append(BR)
        elif isinstance(p, tuple):
            runs.append(f"<run bold='true'><![CDATA[<{p[1]}>]]></run>")
        else:
            runs.append(f"<run>{esc(p)}</run>")
    return "            <customized-tooltip>\n              <formatted-text>\n                " + "\n                ".join(runs) + "\n              </formatted-text>\n            </customized-tooltip>"


def worksheet_xml(name, key, title, deps, rows, cols, mark, encodings, *, filters=(), sorts=(),
                  ws_style="", pane_formats=(), reference_lines=(), tooltip=None, finding=None):
    ds = DSID[key]
    caption = DS[key][0][:-4]
    enc = "\n".join(f"              <{kind} column='{ref}' />" for kind, ref in encodings)
    fmts = "\n".join(f"                <format attr='{a}' value='{v}' />" for a, v in pane_formats)
    pane_style = f"\n            <style>\n              <style-rule element='mark'>\n{fmts}\n              </style-rule>\n            </style>" if pane_formats else ""
    refl = ("\n" + "\n".join(reference_lines)) if reference_lines else ""
    tt = ("\n" + tooltip) if tooltip else ""
    view_extra = "\n".join(list(filters) + list(sorts))
    if view_extra:
        view_extra = "\n" + view_extra
    style_block = f"        <style>\n          <style-rule element='table'>\n            <format attr='background-color' value='{WS_BG}' />\n          </style-rule>\n{ws_style}        </style>"
    return f"""    <worksheet name='{esc(name)}'>
{title_xml(title, finding)}
      <table>
        <view>
          <datasources>
            <datasource caption='{caption}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
{dep_xml(key, deps)}
          </datasource-dependencies>{view_extra}
          <aggregation value='true' />
        </view>
{style_block}
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />
            <encodings>
{enc}
            </encodings>{refl}{tt}{pane_style}
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
      <simple-id uuid='{uid()}' />
    </worksheet>
"""


def axis_fixed(key, col, agg, scope, lo, hi, title=None):
    f = F(key, col, agg)
    s = f"            <encoding attr='space' class='0' field='{f}' field-type='quantitative' max='{hi}' min='{lo}' range-type='fixed' scope='{scope}' type='space' />\n"
    if title is not None:
        s += f"            <format attr='title' class='0' field='{f}' scope='{scope}' value='{esc(title)}' />\n"
    return s


def axis_title(key, col, agg, scope, title):
    return f"            <format attr='title' class='0' field='{F(key, col, agg)}' scope='{scope}' value='{esc(title)}' />\n"


def axis_hide(key, col, agg, scope):
    return f"            <format attr='display' class='0' field='{F(key, col, agg)}' scope='{scope}' value='false' />\n"


def axis_rule(*parts):
    return "          <style-rule element='axis'>\n" + "".join(parts) + "          </style-rule>\n"


def label_fmt(key, col, agg, fmt):
    return f"          <style-rule element='label'>\n            <format attr='text-format' field='{F(key, col, agg)}' value='{fmt}' />\n          </style-rule>\n"


def header_hide(key, col):
    return f"          <style-rule element='header'>\n            <format attr='display' field='{F(key, col)}' value='false' />\n          </style-rule>\n"


LABELS_ON = [("mark-labels-show", "true")]
LINE_END_LABELS = [("mark-labels-show", "true"), ("mark-labels-mode", "line-ends"),
                   ("mark-labels-line-last", "true"), ("mark-labels-line-first", "false"),
                   ("mark-labels-cull", "false"), ("size", "1.5")]
SLOPE_LABELS = [("mark-labels-show", "true"), ("mark-labels-mode", "line-ends"),
                ("mark-labels-line-last", "true"), ("mark-labels-line-first", "true"),
                ("mark-labels-cull", "false"), ("size", "1.6"), ("mark-markers-mode", "all")]

N0 = "n#,##0;-#,##0"
N1 = "n#,##0.0;-#,##0.0"
MONEY_M = "n&quot;$&quot;#,##0&quot;m&quot;;-&quot;$&quot;#,##0&quot;m&quot;"

WS = []  # (sheet name, xml)

# 01 stacked area ---------------------------------------------------------------
k = "popbands"
WS.append(("01 Older Australians", worksheet_xml(
    "01 Older Australians", k,
    "Older Australians, 1971 to 2045",
    deps=[("year", None), ("age_band", None), ("band_type", None), ("population", "sum")],
    rows=F(k, "population", "sum"), cols=F(k, "year"), mark="Area",
    encodings=[("color", F(k, "age_band"))],
    filters=[filter_in(k, "band_type", ["Exclusive"])],
    sorts=[sort_by(k, "age_band", "population", "ASC")],  # smallest band (85+) first = top of stack
    ws_style=axis_rule(axis_fixed(k, "year", None, "cols", 1970, 2046, "Year (30 June)"),
                       axis_title(k, "population", "sum", "rows", "People aged 65 and over")),
    reference_lines=[f"            <reference-line axis-column='{F(k, 'year')}' enable-instant-analytics='true' formula='constant' id='refline0' label-type='none' scope='per-pane' value='2025' value-column='{F(k, 'year')}' z-order='1' />"],
    tooltip=tooltip_xml([("f", F(k, "year")), ": ", ("f", F(k, "population", "sum")), " Australians aged ", ("f", F(k, "age_band")), ".", "BR",
                         "Right of the line: ABS Series B projection."]),
    finding="Right of the line is projected. Between 2025 and 2045 the 65 to 74 group grows by about a quarter; the 85 and over group more than doubles.")))

# 02 pyramid --------------------------------------------------------------------
k = "pyramid"
WS.append(("02 Population pyramid", worksheet_xml(
    "02 Population pyramid", k,
    "Population pyramid, 2025 and 2045",
    deps=[("series", None), ("sex", None), ("age_band", None), ("signed_population", "sum"), ("band_sort", "sum"), ("value", "sum")],
    rows=F(k, "age_band"), cols=f"({F(k, 'series')} / {F(k, 'signed_population', 'sum')})", mark="Bar",
    encodings=[("color", F(k, "sex")), ("tooltip", F(k, "value", "sum"))],
    sorts=[sort_by(k, "age_band", "band_sort", "DESC")],
    ws_style=axis_rule(axis_title(k, "signed_population", "sum", "cols", "People (men left, women right)")),
    tooltip=tooltip_xml([("f", F(k, "value", "sum")), " ", ("f", F(k, "sex")), " Australians aged ", ("f", F(k, "age_band")), ", ", ("f", F(k, "series")), "."]),
    finding="The top thickens. Women outnumber men three to two above 85, and it is women who fill residential care: 227 per 1,000 against 135 for men.")))

# 03 multi-line -----------------------------------------------------------------
k = "progyear"
WS.append(("03 Where people are cared for", worksheet_xml(
    "03 Where people are cared for", k,
    "Where older Australians are cared for, 2017-18 to 2024-25",
    deps=[("year", None), ("programme", None), ("rate_per_1000", "sum")],
    rows=F(k, "rate_per_1000", "sum"), cols=F(k, "year"), mark="Line",
    encodings=[("color", F(k, "programme")), ("text", F(k, "programme"))],
    ws_style=axis_rule(axis_title(k, "rate_per_1000", "sum", "rows", "Recipients per 1,000 people aged 65 and over")),
    pane_formats=LINE_END_LABELS,
    tooltip=tooltip_xml(["In ", ("f", F(k, "year")), ", ", ("f", F(k, "rate_per_1000", "sum")), " of every 1,000 older Australians used ", ("f", F(k, "programme")), "."]),
    finding="2021-22: for the first time, more older Australians were on a Home Care Package than in permanent residential care.")))

# 04 slope ----------------------------------------------------------------------
WS.append(("04 Seven years of change", worksheet_xml(
    "04 Seven years of change", k,
    "Seven years of change, 2017-18 to 2024-25",
    deps=[("year", None), ("programme", None), ("rate_per_1000", "sum")],
    rows=F(k, "rate_per_1000", "sum"), cols=F(k, "year"), mark="Line",
    encodings=[("color", F(k, "programme")), ("text", F(k, "programme")), ("text", F(k, "rate_per_1000", "sum"))],
    filters=[filter_in(k, "year", ["2017-18", "2024-25"])],
    ws_style=axis_rule(axis_hide(k, "rate_per_1000", "sum", "rows")) + label_fmt(k, "rate_per_1000", "sum", N0),
    pane_formats=SLOPE_LABELS,
    tooltip=tooltip_xml([("f", F(k, "programme")), " in ", ("f", F(k, "year")), ": ", ("f", F(k, "rate_per_1000", "sum")), " recipients per 1,000 people aged 65 and over."]),
    finding="Home Care Packages +147%. Home support -13%. Permanent residential care -11%.")))

# 05 heatmap --------------------------------------------------------------------
k = "ageprog"
WS.append(("05 Care use by age", worksheet_xml(
    "05 Care use by age", k,
    "Care use by age and programme, 2024-25",
    deps=[("age_band", None), ("programme", None), ("rate_per_1000", "sum"), ("band_sort", "sum")],
    rows=F(k, "age_band"), cols=F(k, "programme"), mark="Square",
    encodings=[("color", F(k, "rate_per_1000", "sum")), ("text", F(k, "rate_per_1000", "sum"))],
    sorts=[sort_by(k, "age_band", "band_sort", "ASC")],
    ws_style=(f"          <style-rule element='mark'>\n            <encoding attr='color' field='{F(k, 'rate_per_1000', 'sum')}' palette='blue_10_0' type='interpolated' />\n          </style-rule>\n"
              + label_fmt(k, "rate_per_1000", "sum", N0)),
    pane_formats=[("mark-labels-show", "true"), ("has-stroke", "true"), ("stroke-color", "#ffffff")],
    tooltip=tooltip_xml(["Of every 1,000 Australians aged ", ("f", F(k, "age_band")), ", ", ("f", F(k, "rate_per_1000", "sum")), " used ", ("f", F(k, "programme")), " during 2024-25."]),
    finding="People per 1,000 in each age group. Four in 1,000 aged 65 to 69 used permanent residential care. At 90 and over: 414.")))

# 06 waffle ---------------------------------------------------------------------
k = "waffle"
WS.append(("06 Of every 100 aged 90+", worksheet_xml(
    "06 Of every 100 aged 90+", k,
    "Of every 100 Australians aged 90 and over, 2024-25",
    deps=[("row", None), ("col", None), ("category", None), ("cell", "sum")],
    rows=F(k, "row"), cols=F(k, "col"), mark="Square",
    encodings=[("color", F(k, "category"))],
    ws_style=axis_rule(axis_hide(k, "row", None, "rows"), axis_hide(k, "col", None, "cols")),
    pane_formats=[("has-stroke", "true"), ("stroke-color", "#ffffff"), ("size", "1.0")],
    tooltip=tooltip_xml(["Each square is one person in 100 aged 90 and over.", "BR", ("f", F(k, "category"))]),
    finding="41 spent time in permanent residential aged care during the year. The other 59 did not.")))

# 07 remoteness bar -------------------------------------------------------------
k = "remote"
WS.append(("07 Places by remoteness", worksheet_xml(
    "07 Places by remoteness", k,
    "Residential places per 1,000 people aged 65 and over, by remoteness, 2025",
    deps=[("year", None), ("remoteness", None), ("remoteness_sort", "sum"), ("places_per_1000_aged_65plus", "sum")],
    rows=F(k, "remoteness"), cols=F(k, "places_per_1000_aged_65plus", "sum"), mark="Bar",
    encodings=[("text", F(k, "places_per_1000_aged_65plus", "sum"))],
    filters=[filter_in(k, "year", ["2025"])],
    sorts=[sort_by(k, "remoteness", "remoteness_sort", "ASC")],
    ws_style=axis_rule(axis_title(k, "places_per_1000_aged_65plus", "sum", "cols", "Residential places per 1,000 people aged 65 and over"))
             + label_fmt(k, "places_per_1000_aged_65plus", "sum", N1),
    pane_formats=[("mark-labels-show", "true"), ("mark-color", RES)],
    tooltip=tooltip_xml([("f", F(k, "remoteness")), ": ", ("f", F(k, "places_per_1000_aged_65plus", "sum")), " residential aged care places for every 1,000 residents aged 65 and over, 30 June 2025."]),
    finding="48 places per 1,000 older people in the major cities. 10.5 in very remote Australia.")))

# 08 bullet ---------------------------------------------------------------------
WS.append(("08 Occupancy vs national", worksheet_xml(
    "08 Occupancy vs national", k,
    "Occupancy of residential places against the national rate, 2025",
    deps=[("year", None), ("remoteness", None), ("remoteness_sort", "sum"), ("occupancy_pct", "sum"), ("national_occupancy_pct", "sum")],
    rows=F(k, "remoteness"), cols=F(k, "occupancy_pct", "sum"), mark="Bar",
    encodings=[("text", F(k, "occupancy_pct", "sum")), ("lod", F(k, "national_occupancy_pct", "sum"))],
    filters=[filter_in(k, "year", ["2025"])],
    sorts=[sort_by(k, "remoteness", "remoteness_sort", "ASC")],
    ws_style=axis_rule(axis_fixed(k, "occupancy_pct", "sum", "cols", 60, 100, "Occupied places (%)  -  axis starts at 60%"))
             + label_fmt(k, "occupancy_pct", "sum", N1),
    pane_formats=[("mark-labels-show", "true"), ("mark-color", RES)],
    reference_lines=[f"            <reference-line axis-column='{F(k, 'occupancy_pct', 'sum')}' enable-instant-analytics='true' formula='average' id='refline0' label-type='value' scope='per-pane' value-column='{F(k, 'national_occupancy_pct', 'sum')}' z-order='1' />"],
    tooltip=tooltip_xml([("f", F(k, "remoteness")), ": ", ("f", F(k, "occupancy_pct", "sum")), "% of residential places were occupied at 30 June 2025.", "BR",
                         "National rate: ", ("f", F(k, "national_occupancy_pct", "sum")), "% (weighted by places)."]),
    finding="Very remote services run 13.7 points below the national 90.0%, the widest gap of any area. Fewer places, and more of them empty.")))

# 09 waterfall ------------------------------------------------------------------
k = "wfall"
WS.append(("09 Where the extra billions went", worksheet_xml(
    "09 Where the extra billions went", k,
    "Where the extra $19.5 billion went, 2014-15 to 2024-25 (real dollars)",
    deps=[("label", None), ("type", None), ("step", "sum"), ("running_total_m", "sum"), ("amount_m", "sum"), ("Calculation_wf_size", "sum")],
    rows=F(k, "running_total_m", "sum"), cols=F(k, "label"), mark="GanttBar",
    encodings=[("color", F(k, "type")), ("size", F(k, "Calculation_wf_size", "sum")), ("text", F(k, "amount_m", "sum"))],
    sorts=[sort_by(k, "label", "step", "ASC")],
    ws_style=axis_rule(axis_fixed(k, "running_total_m", "sum", "rows", 0, 42000, "Government spending ($ million, 2024-25 dollars)"))
             + label_fmt(k, "amount_m", "sum", MONEY_M),
    pane_formats=[("mark-labels-show", "true")],
    tooltip=tooltip_xml([("f", F(k, "label")), ": ", ("f", F(k, "amount_m", "sum")), " million.", "BR", "Running total: ", ("f", F(k, "running_total_m", "sum")), " million."]),
    finding="Residential and flexible care added $10.9bn. Home care and support added $7.7bn, from a base less than half the size. Total reaches $39.8bn.")))

# 10 treemap --------------------------------------------------------------------
k = "spend"
WS.append(("10 What the money buys", worksheet_xml(
    "10 What the money buys", k,
    "What the money buys, 2024-25",
    deps=[("year", None), ("programme", None), ("real_expenditure_m", "sum")],
    rows="", cols="", mark="Square",
    encodings=[("size", F(k, "real_expenditure_m", "sum")), ("text", F(k, "programme")), ("text", F(k, "real_expenditure_m", "sum"))],
    filters=[filter_in(k, "year", ["2024-25"])],
    ws_style=label_fmt(k, "real_expenditure_m", "sum", MONEY_M),
    pane_formats=[("mark-labels-show", "true"), ("mark-color", RES), ("has-stroke", "true"), ("stroke-color", WS_BG)],
    tooltip=tooltip_xml([("f", F(k, "programme")), ": ", ("f", F(k, "real_expenditure_m", "sum")), " million of government spending in 2024-25."]),
    finding="Residential and flexible care takes 64 cents in every dollar. Home care and support takes 32.")))

# 11 grouped bar ----------------------------------------------------------------
k = "stateyr"
WS.append(("11 Two programmes by state", worksheet_xml(
    "11 Two programmes by state", k,
    "Two programmes, eight jurisdictions, 2024-25",
    deps=[("year", None), ("state", None), ("programme", None), ("rate_per_1000", "sum")],
    rows=F(k, "rate_per_1000", "sum"), cols=f"({F(k, 'state')} / {F(k, 'programme')})", mark="Bar",
    encodings=[("color", F(k, "programme")), ("text", F(k, "rate_per_1000", "sum"))],
    filters=[filter_in(k, "year", ["2024-25"]), filter_not(k, "state", "Aust"),
             filter_in(k, "programme", ["Residential aged care", "Home Care Packages"])],
    sorts=[sort_by(k, "state", "rate_per_1000", "DESC")],
    ws_style=axis_rule(axis_title(k, "rate_per_1000", "sum", "rows", "Recipients per 1,000 people aged 65 and over"))
             + label_fmt(k, "rate_per_1000", "sum", N0) + header_hide(k, "programme"),
    pane_formats=[("mark-labels-show", "true")],
    tooltip=tooltip_xml(["In 2024-25, ", ("f", F(k, "rate_per_1000", "sum")), " of every 1,000 people aged 65 and over in ", ("f", F(k, "state")), " used ", ("f", F(k, "programme")), ".", "BR",
                         "Australia: 51.5 residential, 69.8 home care."]),
    finding="South Australia leads on both. The Northern Territory sits at 18.8 per 1,000 on residential care, a third of every other jurisdiction.")))

# 12 marimekko ------------------------------------------------------------------
k = "mekko"
WS.append(("12 Care mix by population", worksheet_xml(
    "12 Care mix by population", k,
    "Care mix by state, sized by older population, 2024-25",
    deps=[("x", "avg"), ("y", "avg"), ("point_id", None), ("state", None), ("programme", None),
          ("programme_share_pct", "avg"), ("population_65plus_000", "avg"), ("rate_per_1000", "avg")],
    rows=F(k, "y", "avg"), cols=F(k, "x", "avg"), mark="Polygon",
    encodings=[("path", F(k, "point_id")), ("color", F(k, "programme")), ("lod", F(k, "state")),
               ("tooltip", F(k, "programme_share_pct", "avg")), ("tooltip", F(k, "population_65plus_000", "avg")), ("tooltip", F(k, "rate_per_1000", "avg"))],
    ws_style=axis_rule(axis_fixed(k, "x", "avg", "cols", 0, 100, "Share of Australia's population aged 65 and over (%)  -  NSW, Vic, Qld, WA, SA, Tas, ACT, NT"),
                       axis_fixed(k, "y", "avg", "rows", 0, 100, "Share of aged care use (%)")),
    pane_formats=[("has-stroke", "true"), ("stroke-color", "#ffffff")],
    tooltip=tooltip_xml([("f", F(k, "state")), " - ", ("f", F(k, "programme")), "BR",
                         ("f", F(k, "programme_share_pct", "avg")), "% of the state's aged care use (", ("f", F(k, "rate_per_1000", "avg")), " per 1,000).", "BR",
                         ("f", F(k, "population_65plus_000", "avg")), " thousand residents aged 65 and over."]),
    finding="Column width is each state's share of older Australians. NSW, Vic and Qld hold 77%; the Northern Territory 0.5%. Shares describe aged care use, not people.")))

# ---------------------------------------------------------------- dashboard
CW, CH = 1200, 4700  # canvas px
MARGIN, GUTTER = 30, 30
COLW = (CW - 2 * MARGIN - GUTTER) // 2  # 555


def zone_geom(x, y, w, h):
    return (f"h='{round(h / CH * 100000)}' w='{round(w / CW * 100000)}' "
            f"x='{round(x / CW * 100000)}' y='{round(y / CH * 100000)}'")


_zid = [10]


def zid():
    _zid[0] += 1
    return _zid[0]


def text_zone(x, y, w, h, runs):
    return (f"        <zone forceUpdate='true' {zone_geom(x, y, w, h)} id='{zid()}' type-v2='text'>\n"
            f"          <formatted-text>\n            " + "\n            ".join(runs) + "\n          </formatted-text>\n        </zone>")


def sheet_zone(x, y, w, h, name):
    return f"        <zone {zone_geom(x, y, w, h)} id='{zid()}' name='{esc(name)}' />"


def R(text, *, font="Tableau Book", size=11, bold=False, italic=False, color="#0b0b0b"):
    attrs = f"fontname='{font}' fontsize='{size}' fontcolor='{color}'"
    if bold:
        attrs += " bold='true'"
    if italic:
        attrs += " italic='true'"
    return f"<run {attrs}>{esc(text)}</run>"


def para(*texts, size=11, color=INK2, gap=True):
    runs = []
    for i, t in enumerate(texts):
        if i:
            runs += [BR, BR] if gap else [BR]
        runs.append(R(t, size=size, color=color))
    return runs


def heading(num, text):
    return [R(f"{num}  ", font="Tableau Medium", size=12, color=RES), R(text, font="Georgia", size=19, bold=True)]


COPY = {
    1: ("An ageing nation",
        ["Australia's older population has grown steadily for fifty years, but the age groups inside it have not grown at the same pace. Between 2025 and 2045, the number of people aged 65 to 74 grows by about a quarter. The number aged 85 and over more than doubles.",
         "That gap matters, because the need for aged care rises steeply with age. Demand is driven by the smallest and fastest-growing group, not by the headline number of older Australians."]),
    2: ("Where people are cared for",
        ["A decade ago, an older Australian was roughly twice as likely to be living in permanent residential care as to be receiving a Home Care Package at home. That is no longer true. Home Care Packages rose from 28 recipients for every 1,000 older Australians in 2017-18 to 70 in 2024-25, while permanent residential care fell from 58 to 51. The two lines crossed in 2021-22. Home support, the lightest form of help, remains the most common of all, but it too has been declining.",
         "These are drawn as separate lines rather than stacked on top of one another, because a person can use more than one programme in the same year. Stacking them would count some people twice."]),
    3: ("Who uses aged care",
        ["Age, more than anything else, decides whether someone uses aged care. Among Australians aged 65 to 69, four in every thousand spent time in permanent residential care during 2024-25. Among those aged 90 and over, it was 414 in every thousand, more than a hundred times the rate. Home Care Packages and home support climb almost as steeply.",
         "Put a different way: of every 100 Australians aged 90 and over, 41 spent time in permanent residential aged care last year. Many of the rest were receiving help at home. At that age, 308 in every 1,000 held a Home Care Package and 397 used home support."]),
    4: ("City and country gap",
        ["Residential aged care is not spread evenly across the country. For every 1,000 people aged 65 and over, major cities have 48 residential places. Very remote Australia has 10.5, roughly a fifth as many.",
         "The places that do exist outside the cities are also the least used. Across Australia, 90 per cent of residential places were occupied in 2025. In very remote areas it was 76 per cent, nearly 14 percentage points below the national figure and the widest gap of any area. Fewer places, and a larger share of them sitting empty. This data shows the pattern; it cannot tell us the cause."]),
    5: ("Paying for it",
        ["Governments spent $39.8 billion on aged care in 2024-25. A decade earlier, counted in the same dollars, it was $20.3 billion. Almost all of that $19.5 billion increase came from two places: residential and flexible care added $10.9 billion, and home care and support added $7.7 billion.",
         "Home care grew far faster in proportion. It is now two and a half times its 2014-15 size, against one and four-fifths for residential care, the spending signature of the shift shown earlier. Residential care still takes 64 cents in every dollar."]),
    6: ("State by state",
        ["Every state and territory leans on a different mix. South Australia has both the highest rate of permanent residential care, at 55 people per 1,000 aged 65 and over, and the highest rate of Home Care Packages, at 81.",
         "The Northern Territory sits far below every other jurisdiction on residential care, at 19 per 1,000. It also hosts 21 of Australia's 47 National Aboriginal and Torres Strait Islander Flexible Aged Care services, care that is counted outside these figures. Reading the Territory's low number as a simple shortage would be a mistake."]),
}
SHEET_PAIRS = {1: (WS[0][0], WS[1][0]), 2: (WS[2][0], WS[3][0]), 3: (WS[4][0], WS[5][0]),
               4: (WS[6][0], WS[7][0]), 5: (WS[8][0], WS[9][0]), 6: (WS[10][0], WS[11][0])}

zones = []
y = 24
# header
zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 150, [
    R("FIT3179 DATA VISUALISATION 1  ·  AGED CARE IN AUSTRALIA", size=8, color=INK3), BR,
    R("Growing Old in Australia", font="Georgia", size=34, bold=True), BR,
    R("How a nation prepares to age", font="Georgia", size=19, italic=True, color=INK2), BR,
    R("Ian Leong  ·  34423680  ·  September 2026", size=9, color=INK3)]))
y += 162
# intro
zones.append(text_zone(MARGIN, y, 690, 190, para(
    "Australia is getting older, and it is getting older fastest at the very top. In 1971, one Australian in twelve had passed 65. Today it is more than one in six, and by 2045 it will be better than one in five, while the number of people aged 85 and over, the group that relies on aged care most heavily, will have more than doubled.",
    "This page follows what that means for aged care: who uses it, how the balance between a nursing home and care at home has shifted, where access is thinnest, and what it all costs.")))
fig = lambda n, t: [R(n, font="Georgia", size=22, bold=True, color=RES), BR, R(t, size=10, color=INK2)]
zones.append(text_zone(750, y, CW - MARGIN - 750, 190,
                       fig("1 in 5.7", "Australians aged 65 or over in 2025. In 1971 it was 1 in 12.") + [BR, BR]
                       + fig("1.39 million", "Australians expected to be 85 or over in 2045, up from 603,000 today.") + [BR, BR]
                       + fig("$39.8 billion", "Government spending on aged care in 2024-25, almost double a decade earlier after inflation.")))
y += 210
CHART_H = 430
for n in range(1, 7):
    title, paras = COPY[n]
    zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 40, heading(f"0{n + 1}", title)))
    y += 44
    zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 118, para(*paras, size=10, gap=False)))
    y += 126
    left, right = SHEET_PAIRS[n]
    zones.append(sheet_zone(MARGIN, y, COLW, CHART_H, left))
    zones.append(sheet_zone(MARGIN + COLW + GUTTER, y, COLW, CHART_H, right))
    y += CHART_H + 34
# conclusion
zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 40, heading("08", "What today's patterns would produce")))
y += 44
zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 170, para(
    "Three things are happening at once. The number of Australians aged 85 and over will more than double by 2045. The system has been steadily moving people out of residential care and into care at home. And the bill has already doubled in ten years.",
    "If Australians used aged care in 2045 exactly as they did in 2024-25, and only the population changed, permanent residential care would need to serve about 533,000 people, up from roughly 261,000 today. Home Care Packages would need to serve about 662,000, up from 354,000.",
    "That is not a forecast. It is simply what today's patterns would produce if nothing else moved. Everything that could move, how many places get built, how many people can be found to staff them, and how much governments are willing to spend, has to be decided around it.",
    size=10, gap=False)))
y += 190
# footer
zones.append(text_zone(MARGIN, y, CW - 2 * MARGIN, 190, [
    R("Growing Old in Australia  ·  Ian Leong (34423680)  ·  FIT3179 Data Visualisation, Monash University  ·  September 2026", size=8, bold=True, color=INK2), BR, BR,
    R("Data sources.", size=8, bold=True, color=INK2), BR,
    R("Productivity Commission, Report on Government Services 2026, Part F Section 14: Aged care services. pc.gov.au/ongoing/report-on-government-services/community-services/aged-care-services", size=8, color=INK3), BR,
    R("Australian Bureau of Statistics, National, state and territory population, December 2025, Table 59. abs.gov.au/statistics/people/population/national-state-and-territory-population", size=8, color=INK3), BR,
    R("Australian Bureau of Statistics, Population Projections, Australia, 2022 (base) to 2071, Series B, Table B9. abs.gov.au/statistics/people/population/population-projections-australia", size=8, color=INK3), BR,
    R("AIHW / Department of Health, Disability and Ageing, Aged Care Data Snapshot 2025. gen-agedcaredata.gov.au", size=8, color=INK3), BR, BR,
    R("Aged care figures are financial years to 30 June 2025 (the most recent published). Population is at 30 June. Spending is in constant 2024-25 dollars. Rates are people per 1,000 residents aged 65 and over.", size=8, color=INK3), BR, BR,
    R("Use of generative AI. Generative AI (Claude) was used to help locate and reshape the source data, to draft and edit the narrative text, and to review the visual design. All charts were designed and built by the author.", size=8, color=INK3)]))
y += 200
assert y <= CH, y

dashboard_xml = f"""  <dashboards>
    <dashboard name='{esc(DASH)}'>
      <style>
        <style-rule element='table'>
          <format attr='background-color' value='{DASH_BG}' />
        </style-rule>
      </style>
      <size maxheight='{CH}' maxwidth='{CW}' minheight='{CH}' minwidth='{CW}' sizing-mode='fixed' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='100000' id='2' param='vert' type-v2='layout-flow' w='100000' x='0' y='0' />
        </zone>
{chr(10).join(zones)}
      </zones>
      <simple-id uuid='{uid()}' />
    </dashboard>
  </dashboards>
"""

# highlight action on programme across the sheets that carry it
PROG_SHEETS = [WS[2][0], WS[3][0], WS[10][0], WS[11][0]]
NON_PROG = [n for n, _ in WS if n not in PROG_SHEETS]
actions_xml = f"""  <actions>
    <action caption='Highlight programme' name='[Action1_{uuid.uuid4().hex.upper()}]'>
      <activation auto-clear='true' type='on-hover' />
      <source dashboard='{esc(DASH)}' type='sheet'>
{chr(10).join(f"        <exclude-sheet name='{esc(n)}' />" for n in NON_PROG)}
      </source>
      <command command='tsc:brush'>
        <param name='exclude' value='{esc(",".join(NON_PROG))}' />
        <param name='field-captions' value='programme' />
        <param name='target' value='{esc(DASH)}' />
      </command>
    </action>
  </actions>
"""


# ---------------------------------------------------------------- windows
def ws_window(name):
    return f"""    <window class='worksheet' name='{esc(name)}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
          <strip size='30'>
            <card type='title' />
          </strip>
        </edge>
      </cards>
      <viewpoint>
        <zoom type='entire-view' />
      </viewpoint>
      <simple-id uuid='{uid()}' />
    </window>
"""


dash_window = f"""    <window class='dashboard' maximized='true' name='{esc(DASH)}'>
      <viewpoints>
{chr(10).join(f"        <viewpoint name='{esc(n)}'>{chr(10)}          <zoom type='entire-view' />{chr(10)}        </viewpoint>" for n, _ in WS)}
      </viewpoints>
      <active id='-1' />
      <simple-id uuid='{uid()}' />
    </window>
"""

HEAD = """<?xml version='1.0' encoding='utf-8' ?>

<!-- build 20262.26.0819.2015                               -->
<workbook original-version='18.1' source-build='2026.2.2 (20262.26.0819.2015)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <AnimationOnByDefault />
    <MarkAnimation />
    <ObjectModelEncapsulateLegacy />
    <ObjectModelExtractV2 />
    <ObjectModelTableType />
    <SchemaViewerObjectModel />
    <SheetIdentifierTracking />
    <VConnDownstreamExtractsWithWarnings />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
"""


def assemble(with_dashboard):
    s = HEAD
    s += "  <datasources>\n" + "".join(datasource_xml(k) for k in DS) + "  </datasources>\n"
    if with_dashboard:
        s += actions_xml
    s += "  <worksheets>\n" + "".join(x for _, x in WS) + "  </worksheets>\n"
    if with_dashboard:
        s += dashboard_xml
    s += "  <windows source-height='69'>\n" + "".join(ws_window(n) for n, _ in WS)
    if with_dashboard:
        s += dash_window
    s += "  </windows>\n</workbook>\n"
    return s


# ---------------------------------------------------------------- hyper extracts
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    for key in DS:
        hyper_path = os.path.join(HYPER_DIR, DSID[key].split(".")[1] + ".hyper")
        if os.path.exists(hyper_path):
            os.remove(hyper_path)
        cols = SCHEMA[key]
        table = TableDefinition(TableName("Extract", "Extract"),
                                [TableDefinition.Column(c, HYPER_TYPE[k]) for c, k in cols])
        with Connection(hp.endpoint, hyper_path, CreateMode.CREATE_AND_REPLACE) as conn:
            conn.catalog.create_schema("Extract")
            conn.catalog.create_table(table)
            data = []
            for r in ROWS[key]:
                row = []
                for c, k in cols:
                    v = r[c]
                    if v == "":
                        row.append(None)
                    elif k == "i":
                        row.append(int(float(v)))
                    elif k == "d":
                        row.append(float(v))
                    else:
                        row.append(v)
                data.append(row)
            with Inserter(conn, table) as ins:
                ins.add_rows(data)
                ins.execute()
        print(f"hyper {key:9s} {len(data):4d} rows  {[c for c, _ in cols]}")


def write_twbx(twb_text, twb_name, twbx_name):
    twb_path = os.path.join(WORK, twb_name)
    with open(twb_path, "w", encoding="utf-8") as f:
        f.write(twb_text)
    ET.parse(twb_path)  # well-formedness check
    out = os.path.join(OUT_DIR, twbx_name)
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(twb_path, twb_name)
        for root, _, files in os.walk(os.path.join(WORK, "Data")):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, WORK))
    print("wrote", out, os.path.getsize(out), "bytes")


write_twbx(assemble(True), f"{NAME}.twb", f"{NAME}.twbx")
write_twbx(assemble(False), f"{NAME} (sheets only).twb", f"{NAME} (sheets only).twbx")

# sanity: every hex colour lowercase
import re
bad = [m for m in re.findall(r"#[0-9A-Fa-f]{6}", assemble(True)) if m != m.lower()]
print("uppercase hex colours:", bad)
