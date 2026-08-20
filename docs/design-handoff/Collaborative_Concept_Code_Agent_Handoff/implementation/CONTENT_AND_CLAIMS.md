# Content and Claims Register

## Approved positioning copy

- `We develop properties and build solutions that move businesses forward.`
- `Development discipline. Operating clarity. One accountable partner.`
- Development: `Find the opportunity. Prove the plan. Execute with discipline.`
- Solutions: `Recover revenue. Fix the process. Build the system.`
- Revenue recovery: `You already paid for the leads. We help you make them pay you back.`
- About: `Direct accountability from strategy through execution.`
- CTA: `Have a property opportunity or operating problem?`

## Approved labels

- Development
- Solutions
- Selected Work
- About
- Insights
- Ventures
- Start a Conversation

## Verify before publication

| Item | Required verification |
| --- | --- |
| Madeira Beach Double-Lot Development | Correct spelling, parcel/location details, ownership/control, entitlement status, scope, current status, and approved imagery |
| Roofing Operating System | Whether it is internal, client work, live software, prototype, or concept; approved screenshots and outcome claims |
| Permit Packet Builder | Current functionality, supported jurisdictions, ownership, deployment status, and approved screenshots |
| Owner / HOA Portal | Current product status, ownership, clients, capabilities, and approved screenshots |
| Florida Solar Exit | Collaborative Concept's exact role, status, rights to name/image, and any result claims |
| Ventures | Ownership/involvement in every displayed venture and permission to show each brand |
| Team information | Exact name, title, biography, licenses, and approved portrait |
| Metrics | Source, timeframe, methodology, and permission to publish |
| Testimonials | Exact words, identity, company, permission, and disclosure of material relationships |
| Contact and legal | Email, physical/mailing address, privacy policy, terms, entity name, and form recipient |

## Generated-concept content that must not be published as fact

- Any revenue totals, savings values, projections, percentages, lead counts, close rates, or before-and-after metrics shown in concept images.
- Any generated project address, lot dimension, zoning classification, setback, unit count, square footage, budget, return, schedule, acquisition, entitlement, completion, or exit claim.
- Any generated headshot or portrait.
- Any claim that a concept, prototype, or internal tool was delivered to a client.
- Any generated article date, author, testimonial, certification, partner logo, or award.

## Licensed-services boundary

Copy must not imply that Collaborative Concept independently provides architecture, engineering, legal advice, brokerage, general contracting, roofing contracting, inspection, appraisal, financial advice, or other regulated work unless the relevant license and entity relationship are verified. When licensed partners perform work, name the responsibility accurately.

## Recommended content model

Projects and systems should be stored in structured data with fields such as:

```json
{
  "title": "",
  "slug": "",
  "division": "development|solutions|venture",
  "type": "",
  "location": "",
  "status": "concept|active|completed|internal|prototype",
  "summary": "",
  "heroImage": "",
  "heroAlt": "",
  "facts": [],
  "claimsVerified": false,
  "featured": false
}
```

The production build should hide entries whose `claimsVerified` value is false unless a clearly labeled concept mode is intentionally supported.
