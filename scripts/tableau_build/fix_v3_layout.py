import re, zipfile, os
s = open("rec/Growing Old in Australia.twb", encoding="utf-8").read()

def in_ws(s, name, fn):
    a = s.index(f"<worksheet name='{name}'"); b = s.index("</worksheet>", a)
    ws2 = fn(s[a:b]); assert ws2 != s[a:b], name; return s[:a] + ws2 + s[b:]

# every worksheet: hide the row field label (the truncated "Age..", "Remotene.." headers)
HDR_END = "<format attr='display-field-labels' scope='cols' value='false' />\n          </style-rule>"
HIDE_ROW_LABEL = "\n          <style-rule element='worksheet'>\n            <format attr='display-field-labels' scope='rows' value='false' />\n          </style-rule>"
assert s.count(HDR_END) == 12, s.count(HDR_END)
s = s.replace(HDR_END, HDR_END + HIDE_ROW_LABEL)

# waffle: big squares
s = in_ws(s, "06 Of every 100 aged 90+", lambda w: w.replace("<format attr='size' value='1.0' />", "<format attr='size' value='4.0' />"))
# pyramid: small age labels, short axis title
s = in_ws(s, "02 Population pyramid", lambda w: w.replace(
    "<format attr='display-field-labels' scope='rows' value='false' />",
    "<format attr='display-field-labels' scope='rows' value='false' />\n            <format attr='font-size' field='[federated.0pyramid0000000000000000].[none:age_band:nk]' value='8' />", 1
    ).replace("value='People (men left, women right)'", "value='People'"))
# heatmap: programmes down the side, age groups across the top
s = in_ws(s, "05 Care use by age", lambda w: w.replace(
    "<rows>[federated.0ageprog0000000000000000].[none:age_band:nk]</rows>\n        <cols>[federated.0ageprog0000000000000000].[none:programme:nk]</cols>",
    "<rows>[federated.0ageprog0000000000000000].[none:programme:nk]</rows>\n        <cols>[federated.0ageprog0000000000000000].[none:age_band:nk]</cols>"))
# waterfall: shorter title, explanatory subtitle, short axis title
s = in_ws(s, "09 Where the extra billions went", lambda w: w.replace(
    "Where the extra $19.5 billion went, 2014-15 to 2024-25 (real dollars)", "Where the extra $19.5 billion went"
    ).replace("Residential care added $10.9bn, home care $7.7bn. Total reaches $39.8bn.",
              "2014-15 to 2024-25 in real dollars. Residential care added $10.9bn, home care $7.7bn. Orange bars are totals, blue bars are increases."
    ).replace("value='Government spending ($ million, 2024-25 dollars)'", "value='$ million'"
    ).replace("scope='rows' value='$ million'", "scope='cols' value='$ million'"
    ).replace("<rows>[federated.0wfall000000000000000000].[sum:running_total_m:qk]</rows>\n        <cols>[federated.0wfall000000000000000000].[none:label:nk]</cols>",
              "<rows>[federated.0wfall000000000000000000].[none:label:nk]</rows>\n        <cols>[federated.0wfall000000000000000000].[sum:running_total_m:qk]</cols>"))

# slope chart: one-line end labels "Home Care 70" via an aggregate calc instead of two stacked text fields
CALC = ("<column caption='End label' datatype='string' name='[Calculation_endlabel]' role='measure' type='nominal'>\n"
        "        <calculation class='tableau' formula='(CASE ATTR([programme]) WHEN &quot;Home Care Packages&quot; THEN &quot;Home Care&quot; WHEN &quot;Home support (CHSP)&quot; THEN &quot;Home Support&quot; WHEN &quot;Residential aged care&quot; THEN &quot;Residential&quot; ELSE ATTR([programme]) END) + &quot; &quot; + STR(ROUND(SUM([rate_per_1000]), 0))' />\n"
        "      </column>\n")
CALC_INST = "<column-instance column='[Calculation_endlabel]' derivation='User' name='[usr:Calculation_endlabel:nk]' pivot='key' type='nominal' />\n            "
def slope(w):
    w = w.replace("<text column='[federated.0progyear000000000000000].[none:programme:nk]' />\n              <text column='[federated.0progyear000000000000000].[sum:rate_per_1000:qk]' />",
                  "<text column='[federated.0progyear000000000000000].[usr:Calculation_endlabel:nk]' />")
    w = w.replace("<column-instance column='[year]'", CALC_INST + "<column-instance column='[year]'", 1)
    i = w.index("<column-instance"); return w[:i] + CALC.replace("\n      ", "\n            ") + "            " + w[i:]
