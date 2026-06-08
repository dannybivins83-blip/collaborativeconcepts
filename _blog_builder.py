"""Build the /blog index + individual blog posts + sitemap updates.

Generates institutionally-formatted Florida real estate / construction
SEO-friendly long-form posts tied to the site's service pillars:
Development, Roof Consulting, Solar Exit, Operations Software, Florida Market.
"""
import os
import re
import textwrap
from datetime import datetime

REPO = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(REPO, "blog")
os.makedirs(BLOG_DIR, exist_ok=True)

BRAND = "Collaborative Concept"
BASE_URL = "https://collaborativeconceptsfl.com"

# ===========================================================================
# Category taxonomy used for filtering
# ===========================================================================
CATEGORIES = [
    ("development", "Development & Investing", "#0c4a6e"),
    ("roof",        "Roof Consulting",         "#7c5730"),
    ("solar",       "Solar Exit",              "#15803d"),
    ("ops",         "Operations & Software",   "#1b2a41"),
    ("market",      "Florida Market",          "#1a8a9e"),
]
CATEGORY_BY_KEY = {k: (label, color) for k, label, color in CATEGORIES}


# ===========================================================================
# Blog post definitions
# ===========================================================================
POSTS = [
    {
        "slug": "what-is-an-equity-partner-real-estate-jv",
        "category": "development",
        "date": "2026-05-28",
        "title": "What Is an Equity Partner in a Real Estate JV? A Florida Developer's Plain-English Guide",
        "excerpt": "Equity partners contribute 20-25% of a project's all-in cost (cash or unencumbered land), sit in second position behind the bank, and earn 50% of the back-end profit. Here's how the structure actually works.",
        "body": """
<p>Walk into a coastal Florida development deal and you'll hear three words repeatedly: <strong>equity partner</strong>. In the K5 / La Gala Construction model we operate inside &mdash; and the model we structure for our investor introductions &mdash; the equity partner is the financial spine of every project. This post explains what they actually do, what they actually get paid, and why the structure is biased to be safe for the equity side.</p>

<h2>The capital stack in one paragraph</h2>
<p>A typical $10M Florida coastal development is funded in three positions. The <strong>senior bank</strong> covers 75-80% of total project cost through a construction loan that the developer personally guarantees. The <strong>equity partner</strong> contributes 20-25% &mdash; in cash, or in the form of an unencumbered piece of land that they're rolling into the deal at appraised value. The <strong>developer</strong> contributes sweat equity: sourcing, design, packaging, bank relationships, the personal guarantee on the senior loan, and the GC execution.</p>

<h2>Why the equity partner gets paid first</h2>
<p>This is the part many first-time partners don't realize. At the back end &mdash; when the project sells &mdash; the bank gets paid off, then <em>the equity partner's full capital is returned before the developer earns a dollar</em>. Only after that does the remaining profit split, typically 50/50.</p>
<p>This ordering is intentional. The equity partner takes on capital risk (the money is committed for 12-24 months); the developer takes on execution risk (cost overruns, market timing, lender relationships). The waterfall protects the side that brought the cash.</p>

<h2>Cash or land?</h2>
<p>Land contributions are common when the partner already owns the parcel that's being developed. They contribute it at an agreed appraised value and that valuation becomes their equity basis. The advantage: contributing property to a partnership is typically <strong>not a taxable event</strong> under IRC &sect;721 &mdash; gain is deferred until the partnership eventually disposes of the property. For long-term Florida property owners with significant unrealized capital gains, this is materially better than a flat-cash sale.</p>

<h2>What can go wrong &mdash; and what protects you</h2>
<ul>
<li><strong>Cost overruns:</strong> contractually capped by the renovation budget; overage is the developer's problem, not the equity partner's.</li>
<li><strong>Cross-default with the senior loan:</strong> if the bank defaults the developer, the equity partner's note auto-matures and they can foreclose immediately.</li>
<li><strong>Personal guarantee from the developer:</strong> standard ask. The corporate entity is one backstop; the developer's name is the second.</li>
<li><strong>Builder's risk + general liability insurance with the equity partner named:</strong> covers fire, storm, contractor accidents.</li>
<li><strong>Right of first refusal at default:</strong> if the developer defaults, the equity partner can repurchase the property at the senior payoff and finish the project themselves.</li>
</ul>

<h2>Where Collaborative Concept fits</h2>
<p>We don't take an equity position. We <em>structure</em> the deal &mdash; sourcing the property, running the appraisal, drafting the option, profit-share, assignment, and protection riders &mdash; and assign the contract to the developer (typically La Gala Construction / K5 Investment Group) for a flat fee at closing. The seller and the equity partner each have independent counsel review every document before signing. Read more about our role on the <a href="/properties">Project Management page</a> or see the broader business model in the <a href="/">about</a> section.</p>
""",
    },
    {
        "slug": "florida-save-our-homes-portability-explained",
        "category": "market",
        "date": "2026-05-26",
        "title": "Florida Save Our Homes Portability: The $500,000 Tax Benefit That Follows You When You Downsize",
        "excerpt": "Long-term Florida homeowners sitting on Save Our Homes-capped assessments can port up to $500,000 of that benefit to a new homestead. Here's how it works and why it matters for any senior considering a sale.",
        "body": """
<p>If you've owned your Florida home for 20+ years and you're thinking about downsizing, the single most valuable benefit on the table isn't your sale price. It's a Florida-specific tax mechanism called <strong>Save Our Homes (SOH) portability</strong>, and it can save the right homeowner thousands of dollars per year for the rest of their life in a new home.</p>

<h2>What Save Our Homes does</h2>
<p>Florida's Save Our Homes amendment caps annual increases in <strong>assessed value</strong> on a homestead-claimed property at 3% per year (or the CPI, whichever is lower). Over 20-40 years, the gap between assessed value and market value compounds enormously. A long-term Lighthouse Point homeowner might have a $4M+ market-value home but a $1.27M assessed value &mdash; they pay property tax on the $1.27M number, not the $4M.</p>

<h2>What portability does</h2>
<p>When you sell that homestead and buy a new Florida homestead within two assessment years, you can <strong>port up to $500,000 of the difference between assessed and market value</strong> to the new property. The new home's assessed value starts <em>discounted by that ported amount</em>, dropping its tax bill significantly &mdash; sometimes by thousands of dollars per year &mdash; for as long as you own it.</p>

<h2>Worked example</h2>
<p>A widow has owned her Lighthouse Point home since 1985. Market value $4.5M, SOH-capped assessed value $1.27M &mdash; a $3.23M gap. She sells and buys a $1.5M condo in The Villages. Florida lets her port up to $500K of the SOH benefit. Her new condo's assessed value: $1.5M minus $500K = $1.0M. At ~1.8% millage, her property tax on the new condo is about $18,000/year instead of about $27,000/year &mdash; a $9,000-per-year saving that follows her until she stops owning the property.</p>

<h2>The deadline that catches people off-guard</h2>
<p>Portability has a clock. You must <strong>file a new homestead exemption (and a portability application, Form DR-501T) on the new property by March 1st of the second year</strong> following the sale of your prior homestead. Miss it and the benefit is lost. We've seen $9,000-per-year benefits walked away from because the new homestead paperwork wasn't filed timely.</p>

<h2>Where this matters for our investor introductions</h2>
<p>When we structure off-market acquisitions for long-term Florida sellers &mdash; the wholesale-style introductions documented on the <a href="/properties">Project Management page</a> &mdash; we always include a CPA referral and a Portability planning conversation. The cash from the sale is one number. The lifetime tax savings on the next homestead is a second, separate number, and it's frequently bigger than people realize.</p>
""",
    },
    {
        "slug": "hvhz-roof-permitting-broward-noa",
        "category": "roof",
        "date": "2026-05-24",
        "title": "HVHZ Roof Permitting in Broward & Miami-Dade: NOAs, BC Forms, and What Inspectors Actually Look For",
        "excerpt": "Florida's High-Velocity Hurricane Zone is the strictest residential roof code in the country. Here's the inspector-ready checklist for a clean HVHZ permit packet, NOA-driven product selection, and the BC forms you'll need.",
        "body": """
<p>Roofing a single-family home in Broward or Miami-Dade County means submitting one of the most thoroughly scrutinized residential permit packets in the United States. The High-Velocity Hurricane Zone (HVHZ) rules in the Florida Building Code chapter 16 push for products and assemblies that are <strong>tested and approved for hurricane wind loads</strong> &mdash; and they require a paper trail proving every material was installed to its approval.</p>

<h2>The four building blocks of an HVHZ packet</h2>
<ol>
<li><strong>Notice of Acceptance (NOA)</strong>: the product approval document issued by Miami-Dade Building Department for each major component (membrane, underlayment, fasteners, tile system, edge metal). The NOA defines exactly how that product is allowed to be installed.</li>
<li><strong>BC-01 through BC-06 forms</strong>: county-specific submittal forms covering the application data, system schedule, product schedule, wind-load calculations, and PE seal where required.</li>
<li><strong>Roof plan</strong>: drawing showing scope, dimensions, slopes, penetrations, and panel/tile pattern.</li>
<li><strong>Wood replacement unit prices</strong>: itemized sheet showing the per-board-foot or per-sheet pricing for decayed decking replacement found during tear-off (the homeowner pays for these as discovered, on top of the contract).</li>
</ol>

<h2>What inspectors actually look for</h2>
<ul>
<li><strong>Underlayment match to NOA</strong>: the NOA dictates which underlayment is approved with the membrane or tile. Switching to a different one voids the approval &mdash; even if the substitute is "equivalent."</li>
<li><strong>Fastener pattern</strong>: the NOA specifies fastener type, spacing, and embedment. Inspectors photograph nails at field and edges.</li>
<li><strong>Edge metal and flashings</strong>: must match NOA-approved products and dimensions; inspectors verify the metal is the gauge and shape on file.</li>
<li><strong>Self-adhered membranes on sloped roof</strong>: must achieve full primer/adhesion contact &mdash; failures here are the #1 reason tile re-roofs fail inspection.</li>
<li><strong>Permit posting</strong>: the permit card has to be on site and visible. Inspector won't perform the inspection without it.</li>
</ul>

<h2>How a clean permit packet shortens the job</h2>
<p>When we built the automated Permit Packet Builder for our roofing partner SeaBreeze Roofing &amp; Sheet Metal (FL CCC1328689 &middot; CVC57073), the goal was simple: take HVHZ packet assembly from a 4-hour manual exercise to 5-10 minutes of structured data entry. The system auto-fills BC-01/02/03/06 from a project record, pulls the right NOA into the packet based on the membrane and deck type, and produces a PE-seal-ready file &mdash; same format every inspector sees, every time.</p>

<p>If you'd like to engage us to consult on a tough HVHZ permit situation &mdash; insurance denial, code violation, recertification &mdash; reach out via the <a href="/contact">contact page</a>.</p>
""",
    },
    {
        "slug": "150k-inspection-concessions-luxury-waterfront",
        "category": "roof",
        "date": "2026-05-22",
        "title": "Why a 60-Year-Old Waterfront Home Loses $150,000 to Inspection Concessions (And How to Avoid It)",
        "excerpt": "On a $5M-plus luxury waterfront home with a 1965 build year, the realistic inspection-concession range is $150K-$250K. Here's what triggers those credits and the pre-listing workflow that eliminates them.",
        "body": """
<p>If you're selling a Lighthouse Point, Palm Beach, or Coral Gables waterfront home built before 1980 and listed above $5M, you're probably underestimating the inspection-concession line item by an order of magnitude. The "typical $25-50K" figure that residential agents quote is calibrated to inland suburban homes. Luxury waterfront concessions are routinely in the <strong>$150,000 to $250,000 range</strong> &mdash; and we've seen them top $400,000 on properties with a problem dock or seawall.</p>

<h2>The five line items that drive luxury inspection credits</h2>
<ul>
<li><strong>Roof condition</strong>: 1960s and 1970s tile roofs are typically past their useful life. Even if it's not leaking, a buyer's inspector will recommend a full replacement &mdash; $80K-$150K credit ask, sometimes higher with HVHZ rules.</li>
<li><strong>Dock and seawall</strong>: spalled concrete, exposed rebar, settlement at the cap. Marine engineering reports drive 5-figure to 6-figure credits.</li>
<li><strong>Impact glass and openings</strong>: a luxury buyer expects code-current impact windows and doors. A home with original 1970s glass loses a credit equal to the retrofit cost &mdash; often $75K-$150K on a 6,000+ sqft home.</li>
<li><strong>Electrical panel and aluminum wiring</strong>: aluminum branch wiring, Federal Pacific or Zinsco panels &mdash; insurance-disqualifying issues that buyers will not absorb.</li>
<li><strong>HVAC age</strong>: 15-year-old AC systems on a luxury home are a credit ask; buyers expect new high-SEER systems.</li>
</ul>

<h2>The pre-listing workflow that eliminates concessions</h2>
<p>The way to avoid this line item is to put an attorney-grade inspection report in the buyer's hands <em>before</em> they bring their own inspector. We engage a licensed Florida appraiser plus an independent inspection done by our partner roofer SeaBreeze Roofing &amp; Sheet Metal. The report includes:</p>
<ul>
<li>49+ photo record, organized by trade and zone</li>
<li>Roof, dock, seawall, mechanical, and electrical condition notes</li>
<li>HVHZ code compliance review</li>
<li>Itemized scope and ballpark remediation cost</li>
</ul>
<p>With that documentation in hand, the buyer has no information advantage. They can re-inspect if they want, but their inspector will be confirming what they've already seen. Concessions either drop to near-zero or get baked into a pre-negotiated discount on the contract price, eliminating the post-inspection re-negotiation drama.</p>

<h2>How this changes the math</h2>
<p>On a $5.5M listed waterfront home, a typical agent route nets the seller $4.4M-$4.8M after commissions and inspection concessions. With a pre-listing report and an off-market structured sale, the same seller can net $5.0M-$5.5M depending on the buyer pool. The delta is real and it's frequently larger than the buyer pool difference because the inspection drama doesn't happen.</p>

<p>Engage us to build a pre-listing report on the <a href="/contact">contact page</a>, or read about our broader project management approach on the <a href="/properties">Project Management page</a>.</p>
""",
    },
    {
        "slug": "pace-ygrene-solar-loan-florida-homeowner-options",
        "category": "solar",
        "date": "2026-05-20",
        "title": "PACE and Ygrene Solar Loans: What Florida Homeowners Can Actually Do When the Installer Disappears",
        "excerpt": "If your PACE-financed solar system never got PTO, the installer went bankrupt, or the system never produced what you were promised, you have more paths than the lender wants you to know about. Here's the playbook.",
        "body": """
<p>The PACE and Ygrene financing programs were marketed to Florida homeowners as a low-risk way to pay for solar with no upfront cost. For thousands of families they've turned into a 20-year secured debt obligation on a system that never worked, never got Permission to Operate (PTO), or was installed by a company that has since vanished. If you're one of those homeowners, you have more options than your loan paperwork suggests.</p>

<h2>How PACE and Ygrene actually work</h2>
<p>PACE (Property Assessed Clean Energy) and the Ygrene financing program place the debt directly on your property tax bill as a special assessment. That assessment has lien priority over your mortgage and survives a sale. This is what makes it so dangerous: even if you sell the home, the new buyer inherits the assessment (or you have to pay it off at closing). The lender's risk is near zero because their lien is bolted onto the tax roll.</p>

<h2>Common failure scenarios</h2>
<ul>
<li><strong>Installer bankrupt or vanished</strong>: the workmanship warranty is now worthless. The system itself may have a manufacturer warranty, but no one is honoring the labor or installation side.</li>
<li><strong>No PTO from the utility</strong>: the system was installed but never approved to feed the grid. You're paying the loan and your full electric bill.</li>
<li><strong>Underperforming system</strong>: actual production is a fraction of what was modeled in the sales pitch.</li>
<li><strong>Roof leaks caused by the install</strong>: penetrations done by an unlicensed sub or a roofer who didn't understand HVHZ flashing requirements.</li>
<li><strong>Predatory sale to senior</strong>: the homeowner didn't understand what they were signing, or signed under capacity-impaired circumstances.</li>
</ul>

<h2>The accountability paths Florida homeowners can actually pursue</h2>
<ol>
<li><strong>Document everything</strong>: photo the system, the inverter status, the meter readings, every contract page. The Florida Solar Exit Program produces this report formatted for attorneys.</li>
<li><strong>Florida Department of Financial Services</strong>: complaint against the lender for unfair practices.</li>
<li><strong>Florida Office of Financial Regulation</strong>: complaint against the installer or finance broker.</li>
<li><strong>Construction defect claim</strong>: if the install caused roof damage, your homeowner's insurance and any surviving installer bond may be on the hook.</li>
<li><strong>Florida Attorney General's office</strong>: consumer protection complaint, especially for senior-targeted sales.</li>
<li><strong>Class action and individual consumer-protection counsel</strong>: there are vetted Florida law firms specifically pursuing PACE/Ygrene cases.</li>
<li><strong>System removal and roof remediation</strong>: in many cases the right move is to physically remove the system and restore the roof, then pursue the financial remedy separately. SeaBreeze Roofing &amp; Sheet Metal (FL CCC1328689 &middot; CVC57073) is licensed to handle the removal.</li>
</ol>

<h2>The Florida Solar Exit Program</h2>
<p>We launched <a href="https://solarexit.collaborativeconceptsfl.com" rel="noopener">solarexit.collaborativeconceptsfl.com</a> to give Florida homeowners a single coordinated path through this mess: paid inspection report, self-help accountability playbook, attorney referrals to vetted counsel, and licensed remediation. We are <strong>not</strong> attorneys &mdash; we document, refer, and remediate. The legal work is done by counsel who specialize in this fact pattern.</p>

<p>If you're trapped in a failed solar finance situation, start at <a href="https://solarexit.collaborativeconceptsfl.com" rel="noopener">the Solar Exit site</a>.</p>
""",
    },
    {
        "slug": "lighthouse-point-waterfront-real-estate-deep-dive",
        "category": "market",
        "date": "2026-05-18",
        "title": "Lighthouse Point Waterfront: Why the North Grand Canal Justifies $1,000+ Per Square Foot",
        "excerpt": "Lighthouse Point is one of three South Florida residential markets where no-fixed-bridge ocean access meaningfully expands the buyer pool. The North Grand Canal is the premium location within that market. Here's why.",
        "body": """
<p>Lighthouse Point sits at the north end of Broward County's waterfront residential strip, bordered by Deerfield Beach to the north and Pompano Beach to the south. Its identity is built almost entirely on one fact: more than 18 miles of navigable canals connect directly to the Hillsboro Inlet, with <strong>no fixed bridges</strong> between most canal homes and the Atlantic Ocean. That single design feature is why the market commands a premium nearly twice the Broward County waterfront median.</p>

<h2>What "no fixed bridges" actually buys</h2>
<p>A fixed bridge with 25-30 feet of clearance excludes any vessel taller than that air draft. Most quality sportfish boats, sailboats, and motor yachts above 50 feet exceed this. By contrast, Lighthouse Point's canal system reaches the Hillsboro Inlet without forcing the boater under a single fixed bridge. The result: <strong>80-foot-plus yacht owners can keep their vessel at the dock</strong> in front of their house. That single fact expands the buyer pool from "high-net-worth Floridian" to "global UHNW yacht owner."</p>

<h2>The North Grand Canal premium</h2>
<p>Within Lighthouse Point, the North Grand Canal is the wider class &mdash; over 120 feet wide on most blocks, with deeper water and easier boat maneuvering. Properties on NE 44th, NE 45th, and NE 46th Streets sit on this canal and command a premium even within Lighthouse Point pricing.</p>

<h2>Recent comparable trades</h2>
<ul>
<li><strong>2271 NE 44th St</strong> &mdash; sold August 2022 at $2.8M with a premium 100-ft seawall (adjusted to 2026 dollars: roughly $3.8M).</li>
<li><strong>3030 NE 44th St</strong> &mdash; currently listed at $5.65M; sits at a confluence of the largest canal and the Intracoastal Waterway, the trophy lot on the street.</li>
<li><strong>4241 NE 23 Ter</strong> &mdash; sold April 2026 at $2.33M in the same Venetian Isles 3rd Section subdivision, inland of the canal.</li>
<li>New construction in the 5,000-6,000+ sqft range with full no-fixed-bridge access trades at <strong>$8M-$10M</strong>.</li>
</ul>

<h2>The "as-is" vs "renovated" pricing gap</h2>
<p>A 1965-built, 6,347 sqft home with a 2008 effective renovation year on the North Grand Canal carries a defensible as-is appraisal in the $4.8M-$5.2M range. The same home, professionally renovated to current luxury finishes and code, trades at $7.5M-$9M. The renovation arbitrage is what attracts developer buyers like K5 / La Gala Construction &mdash; and what makes off-market introductions to long-term owners so valuable when they're considering a sale.</p>

<h2>Tax exposure to know about</h2>
<p>When a property changes hands, the new owner loses any homestead exemption and Save Our Homes cap the previous owner had. For a $5M+ home, post-sale property taxes can jump to <strong>$75,000-$85,000 per year</strong> at Lighthouse Point's roughly 1.85% millage. This is a meaningful holding cost for any developer modeling a 6-12 month renovation hold, and a meaningful pitch point for any long-term owner-occupant considering portability planning on their downsizing move.</p>

<p>Read our companion post on <a href="/blog/florida-save-our-homes-portability-explained">Save Our Homes portability</a>, or see our <a href="/properties">Project Management approach</a> for putting these deals together.</p>
""",
    },
    {
        "slug": "off-market-wholesale-vs-listing-with-agent-florida",
        "category": "development",
        "date": "2026-05-16",
        "title": "Off-Market Sale vs. Listing With an Agent: The Real Math on a Luxury Florida Waterfront Home",
        "excerpt": "An agent's $5.5M listing price isn't $5.5M in your pocket. Here's the line-by-line breakdown of what a long-term Florida waterfront owner actually nets through both paths, and where the structured off-market deal beats the list every time.",
        "body": """
<p>The question every long-term Florida waterfront owner asks at some point: <em>"My agent says they can get $5.5M. Why would I take a $5M off-market offer?"</em> The honest answer requires walking through the line items that separate the listed price from the cash that ends up in your bank account at closing.</p>

<h2>What an agent's $5.5M actually nets</h2>
<p>On a $5.5M listed price for a 1960s-era Lighthouse Point waterfront home, the realistic deductions:</p>
<ul>
<li>Listing agent commission (3%): &mdash;$165,000</li>
<li>Buyer's agent commission (3%): &mdash;$165,000</li>
<li>Florida documentary stamp tax on deed (0.7%): &mdash;$38,500</li>
<li>Owner's title insurance, seller-paid in Florida: &mdash;$27,500</li>
<li>Closing / attorney / recording: &mdash;$12,000</li>
<li>Pre-list staging and repairs: &mdash;$25,000</li>
<li>Holding costs through 3-month average days-on-market: &mdash;$45,000</li>
<li><strong>Inspection concessions on a 60-year-old waterfront home: &mdash;$150,000 to $250,000</strong> (typical, not worst-case)</li>
</ul>
<p>Best case net to seller: <strong>$4,847,500</strong>. Realistic post-negotiation net: $4.4M to $4.8M. That's <em>before</em> any potential buyer-financing fall-through, which forces a relisting and resets the days-on-market clock.</p>

<h2>What the structured off-market deal nets</h2>
<p>An off-market structured deal at appraised value &mdash; the Collaborative Concept playbook &mdash; runs differently. The buyer is a vetted developer (typically La Gala Construction / K5 Investment Group). The price is the appraised value, set by a licensed Florida appraiser within 30 days of signing. No agent commissions. No inspection concessions. No pre-list staging. The seller is paid in two phases: a structured Phase 1 disbursement at funding closing (signing bonus, bridge, rent-back, ~$100K cash), then the remaining principal at the resale closing along with a profit-share kicker.</p>
<p>At a $5M appraisal: $5,000,000 principal plus a kicker of $270K-$2.5M depending on the resale outcome. Total seller lifetime payout: <strong>$5.27M to $7.5M</strong>.</p>

<h2>Why the off-market path beats the list at every realistic resale price</h2>
<p>Even at the lowest projected resale ($7M), the seller's lifetime payout from the off-market structured deal is $5.27M &mdash; already $470K to $870K above the agent route's best case net. And that's the floor. At a $9M resale (realistic for a well-renovated North Grand Canal property), the seller nets $6.24M.</p>

<h2>What you give up &mdash; and what you get</h2>
<p>The trade is real, and worth understanding:</p>
<ul>
<li><strong>Give up:</strong> open-market price discovery (you accept the appraised value, not what the highest bidder might pay).</li>
<li><strong>Get:</strong> no commissions, no inspection battle, no months of showings, no fall-through, and a profit-share on the developer's upside that captures the renovation arbitrage you couldn't capture on a sell-as-is listing.</li>
</ul>

<h2>The structure matters</h2>
<p>For this to be a fair trade you need: an appraisal contingency (you walk if the number is below a floor), a seller-carry note secured by a recorded 2nd-position mortgage on the home, a personal guarantee from the developer (not just the corporate entity), builder's risk and general liability insurance with the seller as additional insured, cross-default to the senior loan, and a right of first refusal at default to buy the property back. We document all of that on the <a href="/properties">Project Management</a> page.</p>
""",
    },
    {
        "slug": "company-cam-alternatives-jobsite-photo-documentation",
        "category": "ops",
        "date": "2026-05-14",
        "title": "Jobsite Photo Documentation: When a Custom Solution Beats a Monthly Subscription",
        "excerpt": "CompanyCam runs $15-30 per user per month. For a small roofing or construction operation, an in-house photo-doc system with the same auto-tagging, GPS, permit-packet, and insurance-claim workflow eliminates the seat fee and gives the operator ownership of the data.",
        "body": """
<p>CompanyCam is a category-defining product. It's the standard for jobsite photo documentation in residential trades, and for many operators it's worth every dollar. But once a contractor scales past 5-10 active users, the per-seat math starts to bite &mdash; and the data is hosted somewhere else. We built our <strong>SiteCam</strong> internal system to address both issues for our roofing and construction partners.</p>

<h2>What jobsite photo documentation actually needs to do</h2>
<ul>
<li><strong>Auto-tag by job</strong>: when a photo is taken, it's already attached to a job record without a second click.</li>
<li><strong>Auto-tag by phase</strong>: pre-construction, tear-off, dry-in, install, punch-list, final &mdash; visible at a glance.</li>
<li><strong>GPS stamp</strong>: address and lat/long embedded, so the photo can be authenticated as having been taken on the property.</li>
<li><strong>Timestamp</strong>: same.</li>
<li><strong>Direct-to-permit-packet flow</strong>: the photos that prove fastener pattern, edge metal, and dry-in coverage drop straight into the HVHZ permit packet for inspection.</li>
<li><strong>Direct-to-insurance-claim flow</strong>: the photos that document storm damage drop into a claim submission package the adjuster can open.</li>
<li><strong>Client-portal share</strong>: the homeowner sees the same photos the crew sees, with no extra step.</li>
</ul>

<h2>Why ownership of the data matters</h2>
<p>The photos a roofer takes on a 200-job-per-year operation represent a forensic-grade record of <em>every roof they've ever touched</em>. That dataset has real defensive value: insurance disputes, code-compliance challenges, manufacturer warranty claims, even litigation. When the data lives inside a third-party SaaS, the contractor has access only while they're paying for it. When the data lives inside their own system, it's an operating asset.</p>

<h2>What our SiteCam build actually replaces</h2>
<p>For the SeaBreeze Roofing operation, the SiteCam system replaces the CompanyCam seat fee while integrating directly with the Permit Packet Builder and the white-label Roofing CRM. One data layer. Photos taken on a job page appear in the permit packet for that job. Photos taken on a claim page appear in the claim submission. The operator owns the storage, owns the file vault, and pays no per-seat subscription.</p>

<h2>Live example</h2>
<p>The 49-photo inspection record SeaBreeze captured on 2820 NE 44th Street (Lighthouse Point, October 2024) was the documentation that drove a $4.5M-$5M off-market acquisition with no buyer re-inspection. That's the operational value of having the right photo workflow: it doesn't just protect the contractor, it becomes a marketing and dealmaking asset for the entire vertically-integrated operation.</p>

<p>See more on our <a href="/solutions">operation solutions page</a>.</p>
""",
    },
    {
        "slug": "white-label-crm-replacing-acculynx",
        "category": "ops",
        "date": "2026-05-12",
        "title": "Replacing AccuLynx with a White-Label CRM You Own: When It Makes Sense and When It Doesn't",
        "excerpt": "AccuLynx is the de-facto roofing CRM. For 80% of operators it's the right call. For the 20% with specific workflow needs, scale ambitions, or branding requirements, owning a custom build pays back faster than expected.",
        "body": """
<p>AccuLynx earned its market position. The platform handles roofing-specific workflows &mdash; estimating templates, work orders, photo documentation, draws, commissions &mdash; better than any horizontal CRM ever will. For a roofing operation under 200 jobs per year that doesn't have a specific workflow constraint AccuLynx can't accommodate, the answer to "should we switch?" is almost always no.</p>

<h2>The 20% case where ownership wins</h2>
<p>The case for a white-label custom build emerges in five specific situations:</p>
<ol>
<li><strong>Multi-brand operation</strong>: a contractor running multiple DBAs needs different brand skins, different PDF outputs, different domain identities &mdash; without paying per-seat-per-brand.</li>
<li><strong>Workflow that fights the tool</strong>: a niche scope (commercial low-slope, restoration, specialty metals) where the standard estimating templates and stage flow constantly need workarounds.</li>
<li><strong>Local AHJ requirements</strong>: HVHZ permitting, county-specific forms, NOA mapping &mdash; building these into the tool rather than working around them.</li>
<li><strong>Data-as-asset thesis</strong>: the operator wants the lead, job, photo, and document data to live in their own infrastructure, not a vendor's.</li>
<li><strong>Plan to resell or white-label</strong>: the operator sees the CRM itself as a future product, brandable for other contractors.</li>
</ol>

<h2>What we built for SeaBreeze Roofing</h2>
<p>The white-label Roofing CRM we operate for SeaBreeze Roofing &amp; Sheet Metal is a self-hostable Flask application with SQLite storage. Every brand element &mdash; company name, logo, license numbers, color theme, PDF output &mdash; loads from a single <code>company_settings</code> row. Change one record and the whole app re-skins for a different contractor. The modules:</p>
<ul>
<li>Leads, jobs, estimates, invoices, commissions</li>
<li>Photo and document storage (file vault)</li>
<li>Branded PDF generation (estimates, proposals, work orders, contracts)</li>
<li>Library of NOA-driven estimating templates with default line items per work type (shingle, tile, metal galvalume, metal color, flat TPO, flat 3-ply self-adhered, flat hot-mop, plus shingle/tile/metal-flat splits)</li>
<li>Scope-of-work narrative library (lettered AccuLynx-style clauses) per template</li>
</ul>

<h2>What it cost vs. what it saves</h2>
<p>The build investment is real. The savings: roughly <strong>$10,000-$30,000 per year in seat fees</strong> for a mid-size operation, and the long-term option value of owning the dataset and the brand. For a single-operator contractor the math doesn't work. For a multi-brand operation, restoration specialist, or owner with a 5-year horizon thinking about selling the business, the ownership case is strong.</p>

<p>Read more about our productized software work on the <a href="/solutions">solutions page</a>.</p>
""",
    },
    {
        "slug": "florida-coastal-storm-impacted-lots-pipeline",
        "category": "market",
        "date": "2026-05-10",
        "title": "Storm-Impacted Lots and Teardowns: How a Coastal Florida Pipeline Actually Gets Built",
        "excerpt": "Hurricane events reset coastal Florida residential markets in ways that aren't visible from the listing data alone. The structured opportunity is in the lots that didn't make it to the MLS — and the long-term owners with motivation a normal market wouldn't surface.",
        "body": """
<p>The investor-friendly story of coastal Florida real estate is a clean one: rising tides of demand, demographic migration, undeveloped inventory along the barrier islands. The harder operational story is that a 70-year-old single-family home on a Madeira Beach gulf-side lot survives a hurricane and emerges as something different than what its tax record says it is. Building a real coastal Florida pipeline means looking at exactly those properties.</p>

<h2>What hurricanes do to a coastal pipeline</h2>
<p>After a major hurricane impact, three things happen to the affected residential inventory:</p>
<ol>
<li><strong>Insurance settlements vary wildly</strong>. Some owners receive enough to rebuild; others receive a fraction. The gap between what was paid out and what rebuilding actually costs creates a population of motivated sellers.</li>
<li><strong>Flood Insurance Rate Maps (FIRMs) get re-zoned</strong>. A property that previously didn't require flood insurance suddenly does, or vice versa. This changes carrying cost and insurability.</li>
<li><strong>Elevation requirements change</strong>. New construction in a Coastal A or VE zone requires significantly higher finished floor elevations &mdash; sometimes 10+ feet above the existing grade. A teardown-and-rebuild on a previously buildable lot may now require pilings, elevated mechanical, and breakaway walls.</li>
</ol>

<h2>What you're actually buying</h2>
<p>The Madeira Beach double-lot we feature on the <a href="/invest">invest page</a> is a representative example: two side-by-side gulf-side lots, one with a 1958-built home that survived but is at functional end-of-life, the other with a teardown structure already cleared. The asset isn't the houses. The asset is the dirt, the dock access, the elevation profile, and the entitlement to build to current code.</p>

<h2>Why pipeline depth matters</h2>
<p>One deal is a project. Ten deals is an operation. Our 100-deal master pipeline (gated, partner-only access) documents the full inventory across Pinellas County's barrier islands &mdash; lots, homes, duplexes, commercial parcels, hotels, and distressed inventory. The depth is what allows a single investor partner to do their first deal with us at small scale and roll into 10 more without sourcing new opportunities.</p>

<h2>The partnership shape</h2>
<p>For a typical $10M ground-up: the equity partner contributes 20-25% as cash or unencumbered land. The senior bank covers the rest under the developer's personal guarantee. Construction is executed by La Gala Construction (FL CGC 059211). Exit is 12-18 months. Equity returned first, then 50/50 profit split. First-deal partners get first right of refusal on subsequent pipeline deals.</p>

<p>If this matches what you're looking to do, the structured introduction starts at the <a href="/invest">invest page</a>.</p>
""",
    },
    {
        "slug": "hoa-violation-compliance-pay-by-phase-portal",
        "category": "ops",
        "date": "2026-05-08",
        "title": "HOA Violation Compliance Without the Fight: The Pay-By-Phase Portal Model",
        "excerpt": "When a Florida HOA hits a homeowner with a violation, the standard path is six months of board meetings, legal threats, and unpredictable cost. We built a different path: a bilingual portal that breaks compliance into three phases, pays per phase, and ends the dispute.",
        "body": """
<p>Florida's HOA enforcement system is set up for adversarial outcomes. The board issues a violation. The homeowner appeals, ignores, or fights. The board threatens a fine, a lien, and eventually foreclosure. Months pass. Lawyers get involved. Nobody is happier than they were before. We built the Casa Del Monte portal to give homeowners a different option.</p>

<h2>What the portal does</h2>
<p>The Casa Del Monte Violation Compliance Portal is a bilingual (English / Spanish) self-service site where a homeowner under HOA enforcement can:</p>
<ul>
<li><strong>Request a free assessment</strong>: a credentialed inspector walks the property and produces a written compliance scope.</li>
<li><strong>See the work in three phases</strong>: each phase has a fixed price and a clear deliverable.</li>
<li><strong>Pay per phase</strong>: only pay for the next phase when you're ready to start it. No big up-front commitment.</li>
<li><strong>Get documented compliance</strong>: the portal produces the photographic and inspection record the board needs to close the violation file.</li>
</ul>

<h2>Why pay-by-phase changes the dynamic</h2>
<p>The number one reason homeowners fight HOA violations isn't disagreement with the rule. It's distrust of contractors and inability to predict total cost. "I'm not signing for $12,000 of work on a quote I don't understand." Pay-by-phase eliminates that objection: the homeowner pays a small fixed price for an inspection, sees the phase-1 scope, pays for phase 1 only when they're ready to start it, and so on. At any phase break they can stop without owing further. The total cost is predictable and the commitment is reversible.</p>

<h2>What runs underneath</h2>
<p>The operator-facing backend is the second half of the build: a dashboard where the team running the program sees every assessment, tracks which phase each homeowner is in, manages phased payments, and triggers inspections. The public portal and the backend share one data layer &mdash; no double-entry, no spreadsheet bridge.</p>

<h2>Why this matters beyond HOAs</h2>
<p>The pay-by-phase / public-portal-plus-operator-backend pattern shows up everywhere in residential construction operations: insurance restoration, code compliance, accessibility retrofits, even pre-listing renovation work. The homeowner gets predictability and control. The operator gets a documented workflow. Both sides win compared to the standard adversarial contractor relationship.</p>

<p>See more about the system on our <a href="/solutions">solutions page</a>, where Casa Del Monte is featured in the live portfolio block.</p>
""",
    },
    {
        "slug": "k5-investment-group-la-gala-vertical-integration",
        "category": "development",
        "date": "2026-05-05",
        "title": "Vertical Integration in South Florida Development: The K5 + La Gala Construction Model",
        "excerpt": "K5 Investment Group sources, designs, and personally guarantees the senior debt. La Gala Construction executes the build. The same team that picks the deal puts the hammers on the wall. Here's why this matters for investor returns.",
        "body": """
<p>A common failure mode in coastal Florida development: an investor partner funds a deal, a developer entity runs the spreadsheet, and a separately-contracted general contractor builds the project. Three parties, three sets of incentives, three failure points. K5 Investment Group is structured to eliminate two of those gaps.</p>

<h2>What K5 and La Gala actually do</h2>
<p><strong>K5 Investment Group</strong> is the development entity. Founded by Keith La Gala, K5 sources off-market and on-market opportunities across South Florida, runs the deal underwriting, designs the project, packages it for the senior bank, signs the personal guarantee on the construction loan, and manages the equity-partner relationship. K5 is the deal architect and the financial spine.</p>
<p><strong>La Gala Construction</strong> &mdash; the DBA of Tilt Patchers, Inc., FL CGC 059211 &mdash; is the general contractor that physically builds the project. La Gala has 25+ years of restoration and ground-up development experience, including federal contracts to restore U.S. Coast Guard stations and U.S. Army and Air Force bases.</p>

<h2>Why the integration matters</h2>
<p>When the deal architect and the GC are the same operator, three things change:</p>
<ol>
<li><strong>Cost control is real</strong>: the underwriting cost estimates are built by the team that's going to actually do the work. No "GC said $1.2M, actual cost $1.6M" surprise.</li>
<li><strong>Quality oversight is direct</strong>: the project manager reports to the same principal that signed the bank guarantee. There's no middle-management abstraction layer where information gets soft-pedaled.</li>
<li><strong>Sub relationships compound</strong>: La Gala has been working with the same Broward and Palm Beach subs for years. Mobilization is faster, problem-solving is direct, and pricing is competitive without bidding cycles.</li>
</ol>

<h2>Selected La Gala track record</h2>
<ul>
<li><strong>Arrowhead Condominiums</strong>, Davie FL &mdash; $7.0M, 278-unit, 9-building plus clubhouse concrete restoration and 40-year recertification, completed August 2025.</li>
<li><strong>Glass at Victoria Park</strong>, Fort Lauderdale FL &mdash; $6.0M, ground-up development of 8 luxury downtown townhomes, completed March 2021 (through the COVID-era disruption, with mid-build deposit defaults and senior-loan restructuring; all 8 units sold within 3 months of completion).</li>
<li><strong>Datran &amp; Metro Dade Parking Garage</strong>, Miami FL &mdash; $5.7M, 9-story occupied parking garage concrete restoration, completed June 2020.</li>
<li><strong>ICON Student Housing</strong>, Tampa FL &mdash; $3.8M framing, drywall, and painting on a new 185-unit student housing build, completed August 2012.</li>
<li><strong>Fern Oak Estate</strong>, Pomona Park FL &mdash; $3.0M, 15-acre event-venue renovation, completed June 2025.</li>
</ul>

<h2>Where Collaborative Concept fits</h2>
<p>We are not part of K5 or La Gala. We're a separate consulting and structuring practice (FL doc L20000345198) that sources off-market opportunities, runs the appraisal and seller-side documentation, structures the equity-partner introduction, and assigns the resulting contract to K5 / La Gala for a flat fee at closing. Each party has independent counsel. Each party signs documents that protect their position. The structure is documented on the <a href="/properties">Project Management</a> page.</p>
""",
    },
]


