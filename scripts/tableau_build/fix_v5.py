r"""v5 pass (7 Sept 2026): full forms everywhere, Marimekko replaced by a bump chart.

Input : out/Growing Old in Australia.twb  (the v4 output; run fix_v4.py first)
        v3/Data/TableauTemp/*.hyper        (extracts for the ten existing datasources)
        ../data/state_year.csv             (source of the bump data)
Output: out/Growing Old in Australia v5.twbx
        ../data/bump.csv                   (new datasource, also written to the extract)

Changes
  * every abbreviation in visible text expanded (state codes, ABS, AIHW, 65+, bn, $ million)
  * state codes aliased to full names in the dumbbell datasource
  * age bands "90+" / "100+" aliased to "90 and over" / "100 and over"
  * chart 12 is now a bump chart: Home Care Package recipients per 1,000 aged 65 and over,
    states ranked each year 2017-18 to 2024-25, full state names at the line ends
"""
import re, zipfile, os, csv, uuid, hashlib, shutil
from collections import defaultdict
from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter, SqlType,
                             TableDefinition, TableName, Telemetry)

SRC = "out/Growing Old in Australia.twb"
OUT_DIR = "out"
DATA_DIR = os.path.abspath("../../data/out")
s = open(SRC, encoding="utf-8").read()

def in_ws(s, name, fn):
    a = s.index(f"<worksheet name='{name}'"); b = s.index("</worksheet>", a)
    ws2 = fn(s[a:b]); assert ws2 != s[a:b], name; return s[:a] + ws2 + s[b:]

def in_ds(s, key, fn):
    m = re.search(r"<datasource caption='[^']*' inline='true' name='federated\.%s[^']*'" % key, s)
    a = m.start(); b = s.index("</datasource>", a)
    d2 = fn(s[a:b]); assert d2 != s[a:b], key; return s[:a] + d2 + s[b:]

def rep(s, old, new, count=None):
    n = s.count(old); assert n, old[:60]
    if count is not None: assert n == count, (old[:60], n)
    return s.replace(old, new)

# ------------------------------------------------------------ 1. full forms in text
s = rep(s, "Right of the line: ABS Series B projection.",
           "Right of the line: Australian Bureau of Statistics Series B projection.")
s = rep(s, "Projected after 2025. The 85+ group doubles by 2045.",
           "Projected after 2025. The 85 and over group doubles by 2045.")
s = rep(s, "People per 1,000 in each age group. Residential care: 4 at 65-69, 414 at 90+.",
           "Residential care per 1,000: 4 at ages 65 to 69, 414 at 90 and over.")   # 15 words, one line
s = rep(s, "Residential places per 1,000 aged 65+, 2025",
           "Residential places per 1,000 aged 65 and over, 2025")
s = rep(s, "Residential care added $10.9bn, home care $7.7bn.",
           "Residential care added $10.9 billion, home care $7.7 billion.")
s = rep(s, "Government spending by programme in 2024-25, $ million.",
           "Government spending by programme in 2024-25, in millions of dollars.")
assert "AIHW" not in s        # expanded in fix_v4.py before the hard line breaks
s = rep(s, "aged 65+", "aged 65 and over")          # axis titles and field captions
assert "65+" not in re.sub(r"name='\[[^']*\]'", "", s)

# state codes -> full names (dumbbell rows and tooltips)
STATES = [("NSW", "New South Wales"), ("Vic", "Victoria"), ("Qld", "Queensland"),
          ("WA", "Western Australia"), ("SA", "South Australia"), ("Tas", "Tasmania"),
          ("ACT", "Australian Capital Territory"), ("NT", "Northern Territory")]
FULL = dict(STATES)
STATE_COL = "<column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />"
STATE_ALIASED = ("<column caption='State' datatype='string' name='[state]' role='dimension' type='nominal'>\n"
                 "        <aliases>\n" +
                 "".join(f"          <alias key='&quot;{k}&quot;' value='{v}' />\n" for k, v in STATES) +
                 "        </aliases>\n      </column>")
s = in_ds(s, "0stateyr", lambda d: rep(d, STATE_COL, STATE_ALIASED, 1))
def dumbbell_rows(w):
    w = rep(w, STATE_COL, STATE_ALIASED, 1)
    # fixed row-header width so "Australian Capital Territory" is not truncated (web: 28 chars at 9pt ~ 171 px)
    return rep(w, "          <style-rule element='header'>\n",
                  "          <style-rule element='header'>\n            <format attr='width' field='[federated.0stateyr0000000000000000].[none:state:nk]' value='195' />\n", 1)
s = in_ws(s, "11 Two programmes by state", dumbbell_rows)

# age bands
AGE_COL = "<column caption='Age group' datatype='string' name='[age_band]' role='dimension' type='nominal' />"
def age_aliased(pairs):
    return ("<column caption='Age group' datatype='string' name='[age_band]' role='dimension' type='nominal'>\n"
            "        <aliases>\n" +
            "".join(f"          <alias key='&quot;{k}&quot;' value='{v}' />\n" for k, v in pairs) +
            "        </aliases>\n      </column>")
