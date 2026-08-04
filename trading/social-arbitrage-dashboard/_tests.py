"""Offline tests for the pure functions in app.py — no network, run with:
    python3 _tests.py
Network-touching functions (fetch_trend_*, fetch_market_data, fetch_news_headlines)
are intentionally NOT exercised here — see app.py's module docstring re: Google
Trends blocking datacenter IPs, which would make live-network tests flaky by design.
"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    DATA_UNAVAILABLE,
    HYPE_PRICED_IN,
    NO_ANOMALY,
    SLEEPY_WALL_ST,
    build_news_query_url,
    classify_signal,
    compute_breakout_score,
    compute_pct_position,
    parse_google_news_rss,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>"Hoka shoes" OR DECK - Google News</title>
  <item>
    <title>Hoka Sales Surge as Brand Gains Share - Footwear News</title>
    <link>https://news.google.com/rss/articles/xyz1</link>
    <pubDate>Tue, 22 Jul 2026 14:00:00 GMT</pubDate>
    <source url="https://footwearnews.com">Footwear News</source>
  </item>
  <item>
    <title>Deckers Brands Q2 Earnings Beat Estimates</title>
    <link>https://news.google.com/rss/articles/xyz2</link>
    <pubDate>Mon, 21 Jul 2026 09:30:00 GMT</pubDate>
    <source url="https://reuters.com">Reuters</source>
  </item>
  <item>
    <title>Runner's World: Best Trail Shoes 2026</title>
    <link>https://news.google.com/rss/articles/xyz3</link>
    <pubDate>Sun, 20 Jul 2026 08:00:00 GMT</pubDate>
    <source url="https://runnersworld.com">Runner's World</source>
  </item>
  <item>
    <title>Item four</title>
    <link>https://news.google.com/rss/articles/xyz4</link>
    <pubDate>Sat, 19 Jul 2026 08:00:00 GMT</pubDate>
    <source url="https://example.com">Example</source>
  </item>
  <item>
    <title>Item five</title>
    <link>https://news.google.com/rss/articles/xyz5</link>
    <pubDate>Fri, 18 Jul 2026 08:00:00 GMT</pubDate>
    <source url="https://example.com">Example</source>
  </item>
  <item>
    <title>Item six — should be truncated by the limit</title>
    <link>https://news.google.com/rss/articles/xyz6</link>
    <pubDate>Thu, 17 Jul 2026 08:00:00 GMT</pubDate>
    <source url="https://example.com">Example</source>
  </item>
</channel>
</rss>"""


class BreakoutScoreTests(unittest.TestCase):
    def test_normal_case(self):
        # 5-year weekly baseline mean = 50; trailing 7 DAILY points mean = 100 -> 2.0x
        baseline = pd.Series([40, 50, 60, 50, 50])
        recent = pd.Series([90, 95, 100, 100, 105, 105, 105])  # 7 daily points
        self.assertAlmostEqual(compute_breakout_score(baseline, recent), 2.0)

    def test_uses_only_trailing_7_of_recent_series(self):
        # 10 daily points; only the LAST 7 should count toward the mean
        baseline = pd.Series([10, 10, 10])  # mean 10
        recent = pd.Series([1, 1, 1, 20, 20, 20, 20, 20, 20, 20])  # last 7 = mean 20
        self.assertAlmostEqual(compute_breakout_score(baseline, recent), 2.0)

    def test_none_inputs_return_none(self):
        self.assertIsNone(compute_breakout_score(None, pd.Series([1, 2])))
        self.assertIsNone(compute_breakout_score(pd.Series([1, 2]), None))

    def test_empty_series_return_none(self):
        self.assertIsNone(compute_breakout_score(pd.Series([], dtype=float), pd.Series([1])))
        self.assertIsNone(compute_breakout_score(pd.Series([1]), pd.Series([], dtype=float)))

    def test_all_nan_series_return_none(self):
        self.assertIsNone(compute_breakout_score(pd.Series([None, None]), pd.Series([1])))

    def test_zero_baseline_mean_returns_none(self):
        self.assertIsNone(compute_breakout_score(pd.Series([0, 0, 0]), pd.Series([5])))