# ===========================================================================
# Build helpers
# ===========================================================================
def slugify_filter_data(posts):
    out = []
    for p in posts:
        cat_label, cat_color = CATEGORY_BY_KEY[p["category"]]
        out.append({
            "slug": p["slug"],
            "title": p["title"],
            "excerpt": p["excerpt"],
            "date": p["date"],
            "category": p["category"],
            "category_label": cat_label,
            "category_color": cat_color,
        })
    return out


def shared_head(title, description, canonical, post=None):
    """Return shared <head> block with SEO + OG + Twitter + JSON-LD."""
    json_ld_blog = ""
    if post:
        json_ld_blog = (
            '<script type="application/ld+json">'
            + (
                '{'
                f'"@context":"https://schema.org","@type":"BlogPosting",'
                f'"headline":"{post["title"]}",'
                f'"datePublished":"{post["date"]}",'
                f'"author":{{"@type":"Organization","name":"{BRAND} LLC"}},'
                f'"publisher":{{"@type":"Organization","name":"{BRAND} LLC","url":"{BASE_URL}"}},'
                f'"mainEntityOfPage":"{canonical}",'
                f'"description":"{post["excerpt"]}"'
                '}'
            )
            + '</script>'
        )

    org_ld = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization",'
        f'"name":"{BRAND} LLC","url":"{BASE_URL}",'
        '"sameAs":["https://solarexit.collaborativeconceptsfl.com"],'
        '"address":{"@type":"PostalAddress","streetAddress":"513 W Drew Street",'
        '"addressLocality":"Lantana","addressRegion":"FL","postalCode":"33462","addressCountry":"US"},'
        '"areaServed":{"@type":"State","name":"Florida"}}'
        '</script>'
    )

    return f"""<!DOCTYPE html>
<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{title}</title>
<meta name="description" content="{description}"/>
<meta name="author" content="{BRAND}"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<link rel="canonical" href="{canonical}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="{BRAND}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:url" content="{canonical}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta name="theme-color" content="#05152b"/>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2305152b'/%3E%3Ctext x='50%25' y='58%25' text-anchor='middle' font-family='Manrope,Arial,sans-serif' font-size='34' font-weight='800' fill='%237c5730'%3ECC%3C/text%3E%3C/svg%3E"/>
{org_ld}
{json_ld_blog}
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Manrope:wght@700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script>
  tailwind.config = {{
    darkMode: "class",
    theme: {{ extend: {{
      colors: {{ primary:"#05152b","primary-container":"#1b2a41",secondary:"#7c5730","secondary-container":"#6ee7b7","secondary-fixed":"#a7f3d0","on-secondary-fixed":"#064e3b",surface:"#faf9f8","surface-container-low":"#f4f3f2","surface-container-lowest":"#ffffff","surface-container-high":"#e9e8e7","on-surface":"#1a1c1c","on-surface-variant":"#44474d","outline-variant":"#c5c6ce","on-primary":"#ffffff" }},
      fontFamily: {{ headline:["Manrope"], body:["Inter"], label:["Inter"] }}
    }}}}
  }}
</script>
<style>
  body {{ font-family: 'Inter', sans-serif; }}
  h1, h2, h3 {{ font-family: 'Manrope', sans-serif; }}
  .prose-cc h2 {{ font-size: 1.5rem; font-weight: 800; color:#05152b; margin-top: 2.25rem; margin-bottom: 0.75rem; }}
  .prose-cc h3 {{ font-size: 1.15rem; font-weight: 800; color:#05152b; margin-top: 1.75rem; margin-bottom: 0.5rem; }}
  .prose-cc p {{ margin: 0.85rem 0; line-height: 1.7; color:#44474d; }}
  .prose-cc ul, .prose-cc ol {{ margin: 0.75rem 0 0.75rem 1.5rem; color:#44474d; line-height: 1.7; }}
  .prose-cc li {{ margin: 0.35rem 0; }}
  .prose-cc strong {{ color: #05152b; }}
  .prose-cc a {{ color:#7c5730; text-decoration: underline; text-underline-offset: 3px; }}
  .prose-cc a:hover {{ color:#05152b; }}
</style>
</head>"""


