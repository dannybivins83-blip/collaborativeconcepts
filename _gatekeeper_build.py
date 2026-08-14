#!/usr/bin/env python3
"""
Build the Gatekeeper Fence Co. website into /gatekeeper/.

Every page shares one head/nav/footer, so they live here rather than being
copy-pasted across a dozen HTML files. Styling is in gatekeeper/assets/gk.css
and behavior in gatekeeper/assets/gk.js -- neither is generated, edit those
directly.

    python3 _gatekeeper_build.py

Business facts in BIZ below are sourced from public records (FL Division of
Corporations, county contractor licensing, business directories). Anything you
cannot verify does not belong in here.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "gatekeeper")

# --------------------------------------------------------------------------
# Business facts
# --------------------------------------------------------------------------
BIZ = {
    "name": "Gatekeeper Fence Co.",
    "legal": "Gatekeeper Fence, Inc.",
    "owner": "John Tonkery",
    "phone_display": "(561) 503-6502",
    "phone_tel": "+15615036502",
    "street": "6179 Foster St",
    "city": "Jupiter",
    "state": "FL",
    "zip": "33458",
    "license": "U-21206",
    "since": "2007",
    "hours": "Mon–Fri, 8:00 AM – 5:00 PM",
    # Update this once a domain is registered; it only affects canonical/OG tags.
    "origin": "https://collaborativeconceptsfl.com/gatekeeper",
}

# Lead destination. Swap for the owner's inbox when he provides one.
LEAD_EMAIL = "dannybivins83@gmail.com"

AREAS = [
    "Jupiter", "Jupiter Farms", "Tequesta", "Juno Beach", "Palm Beach Gardens",
    "North Palm Beach", "Hobe Sound", "Palm City", "Stuart", "Port St. Lucie",
    "Riviera Beach", "West Palm Beach", "Royal Palm Beach", "Wellington",
    "Loxahatchee", "Singer Island",
]

# --------------------------------------------------------------------------
# Job photos
#
# Drop the image files in gatekeeper/assets/photos/ using the `file` names
# below and rebuild. Any photo whose file is missing is skipped, and if none
# are present the whole gallery section is omitted -- so the site never ships
# a broken image. See gatekeeper/assets/photos/README.md.
#
# Captions describe only what is visible in each frame. Do not add a city,
# a footage count, or a customer name unless the owner confirms it.
# --------------------------------------------------------------------------
PHOTOS = [
    {
        "file": "existing-fence-gate.jpg",
        "caption": "The existing fence and gate, before replacement.",
        "alt": "Weathered stained wood privacy fence and gate alongside a townhouse unit",
    },
    {
        "file": "clearing-fence-line.jpg",
        "caption": "Clearing the fence line before any posts go in.",
        "alt": "Gatekeeper Fence crew member clearing overgrowth along a fence line with a chainsaw",
    },
    {
        "file": "site-prep.jpg",
        "caption": "Old root ball dug out of the line so the new posts sit where they should.",
        "alt": "Root ball excavated from a fence line with pressure-treated lumber staged on the grass",
    },
    {
        "file": "setting-posts.jpg",
        "caption": "Setting posts and laying out rails.",
        "alt": "Two crew members setting a pressure-treated fence post beside a townhouse patio",
    },
    {
        "file": "new-rails-lakefront.jpg",
        "caption": "New pressure-treated posts and rails up on a lakefront run.",
        "alt": "Newly installed pressure-treated fence posts and rails running along a lakefront lawn",
    },
    {
        "file": "finished-gate-corner.jpg",
        "caption": "Finished gate and post, with the site cleaned up after.",
        "alt": "Completed pressure-treated wood fence gate at a house corner, with the yard cleared and raked",
    },
    {
        "file": "finished-corner-run.jpg",
        "caption": "The completed fence turning the corner of the house.",
        "alt": "Completed pressure-treated wood fence running along a stucco house corner into an open lawn",
    },
    {
        "file": "aluminum-estate-gate.jpg",
        "caption": "Powder-coated aluminum driveway gate and matching perimeter fence.",
        "alt": "Black powder-coated aluminum driveway gate and picket fence along a paver driveway",
    },
    {
        "file": "aluminum-pool-fence.jpg",
        "caption": "Aluminum pool fence and gate, set beside the paver deck.",
        "alt": "Black aluminum pool safety fence and self-closing gate beside a backyard pool deck",
    },
    {
        "file": "aluminum-gate-hardware.jpg",
        "caption": "Gate hardware on a powder-coated aluminum gate.",
        "alt": "Close-up of black powder-coated aluminum gate hinge and handle hardware on a stucco post",
    },
]


def available_photos():
    """Only the photos whose files actually exist on disk."""
    d = os.path.join(OUT, "assets", "photos")
    return [p for p in PHOTOS if os.path.exists(os.path.join(d, p["file"]))]


PHONE_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 '
             '19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 '
             '1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/></svg>')

ARROW_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')

SHIELD_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><path d="M12 2 4 5v6c0 5.3 3.4 8.6 8 10 4.6-1.4 8-4.7 8-10V5l-8-3Z"/></svg>')


# --------------------------------------------------------------------------
# Fence illustrations -- inline SVG, no image files to lose
# --------------------------------------------------------------------------
INK = "#3b4a54"
LIGHT = "#ffffff"
SHADE = "#d9d4cb"
BRASS = "#b8791f"
GROUND = "#c3bcb0"


def _frame(uid, body, sky=True):
    top = (f'<rect width="400" height="200" fill="#f0eeea"/>'
           f'<circle cx="336" cy="44" r="20" fill="#fff" opacity=".7"/>') if sky else ''
    return (f'<svg viewBox="0 0 400 200" role="img" xmlns="http://www.w3.org/2000/svg" '
            f'aria-label="{uid.replace("-", " ")} illustration">{top}{body}'
            f'<rect x="0" y="168" width="400" height="4" fill="{GROUND}"/></svg>')


def art_wood(uid="wood fence"):
    boards = ""
    x = 22
    while x < 380:
        boards += (f'<path d="M{x} 62 l7 -9 7 9 V168 H{x} Z" fill="{LIGHT}" stroke="{INK}" stroke-width="2"/>'
                   f'<path d="M{x + 6} 76 V166" stroke="{SHADE}" stroke-width="1.4"/>')
        x += 17
    rails = (f'<rect x="14" y="88" width="372" height="9" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="14" y="134" width="372" height="9" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>')
    posts = (f'<rect x="6" y="46" width="16" height="122" fill="{SHADE}" stroke="{INK}" stroke-width="2.4"/>'
             f'<rect x="378" y="46" width="16" height="122" fill="{SHADE}" stroke="{INK}" stroke-width="2.4"/>')
    return _frame(uid, boards + rails + posts)


def art_vinyl(uid="vinyl fence"):
    panels = ""
    for px in (28, 152, 276):
        panels += (f'<rect x="{px}" y="66" width="96" height="102" fill="{LIGHT}" stroke="{INK}" stroke-width="2"/>')
        for i in range(1, 6):
            panels += f'<path d="M{px + i * 16} 66 V168" stroke="{SHADE}" stroke-width="1.5"/>'
        panels += f'<rect x="{px}" y="66" width="96" height="12" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
    posts = ""
    for qx in (8, 132, 256, 380):
        posts += (f'<rect x="{qx}" y="58" width="20" height="110" fill="{LIGHT}" stroke="{INK}" stroke-width="2.4"/>'
                  f'<path d="M{qx - 4} 58 h28 l-6 -12 h-16 Z" fill="{BRASS}" stroke="{INK}" stroke-width="2"/>')
    return _frame(uid, panels + posts)


def art_aluminum(uid="aluminum fence"):
    pickets = ""
    x = 26
    while x < 378:
        pickets += (f'<rect x="{x}" y="58" width="6" height="110" fill="{INK}"/>'
                    f'<path d="M{x + 3} 58 l0 -12" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
        x += 22
    rails = (f'<rect x="14" y="74" width="372" height="8" fill="{INK}"/>'
             f'<rect x="14" y="142" width="372" height="8" fill="{INK}"/>')
    posts = ""
    for qx in (8, 190, 380):
        posts += (f'<rect x="{qx}" y="40" width="14" height="128" fill="{INK}"/>'
                  f'<rect x="{qx - 3}" y="32" width="20" height="10" rx="3" fill="{BRASS}"/>')
    return _frame(uid, rails + pickets + posts)


def art_chainlink(uid="chain link fence"):
    pid = "mesh-cl"
    defs = (f'<defs><pattern id="{pid}" width="26" height="26" patternUnits="userSpaceOnUse">'
            f'<path d="M0 0 L26 26 M26 0 L0 26" stroke="{INK}" stroke-width="2.2" fill="none"/>'
            f'</pattern></defs>')
    mesh = f'<rect x="16" y="66" width="368" height="102" fill="url(#{pid})" opacity=".85"/>'
    rails = (f'<rect x="8" y="58" width="384" height="9" rx="4.5" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="16" y="164" width="368" height="5" fill="{INK}"/>')
    posts = ""
    for qx in (8, 194, 384):
        posts += (f'<rect x="{qx}" y="44" width="12" height="124" rx="6" fill="{SHADE}" stroke="{INK}" stroke-width="2.2"/>'
                  f'<rect x="{qx - 2}" y="38" width="16" height="8" rx="4" fill="{BRASS}"/>')
    return _frame(uid, defs + mesh + rails + posts)


def art_pool(uid="pool safety fence"):
    pid = "mesh-pool"
    defs = (f'<defs><pattern id="{pid}" width="9" height="9" patternUnits="userSpaceOnUse">'
            f'<path d="M0 0 H9 M0 0 V9" stroke="{INK}" stroke-width="1" fill="none" opacity=".55"/>'
            f'</pattern></defs>')
    water = f'<rect x="0" y="172" width="400" height="28" fill="#bcd9dd"/>'
    mesh = (f'<rect x="24" y="52" width="352" height="116" fill="url(#{pid})"/>'
            f'<rect x="24" y="52" width="352" height="116" fill="none" stroke="{INK}" stroke-width="2"/>')
    poles = ""
    x = 24
    while x <= 376:
        poles += f'<rect x="{x - 4}" y="46" width="8" height="124" rx="4" fill="{INK}"/>'
        x += 44
    top = f'<rect x="24" y="52" width="352" height="6" fill="{INK}"/>'
    latch = (f'<rect x="176" y="46" width="8" height="124" rx="4" fill="{BRASS}"/>'
             f'<rect x="186" y="92" width="16" height="22" rx="4" fill="{BRASS}" stroke="{INK}" stroke-width="2"/>')
    return _frame(uid, defs + mesh + top + poles + latch + water)


def art_gate(uid="driveway gate"):
    posts = ""
    for qx in (10, 380):
        posts += (f'<rect x="{qx}" y="36" width="16" height="132" fill="{SHADE}" stroke="{INK}" stroke-width="2.4"/>'
                  f'<path d="M{qx - 4} 36 h24 l-6 -12 h-12 Z" fill="{BRASS}" stroke="{INK}" stroke-width="2"/>')

    def leaf(x0, w, flip=False):
        s = (f'<rect x="{x0}" y="58" width="{w}" height="110" fill="{LIGHT}" stroke="{INK}" stroke-width="2.4"/>')
        # diagonal brace
        if flip:
            s += f'<path d="M{x0 + w - 6} 162 L{x0 + 6} 64" stroke="{INK}" stroke-width="3"/>'
        else:
            s += f'<path d="M{x0 + 6} 162 L{x0 + w - 6} 64" stroke="{INK}" stroke-width="3"/>'
        # vertical infill
        i = x0 + 14
        while i < x0 + w - 8:
            s += f'<path d="M{i} 64 V162" stroke="{SHADE}" stroke-width="3"/>'
            i += 15
        s += (f'<rect x="{x0}" y="62" width="{w}" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
              f'<rect x="{x0}" y="152" width="{w}" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>')
        return s

    gates = leaf(30, 164) + leaf(206, 164, flip=True)
    hardware = (f'<rect x="186" y="96" width="28" height="20" rx="4" fill="{BRASS}" stroke="{INK}" stroke-width="2"/>'
                f'<circle cx="200" cy="106" r="4" fill="{INK}"/>'
                f'<rect x="22" y="80" width="14" height="10" rx="2" fill="{BRASS}"/>'
                f'<rect x="22" y="136" width="14" height="10" rx="2" fill="{BRASS}"/>'
                f'<rect x="364" y="80" width="14" height="10" rx="2" fill="{BRASS}"/>'
                f'<rect x="364" y="136" width="14" height="10" rx="2" fill="{BRASS}"/>')
    return _frame(uid, posts + gates + hardware)


def art_repair(uid="fence repair"):
    body = ""
    # sound section
    x = 20
    while x < 176:
        body += f'<path d="M{x} 68 l6 -8 6 8 V168 H{x} Z" fill="{LIGHT}" stroke="{INK}" stroke-width="2"/>'
        x += 16
    body += (f'<rect x="14" y="92" width="168" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="14" y="136" width="168" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>')
    # leaning / damaged section
    body += f'<g transform="rotate(7 200 168)">'
    x = 196
    while x < 356:
        fill = BRASS if x in (228, 244) else LIGHT
        body += f'<path d="M{x} 68 l6 -8 6 8 V168 H{x} Z" fill="{fill}" stroke="{INK}" stroke-width="2"/>'
        x += 16
    body += (f'<rect x="190" y="92" width="172" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/>'
             f'<rect x="190" y="136" width="172" height="8" fill="{SHADE}" stroke="{INK}" stroke-width="2"/></g>')
    posts = (f'<rect x="6" y="52" width="16" height="116" fill="{SHADE}" stroke="{INK}" stroke-width="2.4"/>'
             f'<rect x="180" y="52" width="16" height="116" fill="{SHADE}" stroke="{INK}" stroke-width="2.4"/>')
    return _frame(uid, body + posts)


def art_hero_fence():
    """Wide translucent fence silhouette used at the bottom of the dark hero."""
    pickets = ""
    x = 0
    while x < 1440:
        pickets += f'<path d="M{x} 34 l9 -12 9 12 V150 H{x} Z" fill="#ffffff"/>'
        x += 26
    rails = '<rect x="0" y="56" width="1440" height="12" fill="#ffffff"/><rect x="0" y="108" width="1440" height="12" fill="#ffffff"/>'
    return ('<svg class="hero-fence" viewBox="0 0 1440 150" preserveAspectRatio="none" aria-hidden="true" '
            'xmlns="http://www.w3.org/2000/svg">' + pickets + rails + '</svg>')


# --------------------------------------------------------------------------
# Services
# --------------------------------------------------------------------------
SERVICES = [
    {
        "slug": "wood-fence",
        "nav": "Wood Fence",
        "title": "Wood Fence Installation",
        "h1": "Wood fence installation in Jupiter &amp; northern Palm Beach County",
        "card": "Classic board-on-board, shadowbox and picket fencing in pressure-treated pine or cedar. Warm, private, and built with hardware that survives salt air.",
        "lede": "Nothing else gives you the same privacy and warmth for the money. Built right — with the correct post depth, hot-dip galvanized or stainless hardware, and proper board spacing — a wood fence holds up well in South Florida.",
        "art": art_wood,
        "body": """