s = in_ds(s, "0ageprog", lambda d: rep(d, AGE_COL, age_aliased([("90+", "90 and over")]), 1))
s = in_ws(s, "05 Care use by age", lambda w: rep(w, AGE_COL, age_aliased([("90+", "90 and over")]), 1))
# heatmap column headers at 8pt so "90 and over" fits its ~70 px column on the web
def heat_headers(w):
    return rep(w, "          <style-rule element='header'>\n            <format attr='display-field-labels' scope='rows' value='false' />",
                  "          <style-rule element='header'>\n            <format attr='font-size' value='8' />\n            <format attr='display-field-labels' scope='rows' value='false' />", 1)
s = in_ws(s, "05 Care use by age", heat_headers)
s = in_ds(s, "0pyramid", lambda d: rep(d, AGE_COL, age_aliased([("100+", "100 and over")]), 1))
s = in_ws(s, "02 Population pyramid", lambda w: rep(w, AGE_COL, age_aliased([("100+", "100 and over")]), 1))

# ------------------------------------------------------------ 2. bump data
rows = [r for r in csv.DictReader(open(os.path.join(DATA_DIR, "state_year.csv"), encoding="utf-8-sig"))
        if r["state"] != "Aust" and r["programme"] == "Home Care Packages"]
by_year = defaultdict(list)
for r in rows:
    by_year[r["year"]].append((r["state"], float(r["rate_per_1000"])))
years = sorted(by_year)
bump = []
# The x axis is CONTINUOUS (field x) so every text mark can be placed at an exact position: Tableau ignores
# text alignment on text marks, so a label is centred at (left edge + half its width) instead. Rank numbers sit at
# x = 2017, names start at X_START, year labels are text marks along the bottom (series "Y"). Padding series
# L / R / Y are drawn white, so their lines and markers are invisible.
from PIL import ImageFont
_font = ImageFont.truetype("arial.ttf", 11)            # 8pt at 96 dpi = 10.7 px; Arial stands in for Tableau Book
def label_px(txt): return _font.getlength(txt) * 1.05
X_MIN, X_MAX, PANE_PX = 2016.5, 2028.7, 543.0           # fixed axis range and the plot width in px (555 px zone)
PX_PER_UNIT = PANE_PX / (X_MAX - X_MIN)
X_START = 2025.5                                        # left edge of the end labels, half a year right of the last dot
# per-label corrections in canvas px, measured on the 7 Sept 22:42 Tableau Public capture (Arial over-estimates these)
NUDGE_PX = {"6 Tasmania": 5.0, "2 Queensland": 2.0, "3 Victoria": 2.0, "Territory": -6.0}   # Territory hangs under "Australian"
def centre_for(txt): return X_START + (label_px(txt) / 2 - NUDGE_PX.get(txt, 0.0)) / PX_PER_UNIT
END_LABEL = {st: f"{{i}} {name}" for st, name in STATES}
for y in years:
    ranked = sorted(by_year[y], key=lambda kv: (-kv[1], FULL[kv[0]]))   # ties broken alphabetically
    for i, (st, rate) in enumerate(ranked, 1):
        yn = 2000 + int(y[-2:])
        bump.append(dict(year=y, state=st, state_name=FULL[st], year_num=yn, x=float(yn),
                         rate_per_1000=rate, rank=i, neg_rank=float(-i), label=""))
        if y == years[0]:   # start rank in its own column to the left
            bump.append(dict(year=y, state="L", state_name="L", year_num=yn - 1, x=2017.0,
                             rate_per_1000=rate, rank=i, neg_rank=float(-i), label=str(i)))
        if y == years[-1]:  # end labels, left edges aligned at X_START; the long ACT name as two separately placed lines
            lines = [(f"{i} Australian Capital", 0.19), ("Territory", -0.19)] if st == "ACT" else [(END_LABEL[st].format(i=i), 0.0)]
            for txt, dy in lines:
                bump.append(dict(year=y, state="R", state_name="R", year_num=yn + 2, x=centre_for(txt),
                                 rate_per_1000=rate, rank=i, neg_rank=float(-i) + dy, label=txt))
for k, y in enumerate(years):     # year labels along the bottom, staggered on two baselines so they never touch
    yn = 2000 + int(y[-2:])
    bump.append(dict(year=y, state="Y", state_name="Y", year_num=yn, x=float(yn), rate_per_1000=0.0, rank=0, neg_rank=-9.15 if k % 2 == 0 else -9.65, label=y))
BUMP_CSV = os.path.join(DATA_DIR, "bump.csv")
with open(BUMP_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(bump[0].keys())); w.writeheader(); w.writerows(bump)
first, last = {b["state"]: b["rank"] for b in bump if b["year"] == years[0]}, {b["state"]: b["rank"] for b in bump if b["year"] == years[-1]}
print("bump ranks first->last:", {FULL[k]: (first[k], last[k]) for k in first if k in FULL})

