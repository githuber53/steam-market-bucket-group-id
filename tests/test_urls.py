import unittest

from steam_market_params.urls import build_listing_url


class UrlTests(unittest.TestCase):
    def test_build_listing_url_encodes_special_characters(self):
        url = build_listing_url(730, "Dreams & Nightmares Case")

        self.assertEqual(
            url,
            "https://steamcommunity.com/market/listings/730/Dreams%20%26%20Nightmares%20Case",
        )

    def test_build_listing_url_encodes_slash_and_unicode(self):
        url = build_listing_url(730, "AK-47 | Redline (Field-Tested)")

        self.assertTrue(url.endswith("/AK-47%20%7C%20Redline%20%28Field-Tested%29"))
