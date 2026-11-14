"""Idempotent indexing of ZIP exports and standalone PDFs from the official UI."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

MODULE = Path(__file__).resolve().parents[1] / "scripts/import_archive.py"
spec = importlib.util.spec_from_file_location("eboks_import_archive", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportArchiveTests(unittest.TestCase):
    def test_both_official_output_types_are_indexed_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = root / "posta-pubblica/batch-0001"
            batch.mkdir(parents=True)
            with zipfile.ZipFile(batch / "download.zip", "w") as archive:
                archive.writestr("2026-11-11_letter.txt", "Danish text")
            (batch / "2026-11-12_appointment.pdf").write_bytes(b"%PDF-minimal-fixture")
            db = root / "eboks.sqlite"

            with patch.object(module, "extract", side_effect=lambda n, data: (n, 1)):
                first = module.sync(root, db)
                second = module.sync(root, db)

            self.assertEqual(first, (2, 0, 0))
            self.assertEqual(second, (0, 2, 0))
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                rows = connection.execute(
                    "SELECT source_zip, received_date, body FROM documents ORDER BY received_date"
                ).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0][1], "2026-11-11")
                self.assertTrue(rows[1][0].endswith("2026-11-12_appointment.pdf"))
                self.assertEqual(rows[1][1], "2026-11-12")
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM documents_fts WHERE documents_fts MATCH 'appointment'"
                ).fetchone()[0], 1)

            (batch / "2026-11-12_appointment.pdf").write_bytes(b"%PDF-changed")
            with self.assertRaisesRegex(ValueError, "Source PDF changed"):
                module.sync(root, db)


if __name__ == "__main__":
    unittest.main()
