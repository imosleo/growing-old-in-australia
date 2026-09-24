r"""v4 pass: blue-anchored palette, text zones sized to content, narrow measure,
intro/stat sight-lines on the chart columns, dumbbell for chart 11, state
labels on the Marimekko, sources beside the conclusion.

Input : v3/ (unzipped Downloads\Growing Old in Australia.twbx = published 3 Sept)
Output: out/Growing Old in Australia v4.twbx
"""
import re, zipfile, os, math, shutil, html

SRC = "v3/Growing Old in Australia.twb"
OUT_DIR = "out"
s = open(SRC, encoding="utf-8").read()

def in_ws(s, name, fn):
    a = s.index(f"<worksheet name='{name}'"); b = s.index("</worksheet>", a)
    ws2 = fn(s[a:b]); assert ws2 != s[a:b], name; return s[:a] + ws2 + s[b:]

def in_ds(s, key, fn):
    m = re.search(r"<datasource caption='[^']*' inline='true' name='federated\.%s[^']*'" % key, s)
    a = m.start(); b = s.index("</datasource>", a)
    d2 = fn(s[a:b]); assert d2 != s[a:b], key; return s[:a] + d2 + s[b:]

# ---------------------------------------------------------------- 1. palette
BLUE, NAVY, PALE = "#2a78d6", "#1f4e79", "#9ec5f4"
ORANGE, GREEN = "#eb6834", "#3aa76d"
RECOLOUR = {
    "#39c5bb": BLUE,      # residential (teal -> blue) everywhere: palette maps, waffle, remoteness bars
    "#e12885": ORANGE,    # home care packages
    "#ff9f1c": GREEN,     # home support
    "#8b6cc1": "#a39e93", # respite
    "#6c757d": "#c9c4b8", # transition care
    "#d9c8f5": "#c6dbf3", # age 65-74
    "#9b6de0": "#6ea3e6", # age 75-84
    "#5a2ca0": NAVY,      # age 85+
    "#2f55c7": "#9db3cc", # male
    "#7ac943": NAVY,      # female
    "#f0566a": NAVY,      # waterfall total + chart 10 bars
    "#f9bcc4": PALE,      # waterfall increases
}
for old, new in RECOLOUR.items():
    assert old in s, old
    s = s.replace(old, new)
s = s.replace("The solid red bar is the 2014-15 total, the pale bars are the increases.",
              "The dark bar is the 2014-15 total, the pale bars are the increases.")
assert "red bar" not in s

# ------------------------------------------------- 2. waffle title one line
s = in_ws(s, "06 Of every 100 aged 90+", lambda w: w.replace(
    "Of every 100 Australians aged 90 and over, 2024-25", "Of every 100 aged 90 and over, 2024-25"))

# -------------------------------------- 3. chart 11: grouped bar -> dumbbell
DS11 = "[federated.0stateyr0000000000000000]"
R11 = f"{DS11}.[sum:rate_per_1000:qk]"
def dumbbell(w):
    w = w.replace("South Australia leads on both. The Northern Territory: 18.8 per 1,000 in residential care.",
                  "Blue is residential care, orange is Home Care Packages. South Australia leads on both, the Northern Territory trails on residential.")
    w = w.replace(f"<rows>{R11}</rows>\n        <cols>({DS11}.[none:state:nk] / {DS11}.[none:programme:nk])</cols>",
                  f"<rows>{DS11}.[none:state:nk]</rows>\n        <cols>({R11} + {R11})</cols>")
    # axis: synchronised dual axis, secondary hidden, title on primary, fixed range
    w = w.replace(f"<format attr='title' class='0' field='{R11}' scope='rows' value='Per 1,000 aged 65+' />\n"
                  f"            <format attr='display' field='{DS11}.[none:programme:nk]' value='false' />",
                  f"<encoding attr='space' class='0' field='{R11}' field-type='quantitative' max='95' min='0' range-type='fixed' scope='cols' type='space' />\n"
                  f"            <encoding attr='space' class='1' field='{R11}' field-type='quantitative' fold='true' max='95' min='0' range-type='fixed' scope='cols' synchronized='true' type='space' />\n"
                  f"            <format attr='title' class='0' field='{R11}' scope='cols' value='Per 1,000 aged 65+' />\n"
                  f"            <format attr='display' class='1' field='{R11}' scope='cols' value='false' />")
    a = w.index("<panes>"); b = w.index("</panes>") + 8
    tooltip = w[w.index("<customized-tooltip>", a):w.index("</customized-tooltip>", a) + 21]
    panes = f"""<panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Circle' />
            <encodings>
              <color column='{DS11}.[none:programme:nk]' />
            </encodings>
          </pane>
          <pane id='1' selection-relaxation-option='selection-relaxation-allow' x-axis-name='{R11}'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
            <encodings>
              <path column='{DS11}.[none:programme:nk]' />
              <text column='{R11}' />
            </encodings>
            <style>
              <style-rule element='mark'>
                <format attr='mark-color' value='#c9c4b8' />
                <format attr='size' value='1.4' />
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-labels-mode' value='line-ends' />
                <format attr='mark-labels-line-first' value='true' />
                <format attr='mark-labels-line-last' value='true' />
                <format attr='mark-labels-cull' value='false' />
              </style-rule>
              <style-rule element='datalabel'>
                <format attr='color-mode' value='user' />
                <format attr='color' value='#0b0b0b' />
                <format attr='font-weight' value='bold' />
                <format attr='font-size' value='9' />
              </style-rule>
            </style>
          </pane>
          <pane id='2' selection-relaxation-option='selection-relaxation-allow' x-axis-name='{R11}' x-index='1'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Circle' />
            <encodings>
              <color column='{DS11}.[none:programme:nk]' />
            </encodings>
            {tooltip}
            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='false' />
                <format attr='size' value='1.0' />
              </style-rule>
            </style>
          </pane>
        </panes>"""
    return w[:a] + panes + w[b:]
