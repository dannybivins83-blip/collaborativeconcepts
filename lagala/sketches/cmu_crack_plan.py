#!/usr/bin/env python3
"""
LA GALA CONSTRUCTION — SK-1
CMU Wall — Crack at New Garage / Existing Tie-In (PLAN / top view)

Generates a vector PDF (US Letter, portrait) plus a 150-dpi PNG preview.
Geometry reproduced from the provided hand-sketch coordinate spec.
Origin bottom-left, drawing data space x:0-13, y:0-17, equal aspect.
"""

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrow, PathPatch
from matplotlib.path import Path
from matplotlib.lines import Line2D
import numpy as np

# Variant per markup A/B question:
#   A = drop BOTH wordy CMU-wall leaders, replace with "X" WIDE" dimensions
#   B = keep "EXISTING 12" CMU WALL" leader; only drop the garage leader
VARIANT = (sys.argv[1].upper() if len(sys.argv) > 1 else "A")

# ----------------------------------------------------------------------------
# Palette
NAVY  = "#0B2545"
RED   = "#C0392B"
GOLD  = "#B08D57"
AMBER = "#F4C430"
CMU_FACE = "#E9ECF1"
GRID  = "#D9E0EA"
PAPER = "#FFFFFF"

# Wall thicknesses in data units — keep the 3:2 (12":8") ratio EXACT.
T12 = 0.66          # 12" existing walls
T8  = T12 * 2 / 3   # 8" new garage wall  -> 0.44

# ----------------------------------------------------------------------------
fig = plt.figure(figsize=(8.5, 11.0), dpi=150)
fig.patch.set_facecolor(PAPER)

# Full-page axes for borders / title block (figure-fraction coords 0..1)
sheet = fig.add_axes([0, 0, 1, 1])
sheet.set_xlim(0, 1)
sheet.set_ylim(0, 1)
sheet.axis("off")

# Drawing axes (equal aspect) — leaves room for the title block below.
ax = fig.add_axes([0.045, 0.150, 0.910, 0.800])
ax.set_xlim(0, 13)
ax.set_ylim(0, 17)
ax.set_aspect("equal")
ax.axis("off")

# ----------------------------------------------------------------------------
# Faint graph-paper grid behind the drawing
for gx in np.arange(0, 13.001, 0.5):
    ax.plot([gx, gx], [0, 17], color=GRID, lw=0.3, zorder=0)
for gy in np.arange(0, 17.001, 0.5):
    ax.plot([0, 13], [gy, gy], color=GRID, lw=0.3, zorder=0)

# ----------------------------------------------------------------------------
# Helper: draw a CMU wall segment as a thick rectangle (two faces + hatch),
# centered on a centerline from p0 to p1, given total thickness t.
def cmu_segment(p0, p1, t, hatch="//"):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = np.hypot(dx, dy)
    # unit normal
    nx, ny = -dy / L, dx / L
    h = t / 2.0
    corners = [
        (x0 + nx * h, y0 + ny * h),
        (x1 + nx * h, y1 + ny * h),
        (x1 - nx * h, y1 - ny * h),
        (x0 - nx * h, y0 - ny * h),
    ]
    poly = Polygon(corners, closed=True, facecolor=CMU_FACE, edgecolor=NAVY,
                   lw=1.6, hatch=hatch, zorder=3)
    poly.set_linewidth(1.6)
    ax.add_patch(poly)

# Existing exterior wall (horizontal, 12")  — extended further right to read
# as a continuing wall (0.7,14.7) -> (12.6,14.7)
cmu_segment((0.7, 14.7), (12.6, 14.7), T12)
# break marks at the right end to signify the wall continues beyond the sheet
for bx in (12.15, 12.35):
    ax.plot([bx - 0.10, bx + 0.10], [14.7 - 0.40, 14.7 + 0.40],
            color=NAVY, lw=1.1, zorder=4)

# Existing ROOM wall — L-shape, 12"
#   stub (0.7,8.0)->(2.4,8.0) ; vertical (2.4,8.0)->(2.4,0.5)
cmu_segment((0.7, 8.0), (2.4 + T12 / 2, 8.0), T12)   # extend to close corner
cmu_segment((2.4, 8.0 + T12 / 2), (2.4, 0.5), T12)

# NEW GARAGE wall — L-shape, 8"
#   stub (7.0,8.4)->(9.7,8.4) ; vertical (7.0,8.4)->(7.0,0.5)
cmu_segment((7.0 - T8 / 2, 8.4), (9.7, 8.4), T8)
cmu_segment((7.0, 8.4 + T8 / 2), (7.0, 0.5), T8)

# ----------------------------------------------------------------------------
# Rebar band — cross-hatched parallelogram over the upper crack
rebar = [(4.85, 13.9), (5.55, 13.7), (6.05, 10.9), (5.35, 11.1)]
ax.add_patch(Polygon(rebar, closed=True, facecolor=AMBER, alpha=0.40,
                     edgecolor="none", zorder=4))
ax.add_patch(Polygon(rebar, closed=True, facecolor="none",
                     edgecolor=RED, lw=1.1, hatch="xxxx", zorder=5))