<h3>Styles we build</h3>
<ul>
<li><strong>Board-on-board</strong> — overlapping vertical boards with no gaps. The most private option, and it stays private as the wood seasons and boards shrink.</li>
<li><strong>Shadowbox</strong> — alternating boards on either side of the rails. Looks finished from both sides and lets wind pass through, which matters on an exposed lot.</li>
<li><strong>Stockade / privacy</strong> — boards butted edge to edge for a solid wall of screening.</li>
<li><strong>Picket &amp; spaced picket</strong> — 3&nbsp;ft to 4&nbsp;ft front-yard fencing that defines the property without closing it in.</li>
<li><strong>Dog-ear, flat-top, or scalloped</strong> tops, and horizontal-slat designs for a more modern look.</li>
</ul>

<h3>Materials that last down here</h3>
<p>The wood matters less than what holds it together. We use pressure-treated southern yellow pine as the standard, with cedar available when you want the color and the tighter grain. Posts are set in concrete at a depth sized to the fence height and the soil — the sugar sand up in Jupiter Farms behaves very differently from coastal fill, and a post that's fine in one is loose in the other.</p>
<p>Fasteners are where cheap fences fail first. Salt air eats electro-galvanized screws and nails in a couple of seasons, and you get rust bleed down every board before the wood is anywhere near done. We use hot-dip galvanized or stainless fasteners and galvanized post hardware.</p>

<h3>What to expect on cost</h3>
<p>Price moves with height, style, linear footage, gate count, and access. A straight run across an open back yard is a very different job from a fence that has to be hand-carried through a side yard, around a pool deck, and past mature ficus roots. We measure on site and quote the whole job — posts, concrete, hardware, gates, permit, and haul-away of the old fence if there is one — so there is nothing to add later.</p>

<h3>Wood vs. vinyl, honestly</h3>
<p>If you want the lowest maintenance, buy vinyl. If you want the look, the ability to stain it any color you like, and a lower price per foot up front, buy wood. Wood needs to be sealed or stained every few years to hold its color; left alone, it weathers to gray, which plenty of people prefer. Both are legitimate choices — we install both and we'll tell you which one fits your yard.</p>
""",
        "faqs": [
            ("How tall can my wood fence be?",
             "Six feet is typical for back and side yards, with front-yard fencing usually limited to four feet, but every municipality here sets its own limits — and if you're in an HOA, its rules stack on top of the town's. We check the height, setback, and finished-side rules for your specific address before we quote."),
            ("Which side gets the 'good' side?",
             "Most codes and HOAs require the finished side to face out toward the street or your neighbor. Shadowbox sidesteps the argument entirely — it looks the same from both sides."),
            ("How long until I can stain it?",
             "Give pressure-treated wood a few months to dry out before sealing or staining, or the finish won't penetrate. Cedar can be finished much sooner."),
        ],
    },
    {
        "slug": "vinyl-fence",
        "nav": "Vinyl / PVC Fence",
        "title": "Vinyl &amp; PVC Fence Installation",
        "h1": "Vinyl and PVC fencing built for the Florida coast",
        "card": "Won't rot, rust, warp, or need painting. Our PVC fencing carries a limited lifetime warranty on the material — the low-maintenance answer for coastal lots.",
        "lede": "PVC is the closest thing to a set-and-forget fence in this climate. It doesn't rot, it doesn't rust, termites don't care about it, and it never needs paint. Hose it off and it looks new.",
        "art": art_vinyl,
        "body": """