s = in_ws(s, "11 Two programmes by state", dumbbell)

# dumbbell: blank the residential label when both programmes round to the same value (ACT 48/48)
CALC11 = ("<column caption='Dumbbell label' datatype='string' name='[Calculation_dblabel]' role='measure' type='nominal'>\n"
          "        <calculation class='tableau' formula='IF ATTR([programme]) = &quot;Residential aged care&quot; AND ROUND(MAX({FIXED [state], [year] : MAX(IF [programme] = &quot;Home Care Packages&quot; THEN [rate_per_1000] END)}), 0) = ROUND(MAX({FIXED [state], [year] : MAX(IF [programme] = &quot;Residential aged care&quot; THEN [rate_per_1000] END)}), 0) THEN &quot;&quot; ELSE STR(ROUND(SUM([rate_per_1000]), 0)) END' />\n"
          "      </column>\n")
CALC11_INST = "<column-instance column='[Calculation_dblabel]' derivation='User' name='[usr:Calculation_dblabel:nk]' pivot='key' type='nominal' />\n            "
def dumbbell_label(w):
    w = w.replace(f"<path column='{DS11}.[none:programme:nk]' />\n              <text column='{R11}' />",
                  f"<path column='{DS11}.[none:programme:nk]' />\n              <text column='{DS11}.[usr:Calculation_dblabel:nk]' />")
    w = w.replace("<column-instance column='[year]'", CALC11_INST + "<column-instance column='[year]'", 1)
    i = w.index("<column-instance"); return w[:i] + CALC11.replace("\n      ", "\n            ") + "            " + w[i:]
s = in_ws(s, "11 Two programmes by state", dumbbell_label)
def stateyr_ds(d):
    j = min(d.index(t) for t in ("<column-instance", "<extract ", "<layout ", "<style>") if t in d)
    j = d.rindex("\n", 0, j) + 1
    return d[:j] + CALC11 + "      " + d[j:]
s = in_ds(s, "0stateyr", stateyr_ds)

# chart 08: dots instead of bars (a bar axis cannot honestly start at 60%), reference line unlabelled
DS8 = "[federated.0remote00000000000000000]"
def occupancy(w):
    w = w.replace("<mark class='Bar' />", "<mark class='Circle' />")
    w = w.replace("label-type='value'", "label-type='none'")
    w = w.replace("Very remote areas sit 13.7 points below the national 90.0%. Axis starts at 60%.",
                  "Grey line is the national rate, 90%. Very remote areas sit 13.7 points below it.")
    w = w.replace("value='Occupied places (%)  -  axis starts at 60%'", "value='Occupied places (%)'")
    w = w.replace("<format attr='mark-labels-show' value='true' />\n                <format attr='mark-color' value='#2a78d6' />",
                  "<format attr='mark-labels-show' value='true' />\n                <format attr='mark-color' value='#2a78d6' />\n                <format attr='size' value='1.2' />")
    return w
s = in_ws(s, "08 Occupancy vs national", occupancy)