# ----------------------------------------------------------------------------
# Crack notch (zigzag) IN the exterior wall — red, bold.
# Enlarged + sharpened per markup: taller, sharper sawtooth peaks.
notch = [(4.55, 14.7), (4.85, 15.60), (5.1, 14.95), (5.4, 15.75),
         (5.65, 14.95), (5.95, 15.55), (6.1, 14.7)]
nx = [p[0] for p in notch]
ny = [p[1] for p in notch]
ax.plot(nx, ny, color=RED, lw=3.0, solid_capstyle="round",
        solid_joinstyle="round", zorder=8)

# Diagonal crack — two parallel jagged lines to garage top corner (7.0,8.4)
crackA = [(4.9, 14.6), (5.2, 13.0), (5.5, 11.4), (6.1, 10.0), (6.7, 9.0), (7.0, 8.4)]
crackB = [(5.9, 14.6), (6.0, 12.6), (6.2, 10.8), (6.6, 9.4), (7.0, 8.4)]
for crack in (crackA, crackB):
    cx = [p[0] for p in crack]
    cy = [p[1] for p in crack]
    ax.plot(cx, cy, color=RED, lw=2.6, solid_capstyle="round",
            solid_joinstyle="round", zorder=8)

# Emphasize the tie-in corner
ax.plot(7.0, 8.4, "o", color=RED, ms=6, zorder=9)

# ----------------------------------------------------------------------------
# Area labels — placed INSIDE their spaces per markup.
# ROOM sits in the narrow left bay, rotated to fit the column.
ax.text(1.10, 4.0, "ROOM (EXISTING)", ha="center", va="center", rotation=90,
        fontsize=15, color=NAVY, fontweight="bold")
# GARAGE sits large in the open garage interior (right of the 8" wall).
ax.text(10.0, 4.6, "GARAGE\n(NEW)", ha="center", va="center",
        fontsize=17, color=NAVY, fontweight="bold")

# Top centered title for the exterior wall
ax.text(6.1, 16.55, "OUTSIDE WALL", ha="center", va="center",
        fontsize=12.5, color=NAVY, fontweight="bold")
ax.text(6.1, 16.10, "(EXTERIOR – EXISTING 8\" CMU)", ha="center",
        va="center", fontsize=9, color=NAVY)

# ----------------------------------------------------------------------------
# Leader helper
def leader(text, xy, xytext, ha="left", va="center", fs=8.5):
    ax.annotate(text, xy=xy, xytext=xytext, ha=ha, va=va, fontsize=fs,
                color=NAVY, fontweight="bold", zorder=10,
                arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.9,
                                shrinkA=0, shrinkB=2))

# EXISTING 12" CMU WALL leader — removed per request.
# NEW 8" CMU GARAGE WALL leader — struck through in markup: removed.
# DIAGONAL CRACK
leader("DIAGONAL CRACK —\nAT NEW/EXISTING TIE-IN", xy=(6.6, 9.4),
       xytext=(9.6, 9.0), ha="left")
# EXIST. REBAR EXPOSED
leader("EXIST. REBAR EXPOSED\nAT CRACK (V.I.F.)", xy=(5.7, 12.4),
       xytext=(9.0, 13.3), ha="left")

# ----------------------------------------------------------------------------
# CLEAR-WIDTH dimensions — measured BETWEEN the hash-marked walls (the open
# areas), NOT across the wall rectangles.  Double-arrow runs face-to-face; the
# walls themselves act as the witness lines.
def clear_dim_h(xa, xb, y, text):
    ax.annotate("", xy=(xb, y), xytext=(xa, y),
                arrowprops=dict(arrowstyle="<|-|>", color=NAVY, lw=1.4,
                                mutation_scale=13, shrinkA=0, shrinkB=0),
                zorder=11)
    ax.text((xa + xb) / 2.0, y + 0.30, text, ha="center", va="bottom",
            fontsize=10.5, color=NAVY, fontweight="bold", zorder=12,
            bbox=dict(boxstyle="round,pad=0.26", fc="white", ec=NAVY, lw=1.1))

def clear_dim_v(x, ya, yb, text):
    ax.annotate("", xy=(x, yb), xytext=(x, ya),
                arrowprops=dict(arrowstyle="<|-|>", color=NAVY, lw=1.4,
                                mutation_scale=13, shrinkA=0, shrinkB=0),
                zorder=11)
    ax.text(x + 0.30, (ya + yb) / 2.0, text, ha="left", va="center",
            rotation=90, fontsize=10.5, color=NAVY, fontweight="bold",
            zorder=12,
            bbox=dict(boxstyle="round,pad=0.26", fc="white", ec=NAVY, lw=1.1))

