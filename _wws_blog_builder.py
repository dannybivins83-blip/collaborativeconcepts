"""Build the La Gala WWS blog: /wwslgc/blog/index.html + one post per top-15 item.
La Gala-branded (navy #1a1a2e + gold #c9a227), self-contained on the wwslgc subdomain.
Regenerate any time: python _wws_blog_builder.py
"""
import os

REPO = os.path.dirname(os.path.abspath(__file__))
BLOG = os.path.join(REPO, "wwslgc", "blog")
os.makedirs(BLOG, exist_ok=True)
MARKER = '<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">'

# slug, title, standard, image, temp, short(gallery), why, how_often, fix, credit
POSTS = [
 ("unprotected-edges","Unprotected Sides &amp; Edges","§1910.28","Hot",
  "No guardrail where a 4&nbsp;ft+ fall is possible.",
  "Any walking-working surface with an unprotected side or edge 4 feet or more above a lower level is the single most-cited fall hazard in general industry. Roof perimeters, mezzanines, loading platforms, pits and elevated walkways all qualify. A worker doesn't have to be at the edge full-time &mdash; if the path of travel passes within reach of an unguarded drop, OSHA can cite it.",
  "OSHA can flag this any time an inspector observes exposure &mdash; it's a core target of the OSHA Fall-Protection National Emphasis Program (CPL 03-00-024). There's no &lsquo;scheduled&rsquo; check: the duty to have fall protection is continuous, so the only safe cadence is to verify guarding before every work cycle and re-inspect permanent guardrails at least annually.",
  "We engineer and install compliant guardrail (42&Prime; top rail, able to take a 200&nbsp;lb load), or designated-area and travel-restraint systems where rails aren't practical &mdash; then document it so the hazard is closed for good.",
  ""),
 ("floor-holes","Floor Holes &amp; Openings","§1910.28","Hot",
  "Uncovered pits, holes, and floor openings.",
  "A hole is any gap 2 inches or more in the smallest dimension; an opening is 12 inches or more. Uncovered drains, removed grates, demolition gaps, and floor penetrations are easy to walk or step into. They're a fall-through and trip hazard at the same time, and they're routinely missed because the cover &lsquo;was just moved for a minute.&rsquo;",
  "There is no fixed interval &mdash; the requirement to guard a hole is continuous, so it must be verified whenever a cover is removed and at every routine safety walk. OSHA cites it on complaint, accident, or NEP-driven inspection.",
  "We install code-compliant covers (rated for at least twice the maximum load) or guardrails around the opening, and standardize cover hardware so a removed cover gets put back the same way every time.",
  "Photo: Bart Everson, CC BY 2.0"),
 ("housekeeping","Poor Housekeeping","§1910.22","Warm",
  "Cluttered, obstructed, or untidy walkways.",
  "§1910.22(a) requires walking-working surfaces to be kept clean, orderly and sanitary. Boxes in aisles, trailing cords, debris, and blocked egress paths are the most common &lsquo;soft&rsquo; citation &mdash; cheap to fix, but a reliable trigger once an inspector is on site for something else.",
  "Housekeeping is a daily, continuous obligation. There's no recert; it's judged on what the inspector sees that day, which is why it so often rides along with a complaint or accident inspection.",
  "Housekeeping itself is on you, but we eliminate the built-in causes &mdash; poor drainage, missing storage, bad surface transitions and tripping seams &mdash; so the aisles stay clear without a daily fight.",
  ""),
 ("damaged-surfaces","Damaged Walking Surfaces","§1910.22","Hot",
  "Spalled concrete, cracks, and trip hazards.",
  "Spalling concrete, potholes, lifted joints and crumbling slab edges violate §1910.22(b), which requires surfaces to be maintained in good repair. In South Florida the salt-air environment accelerates this &mdash; and the same deterioration that trips a worker is what a structural inspector flags on a recertification.",
  "This is the classic &lsquo;flagged by both&rsquo; item. OSHA cites it on any inspection; separately, Florida's <strong>Milestone</strong> structural inspections (30 years, 25 near the coast, then every 10) and the Miami-Dade / Broward <strong>40-year recertification</strong> document spalled walkways and balcony slabs as structural deficiencies requiring an engineered repair.",
  "Concrete restoration is our core trade &mdash; spall repair, rebar treatment, slab-edge and balcony rebuilds, and protective coatings, sequenced for occupied buildings so tenants stay comfortable while we work.",
  ""),
 ("standing-water","Standing Water &amp; Drainage","§1910.22","Warm",
  "Surfaces not kept dry or properly drained.",
  "§1910.22(a)(2) requires walking-working surfaces to be kept dry where possible and drained where wet processes are used. Ponding on a roof or deck is both a slip hazard and the root cause of the concrete and waterproofing failures that show up later.",
  "OSHA cites the slip exposure whenever it's observed. On the building-code side, the failed waterproofing that causes ponding is a recurring finding on Milestone and 40-year recertification inspections &mdash; so it tends to resurface on the 10-year recert clock if it isn't truly fixed.",
  "We correct the drainage and re-waterproof &mdash; re-sloping, deck coatings, drain repair and joint sealant &mdash; so the surface sheds water and the hazard doesn't come back.",
  ""),
 ("guardrail-systems","Guardrail Systems","§1910.29","Hot",
  "Rails that miss height or strength criteria.",
  "Even where a railing exists, §1910.29 sets the criteria it must meet: a 42-inch (&plusmn;3&Prime;) top rail, a midrail at ~21&Prime;, and the ability to withstand a 200-pound force in any outward or downward direction. Loose, low, corroded, or under-strength rails fail the test &mdash; a rail that looks fine can still be non-compliant.",
  "OSHA judges guardrail criteria on inspection. Because corrosion and loosening are progressive, permanent guardrail should be inspected at least annually &mdash; and it's a standard line item on Florida structural recertifications, where rusted or wobbling balcony and walkway rails are flagged.",
  "We bring rails up to the dimensional and strength criteria, replace corroded sections, and re-anchor to sound substrate &mdash; with a sign-off that documents compliance.",
  ""),
 ("stairways","Non-Compliant Stairways","§1910.25","Warm",
  "Missing stair rails, handrails, or treads.",
  "Industrial and egress stairs must meet §1910.25: stair rails on open sides, handrails within a defined height band, uniform riser/tread geometry, and adequate strength. Worn nosings, missing handrails and inconsistent risers are common &mdash; and they're a frequent injury point as well as a citation.",
  "OSHA cites stair deficiencies on inspection. Exterior and structural stairs are also reviewed on Milestone and 40-year recertifications, where corroded stringers and loose handrails are documented for repair on the recurring 10-year cycle.",
  "We repair or replace handrails and stair rails to the dimensional criteria, restore treads and nosings, and address the structural stringer corrosion behind them.",
  ""),
 ("roof-anchors","Uncertified Roof Anchors","§1910.27","Hot",
  "Tie-offs never load-tested or certified.",
  "Any anchorage a worker ties off to must hold <strong>5,000 pounds per attached person</strong> (§1910.27(b)), or be engineered with a 2:1 safety factor under a qualified person. Older buildings often have anchors that were never load-tested, were added informally, or have corroded &mdash; and a window-washing or maintenance contractor won't work until they're certified.",
  "This is the most calendar-driven item on the list. Anchorages require a <strong>visual inspection at least annually</strong> by a qualified person, and a <strong>load re-certification at least every 10 years</strong> (shorter &mdash; commonly 5 years &mdash; for adhesive/post-installed anchors per ANSI/IWCA I-14.1 and the engineer's spec). That recurring clock is exactly what an ongoing maintenance plan manages.",
  "Our licensed PE partner performs the proof-load test and issues the sealed certification; our crews install, repair, or replace anchors to spec &mdash; one contract for the certify-and-fix.",
  ""),
 ("roof-edge-exposure","Low-Slope Roof-Edge Work","§1910.28","Warm",
  "Work near low-slope roof edges, unprotected.",
  "On low-slope roofs, §1910.28(b)(13) sets graduated requirements based on how close work happens to the edge &mdash; from warning lines and safety monitors to full guardrail or personal fall arrest as you approach the edge. HVAC techs, roofers and inspectors are exposed every time they go up, often with no system in place.",
  "Roof-edge exposure is a primary target of the Fall-Protection NEP &mdash; an inspector who sees an unprotected worker on a roof can open an inspection on the spot. The duty is continuous, so protection has to be verified before every rooftop job.",
  "We design the right mix for the roof &mdash; permanent guardrail at access points and equipment, plus certified anchors and tie-off paths for edge work &mdash; so every trade that goes up is protected.",
  "Photo: Karl and Ali / Geograph, CC BY-SA 2.0"),
 ("fixed-ladders","Unsafe Fixed Ladders","§1910.23","Warm",
  "Fixed ladders missing cages or fall-arrest.",
  "Fixed ladders must meet §1910.23, and the rules have changed: fixed ladders over 24 feet must now have a personal fall-arrest or ladder-safety system, and cages are being phased out as the compliant solution by 2036. Many existing caged ladders, rusted rungs and missing landing platforms are now out of compliance.",
  "OSHA cites fixed-ladder deficiencies on inspection. The 2036 phase-out gives a hard deadline for retrofits, and corroded ladders also surface on structural recertifications &mdash; so there's both a regulatory clock and a maintenance clock on these.",
  "We retrofit fixed ladders with compliant ladder-safety or fall-arrest systems, replace corroded sections and landing platforms, and bring access into line with the current standard and the 2036 deadline.",
  ""),
 ("dockboards","Dockboards &amp; Loading Docks","§1910.26","Warm",
  "Unsecured dockboards and unguarded dock edges.",
  "§1910.26 governs dockboards (dock plates), and §1910.28 covers the open dock edge itself &mdash; a 4-foot drop that forklifts and workers pass constantly. Run-off and shifting dockboards, missing edge protection, and no load ratings are routine findings at loading docks.",
  "Dock hazards are cited on OSHA inspection, frequently after a forklift incident. The exposure is continuous, so edge protection and dockboard condition should be verified daily in use and inspected on the annual safety walk.",
  "We add compliant dock-edge protection (gates, barriers), specify and secure rated dockboards, and repair the spalled dock faces and bumpers that let equipment shift.",
  ""),
 ("skylights-openings","Skylights &amp; Roof Openings","§1910.28","Hot",
  "Fragile skylights and uncovered roof hatches.",
  "Skylights are treated as holes under §1910.28 &mdash; an unguarded or non-load-rated skylight is a fall-through fatality waiting to happen, and roof hatches left open are the same hazard. Workers routinely fall through skylights they assumed would hold their weight; they won't.",
  "OSHA cites unguarded skylights and hatches on inspection and it's a known fatality category, so it draws NEP attention. The duty is continuous &mdash; guarding has to be in place whenever the roof is accessed.",
  "We install skylight screens or guardrails rated to hold the load, and self-closing hatch guards, so the opening is protected without blocking access or light.",
  ""),
 ("mobile-ladder-stands","Mobile Ladder Stands","§1910.29","Cool",
  "Rolling platforms missing rails or locks.",
  "Mobile ladder stands and rolling work platforms have their own criteria in §1910.29 &mdash; handrails and guardrails above set heights, slip-resistant steps, and locking casters. Shop-built or worn units often miss the rails or won't lock, turning routine reach-up work into a fall.",
  "OSHA cites these on inspection. There's no recert interval, but because wheels, locks and rails wear, they should be inspected on the routine (at least annual) equipment safety check and tagged out when they fail.",
  "We specify and supply compliant ladder stands and platforms, and repair or remove the non-compliant units already on your floor.",
  ""),
 ("slippery-surfaces","Slippery Surfaces","§1910.22","Cool",
  "Low-traction or chronically wet surfaces.",
  "Beyond housekeeping, §1910.22 expects walking surfaces to provide adequate traction. Worn smooth concrete, the wrong coating, wet processes and weather-exposed ramps create chronic slip exposure that a &lsquo;wet floor&rsquo; sign doesn't actually fix.",
  "OSHA cites slip exposure whenever observed, usually after a slip-and-fall report. There's no scheduled check &mdash; it's a continuous condition, best caught on routine walks and corrected at the surface, not papered over with signage.",
  "We restore traction at the surface &mdash; high-friction coatings, profiled finishes, and drainage corrections &mdash; so the floor is safe in the conditions it actually sees.",
  "Photo: Phil Champion / Geograph, CC BY-SA 2.0"),
 ("ramps-walkways","Ramps &amp; Elevated Walkways","§1910.22","Cool",
  "Elevated walkways and ramps without protection.",
  "Ramps, runways and elevated walkways must be structurally sound (§1910.22) and guarded where they're 4 feet or more above a lower level (§1910.28). Connector walkways, equipment platforms and roof-access runways are easy to overlook &mdash; until a slab edge spalls or a rail gives way.",
  "OSHA cites the fall and structural exposure on inspection. Elevated concrete walkways are also a core Milestone / 40-year recertification finding, so structural deterioration here rides the recurring 10-year recert clock.",
  "We restore the walking surface and structure and add compliant guardrail and traction &mdash; treating the walkway as both a fall-protection and a concrete-restoration scope.",
  ""),
]

