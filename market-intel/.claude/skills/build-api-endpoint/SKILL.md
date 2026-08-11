---
name: build-api-endpoint
description: Add a route.
---

# build api endpoint

Add a route. Steps: handler in apps/api/handlers.py returning (status, payload) → add to ROUTES → mirror in fastapi_app.py without logic → include provenance in the response → test 200 + 404 + bad params.

## Non-negotiables
- Provenance: every derived row references a source_record_id.
- Idempotency: re-running must converge, never duplicate.
- Temporality: record when a fact was true AND when it became knowable.
- No fake implementations; demo data is labelled DEMO.