<h3>Why PVC does well here</h3>
<p>Salt air, ninety-degree humidity, and afternoon storms are hard on everything. Vinyl is immune to most of it: no rot, no rust bleed, no wood-boring insects, no repainting. The color is through the material rather than sprayed on top, so a scuff doesn't show as a bare patch, and quality extrusions carry UV inhibitors so they don't chalk and yellow.</p>
<p>We stand behind ours with a <strong>limited lifetime warranty on the PVC material</strong> and a one-year guarantee on our workmanship.</p>

<h3>Styles</h3>
<ul>
<li><strong>Solid privacy</strong> — tongue-and-groove panels, typically 6&nbsp;ft, with a choice of flat, arched, or lattice-topped sections.</li>
<li><strong>Semi-privacy</strong> — spaced pickets that block sightlines without walling off the breeze.</li>
<li><strong>Picket</strong> — 3&nbsp;ft to 4&nbsp;ft front-yard fencing with straight or scalloped tops.</li>
<li><strong>Ranch rail</strong> — two-, three-, and four-rail for acreage and horse property out west of town.</li>
<li>White and almond are the everyday colors; tan, khaki, gray, and woodgrain finishes are available.</li>
</ul>

<h3>Installation is what separates good vinyl from bad vinyl</h3>
<p>Vinyl panels are only as good as the posts holding them. A solid 6&nbsp;ft privacy panel is a sail — it catches every bit of wind that hits it, and all of that load ends up in the post and the footing. That means correct post depth, properly sized concrete footings, and appropriate post spacing for the panel and the exposure. We size footings for the conditions at your address rather than running one number everywhere, and on exposed lots we use aluminum-reinforced posts and gate posts where the load calls for it.</p>

<h3>Gates</h3>
<p>Vinyl gates need internal reinforcement to stay square — an unreinforced gate leaf will sag and stop latching within a season or two. Ours get aluminum or steel frames inside the vinyl, self-closing hinges where the code requires them, and hardware rated for coastal exposure.</p>
""",
        "faqs": [
            ("Does vinyl really carry a lifetime warranty?",
             "Our PVC fencing carries a limited lifetime warranty on the material, plus a one-year guarantee on our workmanship. We'll walk you through exactly what the material warranty covers before you sign anything."),
            ("Will it turn yellow?",
             "Quality vinyl fence is extruded with UV inhibitors and titanium dioxide specifically to resist yellowing and chalking. Thin, bargain-grade vinyl is where that reputation comes from. We don't buy that grade."),
            ("How does vinyl handle a storm?",
             "Better than people expect, when it's installed right. The failure point is almost never the panel — it's a post that wasn't set deep enough or a footing that was undersized. Vinyl panels are also designed to pop out of the rails under extreme load rather than snapping the posts off, which usually means you're re-seating panels instead of rebuilding the fence."),
        ],
    },
    {
        "slug": "aluminum-fence",
        "nav": "Aluminum Fence",
        "title": "Aluminum Fence Installation",
        "h1": "Powder-coated aluminum fencing and railings",
        "card": "The best choice for salt air and the standard for pool enclosures. Rust-proof, see-through, and available in code-compliant pool-safe configurations.",
        "lede": "Aluminum doesn't rust — not near the Intracoastal, not on a barrier-island lot, not ever. That's why it's the default for pool enclosures and waterfront properties, and why the powder-coat finish still looks right a decade in.",
        "art": art_aluminum,
        "body": """
<h3>Where aluminum wins</h3>
<ul>
<li><strong>Anywhere near salt water.</strong> Steel and iron corrode within sight of the ocean no matter how they're coated. Aluminum simply doesn't.</li>
<li><strong>Pool enclosures.</strong> Aluminum picket is the most common way to meet Florida's residential pool barrier requirements while keeping an open view of the pool.</li>
<li><strong>Preserving a view.</strong> You get a real boundary without giving up the golf course, the water, or the preserve behind you.</li>
<li><strong>Wind.</strong> An open picket fence has very little sail area, so it sheds wind instead of fighting it.</li>
<li><strong>HOA approval.</strong> Black or bronze aluminum picket is the style most communities in this area specify by name.</li>
</ul>

<h3>Grades and options</h3>
<p>Residential, commercial, and industrial grades differ in wall thickness and picket size — a 4&nbsp;ft residential pool fence and a 6&nbsp;ft commercial perimeter fence are not the same product. Two-rail and three-rail configurations, flat-top, spear-top, and puppy-picket (extra pickets at the bottom to keep small dogs in) are all available. Standard powder-coat colors are black and bronze; white and other colors can be ordered.</p>

<h3>Pool-code configurations</h3>
<p>If the fence forms part of your pool barrier, the picket spacing, overall height, rail placement, and the gate hardware all have to meet Florida's residential pool safety requirements. Rail spacing matters more than people realize — rails placed where a child could use them as a ladder can fail inspection even when the height is right. We build pool enclosures to the applicable code and coordinate the inspection. <a href="/gatekeeper/pool-fence">More on pool safety fencing →</a></p>

<h3>Racking for slope</h3>
<p>Quality aluminum panels rack — the rails pivot at the posts so a panel follows a grade change instead of leaving a wedge-shaped gap underneath. On steeper transitions we step the panels instead. Either way, no gaps at the bottom, which matters both for pets and for pool-barrier compliance.</p>
""",
        "faqs": [
            ("Aluminum or steel?",
             "In coastal Palm Beach and Martin County, aluminum, every time. Steel and wrought iron will rust here regardless of the coating — it's just a question of how many years you get first."),
            ("Will it hold up to wind?",
             "An open picket fence has very little surface for wind to push against, which is a real advantage in this part of Florida. The panels aren't the concern — post setting and footing size are, and that's what we size for your site."),
            ("Can aluminum keep my dog in?",
             "Yes. Standard picket spacing stops most dogs; for small breeds and puppies we add a puppy-picket bottom section that closes the spacing near the ground."),
        ],
    },
    {
        "slug": "chain-link-fence",
        "nav": "Chain Link Fence",
        "title": "Chain Link Fence Installation",
        "h1": "Chain link fencing for homes, businesses and job sites",
        "card": "The most economical way to enclose a lot. Galvanized or black vinyl-coated, in residential and commercial gauges, with gates to match.",
        "lede": "Chain link is the most fence you can get per dollar. Galvanized for utility, black vinyl-coated when you want it to disappear into the landscaping — and it's still the fastest way to secure a large property.",
        "art": art_chainlink,
        "body": """
<h3>What we install</h3>
<ul>
<li><strong>Galvanized chain link</strong> — the standard silver mesh, in residential through commercial gauges.</li>
<li><strong>Black or green vinyl-coated</strong> — visually recedes into hedges and tree lines far better than galvanized, and the coating adds a layer of corrosion protection.</li>
<li><strong>Heights from 4&nbsp;ft to 12&nbsp;ft</strong>, with top rail, bottom tension wire, and the appropriate terminal, corner, and line post schedule.</li>
<li><strong>Privacy slats</strong> woven into the mesh, or hedge planted against it, when you want screening at a chain-link budget.</li>
<li><strong>Commercial and industrial</strong> perimeters, storage yards, ball fields, dumpster enclosures, and construction fencing.</li>
</ul>

<h3>The details that matter</h3>
<p>Chain link looks simple, and that's exactly why it gets installed badly. The mesh has to be stretched properly — a fabric that's merely hung sags into waves within a year. Terminal posts at every corner, gate, and end have to be heavier than the line posts and set deeper, because they're carrying all the tension. Tension bands, brace bands, and tie wires need to be spaced correctly, and near the water everything should be galvanized or coated. We do all of that as a matter of course.</p>

<h3>Residential vs. commercial grade</h3>
<p>Residential chain link uses lighter-gauge fabric and thinner posts, which is fine for a back-yard dog run. A storage yard, a job site, or anything carrying a heavy gate needs commercial-grade pipe and fabric. We'll tell you which one your job actually needs — there's no reason to sell you commercial pipe for a dog run, and no reason to put residential pipe around a business.</p>