s = in_ws(s, "04 Seven years of change", slope)
# and the calc must exist in the datasource itself
dsa = s.index("<datasource caption=", s.index("name='federated.0progyear000000000000000'") - 400)
dsb = s.index("</datasource>", dsa)
ds = s[dsa:dsb]
cands = [ds.index(t) for t in ("<column-instance", "<group ", "<extract ", "<layout ", "<style>") if t in ds]
j = min(cands); j = ds.rindex("\n", 0, j) + 1
ds = ds[:j] + CALC + "      " + ds[j:]
s = s[:dsa] + ds + s[dsb:]

# chart 10: treemap -> sorted horizontal bars with value labels (every value readable)
def bars10(w):
    w = w.replace("Residential care takes 64 cents in every dollar. Home care takes 32.",
                  "Government spending by programme in 2024-25, $ million. Residential care takes 64 cents in every dollar, home care 32.")
    w = w.replace("<mark class='Square' />", "<mark class='Bar' />")
    w = w.replace("<size column='[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]' />\n              <text column='[federated.0spend000000000000000000].[none:programme:nk]' />\n              <text column='[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]' />",
                  "<text column='[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]' />")
    w = w.replace("<run> million of government spending in 2024-25.</run>", "<run> of government spending in 2024-25.</run>")
    w = w.replace("<rows></rows>\n        <cols></cols>",
                  "<rows>[federated.0spend000000000000000000].[none:programme:nk]</rows>\n        <cols>[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]</cols>")
    w = w.replace("<aggregation value='true' />",
                  "<sort class='computed' column='[federated.0spend000000000000000000].[none:programme:nk]' direction='DESC' using='[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]' />\n          <aggregation value='true' />", 1)
    w = w.replace("<format attr='has-stroke' value='true' />\n                <format attr='stroke-color' value='#ffffff' />", "")
    w = w.replace("<style-rule element='label'>", "<style-rule element='axis'>\n            <format attr='title' class='0' field='[federated.0spend000000000000000000].[sum:real_expenditure_m:qk]' scope='cols' value='$ million' />\n          </style-rule>\n          <style-rule element='label'>", 1)
    return w
s = in_ws(s, "10 What the money buys", bars10)

# aliases: waffle legend
old = "<column caption='Group' datatype='string' name='[category]' role='dimension' type='nominal' />"
new = ("<column caption='Group' datatype='string' name='[category]' role='dimension' type='nominal'>\n"
       "        <aliases>\n"
       "          <alias key='&quot;In permanent residential aged care&quot;' value='In residential care' />\n"
       "          <alias key='&quot;Not in residential aged care&quot;' value='No residential care' />\n"
       "        </aliases>\n      </column>")
assert s.count(old) == 2; s = s.replace(old, new)
# aliases: programme names everywhere
oldp = "<column caption='Programme' datatype='string' name='[programme]' role='dimension' type='nominal' />"
newp = ("<column caption='Programme' datatype='string' name='[programme]' role='dimension' type='nominal'>\n"
        "        <aliases>\n"
        "          <alias key='&quot;Home Care Packages&quot;' value='Home Care' />\n"
        "          <alias key='&quot;Home support (CHSP)&quot;' value='Home Support' />\n"
        "          <alias key='&quot;Residential aged care&quot;' value='Residential' />\n"
        "          <alias key='&quot;Residential respite&quot;' value='Respite' />\n"
        "          <alias key='&quot;Transition care&quot;' value='Transition' />\n"
        "        </aliases>\n      </column>")
assert s.count(oldp) == 11, s.count(oldp); s = s.replace(oldp, newp)
# aliases: waterfall steps
oldl = "<column caption='Component' datatype='string' name='[label]' role='dimension' type='nominal' />"
newl = ("<column caption='Component' datatype='string' name='[label]' role='dimension' type='nominal'>\n"
        "        <aliases>\n"
        "          <alias key='&quot;2014-15 total&quot;' value='2014-15 spending' />\n"
        "          <alias key='&quot;Residential &amp; flexible care&quot;' value='Residential care' />\n"
        "          <alias key='&quot;Home care &amp; support&quot;' value='Home care and support' />\n"
        "          <alias key='&quot;Assessment &amp; information&quot;' value='Assessment' />\n"
        "          <alias key='&quot;Quality &amp; Safety Commission&quot;' value='Quality regulator' />\n"
        "          <alias key='&quot;Workforce &amp; quality&quot;' value='Workforce' />\n"
        "        </aliases>\n      </column>")
assert s.count(oldl) == 2, s.count(oldl); s = s.replace(oldl, newl)

