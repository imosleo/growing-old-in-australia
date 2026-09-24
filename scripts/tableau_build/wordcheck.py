"""Words-per-line check for every text block in the built dashboard (web metrics: 0.66*pt px per char).
Usage: python wordcheck.py [twb]   (default out/Growing Old in Australia v5.twb). Flags any line over 15 words."""
import re, html, sys
path = sys.argv[1] if len(sys.argv) > 1 else "out/Growing Old in Australia v5.twb"
s = open(path, encoding="utf-8").read()
d = s[s.index("<dashboard name='Growing Old in Australia'"):s.index("</dashboard>")]

def wrap(txt, pt, w):
    maxc = (w - 12) / (0.66 * pt); lines, cur = [], []
    for wd in txt.split():
        if cur and len(" ".join(cur + [wd])) > maxc: lines.append(cur); cur = [wd]
        else: cur.append(wd)
    lines.append(cur); return [len(l) for l in lines]

over = 0
print("== dashboard text zones")
for m in re.finditer(r"<zone forceUpdate='true' [^>]*?id='(\d+)'[^>]*type-v2='text'>(.*?)</zone>", d, re.S):
    zid, body = m.groups(); w = int(re.search(r"\bw='(\d+)'", m.group(0)).group(1)) * 1200 / 1e5
    for attrs, txt in re.findall(r"<run([^>]*)>(.*?)</run>", body, re.S):
        txt = html.unescape(txt).strip()
        if len(txt) < 30 or "&#10;" in txt: continue
        pt = int(re.search(r"fontsize='(\d+)'", attrs).group(1)); L = wrap(txt, pt, w)
        flag = "  <-- OVER 15" if max(L) > 15 else ""; over += max(L) > 15
        print(f"zone {zid:>3} {w:4.0f}px {pt:2d}pt  max {max(L):2d}  lines {L}{flag}  {txt[:40]}")
print("== chart titles and subtitles (555 px)")
for m in re.finditer(r"<worksheet name='([^']+)'>.*?<title>(.*?)</title>", s, re.S):
    for attrs, txt in re.findall(r"<run([^>]*)>(.*?)</run>", m.group(2), re.S):
        txt = html.unescape(txt).strip()
        if len(txt) < 30: continue
        pt = int(re.search(r"fontsize='(\d+)'", attrs).group(1)); L = wrap(txt, pt, 555)
        flag = "  <-- OVER 15" if max(L) > 15 else ""; over += max(L) > 15
        print(f"{pt:2d}pt max {max(L):2d}  lines {L}{flag}  [{m.group(1)[:30]}]")
print(f"\nblocks over 15 words on a line: {over}")
