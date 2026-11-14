#!/usr/bin/env python3
"""Native host for one on-demand e-Boks UI-control report; no browser data access."""
import json
import os
from pathlib import Path
import struct
import sys

OUT = Path.home() / 'Documents/ChatGPT/Chrome/.eboks-ondemand-probe/report.json'
MAX_ITEMS = 200
TEXT_KEYS = {'tag', 'role', 'type', 'aria', 'title', 'text', 'checked'}

def read_message():
    raw = sys.stdin.buffer.read(4)
    if len(raw) != 4:
        return None
    size = struct.unpack('<I', raw)[0]
    if size > 100_000:
        return None
    return json.loads(sys.stdin.buffer.read(size))

def item(value):
    if not isinstance(value, dict):
        return {}
    out = {}
    for key in TEXT_KEYS:
        raw = value.get(key)
        if raw is None or isinstance(raw, (str, bool)):
            out[key] = raw if not isinstance(raw, str) else raw[:200]
    if isinstance(value.get('disabled'), bool):
        out['disabled'] = value['disabled']
    return out

value = read_message() or {}
report = {
    'checkbox_count': value.get('checkbox_count') if isinstance(value.get('checkbox_count'), int) else 0,
    'checkboxes': [item(x) for x in value.get('checkboxes', [])[:MAX_ITEMS]],
    'export_controls': [item(x) for x in value.get('export_controls', [])[:MAX_ITEMS]],
}
tmp = OUT.with_suffix('.json.tmp')
tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
os.replace(tmp, OUT)
reply = json.dumps({'ok': True}).encode('utf-8')
sys.stdout.buffer.write(struct.pack('<I', len(reply)) + reply)
sys.stdout.buffer.flush()
