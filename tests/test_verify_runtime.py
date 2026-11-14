"""Focused tests for the local-only e-Boks runtime inventory."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/verify_runtime.py"
spec = importlib.util.spec_from_file_location("eboks_verify_runtime", MODULE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home, self.repo = root / "home", root / "repo"
        for source, deployed in runtime.COMPONENTS.values():
            for path in (self.repo / source, self.home / deployed):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("test-code")
        host = self.home / ".config/google-chrome/NativeMessagingHosts/com.gernalix.eboks_ui_probe.json"
        host.parent.mkdir(parents=True, exist_ok=True)
        host.write_text(json.dumps({
            "name": "com.gernalix.eboks_ui_probe",
            "path": str(self.home / "Documents/ChatGPT/Chrome/.eboks-ondemand-probe/native_host.py"),
            "allowed_origins": ["chrome-extension://imapkpjnpakmnapjgbfjoajdieahphco/"],
        }))
        archive = self.home / "Documents/e-Boks/full-export-2026-09-22"
        archive.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(archive / "eboks.sqlite") as c:
            c.execute("CREATE TABLE documents (received_date TEXT, extracted INT)")
            c.execute("INSERT INTO documents VALUES ('2026-11-12', 1)")
        (archive / "progress.json").write_text(json.dumps({
            "sections": {
                "posta-pubblica": {"complete": False},
                "posta-aziende": {"complete": False},
            },
            "last_incremental_check": {"checked_at": "2026-11-14T07:00:00+00:00"},
        }))

    def test_local_inventory_success_is_not_online_sync_claim(self):
        lines, problems = runtime.inventory(self.repo, self.home)
        self.assertEqual(problems, [])
        self.assertIn("sqlite_integrity=ok", lines)
        self.assertIn("latest_indexed_received_date=2026-11-12", lines)
        self.assertIn("keepalive_chrome_registered=False", lines)
        self.assertTrue(any("keepalive_runtime=NOT_INSTALLED" in x for x in lines))
        self.assertTrue(any("online_inbox_freshness=UNVERIFIED" in x for x in lines))

    def test_component_drift_is_blocked(self):
        path = self.home / runtime.COMPONENTS["ui_probe_worker"][1]
        path.write_text("unexpected-drift")
        lines, problems = runtime.inventory(self.repo, self.home)
        self.assertIn("component.ui_probe_worker=DRIFT", lines)
        self.assertTrue(any("ui_probe_worker" in p for p in problems))

    def test_missing_database_is_not_silently_accepted(self):
        (self.home / "Documents/e-Boks/full-export-2026-09-22/eboks.sqlite").unlink()
        lines, problems = runtime.inventory(self.repo, self.home)
        self.assertTrue(any("SQLite" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
