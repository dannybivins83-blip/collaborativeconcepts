"""WWS inspection document engine — pre-fills 4 PDFs from a single inspection dict.

Canonical source for the builders; the same SUBPART_D + _doc_* functions are
inlined into api/index.py for the serverless endpoints (kept identical).
Server-safe: built-in Helvetica only (no font files), CP1252-safe glyphs
(§ · — ° ok; avoid ≥ → ✓). Returns PDF bytes; no storage needed.

Run: python _build_inspection_docs.py   -> renders all 4 to PNG for review
"""
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether)

NAVY = colors.HexColor("#13233f"); GOLD = colors.HexColor("#c9a227")
INK = colors.HexColor("#1f2733"); MUTE = colors.HexColor("#5b6573")
LINE = colors.HexColor("#d8dce2"); ZEBRA = colors.HexColor("#f5f6f8")
CREAM = colors.HexColor("#f6efd9"); RED = "#b3261e"; GREEN = "#1e7a3d"; GREY = "#5b6573"
F, FB = "Helvetica", "Helvetica-Bold"

# OSHA 1910 Subpart D field template — seeds an inspection's findings list.
SUBPART_D = [
    ("General Surface Conditions", "§1910.22", [
        "Surfaces clean, orderly, sanitary; dry or drained where wet",
        "Free of trip / sharp / corrosion / spill / ice hazards",
        "Each surface supports its maximum intended load",
        "Safe means of access and egress at every surface",
        "Inspected regularly; hazards corrected or guarded"]),
    ("Portable Ladders", "§1910.23(b),(c)", [
        "Inspected before use; defective ladders tagged out",
        "Rungs slip-resistant, level, spaced 10-14 in",
        "On stable level surface; secured where needed",
        "Side rails extend >= 3 ft above the landing",
        "Not overloaded; no improper use (boxes, top cap)"]),
    ("Fixed Ladders", "§1910.23(d)", [
        "Supports max load; corrosion-protected",
        "Clearances behind / beside rungs per code",
        "Through / side-step extensions; grab bars where required",
        "Ladders > 24 ft: PFAS or ladder safety system",
        "All fixed ladders need PFAS / LSS by Nov 18, 2036"]),
    ("Stairways", "§1910.25", [
        "Riser / tread geometry and width within limits",
        "Uniform risers and treads between landings",
        "Landings sized correctly; clearance maintained",
        "Stair-rail + handrails per Table D-2",
        "Landings >= 4 ft above lower level guarded"]),
    ("Dockboards", "§1910.26", [
        "Supports load; run-off prevented",
        "Secured / anchored against displacement; handholds",
        "Wheel chocks / restraints where required",
        "Guardrails where fall hazard >= 4 ft"]),
    ("Rope Descent Systems & Anchorages", "§1910.27", [
        "Each anchorage certified >= 5,000 lb per worker",
        "Annual qualified-person inspection current",
        "Anchorages re-tested at least every 10 years",
        "RDS inspected at start of each shift",
        "Each worker on an independent PFAS"]),
    ("Fall Protection - Duty & Criteria", "§1910.28 / .29", [
        "Unprotected sides / edges >= 4 ft protected",
        "Holes / skylights covered, guarded, or PFAS",
        "Low-slope roof edge work rules met",
        "Guardrails meet 200 / 150 lb strength criteria",
        "Toeboards where falling-object exposure exists"]),
    ("Training", "§1910.30", [
        "Trained by qualified person in fall-hazard recognition",
        "Trained to use the fall-protection systems in place",
        "RDS / dockboard users trained for their equipment",
        "Retraining when conditions or equipment change"]),
]


def seed_findings():
    out = []
    for section, std, items in SUBPART_D:
        for it in items:
            out.append({"section": section, "std": std, "item": it, "result": "", "severity": "", "note": ""})
    return out


