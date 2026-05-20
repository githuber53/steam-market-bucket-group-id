import unittest
from unittest.mock import patch

from steam_market_params.api import update_game


class APITests(unittest.TestCase):
    def test_update_game_does_not_share_internal_client_with_process_workers(self):
        with (
            patch("steam_market_params.api.get_name_list", return_value=["A"]) as get_name_list,
            patch("steam_market_params.api.get_item_nameids", return_value={"A": "123"}) as get_item_nameids,
            patch("steam_market_params.api.fetch_Gitemid_results", return_value={}) as fetch_Gitemid_results,
            patch("steam_market_params.api.save_json"),
        ):
            update_game(
                "cs2",
                include_Gitemid=True,
                processes=2,
                delay=0,
                limit=1,
                force=True,
            )

        self.assertIsNotNone(get_name_list.call_args.kwargs["client"])
        self.assertIsNone(get_item_nameids.call_args.kwargs["client"])
        self.assertIsNone(fetch_Gitemid_results.call_args.kwargs["client"])
