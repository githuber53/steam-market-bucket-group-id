import tempfile
import unittest
from pathlib import Path

from new_Gitemid import save_Gitemid
from steam_market_params.storage import load_json, save_json


class NewGBScriptTests(unittest.TestCase):
    def test_save_Gitemid_generates_from_names_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            names_path = data_dir / "cs2" / "names.json"
            save_json(
                names_path,
                [
                    {
                        "count_id": 0,
                        "name": "A",
                        "Gitemid": "G1",
                        "start": 0,
                        "status": "ok",
                    }
                ],
            )

            result = save_Gitemid(
                "cs2",
                limit=None,
                delay=0,
                processes=1,
                retry_attempts=0,
                retry_until_success=False,
                data_dir=data_dir,
                login=False,
            )

            self.assertEqual(result, {"A": "G1"})
            saved = load_json(data_dir / "cs2" / "Gitemid.json", {})
            self.assertEqual(saved["A"]["Gitemid"], "G1")
            self.assertEqual(saved["A"]["source"], "names")