HEAD = """<!DOCTYPE html>
<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{title_plain} | La Gala Construction</title>
<meta name="description" content="{meta}"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
{marker}
<link rel="canonical" href="{canonical}"/>
<meta property="og:type" content="article"/>
<meta property="og:title" content="{title_plain} | La Gala Construction"/>
<meta property="og:description" content="{meta}"/>
<meta property="og:image" content="https://wwslgc.collaborativeconceptsfl.com/assets/wws/{img}.jpg"/>
<meta property="og:url" content="{canonical}"/>
<meta name="theme-color" content="#1a1a2e"/>
<link rel="icon" type="image/png" href="/assets/lagala-mark.png"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Manrope:wght@700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script>
  tailwind.config = {{ darkMode:"class", theme:{{ extend:{{
    colors:{{ primary:"#1a1a2e","primary-container":"#2d2d4a",secondary:"#c9a227","secondary-container":"#e8c547","secondary-fixed":"#f0d060","on-secondary-fixed":"#3d2e00",surface:"#f8f7f5","surface-container-low":"#f0efed","surface-container-lowest":"#ffffff","surface-container-high":"#e5e4e2","on-surface":"#1a1a1a","on-surface-variant":"#4a4a4a","outline-variant":"#c5c5c0","on-primary":"#ffffff" }},
    borderRadius:{{ DEFAULT:"0.5rem", lg:"0.75rem", xl:"1rem", full:"9999px" }},
    fontFamily:{{ headline:["Manrope"], body:["Inter"] }} }} }} }}
</script>
<style>body{{font-family:'Inter',sans-serif}}h1,h2,h3{{font-family:'Manrope',sans-serif}}.material-symbols-outlined{{font-variation-settings:'FILL' 0,'wght' 400}}html{{scroll-behavior:smooth}}</style>
<link rel="preconnect" href="https://www.googletagmanager.com"/>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-K9ZEXRRMCK"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-K9ZEXRRMCK');</script>
</head>
<body class="bg-surface text-on-surface">
<div class="h-1 w-full bg-gradient-to-r from-secondary via-secondary-fixed to-secondary"></div>
<nav class="w-full sticky top-0 z-50 bg-[#f8f7f5]/80 backdrop-blur-md border-b border-outline-variant/20">
<div class="flex justify-between items-center px-6 sm:px-8 py-4 max-w-7xl mx-auto">
<a href="/" class="flex items-center" aria-label="La Gala Construction"><img src="/assets/lagala-logo.png" alt="La Gala Construction" class="h-10 sm:h-12 w-auto"/></a>
<div class="flex items-center gap-6"><a href="/blog" class="text-primary opacity-80 hover:text-secondary font-medium hidden sm:inline">Guides</a><a href="/#assessment" class="bg-secondary text-white px-5 py-2.5 rounded-xl font-semibold hover:bg-secondary-container hover:text-on-secondary-fixed transition-all">Free Assessment</a></div>
</div>
</nav>
"""