# titles and subtitles: same number of lines within each chart pair so the plots start level
TITLE_EDITS = {
    "01 Older Australians": [("Right of the line is projected. By 2045 the 85 and over group more than doubles.",
                              "Projected after 2025. The 85+ group doubles by 2045.")],
    "05 Care use by age": [("People per 1,000 in each age group. Residential care: 4 at 65 to 69, 414 at 90 and over.",
                            "People per 1,000 in each age group. Residential care: 4 at 65-69, 414 at 90+.")],
    "06 Of every 100 aged 90+": [("41 spent time in permanent residential aged care. The other 59 did not.",
                                  "41 spent time in residential care, 59 did not.")],
    "07 Places by remoteness": [("Residential places per 1,000 people aged 65 and over, by remoteness, 2025",
                                 "Residential places per 1,000 aged 65+, 2025"),
                                ("48 places per 1,000 in the major cities. 10.5 in very remote Australia.",
                                 "By remoteness. 48 per 1,000 in the major cities, 10.5 in very remote areas.")],
    "12 Care mix by population": [("Care mix by state, sized by older population, 2024-25", "Care mix by state, 2024-25"),
                                  ("Columns left to right: NSW, Vic, Qld, WA, SA, Tas, ACT, NT. Width is each state&apos;s share of older Australians.",
                                   "Width is each state&apos;s share of over-65s, height its programme mix. The slivers at the right are Tas, ACT and NT. Green is home support.")],
}
for wsn, pairs in TITLE_EDITS.items():
    def fix(w, pairs=pairs):
        for old, new in pairs:
            assert old in w, (wsn, old[:40]); w = w.replace(old, new)
        return w
    s = in_ws(s, wsn, fix)

# ----------------------------------- 4. chart 12: state labels above columns
DS12 = "[federated.0mekko000000000000000000]"
CALC12 = ("<column caption='Label y' datatype='real' name='[Calculation_labely]' role='measure' type='quantitative'>\n"
          "        <calculation class='tableau' formula='9' />\n"
          "      </column>\n"
          "      <column caption='State label' datatype='string' name='[Calculation_statelabel]' role='dimension' type='nominal'>\n"
          "        <calculation class='tableau' formula='CASE [state] WHEN &quot;Tas&quot; THEN &quot;&quot; WHEN &quot;ACT&quot; THEN &quot;&quot; WHEN &quot;NT&quot; THEN &quot;&quot; ELSE [state] END' />\n"
          "      </column>\n")
CALC12_INST = ("<column-instance column='[Calculation_labely]' derivation='Avg' name='[avg:Calculation_labely:qk]' pivot='key' type='quantitative' />\n            "
               "<column-instance column='[Calculation_statelabel]' derivation='None' name='[none:Calculation_statelabel:nk]' pivot='key' type='nominal' />\n            ")
LY = f"{DS12}.[avg:Calculation_labely:qk]"
Y12 = f"{DS12}.[avg:y:qk]"
def mekko(w):
    w = w.replace("Columns left to right: NSW, Vic, Qld, WA, SA, Tas, ACT, NT. Width is each state&apos;s share of older Australians.",
                  "Column width is each state&apos;s share of Australians aged 65 and over. Height is how its aged care use splits across programmes.")
    w = w.replace("<column-instance column='[x]'", CALC12_INST + "<column-instance column='[x]'", 1)
    i = w.index("<column-instance"); w = w[:i] + CALC12.replace("\n      ", "\n            ") + "            " + w[i:]
    w = w.replace(f"<rows>{Y12}</rows>", f"<rows>({Y12} + {LY})</rows>")
    w = w.replace(f"<encoding attr='space' class='0' field='{DS12}.[avg:x:qk]' field-type='quantitative' max='100' min='0'",
                  f"<encoding attr='space' class='0' field='{DS12}.[avg:x:qk]' field-type='quantitative' max='100' min='0'")
    w = w.replace(f"<encoding attr='space' class='0' field='{Y12}' field-type='quantitative' max='100' min='0' range-type='fixed' scope='rows' type='space' />",
                  f"<encoding attr='space' class='0' field='{Y12}' field-type='quantitative' max='100' min='0' range-type='fixed' scope='rows' type='space' />\n"
                  f"            <encoding attr='space' class='0' field='{LY}' field-type='quantitative' fold='true' max='100' min='0' range-type='fixed' scope='rows' synchronized='true' type='space' />\n"
                  f"            <format attr='display' class='0' field='{LY}' scope='rows' value='false' />")
    # existing polygon pane becomes pane 1 on the primary axis; add a text pane on the secondary
    w = w.replace("<pane selection-relaxation-option='selection-relaxation-allow'>",
                  f"<pane id='1' selection-relaxation-option='selection-relaxation-allow' y-axis-name='{Y12}'>", 1)
    text_pane = f"""
          <pane id='2' selection-relaxation-option='selection-relaxation-allow' y-axis-name='{LY}'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Text' />
            <encodings>
              <text column='{DS12}.[none:Calculation_statelabel:nk]' />
            </encodings>
            <customized-tooltip>
              <formatted-text>
                <run bold='true'><![CDATA[<{DS12}.[none:state:nk]>]]></run>
              </formatted-text>
            </customized-tooltip>
            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-color' value='#ffffff' />
              </style-rule>
            </style>
          </pane>
        </panes>"""
    w = w.replace("\n        </panes>", text_pane, 1)
    return w
