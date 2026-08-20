# One-Click Prompt for the Code Agent

Copy everything below this line into the coding agent after attaching this complete ZIP and the current website repository.

---

You are taking over the complete redesign of `https://collaborativeconceptsfl.com/`.

The attached `Collaborative_Concept_Code_Agent_Handoff` package is the approved product/design specification. The current website repository is the implementation source. Do not assume its framework, host, deployment root, form provider, analytics, or environment configuration: inspect and report them first.

## Objective

Implement the complete website so Collaborative Concept is immediately understood as one company with two connected divisions:

1. Development — identify, underwrite, structure, and execute property opportunities.
2. Solutions — recover revenue, improve operating processes, and build practical software and automation.

Use `design-reference/APPROVED_MASTER_SITE_DESIGN.png` as the primary visual source of truth. Use the individual concepts only for page-specific structure. If anything conflicts, the master design and written implementation files win.

## Required process

1. Inspect `git status`, repository instructions, framework, dependencies, routing, content sources, deployment configuration, environment variable names, forms, analytics, integrations, SEO files, and existing URLs.
2. Preserve all unrelated user work. Never run destructive reset or checkout commands.
3. Create a focused feature branch when git and a remote are available.
4. Produce a short implementation plan and URL redirect map before editing.
5. Implement the reusable design system and all routes described in `implementation/SITEMAP.md`.
6. Use structured data for projects, systems, ventures, and articles; do not hard-code repeated cards.
7. Follow `implementation/CONTENT_AND_CLAIMS.md`. Do not publish generated metrics, invented project facts, synthetic portraits, fake testimonials, or unverified licensed-service claims.
8. Preserve functioning forms, analytics, SEO value, and integrations unless replacement is explicitly approved.
9. Add or update automated tests appropriate to the actual stack.
10. Run formatting, linting, type checking, unit/integration tests, production build, link checks, accessibility checks, and responsive browser QA available in the repository.
11. Create a preview deployment only after local verification. Do not replace production without owner approval.
12. Verify the final deployed URL directly before claiming success.

## Design requirements

- Warm ivory background, deep navy typography, sea-glass teal for Development, muted copper for Solutions.
- Editorial serif display typography plus readable sans-serif body/interface typography.
- Restrained floor-plan, parcel, elevation, and dimension linework for Development.
- Restrained workflow, dashboard, and process schematics for Solutions using the same drafting language.
- Large imagery, strong whitespace, thin rules, square or nearly square corners.
- Avoid tech-startup gradients, glassmorphism, neon, excessive cards, pill-heavy UI, cartoon icons, and stock corporate headshots.
- Meet WCAG 2.2 AA and the responsive/performance requirements in `implementation/BUILD_SPEC.md`.

## Required pages

- Home
- Development overview
- Projects and pipeline
- Development project detail template
- Solutions overview
- Revenue Recovery Sprint
- Systems, Software & Automation
- Selected Work
- Work/case-study detail template
- Ventures
- About
- Insights index
- Article template
- Contact
- Privacy
- Terms

## Approved homepage copy

H1: `We develop properties and build solutions that move businesses forward.`

Supporting line: `Development discipline. Operating clarity. One accountable partner.`

Development: `Find the opportunity. Prove the plan. Execute with discipline.`

Solutions: `Recover revenue. Fix the process. Build the system.`

Primary CTA: `Start a Conversation`

Known phone: `(561) 475-8615`

Known location: `Lantana, Florida`

Verify all other content.

## Final report

Return:

1. Repository path used
2. Framework and hosting discovered
3. Branch name and commit hash
4. Exact files changed
5. Routes implemented and redirect map
6. Tests/checks run with exact results
7. Accessibility and responsive QA results
8. Lighthouse/Core Web Vitals results available locally or on preview
9. Preview URL and deployment ID, if created
10. Production URL and deployment ID, only if personally deployed and verified
11. Forms, analytics, integrations, and SEO status
12. Every remaining unverified claim or asset blocker
13. Confirmation that no secrets were exposed
14. Confirmation that no invented metrics, testimonials, project facts, or licensing claims were published

Do not claim the production site was updated unless you personally verified the live production URL after deployment.