FOOTER = """<footer class="w-full py-12 px-6 sm:px-8 flex flex-col items-center text-center space-y-5 bg-[#1a1a2e] text-[#f8f7f5]">
<a href="/" class="inline-block"><img src="/assets/lagala-logo.png" alt="La Gala Construction" class="h-11 w-auto" style="filter:brightness(0) invert(1)"/></a>
<p class="text-sm text-[#f8f7f5]/70 max-w-xl">Concrete Restoration &middot; Waterproofing &middot; Fall-Protection &amp; Compliance &mdash; South Florida.</p>
<div class="flex flex-wrap justify-center gap-6 text-sm"><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/blog">All guides</a><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/#plans">Build a plan</a><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/#assessment">Free assessment</a></div>
<p class="text-xs text-[#f8f7f5]/50">25 SE 7th Street, Ste 12 &middot; Deerfield Beach, FL 33441 &middot; (561) 475-8615 &middot; danny@lagalacon.com</p>
<p class="text-xs text-[#f8f7f5]/40 max-w-3xl">La Gala Construction is a Florida State Certified General Contractor (CGC 059211). Engineering certifications referenced are performed and sealed by an independent, licensed Florida professional engineer; La Gala does not provide engineering services.{credit}</p>
<p class="text-sm text-[#f8f7f5]/60">&copy; 2026 La Gala Construction (Tilt Patchers, Inc.). Licensed &middot; Bonded &middot; Insured.</p>
</footer>
<script defer src="https://va.vercel-scripts.com/v1/script.js" data-website-id="prj_LkelimAuti9JBNu5B8zB7Rr1ILON"></script>
</body></html>"""