s = in_ws(s, "12 Care mix by population", mekko)
def mekko_ds(d):
    j = min(d.index(t) for t in ("<column-instance", "<extract ", "<layout ", "<style>") if t in d)
    j = d.rindex("\n", 0, j) + 1
    return d[:j] + CALC12 + "      " + d[j:]
s = in_ds(s, "0mekko", mekko_ds)

# --------------------------------------------------- 5. dashboard re-layout
H_CANVAS_OLD = 5900
def px(v, h=True):  # 1/100000 of canvas -> px
    return v * (H_CANVAS_OLD if h else 1200) / 1e5
def u_h(p): return int(round(p * 1e5 / NEW_H))
def u_w(p): return int(round(p * 1e5 / 1200))

da = s.index("<dashboards>"); db = s.index("</dashboards>")
d = s[da:db]

# text height estimator: Tableau Book/Georgia in a zone of width w px
def line_h(pt): return 2.0 * pt if pt <= 13 else 1.45 * pt
def char_w(pt): return 0.66 * pt   # measured on the 7 Sept 17:58 Tableau Public capture: 74 chars of 11pt = 518 px (0.64*pt); 0.66 keeps a margin
def est_text_h(zone_xml, w_px, spare=0.5):
    body = zone_xml[zone_xml.index("<formatted-text>"):zone_xml.index("</formatted-text>")]
    runs = re.findall(r"<run([^>]*)>(.*?)</run>", body, re.S)
    lines, cur, cur_pt = [], "", 0
    for attrs, txt in runs:
        if "&#10;" in txt:
            lines.append((cur, cur_pt)); cur, cur_pt = "", 0; continue
        pt = int(re.search(r"fontsize='(\d+)'", attrs).group(1))
        cur += txt; cur_pt = max(cur_pt, pt)
    lines.append((cur, cur_pt))
    h = 0
    for txt, pt in lines:
        if not txt:
            h += 0.7 * line_h(10); continue
        n = max(1, math.ceil(len(txt) / ((w_px - 12) / char_w(pt))))
        h += n * line_h(pt)
    return int(h + spare * line_h(11)) + 10  # spare body lines: text is centred, so excess shows as gaps

zones = {}
for m in re.finditer(r"<zone [^>]*?(?:/>|>.*?</zone>)", d, re.S):
    z = m.group(0)
    zid = re.search(r"\bid='(\d+)'", z).group(1)
    zones[zid] = dict(xml=z, span=m.span())
assert len(zones) == 35, len(zones)
zones["42"]["xml"] = ""                                   # drop the programme legend: colours are named in the subtitles
zones["41"]["xml"] = re.sub(r"\bw='\d+'", "w='46250'", zones["41"]["xml"], count=1)   # Marimekko takes the full half column

def set_geom(z, x=None, y=None, w=None, h=None):
    xml = z["xml"]
    for k, v in (("x", x), ("y", y), ("w", w), ("h", h)):
        if v is not None:
            xml = re.sub(r"\b%s='\d+'" % k, "%s='%d'" % (k, v), xml, count=1)
    z["xml"] = xml

def set_font(z, old_pt, new_pt):
    z["xml"] = z["xml"].replace(f"fontsize='{old_pt}'", f"fontsize='{new_pt}'")