<h3>Gates</h3>
<p>Single walk gates, double drive gates, and rolling or cantilever slide gates where a swing gate won't work. Large drive gates need properly sized posts and hardware or they'll sag and drag; that's the single most common chain-link repair we get called out for.</p>
""",
        "faqs": [
            ("Is chain link allowed in my neighborhood?",
             "Some municipalities and most HOAs restrict chain link in front yards or on street-facing sides, and some prohibit galvanized while allowing black vinyl-coated. We check the rules for your address before quoting."),
            ("Will chain link rust?",
             "Galvanized fabric is zinc-coated and holds up reasonably well, but near the ocean or the Intracoastal, vinyl-coated is worth the difference. Where it usually starts is at cut ends and damaged coating, so clean work matters."),
            ("Can I get privacy from chain link?",
             "Privacy slats woven through the mesh get you most of the way there at a fraction of the cost of a privacy fence. Windscreen fabric is the other option, common on tennis courts and job sites."),
        ],
    },
    {
        "slug": "pool-fence",
        "nav": "Pool Safety Fence",
        "title": "Pool Safety Fence Installation",
        "h1": "Pool safety fencing that passes inspection",
        "card": "Removable mesh and permanent aluminum pool barriers built to Florida's residential pool safety requirements — correct height, no climbable gaps, self-closing and self-latching gates.",
        "lede": "Florida law requires a barrier around a residential pool, and the details are specific: minimum height, no gaps a small child can pass through, nothing climbable, and a gate that closes and latches by itself every single time.",
        "art": art_pool,
        "body": """
<h3>What the code actually requires</h3>
<p>Under Florida's Residential Swimming Pool Safety Act and the building code that implements it, a residential pool barrier generally has to:</p>
<ul>
<li>Be at least <strong>four feet high</strong> on the outside face, measured from the ground.</li>
<li>Have <strong>no gaps, openings, or protrusions</strong> that would let a small child crawl through, squeeze under, or climb over.</li>
<li>Have <strong>no handholds or footholds</strong> that make it climbable — this is the requirement that quietly fails a lot of otherwise correct-height fences.</li>
<li>Be positioned so that anything nearby can't be used to climb it.</li>
<li>Have gates that <strong>open outward, away from the pool</strong>, and are <strong>self-closing and self-latching</strong>, with the release mechanism placed high enough to be out of a small child's reach.</li>
</ul>
<p>Codes change and local jurisdictions add their own amendments. We build to the requirements in force for your address and county at the time of installation, and we're there for the inspection.</p>

<h3>Removable mesh pool fence</h3>
<p>Fine-mesh panels on aluminum poles that drop into sleeves set flush in the deck. Strong enough to meet the barrier requirement, transparent enough that you can watch the pool through it, and removable section by section when you're entertaining. The self-closing, self-latching gate is the part that has to be right — a mesh fence with a gate that doesn't latch is not a barrier.</p>

<h3>Permanent aluminum pool enclosures</h3>
<p>When you want the barrier to be a permanent part of the yard, powder-coated aluminum picket is the standard. It won't rust in the pool-chemical and salt environment, it doesn't block the view, and the picket spacing and rail placement can be configured to meet the barrier requirements. <a href="/gatekeeper/aluminum-fence">More on aluminum fencing →</a></p>

<h3>Not just for new pools</h3>
<p>Two situations bring most of these calls: a new pool that needs a barrier before it can pass final inspection, and a home changing hands where the inspector or the insurer flagged a non-compliant barrier. Both are on a clock. Tell us the deadline you're working against when you call and we'll tell you honestly whether we can hit it.</p>
""",
        "faqs": [
            ("Does a screen enclosure count as the pool barrier?",
             "It can, if it meets the barrier requirements — including gates that are self-closing and self-latching. Plenty of screen enclosures have doors that simply push open, which does not comply. Have it evaluated rather than assumed."),
            ("How high does a pool fence have to be?",
             "Four feet is the minimum for a residential pool barrier under the Florida requirements. Height alone isn't sufficient — spacing, climbability, and gate hardware all have to comply too."),
            ("Can I take a mesh pool fence down for a party?",
             "Yes — that's the main appeal. Sections lift out of the deck sleeves and go back in without tools. Just remember the barrier is a legal requirement, so it goes back up when the party's over."),
            ("Do I need a permit for a pool fence?",
             "Almost always, and it's typically tied to the pool's inspection. We pull the permit and handle the inspection as part of the job."),
        ],
    },
    {
        "slug": "gates",
        "nav": "Gates",
        "title": "Gate Installation &amp; Repair",
        "h1": "Driveway gates, walk gates, and gate repair",
        "card": "New gates built square and hung to stay that way, plus repairs for sagging, dragging, and won't-latch gates on fences we didn't install.",
        "lede": "Gates are the part of a fence that moves, so they're the part that fails. A gate that was built square, hung on the right hardware, and set on posts sized for the load will open the same way in year ten as it did on day one.",
        "art": art_gate,
        "body": """
<h3>What we build</h3>
<ul>
<li><strong>Walk gates</strong> in wood, vinyl, aluminum, and chain link, matched to the fence they sit in.</li>
<li><strong>Double drive gates</strong> for driveways, side yards, and equipment access.</li>
<li><strong>Rolling and cantilever slide gates</strong> where there isn't room for a gate to swing.</li>
<li><strong>Pool gates</strong> with self-closing hinges and self-latching hardware positioned to meet the code.</li>
<li><strong>Gates sized for an operator</strong>, if you're adding or already have an automatic opener.</li>
</ul>

<h3>Why gates sag — and how we prevent it</h3>
<p>A gate leaf is a lever. All of its weight hangs off the hinge side, and the longer and heavier the leaf, the more force it puts on that post every time it swings. Three things prevent sag:</p>
<ul>
<li><strong>An oversized hinge post, set deeper, in a bigger footing.</strong> A gate post is not a line post. Using the same post for both is the number one cause of gates that drag by the second season.</li>
<li><strong>A rigid frame.</strong> Diagonal bracing on wood gates, welded or bolted internal frames inside vinyl and aluminum leaves. A rectangle without a diagonal is a hinge, not a frame.</li>
<li><strong>Hardware rated for the actual weight</strong>, in a finish that survives coastal air. Undersized hinges will pull out and stainless or hot-dip galvanized is worth what it costs here.</li>
</ul>

<h3>Gate repair</h3>
<p>We repair gates on fences we didn't build. Common calls: a gate that dragged a groove into the driveway, a hinge post leaning toward the opening, a latch that stopped catching, a pool gate that no longer self-closes, or a drive gate that racked out of square. Most are fixable in one visit — re-hanging, re-squaring, resetting the post, or replacing hardware. When a post is rotted or the footing has failed, we'll tell you that up front instead of hanging new hardware on something that won't hold it. <a href="/gatekeeper/fence-repair">More on fence repair →</a></p>

<h3>Automatic gates</h3>
<p>If you're planning an operator, the gate has to be built for it from the start — heavier frame, heavier posts, and clearances the operator needs. Tell us at the estimate and we'll build it to accept one, whether that's now or later.</p>
""",
        "faqs": [
            ("My gate drags on the ground. Can it be fixed?",
             "Usually, yes. It's most often the hinge post leaning or the leaf racking out of square, and both can be corrected. If the post itself is rotted or the footing has broken up, the post needs replacing — we'll tell you which one you're looking at before we start."),
            ("How wide can a driveway gate be?",
             "Wide, if the posts and hardware are sized for it. Past a certain width a double gate or a slide gate is the better answer than one enormous leaf, both for the hardware and for how it feels to open."),
            ("Do pool gates have different requirements?",
             "Yes. A gate that's part of a pool barrier has to swing outward away from the pool, close by itself, latch by itself, and have the release positioned out of a small child's reach. Standard gate hardware doesn't meet that."),
        ],
    },
    {
        "slug": "fence-repair",
        "nav": "Fence Repair",
        "title": "Fence Repair &amp; Straightening",
        "h1": "Fence repair, straightening, and picket replacement",
        "card": "Leaning posts, storm damage, broken pickets, gates that won't latch. We repair fences we didn't install — no need to replace the whole run.",
        "lede": "Most of the fences we're called out to don't need replacing. A leaning section, a handful of broken pickets, or a gate that stopped latching is a repair, and we'd rather do the repair than sell you a fence you don't need.",
        "art": art_repair,
        "body": """
<h3>What we repair</h3>
<ul>
<li><strong>Leaning and sagging sections</strong> — straightened and re-secured, with posts reset or replaced where the footing has failed.</li>
<li><strong>Broken and missing pickets or boards</strong> — replaced and matched as closely as the original material allows.</li>
<li><strong>Storm damage</strong> — sections blown over, panels pulled out of rails, posts snapped at grade.</li>
<li><strong>Rotted posts</strong> — the most common failure on older wood fences, and the one that takes whole sections with it if it's left alone.</li>
<li><strong>Gate problems</strong> — dragging, sagging, racked out of square, won't latch, self-closer no longer closing.</li>
<li><strong>Chain link</strong> — sagging or torn fabric re-stretched or replaced, bent top rail, leaning terminal posts.</li>
<li><strong>Vinyl</strong> — panels re-seated, cracked rails and pickets swapped out.</li>
</ul>