HYPER_NAME = "0bump0000000000000000000.hyper"
HYPER_DIR = os.path.join(OUT_DIR, "hyper"); os.makedirs(HYPER_DIR, exist_ok=True)
hyper_path = os.path.join(HYPER_DIR, HYPER_NAME)
if os.path.exists(hyper_path): os.remove(hyper_path)
COLS = [("year", SqlType.text(), "string"), ("state", SqlType.text(), "string"), ("state_name", SqlType.text(), "string"),
        ("year_num", SqlType.big_int(), "integer"),
        ("rate_per_1000", SqlType.double(), "real"), ("rank", SqlType.big_int(), "integer"),
        ("neg_rank", SqlType.double(), "real"), ("label", SqlType.text(), "string"), ("x", SqlType.double(), "real")]   # real: Tableau rounds a fixed axis range on an integer field to whole numbers
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    table = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(c, t) for c, t, _ in COLS])
    with Connection(hp.endpoint, hyper_path, CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema("Extract"); conn.catalog.create_table(table)
        with Inserter(conn, table) as ins:
            ins.add_rows([[b[c] for c, _, _ in COLS] for b in bump]); ins.execute()
print("hyper written", hyper_path, len(bump), "rows")

# ------------------------------------------------------------ 3. bump datasource
DSN = "federated.0bump0000000000000000000"
DS = f"[{DSN}]"
# the columns shelf carries the integer year (numeric order, so the padding sorts last) aliased to
# the financial-year text; the two padding values alias to blank (non-breaking space) headers
YEAR_ALIASES = {b["year_num"]: (b["year"] if b["state"] else b["year"]) for b in bump}
YEAR_COL = ("<column caption='Year number' datatype='integer' name='[year_num]' role='dimension' type='ordinal'>\n"
            "        <aliases>\n" +
            "".join(f"          <alias key='{k}' value='{v}' />\n" for k, v in sorted(YEAR_ALIASES.items())) +
            "        </aliases>\n      </column>")
OBJ = "bump.csv_" + hashlib.md5(b"bump.csv").hexdigest().upper()
rel_cols = "\n".join(f"            <column datatype='{t}' name='{c}' ordinal='{i}' />" for i, (c, _, t) in enumerate(COLS))
HIGHLIGHT = {"South Australia": "#eb6834", "Australian Capital Territory": "#52514e", "Northern Territory": "#52514e",
             "": "#ffffff", "L": "#ffffff", "R": "#ffffff", "Y": "#ffffff"}   # padding series drawn white = invisible
pal = "".join(f"            <map to='{HIGHLIGHT.get(v, '#c9d3df')}'>\n              <bucket>&quot;{v}&quot;</bucket>\n            </map>\n" for _, v in STATES + [("", ""), ("L", "L"), ("R", "R"), ("Y", "Y")])
pal = pal.replace("<map to='#c9d3df'>\n              <bucket>&quot;&quot;</bucket>", "<map to='#ffffff'>\n              <bucket>&quot;&quot;</bucket>")
DS_XML = f"""    <datasource caption='bump' inline='true' name='{DSN}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='bump' name='textscan.0bump0000000000000000000'>
            <connection class='textscan' directory='{DATA_DIR.replace(os.sep, "/")}' filename='bump.csv' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.0bump0000000000000000000' name='bump.csv' table='[bump#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_AU' separator=','>
{rel_cols}
          </columns>
        </relation>
      </connection>
      <aliases enabled='yes' />
      <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />
      <column caption='State code' datatype='string' name='[state]' role='dimension' type='nominal' />
      <column caption='State' datatype='string' name='[state_name]' role='dimension' type='nominal' />
      {YEAR_COL}
      <column caption='Home Care Package recipients per 1,000 aged 65 and over' datatype='real' name='[rate_per_1000]' role='measure' type='quantitative' />
      <column caption='Rank' datatype='integer' name='[rank]' role='measure' type='quantitative' />
      <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />
      <column caption='X' datatype='real' name='[x]' role='measure' type='quantitative' />
      <column caption='Label' datatype='string' name='[label]' role='dimension' type='nominal' />
      <column caption='bump.csv' datatype='table' name='[__tableau_internal_object_id__].[{OBJ}]' role='measure' type='quantitative' />
      <column-instance column='[state_name]' derivation='None' name='[none:state_name:nk]' pivot='key' type='nominal' />
      <extract count='-1' enabled='true' object-id='' units='records' user-specific='false'>
        <connection access_mode='readonly' author-locale='en_US' class='hyper' dbname='Data/TableauTemp/{HYPER_NAME}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' update-time='09/07/2026 04:00:00 PM' username='tableau_internal_user'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
      <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
      <style>
        <style-rule element='mark'>
          <encoding attr='color' field='[none:state_name:nk]' type='palette'>
{pal}          </encoding>
        </style-rule>
      </style>
      <semantic-values>
        <semantic-value key='[Country].[Name]' value='&quot;Australia&quot;' />
      </semantic-values>
      <object-graph>
        <objects>
          <object caption='bump.csv' id='{OBJ}'>
            <properties context=''>
              <relation connection='textscan.0bump0000000000000000000' name='bump.csv' table='[bump#csv]' type='table'>
                        <columns character-set='UTF-8' header='yes' locale='en_AU' separator=','>
{rel_cols.replace("            <", "                          <")}
                        </columns>
                      </relation>
            </properties>
            <properties context='extract'>
              <relation name='Extract' table='[Extract].[Extract]' type='table' />
            </properties>
          </object>
        </objects>
      </object-graph>
    </datasource>
"""
a = s.index("    <datasource caption='marimekko' inline='true'"); b = s.index("</datasource>\n", a) + len("</datasource>\n")
s = s[:a] + DS_XML + s[b:]

# ------------------------------------------------------------ 4. bump worksheet
OLD_NAME, NEW_NAME = "12 Care mix by population", "12 Home care rank by state"
s = rep(s, OLD_NAME, NEW_NAME)         # dashboard zone, window, viewpoint, worksheet tag
NR = f"{DS}.[sum:neg_rank:qk]"
TITLE = "Home Care Package rank by state, 2017-18 to 2024-25"
SUBTITLE = ("Ranked by recipients per 1,000 aged 65 and over. South Australia (orange) rose from sixth to first. "
            "The territories (dark grey) fell to the bottom.")
TOOLTIP = f"""<customized-tooltip>
              <formatted-text>
                <run>In </run>
                <run bold='true'><![CDATA[<{DS}.[attr:year:nk]>]]></run>
                <run>, </run>
                <run bold='true'><![CDATA[<{DS}.[none:state_name:nk]>]]></run>
                <run> ranked </run>
                <run bold='true'><![CDATA[<{DS}.[sum:rank:qk]>]]></run>
                <run> of 8, with </run>
                <run bold='true'><![CDATA[<{DS}.[sum:rate_per_1000:qk]>]]></run>
                <run> Home Care Package recipients for every 1,000 people aged 65 and over.</run>
              </formatted-text>
            </customized-tooltip>"""
WS_XML = f"""    <worksheet name='{NEW_NAME}'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontname='Tableau Medium' fontsize='13'>{TITLE}</run><run>Æ&#10;</run><run fontcolor='#52514e' fontname='Tableau Book' fontsize='10' italic='true'>{SUBTITLE}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='bump' name='{DSN}' />
          </datasources>
          <datasource-dependencies datasource='{DSN}'>
            <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />
            <column caption='State' datatype='string' name='[state_name]' role='dimension' type='nominal' />
            {YEAR_COL.replace(chr(10) + "      ", chr(10) + "            ")}
            <column caption='Home Care Package recipients per 1,000 aged 65 and over' datatype='real' name='[rate_per_1000]' role='measure' type='quantitative' />
            <column caption='Rank' datatype='integer' name='[rank]' role='measure' type='quantitative' />
            <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />
            <column caption='X' datatype='real' name='[x]' role='measure' type='quantitative' />
            <column caption='Label' datatype='string' name='[label]' role='dimension' type='nominal' />
            <column-instance column='[year]' derivation='Attribute' name='[attr:year:nk]' pivot='key' type='nominal' />
            <column-instance column='[state_name]' derivation='None' name='[none:state_name:nk]' pivot='key' type='nominal' />
            <column-instance column='[year_num]' derivation='None' name='[none:year_num:ok]' pivot='key' type='ordinal' />
            <column-instance column='[rate_per_1000]' derivation='Sum' name='[sum:rate_per_1000:qk]' pivot='key' type='quantitative' />
            <column-instance column='[rank]' derivation='Sum' name='[sum:rank:qk]' pivot='key' type='quantitative' />
            <column-instance column='[neg_rank]' derivation='Sum' name='[sum:neg_rank:qk]' pivot='key' type='quantitative' />
            <column-instance column='[x]' derivation='Avg' name='[avg:x:qk]' pivot='key' type='quantitative' />
            <column-instance column='[label]' derivation='None' name='[none:label:nk]' pivot='key' type='nominal' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style>
          <style-rule element='table'>
            <format attr='background-color' value='#ffffff' />
          </style-rule>
          <style-rule element='cell'>
            <format attr='text-align' value='left' />
          </style-rule>
          <style-rule element='header'>
            <format attr='display-field-labels' scope='rows' value='false' />
            <format attr='display-field-labels' scope='cols' value='false' />
            <format attr='font-size' value='8' />
            <format attr='text-orientation' value='0' />
          </style-rule>
          <style-rule element='worksheet'>
            <format attr='display-field-labels' scope='rows' value='false' />
            <format attr='display-field-labels' scope='cols' value='false' />
          </style-rule>
          <style-rule element='axis'>
            <encoding attr='space' class='0' field='{DS}.[avg:x:qk]' field-type='quantitative' max='2028.7' min='2016.5' range-type='fixed' scope='cols' type='space' />
            <format attr='display' class='0' field='{DS}.[avg:x:qk]' scope='cols' value='false' />
            <encoding attr='space' class='0' field='{NR}' field-type='quantitative' max='-0.4' min='-10.0' range-type='fixed' scope='rows' type='space' />
            <encoding attr='space' class='1' field='{NR}' field-type='quantitative' fold='true' max='-0.4' min='-10.0' range-type='fixed' scope='rows' synchronized='true' type='space' />
            <format attr='display' class='0' field='{NR}' scope='rows' value='false' />
            <format attr='display' class='1' field='{NR}' scope='rows' value='false' />
          </style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
            <encodings>
              <color column='{DS}.[none:state_name:nk]' />
            </encodings>
          </pane>
          <pane id='1' selection-relaxation-option='selection-relaxation-allow' y-axis-name='{NR}'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
            <encodings>
              <color column='{DS}.[none:state_name:nk]' />
              <lod column='{DS}.[none:year_num:ok]' />
              <tooltip column='{DS}.[attr:year:nk]' />
              <tooltip column='{DS}.[sum:rank:qk]' />
              <tooltip column='{DS}.[sum:rate_per_1000:qk]' />
            </encodings>
            {TOOLTIP}
            <style>
              <style-rule element='mark'>
                <format attr='size' value='1.4' />
                <format attr='mark-labels-show' value='false' />
                <format attr='mark-markers-mode' value='all' />
              </style-rule>
            </style>
          </pane>
          <pane id='2' selection-relaxation-option='selection-relaxation-allow' y-axis-name='{NR}' y-index='1'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Text' />
            <encodings>
              <lod column='{DS}.[none:state_name:nk]' />
              <lod column='{DS}.[none:year_num:ok]' />
              <text column='{DS}.[none:label:nk]' />
              <tooltip column='{DS}.[attr:year:nk]' />
              <tooltip column='{DS}.[sum:rank:qk]' />
              <tooltip column='{DS}.[sum:rate_per_1000:qk]' />
            </encodings>
            {TOOLTIP}
            <style>
              <style-rule element='mark'>
                <format attr='mark-color' value='#0b0b0b' />
                <format attr='text-align' value='left' />
              </style-rule>
              <style-rule element='label'>
                <format attr='text-align' value='left' />
              </style-rule>
              <style-rule element='datalabel'>
                <format attr='font-size' value='8' />
              </style-rule>
            </style>
          </pane>
        </panes>
        <rows>({NR} + {NR})</rows>
        <cols>{DS}.[avg:x:qk]</cols>
      </table>
      <simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />
    </worksheet>
"""
a = s.index(f"    <worksheet name='{NEW_NAME}'>"); b = s.index("</worksheet>\n", a) + len("</worksheet>\n")
s = s[:a] + WS_XML + s[b:]
assert "0mekko" not in s and "marimekko" not in s

# the programme highlight action has no programme field on the bump sheet: exclude it explicitly
s = rep(s, "        <exclude-sheet name='10 What the money buys' />\n",
           f"        <exclude-sheet name='10 What the money buys' />\n        <exclude-sheet name='{NEW_NAME}' />\n", 1)
s = rep(s, "09 Where the extra billions went,10 What the money buys' />",
           f"09 Where the extra billions went,10 What the money buys,{NEW_NAME}' />", 1)

# ------------------------------------------------------------ 4a2. bump end labels: equal widths so their left edges line up
# Tableau ignores text-align on text marks; the labels are centred in their column, so padding every label
# with no-break spaces to the same width (measured with Arial as a stand-in for Tableau Book) left-aligns them.
# rewrite the bump extract with the padded labels
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    table = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(c, t) for c, t, _ in COLS])
    with Connection(hp.endpoint, hyper_path, CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema("Extract"); conn.catalog.create_table(table)
        with Inserter(conn, table) as ins:
            ins.add_rows([[b[c] for c, _, _ in COLS] for b in bump]); ins.execute()

# ------------------------------------------------------------ 4a3. chart 03: a blank padding column after 2024-25 so the
# line-end labels (Home Support, Home Care, Residential) have room instead of being pushed back over the lines.
# Same recipe as the bump chart: numeric year on the columns shelf, aliased to the financial year, one extra value
# aliased to a blank header, carried by an invisible white "programme" so no null indicator appears.
PY_DS = "federated.0progyear000000000000000"
PY_HYPER = "0progyear000000000000000.hyper"
py_src = os.path.join("v3/Data/TableauTemp", PY_HYPER); py_out = os.path.join(HYPER_DIR, PY_HYPER)
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, py_src) as conn:
        py_rows = conn.execute_list_query('SELECT "year", "programme", "rate_per_1000" FROM "Extract"."Extract"')
    py_rows = [[y, p, r, 2000 + int(y[-2:])] for y, p, r in py_rows]
    py_rows.append([" ", "", 0.0, 2026]); py_rows.append(["  ", "", 0.0, 2027])   # two padding columns, white series
    table = TableDefinition(TableName("Extract", "Extract"),
                            [TableDefinition.Column("year", SqlType.text()), TableDefinition.Column("programme", SqlType.text()),
                             TableDefinition.Column("rate_per_1000", SqlType.double()), TableDefinition.Column("year_num", SqlType.big_int())])
    if os.path.exists(py_out): os.remove(py_out)
    with Connection(hp.endpoint, py_out, CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema("Extract"); conn.catalog.create_table(table)
        with Inserter(conn, table) as ins: ins.add_rows(py_rows); ins.execute()
py_years = sorted({(r[3], r[0]) for r in py_rows})
PY_YEAR_COL = ("<column caption='Year number' datatype='integer' name='[year_num]' role='dimension' type='ordinal'>\n"
               "        <aliases>\n" + "".join(f"          <alias key='{k}' value='{v}' />\n" for k, v in py_years) +
               "        </aliases>\n      </column>")
def progyear_ds(d):
    d = rep(d, "      <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />\n",
               "      <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />\n      " + PY_YEAR_COL + "\n", 1)
    return rep(d, "            <map to='#c9c4b8'>\n              <bucket>&quot;Transition care&quot;</bucket>\n            </map>\n",
                  "            <map to='#c9c4b8'>\n              <bucket>&quot;Transition care&quot;</bucket>\n            </map>\n"
                  "            <map to='#ffffff'>\n              <bucket>&quot;&quot;</bucket>\n            </map>\n", 1)
s = in_ds(s, "0progyear", progyear_ds)
def chart03(w):
    w = rep(w, f"<cols>[{PY_DS}].[none:year:nk]</cols>", f"<cols>[{PY_DS}].[none:year_num:ok]</cols>", 1)
    w = rep(w, "<column-instance column='[year]' derivation='None' name='[none:year:nk]' pivot='key' type='nominal' />",
               "<column-instance column='[year]' derivation='Attribute' name='[attr:year:nk]' pivot='key' type='nominal' />\n"
               "            <column-instance column='[year_num]' derivation='None' name='[none:year_num:ok]' pivot='key' type='ordinal' />", 1)
    w = rep(w, "            <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />\n",
               "            <column caption='Year' datatype='string' name='[year]' role='dimension' type='nominal' />\n            " + PY_YEAR_COL.replace("\n      ", "\n            ") + "\n", 1)
    w = rep(w, f"<groupfilter function='member' level='[none:programme:nk]' member='&quot;Home support (CHSP)&quot;' />",
               f"<groupfilter function='member' level='[none:programme:nk]' member='&quot;Home support (CHSP)&quot;' />\n              <groupfilter function='member' level='[none:programme:nk]' member='&quot;&quot;' />", 1)
    w = w.replace(f"<[{PY_DS}].[none:year:nk]>", f"<[{PY_DS}].[attr:year:nk]>")
    w = rep(w, "          <style-rule element='header'>\n            <format attr='display-field-labels' scope='rows' value='false' />",
               "          <style-rule element='header'>\n            <format attr='text-orientation' value='0' />\n            <format attr='display-field-labels' scope='rows' value='false' />", 1)   # keep year headers horizontal
    w = rep(w, f"<text column='[{PY_DS}].[none:programme:nk]' />",
               f"<text column='[{PY_DS}].[none:programme:nk]' />\n              <tooltip column='[{PY_DS}].[attr:year:nk]' />", 1)
    return w
s = in_ws(s, "03 Where people are cared for", chart03)

# ------------------------------------------------------------ 4b. chart subtitles as explicit lines
# At most 12 words per line, written out as separate runs; side-by-side pairs get the same line count.
SUBTITLES = {
    "01 Older Australians":         ["Projected after 2025. The 85 and over group doubles by 2045."],
    "02 Population pyramid":        ["The top thickens. Women outnumber men three to two above 85."],
    "03 Where people are cared for": ["2021-22: Home Care Packages overtook residential care."],
    "04 Seven years of change":     ["Home Care Packages +147%. Home support -13%. Residential -11%."],
    "05 Care use by age":           ["Residential care per 1,000 people in each age group.",
                                     "4 at ages 65 to 69, 414 at 90 and over."],
    "06 Of every 100 aged 90+":     ["41 spent time in residential care.",
                                     "The other 59 did not."],
    "07 Places by remoteness":      ["48 places per 1,000 in the major cities,",
                                     "10.5 in very remote areas."],
    "08 Occupancy vs national":     ["Grey line is the national rate, 90%.",
                                     "Very remote areas sit 13.7 points below it."],
    "09 Where the extra billions went": ["2014-15 to 2024-25 in real dollars.",
                                     "Residential care added $10.9 billion, home care $7.7 billion.",
                                     "Dark bar: the 2014-15 total. Pale bars: the increases."],
    "10 What the money buys":       ["Spending by programme in 2024-25, in millions of dollars.",
                                     "Residential care takes 64 cents in every dollar.",
                                     "Home care takes 32 cents."],
    "11 Two programmes by state":   ["Blue is residential care, orange is Home Care Packages.",
                                     "South Australia leads on both,",
                                     "the Northern Territory trails on residential."],
    NEW_NAME:                       ["Ranked by recipients per 1,000 aged 65 and over.",
                                     "South Australia (orange) rose from sixth to first,",
                                     "the territories (dark grey) fell to the bottom."],
}
for lines in SUBTITLES.values():
    for l in lines:
        assert len(l.split()) <= 12, l
        assert len(l) <= 62, l          # 10pt italic line capacity in 555 px on the web is ~68 chars (0.78*pt per char)
SUB_RUN = "<run fontcolor='#52514e' fontname='Tableau Book' fontsize='10' italic='true'>"
def set_subtitle(w, lines):
    t0 = w.index("<title>"); t1 = w.index("</title>", t0); title = w[t0:t1]
    nl = re.search(r"<run>[^<]*&#10;</run>", title).group(0)
    m = re.search(re.escape(SUB_RUN) + r"(.*?)</run>", title, re.S); assert m, "no subtitle run"
    new = (nl).join(f"{SUB_RUN}{html.escape(l, quote=False).replace(chr(39), '&apos;')}</run>" for l in lines)
    return w[:t0] + title.replace(m.group(0), new) + w[t1:]
import html
for wsn, lines in SUBTITLES.items():
    a = s.index(f"<worksheet name='{wsn}'"); b = s.index("</worksheet>", a)
    s = s[:a] + set_subtitle(s[a:b], lines) + s[b:]      # may be unchanged when the line was already right
# chart 08 title was 63 chars, one over the 13pt line capacity of the column: shorten so it stays one line like chart 07
s = rep(s, "Occupancy of residential places against the national rate, 2025", "Occupancy of residential places, 2025", 1)

# ------------------------------------------------------------ 4c. chart titles as dashboard text blocks
# (user, 7 Sept) Each chart's title + subtitle becomes its own text zone, the same height for both charts
# of a row, and the worksheet sits below it with its own title hidden, so the plots start level.
# Column field labels ("Year", "Age group") are hidden on every sheet; the two charts with no column
# headers at the top (area chart, waffle) are nudged down by the header height of their partner.
s = s.replace("<style-rule element='worksheet'>\n            <format attr='display-field-labels' scope='rows' value='false' />\n          </style-rule>",
              "<style-rule element='worksheet'>\n            <format attr='display-field-labels' scope='rows' value='false' />\n            <format attr='display-field-labels' scope='cols' value='false' />\n          </style-rule>")
TOP_OFFSET = {"01 Older Australians": 22, "06 Of every 100 aged 90+": 22}
TITLE_LH, SUB_LH, PAD = 26, 20, 12                     # web px: 13pt title line, 10pt subtitle line, zone padding
da = s.index("<dashboard name='Growing Old in Australia'"); db = s.index("</dashboard>", da)
d = s[da:db]
H = int(re.search(r"<size maxheight='(\d+)'", d).group(1))
def uy(px): return int(round(px * 1e5 / H))
def py(u): return u * H / 1e5
zone_re = re.compile(r"<zone (?:(?!type-v2)[^>])*name='([^']+)'(?:(?!type-v2)[^>])*/>")   # sheet zones (self-closing, no type-v2)
sheets = []
for m in zone_re.finditer(d):
    z = m.group(0); name = m.group(1)
    g = {k: int(re.search(r"\b%s='(\d+)'" % k, z).group(1)) for k in "xywh"}
    sheets.append(dict(xml=z, name=name, **g))
assert len(sheets) == 12, [x["name"] for x in sheets]
NL_DASH = re.search(r"<run>[^<]*&#10;</run>", d).group(0)
def title_runs(name):
    a = s.index(f"<worksheet name='{name}'"); t0 = s.index("<formatted-text>", a); t1 = s.index("</formatted-text>", t0)
    return [r for r in re.findall(r"<run[^>]*>.*?</run>", s[t0:t1], re.S) if "&#10;" not in r]
rows = {}
for sh in sheets: rows.setdefault(sh["y"], []).append(sh)       # charts of a row share the same y
new_zones, zid = [], 200
for y0, group in rows.items():
    runs = {sh["name"]: title_runs(sh["name"]) for sh in group}
    n_sub = max(len(r) - 1 for r in runs.values())
    th = TITLE_LH + SUB_LH * n_sub + PAD
    for sh in group:
        off = th + TOP_OFFSET.get(sh["name"], 0)
        text = ("\n            " + NL_DASH + "\n            ").join(runs[sh["name"]])
        new_zones.append("<zone forceUpdate='true' h='%d' w='%d' x='%d' y='%d' id='%d' type-v2='text'>\n          <formatted-text>\n            %s\n          </formatted-text>\n        </zone>"
                         % (uy(th), sh["w"] - 1000, sh["x"] + 1000, sh["y"], zid, text)); zid += 1   # 12 px indent from the card edge
        new = sh["xml"].replace(" name='", " show-title='false' name='", 1)
        new = re.sub(r"\by='\d+'", "y='%d'" % (sh["y"] + uy(off)), new, count=1)
        new = re.sub(r"\bh='\d+'", "h='%d'" % (sh["h"] - uy(off)), new, count=1)
        d = d.replace(sh["xml"], new, 1)
        sh["new_y"] = sh["y"] + uy(off)
# legends: drop to the top of their chart's plot
for m in list(re.finditer(r"<zone [^>]*type-v2='color'[^>]*>", d)):
    z = m.group(0); ly = int(re.search(r"\by='(\d+)'", z).group(1))
    lx = int(re.search(r"\bx='(\d+)'", z).group(1))
    host = max((sh for sh in sheets if sh["y"] <= ly <= sh["y"] + sh["h"] and sh["x"] <= lx), key=lambda sh: sh["x"], default=None)   # the chart to its left
    if host: d = d.replace(z, re.sub(r"\by='\d+'", "y='%d'" % host["new_y"], z, count=1), 1)
d = d.replace("      </zones>", "        " + "\n        ".join(new_zones) + "\n      </zones>", 1)
s = s[:da] + d + s[db:]
assert s.count("show-title='false'") == 12
print("chart title blocks added:", len(new_zones))

# ------------------------------------------------------------ 5. write
twb = os.path.join(OUT_DIR, "Growing Old in Australia v5.twb")
open(twb, "w", encoding="utf-8").write(s)

def write_twbx(twb_text, path, windows=None):
    text = twb_text
    if windows is not None:
        a = text.index("  <windows"); a = text.index(">", a) + 2; b = text.index("  </windows>")
        text = text[:a] + windows + text[b:]
    tmp = path + ".twb"; open(tmp, "w", encoding="utf-8").write(text)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tmp, "Growing Old in Australia.twb")
        for f in os.listdir("v3/Data/TableauTemp"):
            if f.endswith(".hyper") and not f.startswith(("0mekko", "0progyear")):
                zf.write(os.path.join("v3/Data/TableauTemp", f), "Data/TableauTemp/" + f)
        zf.write(hyper_path, "Data/TableauTemp/" + HYPER_NAME)
        zf.write(py_out, "Data/TableauTemp/" + PY_HYPER)
    os.remove(tmp)

