# PROMPT — Collaborative Concept website CODING agent (v2, state-aware)
Issued by the Overlord, 2026-08-20. This SUPERSEDES the handoff's
CODE_AGENT_MASTER_PROMPT.md, which assumed a from-scratch build. The build
happened; do not redo it. Paste everything below the divider.

---

You are continuing work on https://collaborativeconceptsfl.com/ in the repo
`C:\Users\kjburnz\collaborativeconcepts-repo` (static HTML on Vercel,
cleanUrls, autodeploy from main via git push; remote github.com/
dannybivins83-blip/collaborativeconcepts).

## CURRENT STATE — verify, then trust (git log + live site are ground truth)
- 16-route redesign LIVE. Home matched to the approved master at 1.004
  proportional fidelity (commit 5b360c7). Legacy /solutions shadow file
  archived. Development pipeline content restored (7f978ab). Mobile pass
  done: 19 routes, zero horizontal overflow at 375px.
- Design system: assets/redesign/site.css + tokens; docs/MOCKUP_FIDELITY_LOG.md
  records measured results and the two REQUIRED deviations from the concepts
  (register wording beats concept hero copy; the $5,200 fabricated case-study
  panel must never ship — CONTENT_AND_CLAIMS.md forbids it).
- Owner ruling on data: pipeline hero total = $8.37M (closed). The
  /development/pipeline-100 segment band still contradicts its own 100-row
  array (band 35/27/15/10/37 vs data 37/35/11/9/40) — see Task 2.

## YOUR TASKS, IN ORDER
1. SOLUTIONS PAGE STRUCTURAL REBUILD to page-concepts/05_Solutions_Overview.png
   (proportion ratio currently 1.384 — wrong section architecture, not
   spacing). Reproduce the concept's structure: hero w/ right image; 3-lane
   card row; 30-Day Sprint band; RECOVER→CONVERT→COMPOUND→AMPLIFY framework
   strip; proof panel AT THE SAME VISUAL WEIGHT but with NO dollar figures
   (qualitative copy until the owner supplies a verified case); systems row;
   copper CTA band. Keep approved register copy ("Recover revenue. Fix the
   process. Build the system.").
2. FIX the /development/pipeline-100 segment band by COMPUTING it from the
   page's own data array at render/build time so it can never drift again.
3. PAGE-BY-PAGE FIDELITY: compare the remaining 11 pages to their concepts at
   1440px exactly as done for Home (screenshot both, measure section shares,
   fix wrapping/spacing/typography, re-shoot until matched). Method and
   measured-target format are in docs/MOCKUP_FIDELITY_LOG.md.
4. INTEGRATE the design-agent asset package when it lands in inbox/overlord/
   (linework SVGs + editorial imagery replacing the soft upscaled crops).
   Slot-for-slot per its MANIFEST; no compositional changes.
5. MOBILE re-verification after each page change (375px, no overflow, menu ok).

## RULES
- The approved mockups are the visual contract. Written implementation files
  beat concepts where they conflict. Your design judgment is LAST resort and
  must be logged as an intentional difference with a reason.
- Never publish fabricated metrics, projects, portraits, or testimonials.
- Verify with tools; measure, don't eyeball; no claim without a screenshot or
  a curl. Work on a feature branch; push to main only when a task's
  side-by-sides pass; production deploys via push (autodeploy) — confirm the
  live URL after, or say you didn't.
- Coordinate through the OVERLORD bus (_OVERLORD/bus/, slug
  collaborativeconcepts): claim the lane before editing, post DONE with
  evidence after, escalate owner decisions to inbox/overlord/.

## REPORT BACK (to inbox/overlord/)
branch + commits · routes changed · side-by-side screenshots per page ·
measured proportion ratios before/after · intentional-difference log ·
mobile results · live-URL verification · anything still blocked and on whom.
