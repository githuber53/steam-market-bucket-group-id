import unittest
from unittest.mock import patch

from steam_market_params.config import GameConfig
from steam_market_params.item_nameids import fetch_item_nameids


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class ItemNameIDTests(unittest.TestCase):
    def test_fetch_item_nameids_keeps_null_for_failed_items(self):
        with patch(
            "steam_market_params.item_nameids.fetch_html_with_legacy_cookie",
            return_value=("url", FakeResponse("<html></html>")),
        ):
            result = fetch_item_nameids(
                GameConfig(key="cs2", appid=730),
                ["Missing"],
                delay=0,
                retry_attempts=0,
            )

        self.assertEqual(result, {"Missing": None})

    def test_fetch_item_nameids_retries_null_items(self):
        responses = [
            ("url", FakeResponse("<html></html>")),
            ("url", FakeResponse("Market_LoadOrderSpread(12345)")),
        ]

        with patch(
            "steam_market_params.item_nameids.fetch_html_with_legacy_cookie",
            side_effect=responses,
        ):
            result = fetch_item_nameids(
                GameConfig(key="cs2", appid=730),
                ["Retry Me"],
                delay=0,
                retry_attempts=1,
            )

        self.assertEqual(result, {"Retry Me": "12345"})
