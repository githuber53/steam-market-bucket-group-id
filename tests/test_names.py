import unittest

from steam_market_params.config import GameConfig
from steam_market_params.names import fetch_name_list, missing_count_ids, normalize_name_entries, resume_start


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def post_json(self, url, payload):
        self.calls.append((url, payload))
        return self.pages.pop(0)


class NameListTests(unittest.TestCase):
    def test_fetch_name_list_uses_route_action_payload_and_extracts_Gitemid(self):
        client = FakeClient(
            [
                {
                    "start": 0,
                    "total_count": 2,
                    "results": [
                        {
                            "strHash": "AK-47 | Fuel Injector (Minimal Wear)",
                            "asset_description": {"market_bucket_group_id": "G1807208C043004"},
                        },
                        {
                            "asset_description": {
                                "market_bucket_group_name": "StatTrak™ AK-47 | Frontside Misty",
                                "market_bucket_group_id": "G180720EA033004",
                            }
                        },
                    ],
                }
            ]
        )

        names = fetch_name_list(
            GameConfig(key="cs2", appid=730),
            client=client,
            delay=0,
        )

        self.assertEqual(names[0]["count_id"], 0)
        self.assertEqual(names[0]["name"], "AK-47 | Fuel Injector (Minimal Wear)")
        self.assertEqual(names[0]["Gitemid"], "G1807208C043004")
        self.assertIn("appid=730", client.calls[0][0])
        self.assertEqual(client.calls[0][1][0]["appid"], 730)
        self.assertEqual(client.calls[0][1][0]["sort"], 1)
        self.assertEqual(client.calls[0][1][0]["direction"], 1)
        self.assertEqual(client.calls[0][1][0]["start"], 0)

    def test_fetch_name_list_paginates_and_deduplicates(self):
        client = FakeClient(
            [
                {
                    "total_count": 3,
                    "results": [
                        {"strHash": "A", "asset_description": {"market_bucket_group_id": "G1"}},
                        {"strHash": "B", "asset_description": {"market_bucket_group_id": "G2"}},
                    ],
                },
                {
                    "total_count": 3,
                    "results": [
                        {"strHash": "C", "asset_description": {"market_bucket_group_id": "G3"}},
                    ],
                },
            ]
        )

        names = fetch_name_list(
            GameConfig(key="cs2", appid=730),
            client=client,
            count=2,
            delay=0,
        )

        self.assertEqual([entry["name"] for entry in names], ["A", "B", "C"])
        self.assertEqual(client.calls[1][1][0]["start"], 2)

    def test_fetch_name_list_adds_suffix_for_duplicate_names_with_distinct_Gitemids(self):
        client = FakeClient(
            [
                {
                    "total_count": 2,
                    "results": [
                        {"strHash": "Same", "asset_description": {"market_bucket_group_id": "G1"}},
                        {"strHash": "Same", "asset_description": {"market_bucket_group_id": "G2"}},
                    ],
                }
            ]
        )

        names = fetch_name_list(
            GameConfig(key="cs2", appid=730),
            client=client,
            delay=0,
        )

        self.assertEqual([entry["name"] for entry in names], ["Same", "Same #1"])

    def test_fetch_name_list_skips_fetch_when_limit_range_has_no_missing_count_ids(self):
        client = FakeClient(
            [
                {
                    "total_count": 5,
                    "results": [
                        {"strHash": "A", "asset_description": {"market_bucket_group_id": "G1"}},
                        {"strHash": "B", "asset_description": {"market_bucket_group_id": "G2"}},
                    ],
                }
            ]
        )

        names = fetch_name_list(
            GameConfig(key="cs2", appid=730),
            client=client,
            delay=0,
            limit=2,
            existing=normalize_name_entries(
                [
                    {"count_id": 0, "name": "A", "Gitemid": "G1", "start": 0, "status": "ok"},
                    {"count_id": 1, "name": "B", "Gitemid": "G2", "start": 0, "status": "ok"},
                ]
            ),
        )

        self.assertEqual([entry["count_id"] for entry in names], [0, 1])
        self.assertEqual(len(client.calls), 1)

    def test_fetch_name_list_respects_limit(self):
        client = FakeClient(
            [
                {
                    "total_count": 10,
                    "results": [{"strHash": "A"}, {"strHash": "B"}, {"strHash": "C"}],
                }
            ]
        )

        names = fetch_name_list(
            GameConfig(key="tf2", appid=440),
            client=client,
            count=100,
            delay=0,
            limit=2,
        )

        self.assertEqual([entry["name"] for entry in names], ["A", "B"])

    def test_normalize_legacy_string_names_and_resume_start(self):
        entries = normalize_name_entries(["A", "B"])

        self.assertEqual([entry.name for entry in entries], ["A", "B"])
        self.assertEqual(resume_start(entries), 2)

    def test_missing_count_ids_respects_limit_and_total_count(self):
        entries = normalize_name_entries(
            [
                {"count_id": 0, "name": "A", "Gitemid": "G1", "start": 0, "status": "ok"},
                {"count_id": 2, "name": "C", "Gitemid": "G3", "start": 0, "status": "ok"},
            ]
        )

        self.assertEqual(missing_count_ids(entries, total_count=5, limit=4), [1, 3])
