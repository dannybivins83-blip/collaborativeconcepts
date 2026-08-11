# Tag Graph

The core differentiator. Not "NVDA is tagged AI" but: *this document, on this
date, from this source, mentioned AI this many times, and here is the sentence.*

## Data model

`tags` is a self-referencing hierarchy (`Technology › Artificial Intelligence ›
GPUs`). `tag_aliases` holds surface forms. `entity_tags` is the observation
table:

```
entity_id, tag_id, source_record_id, observed_at, effective_at, ingested_at,
frequency, confidence, relevance, evidence, method
```

Unique on `(entity_id, tag_id, source_record_id)` — the same document can never
count twice. Because every row is timestamped, "is this theme accelerating?" is
a `GROUP BY` (`tag_timeseries`), not a separate pipeline.

## Matching (v1: lexical)

- Alias-driven regex with **word boundaries**. `AI` must not fire inside
  "said", "chain" or "maintenance" — there is a test for exactly that.
- Short all-caps aliases (`AI`, `GPU`) match **case-sensitively**; longer
  phrases are case-insensitive.
- Longest alias wins.
- `relevance = sqrt(hits per 1k words)/3`, capped at 1.0 — damped so 40 mentions
  beats 4 without being 10× stronger. Below `MIN_RELEVANCE` the hit is dropped.
- `evidence` stores the surrounding ±60 characters.

Precision over recall, deliberately: a noisy tag graph is worse than a small one
because every downstream signal inherits the noise.

## Roadmap

1. Embedding/semantic matching behind the same `Tagger` interface, evaluated
   against the lexical baseline on labelled examples before replacing it.
2. Brand → parent-company tags (HOKA → Deckers → DECK) via the relationship
   graph, so consumer-brand momentum maps to a ticker.
3. Cross-source confirmation: a theme appearing in filings *and* transcripts
   *and* news scores higher than the same spike in one source.
