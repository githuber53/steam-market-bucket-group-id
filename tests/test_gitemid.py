import unittest

from steam_market_params.config import GameConfig
from steam_market_params.gitemid import fetch_Gitemid_result, fetch_Gitemid_results


class FakeResponse:
    def __init__(self, status_code, location=None):
        self.status_code = status_code
        self.headers = {}
        if location is not None:
            self.headers["location"] = location


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class SequenceClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, url, **kwargs):
        return self.responses.pop(0)


class GitemidTests(unittest.TestCase):
    def test_fetch_Gitemid_result_success(self):
        client = FakeClient(
            FakeResponse(302, "https://steamcommunity.com/market/listings/730/G18D2253004")
        )

        result = fetch_Gitemid_result(
            GameConfig(key="cs2", appid=730),
            "Dreams & Nightmares Case",
            client=client,
        )

        self.assertEqual(result.Gitemid, "G18D2253004")
        self.assertEqual(result.status, "ok")
        self.assertIs(client.calls[0][1]["allow_redirects"], False)

    def test_fetch_Gitemid_result_records_non_redirect_status(self):
        client = FakeClient(FakeResponse(200))

        result = fetch_Gitemid_result(GameConfig(key="cs2", appid=730), "Name", client=client)

        self.assertIsNone(result.Gitemid)
        self.assertEqual(result.status, "http_200")

    def test_fetch_Gitemid_uses_names_source_first(self):
        results = fetch_Gitemid_results(
            GameConfig(key="cs2", appid=730),
            [{"count_id": 0, "name": "A", "Gitemid": "G123", "start": 0, "status": "ok"}],
            delay=0,
        )

        self.assertEqual(results["A"].Gitemid, "G123")
        self.assertEqual(results["A"].source, "names")

    def test_fetch_Gitemid_results_retries_missing_names_value_with_redirect(self):
        client = SequenceClient(
            [
                FakeResponse(200),
                FakeResponse(302, "https://steamcommunity.com/market/listings/730/G18D2253004"),
            ]
        )

        results = fetch_Gitemid_results(
            GameConfig(key="cs2", appid=730),
            [{"count_id": 0, "name": "Retry Me", "Gitemid": None, "start": 0, "status": "missing_Gitemid"}],
            client=client,
            delay=0,
            retry_attempts=1,
        )

        self.assertEqual(results["Retry Me"].status, "ok")
        self.assertEqual(results["Retry Me"].Gitemid, "G18D2253004")
