"""Fill the DV1 Moodle template with Part A to D. Times New Roman throughout, template separator lines removed,
datasets and idiom rationale as tables. Usage: python build_partb.py [partD_png ...]"""
import sys, docx
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TEMPLATE = r"C:\Users\xpert\Downloads\DV1 - Assignment Template v1.0.docx"
OUT = r"C:\Users\xpert\Downloads\DV1 Report FINAL - Ian Leong 34423680.docx"
SKETCH = r"C:\Users\xpert\Downloads\age_in_asutralia_sketch.jpg"
CAPTURE = r"C:\Users\xpert\Downloads\Growing Old in Australia.png"      # full-page capture of the published page
URL = "https://public.tableau.com/app/profile/ian.leong4002/viz/GrowingOldinAustralia/GrowingOldinAustralia"
STUDIO = "[Studio session]"
FONT = "Times New Roman"

DOMAIN = [("", "Aged care in Australia. The page follows how population ageing turns into demand for aged care: how many "
               "Australians are old, which age groups are growing fastest, whether people are cared for in a residential home or at home, "
               "how access differs between the cities and remote areas, what governments spend, and how the states and territories compare. "
               "Population figures run from 1971 to 2025 with projections to 2045. Aged care figures run from 2017-18 to 2024-25.")]

WHY_WHO = [("Why. ", "One Australian in twelve was 65 or over in 1971. Today it is more than one in six, and the 85 and over group, "
                     "which relies on aged care most, will more than double by 2045. The official figures sit in separate tables from three "
                     "agencies, so the need is one connected view that shows who uses aged care, how the balance between residential care and "
                     "care at home has shifted, where access is thinnest and what it costs. The page answers that in a few minutes of reading."),
           ("Who. ", "The average Australian, with no statistical training and no knowledge of aged care programmes. That shaped the writing: "
                     "plain language, no abbreviations, programme names in full, one short paragraph and one headline number per section, and a "
                     "chart title that states the finding so the reader does not have to work it out.")]

WHAT_INTRO = [("", "Four datasets from three independent sources. Population comes from the Australian Bureau of Statistics, aged care use "
                   "and spending from the Productivity Commission, and residential places and occupancy from the Australian Institute of Health "
                   "and Welfare with the Department of Health, Disability and Ageing.")]
WHAT_TABLE = [("Source", "Dataset", "Used for"),
              ("Australian Bureau of Statistics", "National, state and territory population, December 2025, Table 59. Estimated resident population by age and sex, 1971 to 2025.",
               "Older population by age band, the population pyramid, and the denominator of every rate per 1,000."),
              ("Australian Bureau of Statistics", "Population projections, Australia, 2022 (base) to 2071, Series B, Table B9.",
               "The 2045 projections in the area chart and the pyramid."),
              ("Productivity Commission", "Report on Government Services 2026, Part F, Section 14, Aged care services.",
               "Recipients per 1,000 people aged 65 and over by programme, state and age group, 2017-18 to 2024-25. Real government spending by programme, 2014-15 to 2024-25."),
              ("Australian Institute of Health and Welfare, with the Department of Health, Disability and Ageing", "Aged Care Data Snapshot 2025 (GEN Aged Care Data).",
               "Residential places and occupancy by remoteness at 30 June 2025.")]
WHAT_PROCESS = [("Creation process. ", "The spreadsheets were downloaded, reshaped from wide to long form and cut into one tidy file per chart "
                 "with a Python script. Population and aged care figures are combined only as rates per 1,000 people aged 65 and over, because "
                 "the Commission counts people over a financial year while the population is a 30 June estimate, so the two cannot be joined "
                 "row by row. Spending is in constant 2024-25 dollars. Each file is loaded into Tableau as an extract, and the full citations "
                 "with links are printed at the foot of the dashboard.")]

HOW_INTRO = [("", "The dashboard is one scrolling page of twelve charts in six sections, in the order of the Week 2 sketch. Each section has "
                  "a heading, a short paragraph, a callout number and two charts side by side. The idiom for each chart was chosen for the "
                  "question the reader is asking at that point.")]