def shared_nav(active="about"):
    items = [
        ("About", "/", "about"),
        ("Project Management", "/properties", "project-management"),
        ("Operation Solutions", "/solutions", "operation-solutions"),
    ]
    desktop = []
    mobile = []
    for label, href, key in items:
        if key == active:
            desktop.append(f'<a class="text-[#7c5730] border-b-2 border-[#7c5730] pb-1 font-medium" href="{href}" aria-current="page">{label}</a>')
            mobile.append(f'<a class="block text-[#7c5730] font-bold py-2" href="{href}">{label}</a>')
        else:
            desktop.append(f'<a class="text-[#05152b] opacity-80 hover:text-[#7c5730] transition-colors duration-300" href="{href}">{label}</a>')
            mobile.append(f'<a class="block text-[#05152b] font-medium py-2" href="{href}">{label}</a>')
    return f"""<nav class="w-full sticky top-0 z-50 bg-[#faf9f8]/80 backdrop-blur-md">
<div class="flex justify-between items-center px-4 sm:px-8 py-3 sm:py-4 max-w-7xl mx-auto">
<a href="/" class="text-lg sm:text-2xl font-bold tracking-tight text-[#05152b]">{BRAND}</a>
<div class="hidden md:flex items-center space-x-8">
{chr(10).join(desktop)}
</div>
<div class="flex items-center gap-2">
<a href="/contact" class="bg-primary text-on-primary px-4 sm:px-6 py-2 sm:py-2.5 rounded-xl font-semibold text-sm sm:text-base active:scale-95 transition-all shadow-sm hover:bg-primary-container">Investor Inquiries</a>
<button onclick="document.getElementById('mobileMenu').classList.toggle('hidden')" class="md:hidden p-2 text-primary">
<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
</button>
</div>
</div>
<div id="mobileMenu" class="hidden md:hidden bg-[#faf9f8] border-t border-outline-variant/30 px-4 py-4 space-y-3">
{chr(10).join(mobile)}
</div>
</nav>"""


