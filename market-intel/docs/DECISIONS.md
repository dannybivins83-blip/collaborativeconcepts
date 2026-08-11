# Architecture Decision Record

Each entry: the decision, why, what it costs, and how to reverse it.

---

## D-001 — Built as a subdirectory of `collaborativeconcepts`, not a new repo

**Decision.** The platform lives in `market-intel/` inside the existing
construction-business repo, on branch `claude/mimic-trading-research-qy02c9`.

**Why.** The build session was scoped to this repository and branch. A
subdirectory is self-contained, cannot affect the Vercel static site (nothing in
`vercel.json` routes to it, and it is listed in `.vercelignore`), and extracts
cleanly later.

**Cost.** An unrelated marketing/permits repo now carries a financial platform.
CI, issues and history are shared. This gets worse as the project grows.

**Reversal.** `git subtree split --prefix=market-intel -b market-intel-only`
then push that branch to a new repo. Do this before adding a second developer.

---

## D-002 — SQLite for dev/test, PostgreSQL as the production target

**Decision.** `packages/database` speaks plain DB-API SQL with `?` placeholders.
SQLite backs local runs and tests; the Postgres path raises `NotImplementedError`
rather than pretending to work.

**Why.** A new developer runs `make demo` with zero infrastructure. The schema
is written in the intersection of SQLite and Postgres DDL (no engine-specific
types or pragmas), so porting is a driver + type-map change, not a rewrite.

**Cost.** No `JSONB`, no window-function-heavy analytics, no concurrent writers.
SQLite will not survive the "billions of observations" target.

**Reversal.** Add a psycopg driver behind `Database.open()`; the type map is in
DATABASE_SCHEMA.md. Everything above the `Database` class is unchanged.

---

## D-003 — No ORM

**Decision.** Repositories + hand-written SQL instead of SQLAlchemy.

**Why.** The queries here are analytical and set-based; they read better as SQL
than as query-builder chains. It also keeps the core dependency-free, which is
what allowed the entire slice to be *proven running* in an environment with no
package installation.

**Cost.** No migrations tooling (Alembic), no automatic model validation.
Migrations are currently a single idempotent `schema.sql`.

**Reversal.** Introduce Alembic when the schema starts changing under real data.

---

## D-004 — Framework-agnostic API handlers with two adapters

**Decision.** `apps/api/handlers.py` contains `(db, params) -> (status, payload)`
functions. `server.py` (stdlib) and `fastapi_app.py` (target) both delegate to it.

**Why.** Business logic is unit-testable without a running server, and the dev
server works with zero installed packages. The two adapters cannot drift because
neither contains logic.

**Cost.** No automatic OpenAPI schema from the handler layer; the FastAPI
adapter has to restate route signatures.

---

## D-005 — Stdlib-only core (no FastAPI/Pydantic/SQLAlchemy in the hot path)

**Decision.** Every subsystem that runs in the proven slice uses only the
standard library.

**Why.** The build environment has no network and no way to install packages.
Rather than write code that "would work if installed", the core was built to
actually run and be tested here. FastAPI/Next.js remain the documented targets.

**Cost.** Hand-rolled HTTP client, no response-model validation, a hand-written
dev server. All acceptable at this stage; none of it is load-bearing for prod.

---

## D-006 — Fixtures swap bytes, not code paths

**Decision.** Offline mode replaces only the transport (`FixtureTransport`),
never the collector, parser or persistence logic.

**Why.** A mock that replaces the collector proves nothing. Swapping only the
wire bytes means the offline test exercises the production path end to end.

**Cost.** Fixtures must be refreshed when a source changes shape, or tests pass
while live ingestion breaks. Mitigation: `health_check()` per collector plus the
data-health endpoint.

---

## D-007 — Signals carry `knowable_at`, and backtests must filter on it

**Decision.** `signal_observations` stores both `observed_at` (the period the
value describes) and `ingested_at` (when the value first became computable —
for fundamentals, the filing date, not the period end).

**Why.** Q1 revenue is not knowable on the last day of Q1; it is knowable when
the 10-Q is filed weeks later. Filtering a backtest on `observed_at` silently
buys the future. This is the single most common way a research platform lies to
its owner.

**Cost.** Slightly more bookkeeping in every signal.

---

## D-008 — Composite score ships with `coverage`, and says it is not backtested

**Decision.** Missing signal categories are excluded and their weight
redistributed (never scored as zero), `coverage` is stored and displayed, and
both the API and UI carry an explicit "weights are a v1 prior, not backtested"
disclaimer.

**Why.** A score of 78 built from one signal is not the same claim as a 78 built
from eight. Hiding that difference is the difference between a research tool and
a confidence trick.

**Cost.** The headline number is less clean.

---

## D-009 — Per-tag signals need `subject_id` in the uniqueness key

**Decision.** `signal_observations` is unique on
`(signal_id, entity_id, subject_id, observed_at, signal_version)` where
`subject_id` defaults to `''` (empty string, not NULL).

**Why.** Found during the build: nine per-tag `topic_acceleration` rows silently
collapsed into one because the key had no tag dimension. NULL is wrong here
because `NULL != NULL` in SQL, which would break idempotency for entity-level
signals.

**Cost.** One more column in the hottest derived table.

---

## D-010 — Word-boundary lexical tagging before embeddings

**Decision.** v1 tagging is alias-driven regex with word boundaries, and short
all-caps aliases (`AI`, `GPU`) match case-sensitively.

**Why.** Substring matching produces silent garbage ("AI" inside "said",
"chain", "maintenance") and a tag graph nobody trusts is worthless. A small
precise taxonomy beats a large noisy one. There is a test asserting exactly this.

**Cost.** Misses paraphrase and synonymy. Embedding-based matching slots in
behind the same `Tagger` interface when there is data to evaluate it against.