<h3>Straightening a leaning fence</h3>
<p>A fence leans for a reason, and the reason is almost always below the ground. Sometimes the post was never set deep enough for our sandy soil. Sometimes the footing was too small for the height. Sometimes the post rotted at grade, where wet meets dry, or a root system pushed it over. Pushing it back upright without fixing the footing gets you a fence that leans again by next summer, so we look at what's actually failed and correct that.</p>

<h3>When repair stops making sense</h3>
<p>We'll tell you when you're better off replacing. If most of the posts are rotted at grade, if the fence is failing in several places at once, or if the repair cost is closing in on the cost of a new run, replacement is the honest answer and we'll say so. Being straight about it is the whole reason people call us back.</p>

<h3>After a storm</h3>
<p>Hurricane season keeps us busy, and calls stack up fast after a named storm. If your fence is down and it's holding a dog in, holding a pool barrier together, or leaning on something it shouldn't be, say that when you call — those go to the front of the line.</p>
""",
        "faqs": [
            ("Do you repair fences you didn't install?",
             "Yes — that's most of our repair work. Wood, vinyl, aluminum, and chain link."),
            ("Can you match my existing fence?",
             "Usually. Wood we can match closely, though new boards will be lighter until they weather in. Vinyl and aluminum depend on the profile and color the original installer used; some are still in production, some aren't. We'll tell you honestly what the match will look like before we order anything."),
            ("How fast can you get out here?",
             "Depends on the week and on what's wrong. A leaning fence can usually wait; a pool barrier that isn't a barrier anymore or a fence that's letting a dog out cannot. Tell us which one you've got when you call."),
        ],
    },
]

SERVICE_BY_SLUG = {s["slug"]: s for s in SERVICES}


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------
NAV_ITEMS = [
    ("/gatekeeper/services", "Services"),
    ("/gatekeeper/pool-fence", "Pool Fence"),
    ("/gatekeeper/fence-repair", "Repairs"),
    ("/gatekeeper/service-area", "Service Area"),
    ("/gatekeeper/about", "About"),
    ("/gatekeeper/contact", "Contact"),
]


def head(title, desc, slug, extra=""):
    canonical = BIZ["origin"] + ("" if slug == "index" else "/" + slug)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta name="theme-color" content="#131a1f">
<link rel="icon" type="image/svg+xml" href="/gatekeeper/assets/logo.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=DM+Sans:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/gatekeeper/assets/gk.css">
<script>
/* CONFIG — where website leads are delivered. Change LEAD_EMAIL and rebuild. */
window.GK_CONFIG = {{
  FORM_ENDPOINT: "https://formsubmit.co/ajax/{LEAD_EMAIL}",
  PHONE: "{BIZ['phone_display']}"
}};
</script>
{extra}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


def header(active=""):
    links = ""
    for href, label in NAV_ITEMS:
        cur = ' aria-current="page"' if href.rsplit("/", 1)[-1] == active else ""
        links += f'<a href="{href}"{cur}>{label}</a>'
    return f"""<div class="topbar"><div class="wrap">
  <span class="tb-hours">{BIZ['hours']} &nbsp;·&nbsp; Serving Jupiter &amp; northern Palm Beach County since {BIZ['since']}</span>
  <span>Free estimates — <a href="tel:{BIZ['phone_tel']}">{BIZ['phone_display']}</a></span>
</div></div>
<header class="hdr"><div class="wrap">
  <a class="brand" href="/gatekeeper">
    <img class="brand-mark" src="/gatekeeper/assets/logo.svg" alt="" width="40" height="40">
    <span class="brand-txt"><span class="brand-name">Gatekeeper</span><span class="brand-sub">Fence Co.</span></span>
  </a>
  <nav class="nav" id="nav" data-open="false" aria-label="Main">
    <button class="navclose" type="button" aria-label="Close menu">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>
    {links}
    <a class="btn btn-brass" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}{BIZ['phone_display']}</a>
  </nav>
  <div class="hdr-cta">
    <a class="btn btn-brass btn-hide-sm" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}{BIZ['phone_display']}</a>
    <button class="navtoggle" aria-label="Open menu" aria-expanded="false" aria-controls="nav">
      <svg viewBox="0 0 24 24" fill="none" stroke="#131a1f" stroke-width="2.4" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
    </button>
  </div>
</div></header>
<div class="navscrim" data-open="false" hidden></div>
<main id="main">
"""


def quote_form(heading="Request a free estimate", sub="Tell us what you need. We'll call you back to schedule an on-site measure and quote.", compact=False):
    services_opts = "".join(
        f'<option>{re.sub("<.*?>", "", s["nav"])}</option>' for s in SERVICES
    )
    return f"""<form data-gkform novalidate>
  <h2>{heading}</h2>
  <p class="qsub">{sub}</p>
  <input class="hp" type="text" name="_honey" tabindex="-1" autocomplete="off" aria-hidden="true">
  <div class="field-row">
    <div class="field"><label for="f-name">Name</label>
      <input id="f-name" name="name" type="text" autocomplete="name" required></div>
    <div class="field"><label for="f-phone">Phone</label>
      <input id="f-phone" name="phone" type="tel" autocomplete="tel" required></div>
  </div>
  <div class="field"><label for="f-email">Email</label>
    <input id="f-email" name="email" type="email" autocomplete="email"></div>
  <div class="field-row">
    <div class="field"><label for="f-city">Property city</label>
      <input id="f-city" name="city" type="text" autocomplete="address-level2" placeholder="Jupiter"></div>
    <div class="field"><label for="f-service">What do you need?</label>
      <select id="f-service" name="service">
        <option value="">Select one…</option>
        {services_opts}
        <option>Not sure — need advice</option>
      </select></div>
  </div>
  <div class="field"><label for="f-notes">Details</label>
    <textarea id="f-notes" name="notes" placeholder="Roughly how many feet, fence height, new install or repair, any HOA or permit deadline you're working against."></textarea></div>
  <button class="btn btn-brass btn-wide" type="submit">Request my free estimate</button>
  <div class="formmsg" role="status" aria-live="polite"></div>
  <p class="form-note">Or just call — <a href="tel:{BIZ['phone_tel']}">{BIZ['phone_display']}</a>. {BIZ['hours']}.</p>
</form>"""


def gallery(heading="Recent work", lede=None, sand=True):
    """Job-photo gallery. Returns '' when no photo files are present."""
    photos = available_photos()
    if not photos:
        return ""
    if lede is None:
        lede = ("Real jobs, photographed as they were built — not stock images. "
                "The unglamorous parts are the parts that decide whether a fence lasts.")
    # first photo runs wide, the rest tile beneath it
    lead, rest = photos[0], photos[1:]

    def fig(p, wide=False):
        return (f'<figure class="shot{" shot-wide" if wide else ""}">'
                f'<img src="/gatekeeper/assets/photos/{p["file"]}" alt="{p["alt"]}" '
                f'loading="lazy" decoding="async">'
                f'<figcaption>{p["caption"]}</figcaption></figure>')

    tiles = "".join(fig(p) for p in rest)
    return f"""<section class="{'sec-sand' if sand else ''}">
  <div class="wrap">
    <div class="sec-head center">
      <span class="kicker">Our work</span>
      <h2 class="big">{heading}</h2>
      <p class="lede">{lede}</p>
    </div>
    <div class="shots">
      {fig(lead, wide=True)}
      {tiles}
    </div>
  </div>
</section>"""


def cta_band():
    return f"""<section class="ctaband">
  <div class="wrap">
    <h2>Ready for a straight answer and a real number?</h2>
    <p>We come out, measure, look at the access and the soil, and give you one price for the whole job. No charge, no pressure.</p>
    <div class="hero-btns">
      <a class="btn btn-brass" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
      <a class="btn btn-light" href="/gatekeeper/contact">Request an estimate {ARROW_SVG}</a>
    </div>
  </div>
</section>"""


def footer():
    svc_links = "".join(
        f'<li><a href="/gatekeeper/{s["slug"]}">{s["nav"]}</a></li>' for s in SERVICES
    )
    area_links = "".join(f"<li>{a}</li>" for a in AREAS[:8])
    return f"""</main>
{cta_band()}
<footer class="ftr"><div class="wrap">
  <div class="ftr-top">
    <div class="ftr-brand">
      <a class="brand" href="/gatekeeper">
        <img class="brand-mark" src="/gatekeeper/assets/logo.svg" alt="" width="40" height="40">
        <span class="brand-txt"><span class="brand-name">Gatekeeper</span><span class="brand-sub">Fence Co.</span></span>
      </a>
      <p>Family-owned fence contractor in Jupiter, Florida. Installing and repairing fences and gates across northern Palm Beach County and southern Martin County since {BIZ['since']}.</p>
      <span class="ftr-lic">Licensed &amp; insured · Lic. #{BIZ['license']}</span>
    </div>
    <div>
      <h4>Services</h4>
      <ul>{svc_links}</ul>
    </div>
    <div>
      <h4>Service area</h4>
      <ul>{area_links}<li><a href="/gatekeeper/service-area">See all →</a></li></ul>
    </div>
    <div>
      <h4>Contact</h4>
      <ul>
        <li><a href="tel:{BIZ['phone_tel']}">{BIZ['phone_display']}</a></li>
        <li>{BIZ['street']}<br>{BIZ['city']}, {BIZ['state']} {BIZ['zip']}</li>
        <li>{BIZ['hours']}</li>
        <li><a href="/gatekeeper/contact">Request an estimate</a></li>
      </ul>
    </div>
  </div>
  <div class="ftr-bot">
    <span>&copy; <span data-year>2026</span> {BIZ['legal']} · d/b/a {BIZ['name']}. All rights reserved.</span>
    <span>Florida contractor license #{BIZ['license']} · Bonded &amp; insured</span>
  </div>