HOW_TABLE = [("Section", "Charts", "Why these idioms"),
             ("02 An ageing nation", "Stacked area chart of the population aged 65 and over in three age bands. Population pyramid for 2025 and 2045.",
              "The area chart shows the total and the growing share of the 85 and over band at once. The pyramid shows the shape of the age distribution by sex, which is where the thickening at the top is visible."),
             ("03 Where people are cared for", "Multi-line chart of recipients per 1,000 by programme. Slope chart of 2017-18 against 2024-25.",
              "The lines show the 2021-22 crossover where Home Care Packages overtook residential care. The slope chart strips the series down to the change itself."),
             ("04 Who uses aged care", "Heatmap of programme by age group. Waffle chart of every 100 people aged 90 and over.",
              "A heatmap compares two categories at once, and colour makes the steep rise with age readable before the numbers are read. The waffle turns a percentage into countable people."),
             ("05 City and country gap", "Sorted bar chart of places per 1,000 by remoteness. Dot plot of occupancy with a line for the national rate.",
              "Bars give an exact ranking of five ordered categories. Dots are used for occupancy because the scale starts at 60 per cent, and a bar drawn from 60 would exaggerate the gap."),
             ("06 Paying for it", "Waterfall chart of the $19.5 billion increase in spending. Sorted bar chart of 2024-25 spending by programme.",
              "The waterfall shows which programmes added the money, part by part. The bars show where the money goes now."),
             ("07 State by state", "Dumbbell chart of residential care against Home Care Packages by state. Bump chart ranking the states on Home Care Packages each year.",
              "The dumbbell shows the level and the gap between the two programmes in one row per state. The bump chart is the only idiom that shows South Australia rising from sixth to first while both territories fell to the bottom.")]
HOW_AFTER = [("Advanced idioms. ", "Population pyramid, slope chart, heatmap, waffle chart, waterfall chart, dumbbell chart and bump chart, seven in all."),
             ("Colour. ", "Blue is residential care, orange is Home Care Packages and green is home support on every chart that shows programmes. "
                          "Age bands use one blue ramp. The palette is limited to these so colour always means the same thing."),
             ("Interaction. ", "Hovering any mark gives a plain-language tooltip with the full year, place and value. Hovering a programme in one "
                               "chart highlights it in the other charts that show programmes."),
             ("Custom-built elements. ", "The bump chart's rank numbers, state names and year labels are placed as text marks on a continuous axis "
                                         "so they never overlap. The dumbbell uses a dual axis. Every chart title sits in its own block of equal height, "
                                         "so paired charts start level. These were built by editing the workbook file, because Tableau's menus do not offer them."),
             ("Sketch. ", "The sections follow the Week 2 sketch one for one. The sketch's closing section, a summary with two or three big numbers, "
                          "became the three tiles beside the introduction and the callout beside each section, so the conclusion is carried by the numbers.")]

doc = docx.Document(TEMPLATE)

def set_font(run, bold=None, size=None):
    run.font.name = FONT
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    rpr = run._r.get_or_add_rPr(); rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.append(rf)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(k), FONT)

def para_after(el):
    p = OxmlElement('w:p'); el.addnext(p)
    return docx.text.paragraph.Paragraph(p, doc._body)

def add_paras(el, items, gap_after=True):
    for lead, text in items:
        para = para_after(el); para.paragraph_format.space_after = Pt(0); para.paragraph_format.space_before = Pt(0)
        if lead: set_font(para.add_run(lead), bold=True, size=11)
        set_font(para.add_run(text), bold=False, size=11); el = para._p
    if gap_after:                      # exactly one empty line before the next prompt
        blank = para_after(el); blank.paragraph_format.space_after = Pt(0); el = blank._p
    return el

