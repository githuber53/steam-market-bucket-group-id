import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from steam_market_params.cli import build_parser, command_update_Gitemid, selected_games


class CLITests(unittest.TestCase):
    def test_cli_selects_all_games(self):
        parser = build_parser()
        args = parser.parse_args(["update-names", "--all-games", "--limit", "1", "--processes", "3"])

        self.assertEqual(selected_games(args), ["cs2", "dota2", "tf2"])
        self.assertEqual(args.limit, 1)
        self.assertEqual(args.processes, 3)

    def test_cli_selects_single_game(self):
        parser = build_parser()
        args = parser.parse_args(["update-Gitemid", "cs2", "--enable-Gitemid"])

        self.assertEqual(selected_games(args), ["cs2"])
        self.assertIs(args.enable_Gitemid, True)

    def test_update_Gitemid_skips_games_disabled_by_config(self):
        parser = build_parser()
        args = parser.parse_args(["update-Gitemid", "tf2"])

        with redirect_stdout(StringIO()), patch("steam_market_params.cli.fetch_Gitemid_results") as fetch_Gitemid_results:
            command_update_Gitemid(args)

        fetch_Gitemid_results.assert_not_called()

    def test_cli_accepts_scan_mode_and_login(self):
        parser = build_parser()
        args = parser.parse_args(["update-names", "cs2", "--scan-mode", "full", "--login"])

        self.assertEqual(args.scan_mode, "full")
        self.assertIs(args.login, True)