def cta():
    return """<div class="bg-primary text-on-primary rounded-2xl p-8 sm:p-10 mt-12 text-center">
<h2 class="text-2xl sm:text-3xl font-extrabold">Got this on a citation — or want to get ahead of it?</h2>
<p class="text-on-primary/75 mt-3 max-w-2xl mx-auto">We certify it and we fix it, under one contract. Start with a free, no-obligation assessment, or build a custom compliance plan in two minutes.</p>
<div class="flex flex-wrap gap-4 justify-center mt-7">
<a href="/#assessment" class="bg-secondary text-white px-7 py-3.5 rounded-xl font-bold hover:bg-secondary-container hover:text-on-secondary-fixed transition-colors">Get a free assessment</a>
<a href="/#plans" class="border-2 border-secondary-fixed text-secondary-fixed px-7 py-3.5 rounded-xl font-bold hover:bg-secondary-fixed hover:text-on-secondary-fixed transition-colors">Build a plan</a>
</div></div>"""

def build_post(p):
    slug,title,std,temp,short,why,how,fix,credit = p
    img = slug
    title_plain = title.replace("&amp;","&")
    meta = (why[:150].rsplit(" ",1)[0]) + "…"
    head = HEAD.format(title_plain=title_plain, meta=meta, marker=MARKER,
                       canonical=f"https://wwslgc.collaborativeconceptsfl.com/blog/{slug}", img=img)
    credit_html = f'<p class="text-xs text-on-surface-variant/60 mt-3 italic">{credit}.</p>' if credit else ""
    foot_credit = f" {credit}." if credit else ""
    art = f"""<main class="overflow-x-hidden">
<article class="max-w-3xl mx-auto px-6 sm:px-8 py-12">
<a href="/blog" class="text-sm font-semibold text-secondary hover:underline inline-flex items-center gap-1"><span class="material-symbols-outlined text-base">arrow_back</span> All compliance guides</a>
<div class="mt-5 flex items-center gap-3"><span class="text-xs font-bold bg-secondary text-white px-2.5 py-1 rounded-full">{std}</span><span class="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">{temp} lead item</span></div>
<h1 class="text-3xl sm:text-5xl font-extrabold text-primary leading-tight tracking-tight mt-4">{title}</h1>
<img src="/assets/wws/{img}.jpg" alt="{title_plain}" class="w-full rounded-2xl mt-8 shadow-lg aspect-[16/9] object-cover"/>
{credit_html}
<div class="prose mt-10 space-y-8">
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">priority_high</span> Why it matters</h2><p class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{why}</p></section>
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">event_repeat</span> How often it's checked</h2><p class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{how}</p></section>
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">construction</span> How La Gala fixes it</h2><p class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{fix}</p></section>
</div>
{cta()}
</article>
</main>
"""
    return head + art + FOOTER.format(credit=foot_credit)

