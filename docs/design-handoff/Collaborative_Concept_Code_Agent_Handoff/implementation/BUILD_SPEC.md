# Build Specification

## Objective

Redesign the complete Collaborative Concept website around a single visual and messaging system. The visitor must understand within five seconds that the company has two connected divisions: Development and Solutions.

## Design hierarchy

1. `design-reference/APPROVED_MASTER_SITE_DESIGN.png`
2. `design-reference/APPROVED_SELECTED_WORK_REFERENCE.png`
3. Individual images in `page-concepts/`
4. Written rules in this folder

## Global structure

Desktop navigation:

- Development
- Solutions
- Selected Work
- About
- Insights
- Start a Conversation

Mobile navigation must use an accessible menu button, visible focus state, focus containment while open, Escape-to-close behavior, and restoration of focus to the trigger.

## Visual language

- Warm ivory canvas, Atlantic navy typography, teal Development accent, copper Solutions accent.
- Editorial serif display type with a highly readable sans-serif interface/body face.
- Architectural plans, parcel lines, elevation marks, dimensions, and site-plan fragments appear as restrained background layers.
- Solutions graphics use the same drafting logic for workflows, process maps, dashboards, and reporting.
- Photography should feel authentically South Florida: coastal property, construction documents, operating work, and real project context.
- Avoid gradients, glass effects, neon, generic startup illustration, excessive cards, excessive corner radii, and stock corporate headshots.

## Reusable components

- `SiteHeader`
- `MobileNavigation`
- `DivisionLabel` with Development and Solutions variants
- `EditorialHero`
- `TechnicalOverlay`
- `DivisionSplit`
- `ProjectCard`
- `CaseStudyRow`
- `MetricGroup` — render only verified metrics
- `ProcessStrip`
- `ArticleCard`
- `InquiryRouter`
- `PrimaryCTA`
- `SiteFooter`

Components may be named differently in the existing stack, but the system should remain reusable and data-driven.

## Master homepage

1. Hero
   - H1: `We develop properties and build solutions that move businesses forward.`
   - Supporting line: `Development discipline. Operating clarity. One accountable partner.`
   - CTAs: `Explore Development` and `Explore Solutions`
2. Two-division introduction
   - Development: `Find the opportunity. Prove the plan. Execute with discipline.`
   - Solutions: `Recover revenue. Fix the process. Build the system.`
3. Featured development opportunity
4. Featured Solutions engagement or system
5. Selected work
6. Process: `Opportunity → Plan → Execution → Measured Result`
7. About/accountability section
8. Insights preview
9. Final conversation CTA

## Page-specific requirements

### Development overview

- Explain sourcing, underwriting, structure, execution, and exit.
- Use site plans, maps, elevations, schedules, and development photography.
- Show only real, verified projects and status labels.

### Projects and pipeline

- Filter by status or property type only if enough verified items exist.
- Each project needs title, location, category, verified status, short summary, and detail link.
- Never present an early concept as an entitled or completed development.

### Project detail

- Hero and project summary
- Opportunity and constraints
- Plan/site strategy
- Team and responsibility matrix
- Timeline or milestones
- Risks and disclosures
- Investor-information request CTA when appropriate
- Financial figures must be sourced, dated, and clearly labeled as actual, estimated, or projected.

### Solutions overview

- Organize around business outcomes, not a long service catalog.
- Recommended lanes: Revenue Recovery; Operating Systems; Software & Automation.
- Explain the diagnostic-to-implementation process.

### Revenue Recovery Sprint

- Promise a defined process, not guaranteed revenue.
- Show four weeks: Diagnose; Prioritize; Relaunch; Measure.
- Deliverables may include database analysis, ranked call lists, messaging, follow-up cadence, pipeline dashboard, and findings report.

### Systems, software, and automation

- Show representative workflows and interfaces.
- Identify what is live, internal, prototype, concept, or client work.
- Do not imply third-party platform integrations unless currently verified.

### Selected work

- Filters: All; Development; Solutions; Ventures, only when populated.
- Use alternating editorial rows on desktop and stacked cards on mobile.
- Every claim must be traceable to a real project record.

### About

- Explain the operator-led model and direct accountability.
- Use a real, owner-approved portrait only.
- Clearly distinguish Collaborative Concept responsibilities from licensed partners.

### Insights

- Two editorial tracks: Development and Solutions.
- Use real publish dates, authors, canonical URLs, and structured data.

### Contact

- Route visitors into Development or Solutions inquiries.
- Keep the phone number visible and clickable.
- Use accessible labels, confirmation state, spam protection, and a privacy disclosure.

### Ventures

- Keep ventures visually related but organizationally separate.
- Verify ownership, involvement, and status before displaying any venture.

## Responsive behavior

- Container max width: approximately 1280px.
- Breakpoints should follow content rather than devices; suggested starting points are 768px and 1024px.
- Two-column editorial layouts stack into one column.
- Ensure headings never overflow at 320px width.
- Use `clamp()` for display typography and section spacing.
- Maintain a minimum 44px interactive target.
- No horizontal overflow at 320, 375, 768, 1024, and 1440px.

## Image handling

- Prefer AVIF or WebP with JPEG/PNG fallback where appropriate.
- Use responsive `srcset` and `sizes`.
- Set width, height, and aspect ratio to prevent layout shift.
- Use descriptive alt text; decorative plan overlays should use empty alt text or CSS backgrounds.
- Lazy-load below-the-fold images; do not lazy-load the primary LCP hero image.

## Accessibility

- Target WCAG 2.2 AA.
- Semantic landmarks and a logical heading hierarchy.
- Keyboard-operable navigation, filtering, dialogs, forms, and accordions.
- Visible focus indicators.
- Respect `prefers-reduced-motion`.
- Do not rely on teal or copper alone to convey category.
- Validate contrast using final computed colors and font sizes.

## SEO and analytics

- Preserve useful existing URLs or create explicit permanent redirects.
- Unique title, meta description, canonical, social metadata, and H1 for every indexable page.
- Add Organization, WebSite, BreadcrumbList, Article, and project-relevant structured data only where valid.
- Preserve existing verified analytics and conversion events.
- Track division CTA clicks, project views, contact starts, successful submissions, phone clicks, and email clicks without collecting unnecessary personal data.

## Performance targets

- Lighthouse mobile targets: Performance 90+, Accessibility 95+, Best Practices 95+, SEO 95+.
- LCP under 2.5 seconds, CLS under 0.1, INP under 200ms under representative conditions.
- Avoid shipping a heavy animation or UI library solely for decorative effects.
