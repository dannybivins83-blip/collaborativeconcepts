"""Typed errors. Collector failures must be isolatable: one dead provider may
never take down unrelated pipelines, so callers catch CollectorError per source."""


class MarketIntelError(Exception):
    """Base for everything this platform raises."""


class CollectorError(MarketIntelError):
    """A source could not be fetched/validated. Isolated per collector run."""

    def __init__(self, message, source=None, retryable=False):
        super().__init__(message)
        self.source = source
        self.retryable = retryable


class ValidationError(MarketIntelError):
    """A record failed validation and was rejected (counted, never silently dropped)."""


class ResolutionError(MarketIntelError):
    """Entity resolution could not proceed (never used for 'ambiguous' — that is a
    normal outcome returning candidates for review)."""
