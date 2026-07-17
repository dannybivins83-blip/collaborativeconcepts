"""Build the La Gala WWS blog: /wwslgc/guides/index.html + one post per top-15 item.
La Gala-branded (navy #1a1a2e + gold #c9a227), self-contained on the wwslgc subdomain.
Regenerate any time: python _wws_blog_builder.py
"""
import os

REPO = os.path.dirname(os.path.abspath(__file__))
BLOG = os.path.join(REPO, "wwslgc", "guides")
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
  "This is the classic &lsquo;flagged by both&rsquo; item. OSHA cites it on any inspection; separately, Florida's <strong>Milestone</strong> structural inspections (30 years, or 25 near salt water, then every 10) and the Miami-Dade / Broward <strong>county recertification</strong> document spalled walkways and balcony slabs as structural deficiencies requiring an engineered repair.",
  "Concrete restoration is our core trade &mdash; spall repair, rebar treatment, slab-edge and balcony rebuilds, and protective coatings, sequenced for occupied buildings so tenants stay comfortable while we work.",
  ""),
 ("standing-water","Standing Water &amp; Drainage","§1910.22","Warm",
  "Surfaces not kept dry or properly drained.",
  "§1910.22(a)(2) requires walking-working surfaces to be kept dry where possible and drained where wet processes are used. Ponding on a roof or deck is both a slip hazard and the root cause of the concrete and waterproofing failures that show up later.",
  "OSHA cites the slip exposure whenever it's observed. On the building-code side, the failed waterproofing that causes ponding is a recurring finding on Milestone and county recertification inspections &mdash; so it tends to resurface on the 10-year recert clock if it isn't truly fixed.",
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
  "OSHA cites stair deficiencies on inspection. Exterior and structural stairs are also reviewed on Milestone and county recertifications, where corroded stringers and loose handrails are documented for repair on the recurring 10-year cycle.",
  "We repair or replace handrails and stair rails to the dimensional criteria, restore treads and nosings, and address the structural stringer corrosion behind them.",
  ""),
 ("roof-anchors","Uncertified Roof Anchors","§1910.27","Hot",
  "Tie-offs never load-tested or certified.",
  "Any anchorage a worker ties off to must hold <strong>5,000 pounds per attached person</strong> (§1910.27(b)), or be engineered with a 2:1 safety factor under a qualified person. Older buildings often have anchors that were never load-tested, were added informally, or have corroded &mdash; and a window-washing or maintenance contractor won't work until they're certified.",
  "This is the most calendar-driven item on the list. Anchorages require a <strong>visual inspection at least annually</strong> by a qualified person, and a <strong>load re-certification at least every 10 years</strong> (shorter &mdash; commonly 5 years &mdash; for adhesive/post-installed anchors per ANSI/IWCA I-14.1 and the engineer's spec). That recurring clock is exactly what an ongoing maintenance plan manages.",
  "Our licensed PE partner performs the proof-load test and issues the sealed certification; our crews install, repair, or replace anchors to spec &mdash; one contract for the certify-and-fix.",
  ""),
 ("window-washing","Window-Washing &amp; Rope-Descent Anchors","§1910.27","Hot",
  "Uncertified rooftop anchors for window cleaning.",
  "Before any contractor can drop a rope to wash your windows or work the facade, OSHA §1910.27(b) makes the building owner identify and certify the rooftop tie-back and rope descent system (RDS) anchors &mdash; each one must hold 5,000 pounds. Most older buildings have davits, parapet clamps or roof anchors that were never tested, and a reputable window-washing company simply won't tie off until they're certified.",
  "One of the most calendar-driven duties in Subpart D: RDS anchorages must be inspected by a qualified person at least annually, with a load re-certification at least every 10 years &mdash; and ANSI/IWCA I-14.1 practice is tighter, commonly every 5 years and before any re-roof or facade project. It's a recurring liability an ongoing plan keeps on schedule.",
  "Our licensed PE partner load-tests and certifies every davit, outrigger and roof anchor; our crews install, repair or replace them to spec &mdash; so your window-washing and facade contractors can work and you hold the sealed certification OSHA wants.",
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
 ("slippery-surfaces","Slippery Surfaces","§1910.22","Cool",
  "Low-traction or chronically wet surfaces.",
  "Beyond housekeeping, §1910.22 expects walking surfaces to provide adequate traction. Worn smooth concrete, the wrong coating, wet processes and weather-exposed ramps create chronic slip exposure that a &lsquo;wet floor&rsquo; sign doesn't actually fix.",
  "OSHA cites slip exposure whenever observed, usually after a slip-and-fall report. There's no scheduled check &mdash; it's a continuous condition, best caught on routine walks and corrected at the surface, not papered over with signage.",
  "We restore traction at the surface &mdash; high-friction coatings, profiled finishes, and drainage corrections &mdash; so the floor is safe in the conditions it actually sees.",
  "Photo: Phil Champion / Geograph, CC BY-SA 2.0"),
 ("ramps-walkways","Ramps &amp; Elevated Walkways","§1910.22","Cool",
  "Elevated walkways and ramps without protection.",
  "Ramps, runways and elevated walkways must be structurally sound (§1910.22) and guarded where they're 4 feet or more above a lower level (§1910.28). Connector walkways, equipment platforms and roof-access runways are easy to overlook &mdash; until a slab edge spalls or a rail gives way.",
  "OSHA cites the fall and structural exposure on inspection. Elevated concrete walkways are also a core Milestone / county recertification finding, so structural deterioration here rides the recurring 10-year recert clock.",
  "We restore the walking surface and structure and add compliant guardrail and traction &mdash; treating the walkway as both a fall-protection and a concrete-restoration scope.",
  ""),
 ("rooftop-crossover","Rooftop Pipe &amp; Utility Crossovers","§1910.28","Warm",
  "Crossing over roof pipes, gas &amp; water lines.",
  "Commercial roofs are crowded with gas lines, condensate and water piping, conduit and duct. When workers have to step over those runs to service equipment, OSHA requires a crossover platform or bridge &mdash; a stepped, guardrailed walkover &mdash; not a leg-over-the-pipe scramble. Tripping over a roof line is both a fall hazard and a risk to the line itself.",
  "The duty to provide safe access is continuous, so a compliant crossover has to be in place wherever the path of travel crosses an obstruction. OSHA cites it on inspection, and on the structural side corroded roof-access platforms and walkways get flagged on Milestone and county recertifications.",
  "We design and fabricate compliant crossover stairs and bridge platforms &mdash; guardrailed, slip-resistant, and engineered to clear the line &mdash; so crews cross gas, water and conduit runs safely instead of over them.",
  ""),
]

