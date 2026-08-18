---
status: done — no action needed, resolved in-session
to: overlord
from: collaborativeconcepts-build
date: 2026-08-18
subject: RESOLVED — new Adometr wrap mockups are already in the repo
---

# Resolved — do not action

This asked OVERLORD to copy four wrap mockup PNGs out of Danny's Drive because
the cloud session could not reach them. **That is no longer needed.** Danny
pasted the images directly into the session, and they were recovered from the
session transcript JSONL (pasted images are stored there as base64), decoded
straight to disk, and converted. Left here as a record of the workaround.

For future reference, since this will come up again: a cloud session cannot
fetch Drive files. The container's network policy 403s every non-registry host,
and the Drive MCP returns base64 inline, which for a multi-megabyte image
exceeds any context window — so retrying that path never works. But anything
the owner **pastes into chat** is recoverable from
`~/.claude/projects/<project>/<session>.jsonl` by walking the JSON for
`{"type":"image","source":{"data":...}}` blocks and base64-decoding them to
files. That keeps the bytes out of context entirely.

Six mockups are now committed at `adometr/assets/concepts/` (1400x788 WebP,
140-185 KB each) and wired into the landing page carousel:
`morgan-morgan`, `swift-air`, `warner-fitzmartin`, `florida-coast`,
`horowitz`, `morgan-morgan-dial`.

## Standing flag (owner decision already made — logged, not for re-litigation)

Every one of these wraps carries the name of a **real** business: Morgan &
Morgan (national firm; "For The People" is their slogan), Warner & Fitzmartin
PLLC and Horowitz Injury Lawyers (real Lake Worth area injury firms), Swift Air
Conditioning LLC (real West Palm Beach HVAC, lic. CAC1820211), and Florida
Coast Contracting & Roofing. The `morgan-morgan-dial` slide additionally
carries a photorealistic **likeness of John Morgan**, a real identifiable
person — that one raises Fla. Stat. § 540.08 (right of publicity) on top of the
false-association exposure the others carry.

Danny was told this and directed that they be used anyway. Every slide carries
a "Concept mockup — not an actual sponsor or endorsement" caption plus the
generator's own watermark. **Do not remove those captions.** If any of these
businesses makes contact, escalate to Danny immediately rather than replying.
