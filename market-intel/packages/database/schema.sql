-- Market Intelligence Terminal — core schema (v1)
--
-- Dialect: written for SQLite (the zero-infrastructure dev/test target) but
-- deliberately restricted to constructs PostgreSQL also accepts, so the same
-- DDL ports with a small type map (see docs/DATABASE_SCHEMA.md):
--   TEXT -> TEXT/VARCHAR, REAL -> DOUBLE PRECISION, INTEGER PK -> BIGSERIAL,
--   ISO-8601 TEXT timestamps -> TIMESTAMPTZ.
-- No SQLite-only pragmas or types appear below.
--
-- Three invariants this schema enforces rather than documents:
--   1. PROVENANCE — every normalized/derived row references source_records.
--   2. IDEMPOTENCY — every ingested row has a UNIQUE natural key, so a repeated
--      collector run upserts instead of duplicating.
--   3. TEMPORALITY — observations record effective_at (when true) AND
--      ingested_at (when we learned it). Backtests filter on ingested_at.

-- ---------------------------------------------------------------- sources --
CREATE TABLE IF NOT EXISTS data_sources (
    id              TEXT PRIMARY KEY,            -- 'sec', 'fred', ...
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,               -- filings|market|macro|news|alt
    official_url    TEXT,
    access_method   TEXT,                        -- http-json|http-xml|bulk|api
    auth_required    INTEGER NOT NULL DEFAULT 0,
    license_class   TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
                    -- PUBLIC|OPEN_DATA|API|LICENSE_REQUIRED|REVIEW_REQUIRED
    rate_limit      TEXT,
    update_frequency TEXT,
    historical_depth TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,  -- kill switch per source
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id              INTEGER PRIMARY KEY,
    source_id       TEXT NOT NULL REFERENCES data_sources(id),
    collector       TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',  -- running|ok|partial|failed
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_written INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    checkpoint      TEXT,                        -- opaque cursor for incremental sync
    error           TEXT
);
CREATE INDEX IF NOT EXISTS ix_runs_source ON ingestion_runs(source_id, started_at);

-- RAW LAYER. Never updated in place, never deleted by pipelines. `payload` is
-- the untouched source document; everything downstream is derivable from here.
CREATE TABLE IF NOT EXISTS source_records (
    id              TEXT PRIMARY KEY,            -- shared.source_id(...) natural key
    source_id       TEXT NOT NULL REFERENCES data_sources(id),
    kind            TEXT NOT NULL,               -- filing|facts|ticker_map|quote|article
    source_url      TEXT,
    payload         TEXT NOT NULL,               -- raw JSON/text as retrieved
    content_hash    TEXT NOT NULL,
    observed_at     TEXT,
    effective_at    TEXT,
    ingested_at     TEXT NOT NULL,
    run_id          INTEGER REFERENCES ingestion_runs(id)
);
CREATE INDEX IF NOT EXISTS ix_source_records_kind ON source_records(source_id, kind, ingested_at);

-- --------------------------------------------------------------- entities --
-- One table for every kind of thing (company, brand, product, theme, ...) so a
-- relationship can connect any two of them without a table per pair.
CREATE TABLE IF NOT EXISTS entities (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,   -- COMPANY|PUBLIC_COMPANY|TICKER|BRAND|PRODUCT|
                                     -- PERSON|EXECUTIVE|SUBSIDIARY|INDUSTRY|TECHNOLOGY|
                                     -- THEME|LOCATION|SUPPLIER|CUSTOMER|COMPETITOR|
                                     -- WEBSITE|APP|DRUG|COMMODITY|CRYPTO_ASSET
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'active',   -- active|merged|needs_review
    merged_into     TEXT REFERENCES entities(id),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE (type, slug)
);
CREATE INDEX IF NOT EXISTS ix_entities_name ON entities(name);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    alias           TEXT NOT NULL,
    alias_norm      TEXT NOT NULL,               -- casefolded/suffix-stripped
    kind            TEXT NOT NULL DEFAULT 'name',-- name|former_name|brand|abbrev
    source_record_id TEXT REFERENCES source_records(id),
    confidence      REAL NOT NULL DEFAULT 1.0,
    UNIQUE (entity_id, alias_norm, kind)
);
CREATE INDEX IF NOT EXISTS ix_alias_norm ON entity_aliases(alias_norm);

