import unittest

from steam_market_params.gitemid import extract_Gitemid_from_location
from steam_market_params.item_nameids import extract_item_nameid


class ExtractorTests(unittest.TestCase):
    def test_extract_item_nameid_from_listing_html(self):
        html = "before Market_LoadOrderSpread( 123456789 ) after"

        self.assertEqual(extract_item_nameid(html), "123456789")

    def test_extract_item_nameid_returns_none_when_missing(self):
        self.assertIsNone(extract_item_nameid("<html></html>"))

    def test_extract_Gitemid_from_redirect_location(self):
        location = "https://steamcommunity.com/market/listings/730/G18D2253004"

        self.assertEqual(extract_Gitemid_from_location(location), "G18D2253004")

    def test_extract_Gitemid_rejects_non_Gitemid_redirect_location(self):
        location = "https://steamcommunity.com/market/listings/730/Dreams%20Case"

        self.assertIsNone(extract_Gitemid_from_location(location))

    def test_extract_Gitemid_handles_missing_location(self):
        self.assertIsNone(extract_Gitemid_from_location(None))