twbx = os.path.join(OUT_DIR, "Growing Old in Australia v5.twbx")
write_twbx(s, twbx)
# test copy: a 555 x 450 dashboard holding only the bump sheet (its real zone size), opened maximised
TEST_DASH = f"""    <dashboard name='Test'>
      <style>
        <style-rule element='table'>
          <format attr='background-color' value='#ffffff' />
        </style-rule>
      </style>
      <size maxheight='450' maxwidth='555' minheight='450' minwidth='555' sizing-mode='fixed' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='100000' id='2' param='vert' type-v2='layout-flow' w='100000' x='0' y='0' />
        </zone>
        <zone h='100000' w='100000' x='0' y='0' id='3' name='{NEW_NAME}' />
      </zones>
      <simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />
    </dashboard>
"""
TEST_WIN = f"""    <window class='dashboard' maximized='true' name='Test'>
      <viewpoints>
        <viewpoint name='{NEW_NAME}'>
          <zoom type='entire-view' />
        </viewpoint>
      </viewpoints>
      <active id='-1' />
      <simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />
    </window>
"""
t = s.replace("  </dashboards>", TEST_DASH + "  </dashboards>", 1)
write_twbx(t, os.path.join(OUT_DIR, "test_bump.twbx"), windows=TEST_WIN)
# same for the other sheets whose labels changed width
for sheet, w_px, h_px, fname in (("11 Two programmes by state", 555, 450, "test_11.twbx"),
                                 ("05 Care use by age", 555, 520, "test_05.twbx"),
                                 ("03 Where people are cared for", 555, 520, "test_03.twbx")):
    td = TEST_DASH.replace(NEW_NAME, sheet).replace("maxheight='450' maxwidth='555' minheight='450' minwidth='555'",
                                                    f"maxheight='{h_px}' maxwidth='{w_px}' minheight='{h_px}' minwidth='{w_px}'")
    write_twbx(s.replace("  </dashboards>", td + "  </dashboards>", 1), os.path.join(OUT_DIR, fname), windows=TEST_WIN.replace(NEW_NAME, sheet))
# and a copy that opens on the worksheet itself (shows query errors in the pane)
win = re.search(rf"    <window class='worksheet' name='{re.escape(NEW_NAME)}'>.*?</window>\n", s, re.S).group(0)
write_twbx(s, os.path.join(OUT_DIR, "test_bump_sheet.twbx"), windows=win.replace("<window class='worksheet'", "<window class='worksheet' maximized='true'", 1))
print("wrote", twbx, "and out/test_bump.twbx")
