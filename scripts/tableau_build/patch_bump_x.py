"""One-off patch (7 Sept 11 PM): bump chart on a continuous x axis with computed label positions; chart 03 two pad columns."""
NB = chr(160)
p = 'fix_v5.py'; t = open(p, encoding='utf-8').read()

def rep(old, new, n=1):
    global t
    assert t.count(old) == n, (old[:70], t.count(old)); t = t.replace(old, new)

# ---- 1. data generation: x positions, year-label rows, no discrete padding
a = t.index('# labels are drawn as TEXT MARKS'); b = t.index('BUMP_CSV = ')
NEW_GEN = '''# The x axis is CONTINUOUS (field x) so every text mark can be placed at an exact position: Tableau ignores
# text alignment on text marks, so a label is centred at (left edge + half its width) instead. Rank numbers sit at
# x = 2017, names start at X_START, year labels are text marks along the bottom (series "Y"). Padding series
# L / R / Y are drawn white, so their lines and markers are invisible.
from PIL import ImageFont
_font = ImageFont.truetype("arial.ttf", 11)            # 8pt at 96 dpi = 10.7 px; Arial stands in for Tableau Book
def label_px(txt): return _font.getlength(txt) * 1.05
X_MIN, X_MAX, PANE_PX = 2016.5, 2028.7, 543.0           # fixed axis range and the plot width in px (555 px zone)
PX_PER_UNIT = PANE_PX / (X_MAX - X_MIN)
X_START = 2025.5                                        # left edge of the end labels, half a year right of the last dot
def centre_for(txt): return X_START + (label_px(txt) / 2) / PX_PER_UNIT
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
for y in years:     # year labels along the bottom
    yn = 2000 + int(y[-2:])
    bump.append(dict(year=y, state="Y", state_name="Y", year_num=yn, x=float(yn), rate_per_1000=0.0, rank=0, neg_rank=-9.35, label=y))
'''
t = t[:a] + NEW_GEN + t[b:]

# ---- 2. extract columns
rep('        ("neg_rank", SqlType.double(), "real"), ("label", SqlType.text(), "string")]',
    '        ("neg_rank", SqlType.double(), "real"), ("label", SqlType.text(), "string"), ("x", SqlType.double(), "real")]')

# ---- 3. datasource + worksheet columns, cols shelf, palette
rep("      <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />\n      <column caption='Label'",
    "      <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />\n      <column caption='X' datatype='real' name='[x]' role='measure' type='quantitative' />\n      <column caption='Label'")
rep("            <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />\n            <column caption='Label'",
    "            <column caption='Rank (negative)' datatype='real' name='[neg_rank]' role='measure' type='quantitative' />\n            <column caption='X' datatype='real' name='[x]' role='measure' type='quantitative' />\n            <column caption='Label'")
rep("            <column-instance column='[neg_rank]' derivation='Sum' name='[sum:neg_rank:qk]' pivot='key' type='quantitative' />",
    "            <column-instance column='[neg_rank]' derivation='Sum' name='[sum:neg_rank:qk]' pivot='key' type='quantitative' />\n            <column-instance column='[x]' derivation='Avg' name='[avg:x:qk]' pivot='key' type='quantitative' />")
rep("        <cols>{DS}.[none:year_num:ok]</cols>", "        <cols>{DS}.[avg:x:qk]</cols>")
rep('"": "#ffffff", "L": "#ffffff", "R": "#ffffff"}', '"": "#ffffff", "L": "#ffffff", "R": "#ffffff", "Y": "#ffffff"}')
rep('for _, v in STATES + [("", ""), ("L", "L"), ("R", "R")])', 'for _, v in STATES + [("", ""), ("L", "L"), ("R", "R"), ("Y", "Y")])')

# ---- 4. axes: fixed continuous x, hidden; y range down to -9.8 for the year-label row
rep("            <encoding attr='space' class='0' field='{NR}' field-type='quantitative' max='-0.4' min='-8.6' range-type='fixed' scope='rows' type='space' />",
    "            <encoding attr='space' class='0' field='{DS}.[avg:x:qk]' field-type='quantitative' max='2028.7' min='2016.5' range-type='fixed' scope='cols' type='space' />\n"
    "            <format attr='display' class='0' field='{DS}.[avg:x:qk]' scope='cols' value='false' />\n"
    "            <encoding attr='space' class='0' field='{NR}' field-type='quantitative' max='-0.4' min='-9.8' range-type='fixed' scope='rows' type='space' />")
rep("            <encoding attr='space' class='1' field='{NR}' field-type='quantitative' fold='true' max='-0.4' min='-8.6' range-type='fixed' scope='rows' synchronized='true' type='space' />",
    "            <encoding attr='space' class='1' field='{NR}' field-type='quantitative' fold='true' max='-0.4' min='-9.8' range-type='fixed' scope='rows' synchronized='true' type='space' />")

# ---- 5. drop the old no-break-space padding block (keep the hyper rewrite that follows it)
a = t.index('from PIL import ImageFont\n_font = ImageFont.truetype("arial.ttf", 40)'); b = t.index('# rewrite the bump extract')
t = t[:a] + t[b:]

# ---- 6. chart 03: two padding columns
rep('    py_rows.append([" ", "", 0.0, 2026])                      # padding column, white series, single point = no line',
    '    py_rows.append(["' + NB + '", "", 0.0, 2026]); py_rows.append(["' + NB * 2 + '", "", 0.0, 2027])   # two padding columns, white series')

open(p, 'w', encoding='utf-8').write(t); print("fix_v5 patched")