</div></footer>
<div class="callbar">
  <a class="btn btn-brass" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call now</a>
  <a class="btn btn-out" href="/gatekeeper/contact">Free estimate</a>
</div>
<script src="/gatekeeper/assets/gk.js"></script>
</body>
</html>
"""


def local_business_schema():
    """LocalBusiness JSON-LD. Only asserts facts we can source."""
    svc = ", ".join(re.sub("<.*?>", "", s["nav"]) for s in SERVICES)
    areas = ",".join(f'{{"@type":"City","name":"{a}"}}' for a in AREAS)
    return f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FenceContractor",
  "name": "{BIZ['name']}",
  "legalName": "{BIZ['legal']}",
  "url": "{BIZ['origin']}",
  "telephone": "{BIZ['phone_tel']}",
  "foundingDate": "{BIZ['since']}",
  "address": {{
    "@type": "PostalAddress",
    "streetAddress": "{BIZ['street']}",
    "addressLocality": "{BIZ['city']}",
    "addressRegion": "{BIZ['state']}",
    "postalCode": "{BIZ['zip']}",
    "addressCountry": "US"
  }},
  "openingHoursSpecification": [{{
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
    "opens": "08:00", "closes": "17:00"
  }}],
  "areaServed": [{areas}],
  "knowsAbout": "{svc}",
  "priceRange": "$$"
}}
</script>
"""


def faq_schema(faqs):
    items = ",".join(
        '{{"@type":"Question","name":{q},"acceptedAnswer":{{"@type":"Answer","text":{a}}}}}'.format(
            q=_json_str(q), a=_json_str(a)
        )
        for q, a in faqs
    )
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[' + items + ']}'
            '</script>\n')


def _json_str(s):
    s = re.sub("<.*?>", "", s).replace("&nbsp;", " ").replace("&amp;", "&").replace("→", "")
    s = s.replace("\\", "\\\\").replace('"', '\\"').strip()
    return '"' + s + '"'


def faq_block(faqs):
    out = ""
    for q, a in faqs:
        out += (f'<details><summary>{q}</summary><div class="faq-body"><p>{a}</p></div></details>')
    return f'<div class="faq">{out}</div>'


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
HOME_FAQS = [
    ("Do I need a permit for a fence in Jupiter?",
     "Almost always. Municipalities in this area generally require a building permit for a new fence, and the height, setback, and material rules differ from town to town. We pull the permit as part of the job and we call in the Sunshine 811 utility locates before anything gets dug."),
    ("How much does a fence cost?",
     "It depends on material, height, linear footage, gate count, and access — and anyone quoting a per-foot price over the phone without seeing the property is guessing. We measure on site for free and give you one number covering posts, concrete, hardware, gates, permit, and removal of the old fence."),
    ("How long does installation take?",
     "Most residential jobs are one to three days of actual work once materials are on site. The longer part of the calendar is usually permitting and, if you're in an HOA, architectural review. We'll give you a realistic timeline at the estimate, not an optimistic one."),
    ("Will you deal with my HOA?",
     "We're used to it. We can supply the specs, drawings, and material details most architectural review boards ask for. Getting the approval is ultimately the homeowner's submission, but we'll give you everything you need to submit."),
    ("Do you handle repairs, or only new fences?",
     "Both, and we repair fences we didn't install. Leaning sections, rotted posts, broken pickets, storm damage, and gates that won't latch are a large share of what we do."),
    ("Are you licensed and insured?",
     f"Yes — {BIZ['legal']} is licensed under #{BIZ['license']} and is bonded and insured. Ask any contractor for that before they set foot on your property, us included."),
    ("What's your warranty?",
     "One year on our workmanship, and a limited lifetime warranty on the material for our PVC fencing. We'll go over exactly what's covered before you sign."),
]


def page_index():
    cards = ""
    for s in SERVICES:
        cards += f"""<a class="scard" href="/gatekeeper/{s['slug']}">
  <div class="scard-art">{s['art'](s['slug'])}</div>
  <div class="scard-body">
    <h3>{s['nav']}</h3>
    <p>{s['card']}</p>
    <span class="scard-more">Learn more {ARROW_SVG}</span>
  </div>
</a>"""

    area_pills = "".join(f'<span class="area-pill">{a}</span>' for a in AREAS)

    html = head(
        f"Fence Company in Jupiter, FL | {BIZ['name']} | Free Estimates",
        f"Family-owned fence contractor in Jupiter, FL since {BIZ['since']}. Wood, vinyl, aluminum, chain link, and pool safety fencing, gates, and fence repair across northern Palm Beach County. Licensed #{BIZ['license']}, bonded and insured. Call {BIZ['phone_display']}.",
        "index",
        extra=local_business_schema() + faq_schema(HOME_FAQS),
    )
    html += header("gatekeeper")
    html += f"""
<section class="hero">
  {art_hero_fence()}
  <div class="wrap">
    <div>
      <span class="eyebrow">Jupiter, Florida · Since {BIZ['since']}</span>
      <h1>Fences and gates built to <em>stand up to the coast.</em></h1>
      <p class="hero-lede">Family-owned and owner-run. We install wood, vinyl, aluminum, chain link, and pool safety fencing across northern Palm Beach County — and we repair the ones somebody else got wrong.</p>
      <div class="hero-btns">
        <a class="btn btn-brass" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
        <a class="btn btn-light" href="#estimate">Get a free estimate {ARROW_SVG}</a>
      </div>
      <div class="hero-chips">
        <span class="chip">{SHIELD_SVG}Licensed #{BIZ['license']}</span>
        <span class="chip">{SHIELD_SVG}Bonded &amp; insured</span>
        <span class="chip">{SHIELD_SVG}Free on-site estimates</span>
        <span class="chip">{SHIELD_SVG}1-year workmanship guarantee</span>
      </div>
    </div>
    <div class="qcard" id="estimate">
      {quote_form()}
    </div>
  </div>
</section>

<section class="trust" style="padding:0">
  <div class="wrap">
    <div class="trust-item"><b>Since {BIZ['since']}</b><span>Locally owned in Jupiter</span></div>
    <div class="trust-item"><b>#{BIZ['license']}</b><span>Licensed, bonded &amp; insured</span></div>
    <div class="trust-item"><b>Lifetime</b><span>Limited warranty on PVC material</span></div>
    <div class="trust-item"><b>Free</b><span>On-site measure &amp; written quote</span></div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="sec-head center">
      <span class="kicker">What we build</span>
      <h2 class="big">Every fence type, one contractor</h2>
      <p class="lede">Residential and commercial. New installs, replacements, and repairs — from a four-foot pool barrier to a commercial perimeter.</p>
    </div>
    <div class="grid3">{cards}</div>
  </div>
</section>

{gallery(sand=True)}

<section class="sec-ink">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">Why Gatekeeper</span>
      <h2 class="big">The owner is on your job</h2>
      <p class="lede">We're a small, family-owned outfit in Jupiter — not a call center that subs your fence out to whoever's available. You talk to the person responsible for the work.</p>
    </div>
    <div class="feats">
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>Built for salt air</h3>
        <p>Hot-dip galvanized and stainless hardware, aluminum where steel would rust, and post depths sized for our sand. The details that decide whether a fence lasts five years or twenty.</p></div></div>
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>Permits and locates handled</h3>
        <p>We pull the permit, call in the Sunshine 811 utility locates, and meet the inspector. You don't chase paperwork.</p></div></div>
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>One price, whole job</h3>
        <p>Posts, concrete, hardware, gates, permit, and hauling off the old fence — all in the quote. Nothing appears halfway through the install.</p></div></div>
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>We'll talk you out of it</h3>
        <p>If a repair beats a replacement, we say so. If the material you asked for is wrong for your lot, we say that too. It's why people call us back years later.</p></div></div>
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>HOA and code experience</h3>
        <p>Height limits, setbacks, finished-side rules, architectural review packets, and Florida pool barrier requirements. We've been through all of it in these communities.</p></div></div>
      <div class="feat"><div class="feat-ico">{SHIELD_SVG}</div><div>
        <h3>Backed in writing</h3>
        <p>One-year guarantee on our workmanship and a limited lifetime warranty on PVC material. Licensed #{BIZ['license']}, bonded, and insured.</p></div></div>
    </div>
  </div>
</section>

<section class="sec-sand">
  <div class="wrap">
    <div class="sec-head center">
      <span class="kicker">How it works</span>
      <h2 class="big">Four steps, no surprises</h2>
    </div>
    <div class="steps">
      <div class="step"><h3>Call or request online</h3><p>Tell us roughly what you're after and where the property is. Takes two minutes.</p></div>
      <div class="step"><h3>Free on-site estimate</h3><p>We measure, look at access, grade, and soil, check the HOA and code constraints, and hand you one written number.</p></div>
      <div class="step"><h3>Permit &amp; locates</h3><p>We pull the permit and call in Sunshine 811 utility locates. Then we schedule your install date.</p></div>
      <div class="step"><h3>Install &amp; walkthrough</h3><p>We build it, clean up after ourselves, haul off the old fence, and walk the finished line with you before we leave.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="callout">
      <div>
        <span class="kicker" style="color:#fff;opacity:.85">Our guarantee</span>
        <h2>Backed by a warranty, not a handshake</h2>
        <p>We've been doing this in Jupiter since {BIZ['since']}, and we're still here because the work holds up.</p>
      </div>
      <ul class="ticks">
        <li>Limited lifetime warranty on PVC fence material</li>
        <li>One-year guarantee on our workmanship</li>
        <li>Licensed #{BIZ['license']}, bonded and insured</li>
        <li>Free, no-pressure on-site estimates</li>
      </ul>
    </div>
  </div>
</section>

<section class="sec-sand">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">Where we work</span>
      <h2 class="big">Northern Palm Beach &amp; southern Martin County</h2>
      <p class="lede">We're based on Foster Street in Jupiter and we work the corridor around it. If you're near the edge of this list, call anyway — we'll tell you straight whether we can get to you.</p>
    </div>
    <div class="areas">{area_pills}</div>
    <p style="margin-top:26px"><a class="btn btn-out" href="/gatekeeper/service-area">See the full service area {ARROW_SVG}</a></p>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="sec-head center">
      <span class="kicker">Questions</span>
      <h2 class="big">The things everybody asks</h2>
    </div>
    {faq_block(HOME_FAQS)}
  </div>
</section>
"""
    html += footer()
    return html


