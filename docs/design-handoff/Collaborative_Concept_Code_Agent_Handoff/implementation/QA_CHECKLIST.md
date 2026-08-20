# Prelaunch QA Checklist

## Content and claims

- [ ] Every project name, location, role, status, and outcome is verified.
- [ ] No generated metric, testimonial, portrait, article date, or partner logo remains.
- [ ] Regulated and licensed responsibilities are accurately attributed.
- [ ] Contact details and legal entity information are correct.

## Functional

- [ ] Every navigation, CTA, filter, form, phone link, and email link works.
- [ ] Development and Solutions inquiry routing reaches the correct destination.
- [ ] Forms show validation, success, and recoverable error states.
- [ ] Spam protection and rate limiting are configured where appropriate.
- [ ] Existing integrations are preserved or intentionally replaced.
- [ ] No console errors or failed network requests occur.

## Responsive

- [ ] Verify 320×568, 375×812, 768×1024, 1024×768, 1440×900, and a large desktop.
- [ ] No horizontal overflow.
- [ ] Navigation remains usable at every width.
- [ ] Editorial rows stack in the intended order.
- [ ] Technical overlays remain subtle and do not obscure copy.

## Accessibility

- [ ] Keyboard-only completion of all tasks.
- [ ] Visible focus states and logical focus order.
- [ ] Correct landmarks, labels, headings, and alt text.
- [ ] Contrast passes WCAG 2.2 AA.
- [ ] Reduced-motion preference is respected.
- [ ] Automated accessibility scan plus manual screen-reader spot check.

## SEO

- [ ] Titles, descriptions, canonicals, Open Graph images, and H1s are unique.
- [ ] Redirect map covers changed legacy URLs.
- [ ] XML sitemap and robots rules are correct for production.
- [ ] Structured data validates and contains no unsupported claims.
- [ ] Preview/staging is blocked from indexing.

## Performance

- [ ] Responsive images and dimensions are present.
- [ ] Hero image is optimized and intentionally prioritized.
- [ ] Fonts are subsetted/preloaded only when justified.
- [ ] Lighthouse targets are met on mobile and desktop.
- [ ] Core Web Vitals are checked after production deployment.

## Deployment

- [ ] Current repository, branch, host, domain, DNS, environment variables, and deployment root are documented.
- [ ] Preview deployment is reviewed by the owner.
- [ ] Backout plan is documented.
- [ ] Production deployment is verified at the live URL.
- [ ] Analytics, forms, redirects, and key conversion events are verified live.
