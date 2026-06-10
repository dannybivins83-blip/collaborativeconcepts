"""Rebuild the WWS field-inspection checklist (clean version).
Fixes: sections kept together (no page-break runoff), lighter/less-boxy tables,
centered branded header with the real logo, clean text wrapping.
Run: python _build_collateral.py   ->  wwslgc/collateral/Subpart_D_Inspection_Checklist_LaGala.pdf
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, Image)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "wwslgc", "collateral", "Subpart_D_Inspection_Checklist_LaGala.pdf")
LOGO = os.path.join(REPO, "assets", "lagala-logo.png")

# Arial has the glyphs we need (>=, deg, section sign) -> no tofu boxes
F, FB = "Arial", "Arial-Bold"
try:
    pdfmetrics.registerFont(TTFont(F, r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont(FB, r"C:\Windows\Fonts\arialbd.ttf"))
except Exception:
    F, FB = "Helvetica", "Helvetica-Bold"

NAVY = colors.HexColor("#13233f")
GOLD = colors.HexColor("#c9a227")
INK = colors.HexColor("#1f2733")
MUTE = colors.HexColor("#5b6573")
GRID = colors.HexColor("#d8dce2")
ZEBRA = colors.HexColor("#f5f6f8")

title = ParagraphStyle("title", fontName=FB, fontSize=15, textColor=NAVY, alignment=1, leading=18)
sub = ParagraphStyle("sub", fontName=F, fontSize=10.5, textColor=GOLD, alignment=1, leading=13, spaceAfter=2)
legend = ParagraphStyle("legend", fontName=F, fontSize=8.5, textColor=MUTE, alignment=1, leading=11)
sect = ParagraphStyle("sect", fontName=FB, fontSize=9.5, textColor=colors.white, leading=12)
cell = ParagraphStyle("cell", fontName=F, fontSize=8.6, textColor=INK, leading=11)
chead = ParagraphStyle("chead", fontName=FB, fontSize=7.8, textColor=colors.white, leading=9, alignment=0)
cheadc = ParagraphStyle("cheadc", fontName=FB, fontSize=7.8, textColor=colors.white, leading=9, alignment=1)
field = ParagraphStyle("field", fontName=FB, fontSize=8.6, textColor=NAVY, leading=12)

SECTIONS = [
 ("1.  General Surface Conditions  ·  §1910.22", [
   "Walking-working surfaces clean, orderly, sanitary; floors dry where feasible (drainage / mats for wet processes)",
   "Surfaces free of hazards: sharp / protruding objects, loose boards, corrosion, leaks, spills, snow, ice",
   "Each surface supports its maximum intended load (people + equipment + materials)",
   "Safe means of access and egress provided and used at every surface",
   "Surfaces inspected regularly; hazards corrected / repaired before reuse, or guarded until repaired",
   "Structural repairs performed or supervised by a qualified person"]),
 ("2.  Portable Ladders  ·  §1910.23(b),(c)", [
   "Inspected before each shift; defective ladders tagged “Dangerous: Do Not Use” and removed",
   "Rungs / steps level, uniformly spaced 10–14 in; slip-resistant; free of puncture / laceration hazards",
   "Used on stable, level surfaces; secured on slippery surfaces / passageways / doorways",
   "Side rails extend ≥ 3 ft (0.9 m) above the upper landing surface",
   "Not loaded beyond max intended load; not moved / extended while occupied",
   "No single-rail ladders; not placed on boxes / barrels for height; top cap / top step not used as steps"]),
 ("3.  Fixed Ladders  ·  §1910.23(d) & §1910.28(b)(9)", [
   "Capable of supporting max intended load; corrosion-protected; surfaces free of hazards",
   "≥ 7 in (18 cm) clearance behind rungs; ≥ 15 in (38 cm) each side of centerline (no cage / well)",
   "Through / side-step rails extend ≥ 42 in (1.1 m) above landing; grab bars where required",
   "Ladders > 24 ft (7.3 m): personal fall arrest or ladder safety system (cage / well alone NOT compliant for new installs)",
   "Replacement sections trigger PFAS / ladder safety system; rest platforms ≤ 150 ft intervals",
   "NOTE: all fixed ladders must have PFAS or a ladder safety system by Nov 18, 2036"]),
 ("4.  Step Bolts & Manhole Steps  ·  §1910.24", [
   "Inspected at start of shift; corrosion- and slip-resistant",
   "Step bolts spaced 12–18 in; ≥ 4.5 in clear width; ≥ 7 in behind centerline",
   "No step bolt bent > 15° from perpendicular (remove & replace if so)",
   "Post-1/17/2017 step bolts support ≥ 4x max intended load"]),
 ("5.  Stairways  ·  §1910.25 & §1910.28(b)(11)", [
   "Standard stairs at 30–50°; max riser 9.5 in; min tread depth 9.5 in; min width 22 in",
   "Uniform riser heights & tread depths between landings; ≥ 6 ft 8 in vertical clearance",
   "Landings / platforms ≥ stair width and ≥ 30 in deep; door swing leaves ≥ 22 in usable platform",
   "Each stair supports ≥ 5x live load, never < 1,000 lb point load",
   "Flights with ≥ 3 treads & ≥ 4 risers have stair-rail systems + handrails (per Table D-2)",
   "Landings ≥ 4 ft above lower level protected by guardrail / stair rail; ship / alt-tread stairs have handrails both sides"]),
 ("6.  Dockboards  ·  §1910.26 & §1910.28(b)(4)", [
   "Support max intended load; designed / maintained to prevent transfer vehicles running off edge",
   "Portable dockboards secured / anchored against displacement; equipped with handholds",
   "Wheel chocks / sand shoes prevent transport vehicle movement while occupied",
   "Guardrails or handrails where fall ≥ 4 ft (exceptions: motorized materials handling, < 10 ft, trained)"]),
 ("7.  Rope Descent Systems & Anchorages  ·  §1910.27", [
   "Written owner certification on file: each anchorage tested / certified ≥ 5,000 lb any direction per worker",
   "Annual inspection by qualified person current; re-test ≤ every 10 years (verify next-due dates)",
   "RDS inspected at start of each shift; damaged / defective equipment removed immediately",
   "Proper rigging, anchorages & tiebacks (esp. counterweights, cornice hooks, parapet clamps)",
   "Each worker on independent PFAS; anchorages for lifelines & suspension lines kept independent",
   "Not used > 300 ft above grade; stabilization for descents > 130 ft; ropes padded at edges",
   "Tools secured by lanyard; not used in storms / gusty / excessive wind"]),
 ("8.  Fall Protection — Duty & Criteria  ·  §1910.28 / §1910.29", [
   "Every unprotected side / edge ≥ 4 ft protected (guardrail, safety net, or personal fall protection)",
   "Holes / skylights ≥ 4 ft: covers, guardrails, travel restraint, or PFAS; covers secured + rated ≥ 2x load",
   "Low-slope roof: < 6 ft from edge = full protection; 6–15 ft = protection; ≥ 15 ft = protection or enforced 15-ft work rule",
   "Guardrails: top rail 42 in (±3 in); withstands 200 lb top / 150 lb mid; openings ≤ 19 in",
   "Runways / ramps guarded each unprotected side; dangerous equipment guarded",
   "Toeboards ≥ 3.5 in where falling-object exposure; head protection provided"]),
 ("9.  Training  ·  §1910.30", [
   "Each exposed employee trained by a qualified person in fall-hazard recognition & procedures",
   "Trained in install / inspect / operate / maintain / disassemble of fall-protection systems used",
   "RDS users trained in rigging & use; dockboard users trained in placement / securing",
   "Retraining when workplace, equipment, or employee knowledge changes; training understandable"]),
]

# column widths (letter, 0.6in margins -> 7.3in usable)
CW = [3.85*inch, 0.5*inch, 0.5*inch, 0.5*inch, 1.45*inch]

def section_block(heading, items):
    bar = Table([[Paragraph(heading, sect)]], colWidths=[sum(CW)])
    bar.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),("LEFTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    head = [Paragraph("Inspection item", chead), Paragraph("OK", cheadc),
            Paragraph("DEF", cheadc), Paragraph("N/A", cheadc), Paragraph("Location / note", cheadc)]
    data = [head] + [[Paragraph(it, cell), "", "", "", ""] for it in items]
    t = Table(data, colWidths=CW, repeatRows=1)
    st = [
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#3a4a63")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(1,0),(3,-1),"CENTER"),
        ("LINEBELOW",(0,0),(-1,-1),0.4,GRID),
        ("LINEAFTER",(0,0),(-2,-1),0.4,GRID),
        ("BOX",(0,0),(-1,-1),0.5,GRID),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),5),
    ]
    for r in range(1, len(data)):  # subtle zebra only on alternating, very light
        if r % 2 == 0:
            st.append(("BACKGROUND",(0,r),(-1,r),ZEBRA))
    t.setStyle(TableStyle(st))
    return KeepTogether([bar, t, Spacer(1, 6)])

def meta_block():
    line = "_______________________________"
    rows = [
        [Paragraph("Project / building", field), Paragraph(line, cell), Paragraph("Date", field), Paragraph("____________", cell)],
        [Paragraph("Address", field), Paragraph(line, cell), Paragraph("Inspector", field), Paragraph("____________", cell)],
        [Paragraph("Owner / manager", field), Paragraph(line, cell), Paragraph("Weather / temp", field), Paragraph("____________", cell)],
    ]
    t = Table(rows, colWidths=[1.25*inch, 2.6*inch, 1.15*inch, 2.3*inch])
    t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),5),
                           ("LEFTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"BOTTOM")]))
    return t

def corrective_block():
    head = [Paragraph(h, cheadc if i else chead) for i,h in
            enumerate(["#", "§ / item deficient", "Location", "Corrective action / scope", "Priority"])]
    data = [head] + [[Paragraph(str(n), cheadc.clone('n', textColor=INK)), "", "", "", ""] for n in range(1,7)]
    t = Table(data, colWidths=[0.4*inch, 2.0*inch, 1.2*inch, 2.5*inch, 1.2*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#3a4a63")),
        ("ALIGN",(0,0),(0,-1),"CENTER"),("ALIGN",(4,0),(4,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BOX",(0,0),(-1,-1),0.5,GRID),
        ("INNERGRID",(0,0),(-1,-1),0.4,GRID),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),6)]))
    bar = Table([[Paragraph("Corrective action summary", sect)]], colWidths=[sum(CW)])
    bar.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),("LEFTPADDING",(0,0),(-1,-1),8),
                             ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    sig = Table([[Paragraph("Inspector signature", field), Paragraph("______________________________   Date ____________", cell)],
                 [Paragraph("Owner / mgr acknowledgment", field), Paragraph("______________________________   Date ____________", cell)]],
                colWidths=[2.0*inch, 5.3*inch])
    sig.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),9),("VALIGN",(0,0),(-1,-1),"BOTTOM")]))
    return KeepTogether([bar, t, Spacer(1,7), sig])

def header_footer(canvas, doc):
    canvas.saveState()
    w, h = letter
    # footer
    canvas.setStrokeColor(GRID); canvas.setLineWidth(0.5)
    canvas.line(0.6*inch, 0.55*inch, w-0.6*inch, 0.55*inch)
    canvas.setFont(F, 7); canvas.setFillColor(MUTE)
    canvas.drawString(0.6*inch, 0.4*inch, "La Gala Construction / Tilt Patchers, Inc.  ·  CGC059211  ·  Walking-Working Surfaces field checklist")
    canvas.drawRightString(w-0.6*inch, 0.4*inch, "Page %d" % doc.page)
    canvas.restoreState()

def build():
    doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch,
                            topMargin=0.6*inch, bottomMargin=0.7*inch, title="OSHA Subpart D Inspection Checklist")
    story = []
    if os.path.exists(LOGO):
        img = Image(LOGO, width=1.9*inch, height=1.9*inch*400/860)
        img.hAlign = "CENTER"
        story += [img, Spacer(1, 6)]
    story += [
        Paragraph("OSHA 1910 Subpart D — Walking-Working Surfaces", title),
        Paragraph("Field Inspection &amp; Compliance Checklist", sub),
        Spacer(1, 2),
    ]
    # gold rule
    rule = Table([[""]], colWidths=[sum(CW)]); rule.setStyle(TableStyle([("LINEABOVE",(0,0),(-1,-1),1.4,GOLD)]))
    story += [rule, Spacer(1, 8), meta_block(),
              Paragraph("Mark each item:  OK = compliant   ·   DEF = deficient (log below)   ·   N/A = not present", legend),
              Spacer(1, 10)]
    for heading, items in SECTIONS:
        story.append(section_block(heading, items))
    story.append(corrective_block())
    story += [Spacer(1, 6), Paragraph(
        "Field compliance checklist only. Anchorage load-test certification (§1910.27 / §1910.140) and any structural repair "
        "affecting integrity must be performed and sealed by a licensed Florida professional engineer. Thresholds per 29 CFR 1910 "
        "Subpart D. © La Gala Construction / Tilt Patchers, Inc. — CGC059211.",
        ParagraphStyle("disc", fontName=F, fontSize=7, textColor=MUTE, leading=9))]
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print("Built:", OUT, "(%.1f KB)" % (os.path.getsize(OUT)/1024))

if __name__ == "__main__":
    build()
