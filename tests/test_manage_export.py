import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/manage_export.py'


class CollectorTests(unittest.TestCase):
    def test_only_requested_download_can_block_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / 'Documents/e-Boks/full-export-2026-09-22'
            root.mkdir(parents=True)
            downloads = home / 'Downloads'
            downloads.mkdir()
            state = {'download_baseline': [], 'sections': {'posta-pubblica': {
                'batches': [], 'processed_signatures': []}}}
            (root / 'progress.json').write_text(json.dumps(state))
            with zipfile.ZipFile(downloads / 'export.zip', 'w') as archive:
                archive.writestr('letter.txt', 'fixture')
            (downloads / 'unrelated.crdownload').write_bytes(b'partial')
            requested = downloads / 'export.zip.crdownload'
            requested.write_bytes(b'partial')
            command = ['python3', str(SCRIPT), 'collect', '--section',
                       'posta-pubblica', '--batch', '1', '--signatures',
                       '["message-id"]', '--files', 'export.zip', '--timeout', '0']
            env = dict(os.environ, HOME=tmp)
            blocked = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertIn('crdownload_timeout', blocked.stderr)
            self.assertEqual(json.loads((root / 'progress.json').read_text()), state)
            requested.unlink()
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'posta-pubblica/batch-0001/export.zip').is_file())
            self.assertTrue((downloads / 'unrelated.crdownload').is_file())
