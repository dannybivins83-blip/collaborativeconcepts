"""
Offline tests for the address-list matcher (api/match.py). No network — the
normalization + matching is pure. Run: python3 _match_tests.py
"""
import sys
import unittest

sys.path.insert(0, "api")
import match  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_basic(self):
        n = match.normalize_address("810 North A Street, Lake Worth Beach, FL 33460")
        self.assertEqual(n["num"], "810")
        self.assertEqual(n["street"], "n a st")
        self.assertEqual(n["zip"], "33460")

    def test_ordinals_and_dirs(self):
        n = match.normalize_address("2542 Southwest 12th Street, Boynton Beach 33426")
        self.assertEqual(n["num"], "2542")
        self.assertEqual(n["street"], "sw 12 st")

    def test_unit_stripped(self):
        n = match.normalize_address("1164 Biarritz Dr Apt 5, Miami Beach FL 33141")
        self.assertEqual(n["street"], "biarritz dr")
        self.assertEqual(n["num"], "1164")

    def test_no_zip(self):
        n = match.normalize_address("15531 42nd Road North, Loxahatchee")
        self.assertEqual(n["num"], "15531")
        self.assertIn("42", n["street"])
        self.assertEqual(n["zip"], "")


class MatchTests(unittest.TestCase):
    def test_same_property_diff_formatting(self):
        a = match.normalize_address("810 North A Street, Lake Worth Beach, FL 33460")
        b = match.normalize_address("810 N A ST, LAKE WORTH BEACH FL 33460")
        self.assertTrue(match.addr_matches(a, b))

    def test_ordinal_equivalence(self):
        a = match.normalize_address("15531 42nd Road North, Loxahatchee 33470")
        b = match.normalize_address("15531 42 RD N, LOXAHATCHEE, FL 33470")
        self.assertTrue(match.addr_matches(a, b))

    def test_different_house_number_no_match(self):
        a = match.normalize_address("12 Kensington Lane, Boynton Beach 33426")
        b = match.normalize_address("14 Kensington Lane, Boynton Beach 33426")
        self.assertFalse(match.addr_matches(a, b))

    def test_different_street_no_match(self):
        a = match.normalize_address("5 Sailfish Lane, Boynton Beach 33435")
        b = match.normalize_address("5 Marlin Lane, Boynton Beach 33435")
        self.assertFalse(match.addr_matches(a, b))

    def test_zip_mismatch_needs_strong_street(self):
        # same num+street, different zip -> still matches on strong street overlap
        a = match.normalize_address("18 Hastings Lane, Boynton Beach 33426")
        b = match.normalize_address("18 Hastings Lane, Boynton Beach 33472")
        self.assertTrue(match.addr_matches(a, b))


class MatchListTests(unittest.TestCase):
    PERMITS = [
        {"permit_number": "SOL-1", "address": "810 N A ST", "zip": "33460",
         "city": "Lake Worth Beach", "county": "Palm Beach",
         "description": "SOLAR PV 8KW", "contractor": "SUNCO", "tags": ["solar"]},
        {"permit_number": "SOL-2", "address": "9017 CARMA DR", "zip": "33472",
         "city": "Boynton Beach", "county": "Palm Beach",
         "description": "ROOF MOUNT SOLAR", "contractor": "X", "tags": ["solar"]},
    ]

    def test_matches_and_misses(self):
        inputs = [
            {"name": "Juan Vernal", "address": "810 North A Street, Lake Worth Beach, FL 33460",
             "status": "open"},
            {"name": "Antonio Santiago", "address": "9017 Carma Drive, Boynton Beach, FL 33472",
             "status": "open"},
            {"name": "Nobody", "address": "999 Nowhere Rd, Boynton Beach, FL 33426",
             "status": "CANCELED"},
        ]
        res = match.match_list(inputs, self.PERMITS)
        self.assertTrue(res[0]["matched"])
        self.assertEqual(res[0]["permits"][0]["permit_number"], "SOL-1")
        self.assertTrue(res[1]["matched"])
        self.assertFalse(res[2]["matched"])

    def test_preserves_input_metadata(self):
        res = match.match_list(
            [{"name": "Juan Vernal", "address": "810 N A St, Lake Worth Beach FL 33460",
              "status": "open"}], self.PERMITS)
        self.assertEqual(res[0]["input"]["name"], "Juan Vernal")
        self.assertEqual(res[0]["input"]["status"], "open")


class ParseTests(unittest.TestCase):
    def test_parse_name_pipe_address(self):
        text = ("Juan Vernal | 810 North A St, Lake Worth Beach FL 33460\n"
                "5151 Brian Boulevard, Boynton Beach FL 33472\n"
                "\n")
        items = match.parse_pasted(text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["name"], "Juan Vernal")
        self.assertIn("810", items[0]["address"])
        self.assertEqual(items[1]["name"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