# SEO topic guides — show in the guides index + sitemap, NOT the landing hazard gallery
TOPICS = [
 ("florida-recertification","Florida Building Recertification &amp; Milestone Inspections","FL §553.899","Hot",
  "When your building's recert is due &mdash; and the repairs it triggers.",
  "Florida's recertification laws run separate from OSHA, but they flag the same conditions. The statewide <strong>Milestone</strong> program (FS 553.899) requires residential condos and co-ops <strong>three habitable stories or more</strong> to pass a structural inspection, and Miami-Dade and Broward run their own county <strong>building-safety recertification</strong> (structural <em>and</em> electrical). The reviewing engineer documents spalling walkways, corroded railings, failed waterproofing and loose anchors &mdash; the exact walking-working-surface conditions OSHA also cites.",
  "The statewide milestone comes due by the year a building turns <strong>30</strong> (a local building official may require it at <strong>25</strong> for buildings near salt water), then every 10 years. The county programs run on their own clock &mdash; Miami-Dade at <strong>30 years</strong> (25 near the coast) and Broward at <strong>25 years</strong>, then every 10 &mdash; and once an engineer flags deficiencies the repair plan carries its own deadline.",
  "Concrete restoration is our core trade. La Gala self-performs the structural concrete, balcony, walkway, waterproofing and railing repairs the recertification requires &mdash; coordinated with the engineer's report &mdash; so your building passes and stays safe.",
  ""),
 ("fixed-ladder-2036","The Fixed-Ladder 2036 Deadline","§1910.28(b)(9)","Hot",
  "Cages out, fall-arrest in &mdash; by Nov 18, 2036.",
  "The rule changed. Under OSHA §1910.28(b)(9), every <strong>new</strong> fixed ladder over 24 feet (installed since Nov 19, 2018) must carry a personal fall-arrest or ladder-safety system &mdash; a cage no longer counts &mdash; and <strong>by November 18, 2036 every</strong> fixed ladder over 24 ft must have one. Older caged ladders across South Florida are on the clock.",
  "The hard date is <strong>November 18, 2036</strong>, when every fixed ladder over 24 ft must have a fall-arrest or ladder-safety system. New ladders and any replaced section must comply now; an existing caged ladder is compliant until then, but retrofitting early beats the 2036 rush.",
  "We retrofit fixed ladders with compliant ladder-safety or personal fall-arrest systems, replace corroded rails, rungs and landing platforms, and bring rooftop and mechanical access in line with the standard &mdash; well before 2036 becomes a scramble.",
  ""),
 ("four-foot-rule","The OSHA 4-Foot Rule","§1910.28","Warm",
  "Why 4 feet is the general-industry fall trigger.",
  "In general industry the fall-protection trigger is just <strong>4 feet</strong> &mdash; not the 6 feet most people assume from construction. OSHA §1910.28 requires protection for any worker on a walking-working surface with an unprotected side or edge 4 feet or more above a lower level. Mezzanines, loading docks, roof access, pits and elevated walkways all qualify.",
  "The duty is continuous &mdash; there is no inspection interval; protection simply has to be in place whenever the exposure exists. It's a core target of OSHA's fall-protection emphasis program, so an inspector can cite an unprotected 4-foot edge the moment they see it.",
  "We assess every surface against the 4-foot rule and install the right protection &mdash; compliant guardrail, hole covers, designated-area systems, or certified anchors and tie-offs &mdash; then document it for your compliance file.",
  ""),
 ("osha-penalties","2026 OSHA Penalty Amounts","Penalties","Hot",
  "What a Subpart D citation actually costs in 2026.",
  "A Walking-Working Surfaces citation isn't a slap on the wrist. For 2026, OSHA's civil penalties run up to <strong>$16,550 per serious violation</strong>, the same amount <strong>per day</strong> for Failure-to-Abate past the deadline, and up to <strong>$165,514</strong> for a willful or repeat violation. Stack a few items on one inspection and the number climbs into six figures &mdash; before injury liability or the insurance fallout.",
  "Penalties attach <strong>per violation</strong>, not per inspection, so multiple cited items add up. Failure-to-Abate accrues for <strong>each day</strong> past the abatement date. A <strong>Repeat</strong> classification &mdash; the same standard cited again &mdash; is where the figure explodes. OSHA adjusts these maximums for inflation in most years, so they tend to climb.",
  "The cheapest penalty is the one you never get. We close open citations correctly the first time &mdash; sealed certification plus self-performed repair, documented for abatement &mdash; and keep you ahead with a recurring inspect-and-maintain plan, so a closed citation never reopens as a Repeat.",
  "",(("payments","The numbers"),("calculate","How the math works"),("verified_user","How we keep you ahead"))),
 ("inspection-checklist","Free OSHA Subpart D Inspection Checklist","Free download","Hot",
  "The field checklist we inspect against &mdash; yours to download.",
  "","","",""),
 ("is-my-building-exposed","Is My Building Exposed? A 2-Minute Self-Check","Self-check","Hot",
  "Five questions that tell you whether you're carrying an OSHA Subpart D violation right now.",
  "Walk your property and answer honestly: <strong>(1)</strong> Is every roof or balcony edge where someone could fall 4+ feet guarded or anchored? <strong>(2)</strong> Are your rooftop tie-off and window-washing anchors load-tested and certified within the last 10 years, with paperwork on file? <strong>(3)</strong> Are walkways, stairs and ramps free of spalling, standing water and trip hazards? <strong>(4)</strong> Do fixed ladders over 24 ft have a cage or fall-arrest system? <strong>(5)</strong> Could you produce inspection and training records if an inspector asked today? A &ldquo;no&rdquo; or &ldquo;not sure&rdquo; on any one is a citable Subpart D gap.",
  "Each &ldquo;no&rdquo; is a likely violation &mdash; citation or not. OSHA's fall-protection emphasis program lets an inspector open an inspection with no complaint and no advance notice, and every gap is its own penalty (about $16,550 per serious violation, more per day past an abatement deadline). The buildings that get hit aren't unlucky &mdash; they're the ones that never ran this check.",
  "We turn the self-check into a documented, PE-sealed inspection, then self-perform the corrections &mdash; guardrail, anchors, concrete, drainage &mdash; to the engineer's spec, and hand you abatement-ready paperwork. One team, one contract. Start with a comprehensive assessment.",
  "",(("fact_check","The 2-minute self-check"),("warning","What a &ldquo;no&rdquo; really means"),("verified_user","How we close the gaps"))),
 ("fall-protection-emphasis-program","OSHA's Fall-Protection Emphasis Program, Explained","Enforcement","Warm",
  "Why an inspector can open a fall-protection case on your building with no complaint and no advance notice.",
  "OSHA runs a National Emphasis Program on falls (CPL 03-00-025) plus regional programs that direct inspectors to prioritize fall hazards. Fall protection is the most-cited area on OSHA's Top 10 list year after year, and it applies in general industry, not just construction. Under an emphasis program, fall hazards are a programmed inspection target, not just something OSHA reacts to after a complaint or an accident.",
  "It means an inspector doesn't need a worker complaint or an injury to open a case. If a compliance officer is on site for any reason &mdash; or even observes a hazard in plain view, like an unguarded roof edge or workers without tie-offs &mdash; fall protection is fair game. The first many owners hear of it is the citation, with an abatement deadline already attached.",
  "You can't control when OSHA shows up &mdash; only what they find. A proactive PE-sealed inspection closes the gaps before they're cited and puts documentation on file. Our PE partner certifies it and our crews fix it, under one contract. Get a comprehensive assessment to find out where you stand.",
  "",(("gavel","What the emphasis program is"),("visibility_off","Why there's no heads-up"),("shield","How to stay ahead of it"))),
 ("osha-fall-protection-fines","OSHA Fall-Protection Fines in 2026","Penalties","Hot",
  "What an unprotected edge or missing tie-off actually costs.",
  "Fall protection is the most-cited area in all of OSHA enforcement, and the fines are not symbolic. For 2026 a single <strong>serious</strong> fall-protection violation runs up to <strong>$16,550</strong>, and because OSHA penalizes <strong>per violation</strong>, one walkthrough that flags an unguarded roof edge, a missing tie-off and an uncertified anchor can stack into five figures fast &mdash; before any injury or insurance fallout.",
  "OSHA cites fall hazards under Subpart D and the General Duty Clause, and an inspector doesn't need a complaint to do it &mdash; fall protection is a programmed emphasis-program target they can act on once they see an exposure 4 feet or more above a lower level. Penalties escalate from Serious to <strong>Willful or Repeat</strong> (up to $165,514), and Failure-to-Abate adds the serious amount again for <strong>each day</strong> past the deadline.",
  "The only fine you can fully control is the one you never receive. La Gala closes fall-protection gaps under one contract &mdash; PE-sealed inspection, then self-performed guardrail, anchor and edge work &mdash; and documents the abatement the way OSHA wants to see it, so you hold proof the hazard was corrected. Start with a comprehensive assessment.",
  "",(("payments","What the fines run in 2026"),("gavel","How a fine becomes a bigger fine"),("verified_user","How to take the fine off the table")),"osha-penalties"),
 ("cost-of-osha-citation","What an OSHA Walking-Surface Citation Really Costs","Penalties","Warm",
  "The fine is only the first line on the bill.",
  "Building owners fixate on the headline penalty &mdash; up to about <strong>$16,550</strong> per serious Subpart D violation &mdash; but the citation itself is the cheapest part. The real cost is the <strong>abatement work</strong> on a forced deadline, the legal and administrative time to respond, higher workers-comp and liability premiums, and the business disruption of a stop-work or re-inspection.",
  "A citation arrives with an abatement date, and missing it triggers <strong>Failure-to-Abate</strong> penalties that accrue per day. If the same hazard is ever cited again it becomes a <strong>Repeat</strong> &mdash; up to $165,514 &mdash; and a documented OSHA history follows you into insurance renewals and contractor prequalification. One serious injury from the same hazard dwarfs all of it.",
  "Handling it correctly the first time is far cheaper than handling it twice. We scope the full cost up front, self-perform the repairs to the engineer's spec, and hand you an abatement package built to close the citation cleanly &mdash; so the same hazard doesn't come back as a Repeat.",
  "",(("receipt_long","The full bill, not just the fine"),("event_busy","Where the costs compound"),("savings","How we keep the total down")),"damaged-surfaces"),
 ("repeat-willful-violations","OSHA Repeat &amp; Willful Violations, Explained","Penalties","Warm",
  "Where a $16K fine turns into a $165K one.",
  "Not all OSHA violations are priced the same. A <strong>Serious</strong> violation tops out around $16,550, but a <strong>Repeat</strong> (the same or a substantially similar standard cited again) or a <strong>Willful</strong> violation (knowing, or with plain indifference) jumps to as much as <strong>$165,514</strong> each &mdash; a 10x multiplier on the very same hazard.",
  "The classification is set by OSHA, and walking-working-surface items are common Repeat candidates because the same spalled walkway or uncertified anchor tends to resurface. A prior final citation is what arms the Repeat designation &mdash; OSHA generally looks back five years, though courts have allowed longer. These maximums are also adjusted for inflation in most years.",
  "Avoiding the multiplier comes down to two things: correct the hazard completely, and keep it corrected. La Gala self-performs durable repairs and pairs them with a recurring inspect-and-maintain plan, so a closed citation stays closed and never escalates into Repeat territory.",
  "",(("trending_up","The 10x classifications"),("history","Why Subpart D items repeat"),("shield","How to never see a Repeat")),"unprotected-edges"),
 ("condo-hoa-compliance","OSHA Walking-Surface Compliance for Condos &amp; HOAs","FL Condo/HOA","Hot",
  "Why associations carry OSHA exposure most boards never consider.",
  "Condo and HOA boards focus on the Florida Building Code and milestone inspections, but the moment the association directs <strong>any</strong> work on walking surfaces &mdash; staff, a handyman, or a contractor on the roof, balconies or catwalks &mdash; OSHA's general-industry walking-working-surface rules apply. Unguarded roof edges, uncertified rope-descent anchors for window washing, and deteriorated walkways are all citable Subpart D conditions on association property.",
  "There's no inspection interval that makes the duty appear or disappear &mdash; the hazard is citable whenever the exposure exists, and a worker injury or complaint is the usual trigger. For Florida associations it overlaps directly with milestone and county building-safety recertification findings, so the same spalling and corrosion get flagged from two directions at once.",
  "We give boards one accountable partner: a PE-sealed walking-surface inspection, self-performed concrete, railing, waterproofing and anchor repairs, and clean documentation for the association's records and the milestone engineer. One contract, one point of contact for the whole board.",
  "",(("apartment","Why associations are exposed"),("event_repeat","How it overlaps milestone rules"),("groups","How we work with boards")),"florida-recertification"),
 ("miami-dade-roof-anchors","Miami-Dade Roof Anchor &amp; Tie-Off Requirements","§1910.27","Warm",
  "What rooftop anchors a South-Florida building actually needs certified.",
  "Any South-Florida building where workers suspend from the roof to clean windows or service the façade needs <strong>certified anchorage</strong>. OSHA §1910.27 requires rope-descent-system (RDS) anchorages to be identified, tested, certified and maintained to hold at least 5,000 lb per worker &mdash; and in the Miami-Dade and Broward high-rise environment, salt air and sun accelerate the corrosion that makes an old anchor unsafe. (Anchors used only as fall-arrest tie-offs fall under §1910.140 instead.)",
  "RDS anchorages must be inspected <strong>annually by a qualified person</strong> and <strong>certified at least every 10 years</strong> under §1910.27(b) &mdash; sooner if an inspection finds a problem &mdash; and the building owner must keep that on file and give it to every contractor before work begins. Coastal exposure often means anchors need attention well before the 10-year mark.",
  "Our licensed Florida PE partner load-tests and certifies your anchors, and La Gala installs or replaces non-compliant ones &mdash; tagged, logged and photographed &mdash; so your rooftop is documented and ready for any window-washing or maintenance crew. One contract covers the test and the fix.",
  "",(("anchor","What needs certifying"),("schedule","The 10-year certification clock"),("construction","How we test and install")),"roof-anchors"),
 ("florida-milestone-inspection-osha","Florida Milestone Inspections &amp; OSHA Subpart D","FL §553.899","Hot",
  "How the milestone engineer's findings become OSHA repairs.",
  "Florida's <strong>Milestone Inspection</strong> law (FS 553.899) requires residential condos and co-ops <strong>three habitable stories or more</strong> to pass a structural inspection, and the reviewing engineer documents the exact conditions OSHA also cites &mdash; spalling walkways, corroded railings, failed waterproofing and loose rooftop anchors. The milestone report effectively hands you a list of Subpart D hazards in writing.",
  "The first milestone comes due by the year the building turns <strong>30</strong> (a local official may require it at <strong>25</strong> for buildings near salt water), then repeats every 10 years; in Miami-Dade and Broward the county building-safety recertification (which also covers electrical) applies on its own 25- to 30-year schedule. Once an engineer flags deficiencies, the repair plan carries its own deadline &mdash; and an unaddressed report is both a structural and an OSHA liability.",
  "Concrete restoration is our core trade. La Gala self-performs the structural concrete, balcony, walkway, waterproofing and railing repairs the milestone requires &mdash; coordinated with your engineer &mdash; so the building passes recertification and clears the walking-surface hazards in one pass.",
  "",(("description","What the milestone flags"),("event","The 30-year clock"),("construction","How we close the report")),"ramps-walkways"),
 ("parking-garage-safety","Parking-Garage Walking-Surface Compliance","§1910.22","Warm",
  "Decks, ramps and edges that quietly fail Subpart D.",
  "Parking structures are walking-working surfaces under OSHA, and they age hard: <strong>spalling concrete decks</strong>, cracked ramps, standing water from clogged drains, low-traction painted surfaces and unguarded perimeter edges and floor openings are all citable §1910.22 and §1910.28 conditions &mdash; and they're exactly what deteriorates first in a humid, salt-laden climate.",
  "The surface has to be kept clean, orderly, drained and in good repair, and any edge with a 4-foot-plus drop needs guarding &mdash; with no inspection interval that excuses a gap. Garages also feed milestone and county recertification findings, so problems get flagged from multiple directions.",
  "La Gala restores garage decks and ramps, fixes the drainage and waterproofing that drive the hazards, and brings perimeter guardrail and openings into compliance &mdash; self-performed and documented, so the structure is safe and inspection-ready.",
  "",(("local_parking","Why garages fail"),("priority_high","The conditions OSHA cites"),("construction","How we restore them")),"standing-water"),
 ("warehouse-dock-safety","Warehouse &amp; Loading-Dock Fall Protection","§1910.28","Warm",
  "The 48-inch drop nobody guards until someone falls.",
  "A loading dock is a classic <strong>4-foot fall hazard</strong> hiding in plain sight: an open dock door with a 48-inch drop to grade is an unprotected edge under OSHA §1910.28, and dockboards, mezzanine edges, pits and elevated walkways in the same building stack more exposure on top.",
  "Fall protection is required wherever a walking surface has an unprotected side or edge <strong>4 feet or more</strong> above a lower level &mdash; a continuous duty with no inspection interval. Docks are high-traffic and high-visibility, which makes them an easy citation if a compliance officer is ever on site.",
  "We assess every dock, mezzanine and edge against the 4-foot rule and install the right fix &mdash; gates, guardrail, hole covers or designated-area systems &mdash; plus repair worn dockboards and dock-edge concrete, all self-performed and documented for your file.",
  "",(("warehouse","The hidden dock hazard"),("straighten","Where the 4-foot rule applies"),("construction","How we protect it")),"dockboards"),
 ("retail-rooftop-units","Rooftop HVAC Access &amp; Fall Protection for Retail","§1910.28","Warm",
  "Strip-center roofs that fail the moment a tech goes up.",
  "Strip centers and retail buildings put HVAC, refrigeration and utilities on low-slope roofs, and every time a technician goes up to service them they're on a walking-working surface near an <strong>unprotected roof edge</strong>. Units close to an edge, skylights, hatches and pipe crossovers are all citable §1910.28 fall hazards on retail property.",
  "OSHA's low-slope roof rules (§1910.28(b)(13)) are distance-based: work <strong>within 6 ft</strong> of the edge always needs conventional fall protection; <strong>6&ndash;15 ft</strong> needs protection too (a designated area is allowed only for infrequent, temporary work); and <strong>beyond 15 ft</strong> you still must enforce a work rule keeping crews back from the edge. Multi-tenant retail roofs see frequent vendor traffic, which raises the odds someone is exposed on any given day.",
  "La Gala adds the right rooftop protection &mdash; guardrail or designated-area systems at the units, certified tie-off anchors, and covers for skylights and hatches &mdash; and certifies it through our PE partner, so every service visit is compliant. One contract for the inspection and the install.",
  "",(("storefront","Why retail roofs are exposed"),("ac_unit","The units that trigger it"),("construction","How we make access safe")),"rooftop-crossover"),
 ("guardrail-requirements","OSHA Guardrail Height &amp; Strength Requirements","§1910.29","Warm",
  "42 inches, 200 pounds &mdash; and why most rails miss.",
  "A guardrail only counts if it meets the numbers. OSHA §1910.29 requires a top rail <strong>42 inches</strong> (plus or minus 3) above the walking surface, a midrail <strong>midway</strong> (about 21 in), and a top rail that withstands at least <strong>200 pounds</strong> of downward or outward force &mdash; without deflecting below <strong>39 inches</strong> under that load. A lot of older or improvised railings quietly fail these.",
  "The requirement is dimensional and continuous &mdash; there's no interval, the rail simply has to meet the criteria wherever fall protection is provided by guarding. Corrosion, impact damage and non-compliant retrofits are what turn a rail that looks fine into a citable one.",
  "We measure existing rails against the §1910.29 criteria and fabricate or repair compliant guardrail, handrail and stair-rail systems &mdash; built to the height and strength the standard requires and documented for your compliance file.",
  "",(("straighten","The 42-inch / 200-lb criteria"),("rule","Why rails fail the test"),("construction","How we bring them to code")),"guardrail-systems"),
 ("rope-descent-recertification","Rope-Descent (Window-Washing) Anchor Recertification","§1910.27","Warm",
  "The 10-year clock on every rooftop window-washing anchor.",
  "If a building uses a rope descent system &mdash; the rigging window washers and façade crews suspend from &mdash; OSHA §1910.27 makes the <strong>building owner</strong> responsible for the anchorages. Each anchorage must be identified, tested, certified and maintained to hold at least 5,000 lb per worker, and the owner has to give every contractor written assurance the anchors are sound before work begins.",
  "The hard requirement is an <strong>annual inspection by a qualified person</strong> plus <strong>certification at least every 10 years</strong> (sooner if a problem turns up), and in South Florida's salt-air environment anchors often degrade faster than that. No certification on file means no compliant rope-descent work &mdash; and direct owner liability if a crew rigs to an untested anchor.",
  "Our licensed Florida PE partner load-tests and recertifies your rope-descent anchorages, and La Gala repairs or replaces any that fail &mdash; tagged, logged and photographed &mdash; so you can hand any window-washing contractor current paperwork. One contract for the test and the fix.",
  "",(("cleaning_services","Who's responsible"),("schedule","The 10-year recert rule"),("verified_user","How we certify and document")),"window-washing"),
 ("roof-anchor-recert-frequency","How Often Must Roof Anchors Be Recertified?","§1910.27","Hot",
  "The straight answer: it depends on how the anchor is used.",
  "It's the question every building owner eventually asks, and the answer depends on the anchor's use. <strong>Rope-descent-system (RDS) anchorages</strong> &mdash; the ones crews suspend from for window-washing and façade work &mdash; must be inspected <strong>annually by a qualified person</strong> and <strong>certified at least every 10 years</strong> under §1910.27(b), sooner if an inspection finds a problem. Anchors used only as <strong>fall-arrest tie-offs</strong> follow §1910.140 instead: inspected <strong>before each use</strong>, with periodic checks per the manufacturer and ANSI Z359.",
  "For RDS anchorages the 10-year certification is the maximum interval, not a target; coastal corrosion, roof work, or any damage demands a fresh test, and the annual inspection is non-negotiable. The owner must keep the records on file and provide them to contractors &mdash; missing paperwork is itself the violation, even on a sound anchor.",
  "La Gala and our PE partner put your anchors on a documented schedule &mdash; load-tested, certified and tagged, with the records you need on hand &mdash; and replace any that don't pass. We make the recert a routine line item instead of a scramble before a window-washing job.",
  "",(("schedule","How often, by anchor type"),("checklist","What resets the clock"),("event_repeat","How we keep you current")),"roof-anchors"),
 ("1910-28-explained","OSHA 1910.28 Fall Protection, in Plain English","§1910.28","Warm",
  "The core fall-protection rule for general industry.",
  "Section <strong>1910.28</strong> is the heart of OSHA's walking-working-surfaces fall protection: it requires employers to protect workers from falling off any walking-working surface with an unprotected side or edge <strong>4 feet or more</strong> above a lower level, and from falling into holes and openings. It reaches roofs, mezzanines, docks, pits, runways, stairs and ladders alike.",
  "Acceptable protection includes guardrail systems, safety-net systems, and personal fall-arrest systems &mdash; chosen for the situation &mdash; and the duty is continuous wherever the exposure exists. Low-slope roof work has its own distance-based rules (within 6 ft, 6&ndash;15 ft, and beyond 15 ft of the edge), and skylights and holes 4 ft or more above a lower level must be protected by a cover, guardrail, travel-restraint or fall-arrest system.",
  "We translate §1910.28 into a concrete plan for your building: identify every 4-foot-plus exposure, install the right protection, certify anchors through our PE partner, and document it &mdash; one contract from assessment to sign-off.",
  "",(("menu_book","What 1910.28 says"),("checklist","How it's satisfied"),("construction","How we apply it to your building")),"roof-edge-exposure"),
 ("what-to-expect-osha-inspection","What to Expect During an OSHA Inspection","Enforcement","Warm",
  "The walkthrough, the citation window, and your clock.",
  "An OSHA inspection usually moves in three steps: an <strong>opening conference</strong> where the compliance officer states the reason, a <strong>walkaround</strong> of the site, and a <strong>closing conference</strong>. For walking-working surfaces, the officer can cite anything in plain view &mdash; an unguarded edge, a spalled walkway, an uncertified anchor &mdash; without needing a complaint.",
  "Citations can be issued up to <strong>six months</strong> after the violation occurs (OSH Act §9(c)), and each arrives with a proposed penalty and an <strong>abatement deadline</strong>. Miss that date and Failure-to-Abate penalties accrue per day; the smartest position is to have your documentation ready before the officer ever arrives.",
  "We get you inspection-ready ahead of time &mdash; a PE-sealed walking-surface review, corrected hazards, and an organized compliance file &mdash; and if a citation does land, we close it correctly with self-performed repair and abatement paperwork. Start with a comprehensive assessment.",
  "",(("badge","The three-step inspection"),("schedule","Citations and your deadline"),("verified_user","How to be ready first")),"housekeeping"),
 ("annual-fall-protection-inspection","Annual Fall-Protection Inspection Requirements","§1910.140","Warm",
  "What has to be checked, and how often.",
  "Fall-protection gear and anchors aren't install-and-forget. OSHA requires personal fall-arrest equipment to be inspected <strong>before each use</strong> (and removed from service when defective or after any fall), and rope-descent anchorages to be inspected annually and <strong>certified at least every 10 years</strong>. OSHA itself sets no fixed annual interval for ordinary fall-arrest gear &mdash; that annual cadence comes from <strong>ANSI Z359</strong> and the manufacturer.",
  "Harnesses, lanyards and connectors get a documented periodic inspection &mdash; <strong>annually</strong> is the widely-followed ANSI Z359 / manufacturer practice, not an OSHA mandate &mdash; while RDS anchorages follow the 10-year certification clock. In a coastal climate, UV and salt shorten the life of webbing and hardware, so treat those intervals as maximums.",
  "La Gala sets up a documented inspect-and-maintain program &mdash; gear checks, anchor load tests and certifications through our PE partner, and the records to prove it &mdash; so your fall-protection system stays compliant year-round instead of lapsing between projects.",
  "",(("fact_check","What gets inspected"),("schedule","How often"),("event_repeat","How we keep it current")),"fixed-ladders"),
 ("compliance-calendar","OSHA &amp; Florida Compliance Calendar: What's Required &amp; How Often","Schedule","Hot",
  "Which inspections are required, how often, and the deadlines already on the clock.",
  "Compliance isn't one-and-done &mdash; once a hazard exists, keeping it in check is an ongoing duty. The cadence: <strong>fall-arrest gear</strong> (harnesses, lanyards, SRLs) is inspected <strong>before every use</strong> under §1910.140, with a documented check yearly (ANSI Z359 best practice). <strong>Rope-descent and window-washing anchors</strong> get a <strong>yearly</strong> qualified-person inspection and <strong>certification at least every 10 years</strong> (§1910.27(b)). <strong>Walking surfaces, guardrails, stairs and edges</strong> must be inspected &lsquo;regularly&rsquo; under §1910.22(d) &mdash; we recommend <strong>semi-annually</strong> (yearly at a minimum), and <strong>quarterly</strong> for parking decks and high-traffic coastal surfaces where salt air speeds the wear. Structural recertification runs on the building's age.",
  "<p class='font-semibold text-primary'>The five things that fail most on South-Florida buildings:</p><ol class='mt-3 space-y-3'><li><span class='font-bold text-primary'>1. Unprotected roof edges &amp; low-slope access</span> <span class='text-xs font-bold text-secondary'>§1910.28</span><br/>No guardrail or tie-off where crews reach rooftop HVAC, antennas or drains and a 4-ft-plus fall is possible.</li><li><span class='font-bold text-primary'>2. Corroded or uncertified rooftop anchors</span> <span class='text-xs font-bold text-secondary'>§1910.27</span><br/>Window-washing / rope-descent and tie-off anchors never load-tested, or rusted by salt air, with no certification on file.</li><li><span class='font-bold text-primary'>3. Spalling concrete walkways, balconies &amp; parking decks</span> <span class='text-xs font-bold text-secondary'>§1910.22</span><br/>Cracked, delaminated or trip-hazard surfaces &mdash; the classic coastal-Florida deterioration.</li><li><span class='font-bold text-primary'>4. Guardrails that miss the spec</span> <span class='text-xs font-bold text-secondary'>§1910.29</span><br/>Under 42&Prime; tall, or unable to take 200 lb of force &mdash; common on older or improvised rails.</li><li><span class='font-bold text-primary'>5. Caged fixed ladders not yet retrofitted</span> <span class='text-xs font-bold text-secondary'>§1910.28(b)(9)</span><br/>Still relying on a cage instead of a fall-arrest or ladder-safety system.</li></ol><p class='font-semibold text-primary mt-6'>The deadlines already on the clock:</p><ul class='mt-3 space-y-3'><li><span class='font-bold text-primary'>Right now</span> &mdash; new and replaced fixed ladders must already use a fall-arrest or ladder-safety system, and rope-descent anchors need a current (within-10-year) certification on file.</li><li><span class='font-bold text-primary'>Every year</span> &mdash; a qualified-person inspection of rope-descent anchorages; a documented Subpart D walkthrough and fall-gear check is the smart add-on.</li><li><span class='font-bold text-primary'>At the building&rsquo;s age</span> &mdash; the Florida Milestone at 30 years (a local official may require 25 near salt water), then every 10; plus Miami-Dade county recertification at 30/25 and Broward at 25, then every 10.</li><li><span class='font-bold text-primary'>November 18, 2036</span> &mdash; every fixed ladder over 24 ft must have a fall-arrest or ladder-safety system; cages no longer count.</li></ul>",
  "You can't track all of that building-by-building from a spreadsheet &mdash; so we do it for you. La Gala puts your property on a documented inspect-and-maintain schedule: gear and anchor checks, PE-sealed certifications through our engineering partner, walking-surface walkthroughs, and the records to prove every one &mdash; turning a pile of deadlines into one predictable line item. Start with a comprehensive assessment.",
  "",(("event_available","What's required &mdash; and how often"),("priority_high","The top 5 failures &amp; the deadlines"),("event_repeat","How we keep you on schedule")),"damaged-surfaces"),
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
<meta property="og:image" content="https://roofanchorcert.com/assets/wws/{img}.jpg"/>
<meta property="og:url" content="{canonical}"/>
<meta name="theme-color" content="#1a1a2e"/>
<link rel="icon" type="image/png" href="/assets/lagala-mark.png"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Manrope:wght@700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script>
  tailwind.config = {{ darkMode:"class", theme:{{ extend:{{
    colors:{{ primary:"#13233f","primary-container":"#1e3a5f",secondary:"#c9a227","secondary-container":"#e8c547","secondary-fixed":"#f0d060","on-secondary-fixed":"#3d2e00",steel:"#8b97a8",surface:"#f7f6f3","surface-container-low":"#f0eee8","surface-container-lowest":"#ffffff","surface-container-high":"#e8e5dd","on-surface":"#1a1a1a","on-surface-variant":"#54606f","outline-variant":"#dcd8cf","on-primary":"#ffffff" }},
    borderRadius:{{ DEFAULT:"0.625rem", lg:"0.875rem", xl:"1.25rem", "2xl":"1.5rem", full:"9999px" }},
    fontFamily:{{ headline:["Manrope"], body:["Inter"] }} }} }} }}
</script>
<style>body{{font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}}h1,h2,h3{{font-family:'Manrope',sans-serif;letter-spacing:-0.01em}}.material-symbols-outlined{{font-variation-settings:'FILL' 0,'wght' 400}}html{{scroll-behavior:smooth}}a,button{{transition:all .2s ease}}section.bg-primary,footer{{background-image:radial-gradient(90% 75% at 100% 0%,rgba(201,162,39,0.12),transparent 52%),linear-gradient(150deg,#13233f 0%,#1f3c63 100%)}}</style>
<link rel="preconnect" href="https://www.googletagmanager.com"/>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-K9ZEXRRMCK"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-K9ZEXRRMCK');</script>
</head>
<body class="bg-surface text-on-surface">
<div class="h-1 w-full bg-gradient-to-r from-secondary via-secondary-fixed to-secondary"></div>
<nav class="w-full sticky top-0 z-50 bg-[#f8f7f5]/80 backdrop-blur-md border-b border-outline-variant/20">
<div class="flex justify-between items-center px-6 sm:px-8 py-4 max-w-7xl mx-auto">
<a href="/" class="flex items-center" aria-label="La Gala Construction"><img src="/assets/lagala-logo.png" alt="La Gala Construction" class="h-10 sm:h-12 w-auto"/></a>
<div class="hidden md:flex items-center space-x-8">
<a class="text-primary opacity-80 hover:text-secondary transition-colors" href="/roof-anchor-certification">Roof Anchors</a>
<a class="text-primary opacity-80 hover:text-secondary transition-colors" href="/#schedule">Deadlines</a>
<a class="text-primary opacity-80 hover:text-secondary transition-colors" href="/#plans">Plans</a>
<a class="text-secondary font-semibold border-b-2 border-secondary pb-0.5" href="/guides">Guides</a>
<a class="text-primary opacity-80 hover:text-secondary transition-colors font-semibold" href="tel:+15614758615">(561)&nbsp;475-8615</a>
</div>
<a href="/#assessment" class="hidden md:inline-flex bg-secondary text-white px-5 py-2.5 rounded-xl font-semibold hover:bg-secondary-container hover:text-on-secondary-fixed transition-all whitespace-nowrap">Comprehensive Assessment</a>
<button id="navToggle" type="button" class="md:hidden p-2 -mr-1 text-primary" aria-label="Open menu" aria-expanded="false"><span class="material-symbols-outlined text-3xl">menu</span></button>
</div>
<div id="mobileMenu" class="hidden md:hidden border-t border-outline-variant/20 bg-surface-container-lowest px-6 pb-4 pt-1">
<a class="block py-2.5 text-primary font-medium border-b border-outline-variant/15" href="/roof-anchor-certification">Roof Anchors</a>
<a class="block py-2.5 text-primary font-medium border-b border-outline-variant/15" href="/#schedule">Deadlines</a>
<a class="block py-2.5 text-primary font-medium border-b border-outline-variant/15" href="/#plans">Plans</a>
<a class="block py-2.5 text-secondary font-semibold border-b border-outline-variant/15" href="/guides">Guides</a>
<a class="block py-2.5 text-primary font-semibold" href="tel:+15614758615">(561)&nbsp;475-8615</a>
<a href="/#assessment" class="block mt-3 text-center bg-secondary text-white py-3 rounded-xl font-semibold">Comprehensive Assessment</a>
</div>
</nav>
<script>
(function(){{var t=document.getElementById('navToggle'),m=document.getElementById('mobileMenu');if(!t||!m)return;function set(o){{m.classList.toggle('hidden',!o);t.setAttribute('aria-expanded',o?'true':'false');t.querySelector('span').textContent=o?'close':'menu';}}t.addEventListener('click',function(){{set(m.classList.contains('hidden'));}});m.querySelectorAll('a').forEach(function(a){{a.addEventListener('click',function(){{set(false);}});}});}})();
</script>
"""

FOOTER = """<footer class="w-full py-12 px-6 sm:px-8 flex flex-col items-center text-center space-y-5 bg-[#1a1a2e] text-[#f8f7f5]">
<a href="/" class="inline-block"><img src="/assets/lagala-logo.png" alt="La Gala Construction" class="h-11 w-auto" style="filter:brightness(0) invert(1)"/></a>
<p class="text-sm text-[#f8f7f5]/70 max-w-xl">Concrete Restoration &middot; Waterproofing &middot; Fall-Protection &amp; Compliance &mdash; South Florida.</p>
<div class="flex flex-wrap justify-center gap-6 text-sm"><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/guides">All guides</a><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/#plans">Build a plan</a><a class="text-[#f8f7f5]/60 hover:text-[#e8c547]" href="/#assessment">Comprehensive assessment</a></div>
<p class="text-xs text-[#f8f7f5]/50">25 SE 7th Street, Ste 12 &middot; Deerfield Beach, FL 33441 &middot; (561) 475-8615 &middot; danny@lagalacon.com</p>
<p class="text-xs text-[#f8f7f5]/40 max-w-3xl">La Gala Construction is a Florida State Certified General Contractor (CGC 059211). Engineering certifications referenced are performed and sealed by an independent, licensed Florida professional engineer; La Gala does not provide engineering services.{credit}</p>
<p class="text-sm text-[#f8f7f5]/60">&copy; 2026 La Gala Construction (Tilt Patchers, Inc.). Licensed &middot; Bonded &middot; Insured.</p>
</footer>
<script>(function(){function ev(n,p){try{if(typeof gtag==='function')gtag('event',n,p||{});}catch(e){}}document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a,button');if(!a)return;var h=a.getAttribute('href')||'';if(h.indexOf('tel:')===0)ev('phone_click',{});else if(h.indexOf('mailto:')===0)ev('email_click',{});else if(h.indexOf('#assessment')!==-1)ev('cta_click',{cta:'assessment'});else if(h.indexOf('#plans')!==-1)ev('cta_click',{cta:'plans'});else if(h.indexOf('/guides/')!==-1)ev('guide_open',{guide:h.split('/').pop()});},true);})();</script>
<script>(function(){try{document.querySelectorAll('.material-symbols-outlined').forEach(function(s){if(!s.hasAttribute('aria-hidden'))s.setAttribute('aria-hidden','true');});}catch(e){}})();</script>
<script defer src="https://va.vercel-scripts.com/v1/script.js" data-website-id="prj_LkelimAuti9JBNu5B8zB7Rr1ILON"></script>
</body></html>"""

def cta():
    return """<div class="bg-primary text-on-primary rounded-2xl p-8 sm:p-10 mt-12 text-center">
<h2 class="text-2xl sm:text-3xl font-extrabold">Got this on a citation — or want to get ahead of it?</h2>
<p class="text-on-primary/75 mt-3 max-w-2xl mx-auto">Our PE partner certifies it and our crews fix it, under one contract. Start with a comprehensive, no-obligation assessment, or build a custom compliance plan in two minutes.</p>
<div class="flex flex-wrap gap-4 justify-center mt-7">
<a href="/#assessment" class="bg-secondary text-white px-7 py-3.5 rounded-xl font-bold hover:bg-secondary-container hover:text-on-secondary-fixed transition-colors">Get a comprehensive assessment</a>
<a href="/#plans" class="border-2 border-secondary-fixed text-secondary-fixed px-7 py-3.5 rounded-xl font-bold hover:bg-secondary-fixed hover:text-on-secondary-fixed transition-colors">Build a plan</a>
</div></div>"""

def build_post(p):
    slug,title,std,temp,short,why,how,fix,credit = p[:9]
    secs = p[9] if len(p) > 9 and p[9] else (("priority_high","Why it matters"),("event_repeat","How often it's checked"),("construction","How La Gala fixes it"))
    img = p[10] if len(p) > 10 and p[10] else slug
    title_plain = title.replace("&amp;","&")
    import re as _re, json as _json
    meta = (_re.sub(r"<[^>]+>", "", (why or ""))[:150].rsplit(" ", 1)[0]) + "…"
    canon = f"https://roofanchorcert.com/guides/{slug}"
    head = HEAD.format(title_plain=title_plain, meta=meta, marker=MARKER, canonical=canon, img=img)
    _img = f"https://roofanchorcert.com/assets/wws/{img}.jpg"
    _ld = {"@context":"https://schema.org","@type":"Article","headline":title_plain,"description":meta,"image":_img,"author":{"@type":"Organization","name":"La Gala Construction"},"publisher":{"@type":"Organization","name":"La Gala Construction"},"mainEntityOfPage":canon}
    _bc = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Compliance guides","item":"https://roofanchorcert.com/guides"},{"@type":"ListItem","position":2,"name":title_plain,"item":canon}]}
    head = head.replace("</head>", '<script type="application/ld+json">'+_json.dumps(_ld)+'</script>\n<script type="application/ld+json">'+_json.dumps(_bc)+'</script>\n</head>')
    credit_html = f'<p class="text-xs text-on-surface-variant/60 mt-3 italic">{credit}.</p>' if credit else ""
    foot_credit = f" {credit}." if credit else ""
    art = f"""<main class="overflow-x-hidden">
<article class="max-w-3xl mx-auto px-6 sm:px-8 py-12">
<a href="/guides" class="text-sm font-semibold text-secondary hover:underline inline-flex items-center gap-1"><span class="material-symbols-outlined text-base">arrow_back</span> All compliance guides</a>
<div class="mt-5 flex items-center gap-3"><span class="text-xs font-bold bg-secondary text-white px-2.5 py-1 rounded-full">{std}</span><span class="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">{temp} lead item</span></div>
<h1 class="text-3xl sm:text-5xl font-extrabold text-primary leading-tight tracking-tight mt-4">{title}</h1>
<img src="/assets/wws/{img}.jpg" alt="{title_plain}" class="w-full rounded-2xl mt-8 shadow-lg aspect-[16/9] object-cover"/>
{credit_html}
<div class="prose mt-10 space-y-8">
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">{secs[0][0]}</span> {secs[0][1]}</h2><p class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{why}</p></section>
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">{secs[1][0]}</span> {secs[1][1]}</h2><div class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{how}</div></section>
<section><h2 class="text-2xl font-bold text-primary flex items-center gap-2"><span class="material-symbols-outlined text-secondary">{secs[2][0]}</span> {secs[2][1]}</h2><p class="text-on-surface-variant leading-relaxed mt-3 text-[17px]">{fix}</p></section>
</div>
{cta()}
</article>
</main>
"""
    return head + art + FOOTER.replace("{credit}", foot_credit)

def build_index():
    head = HEAD.format(title_plain="OSHA Walking-Working Surfaces — Compliance Guides", meta="The top 15 OSHA Walking-Working Surfaces violations explained — what each one is, how often it's inspected, and how La Gala Construction fixes it. South Florida.", marker=MARKER, canonical="https://roofanchorcert.com/guides", img="unprotected-edges")
    cards = ""
    for p in POSTS:
        slug,title,std,temp,short = p[0],p[1],p[2],p[3],p[4]
        img = slug
        cards += f"""<a href="/guides/{slug}" class="group bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/20 shadow-sm hover:shadow-lg hover:border-secondary transition-all flex flex-col">
<div class="aspect-[16/10] overflow-hidden"><img src="/assets/wws/{img}.jpg" alt="{title.replace('&amp;','&')}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/></div>
<div class="p-5 flex-1 flex flex-col"><span class="text-[11px] font-bold text-secondary">{std}</span><h3 class="font-bold text-primary mt-1 leading-tight">{title}</h3><p class="text-sm text-on-surface-variant mt-1.5 flex-1">{short}</p><span class="text-sm font-semibold text-primary mt-3 inline-flex items-center gap-1 group-hover:text-secondary">Read the guide <span class="material-symbols-outlined text-base">arrow_forward</span></span></div></a>"""
    topics = ""
    for tp in TOPICS:
        tslug,ttitle,tstd,tshort = tp[0],tp[1],tp[2],tp[4]
        topics += f"""<a href="/guides/{tslug}" class="group bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm hover:shadow-lg hover:border-secondary transition-all p-5 flex flex-col"><span class="text-[11px] font-bold text-secondary">{tstd}</span><h3 class="font-bold text-primary mt-1 leading-tight">{ttitle}</h3><p class="text-sm text-on-surface-variant mt-1.5 flex-1">{tshort}</p><span class="text-sm font-semibold text-primary mt-3 inline-flex items-center gap-1 group-hover:text-secondary">Read the guide <span class="material-symbols-outlined text-base">arrow_forward</span></span></a>"""
    downloads = """<section id="downloads" class="bg-surface-container-low border-y border-outline-variant/20 py-16 mt-4">
<div class="max-w-7xl mx-auto px-6 sm:px-8">
<div class="max-w-3xl"><span class="text-secondary font-semibold tracking-widest uppercase text-xs">Free downloads</span>
<h2 class="text-3xl font-extrabold text-primary leading-tight tracking-tight mt-3">Resources &amp; collateral.</h2>
<p class="text-lg text-on-surface-variant leading-relaxed mt-4">Hand these to your board, your safety committee, or your team &mdash; or self-audit before an inspector does.</p></div>
<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-10">
<a href="/collateral/OSHA_WWS_Flyer.pdf" target="_blank" rel="noopener" class="group bg-surface-container-lowest rounded-xl border border-outline-variant/20 p-6 hover:border-secondary hover:shadow-lg transition-all flex flex-col">
<span class="material-symbols-outlined text-4xl text-secondary">description</span>
<h3 class="font-bold text-primary mt-4">Program Flyer</h3>
<p class="text-sm text-on-surface-variant mt-1 flex-1">The one-page overview of the WWS compliance program.</p>
<span class="text-sm font-semibold text-primary mt-4 inline-flex items-center gap-1 group-hover:text-secondary">Download PDF <span class="material-symbols-outlined text-base">download</span></span></a>
<a href="/collateral/Free_Assessment_Offer.pdf" target="_blank" rel="noopener" class="group bg-surface-container-lowest rounded-xl border border-outline-variant/20 p-6 hover:border-secondary hover:shadow-lg transition-all flex flex-col">
<span class="material-symbols-outlined text-4xl text-secondary">redeem</span>
<h3 class="font-bold text-primary mt-4">Comprehensive Assessment Offer</h3>
<p class="text-sm text-on-surface-variant mt-1 flex-1">Our no-cost, no-obligation compliance assessment.</p>
<span class="text-sm font-semibold text-primary mt-4 inline-flex items-center gap-1 group-hover:text-secondary">Download PDF <span class="material-symbols-outlined text-base">download</span></span></a>
<a href="/collateral/Subpart_D_Inspection_Checklist_LaGala.pdf" target="_blank" rel="noopener" class="group bg-surface-container-lowest rounded-xl border border-outline-variant/20 p-6 hover:border-secondary hover:shadow-lg transition-all flex flex-col">
<span class="material-symbols-outlined text-4xl text-secondary">checklist</span>
<h3 class="font-bold text-primary mt-4">Inspection Checklist</h3>
<p class="text-sm text-on-surface-variant mt-1 flex-1">The Subpart D field checklist we inspect against (.22&ndash;.30).</p>
<span class="text-sm font-semibold text-primary mt-4 inline-flex items-center gap-1 group-hover:text-secondary">Download PDF <span class="material-symbols-outlined text-base">download</span></span></a>
<a href="/collateral/LaGala_WWS_Postcard_4x6_READY.pdf" target="_blank" rel="noopener" class="group bg-surface-container-lowest rounded-xl border border-outline-variant/20 p-6 hover:border-secondary hover:shadow-lg transition-all flex flex-col">
<span class="material-symbols-outlined text-4xl text-secondary">mail</span>
<h3 class="font-bold text-primary mt-4">4&times;6 Postcard</h3>
<p class="text-sm text-on-surface-variant mt-1 flex-1">Print-ready direct-mail card for outreach.</p>
<span class="text-sm font-semibold text-primary mt-4 inline-flex items-center gap-1 group-hover:text-secondary">Download PDF <span class="material-symbols-outlined text-base">download</span></span></a>
</div>
</div>
</section>"""
    body = f"""<main class="overflow-x-hidden">
<section class="max-w-7xl mx-auto px-6 sm:px-8 pt-14 pb-8">
<span class="text-secondary font-semibold tracking-widest uppercase text-xs">Compliance guides</span>
<h1 class="text-4xl sm:text-5xl font-extrabold text-primary leading-tight tracking-tight mt-3 max-w-3xl">The hazards OSHA cites most — explained.</h1>
<p class="text-lg text-on-surface-variant leading-relaxed mt-5 max-w-2xl">For each Walking-Working Surfaces hazard: what it is, why it matters, how often it's inspected or re-certified, and how we close it out. Click any one to read the guide.</p>
</section>
<section class="max-w-7xl mx-auto px-6 sm:px-8 pb-20"><div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">{cards}</div></section>
<section class="max-w-7xl mx-auto px-6 sm:px-8 pb-16"><h2 class="text-2xl font-extrabold text-primary mb-1">More compliance guides</h2><p class="text-on-surface-variant mb-6">Deadlines, rules and Florida-specific requirements worth knowing.</p><div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{topics}</div></section>
{downloads}
{('<section class="max-w-7xl mx-auto px-6 sm:px-8 py-20">'+cta()+'</section>')}
</main>
"""
    return head + body + FOOTER.replace("{credit}", "")

def build_checklist():
    head = HEAD.format(title_plain="Free OSHA Walking-Working Surfaces Inspection Checklist", meta="Download La Gala's free OSHA 1910 Subpart D field inspection checklist — the same one we audit against. Self-check your building before an inspector does. South Florida.", marker=MARKER, canonical="https://roofanchorcert.com/guides/inspection-checklist", img="damaged-surfaces")
    items = ["§1910.22 — General surface conditions, housekeeping &amp; drainage","§1910.23 — Portable &amp; fixed ladders","§1910.24 — Step bolts &amp; manhole steps","§1910.25 — Stairways","§1910.26 — Dockboards","§1910.27 — Rope descent systems &amp; anchorages","§1910.28 / .29 — Fall protection: duty &amp; criteria","§1910.30 — Training","Corrective-action summary log"]
    lis = "".join('<li class="flex items-start gap-3"><span class="material-symbols-outlined text-secondary text-xl">check_circle</span><span>'+it+'</span></li>' for it in items)
    body = f"""<main class="overflow-x-hidden">
<article class="max-w-3xl mx-auto px-6 sm:px-8 py-12">
<a href="/guides" class="text-sm font-semibold text-secondary hover:underline inline-flex items-center gap-1"><span class="material-symbols-outlined text-base">arrow_back</span> All compliance guides</a>
<div class="mt-5 flex items-center gap-3"><span class="text-xs font-bold bg-secondary text-white px-2.5 py-1 rounded-full">Free download</span></div>
<h1 class="text-3xl sm:text-5xl font-extrabold text-primary leading-tight tracking-tight mt-4">The free OSHA Subpart D inspection checklist.</h1>
<p class="text-lg text-on-surface-variant leading-relaxed mt-5">The same field checklist La Gala inspects against &mdash; every Walking-Working Surfaces standard, §1910.22 through .30, plus a corrective-action log. Download it and self-audit your building before an inspector does.</p>
<div class="bg-surface-container-low rounded-2xl border border-outline-variant/30 p-7 mt-8">
<h2 class="text-xl font-bold text-primary">What's inside</h2>
<ul class="mt-4 space-y-3 text-on-surface-variant text-[16px]">{lis}</ul>
</div>
<div class="mt-8">
<a href="/collateral/Subpart_D_Inspection_Checklist_LaGala.pdf" download class="inline-flex items-center gap-2 bg-secondary text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-secondary-container hover:text-on-secondary-fixed transition-colors"><span class="material-symbols-outlined">download</span> Download the checklist (PDF)</a>
</div>
<p class="text-sm text-on-surface-variant/70 mt-4">Free, no email required. This is a field compliance checklist only &mdash; anchorage load-test certification and any structural repair must be performed and sealed by a licensed Florida professional engineer.</p>
{cta()}
</article>
</main>
"""
    return head + body + FOOTER.replace("{credit}", "")

n=0
for p in POSTS:
    open(os.path.join(BLOG, p[0]+".html"), "w", encoding="utf-8", newline="").write(build_post(p))
    n+=1
for p in TOPICS:
    page = build_checklist() if p[0]=="inspection-checklist" else build_post(p)
    open(os.path.join(BLOG, p[0]+".html"), "w", encoding="utf-8", newline="").write(page)
    n+=1
open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8", newline="").write(build_index())
print(f"Generated {n} posts + index in wwslgc/guides/")
print("Posts:", ", ".join(p[0] for p in POSTS))

# ---- sync the landing-page gallery from the same POSTS (single source of truth) ----
def gallery_cards():
    # Curated TOP 5 — most-cited + most relevant to La Gala's South-FL condo/anchor niche.
    # (guide slug, title, std badge, short scope line, image slug = best-matching photo)
    TOP5=[
      ("damaged-surfaces","Spalling Concrete &amp; Walkways","§1910.22","Spalled concrete, exposed rebar, cracked balconies &amp; walkways.","damaged-surfaces"),
      ("roof-anchors","Uncertified Roof &amp; RDS Anchors","§1910.27","Window-washing &amp; tie-off anchors never load-tested or certified.","window-washing"),
      ("unprotected-edges","Unprotected Roof Edges","§1910.28","No guardrail or tie-off where a 4&nbsp;ft+ fall is possible.","unprotected-edges"),
      ("guardrail-systems","Non-Compliant Guardrails","§1910.29","Rails that miss the 42&Prime; height or 200&nbsp;lb strength.","guardrail-systems"),
      ("standing-water","Standing Water &amp; Drainage","§1910.22","Decks and walkways not kept dry or properly drained.","standing-water"),
    ]
    out=""
    for slug,title,std,short,img in TOP5:
        alt=title.replace("&amp;","&")
        out+=('<a href="/guides/'+slug+'" class="group bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/20 shadow-sm hover:shadow-lg hover:border-secondary transition-all">'
              '<div class="aspect-[4/3] overflow-hidden relative"><img src="/assets/wws/'+img+'.jpg" alt="'+alt+'" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>'
              '<span class="absolute top-2 right-2 text-[10px] font-bold bg-secondary text-white px-2 py-0.5 rounded-full">'+std+'</span></div>'
              '<div class="p-4"><h3 class="font-bold text-primary text-[15px] leading-tight">'+title+'</h3>'
              '<p class="text-xs text-on-surface-variant mt-1.5 leading-snug">'+short+'</p></div></a>')
    return out

LANDING=os.path.join(REPO,"wwslgc","index.html")
lc=open(LANDING,encoding="utf-8").read()
gstart='<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-5 mt-12">'
gend='<div class="mt-8"><a href="/guides"'
i=lc.index(gstart); j=lc.index(gend)
lc=lc[:i]+gstart+gallery_cards()+'</div>\n'+lc[j:]
lc=lc.replace("The top 15 things OSHA cites &mdash; and we fix.","The hazards OSHA cites most &mdash; and we fix.")
lc=lc.replace("Read all 15 compliance guides","Read all the compliance guides")
lc=lc.replace('href="/blog"','href="/guides"')
open(LANDING,"w",encoding="utf-8",newline="").write(lc)
print("Landing gallery synced:",len(POSTS),"cards")

# ---- sitemap for the wwslgc subdomain (landing + blog index + every guide) ----
BASEW="https://roofanchorcert.com"
import datetime as _dt
LASTMOD=_dt.date.today().isoformat()  # auto-fresh on every regen so crawlers see the real last-build date
sm_urls=[(BASEW+"/wwslgc","1.0","weekly"),(BASEW+"/roof-anchor-certification","0.9","weekly"),(BASEW+"/reroof-anchor-certification","0.9","monthly"),(BASEW+"/bee-access-dealer","0.8","monthly"),(BASEW+"/swing-stage-osha-training","0.8","monthly"),(BASEW+"/miami-roof-anchor-certification","0.8","monthly"),(BASEW+"/fort-lauderdale-roof-anchor-certification","0.8","monthly"),(BASEW+"/west-palm-beach-roof-anchor-certification","0.8","monthly"),(BASEW+"/guides","0.8","weekly")]+[(BASEW+"/guides/"+p[0],"0.7","monthly") for p in POSTS]+[(BASEW+"/guides/"+p[0],"0.7","monthly") for p in TOPICS]
sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for u,pr,cf in sm_urls:
    sm+='  <url><loc>'+u+'</loc><lastmod>'+LASTMOD+'</lastmod><changefreq>'+cf+'</changefreq><priority>'+pr+'</priority></url>\n'
sm+='</urlset>\n'
open(os.path.join(REPO,"wwslgc","sitemap-wws.xml"),"w",encoding="utf-8",newline="").write(sm)
print("Sitemap written:",len(sm_urls),"urls -> wwslgc/sitemap-wws.xml")