def page_services():
    cards = ""
    for s in SERVICES:
        cards += f"""<a class="scard" href="/gatekeeper/{s['slug']}">
  <div class="scard-art">{s['art'](s['slug'])}</div>
  <div class="scard-body">
    <h3>{s['nav']}</h3>
    <p>{s['card']}</p>
    <span class="scard-more">Learn more {ARROW_SVG}</span>
  </div>
</a>"""

    html = head(
        f"Fence Services in Jupiter, FL — Wood, Vinyl, Aluminum, Chain Link | {BIZ['name']}",
        "Wood, vinyl/PVC, aluminum, chain link, and pool safety fence installation, plus gates and fence repair in Jupiter and northern Palm Beach County. Free estimates.",
        "services",
    )
    html += header("services")
    html += f"""
<section class="pagehero"><div class="wrap">
  <p class="crumbs"><a href="/gatekeeper">Home</a> / Services</p>
  <h1>Fence services in Jupiter and northern Palm Beach County</h1>
  <p class="lede">Residential and commercial fencing, gates, and repairs. Every job includes a free on-site measure, the permit, and one written price for the whole thing.</p>
</div></section>

<section>
  <div class="wrap"><div class="grid3">{cards}</div></div>
</section>

<section class="sec-sand">
  <div class="wrap">
    <div class="split">
      <div>
        <span class="kicker">Choosing a material</span>
        <h2 class="big">Which fence is right for your lot?</h2>
        <div class="prose">
          <p>There isn't one correct answer — there's a correct answer for your property, your budget, and how much maintenance you're willing to do. The short version:</p>
          <ul>
            <li><strong>You want maximum privacy for the least money</strong> — wood. Board-on-board or stockade at six feet.</li>
            <li><strong>You never want to think about it again</strong> — vinyl. Costs more up front, no painting, no rot, no rust.</li>
            <li><strong>You're near the water, or it's a pool enclosure</strong> — aluminum. Won't corrode, won't block the view, and it's what most HOAs specify.</li>
            <li><strong>You need to enclose a lot of ground economically</strong> — chain link. Black vinyl-coated if you'd rather not see it.</li>
            <li><strong>You have a pool</strong> — you have a legal barrier requirement, not just a preference. Height, gaps, climbability, and gate hardware all have to comply.</li>
          </ul>
          <p>The other half of the decision is wind exposure. A solid six-foot privacy panel on an open, west-facing lot takes a beating that the same fence tucked behind a hedge never sees. That changes post depth and footing size — and it's a big part of why we insist on looking at the property before we quote.</p>
        </div>
      </div>
      <div class="aside-card">
        <h3>Not sure what you need?</h3>
        <p>That's a normal place to start. Tell us about the property and we'll walk the yard with you, explain the tradeoffs, and put a number on each option so you can compare them honestly.</p>
        <a class="btn btn-brass btn-wide" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
        <p style="margin:12px 0 0;text-align:center;font-size:14px">{BIZ['hours']}</p>
      </div>
    </div>
  </div>
</section>
"""
    html += footer()
    return html


def page_service(s):
    others = [x for x in SERVICES if x["slug"] != s["slug"]][:3]
    rel = ""
    for o in others:
        rel += f"""<a class="scard" href="/gatekeeper/{o['slug']}">
  <div class="scard-art">{o['art'](o['slug'])}</div>
  <div class="scard-body"><h3>{o['nav']}</h3><p>{o['card']}</p>
  <span class="scard-more">Learn more {ARROW_SVG}</span></div></a>"""

    plain_title = re.sub("<.*?>", "", s["title"]).replace("&amp;", "&")
    html = head(
        f"{plain_title} in Jupiter, FL | {BIZ['name']}",
        re.sub("<.*?>", "", s["card"]).replace("&nbsp;", " ")[:158],
        s["slug"],
        extra=faq_schema(s["faqs"]),
    )
    html += header(s["slug"])
    html += f"""
<section class="pagehero"><div class="wrap">
  <p class="crumbs"><a href="/gatekeeper">Home</a> / <a href="/gatekeeper/services">Services</a> / {s['nav']}</p>
  <h1>{s['h1']}</h1>
  <p class="lede">{s['lede']}</p>
</div></section>

<section>
  <div class="wrap">
    <div class="split">
      <div>
        <div class="artband">{s['art'](s['slug'])}</div>
        <div class="prose">{s['body']}</div>
      </div>
      <div class="aside-card">
        <h3>Free on-site estimate</h3>
        <p>We measure, check the code and HOA constraints for your address, and give you one written price for the whole job — permit included.</p>
        <a class="btn btn-brass btn-wide" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
        <p style="margin:12px 0 18px;text-align:center;font-size:14px">{BIZ['hours']}</p>
        <a class="btn btn-out btn-wide" href="/gatekeeper/contact">Request online {ARROW_SVG}</a>
        <ul class="ticks brass" style="margin-top:22px;font-size:15px">
          <li>Licensed #{BIZ['license']}, bonded &amp; insured</li>
          <li>Family-owned in Jupiter since {BIZ['since']}</li>
          <li>1-year workmanship guarantee</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<section class="sec-sand">
  <div class="wrap">
    <div class="sec-head center"><span class="kicker">{s['nav']} FAQs</span><h2 class="big">Common questions</h2></div>
    {faq_block(s['faqs'])}
  </div>
</section>

<section>
  <div class="wrap">
    <div class="sec-head center"><span class="kicker">Also from Gatekeeper</span><h2 class="big">Other services</h2></div>
    <div class="grid3">{rel}</div>
  </div>
</section>
"""
    html += footer()
    return html


def page_service_area():
    pills = "".join(f'<span class="area-pill">{a}</span>' for a in AREAS)
    html = head(
        f"Fence Company Service Area — Jupiter, Palm Beach Gardens, Tequesta &amp; More | {BIZ['name']}",
        "Gatekeeper Fence Co. installs and repairs fences across northern Palm Beach County and southern Martin County — Jupiter, Tequesta, Palm Beach Gardens, Juno Beach, Hobe Sound, Stuart and more.",
        "service-area",
    )
    html += header("service-area")
    html += f"""
<section class="pagehero"><div class="wrap">
  <p class="crumbs"><a href="/gatekeeper">Home</a> / Service Area</p>
  <h1>Where we work</h1>
  <p class="lede">We're based on {BIZ['street']} in {BIZ['city']} and we work the corridor around it — northern Palm Beach County up into southern Martin County.</p>
</div></section>

<section>
  <div class="wrap">
    <div class="split">
      <div class="prose">
        <h3>Communities we serve</h3>
        <div class="areas" style="margin-bottom:28px">{pills}</div>
        <p>Not on the list? Call anyway. We're a small crew, so we're honest about how far we'll travel and when — but the edges move depending on the size of the job and where else we're working that week. You'll get a straight yes or no on the phone, not a runaround.</p>

        <h3>Why local matters for a fence</h3>
        <p>Fencing is one of those trades where local knowledge shows up in the finished product. A few examples from right around here:</p>
        <ul>
          <li><strong>Soil changes fast in this county.</strong> Sugar sand out in Jupiter Farms holds a post very differently than coastal fill east of US-1. Post depth and footing size have to follow the ground, not a spec sheet.</li>
          <li><strong>Salt air reaches further inland than people think.</strong> Hardware that's fine in Wellington will bleed rust down a fence in Juno Beach. Material selection is a location decision.</li>
          <li><strong>Every municipality writes its own fence rules.</strong> Height limits, corner-lot visibility triangles, setbacks, and which side has to face the street all vary from town to town along this stretch.</li>
          <li><strong>HOA review is its own process.</strong> Communities up and down here have architectural review boards with specific approved materials and colors. Knowing which ones want what saves weeks.</li>
        </ul>

        <h3>Residential and commercial</h3>
        <p>Single-family homes, condo and HOA common areas, pool enclosures, dog runs, storage yards, dumpster enclosures, and commercial perimeters. If you manage property in this area and need a fence contractor who shows up and pulls the permit, call us.</p>
      </div>
      <div class="aside-card">
        <h3>{BIZ['name']}</h3>
        <p>{BIZ['street']}<br>{BIZ['city']}, {BIZ['state']} {BIZ['zip']}<br><br>{BIZ['hours']}</p>
        <a class="btn btn-brass btn-wide" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
        <p style="margin:12px 0 0;text-align:center;font-size:14px">Free on-site estimates</p>
      </div>
    </div>
  </div>
</section>
"""
    html += footer()
    return html