def _esc(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles():
    return {
        "wordmark": ParagraphStyle("wm", fontName=FB, fontSize=13, textColor=NAVY, leading=15),
        "doctype": ParagraphStyle("dt", fontName=F, fontSize=9, textColor=GOLD, leading=11, spaceAfter=1),
        "h1": ParagraphStyle("h1", fontName=FB, fontSize=17, textColor=NAVY, leading=20, spaceBefore=2, spaceAfter=2),
        "meta": ParagraphStyle("meta", fontName=F, fontSize=8.5, textColor=MUTE, leading=12),
        "metab": ParagraphStyle("metab", fontName=FB, fontSize=8.5, textColor=NAVY, leading=12),
        "sect": ParagraphStyle("sect", fontName=FB, fontSize=10.5, textColor=NAVY, leading=13, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", fontName=F, fontSize=9.5, textColor=INK, leading=13.5, spaceBefore=2),
        "th": ParagraphStyle("th", fontName=FB, fontSize=8, textColor=colors.white, leading=10),
        "thc": ParagraphStyle("thc", fontName=FB, fontSize=8, textColor=colors.white, leading=10, alignment=1),
        "td": ParagraphStyle("td", fontName=F, fontSize=8.5, textColor=INK, leading=11),
        "tdc": ParagraphStyle("tdc", fontName=F, fontSize=8.5, textColor=INK, leading=11, alignment=1),
        "tdr": ParagraphStyle("tdr", fontName=F, fontSize=8.5, textColor=INK, leading=11, alignment=2),
        "key": ParagraphStyle("key", fontName=F, fontSize=9, textColor=NAVY, leading=13, backColor=CREAM, borderPadding=(5, 6, 5, 6)),
        "disc": ParagraphStyle("disc", fontName=F, fontSize=7, textColor=MUTE, leading=9, spaceBefore=8),
    }


def _footer(c, d):
    c.saveState(); w, h = letter
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(0.7 * inch, 0.55 * inch, w - 0.7 * inch, 0.55 * inch)
    c.setFont(F, 7); c.setFillColor(MUTE)
    c.drawString(0.7 * inch, 0.4 * inch, "La Gala Construction / Tilt Patchers, Inc.  ·  CGC059211  ·  in partnership with a FL State Certified Engineer")
    c.drawRightString(w - 0.7 * inch, 0.4 * inch, "Page %d" % d.page)
    c.restoreState()


def _header(story, st, doctype, title, insp):
    p = insp.get("property", {}); cl = insp.get("client", {}); insr = insp.get("inspector", {})
    story.append(Paragraph("LA GALA CONSTRUCTION", st["wordmark"]))
    story.append(Paragraph(_esc(doctype), st["doctype"]))
    story.append(Paragraph(_esc(title), st["h1"]))
    rule = Table([[""]], colWidths=[7.1 * inch]); rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.3, GOLD)]))
    story.append(Spacer(1, 3)); story.append(rule); story.append(Spacer(1, 6))
    def kv(k, v): return [Paragraph(k, st["meta"]), Paragraph(_esc(v or "—"), st["metab"])]
    rows = [
        kv("Property", p.get("name", "")) + kv("Inspected", insr.get("date", "")),
        kv("Address", p.get("address", "")) + kv("Inspector", insr.get("name", "")),
        kv("Owner / contact", (cl.get("name", "") + (("  ·  " + cl.get("company", "")) if cl.get("company") else "")).strip(" ·")) + kv("License", insr.get("license", "CGC059211")),
    ]
    t = Table(rows, colWidths=[0.95 * inch, 2.55 * inch, 0.85 * inch, 2.05 * inch])
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 6))


def _table_style(headcols=1):
    s = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3a4a63")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    return TableStyle(s)


def _new(title):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.7 * inch, title=title)
    return buf, doc


def _finish(buf, doc, story):
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _zebra(t, nrows, start=1):
    for r in range(start, nrows):
        if (r - start) % 2 == 1:
            t.setStyle(TableStyle([("BACKGROUND", (0, r), (-1, r), ZEBRA)]))


