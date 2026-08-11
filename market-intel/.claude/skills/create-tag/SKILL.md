---
name: create-tag
description: Add a taxonomy node.
---

# create tag

Add a taxonomy node. Requirements: a human-defensible name, a parent, aliases that cannot false-positive (check short/uppercase forms), and a test asserting it does not match inside other words.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