def page_about():
    html = head(
        f"About {BIZ['name']} — Family-Owned Fence Contractor in Jupiter, FL",
        f"Gatekeeper Fence, Inc. has been a family-owned fence contractor in Jupiter, Florida since {BIZ['since']}. Licensed #{BIZ['license']}, bonded and insured. Owner {BIZ['owner']}.",
        "about",
    )
    html += header("about")
    html += f"""
<section class="pagehero"><div class="wrap">
  <p class="crumbs"><a href="/gatekeeper">Home</a> / About</p>
  <h1>A small Jupiter fence company that's still here</h1>
  <p class="lede">{BIZ['legal']} has been building and repairing fences out of {BIZ['city']}, Florida since {BIZ['since']} — family-owned, owner-run, and licensed under #{BIZ['license']}.</p>
</div></section>

<section>
  <div class="wrap">
    <div class="split">
      <div class="prose">
        <h3>Who you're dealing with</h3>
        <p>Gatekeeper is a family business owned by {BIZ['owner']}, operating out of {BIZ['street']} in {BIZ['city']}. That's not a marketing line — it's the practical difference between us and a lot of the fence outfits advertising in this market. When you call, you get someone who will actually be involved in your job. When there's a problem, there's no layer of dispatchers between you and the person who can fix it.</p>
        <p>Plenty of fence companies come and go around here. We've been at it since {BIZ['since']}, through the hurricanes and the housing swings, largely on repeat customers and their neighbors.</p>

        <h3>How we work</h3>
        <ul>
          <li><strong>We look before we quote.</strong> No per-foot phone estimates. Access, grade, soil, and existing structures change the number, sometimes a lot.</li>
          <li><strong>One price, whole job.</strong> Posts, concrete, hardware, gates, the permit, and hauling off the old fence are in the quote. We don't discover things halfway through.</li>
          <li><strong>We'll tell you not to buy something.</strong> If your fence needs a repair instead of a replacement, that's what we'll recommend, even though it's the smaller ticket.</li>
          <li><strong>We clean up.</strong> Old fence hauled off, concrete spoil removed, the yard raked. You shouldn't be able to tell we were there except for the fence.</li>
        </ul>

        <h3>Licensed, bonded, and insured</h3>
        <p>We hold Florida contractor license <strong>#{BIZ['license']}</strong> and we carry bonding and insurance. Ask to see that from any contractor before they dig on your property — it protects you if something goes wrong, and a contractor who hesitates to show it is telling you something.</p>

        <h3>What we stand behind</h3>
        <ul>
          <li><strong>One-year guarantee</strong> on our workmanship.</li>
          <li><strong>Limited lifetime warranty</strong> on the material for our PVC fencing.</li>
          <li><strong>Free on-site estimates</strong>, with no pressure to sign anything at the kitchen table.</li>
        </ul>

        <h3>What we do</h3>
        <p>Residential and commercial fence installation in wood, vinyl/PVC, aluminum, and chain link; pool safety barriers; gate installation; and repair work — leaning fences straightened, rotted posts replaced, broken pickets swapped, storm damage put back together, and gates re-hung. We repair fences we didn't install, which is a large share of what keeps us busy.</p>
      </div>
      <div class="aside-card">
        <h3>Get us out there</h3>
        <p>Free on-site measure and a written quote for the whole job. Call and we'll find a time.</p>
        <a class="btn btn-brass btn-wide" href="tel:{BIZ['phone_tel']}">{PHONE_SVG}Call {BIZ['phone_display']}</a>
        <p style="margin:12px 0 18px;text-align:center;font-size:14px">{BIZ['hours']}</p>
        <a class="btn btn-out btn-wide" href="/gatekeeper/contact">Request online {ARROW_SVG}</a>
        <ul class="ticks brass" style="margin-top:22px;font-size:15px">
          <li>Family-owned since {BIZ['since']}</li>
          <li>Licensed #{BIZ['license']}</li>
          <li>Bonded &amp; insured</li>
        </ul>
      </div>
    </div>
  </div>
</section>
"""
    html += footer()
    return html


def page_contact():
    html = head(
        f"Contact {BIZ['name']} — Free Fence Estimates in Jupiter, FL",
        f"Call {BIZ['phone_display']} or request a free on-site fence estimate. Gatekeeper Fence Co., {BIZ['street']}, {BIZ['city']}, FL {BIZ['zip']}. {BIZ['hours']}.",
        "contact",
        extra=local_business_schema(),
    )
    html += header("contact")
    html += f"""
<section class="pagehero"><div class="wrap">
  <p class="crumbs"><a href="/gatekeeper">Home</a> / Contact</p>
  <h1>Get a free estimate</h1>
  <p class="lede">Fastest way to reach us is the phone. If it's after hours, send the form and we'll call you back.</p>
</div></section>

<section>
  <div class="wrap">
    <div class="split">
      <div class="qcard" style="box-shadow:var(--shadow);border:1px solid var(--line)">
        {quote_form("Tell us about your project", "We'll call you back to schedule a free on-site measure and quote.")}
      </div>
      <div>
        <div class="prose">
          <h3 style="margin-top:0">Call or text</h3>
          <p style="font-family:'Archivo',sans-serif;font-size:30px;font-weight:800;margin-bottom:6px">
            <a href="tel:{BIZ['phone_tel']}" style="text-decoration:none;color:var(--brass)">{BIZ['phone_display']}</a>
          </p>
          <p>{BIZ['hours']}</p>

          <h3>Where we are</h3>
          <p>{BIZ['name']}<br>{BIZ['street']}<br>{BIZ['city']}, {BIZ['state']} {BIZ['zip']}</p>
          <p><a class="btn btn-out" href="https://www.google.com/maps/search/?api=1&amp;query={BIZ['street'].replace(' ', '+')}+{BIZ['city']}+{BIZ['state']}+{BIZ['zip']}" target="_blank" rel="noopener">Open in Maps {ARROW_SVG}</a></p>

          <h3>What to have ready</h3>
          <p>None of this is required, but it makes the first call faster:</p>
          <ul>
            <li>Rough linear footage, or just the property address so we can look at it.</li>
            <li>Fence height you're after, and whether you have an HOA.</li>
            <li>New install, replacement, or repair.</li>
            <li>Any deadline you're working against — a closing date, a pool inspection, an HOA notice.</li>
          </ul>

          <h3>Emergencies and storm damage</h3>
          <p>If your fence is down and it's holding a dog in or serving as a pool barrier, say that when you call. Those don't wait in line.</p>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    html += footer()
    return html


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build():
    os.makedirs(OUT, exist_ok=True)
    pages = {
        "index.html": page_index(),
        "services.html": page_services(),
        "service-area.html": page_service_area(),
        "about.html": page_about(),
        "contact.html": page_contact(),
    }
    for s in SERVICES:
        pages[s["slug"] + ".html"] = page_service(s)

    for name, html in sorted(pages.items()):
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"  wrote gatekeeper/{name}  ({len(html):,} bytes)")

    # sitemap for when a domain is pointed at this folder
    urls = ["index"] + ["services", "service-area", "about", "contact"] + [s["slug"] for s in SERVICES]
    body = ""
    for u in urls:
        loc = BIZ["origin"] + ("" if u == "index" else "/" + u)
        pri = "1.0" if u == "index" else "0.8"
        body += (f"  <url><loc>{loc}</loc><changefreq>monthly</changefreq>"
                 f"<priority>{pri}</priority></url>\n")
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sm)
    print(f"  wrote gatekeeper/sitemap.xml ({len(urls)} urls)")
    print(f"\nDone — {len(pages)} pages.")


if __name__ == "__main__":
    build()
