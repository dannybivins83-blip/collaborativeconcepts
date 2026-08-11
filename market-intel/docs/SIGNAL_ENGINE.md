# Signal Engine

A signal is a registered definition plus a compute function. Nothing is
hardcoded into a UI component; adding a signal makes it appear in the API,
scoring and (later) alerts automatically.

## Contract

```python
@signal(id="topic_acceleration", name="Topic Acceleration",
        description="...", category="text", params={...})
def topic_acceleration(db, entity_id, **kw) -> list[dict]:
    return [{"entity_id": ..., "observed_at": ..., "raw_value": ...,
             "knowable_at": ..., "detail": {...}, "source_record_ids": [...]}]
```

`compute_for_entities` then z-scores and percentile-ranks the batch **within its
cross-section**, so values are comparable between companies, and `persist`
writes them with evidence.

## Implemented

| Signal | Category | Measures |
|---|---|---|
| `topic_acceleration` | text | latest-period tag mentions vs the mean of the prior 3, per tag |
| `revenue_acceleration` | fundamental | change in the QoQ revenue growth *rate* (2nd derivative) |
| `margin_expansion` | fundamental | gross-margin change vs prior quarter |
| `filing_velocity` | flow | 8-K count, trailing 90d vs prior 90d |

## Rules that keep the numbers honest

- **Quarterly means quarterly.** `_quarterly()` drops periods outside 60–110
  days. Mixing an FY total into a quarterly series manufactures a fake +300%
  acceleration; there is a regression test.
- **`knowable_at`, not period end.** Q1 revenue is knowable when the 10-Q is
  filed, not on the last day of Q1. Backtests filter on `ingested_at`, which is
  set from `knowable_at`. This is the main defence against look-ahead bias.
- **Degenerate samples score zero, not infinity.** `zscores()` returns zeros for
  n<3 or zero variance instead of dividing by ~0.
- **Per-dimension signals need `subject_id`** (see D-009).
- **Errors are per-entity.** One entity raising does not kill the batch.

## Not claimed

None of these signals is known to predict returns. They are measurements. Until
a backtest harness exists (BUILD_STATUS → NEXT), any statement about edge is
unsupported.