L, R, HALF, FULL = 2500, 51250, 46250, 95000
# body paragraphs stay 10pt: 555 px at 10pt holds 12-13 words per line (0.64 px per pt per char measured on the web)
set_font(zones["12"], 11, 10)   # intro matches the section paragraphs
# the cluster of two-letter words packed 16 on one line; longer words bring it to 14 (wordcheck.py)
old_intro = "Today it is more than one in six, and by 2045 it will be better than one in five,"
assert old_intro in zones["12"]["xml"]
zones["12"]["xml"] = zones["12"]["xml"].replace(old_intro, "Today the proportion is more than one in six, and by 2045 it will exceed one in five,")
# 7 Sept: conclusion (zone 44) and its heading (zone 43) dropped at the user's request; the page ends after section 07
zones["43"]["xml"] = ""; zones["44"]["xml"] = ""
# conclusion: one short paragraph instead of three (critique: too many words)
CONCLUSION = ("Three things are happening at once: the number of Australians aged 85 and over will more than double by 2045, "
              "the system keeps moving people out of residential care and into care at home, and the bill has already doubled in ten years. "
              "If people used aged care in 2045 exactly as they did in 2024-25, residential care would need to serve about 533,000 people, "
              "up from 261,000 today, and Home Care Packages about 662,000, up from 354,000. "
              "That is not a forecast, only what today&apos;s patterns would produce if nothing else moved.")
# section paragraphs run as two equal columns: split at the sentence boundary nearest the middle
SPLIT = ()   # 7 Sept: no more twin columns; each paragraph is one 860 px column (12-14 words per line at 11pt)
PARAS = ("15", "21", "25", "30", "34", "39")
PARA_PX, TILE_X_PX, TILE_PX = 555, 615, 555   # text on the LEFT chart column, tiles/callouts on the RIGHT one (friend: text and boxes must match)
for zid in SPLIT:
    xml = zones[zid]["xml"]
    m = re.search(r"(<run [^>]*>)(.*?)(</run>)", xml, re.S)
    text = m.group(2)
    sents = re.split(r"(?<=[.!?])\s+", text)
    cuts = [sum(len(x) for x in sents[:k]) for k in range(1, len(sents))]
    k = 1 + min(range(len(cuts)), key=lambda j: abs(cuts[j] - len(text) / 2))
    left, sents = sents[:k], sents[k:]
    zones[zid]["xml"] = xml.replace(m.group(0), m.group(1) + " ".join(left) + m.group(3))
    twin = str(100 + int(zid))
    zones[twin] = dict(xml=xml.replace(m.group(0), m.group(1) + " ".join(sents) + m.group(3)).replace(f"id='{zid}'", f"id='{twin}'"), span=None)
# lock the two columns level: line counts MEASURED on the Tableau Public render of 4 Sept 20:36
# (12pt Tableau Book in a 555 px zone); the shorter column gets blank lines so both blocks are the
# same height and Tableau's vertical centring puts their first lines on the same y.
# HARD line breaks (7 Sept, user rule: never more than 15 words on a line; Week 4 rubric said 12). Every
# paragraph run is rewritten as explicit lines of at most MAX_WORDS words and a char budget 10% under the
# web line capacity, so words per line and line counts are exact on any renderer. Lines are balanced
# (no one-word orphans).
MAX_WORDS = 15
NL = re.search(r"<run>[^<]*&#10;</run>", zones["12"]["xml"]).group(0)
NL_SEP = "\n            " + NL + "\n            "
def cap_chars(pt, w_px=555): return int(0.95 * (w_px - 12) / char_w(pt))   # 0.66 metric already carries margin over the measured 0.64
def strip_trailing_nl(xml):
    return re.sub(r"(\s*<run>[^<]*&#10;</run>)+\s*</formatted-text>", "\n          </formatted-text>", xml)
def break_lines(words, budget, max_words):
    lines, cur = [], []
    for wd in words:
        if cur and (len(cur) >= max_words or len(html.unescape(" ".join(cur + [wd]))) > budget):
            lines.append(cur); cur = [wd]
        else: cur.append(wd)
    lines.append(cur); return lines
def hard_wrap(xml, w_px=555, max_words=MAX_WORDS):
    xml = strip_trailing_nl(xml)
    def fix(m):
        attrs, txt = m.group(1), m.group(2)
        if "&#10;" in txt or len(txt) < 30: return m.group(0)
        pt = int(re.search(r"fontsize='(\d+)'", attrs).group(1)); budget = cap_chars(pt, w_px)
        words = txt.split(" ")
        n = len(break_lines(words, budget, max_words))          # as few lines as the width allows...
        target = math.ceil(len(words) / n)                       # ...then balanced: same number of words per line
        lines = break_lines(words, budget, min(max_words, target))
        return NL_SEP.join(f"<run{attrs}>{' '.join(l)}</run>" for l in lines)
    return re.sub(r"<run([^>]*)>(.*?)</run>", fix, xml, flags=re.S)