# ---------------------------------------------------------------- 1. CHECKLIST
def doc_checklist(insp):
    st = _styles(); buf, doc = _new("Completed OSHA Subpart D Checklist"); story = []
    _header(story, st, "OSHA 1910 Subpart D - field compliance record", "Completed Inspection Checklist", insp)
    findings = insp.get("findings") or seed_findings()
    secs, order = {}, []
    for f in findings:
        s = f.get("section", "Other")
        if s not in secs:
            secs[s] = []; order.append(s)
        secs[s].append(f)
    for s in order:
        std = secs[s][0].get("std", "")
        story.append(Paragraph(_esc(s) + "  ·  " + _esc(std), st["sect"]))
        rows = [[Paragraph("Inspection item", st["th"]), Paragraph("Result", st["thc"]), Paragraph("Note", st["th"])]]
        for f in secs[s]:
            res = (f.get("result") or "").lower()
            label = {"ok": "OK", "def": "DEF", "na": "N/A"}.get(res, "—")
            col = RED if res == "def" else (GREEN if res == "ok" else GREY)
            rows.append([Paragraph(_esc(f.get("item", "")), st["td"]),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (col, label), st["tdc"]),
                         Paragraph(_esc(f.get("note", "")), st["td"])])
        t = Table(rows, colWidths=[3.7 * inch, 0.8 * inch, 2.6 * inch], repeatRows=1)
        t.setStyle(_table_style()); _zebra(t, len(rows))
        story.append(t)
    defs = [f for f in findings if (f.get("result") or "").lower() == "def"]
    story.append(Paragraph("Deficiencies to correct (%d)" % len(defs), st["sect"]))
    if defs:
        for f in defs:
            story.append(Paragraph("&bull; <b>%s</b> (%s): %s" % (_esc(f.get("item", "")), _esc(f.get("std", "")), _esc(f.get("note", "") or "see field notes")), st["body"]))
    else:
        story.append(Paragraph("No deficiencies recorded at the time of inspection.", st["body"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Inspector signature: ______________________________     Date: ____________", st["body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Owner / manager acknowledgment: ______________________________     Date: ____________", st["body"]))
    story.append(Paragraph("Field compliance record only. Anchorage load-test certification (§1910.27) and any structural repair must be performed and sealed by a licensed Florida professional engineer. Thresholds per 29 CFR 1910 Subpart D.", st["disc"]))
    return _finish(buf, doc, story)


# ------------------------------------------------------------------- 2. REPORT
SEV = {"high": ("#b3261e", "HIGH"), "med": ("#b8860b", "MEDIUM"), "low": ("#1e7a3d", "LOW")}


def doc_report(insp):
    st = _styles(); buf, doc = _new("WWS Inspection Report"); story = []
    _header(story, st, "Walking-Working Surfaces - inspection findings", "Inspection Report", insp)
    findings = insp.get("findings") or []
    defs = [f for f in findings if (f.get("result") or "").lower() == "def"]
    # summary band
    nhigh = sum(1 for f in defs if (f.get("severity") or "").lower() == "high")
    band = [[Paragraph("Items reviewed", st["thc"]), Paragraph("Deficiencies", st["thc"]), Paragraph("High severity", st["thc"]), Paragraph("Standards", st["thc"])],
            [Paragraph(str(len(findings)), st["tdc"]), Paragraph(str(len(defs)), st["tdc"]), Paragraph(str(nhigh), st["tdc"]), Paragraph(str(len(set(f.get("std", "") for f in findings))), st["tdc"])]]
    bt = Table(band, colWidths=[1.78 * inch] * 4); bt.setStyle(_table_style())
    story.append(bt); story.append(Spacer(1, 4))
    if insp.get("summary"):
        story.append(Paragraph("Summary", st["sect"]))
        story.append(Paragraph(_esc(insp["summary"]), st["body"]))
    story.append(Paragraph("Findings", st["sect"]))
    if defs:
        rows = [[Paragraph("Standard", st["th"]), Paragraph("Finding", st["th"]), Paragraph("Severity", st["thc"]), Paragraph("Note", st["th"])]]
        for f in defs:
            sevc, sevl = SEV.get((f.get("severity") or "").lower(), (GREY, "—"))
            rows.append([Paragraph(_esc(f.get("std", "")), st["td"]),
                         Paragraph(_esc(f.get("item", "")), st["td"]),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (sevc, sevl), st["tdc"]),
                         Paragraph(_esc(f.get("note", "")), st["td"])])
        t = Table(rows, colWidths=[1.0 * inch, 2.7 * inch, 0.8 * inch, 2.6 * inch], repeatRows=1)
        t.setStyle(_table_style()); _zebra(t, len(rows))
        story.append(t)
    else:
        story.append(Paragraph("No deficiencies were identified at the time of inspection.", st["body"]))
    photos = insp.get("photos") or []
    if photos:
        story.append(Paragraph("Photo log", st["sect"]))
        rows = [[Paragraph("#", st["thc"]), Paragraph("Caption", st["th"]), Paragraph("Reference", st["th"])]]
        for i, ph in enumerate(photos, 1):
            rows.append([Paragraph(str(i), st["tdc"]), Paragraph(_esc(ph.get("caption", "")), st["td"]), Paragraph(_esc(ph.get("url", "") or "captured in SiteCam"), st["td"])])
        t = Table(rows, colWidths=[0.4 * inch, 3.4 * inch, 3.3 * inch], repeatRows=1)
        t.setStyle(_table_style()); _zebra(t, len(rows)); story.append(t)
    if insp.get("recommendations"):
        story.append(Paragraph("Recommendations", st["sect"]))
        story.append(Paragraph(_esc(insp["recommendations"]), st["body"]))
    story.append(Paragraph("La Gala Construction provides licensed contracting services; engineered inspection and anchorage load-test certification are performed and sealed by an independent licensed Florida professional engineer. La Gala does not provide engineering services. Not legal advice.", st["disc"]))
    return _finish(buf, doc, story)


# --------------------------------------------------------- 3. ENGINEER PACKET
def doc_cert(insp):
    st = _styles(); buf, doc = _new("Engineer Certification Packet"); story = []
    _header(story, st, "For review and seal by the licensed FL professional engineer", "Engineer Certification Packet", insp)
    pe = insp.get("pe", {})
    story.append(Paragraph("Items submitted for engineered certification", st["sect"]))
    findings = insp.get("findings") or []
    eng = [f for f in findings if f.get("std", "").startswith("§1910.27") or "anchor" in (f.get("item", "").lower()) or (f.get("result", "").lower() == "def" and (f.get("severity", "").lower() == "high"))]
    if not eng:
        eng = [f for f in findings if f.get("std", "").startswith("§1910.27")]
    rows = [[Paragraph("Standard", st["th"]), Paragraph("Item requiring engineered certification", st["th"]), Paragraph("Field note", st["th"])]]
    for f in (eng or [{"std": "§1910.27", "item": "Roof anchorage load-test certification (5,000 lb / worker)", "note": ""}]):
        rows.append([Paragraph(_esc(f.get("std", "")), st["td"]), Paragraph(_esc(f.get("item", "")), st["td"]), Paragraph(_esc(f.get("note", "")), st["td"])])
    t = Table(rows, colWidths=[1.0 * inch, 3.5 * inch, 2.6 * inch], repeatRows=1)
    t.setStyle(_table_style()); _zebra(t, len(rows)); story.append(t)
    story.append(Spacer(1, 6))
    story.append(Paragraph("Scope of certification requested", st["sect"]))
    story.append(Paragraph("The engineer is asked to inspect, test where applicable, and provide a sealed certification that the items above meet 29 CFR 1910 Subpart D (including §1910.27 anchorage capacity of 5,000 lb in any direction per worker) and applicable Florida Building Code. La Gala Construction performs the corrective work <b>to the engineer's sealed specification</b>.", st["key"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Engineer of record", st["sect"]))
    rows = [
        [Paragraph("Name", st["meta"]), Paragraph(_esc(pe.get("name", "") or "______________________________"), st["metab"])],
        [Paragraph("Firm", st["meta"]), Paragraph(_esc(pe.get("firm", "") or "______________________________"), st["metab"])],
        [Paragraph("FL PE license #", st["meta"]), Paragraph(_esc(pe.get("license", "") or "______________________________"), st["metab"])],
    ]
    t = Table(rows, colWidths=[1.3 * inch, 5.8 * inch]); t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(t); story.append(Spacer(1, 22))
    seal = Table([[Paragraph("Engineer signature & date", st["meta"]), Paragraph("Professional engineer seal", st["meta"])],
                  [Paragraph("______________________________", st["body"]), Paragraph("", st["body"])]],
                 colWidths=[3.55 * inch, 3.55 * inch], rowHeights=[14, 96])
    seal.setStyle(TableStyle([("BOX", (1, 0), (1, 1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
    story.append(seal)
    return _finish(buf, doc, story)


# ------------------------------------------------------------- 4. PROPOSAL
def _money(v):
    try:
        return "{:,.0f}".format(float(str(v).replace(",", "").replace("$", "")))
    except Exception:
        return str(v)


def doc_proposal(insp):
    st = _styles(); buf, doc = _new("Corrective-Work Proposal"); story = []
    _header(story, st, "Scope of corrective work self-performed by La Gala", "Corrective-Work Proposal", insp)
    items = insp.get("corrective") or []
    rows = [[Paragraph("Scope of work", st["th"]), Paragraph("Standard", st["thc"]), Paragraph("Qty", st["thc"]), Paragraph("Unit", st["th"]), Paragraph("Price", st["thc"])]]
    total = 0.0
    for it in items:
        try:
            total += float(str(it.get("price", "0")).replace(",", "").replace("$", "") or 0)
        except Exception:
            pass
        line = it.get("scope", "")
        if it.get("note"):
            line += '  <font color="%s">(%s)</font>' % (GREY, _esc(it["note"]))
        rows.append([Paragraph(line, st["td"]), Paragraph(_esc(it.get("std", "")), st["tdc"]),
                     Paragraph(_esc(it.get("qty", "")), st["tdc"]), Paragraph(_esc(it.get("unit", "")), st["td"]),
                     Paragraph("$" + _money(it.get("price", "")), st["tdr"])])
    if not items:
        rows.append([Paragraph("<i>Scope to be itemized from inspection findings.</i>", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"])])
    rows.append([Paragraph("<b>Total</b>", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("", st["td"]), Paragraph("<b>$" + _money(total) + "</b>", st["tdr"])])
    t = Table(rows, colWidths=[3.5 * inch, 0.9 * inch, 0.5 * inch, 0.8 * inch, 1.0 * inch], repeatRows=1)
    t.setStyle(_table_style()); _zebra(t, len(rows) - 1)
    t.setStyle(TableStyle([("LINEABOVE", (0, len(rows) - 1), (-1, len(rows) - 1), 1, NAVY), ("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), CREAM)]))
    story.append(t); story.append(Spacer(1, 8))
    story.append(Paragraph("La Gala Construction self-performs the corrective work above and <b>performs that work to the engineer's sealed specification</b>; the engineered inspection and any anchorage certification are provided and sealed by a licensed Florida professional engineer. One accountable team for the certificate and the fix.", st["key"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Terms", st["sect"]))
    story.append(Paragraph("Pricing is an estimate based on the inspection findings and is valid for 30 days. Final scope and price are confirmed after the engineered inspection. Engineered certification fees are billed by the professional engineer. Florida CGC059211; licensed, bonded, and insured.", st["body"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Accepted by: ______________________________     Title: ______________     Date: ____________", st["body"]))
    return _finish(buf, doc, story)


BUILDERS = {"checklist": doc_checklist, "report": doc_report, "cert": doc_cert, "proposal": doc_proposal}


def build(kind, insp):
    return BUILDERS[kind](insp)


# --------------------------------------------------------------- local test
SAMPLE = {
    "id": "demo", "status": "complete",
    "property": {"name": "Bayview Office Plaza", "address": "1200 S Federal Hwy, Deerfield Beach, FL 33441", "county": "Broward", "year_built": "1998", "stories": "4", "buildings": "2", "type": "Commercial office"},
    "client": {"name": "Maria Lopez", "company": "Bayview Property Mgmt", "email": "mlopez@example.com", "phone": "(954) 555-0142", "role": "Property Manager"},
    "inspector": {"name": "Daniel Bivins", "title": "Client Relations / GC", "license": "CGC059211", "date": "2026-06-10"},
    "pe": {"name": "", "firm": "", "license": ""},
    "summary": "Two 4-story commercial office buildings with shared rooftop mechanical access. Overall housekeeping and stairways were compliant; the primary exposures are uncertified roof anchors and a deteriorated north-side walkway. None of the deficiencies preclude occupancy but each is a citable Subpart D item that should be closed out.",
    "recommendations": "Prioritize the §1910.27 anchorage certification and the open roof-access edge as high-severity. Schedule the walkway concrete and coating repair before the rainy season. Re-inspect after corrective work and retain this documentation for the compliance file.",
    "corrective": [
        {"scope": "Load-test & certify 6 roof anchors to 5,000 lb/worker", "std": "§1910.27", "qty": "6", "unit": "anchor", "price": "1800", "note": "PE-sealed"},
        {"scope": "Concrete spall repair + slip-resistant urethane traffic coating, north walkway", "std": "§1910.22", "qty": "420", "unit": "sq ft", "price": "6300", "note": ""},
        {"scope": "Install compliant guardrail at open roof-access edge", "std": "§1910.28", "qty": "60", "unit": "lin ft", "price": "4200", "note": ""},
    ],
    "photos": [{"caption": "North walkway concrete spalling", "url": ""}, {"caption": "Uncertified roof anchor, NE corner", "url": ""}],
}


def _seed_sample():
    f = seed_findings()
    marks = {0: ("ok", "", ""), 1: ("def", "med", "Spalled concrete + slick coating, north walkway"),
             10: ("def", "high", "6 anchors with no current load-test certification"),
             16: ("def", "high", "Open roof-access edge, no guardrail"), 2: ("ok", "", ""), 3: ("ok", "", ""),
             15: ("na", "", "No rope descent system in use")}
    for i, fd in enumerate(f):
        if i in marks:
            fd["result"], fd["severity"], fd["note"] = marks[i]
        elif i % 3 == 0:
            fd["result"] = "ok"
    return f


if __name__ == "__main__":
    import fitz
    SAMPLE["findings"] = _seed_sample()
    for kind in ("checklist", "report", "cert", "proposal"):
        pdf = build(kind, SAMPLE)
        path = r"C:\Users\kjburnz\_insp_%s.pdf" % kind
        open(path, "wb").write(pdf)
        d = fitz.open(path)
        d[0].get_pixmap(dpi=110).save(r"C:\Users\kjburnz\_insp_%s.png" % kind)
        print("built %s — %d pages, %d KB" % (kind, len(d), len(pdf) // 1024))
