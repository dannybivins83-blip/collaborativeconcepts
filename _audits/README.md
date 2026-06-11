# _audits — WWS Site Auditor reports

Automated **propose-mode** audit reports for the La Gala WWS site, written by the
`wws-site-auditor` scheduled task (runs every 6 hours).

- Each run writes `audit-<UTC-timestamp>.md` — a prioritized findings report
  (P0 blocker → P3 polish) across **front-end/design, back-end, SEO, conversion,
  information architecture, accessibility, and bugs**, auditing both the live site
  (`https://wwslgc.collaborativeconceptsfl.com`) and the code in this repo.
- `LATEST.md` always points to the most recent report.

**Propose-mode:** the auditor never edits the live site (`wwslgc/`, `api/`). It only
reports + recommends, and commits its reports here. Apply fixes yourself, or hand a
report to Claude and say "do the P0/P1 fixes."

Manage the schedule in the app's **Scheduled** section (task id: `wws-site-auditor`).
