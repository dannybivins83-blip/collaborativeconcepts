"""Shared primitives: time, identifiers, provenance, errors.

Everything in this package is dependency-free (stdlib only) so it can be
imported by collectors, pipelines, the API, and tests alike.
"""
from .provenance import Provenance, source_id
from .timeutil import iso, now_utc, parse_ts
from .errors import CollectorError, ResolutionError, ValidationError

__all__ = ["Provenance", "source_id", "iso", "now_utc", "parse_ts",
           "CollectorError", "ResolutionError", "ValidationError"]