def shared_footer():
    return f"""<footer class="w-full py-12 px-4 sm:px-8 flex flex-col items-center text-center space-y-6 bg-[#05152b] text-[#faf9f8]">
<a href="/" class="text-xl font-bold">{BRAND}</a>
<div class="flex flex-wrap justify-center gap-6">
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/">About</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/properties">Project Management</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/solutions">Operation Solutions</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/blog">Blog</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/team">Team</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/pipeline">Pipeline (Partners)</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="https://solarexit.collaborativeconceptsfl.com" rel="noopener">Solar Exit</a>
<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/contact">Contact</a>
</div>
<p class="text-sm text-[#faf9f8]/60 max-w-2xl">&copy; 2026 {BRAND} LLC. Florida real estate consulting, off-market deal structuring, and operator software. Build execution by La Gala Construction (CGC 059211). Not an offer of securities.</p>
</footer>"""


# ===========================================================================
# Build /blog/index.html
# ===========================================================================
def build_blog_index():
    cat_chips = (
        '<button class="cat-chip filter-active" data-cat="all">All</button>\n'
        + "\n".join(
            f'<button class="cat-chip" data-cat="{key}" style="--chip-color:{color}">{label}</button>'
            for key, label, color in CATEGORIES
        )
    )

    cards = []
    for p in POSTS:
        cat_label, cat_color = CATEGORY_BY_KEY[p["category"]]
        cards.append(
            f'<a href="/blog/{p["slug"]}" data-cat="{p["category"]}" '
            f'class="post-card group border border-outline-variant/40 rounded-2xl p-7 bg-surface-container-lowest hover:border-secondary hover:shadow-md transition-all flex flex-col">\n'
            f'<div class="flex items-center gap-3 mb-3">\n'
            f'<span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded" style="background:{cat_color}15;color:{cat_color}">{cat_label}</span>\n'
            f'<span class="text-xs text-on-surface-variant">{p["date"]}</span>\n'
            f'</div>\n'
            f'<h3 class="font-extrabold text-primary text-lg leading-snug group-hover:text-secondary transition-colors">{p["title"]}</h3>\n'
            f'<p class="text-sm text-on-surface-variant mt-3 leading-relaxed flex-1">{p["excerpt"]}</p>\n'
            f'<span class="mt-5 inline-flex items-center gap-1 text-sm font-bold text-primary group-hover:text-secondary">Read article <span class="material-symbols-outlined text-base">arrow_forward</span></span>\n'
            f'</a>'
        )

    head = shared_head(
        f"Blog — Florida Real Estate, Roof Consulting, Solar Exit | {BRAND}",
        f"Long-form Florida real estate, roof consulting, solar exit, and operations software guides from {BRAND} LLC. Lighthouse Point, Madeira Beach, Broward, Palm Beach.",
        f"{BASE_URL}/blog/",
    )

    html = head + f"""
<body class="bg-surface text-on-surface">
{shared_nav('about')}

<main class="overflow-x-hidden">
<section class="max-w-7xl mx-auto px-4 sm:px-8 pt-12 sm:pt-20 pb-8">
<span class="text-secondary font-semibold tracking-widest uppercase text-xs">Field notes from the operation</span>
<h1 class="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-primary mt-3 leading-[1.05] tracking-tight">Florida real estate, construction, and operations &mdash; in plain English.</h1>
<p class="mt-6 max-w-3xl text-lg text-on-surface-variant leading-relaxed">Long-form posts on off-market deal structuring, HVHZ roof permitting, the Florida Solar Exit program, custom operator software, and the South Florida coastal market. Written by the team running the operation, not a content shop.</p>
</section>

<section class="max-w-7xl mx-auto px-4 sm:px-8 pb-16">
<div id="cat-filter" class="flex flex-wrap gap-2 mb-10">
{cat_chips}
</div>

<div id="post-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
{chr(10).join(cards)}
</div>

<p id="empty-state" class="hidden text-center text-on-surface-variant mt-12">No posts in this category yet.</p>
</section>
</main>

{shared_footer()}

<style>
.cat-chip {{
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid #c5c6ce;
  color: #44474d;
  background: #ffffff;
  transition: all 0.15s ease;
}}
.cat-chip:hover {{ border-color: #7c5730; color: #05152b; }}
.cat-chip.filter-active {{ background: #05152b; color: #ffffff; border-color: #05152b; }}
</style>

<script>
(function(){{
  var chips = document.querySelectorAll('.cat-chip');
  var cards = document.querySelectorAll('.post-card');
  var empty = document.getElementById('empty-state');
  chips.forEach(function(c){{
    c.addEventListener('click', function(){{
      chips.forEach(function(x){{ x.classList.remove('filter-active'); }});
      c.classList.add('filter-active');
      var cat = c.getAttribute('data-cat');
      var visible = 0;
      cards.forEach(function(card){{
        if (cat === 'all' || card.getAttribute('data-cat') === cat) {{
          card.style.display = ''; visible++;
        }} else {{
          card.style.display = 'none';
        }}
      }});
      empty.classList.toggle('hidden', visible !== 0);
    }});
  }});
}})();
</script>

</body></html>
"""
    with open(os.path.join(BLOG_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {BLOG_DIR}/index.html")


# ===========================================================================
# Build individual post pages
# ===========================================================================
def build_posts():
    for p in POSTS:
        cat_label, cat_color = CATEGORY_BY_KEY[p["category"]]
        canonical = f"{BASE_URL}/blog/{p['slug']}"
        head = shared_head(
            f"{p['title']} | {BRAND}",
            p["excerpt"],
            canonical,
            post=p,
        )

        html = head + f"""
<body class="bg-surface text-on-surface">
{shared_nav('about')}

<main class="overflow-x-hidden">
<article class="max-w-3xl mx-auto px-4 sm:px-8 pt-12 sm:pt-16 pb-20">
<nav class="text-xs text-on-surface-variant mb-6">
<a href="/blog" class="hover:text-primary">&larr; All posts</a>
</nav>

<div class="flex items-center gap-3 mb-5">
<span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded" style="background:{cat_color}15;color:{cat_color}">{cat_label}</span>
<span class="text-xs text-on-surface-variant">{p['date']}</span>
</div>

<h1 class="text-3xl sm:text-5xl font-extrabold text-primary leading-[1.1] tracking-tight">{p['title']}</h1>
<p class="mt-5 text-lg text-on-surface-variant leading-relaxed">{p['excerpt']}</p>

<hr class="my-10 border-outline-variant/40"/>

<div class="prose-cc max-w-none">
{p['body']}
</div>

<hr class="my-12 border-outline-variant/40"/>

<div class="bg-surface-container-low rounded-2xl p-7 border border-outline-variant/30">
<p class="text-xs uppercase tracking-widest text-secondary font-semibold">About the operator</p>
<p class="mt-3 text-sm text-on-surface-variant leading-relaxed">{BRAND} LLC is a Florida multi-vertical real estate consultancy headquartered in Lantana. We structure off-market acquisitions, run the Florida Solar Exit Program, and build operator software for partner contractors and developers. All licensed construction work is performed by our partners SeaBreeze Roofing &amp; Sheet Metal (FL CCC1328689 / CVC57073) and La Gala Construction (FL CGC 059211).</p>
<div class="mt-5 flex flex-wrap gap-3">
<a href="/contact" class="inline-block bg-primary text-on-primary px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-primary-container transition-colors">Talk to us</a>
<a href="/blog" class="inline-block border border-outline-variant text-primary px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-surface-container-low transition-colors">More posts</a>
</div>
</div>

</article>
</main>

{shared_footer()}
</body></html>
"""
        out_path = os.path.join(BLOG_DIR, f"{p['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Wrote {len(POSTS)} post pages to {BLOG_DIR}/")


# ===========================================================================
# Update sitemap.xml
# ===========================================================================
def update_sitemap():
    sitemap_path = os.path.join(REPO, "sitemap.xml")
    with open(sitemap_path, "r", encoding="utf-8") as f:
        sm = f.read()

    blog_entries = (
        f'  <url>\n    <loc>{BASE_URL}/blog/</loc>\n    <lastmod>2026-05-28</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.9</priority>\n  </url>\n'
    )
    for p in POSTS:
        blog_entries += (
            f'  <url>\n    <loc>{BASE_URL}/blog/{p["slug"]}</loc>\n    <lastmod>{p["date"]}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
        )

    # Remove any existing blog entries to avoid duplicates on re-run
    sm = re.sub(
        r'\s*<url>\s*<loc>https://collaborativeconceptsfl\.com/blog[^<]*</loc>.*?</url>\s*',
        '\n',
        sm,
        flags=re.DOTALL,
    )

    sm = sm.replace('</urlset>', blog_entries + '</urlset>')

    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sm)
    print(f"Updated sitemap.xml with {len(POSTS) + 1} blog URLs")


# ===========================================================================
# Add Blog link to nav on top-level pages
# ===========================================================================
def patch_footers():
    """Add Blog link into the footer nav on top-level pages if missing."""
    top_pages = ["index.html", "team.html", "properties.html", "invest.html",
                 "pipeline.html", "solutions.html", "contact.html"]
    for fn in top_pages:
        path = os.path.join(REPO, fn)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            c = f.read()
        if 'href="/blog"' in c:
            continue
        # insert Blog after Operation Solutions in footer
        c = c.replace(
            '<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/solutions">Operation Solutions</a>',
            '<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/solutions">Operation Solutions</a>\n<a class="text-[#faf9f8]/60 hover:text-[#7c5730] transition-all text-sm" href="/blog">Blog</a>',
        )
        c = c.replace(
            '<a class="text-[#faf9f8]/60 hover:text-[#1a8a9e] transition-all text-sm" href="/solutions">Operation Solutions</a>',
            '<a class="text-[#faf9f8]/60 hover:text-[#1a8a9e] transition-all text-sm" href="/solutions">Operation Solutions</a>\n<a class="text-[#faf9f8]/60 hover:text-[#1a8a9e] transition-all text-sm" href="/blog">Blog</a>',
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
    print("Patched footer Blog links on top-level pages")


# ===========================================================================
# Run all
# ===========================================================================
build_blog_index()
build_posts()
update_sitemap()
patch_footers()
print("done")