for z in ("12",) + PARAS:
    zones[z]["xml"] = hard_wrap(zones[z]["xml"], PARA_PX)       # 860 px at 11pt: 12-14 words per line
# stat captions shortened to one line each in the 390 px rail, so the rail is no taller than the intro paragraph
for old_cap, new_cap in (("Australians aged 65 or over in 2025. In 1971 it was 1 in 12.", "Aged 65 or over in 2025. In 1971 it was 1 in 12."),
                         ("Australians expected to be 85 or over in 2045, up from 603,000 today.", "Aged 85 or over by 2045, up from 603,000 today."),
                         ("Government spending on aged care in 2024-25, almost double a decade earlier after inflation.", "Spent on aged care in 2024-25, double a decade ago.")):
    assert old_cap in zones["13"]["xml"], old_cap[:30]
    zones["13"]["xml"] = zones["13"]["xml"].replace(old_cap, new_cap)
zones["13"]["xml"] = hard_wrap(zones["13"]["xml"], TILE_PX)
# 7 Sept: one callout tile beside each section paragraph (fills the right column the 12-15 word rule leaves empty)
CALLOUTS = {"15": ("2.3×", "growth in Australians aged 85 and over, 2025 to 2045"),
            "21": ("70 in 1,000", "held a Home Care Package in 2024-25, up from 28"),
            "25": ("414 in 1,000", "aged 90 and over used residential care in 2024-25"),
            "30": ("10.5 places", "per 1,000 in very remote areas, against 48 in the cities"),
            "34": ("$19.5 billion", "added to aged care spending in a decade, in today's dollars"),
            "39": ("81 in 1,000", "South Australians aged 65 and over hold a Home Care Package")}
CALLOUT_OF = {}
for n, (pz, (num, cap)) in enumerate(CALLOUTS.items()):
    cid = str(50 + n); CALLOUT_OF[pz] = cid
    xml = ("<zone forceUpdate='true' h='0' w='%d' x='%d' y='0' id='%s' type-v2='text'>\n          <formatted-text>\n"
           "            <run fontname='Georgia' fontsize='22' fontcolor='#2a78d6' bold='true'>%s</run>\n            %s\n"
           "            <run fontname='Tableau Book' fontsize='10' fontcolor='#52514e'>%s</run>\n          </formatted-text>\n        </zone>"
           % (u_w(TILE_PX), u_w(TILE_X_PX), cid, num, NL, cap.replace("'", "&apos;")))
    zones[cid] = dict(xml=hard_wrap(xml, TILE_PX), span=None)
LH = 22   # px per 11pt line on the web (2.0 * pt)
LINES = {z: zones[z]["xml"].count("&#10;") + 1 for zid in SPLIT for z in (zid, str(100 + int(zid)))}
print("lines per column (exact):", LINES)
NL = re.search(r"<run>[^<]*&#10;</run>", zones["12"]["xml"]).group(0)
for zid in SPLIT:
    twin = str(100 + int(zid)); n = max(LINES[zid], LINES[twin])
    for z in (zid, twin):
        pad = n - LINES[z]
        if pad:
            zones[z]["xml"] = zones[z]["xml"].replace("\n          </formatted-text>", "\n            " + "\n            ".join([NL] * pad) + "\n          </formatted-text>", 1)
            assert zones[z]["xml"].count("&#10;") == pad + LINES[z] - 1, z
