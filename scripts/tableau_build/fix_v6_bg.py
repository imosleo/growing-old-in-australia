r"""Background variant (7 Sept): warm sand page, white chart cards, navy header band.
Input : out/Growing Old in Australia v5.twb (fix_v5.py output)   Output: out/Growing Old in Australia v5 sand.twbx
The v5 file is left untouched; this is a duplicate for comparison."""
import re, zipfile, os

SAND, NAVY, CARD = "#f4efe6", "#1f4e79", "#ffffff"
SRC = "out/Growing Old in Australia v5.twb"
s = open(SRC, encoding="utf-8").read()
da = s.index("<dashboard name='Growing Old in Australia'"); db = s.index("</dashboard>", da)
d = s[da:db]
H = int(re.search(r"<size maxheight='(\d+)'", d).group(1))
def uy(px): return int(round(px * 1e5 / H))
def geom(z): return {k: int(re.search(r"\b%s='(\d+)'" % k, z).group(1)) for k in "xywh"}

# 1. page colour
d = d.replace("<format attr='background-color' value='#ffffff' />", "<format attr='background-color' value='%s' />" % SAND, 1)

def block(zid, x, y, w, h, colour):
    return ("<zone forceUpdate='true' h='%d' w='%d' x='%d' y='%d' id='%d' type-v2='text'>\n"
            "          <formatted-text>\n            <run> </run>\n          </formatted-text>\n"
            "          <zone-style>\n            <format attr='background-color' value='%s' />\n          </zone-style>\n        </zone>"
            % (h, w, x, y, zid, colour))

# 2. navy band behind the header (zone 11), full bleed, with white text
z11 = re.search(r"<zone forceUpdate='true' [^>]*?id='11'[^>]*>.*?</zone>", d, re.S).group(0)
g = geom(z11)
band = block(300, 0, 0, 100000, g["y"] + g["h"] + uy(22), NAVY)
z11_new = (z11.replace("fontcolor='#898781'", "fontcolor='#c6dbf3'")
              .replace("fontcolor='#0b0b0b'", "fontcolor='#ffffff'")
              .replace("fontcolor='#52514e'", "fontcolor='#dbe7f5'"))
assert z11_new != z11
d = d.replace(z11, z11_new, 1)

# 3. one white card per chart: from the top of its title block to the bottom of the sheet, half-column wide
titles = {geom(m.group(0))["x"]: [] for m in re.finditer(r"<zone forceUpdate='true' [^>]*?id='2\d\d'[^>]*type-v2='text'>", d)}
sheets = [m.group(0) for m in re.finditer(r"<zone [^>]*show-title='false'[^>]*/>", d)]
assert len(sheets) == 12, len(sheets)
title_zones = [m.group(0) for m in re.finditer(r"<zone forceUpdate='true' [^>]*?id='2\d\d'[^>]*type-v2='text'>", d)]
cards, zid = [], 310
for sh in sheets:
    gs = geom(sh)
    # the title block of this chart: same x, directly above the sheet
    tz = min((geom(t) for t in title_zones if abs(geom(t)["x"] - gs["x"]) <= 1500 and geom(t)["y"] < gs["y"]), key=lambda t: gs["y"] - t["y"])   # title block is indented 12 px
    top = tz["y"]; bottom = gs["y"] + gs["h"]
    cards.append(block(zid, gs["x"], top, 46250, bottom - top, CARD)); zid += 1

# insert band + cards right after the root layout zone so they sit underneath everything else
root_end = d.index("</zone>", d.index("<zones>")) + len("</zone>")
d = d[:root_end] + "\n        " + band + "\n        " + "\n        ".join(cards) + d[root_end:]
s = s[:da] + d + s[db:]

out_twb = "out/Growing Old in Australia v5 sand.twb"
open(out_twb, "w", encoding="utf-8").write(s)
twbx = "out/Growing Old in Australia v5 sand.twbx"
with zipfile.ZipFile(twbx, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(out_twb, "Growing Old in Australia.twb")
    for f in os.listdir("v3/Data/TableauTemp"):
        if f.endswith(".hyper") and not f.startswith(("0mekko", "0progyear")):
            zf.write(os.path.join("v3/Data/TableauTemp", f), "Data/TableauTemp/" + f)
    zf.write("out/hyper/0bump0000000000000000000.hyper", "Data/TableauTemp/0bump0000000000000000000.hyper")
    zf.write("out/hyper/0progyear000000000000000.hyper", "Data/TableauTemp/0progyear000000000000000.hyper")
print("wrote", twbx, "cards:", len(cards))