# Clear opening between the existing (room) wall and the new (garage) wall —
# face-to-face across the area between them.
clear_dim_h(2.4 + T12 / 2, 7.0 - T8 / 2, 4.6, "8\" WIDE")
# Clear height of the left room bay, exterior-wall face down to room-stub face.
clear_dim_v(0.95, 8.0 + T12 / 2, 14.7 - T12 / 2, "8\" WIDE")
# Clear height of the right garage bay, exterior-wall face down to garage-stub
# face — the circled span, dimensioned 8" WIDE.
clear_dim_v(8.3, 8.4 + T8 / 2, 14.7 - T12 / 2, "8\" WIDE")

# ----------------------------------------------------------------------------
# North arrow — circled-N compass, pointing DOWN (north reoriented per markup)
from matplotlib.patches import Circle
ncx, ncy, nr = 12.05, 16.40, 0.46
ax.add_patch(Circle((ncx, ncy), nr, fill=False, edgecolor=NAVY, lw=1.6,
                    zorder=10))
# arrow through the circle pointing down
ax.annotate("", xy=(ncx, ncy - nr - 0.30), xytext=(ncx, ncy + nr - 0.02),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.0,
                            mutation_scale=18), zorder=11)
# "N" at the arrowhead (south-on-page = true north)
ax.text(ncx, ncy - nr - 0.52, "N", ha="center", va="center", fontsize=12,
        color=NAVY, fontweight="bold", zorder=11)

# NOTE box — removed per request.

# ----------------------------------------------------------------------------
# Borders (figure-fraction on the sheet axes)
def rect(x, y, w, h, ec, lw):
    sheet.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=ec, lw=lw))

rect(0.025, 0.022, 0.950, 0.962, NAVY, 2.0)   # outer border
rect(0.040, 0.036, 0.920, 0.934, GOLD, 1.0)   # gold inner accent

# Header tag — FOR ENGINEER REVIEW
sheet.text(0.5, 0.958, "FOR ENGINEER REVIEW", ha="center", va="center",
           fontsize=10.5, color=RED, fontweight="bold",
           bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=RED, lw=1.0))

# ----------------------------------------------------------------------------
# Title block (bottom)
tb_x, tb_y, tb_w, tb_h = 0.040, 0.036, 0.920, 0.092
sheet.add_patch(Rectangle((tb_x, tb_y), tb_w, tb_h, fill=False,
                          edgecolor=NAVY, lw=1.4))

# Navy company bar
bar_h = 0.030
sheet.add_patch(Rectangle((tb_x, tb_y + tb_h - bar_h), tb_w, bar_h,
                          facecolor=NAVY, edgecolor="none"))
sheet.text(tb_x + 0.015, tb_y + tb_h - bar_h / 2, "LA GALA CONSTRUCTION",
           ha="left", va="center", fontsize=13, color="white",
           fontweight="bold")
sheet.text(tb_x + tb_w - 0.015, tb_y + tb_h - bar_h / 2,
           "STRUCTURAL EXHIBIT", ha="right", va="center", fontsize=8.5,
           color=GOLD, fontweight="bold")
# Gold accent line under the bar
sheet.plot([tb_x, tb_x + tb_w], [tb_y + tb_h - bar_h]*2, color=GOLD, lw=1.4)

# Fields
fields_left = [
    ("PROJECT", "New Garage Addition to Existing Structure"),
    ("DRAWING TITLE", "CMU Wall — Crack at New Garage / Existing Tie-In (Plan)"),
]
fields_right = [
    ("SCALE", "N.T.S."),
    ("DATE", "06/25/2026"),
    ("LICENSE", "CGC059211"),
    ("SHEET", "SK-1"),
]
# vertical divider
divx = tb_x + 0.62
sheet.plot([divx, divx], [tb_y, tb_y + tb_h - bar_h], color=NAVY, lw=0.8)

fy = tb_y + tb_h - bar_h - 0.018
for label, val in fields_left:
    sheet.text(tb_x + 0.015, fy, label + ":", ha="left", va="center",
               fontsize=7.2, color=GOLD, fontweight="bold")
    sheet.text(tb_x + 0.150, fy, val, ha="left", va="center",
               fontsize=7.6, color=NAVY)
    fy -= 0.024

# right column: 2x2 grid
# label x, value x (fixed value columns so the longest label can't collide)
row_top = tb_y + tb_h - bar_h - 0.018
row_bot = tb_y + tb_h - bar_h - 0.042
rcells = [(divx + 0.012, divx + 0.085, row_top),   # SCALE
          (divx + 0.175, divx + 0.225, row_top),   # DATE
          (divx + 0.012, divx + 0.085, row_bot),   # LICENSE
          (divx + 0.175, divx + 0.225, row_bot)]   # SHEET
for (label, val), (lx, vx, cy) in zip(fields_right, rcells):
    sheet.text(lx, cy, label + ":", ha="left", va="center",
               fontsize=7.0, color=GOLD, fontweight="bold")
    sheet.text(vx, cy, val, ha="left", va="center",
               fontsize=7.6, color=NAVY)

# ----------------------------------------------------------------------------
out_pdf = "cmu_crack_plan_SK-1.pdf"
out_png = "cmu_crack_plan_SK-1.png"
fig.savefig(out_pdf)
fig.savefig(out_png, dpi=150)
print("wrote", out_pdf, out_png)