# intro: narrow to the left chart column; stat tiles on the right column
set_geom(zones["12"], x=L, w=HALF); set_geom(zones["13"], x=R, w=HALF)
# footer: split into the colophon line (id 45) and a sources block (new id 46) beside the conclusion
foot = zones["45"]["xml"]
ft = foot[foot.index("<formatted-text>"):foot.index("</formatted-text>") + 17]
runs = re.findall(r"<run[^>]*>.*?</run>", ft, re.S)
colophon = runs[0]
# colophon on two lines (one full-width 8pt line held 17 words; the rule is 12-15 per line)
cm = re.match(r"(<run[^>]*>)(.*?)(</run>)", colophon, re.S)
ct = cm.group(2); ci = ct.index("FIT3179")
colophon = cm.group(1) + re.sub(r"[^\w)]+$", "", ct[:ci]) + cm.group(3)   # drop the separator but keep the closing bracket + "\n            " + NL + "\n            " + cm.group(1) + ct[ci:] + cm.group(3)
zones["45"]["xml"] = foot.replace(ft, "<formatted-text>\n            " + colophon + "\n          </formatted-text>")
# sources block as two 555 px columns at 9pt (full width at 8pt ran 16-37 words per line):
# left = the source list, right = the data notes and the generative AI statement
# references block (friend: make the sources neater; user: APA style): heading, rule, one APA reference per
# line at 9pt across the full width, rule, then the data notes (left column) and the AI statement (right column)
R9 = "<run fontname='Tableau Book' fontsize='9' fontcolor='#52514e'>"
R9I = "<run fontname='Tableau Book' fontsize='9' fontcolor='#52514e' italic='true'>"
REFS = [
    ("Productivity Commission. (2026). ", "Report on Government Services 2026: Part F, Section 14, Aged care services",
     " [Data set]. https://www.pc.gov.au/ongoing/report-on-government-services/community-services/aged-care-services"),
    ("Australian Bureau of Statistics. (2026). ", "National, state and territory population, December 2025",
     " (Table 59) [Data set]. https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population"),
    ("Australian Bureau of Statistics. (2023). ", "Population projections, Australia, 2022 (base) to 2071",
     " (Series B, Table B9) [Data set]. https://www.abs.gov.au/statistics/people/population/population-projections-australia"),
    ("Australian Institute of Health and Welfare, &amp; Department of Health, Disability and Ageing. (2025). ", "Aged care data snapshot 2025",
     " [Data set]. GEN Aged Care Data. https://www.gen-agedcaredata.gov.au"),
]
NLS = "\n            " + NL + "\n            "
# APA hanging style, two explicit lines per reference: citation, then the URL indented underneath
ref_body = NLS.join(R9 + a_ + "</run>" + R9I + t_ + "</run>" + R9 + c_.split(" https://")[0] + "</run>" + NLS
                    + R9 + "        https://" + c_.split(" https://")[1] + "</run>" for a_, t_, c_ in REFS)
def tzone(zid, x, w, body, style=""):
    return dict(xml="<zone forceUpdate='true' h='0' w='%d' x='%d' y='0' id='%s' type-v2='text'>\n          <formatted-text>\n            %s\n          </formatted-text>%s\n        </zone>"
                % (w, x, zid, body, style), span=None)
RULE = "\n          <zone-style>\n            <format attr='background-color' value='#c9c4b8' />\n          </zone-style>"
zones["48"] = tzone("48", L, FULL, "<run fontname='Tableau Medium' fontsize='11' fontcolor='#0b0b0b' bold='true'>Data sources</run>")
zones["60"] = tzone("60", L, FULL, "<run> </run>", RULE)
zones["46"] = tzone("46", L, FULL, ref_body)
zones["61"] = tzone("61", L, FULL, "<run> </run>", RULE)
notes_run = next(r for r in runs[3:] if "Aged care figures are financial years" in r).replace("fontsize='8'", "fontsize='10'").replace(">Aged care figures", ">Notes. Aged care figures")
ai_run = next(r for r in runs[3:] if "Use of generative AI" in r).replace("fontsize='8'", "fontsize='10'")
# notes paragraph and the generative AI statement both dropped at the user's request (7 Sept 10:20 PM); the page ends with the colophon