class PctPositionTests(unittest.TestCase):
    def test_midpoint(self):
        self.assertAlmostEqual(compute_pct_position(50, 0, 100), 50.0)

    def test_at_low(self):
        self.assertAlmostEqual(compute_pct_position(10, 10, 20), 0.0)

    def test_at_high(self):
        self.assertAlmostEqual(compute_pct_position(20, 10, 20), 100.0)

    def test_clamps_above_high(self):
        # stale/lagged 52wk bounds can put price fractionally outside the band
        self.assertAlmostEqual(compute_pct_position(25, 10, 20), 100.0)

    def test_clamps_below_low(self):
        self.assertAlmostEqual(compute_pct_position(5, 10, 20), 0.0)

    def test_none_inputs_return_none(self):
        self.assertIsNone(compute_pct_position(None, 10, 20))
        self.assertIsNone(compute_pct_position(15, None, 20))
        self.assertIsNone(compute_pct_position(15, 10, None))

    def test_high_equals_low_returns_none(self):
        self.assertIsNone(compute_pct_position(15, 10, 10))


class ClassifySignalTests(unittest.TestCase):
    def test_sleepy_wall_st(self):
        # breakout above threshold, price still below the ceiling
        self.assertEqual(classify_signal(2.5, 30, min_score=2.0, max_pct=50), SLEEPY_WALL_ST)

    def test_hype_priced_in(self):
        self.assertEqual(classify_signal(2.5, 80, min_score=2.0, max_pct=50), HYPE_PRICED_IN)

    def test_no_anomaly(self):
        self.assertEqual(classify_signal(1.2, 30, min_score=2.0, max_pct=50), NO_ANOMALY)

    def test_boundary_score_equal_to_threshold_counts_as_breakout(self):
        self.assertEqual(classify_signal(2.0, 30, min_score=2.0, max_pct=50), SLEEPY_WALL_ST)

    def test_boundary_pct_equal_to_ceiling_counts_as_sleepy(self):
        self.assertEqual(classify_signal(2.0, 50, min_score=2.0, max_pct=50), SLEEPY_WALL_ST)

    def test_missing_data_returns_unavailable(self):
        self.assertEqual(classify_signal(None, 30, 2.0, 50), DATA_UNAVAILABLE)
        self.assertEqual(classify_signal(2.5, None, 2.0, 50), DATA_UNAVAILABLE)


class NewsUrlTests(unittest.TestCase):
    def test_url_structure(self):
        url = build_news_query_url("Hoka shoes", "DECK")
        self.assertTrue(url.startswith("https://news.google.com/rss/search?"))
        self.assertIn("hl=en-US", url)
        self.assertIn("gl=US", url)
        self.assertIn("ceid=US%3AEN".lower(), url.lower().replace("%3aen", "%3aen"))  # ceid present, case-insensitive
        self.assertIn("DECK", url)
        self.assertIn("Hoka", url)  # url-encoded but substring survives quote()'s default safe chars for letters


class NewsRssParseTests(unittest.TestCase):
    def test_parses_expected_fields(self):
        items = parse_google_news_rss(SAMPLE_RSS, limit=5)
        self.assertEqual(len(items), 5)  # truncated by limit, 6th item dropped
        first = items[0]
        self.assertEqual(first["title"], "Hoka Sales Surge as Brand Gains Share - Footwear News")
        self.assertEqual(first["source"], "Footwear News")
        self.assertIn("2026", first["pubDate"])
        self.assertTrue(first["link"].startswith("https://"))

    def test_limit_respected_lower(self):
        items = parse_google_news_rss(SAMPLE_RSS, limit=3)
        self.assertEqual(len(items), 3)

    def test_malformed_xml_returns_empty_list(self):
        self.assertEqual(parse_google_news_rss("<rss><not-closed>"), [])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(parse_google_news_rss(""), [])

    def test_no_items_returns_empty_list(self):
        self.assertEqual(parse_google_news_rss("<rss><channel></channel></rss>"), [])

    def test_item_missing_title_is_skipped(self):
        xml = """<rss><channel><item><link>https://x.com</link></item></channel></rss>"""
        self.assertEqual(parse_google_news_rss(xml), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
