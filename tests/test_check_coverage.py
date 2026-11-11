"""Regression tests for false-negative appointment searches on stale e-Boks exports."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_coverage import assess  # noqa: E402


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        db = sqlite3.connect(self.root / "eboks.sqlite")
        db.execute("CREATE TABLE documents (received_date TEXT, extracted INTEGER)")
        db.execute("INSERT INTO documents VALUES ('2026-10-27', 1)")
        db.commit()
        db.close()
        self.progress = {
            "sections": {"posta-pubblica": {"complete": False},
                         "posta-aziende": {"complete": False}},
            "last_incremental_check": {
                "checked_at": "2026-11-03T05:05:49+00:00",
                "after_date": "2026-09-15",
                "latest_archived_date": "2026-10-27",
                "sections": {"posta-pubblica": {}, "posta-aziende": {}},
            },
        }
        self.save_progress()

    def save_progress(self):
        (self.root / "progress.json").write_text(json.dumps(self.progress))

    def assess(self, notifications=None):
        return assess(self.root, date(2026, 10, 11), date(2026, 11, 11), notifications or [])

    def test_real_stale_export_blocks_absence_claim(self):
        reasons, facts = self.assess()
        self.assertIn("Ultimo controllo inbox antecedente", " ".join(reasons))
        self.assertEqual(facts["newest_document"], "2026-10-27")

    def test_later_notification_blocks_even_if_check_made_today(self):
        self.progress["last_incremental_check"]["checked_at"] = "2026-11-11T06:00:00+00:00"
        self.save_progress()
        reasons, _ = self.assess([datetime(2026, 11, 11, 7, 0, tzinfo=timezone.utc)])
        self.assertTrue(any("successiva al controllo" in r for r in reasons))

    def test_unimported_notice_blocks_after_recent_inbox_check(self):
        self.progress["last_incremental_check"]["checked_at"] = "2026-11-11T07:00:00+00:00"
        self.save_progress()
        reasons, _ = self.assess([datetime(2026, 11, 5, 15, 41, tzinfo=timezone.utc)])
        self.assertTrue(any("Nessun documento indicizzato" in r for r in reasons))

    def test_valid_recent_local_data_passes_only_precheck(self):
        self.progress["last_incremental_check"]["checked_at"] = "2026-11-11T08:00:00+00:00"
        self.progress["last_incremental_check"]["latest_archived_date"] = "2026-11-05"
        self.save_progress()
        with sqlite3.connect(self.root / "eboks.sqlite") as db:
            db.execute("INSERT INTO documents VALUES ('2026-11-05', 1)")
        reasons, _ = self.assess([datetime(2026, 11, 5, 15, 41, tzinfo=timezone.utc)])
        self.assertEqual(reasons, [])

    def test_missing_section_blocks(self):
        self.progress["last_incremental_check"]["checked_at"] = "2026-11-11T08:00:00+00:00"
        self.progress["last_incremental_check"]["sections"].pop("posta-aziende")
        self.save_progress()
        reasons, _ = self.assess()
        self.assertTrue(any("entrambe le sezioni" in r for r in reasons))

    def test_missing_extracted_text_blocks(self):
        self.progress["last_incremental_check"]["checked_at"] = "2026-11-11T08:00:00+00:00"
        self.save_progress()
        with sqlite3.connect(self.root / "eboks.sqlite") as db:
            db.execute("INSERT INTO documents VALUES ('2026-11-02', 0)")
        reasons, _ = self.assess()
        self.assertTrue(any("senza testo estratto" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