# row plan (px). chart rows keep their v3 heights; legends keep their 70 px offset
GAP_HEAD, GAP_PARA, GAP_SECTION, GAP_INTRO = 0, 4, 22, 34
plan = [
    ("text", ["11"], None),
    ("intro", ["12", "13"], None),
    ("head", ["14"], None), ("text", ["15"], None), ("charts", ["16", "17", "18", "19"], 648),
    ("head", ["20"], None), ("text", ["21"], None), ("charts", ["22", "23"], 520),
    ("head", ["24"], None), ("text", ["25"], None), ("charts", ["26", "27", "28"], 520),
    ("head", ["29"], None), ("text", ["30"], None), ("charts", ["31", "32"], 450),
    ("head", ["33"], None), ("text", ["34"], None), ("charts", ["35", "37"], 520),
    ("head", ["38"], None), ("text", ["39"], None), ("charts", ["40", "41"], 450),
    ("sources", ["46"], None),
    ("colophon", ["45"], None),
]
y = 24
placed = []   # (zid, x_units, y_px, w_units, h_px)
for kind, ids, ch in plan:
    if kind == "head":
        for i in ids: placed.append((i, L, y, FULL, 40))
        y += 40 + GAP_HEAD
    elif kind == "text":
        z = zones[ids[0]]
        w_units = FULL if ids[0] == "11" else u_w(PARA_PX)
        h = est_text_h(z["xml"], px(w_units, False))
        placed.append((ids[0], L, y, w_units, h))
        if ids[0] in CALLOUT_OF:      # callout tile top-aligned with its paragraph, only as tall as its text
            cid = CALLOUT_OF[ids[0]]; ch_ = est_text_h(zones[cid]["xml"], TILE_PX, spare=0)
            placed.append((cid, u_w(TILE_X_PX), y, u_w(TILE_PX), min(ch_, h)))
        y += h + (GAP_INTRO if ids[0] == "11" else GAP_PARA)
    elif kind == "intro":   # intro paragraph in the 860 px column, stat tiles in a 250 px rail on the right
        hs = [est_text_h(zones["12"]["xml"], PARA_PX), est_text_h(zones["13"]["xml"], TILE_PX)]
        placed.append(("12", L, y, u_w(PARA_PX), hs[0])); placed.append(("13", u_w(TILE_X_PX), y, u_w(TILE_PX), hs[1]))
        y += max(hs) + GAP_SECTION
    elif kind == "sources":
        placed.append(("48", L, y, FULL, 28)); y += 28 + 2
        placed.append(("60", L, y, FULL, 1)); y += 1 + 6
        h = est_text_h(zones["46"]["xml"], px(FULL, False), spare=0); placed.append(("46", L, y, FULL, h)); y += h + 6
        placed.append(("61", L, y, FULL, 1)); y += 1 + 10
        y += 6
    elif kind == "conclusion":
        hs = [est_text_h(zones[i]["xml"], px(HALF, False)) for i in ids]
        placed.append(("44", L, y, HALF, hs[0])); placed.append(("46", R, y, HALF, hs[1]))
        y += max(hs) + GAP_PARA
    elif kind == "colophon":
        placed.append((ids[0], L, y, FULL, 46)); y += 46 + 24     # two 8pt lines
    elif kind == "charts":
        for i in ids:
            z = zones[i]
            xu = int(re.search(r"\bx='(\d+)'", z["xml"]).group(1)); wu = int(re.search(r"\bw='(\d+)'", z["xml"]).group(1))
            legend = "type-v2='color'" in z["xml"]
            placed.append((i, xu, y + (70 if legend else 0), wu, 150 if legend else ch))
        y += ch + GAP_SECTION
NEW_H = int(math.ceil(y / 10.0) * 10)
for zid, xu, yp, wu, hp in placed:
    set_geom(zones[zid], x=xu, y=u_h(yp), w=wu, h=u_h(hp))

# rebuild the dashboard zones block in the original order, then append the new sources zone
order = sorted((z for z in zones.values() if z["span"]), key=lambda z: z["span"][0])
out, pos = [], 0
for z in order:
    a, b = z["span"]; out.append(d[pos:a]); out.append(z["xml"]); pos = b
tail = d[pos:]
i = tail.index("</zones>")
new_zones = "\n        ".join(z["xml"] for z in zones.values() if not z["span"])
tail = tail[:i] + new_zones + "\n      " + tail[i:]
d2 = "".join(out) + tail
d2 = d2.replace("maxheight='5900'", "maxheight='%d'" % NEW_H).replace("minheight='5900'", "minheight='%d'" % NEW_H)
s = s[:da] + d2 + s[db:]
assert s.count("<zone ") == 35 + len(CALLOUTS) + 2 + len(SPLIT), s.count("<zone ")

# ------------------------------------------------------------------ write
os.makedirs(OUT_DIR, exist_ok=True)
twb = os.path.join(OUT_DIR, "Growing Old in Australia.twb")
open(twb, "w", encoding="utf-8").write(s)
twbx = os.path.join(OUT_DIR, "Growing Old in Australia v4.twbx")
with zipfile.ZipFile(twbx, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(twb, "Growing Old in Australia.twb")
    for root, _, files in os.walk("v3/Data"):
        for f in files:
            p = os.path.join(root, f); zf.write(p, os.path.relpath(p, "v3"))
print("canvas 1200 x", NEW_H)
for zid, xu, yp, wu, hp in placed:
    print(f"  zone {zid:>2}  x={px(xu,False):5.0f} y={yp:5d} w={px(wu,False):4.0f} h={hp}")
print("wrote", twbx)