# axis titles that were truncating
reps = [
 ("value='Recipients per 1,000 people aged 65+'", "value='Per 1,000 aged 65+'"),
 ("value='Share of Australia&apos;s population aged 65+ (%), left to right: NSW, Vic, Qld, WA, SA, Tas, ACT, NT'", "value='Share of over-65s (%)'"),
 ("value='Share of aged care use (%)'", "value='Care use share (%)'"),
 ("value='Residential places per 1,000 people aged 65 and over'", "value='Places per 1,000 aged 65+'"),
 ("Column width is each state&apos;s share of older Australians. Shares are of care use, not people.",
  "Columns left to right: NSW, Vic, Qld, WA, SA, Tas, ACT, NT. Width is each state&apos;s share of older Australians."),
]
for a, b in reps:
    assert a in s, a[:60]; s = s.replace(a, b)

# ---- object model: declare each extract the way Tableau 2026 does, so Publish accepts it ----
import hashlib
def add_object_graph(s):
    out = []; pos = 0
    for m in re.finditer(r"<datasource caption='([^']+)' inline='true' name='(federated\.[^']+)' version='18\.1'>.*?</datasource>", s, re.S):
        d = m.group(0); cap = m.group(1)
        rel = re.search(r"<relation connection='(textscan\.[^']+)' name='([^']+)' table='([^']+)' type='table'>.*?</relation>", d, re.S)
        conn, csv, tbl = rel.group(1), rel.group(2), rel.group(3)
        oid = f"{csv}_{hashlib.md5(cap.encode()).hexdigest().upper()}"
        col = f"      <column caption='{csv}' datatype='table' name='[__tableau_internal_object_id__].[{oid}]' role='measure' type='quantitative' />\n"
        j = d.index("<extract "); j = d.rindex("\n", 0, j) + 1
        d = d[:j] + col + d[j:]
        og = ("      <object-graph>\n        <objects>\n"
              f"          <object caption='{csv}' id='{oid}'>\n"
              "            <properties context=''>\n"
              + re.sub(r"^", "              ", rel.group(0), flags=re.M) + "\n"
              "            </properties>\n"
              "            <properties context='extract'>\n"
              "              <relation name='Extract' table='[Extract].[Extract]' type='table' />\n"
              "            </properties>\n          </object>\n        </objects>\n      </object-graph>\n")
        d = d.replace("    </datasource>", og + "    </datasource>")
        out.append(s[pos:m.start()]); out.append(d); pos = m.end()
    out.append(s[pos:]); return "".join(out)
s = add_object_graph(s)
assert s.count("<object-graph>") == 10, s.count("<object-graph>")

# ---- colours: one scheme for the whole page ----
# Tableau ignores a datasource palette unless the datasource also declares a column-instance for the field.
s = re.sub(r"\s*<encoding attr='color' field='\[federated\.[^']+\]\.\[[^']+\]' type='palette'>.*?</encoding>", "", s, flags=re.S)
s = re.sub(r"\s*<style-rule element='mark'>\s*</style-rule>", "", s)
for ds, field in [("0popbands000000000000000","age_band"),("0pyramid0000000000000000","sex"),("0progyear000000000000000","programme"),
                  ("0waffle00000000000000000","category"),("0wfall000000000000000000","type"),("0stateyr0000000000000000","programme"),
                  ("0mekko000000000000000000","programme")]:
    a = s.index("<datasource caption=", s.index(f"name='federated.{ds}'") - 400); b = s.index("</datasource>", a)
    d = s[a:b]; j = d.index("<extract "); j = d.rindex("\n", 0, j) + 1
    d = d[:j] + f"      <column-instance column='[{field}]' derivation='None' name='[none:{field}:nk]' pivot='key' type='nominal' />\n" + d[j:]
    s = s[:a] + d + s[b:]
# blue = residential everywhere (programme palette, waffle, remoteness bars); other variables get non-programme hues
def recolour(pairs):
    global s
    for old_hex, bucket, new_hex in pairs:
        pat = re.compile(r"<map to='%s'>(\s*<bucket>&quot;%s&quot;</bucket>)" % (re.escape(old_hex), re.escape(bucket)))
        s, n = pat.subn(lambda m: f"<map to='{new_hex}'>{m.group(1)}", s)
        assert n >= 1, (old_hex, bucket)
TEAL = "#39c5bb"
recolour([("#2a78d6","Residential aged care",TEAL), ("#eb6834","Home Care Packages","#e12885"), ("#1baf7a","Home support (CHSP)","#ff9f1c"),
          ("#eda100","Residential respite","#8b6cc1"), ("#e87ba4","Transition care","#6c757d"),                 # programmes: teal / magenta / amber
          ("#2a78d6","In permanent residential aged care",TEAL), ("#e1e0d9","Not in residential aged care","#e6ebee"),   # waffle: teal = residential
          ("#9ec5f4","65-74","#d9c8f5"), ("#3987e5","75-84","#9b6de0"), ("#184f95","85 and over","#5a2ca0"),   # age bands: purple ramp
          ("#4a6b8a","Male","#2f55c7"), ("#8c5f7d","Female","#7ac943"),                                         # sex: royal blue / lime
          ("#52514e","Total","#f0566a"), ("#2a78d6","Increase","#f9bcc4")])                                     # waterfall: crimson total, coral steps