-- Strong identifiers (CIK, ticker, LEI, domain, ISIN). A match here is
-- authoritative; a name match never is.
CREATE TABLE IF NOT EXISTS entity_identifiers (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    scheme          TEXT NOT NULL,               -- cik|ticker|lei|domain|isin|cusip
    value           TEXT NOT NULL,
    value_norm      TEXT NOT NULL,
    source_record_id TEXT REFERENCES source_records(id),
    valid_from      TEXT,
    valid_to        TEXT,                        -- tickers get reassigned; keep history
    UNIQUE (scheme, value_norm, entity_id)
);
CREATE INDEX IF NOT EXISTS ix_ident_lookup ON entity_identifiers(scheme, value_norm);

-- Ambiguous matches are queued, never auto-merged.
CREATE TABLE IF NOT EXISTS resolution_candidates (
    id              INTEGER PRIMARY KEY,
    mention         TEXT NOT NULL,
    context         TEXT,
    candidate_entity_id TEXT REFERENCES entities(id),
    score           REAL NOT NULL,
    method          TEXT NOT NULL,               -- identifier|alias|fuzzy|context
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|accepted|rejected
    source_record_id TEXT REFERENCES source_records(id),
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rescand_status ON resolution_candidates(status, score);

-- --------------------------------------------------------------- markets ---
CREATE TABLE IF NOT EXISTS securities (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    ticker          TEXT NOT NULL,
    exchange        TEXT,
    currency        TEXT NOT NULL DEFAULT 'USD',
    security_type   TEXT NOT NULL DEFAULT 'common',
    active          INTEGER NOT NULL DEFAULT 1,
    UNIQUE (ticker, exchange)
);

CREATE TABLE IF NOT EXISTS ohlcv (
    id              INTEGER PRIMARY KEY,
    security_id     TEXT NOT NULL REFERENCES securities(id),
    trade_date      TEXT NOT NULL,
    open            REAL, high REAL, low REAL, close REAL,
    adj_close       REAL, volume REAL,
    source_record_id TEXT NOT NULL REFERENCES source_records(id),
    ingested_at     TEXT NOT NULL,
    UNIQUE (security_id, trade_date)
);

-- ------------------------------------------------------------------- SEC ---
CREATE TABLE IF NOT EXISTS sec_filings (
    id              TEXT PRIMARY KEY,            -- source_id('sec','filing',cik,accession)
    entity_id       TEXT REFERENCES entities(id),
    cik             TEXT NOT NULL,
    accession_no    TEXT NOT NULL,
    form            TEXT NOT NULL,               -- 10-K|10-Q|8-K|4|13F-HR|S-1...
    filed_at        TEXT NOT NULL,
    period_end      TEXT,
    primary_doc     TEXT,
    doc_url         TEXT,
    items           TEXT,                        -- 8-K item codes, comma separated
    source_record_id TEXT NOT NULL REFERENCES source_records(id),
    ingested_at     TEXT NOT NULL,
    UNIQUE (cik, accession_no)
);
CREATE INDEX IF NOT EXISTS ix_filings_entity ON sec_filings(entity_id, filed_at);
CREATE INDEX IF NOT EXISTS ix_filings_form ON sec_filings(form, filed_at);

-- Extracted document sections (risk factors, MD&A, business) for diffing.
CREATE TABLE IF NOT EXISTS filing_sections (
    id              INTEGER PRIMARY KEY,
    filing_id       TEXT NOT NULL REFERENCES sec_filings(id),
    section         TEXT NOT NULL,               -- item_1a_risk_factors|item_7_mdna|...
    heading         TEXT,
    body            TEXT NOT NULL,
    body_hash       TEXT NOT NULL,
    ordinal         INTEGER NOT NULL DEFAULT 0,
    UNIQUE (filing_id, section, ordinal)
);

-- Structured XBRL facts. `frame` distinguishes duration vs instant periods.
CREATE TABLE IF NOT EXISTS filing_facts (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    filing_id       TEXT REFERENCES sec_filings(id),
    taxonomy        TEXT NOT NULL,               -- us-gaap|dei
    concept         TEXT NOT NULL,               -- Revenues|NetIncomeLoss|...
    unit            TEXT NOT NULL,               -- USD|shares
    value           REAL NOT NULL,
    period_start    TEXT,
    period_end      TEXT NOT NULL,
    fiscal_year     INTEGER,
    fiscal_period   TEXT,                        -- FY|Q1|Q2|Q3
    form            TEXT,
    filed_at        TEXT,
    source_record_id TEXT NOT NULL REFERENCES source_records(id),
    ingested_at     TEXT NOT NULL,
    UNIQUE (entity_id, taxonomy, concept, unit, period_start, period_end, form)
);
CREATE INDEX IF NOT EXISTS ix_facts_lookup ON filing_facts(entity_id, concept, period_end);

-- Diff between a filing and its prior comparable (same form, same registrant).
CREATE TABLE IF NOT EXISTS filing_diffs (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    section         TEXT NOT NULL,
    current_filing_id  TEXT NOT NULL REFERENCES sec_filings(id),
    previous_filing_id TEXT NOT NULL REFERENCES sec_filings(id),
    change_type     TEXT NOT NULL,               -- added|removed|modified
    excerpt         TEXT NOT NULL,
    similarity      REAL,
    created_at      TEXT NOT NULL,
    UNIQUE (current_filing_id, previous_filing_id, section, change_type, excerpt)
);

-- -------------------------------------------------------------- tag graph --
CREATE TABLE IF NOT EXISTS tags (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    description     TEXT,
    parent_id       TEXT REFERENCES tags(id),
    category        TEXT,                        -- technology|consumer|health|energy...
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tags_parent ON tags(parent_id);

CREATE TABLE IF NOT EXISTS tag_aliases (
    id              INTEGER PRIMARY KEY,
    tag_id          TEXT NOT NULL REFERENCES tags(id),
    alias           TEXT NOT NULL,
    alias_norm      TEXT NOT NULL,
    UNIQUE (tag_id, alias_norm)
);
CREATE INDEX IF NOT EXISTS ix_tag_alias_norm ON tag_aliases(alias_norm);

-- TEMPORAL observations, not a join table: each row is "this source said this
-- entity relates to this tag at this time". Strength over time is a GROUP BY.
CREATE TABLE IF NOT EXISTS entity_tags (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    tag_id          TEXT NOT NULL REFERENCES tags(id),
    source_record_id TEXT NOT NULL REFERENCES source_records(id),
    observed_at     TEXT NOT NULL,
    effective_at    TEXT,
    ingested_at     TEXT NOT NULL,
    frequency       INTEGER NOT NULL DEFAULT 1,  -- mentions inside that document
    confidence      REAL NOT NULL DEFAULT 1.0,
    relevance       REAL NOT NULL DEFAULT 0.0,
    evidence        TEXT,                        -- the matched snippet
    method          TEXT NOT NULL DEFAULT 'lexical',
    UNIQUE (entity_id, tag_id, source_record_id)
);
CREATE INDEX IF NOT EXISTS ix_etags_entity ON entity_tags(entity_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_etags_tag ON entity_tags(tag_id, observed_at);

-- ---------------------------------------------------------- relationships --
CREATE TABLE IF NOT EXISTS relationships (
    id              TEXT PRIMARY KEY,
    from_entity_id  TEXT NOT NULL REFERENCES entities(id),
    to_entity_id    TEXT NOT NULL REFERENCES entities(id),
    type            TEXT NOT NULL,   -- OWNS|OWNED_BY|COMPETES_WITH|SUPPLIES|CUSTOMER_OF|
                                     -- PARTNERS_WITH|MANUFACTURES|USES_TECHNOLOGY|
                                     -- SELLS_PRODUCT|OPERATES_IN|MENTIONED_WITH|
                                     -- EXECUTIVE_OF|SUBSIDIARY_OF|BENEFITS_FROM_THEME|
                                     -- EXPOSED_TO_THEME
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    observation_count INTEGER NOT NULL DEFAULT 1,
    confidence      REAL NOT NULL DEFAULT 0.5,
    status          TEXT NOT NULL DEFAULT 'active',
    UNIQUE (from_entity_id, to_entity_id, type)
);
CREATE INDEX IF NOT EXISTS ix_rel_from ON relationships(from_entity_id, type);
CREATE INDEX IF NOT EXISTS ix_rel_to ON relationships(to_entity_id, type);

-- Evidence lives apart from the assertion: one relationship, many supports.
CREATE TABLE IF NOT EXISTS relationship_evidence (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL REFERENCES relationships(id),
    source_record_id TEXT NOT NULL REFERENCES source_records(id),
    observed_at     TEXT NOT NULL,
    excerpt         TEXT,
    confidence      REAL NOT NULL DEFAULT 0.5,
    UNIQUE (relationship_id, source_record_id, excerpt)
);

-- ---------------------------------------------------------------- signals --
CREATE TABLE IF NOT EXISTS signals (
    id              TEXT PRIMARY KEY,            -- 'topic_acceleration'
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT,                        -- fundamental|alt|flow|technical|text
    direction       TEXT NOT NULL DEFAULT 'higher_is_bullish',
    version         INTEGER NOT NULL DEFAULT 1,
    definition      TEXT,                        -- JSON params, versioned
    enabled         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS signal_observations (
    id              INTEGER PRIMARY KEY,
    signal_id       TEXT NOT NULL REFERENCES signals(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    -- A signal may be about a (entity, dimension) pair rather than the entity
    -- alone — topic_acceleration is per TAG. Empty string (not NULL) so the
    -- UNIQUE key still collapses repeats: in SQL, NULL != NULL.
    subject_id      TEXT NOT NULL DEFAULT '',
    observed_at     TEXT NOT NULL,               -- period the value describes
    ingested_at     TEXT NOT NULL,               -- when computable (backtest cutoff)
    raw_value       REAL,
    normalized_value REAL,                       -- 0..1
    zscore          REAL,
    percentile      REAL,
    confidence      REAL NOT NULL DEFAULT 1.0,
    signal_version  INTEGER NOT NULL DEFAULT 1,
    evidence        TEXT,                        -- JSON: source_record_ids + notes
    UNIQUE (signal_id, entity_id, subject_id, observed_at, signal_version)
);
CREATE INDEX IF NOT EXISTS ix_sigobs_entity ON signal_observations(entity_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_sigobs_signal ON signal_observations(signal_id, observed_at);

-- --------------------------------------------------------------- scoring ---
CREATE TABLE IF NOT EXISTS score_models (
    id              TEXT PRIMARY KEY,
    version         INTEGER NOT NULL,
    weights         TEXT NOT NULL,               -- JSON category -> weight
    created_at      TEXT NOT NULL,
    notes           TEXT,
    UNIQUE (id, version)
);

CREATE TABLE IF NOT EXISTS scores (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    model_id        TEXT NOT NULL,
    model_version   INTEGER NOT NULL,
    as_of           TEXT NOT NULL,
    composite       REAL NOT NULL,               -- 0..100
    categories      TEXT NOT NULL,               -- JSON category -> score
    coverage        REAL NOT NULL DEFAULT 0.0,   -- share of inputs actually present
    computed_at     TEXT NOT NULL,
    UNIQUE (entity_id, model_id, model_version, as_of)
);
CREATE INDEX IF NOT EXISTS ix_scores_asof ON scores(as_of, composite);

-- ------------------------------------------------------------ user layer ---
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT,                        -- PBKDF2/argon2 digest, never plaintext
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS watchlists (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id              INTEGER PRIMARY KEY,
    watchlist_id    TEXT NOT NULL REFERENCES watchlists(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    added_at        TEXT NOT NULL,
    UNIQUE (watchlist_id, entity_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    definition      TEXT NOT NULL,               -- JSON predicate over signals/events
    channel         TEXT NOT NULL DEFAULT 'in_app',
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_events (
    id              INTEGER PRIMARY KEY,
    alert_id        TEXT NOT NULL REFERENCES alerts(id),
    entity_id       TEXT REFERENCES entities(id),
    fired_at        TEXT NOT NULL,
    payload         TEXT,
    delivered       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INTEGER PRIMARY KEY,
    applied_at      TEXT NOT NULL
);
