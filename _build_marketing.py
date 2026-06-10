"""Rebuild the WWS marketing collateral with the sharpened 'compliance-check'
enforcement tone: the fall NEP (no complaint needed), 'not cited isn't compliant',
and the 2026 penalty numbers. Generates all three pieces from one place.

Run: python _build_marketing.py
 -> wwslgc/collateral/OSHA_WWS_Flyer.pdf
 -> wwslgc/collateral/Free_Assessment_Offer.pdf
 -> wwslgc/collateral/LaGala_WWS_Postcard_4x6_READY.pdf
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, Image, ListFlowable, ListItem)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

REPO = os.path.dirname(os.path.abspath(__file__))
COL = os.path.join(REPO, "wwslgc", "collateral")
LOGO = os.path.join(REPO, "assets", "lagala-logo.png")

F, FB = "Arial", "Arial-Bold"
try:
    pdfmetrics.registerFont(TTFont(F, r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont(FB, r"C:\Windows\Fonts\arialbd.ttf"))
except Exception:
    F, FB = "Helvetica", "Helvetica-Bold"

NAVY = colors.HexColor("#13233f")
NAVY2 = colors.HexColor("#1f3c63")
GOLD = colors.HexColor("#c9a227")
GOLDLT = colors.HexColor("#f0d060")
INK = colors.HexColor("#1f2733")
MUTE = colors.HexColor("#5b6573")
CREAM = colors.HexColor("#f6efd9")
GRID = colors.HexColor("#d8dce2")

# ---- shared styles (flyer / offer) ----
company = ParagraphStyle("company", fontName=FB, fontSize=12.5, textColor=NAVY, alignment=1, leading=15)
tagline = ParagraphStyle("tagline", fontName=F, fontSize=8.5, textColor=MUTE, alignment=1, leading=11)
lic = ParagraphStyle("lic", fontName=F, fontSize=8, textColor=GOLD, alignment=1, leading=10)
h1 = ParagraphStyle("h1", fontName=FB, fontSize=18, textColor=NAVY, alignment=1, leading=21, spaceBefore=8)
lead = ParagraphStyle("lead", fontName=F, fontSize=9.5, textColor=INK, leading=13.5, spaceBefore=4)
scare = ParagraphStyle("scare", fontName=FB, fontSize=10, textColor=NAVY, leading=13.5, spaceBefore=6, spaceAfter=2)
sh = ParagraphStyle("sh", fontName=FB, fontSize=11, textColor=NAVY, leading=14, spaceBefore=10, spaceAfter=2)
bdy = ParagraphStyle("bdy", fontName=F, fontSize=9, textColor=INK, leading=12.5)
boxh = ParagraphStyle("boxh", fontName=FB, fontSize=9.5, textColor=NAVY, leading=12)
boxb = ParagraphStyle("boxb", fontName=F, fontSize=8.8, textColor=INK, leading=12)
cta = ParagraphStyle("cta", fontName=FB, fontSize=11, textColor=colors.white, alignment=1, leading=14)
ctas = ParagraphStyle("ctas", fontName=F, fontSize=8.8, textColor=colors.white, alignment=1, leading=11)
disc = ParagraphStyle("disc", fontName=F, fontSize=7, textColor=MUTE, leading=9, spaceBefore=6)


def bullets(items, style=bdy, gap=2):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=14, value="•", bulletColor=GOLD, spaceBefore=gap) for t in items],
        bulletType="bullet", leftIndent=12)


def header(story):
    if os.path.exists(LOGO):
        img = Image(LOGO, width=1.55 * inch, height=1.55 * inch * 400 / 860)
        img.hAlign = "CENTER"
        story += [img, Spacer(1, 3)]
    story += [Paragraph("LA GALA CONSTRUCTION&nbsp;&nbsp;/&nbsp;&nbsp;Tilt Patchers, Inc.", company),
              Paragraph("Concrete Restoration&nbsp; · &nbsp;Waterproofing&nbsp; · &nbsp;Fall-Protection &amp; Compliance", tagline),
              Paragraph("FL General Contractor CGC059211&nbsp;&nbsp;·&nbsp;&nbsp;in partnership with a FL State Certified Engineer", lic)]
    rule = Table([[""]], colWidths=[7.3 * inch]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.3, GOLD)]))
    story += [Spacer(1, 6), rule, Spacer(1, 2)]


def penalty_box():
    inner = [[Paragraph("What a Subpart D citation costs in 2026", boxh)],
             [Paragraph("About <b>$16,500 per serious violation</b> · the same amount <b>per day</b> past the abatement deadline · up to roughly <b>$165,000</b> for a willful or repeat violation &mdash; <b>per violation</b>, before injury liability or insurance fallout. OSHA raises these maximums every January.", boxb)]]
    t = Table(inner, colWidths=[7.3 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM), ("BOX", (0, 0), (-1, -1), 0.8, GOLD),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (0, 0), 7), ("BOTTOMPADDING", (0, 0), (0, 0), 1),
                           ("TOPPADDING", (0, 1), (0, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, -1), 8)]))
    return t


def cta_band(big, small):
    inner = [[Paragraph(big, cta)], [Paragraph(small, ctas)]]
    t = Table(inner, colWidths=[7.3 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 12),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (0, 0), 9),
                           ("BOTTOMPADDING", (0, 0), (0, 0), 1), ("TOPPADDING", (0, 1), (0, 1), 2),
                           ("BOTTOMPADDING", (0, 1), (-1, -1), 9)]))
    return t


def footer_cb(canvas, doc):
    canvas.saveState(); w, h = letter
    canvas.setStrokeColor(GRID); canvas.setLineWidth(0.5)
    canvas.line(0.6 * inch, 0.5 * inch, w - 0.6 * inch, 0.5 * inch)
    canvas.setFont(F, 7); canvas.setFillColor(MUTE)
    canvas.drawCentredString(w / 2, 0.36 * inch, "La Gala Construction / Tilt Patchers, Inc.  ·  25 SE 7th Street, Suite 12, Deerfield Beach, FL 33441  ·  (561) 475-8615  ·  lagalacon.com")
    canvas.restoreState()


def doc_build(path, story, title):
    d = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                          topMargin=0.55 * inch, bottomMargin=0.6 * inch, title=title)
    d.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
    print("Built:", os.path.basename(path), "(%.0f KB)" % (os.path.getsize(path) / 1024))


# ============================ FLYER ============================
def build_flyer():
    s = []
    header(s)
    s += [Paragraph("Does your property pass OSHA's fall-protection rule?", h1)]
    s += [Paragraph("Since January 2017, OSHA's Walking-Working Surfaces standard (29 CFR 1910, Subpart D) has applied to nearly every commercial property in Florida &mdash; floors, stairs, ramps, loading docks, roof access, and fall-protection anchorages. The general-industry trigger is just <b>4 feet</b>. And OSHA doesn't need a complaint to walk in: its <b>national emphasis program on falls</b> lets an inspector open a case the moment they spot an unprotected edge or an uncertified anchor.", lead)]
    s += [Paragraph("Not being cited yet isn't the same as being compliant. Most older commercial buildings carry at least one Subpart D gap right now &mdash; the owners who get hit aren't unlucky, they're the ones who bet nobody would look.", scare)]
    s += [Paragraph("One accountable team: we certify it, and we fix it.", sh)]
    s += [bullets([
        "<b>FL State Certified Engineer (engineering):</b> performs and SEALS the engineered inspections and the 5,000-lb anchor certifications.",
        "<b>La Gala (contractor):</b> self-performs the restoration that brings the surface into compliance &mdash; including Complete Building Code Compliant Recertifications. No hand-offs.",
    ])]
    s += [Paragraph("What we self-perform", sh)]
    s += [bullets([
        "Spalled / slick / cracked surfaces → concrete restoration + slip-resistant urethane/epoxy traffic coating",
        "Standing water / poor drainage → waterproofing membrane, slope correction, drainage repair",
        "Deteriorated stairs → tread &amp; nosing rebuild, handrails and guardrails",
        "Unprotected roof / deck edges → guardrail, hole covers, fall-protection anchor points",
        "Uncertified rope-descent anchorages → anchor install / replacement (the engineer seals the certification)",
    ])]
    s += [Spacer(1, 8), penalty_box()]
    s += [Paragraph("The recurring obligation &mdash; §1910.27", sh)]
    s += [Paragraph("Each anchorage must hold 5,000 lb in any direction per worker; the owner must keep a written certification, inspect annually, and re-test at least every 10 years. We manage the whole cycle &mdash; so you stay compliant and budgeted.", bdy)]
    s += [Spacer(1, 12), cta_band("FREE walking-surface assessment &mdash; find your gaps before an inspector does.",
                                  "A no-obligation walkthrough against the Subpart D checklist, with written documentation for your file.")]
    s += [Spacer(1, 6), Paragraph("Daniel Bivins, Client Relations&nbsp;&nbsp;·&nbsp;&nbsp;(561) 475-8615&nbsp;&nbsp;·&nbsp;&nbsp;danny@lagalacon.com&nbsp;&nbsp;·&nbsp;&nbsp;lagalacon.com",
                                  ParagraphStyle("contact", fontName=FB, fontSize=9.5, textColor=NAVY, alignment=1, leading=12))]
    s += [Paragraph("La Gala Construction provides licensed contracting services; anchorage load-test certification is performed and sealed by a FL State Certified Engineer. Penalty figures are OSHA civil-penalty maximums, adjusted annually for inflation; thresholds per 29 CFR 1910 Subpart D (final rule, eff. 1/17/2017). Not legal advice.", disc)]
    doc_build(os.path.join(COL, "OSHA_WWS_Flyer.pdf"), s, "OSHA WWS Flyer")


# ============================ OFFER ============================
def build_offer():
    s = []
    header(s)
    s += [Paragraph("Book Your FREE Walking-Surface Assessment", h1)]
    s += [Paragraph("Not being cited yet isn't the same as being compliant &mdash; know where you stand before an inspector does.",
                    ParagraphStyle("offsub", fontName=FB, fontSize=11, textColor=GOLD, alignment=1, leading=14, spaceBefore=2, spaceAfter=2))]
    s += [Paragraph("What you get", sh)]
    s += [bullets([
        "A no-obligation walkthrough of your property by a licensed Florida GC.",
        "An inspection against the OSHA Subpart D checklist (§1910.22–.30).",
        "A written summary of findings you can keep in your compliance file.",
        "A clear, priced scope to correct anything flagged &mdash; self-performed by La Gala, including Complete Building Code Compliant Recertifications.",
    ])]
    s += [Paragraph("What we check (preview)", sh)]
    s += [bullets([
        "<b>§1910.22 General surfaces</b> &mdash; clean, dry, slip-resistant, in good repair; drainage and standing water",
        "<b>§1910.25 Stairways</b> &mdash; riser/tread geometry, handrails and stair-rail systems",
        "<b>§1910.27 Rope descent &amp; anchorages</b> &mdash; 5,000-lb written certification, annual inspection, 10-year re-test (engineer-sealed)",
        "<b>§1910.28/.29 Fall protection</b> &mdash; unprotected edges ≥ 4 ft, holes/skylights, guardrail strength criteria",
    ])]
    s += [Spacer(1, 8), penalty_box()]
    s += [Paragraph("Why now", sh)]
    s += [Paragraph("OSHA's fall-protection emphasis program means inspectors don't wait for a complaint &mdash; an unprotected edge, a spalled walkway, or an uncertified anchor is a documented liability the moment they (or an attorney) find it. Stack a few items on one inspection and the penalty climbs into six figures fast. The assessment is free; the gap you don't know about isn't.", bdy)]
    s += [Spacer(1, 12), cta_band("Schedule your free assessment this week.",
                                  "One walkthrough tells you exactly where you stand &mdash; and what, if anything, it takes to close it out.")]
    s += [Spacer(1, 6), Paragraph("Daniel Bivins, Client Relations&nbsp;&nbsp;·&nbsp;&nbsp;(561) 475-8615&nbsp;&nbsp;·&nbsp;&nbsp;danny@lagalacon.com&nbsp;&nbsp;·&nbsp;&nbsp;lagalacon.com",
                                  ParagraphStyle("contact2", fontName=FB, fontSize=9.5, textColor=NAVY, alignment=1, leading=12))]
    s += [Paragraph("La Gala Construction provides licensed contracting services; anchorage load-test certification is performed and sealed by a FL State Certified Engineer. Penalty figures are OSHA civil-penalty maximums, adjusted annually for inflation; thresholds per 29 CFR 1910 Subpart D (final rule, eff. 1/17/2017). Not legal advice.", disc)]
    doc_build(os.path.join(COL, "Free_Assessment_Offer.pdf"), s, "Free Walking-Surface Assessment")


# ============================ POSTCARD (4x6, 2 pages) ============================
PW, PH = 432, 288  # 6x4 in landscape, points


def wrap(c, text, font, size, maxw):
    c.setFont(font, size)
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_lines(c, lines, x, y, font, size, lead, color, center=False, cx=None):
    c.setFont(font, size); c.setFillColor(color)
    for ln in lines:
        if center:
            c.drawCentredString(cx, y, ln)
        else:
            c.drawString(x, y, ln)
        y -= lead
    return y


def build_postcard():
    out = os.path.join(COL, "LaGala_WWS_Postcard_4x6_READY.pdf")
    c = pdfcanvas.Canvas(out, pagesize=(PW, PH))

    # ---------- FRONT ----------
    c.setFillColor(NAVY); c.rect(0, 0, PW, PH, fill=1, stroke=0)
    c.setFillColor(NAVY2); c.rect(0, PH - 6, PW, 6, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(0, PH - 6, PW, 2, fill=1, stroke=0)
    cx = PW / 2
    c.setFillColor(colors.white); c.setFont(FB, 17)
    c.drawCentredString(cx, PH - 34, "LA GALA CONSTRUCTION")
    c.setFillColor(GOLDLT); c.setFont(F, 8.5)
    c.drawCentredString(cx, PH - 48, "in partnership with a FL State Certified Engineer")
    c.setFillColor(GOLD); c.setFont(FB, 8)
    c.drawCentredString(cx, PH - 74, "O S H A   2 9   C F R   1 9 1 0   ·   S U B P A R T   D")
    # headline
    c.setFillColor(colors.white)
    hl = ["Does your building pass", "OSHA's fall-protection rule?"]
    y = PH - 102
    for i, ln in enumerate(hl):
        c.setFont(FB, 21 if i == 0 else 21)
        c.drawCentredString(cx, y, ln); y -= 26
    # enforcement line
    c.setFillColor(colors.HexColor("#c5d0e0")); c.setFont(F, 9)
    for ln in ["An inspector doesn't need a complaint to open a case —",
               "and not being cited yet isn't the same as being compliant."]:
        c.drawCentredString(cx, y, ln); y -= 12.5
    # gold CTA band
    bandh = 30; bw = 300; bx = cx - bw / 2; by = 40
    c.setFillColor(GOLD); c.roundRect(bx, by, bw, bandh, 6, fill=1, stroke=0)
    c.setFillColor(NAVY); c.setFont(FB, 13)
    c.drawCentredString(cx, by + 10, "FREE WALKING-SURFACE ASSESSMENT")
    c.setFillColor(colors.white); c.setFont(FB, 9.5)
    c.drawCentredString(cx, 26, "lagalacon.com")
    c.setFillColor(GOLDLT); c.setFont(F, 7)
    c.drawCentredString(cx, 13, "Licensed FL General Contractor  ·  CGC059211")
    c.showPage()

    # ---------- BACK ----------
    c.setFillColor(colors.white); c.rect(0, 0, PW, PH, fill=1, stroke=0)
    M = 22
    midx = 250  # divider between message (left) and mailing panel (right)
    # message block
    yL = PH - 30
    yL = draw_lines(c, ["Know where you stand —", "before an inspector does."], M, yL, FB, 14, 17, NAVY)
    yL -= 8
    body = ("OSHA's fall-protection emphasis program lets an inspector open a case the "
            "moment they spot an unprotected edge or an uncertified anchor — no complaint "
            "required. A serious citation runs about $16,500; a willful or repeat one up to "
            "roughly $165,000, per violation.")
    yL = draw_lines(c, wrap(c, body, F, 8.2, midx - M - 8), M, yL - 2, F, 8.2, 11, INK)
    yL -= 6
    body2 = ("We self-perform the concrete, coating, drainage and fall-protection work — "
             "including Complete Building Code Compliant Recertifications; a FL State Certified "
             "Engineer seals the certification.")
    yL = draw_lines(c, wrap(c, body2, F, 8.2, midx - M - 8), M, yL, F, 8.2, 11, INK)
    yL -= 10
    c.setFillColor(GOLD); c.setFont(FB, 9)
    c.drawString(M, yL, "Schedule your free assessment:")
    yL -= 13
    c.setFillColor(NAVY); c.setFont(FB, 9)
    c.drawString(M, yL, "Daniel Bivins, Client Relations")
    yL -= 12
    c.setFillColor(INK); c.setFont(F, 8.5)
    c.drawString(M, yL, "(561) 475-8615  ·  danny@lagalacon.com")

    # divider
    c.setStrokeColor(GRID); c.setLineWidth(0.7); c.line(midx, 20, midx, PH - 20)

    # mailing panel (right)
    px = midx + 16
    # stamp box
    c.setStrokeColor(MUTE); c.setLineWidth(0.7); c.setDash(2, 2)
    c.rect(PW - 58, PH - 64, 40, 46, fill=0, stroke=1); c.setDash()
    c.setFillColor(MUTE); c.setFont(F, 5.5)
    c.drawCentredString(PW - 38, PH - 36, "PLACE"); c.drawCentredString(PW - 38, PH - 44, "STAMP"); c.drawCentredString(PW - 38, PH - 52, "HERE")
    # return address (narrow stack so it clears the stamp box)
    c.setFillColor(NAVY); c.setFont(FB, 7.5)
    c.drawString(px, PH - 26, "La Gala Construction")
    c.setFillColor(MUTE); c.setFont(F, 7)
    c.drawString(px, PH - 36, "Tilt Patchers, Inc.")
    c.drawString(px, PH - 46, "25 SE 7th Street, Suite 12")
    c.drawString(px, PH - 56, "Deerfield Beach, FL 33441")
    c.drawString(px, PH - 66, "CGC059211")
    # addressee
    c.setFillColor(INK); c.setFont(FB, 8.5)
    c.drawString(px, 96, "Building Owner / Property Manager")
    c.setStrokeColor(GRID); c.setLineWidth(0.6)
    for ay in (78, 62, 46):
        c.line(px, ay, PW - 18, ay)
    c.setFillColor(MUTE); c.setFont(F, 6)
    c.drawString(px, 28, "Keep clear for delivery address & postage")
    c.showPage()
    c.save()
    print("Built:", os.path.basename(out), "(%.0f KB, 2 pages 6x4)" % (os.path.getsize(out) / 1024))


if __name__ == "__main__":
    build_flyer()
    build_offer()
    build_postcard()