s = in_ws(s, "09 Where the extra billions went", lambda w: w.replace("Orange bars are totals, blue bars are increases.", "The solid red bar is the 2014-15 total, the pale bars are the increases."))
s = in_ws(s, "10 What the money buys", lambda w: w.replace("<format attr='mark-color' value='#2a78d6' />", "<format attr='mark-color' value='#f0566a' />"))
for wsn in ("07 Places by remoteness", "08 Occupancy vs national"):                                              # residential places: teal
    s = in_ws(s, wsn, lambda w: w.replace("<format attr='mark-color' value='#2a78d6' />", f"<format attr='mark-color' value='{TEAL}' />"))

# tooltips: Tableau drops a whitespace-only run, so "857,315Female" needs a non-breaking space
s = s.replace("<run> </run>", "<run>&#160;</run>")

# dashboard geometry, computed in pixels on the original 1200x5400 canvas
OLD_H = 5400
da = s.index("<dashboard name='Growing Old in Australia'>"); db = s.index("</dashboard>", da)
d = s[da:db]
zones = []
for m in re.finditer(r"<zone [^>]*>", d):
    z = m.group(0)
    g = lambda k: int(re.search(" %s='(\\d+)'" % k, z).group(1))
    if g("h") == 100000: continue
    n = re.search(r" name='([^']*)'", z)
    zones.append(dict(span=m.span(), z=z, h=g("h")*OLD_H/1e5, w=g("w"), x=g("x"), y=g("y")*OLD_H/1e5,
                      name=n.group(1) if n else "", legend="type-v2='color'" in z))
overrides = {229: 380, 767: 648, 1472: 520, 2177: 520, 3533: 520}     # row top (px) -> new row height (px)
rows = sorted(overrides)
def find_row(y):
    for r in rows:
        if abs(y - r) < 3: return r
def row_old_h(r):
    return next(z["h"] for z in zones if find_row(z["y"]) == r and not z["legend"])
for z in zones:
    r = find_row(z["y"])
    z["nh"] = overrides[r] if (r is not None and not z["legend"]) else z["h"]
    shift = sum(overrides[r] - row_old_h(r) for r in rows if z["y"] >= r + row_old_h(r) - 3)
    z["ny"] = z["y"] + shift
    z["drop"] = False
    LEG_W = {"01 ": 12500, "02 ": 8333, "06 ": 16583, "12 ": 14167}          # legend width sized to its longest label
    key = z["name"][:3]
    if key in LEG_W and z["w"] == 35750: z["w"] = 46250 - LEG_W[key] - 833     # chart takes the rest of the half
    if z["name"].startswith("09 ") and not z["legend"]: z["w"] = 46250          # waterfall full half width
    if z["name"].startswith("09 ") and z["legend"]: z["drop"] = True            # subtitle explains the colours
    if z["legend"] and not z["drop"]:
        cx = 2500 if z["x"] < 50000 else 51250
        z["w"] = LEG_W[key]; z["x"] = cx + 46250 - LEG_W[key]
    if int(round(z["y"])) == 229 and z["w"] == 35000: z["x"] = 60000; z["w"] = 37500   # stat tiles wider
NEW_H = OLD_H + sum(overrides[r] - row_old_h(r) for r in rows)
NEW_H = int(((NEW_H + 49)//50)*50)
out = []; pos = 0
for z in zones:
    a, b = z["span"]; out.append(d[pos:a]); pos = b
    if z["drop"]: continue
    zz = z["z"]
    zz = re.sub(r" h='\d+'", " h='%d'" % round(z['nh']/NEW_H*1e5), zz)
    zz = re.sub(r" y='\d+'", " y='%d'" % round(z['ny']/NEW_H*1e5), zz)
    zz = re.sub(r" w='\d+'", " w='%d'" % z['w'], zz)
    zz = re.sub(r" x='\d+'", " x='%d'" % z['x'], zz)
    out.append(zz)
out.append(d[pos:]); d2 = "".join(out)
d2 = d2.replace("maxheight='5400'", "maxheight='%d'" % NEW_H).replace("minheight='5400'", "minheight='%d'" % NEW_H)
s = s[:da] + d2 + s[db:]

os.makedirs("v3", exist_ok=True)
open("v3/Growing Old in Australia.twb", "w", encoding="utf-8").write(s)
out = "C:/Users/xpert/Downloads/Growing Old in Australia v3.twbx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.write("v3/Growing Old in Australia.twb", "Growing Old in Australia.twb")
    for root, _, files in os.walk("rec/Data"):
        for fn in files:
            p = os.path.join(root, fn); z.write(p, os.path.relpath(p, "rec"))
print("canvas height", NEW_H, "-> wrote", out)