def build_index():
    head = HEAD.format(title_plain="OSHA Walking-Working Surfaces — Compliance Guides", meta="The top 15 OSHA Walking-Working Surfaces violations explained — what each one is, how often it's inspected, and how La Gala Construction fixes it. South Florida.", marker=MARKER, canonical="https://wwslgc.collaborativeconceptsfl.com/blog", img="unprotected-edges")
    cards = ""
    for p in POSTS:
        slug,title,std,temp,short = p[0],p[1],p[2],p[3],p[4]
        img = slug
        cards += f"""<a href="/blog/{slug}" class="group bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/20 shadow-sm hover:shadow-lg hover:border-secondary transition-all flex flex-col">
<div class="aspect-[16/10] overflow-hidden"><img src="/assets/wws/{img}.jpg" alt="{title.replace('&amp;','&')}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/></div>
<div class="p-5 flex-1 flex flex-col"><span class="text-[11px] font-bold text-secondary">{std}</span><h3 class="font-bold text-primary mt-1 leading-tight">{title}</h3><p class="text-sm text-on-surface-variant mt-1.5 flex-1">{short}</p><span class="text-sm font-semibold text-primary mt-3 inline-flex items-center gap-1 group-hover:text-secondary">Read the guide <span class="material-symbols-outlined text-base">arrow_forward</span></span></div></a>"""
    body = f"""<main class="overflow-x-hidden">
<section class="max-w-7xl mx-auto px-6 sm:px-8 pt-14 pb-8">
<span class="text-secondary font-semibold tracking-widest uppercase text-xs">Compliance guides</span>
<h1 class="text-4xl sm:text-5xl font-extrabold text-primary leading-tight tracking-tight mt-3 max-w-3xl">The top 15 things OSHA cites — explained.</h1>
<p class="text-lg text-on-surface-variant leading-relaxed mt-5 max-w-2xl">For each Walking-Working Surfaces hazard: what it is, why it matters, how often it's inspected or re-certified, and how we close it out. Click any one to read the guide.</p>
</section>
<section class="max-w-7xl mx-auto px-6 sm:px-8 pb-20"><div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">{cards}</div></section>
{('<section class="max-w-7xl mx-auto px-6 sm:px-8 pb-20">'+cta()+'</section>')}
</main>
"""
    return head + body + FOOTER.format(credit="")

n=0
for p in POSTS:
    open(os.path.join(BLOG, p[0]+".html"), "w", encoding="utf-8", newline="").write(build_post(p))
    n+=1
open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8", newline="").write(build_index())
print(f"Generated {n} posts + index in wwslgc/blog/")
print("Posts:", ", ".join(p[0] for p in POSTS))
