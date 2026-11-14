"""Native Messaging Host accepts a bounded report without using real Chrome."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


class UIProbeNativeHostTests(unittest.TestCase):
    def test_report_written_only_to_configured_home(self):
        script = Path(__file__).resolve().parents[1] / "extension/ui-probe/native_host.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dest = root / "Documents/ChatGPT/Chrome/.eboks-ondemand-probe"
            dest.mkdir(parents=True)
            payload = json.dumps({
                "checkbox_count": 2,
                "checkboxes": [{"tag": "input", "type": "checkbox", "checked": False}],
                "export_controls": [{"tag": "button", "text": "Gem en lokal kopi"}],
            }).encode()
            command = struct.pack("<I", len(payload)) + payload
            process = subprocess.run([sys.executable, str(script)], input=command,
                                     capture_output=True, env={**os.environ, "HOME": directory},
                                     timeout=5, check=True)
            n = struct.unpack("<I", process.stdout[:4])[0]
            self.assertEqual(json.loads(process.stdout[4:4+n])["ok"], True)
            report = json.loads((dest / "report.json").read_text())
            self.assertEqual(report["checkbox_count"], 2)
            self.assertEqual(report["export_controls"][0]["text"], "Gem en lokal kopi")


if __name__ == "__main__":
    unittest.main()