def add_table_after(el, rows, widths_cm):
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    borders = OxmlElement('w:tblBorders')
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f'w:{edge}'); b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '4'); b.set(qn('w:color'), '000000'); borders.append(b)
    tbl._tbl.tblPr.append(borders)
    for ri, row in enumerate(rows):
        for ci, text in enumerate(row):
            cell = tbl.cell(ri, ci); cell.width = Cm(widths_cm[ci])
            set_font(cell.paragraphs[0].add_run(text), bold=(ri == 0), size=10)
    el.addnext(tbl._tbl)
    spacer = OxmlElement('w:p'); tbl._tbl.addnext(spacer)
    return spacer

def find(startswith, contains=""):
    for p in doc.paragraphs:
        if p.text.strip().startswith(startswith) and contains in p.text: return p
    raise KeyError(startswith)

for label, value in (("Name", "Ian Leong"), ("Student ID", "34423680"), ("Studio Session", STUDIO)):
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = row.cells
            for ci, c in enumerate(cells):
                if c.text.strip() == label and ci + 1 < len(cells) and not cells[ci + 1].text.strip():
                    set_font(cells[ci + 1].paragraphs[0].add_run(value), size=11)

add_paras(find("Tip: Test your URL")._p, [("", URL)])
add_paras(find("Describe your domain chosen")._p, DOMAIN)
add_paras(find("Describe the Why and Who")._p, WHY_WHO)
el = add_paras(find("Describe the", "What")._p, WHAT_INTRO, gap_after=False); el = add_table_after(el, WHAT_TABLE, (4.2, 6.6, 6.2)); add_paras(el, WHAT_PROCESS)
el = add_paras(find("Describe the", "How")._p, HOW_INTRO, gap_after=False); el = add_table_after(el, HOW_TABLE, (3.4, 6.2, 7.4)); add_paras(el, HOW_AFTER)

p = para_after(find("Note: Use the entire page")._p); p.add_run().add_picture(SKETCH, height=Cm(23.5))

# Part D: the full-page capture cut into three page-sized slices at full text width, one per page
from PIL import Image
from docx.enum.text import WD_BREAK
import os, tempfile
el = find("Paste a full-size screenshot")._p
im = Image.open(CAPTURE); W, H = im.size; n = 3; step = -(-H // n)
tmpdir = tempfile.mkdtemp()
for i in range(n):
    part = im.crop((0, i * step, W, min(H, (i + 1) * step))); fp = os.path.join(tmpdir, f"partd_{i + 1}.png"); part.save(fp)
    p = para_after(el); p.paragraph_format.space_after = Pt(0)
    if i: p.add_run().add_break(WD_BREAK.PAGE)
    p.add_run().add_picture(fp, width=Cm(16.0)); el = p._p

body = doc.element.body
for pict in list(body.iter(qn('w:pict'))):          # the template's separator lines
    r = pict.getparent(); r.getparent().remove(r)
for r in body.iter(qn('w:r')):                       # Times New Roman on every run, template prompts included
    rpr = r.find(qn('w:rPr'))
    if rpr is None: rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
    rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(k), FONT)
# the template leaves five empty paragraphs under every prompt: collapse each run of empties to one line
def is_empty(p_el):
    if p_el.find('.//' + qn('w:drawing')) is not None or p_el.find('.//' + qn('w:br')) is not None: return False
    return "".join(t.text or "" for t in p_el.iter(qn('w:t'))).strip() == ""
prev_empty = False
for p_el in list(body.iter(qn('w:p'))):
    if p_el.getparent().tag != qn('w:body'): continue          # leave table cells alone
    e = is_empty(p_el)
    if e and prev_empty: body.remove(p_el); continue
    prev_empty = e
for para in doc.paragraphs:                          # single spacing on every body paragraph
    if not para.style.name.startswith("Heading"):
        para.paragraph_format.space_before = Pt(0); para.paragraph_format.space_after = Pt(0); para.paragraph_format.line_spacing = 1.0
for st in doc.styles:
    try: st.font.name = FONT
    except Exception: pass

doc.save(OUT); print("wrote", OUT)
