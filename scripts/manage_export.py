#!/usr/bin/env python3
"""Local resumable state and per-batch Downloads collector for this export."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

ROOT = Path.home() / 'Documents/e-Boks/full-export-2026-09-22'
STATE = ROOT / 'progress.json'
DOWNLOADS = Path.home() / 'Downloads'

def load():
    return json.loads(STATE.read_text(encoding='utf-8'))

def save(state):
    temporary = STATE.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, STATE)

def files():
    return [p for p in DOWNLOADS.iterdir() if p.is_file() and not p.name.endswith('.crdownload')]

def signature(p):
    stat = p.stat()
    return [p.name, stat.st_size, stat.st_mtime_ns]

def snapshot(_args):
    state = load()
    state['download_baseline'] = [signature(p) for p in files()]
    save(state)
    print(json.dumps({'baseline_files': len(state['download_baseline'])}))

def collect(args):
    state = load()
    try:
        signatures = json.loads(args.signatures)
    except json.JSONDecodeError:
        signatures = [value for value in args.signatures.split('|') if value]
    section = state['sections'][args.section]
    destination = ROOT / args.section / f'batch-{args.batch:04d}'
    existing = next((item for item in section['batches'] if item['batch'] == args.batch), None)
    if existing:
        raise SystemExit('batch_already_recorded')
    if destination.exists():
        raise SystemExit('unrecorded_batch_requires_verification')
    deadline = time.monotonic() + args.timeout
    # Other Chrome downloads must not block a completed, explicitly named export.
    while any((DOWNLOADS / (name + '.crdownload')).is_file() for name in (args.files or [])):
        if time.monotonic() >= deadline:
            raise SystemExit('crdownload_timeout')
        time.sleep(1)
    if 'download_baseline' not in state:
        raise SystemExit('download_baseline_required')
    baseline_names = {value[0] for value in state['download_baseline']}
    if not args.files:
        raise SystemExit('explicit_download_filenames_required')
    if not signatures or len(set(signatures)) != len(signatures) or set(signatures) & set(section['processed_signatures']):
        raise SystemExit('duplicate_message_signatures')
    if len(set(args.files)) != len(args.files):
        raise SystemExit('duplicate_download_filenames')
    new_files = []
    for name in args.files:
        if Path(name).name != name or name in baseline_names:
            raise SystemExit('preexisting_or_invalid_download')
        path = DOWNLOADS / name
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit('download_missing_or_empty')
        if path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as archive:
                if not archive.namelist() or archive.testzip() is not None:
                    raise SystemExit('invalid_download_zip')
        elif path.suffix.lower() != '.pdf' or path.open('rb').read(5) != b'%PDF-':
            raise SystemExit('invalid_download_format')
        new_files.append(path)
    if not new_files:
        raise SystemExit('no_new_downloads')
    destination.mkdir(parents=True, exist_ok=False)
    moved = []
    for source in new_files:
        target = destination / source.name
        number = 1
        while target.exists():
            target = destination / f'{source.stem}-{number}{source.suffix}'
            number += 1
        shutil.move(str(source), str(target))
        moved.append(target.name)
    section['processed_signatures'].extend(signatures)
    section['batches'].append({'batch': args.batch, 'signatures': signatures, 'files': moved})
    state.pop('download_baseline', None)
    save(state)
    print(json.dumps({'moved_files': len(moved), 'batch': args.batch}))

def complete(args):
    state = load()
    state['sections'][args.section]['complete'] = True
    save(state)

def repair_signature(args):
    section = load()['sections'][args.section]
    section['processed_signatures'] = [args.new if value == args.old else value for value in section['processed_signatures']]
    for batch in section['batches']:
        batch['signatures'] = [args.new if value == args.old else value for value in batch['signatures']]
    state = load()
    state['sections'][args.section] = section
    save(state)

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(required=True)
sub.add_parser('snapshot').set_defaults(func=snapshot)
collect_parser = sub.add_parser('collect')
collect_parser.add_argument('--section', required=True, choices=['posta-pubblica', 'posta-aziende'])
collect_parser.add_argument('--batch', required=True, type=int)
collect_parser.add_argument('--signatures', required=True)
collect_parser.add_argument('--timeout', type=int, default=60)
collect_parser.add_argument('--files', nargs='+', help='Exact new e-Boks download filenames; unrelated downloads are never collected')
collect_parser.set_defaults(func=collect)
complete_parser = sub.add_parser('complete')
complete_parser.add_argument('--section', required=True, choices=['posta-pubblica', 'posta-aziende'])
complete_parser.set_defaults(func=complete)
repair_parser = sub.add_parser('repair-signature')
repair_parser.add_argument('--section', required=True, choices=['posta-pubblica', 'posta-aziende'])
repair_parser.add_argument('--old', required=True)
repair_parser.add_argument('--new', required=True)
repair_parser.set_defaults(func=repair_signature)
args = parser.parse_args()
args.func(args)
