import unittest

from steam_market_params.client import SteamMarketClient, build_default_headers, build_legacy_headers


class ClientTests(unittest.TestCase):
    def test_build_default_headers_uses_appid_in_referer(self):
        headers = build_default_headers(440)

        self.assertEqual(headers["Referer"], "https://steamcommunity.com/market/search?appid=440")
        self.assertEqual(headers["x-valve-request-type"], "routeAction")
        self.assertEqual(headers["x-valve-action-type"], "ZFJAHYDA:SearchMarketListings")

    def test_client_session_headers_use_appid(self):
        client = SteamMarketClient(appid=570)

        self.assertEqual(client.session.headers["Referer"], "https://steamcommunity.com/market/search?appid=570")
        self.assertEqual(client.session.headers["Content-Type"], "application/json; charset=utf-8")

    def test_build_legacy_headers_are_for_listing_html(self):
        headers = build_legacy_headers()

        self.assertEqual(headers["Referer"], "https://steamcommunity.com/market/")
        self.assertEqual(headers["Sec-Fetch-Mode"], "navigate")
        self.assertEqual(headers["sec-ch-viewport-width"], "1787")
        self.assertNotIn("x-valve-request-type", headers)

    def test_client_legacy_headers_do_not_use_route_action_headers(self):
        client = SteamMarketClient(appid=730, legacy=True)

        self.assertEqual(client.session.headers["Referer"], "https://steamcommunity.com/market/")
        self.assertEqual(client.session.headers["Accept"], "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8")
        self.assertNotIn("x-valve-action-type", client.session.headers)
