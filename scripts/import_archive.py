#!/usr/bin/env python3
"""Idempotent SQLite text index of existing official e-Boks ZIP exports.

Source ZIPs remain authoritative; the database is derived and must stay local.
"""
import argparse
import hashlib
import html
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import zipfile

EXTS = {".pdf", ".txt", ".plain", ".html", ".htm", ".xml", ".rtf"}
DATE_AT_START = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


def extract(name: str, data: bytes) -> tuple[str | None, int]:
    extension = Path(name).suffix.lower()
    if extension == ".pdf":
        try:
            process = subprocess.run(
                ["pdftotext", "-layout", "-", "-"],
                input=data, capture_output=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None, 0
        if process.returncode != 0:
            return None, 0
        return process.stdout.decode("utf-8", errors="replace"), 1
    if extension in EXTS:
        text = data.decode("utf-8", errors="replace")
        if extension in {".html", ".htm", ".xml"}:
            text = html.unescape(re.sub(r"<[^>]*>", " ", text))
        return text, 1
    return None, 0


def sync(root: Path, db: Path) -> tuple[int, int, int]:
    if not (root / "posta-pubblica").is_dir():
        raise SystemExit(f"Missing e-Boks archive: {root / 'posta-pubblica'}")
    db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db)
    os.chmod(db, 0o600)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            section TEXT NOT NULL,
            source_zip TEXT NOT NULL,
            entry_name TEXT NOT NULL,
            received_date TEXT,
            format TEXT NOT NULL,
            body TEXT,
            sha256 TEXT NOT NULL,
            extracted INTEGER NOT NULL DEFAULT 0,
            UNIQUE(source_zip, entry_name)
        )""")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_eboks_received ON documents(received_date)"
        )
        connection.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(entry_name, body, content='documents', content_rowid='id')""")
        added = skipped = unavailable = 0
        with connection:
            for path in sorted(root.glob("posta-*/batch-*/*.zip")):
                relpath = str(path.relative_to(root))
                section = path.relative_to(root).parts[0]
                with zipfile.ZipFile(path) as archive:
                    for info in archive.infolist():
                        if info.is_dir():
                            continue
                        existing = connection.execute(
                            "SELECT sha256 FROM documents WHERE source_zip=? AND entry_name=?",
                            (relpath, info.filename),
                        ).fetchone()
                        data = archive.read(info)
                        digest = hashlib.sha256(data).hexdigest()
                        if existing:
                            if existing[0] != digest:
                                raise ValueError(f"Source ZIP member changed: {relpath}: {info.filename}")
                            skipped += 1
                            continue
                        body, extracted = extract(info.filename, data)
                        match = DATE_AT_START.match(Path(info.filename).name)
                        connection.execute(
                            """INSERT INTO documents
                            (section, source_zip, entry_name, received_date, format,
                             body, sha256, extracted)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (section, relpath, info.filename,
                             match.group(1) if match else None,
                             Path(info.filename).suffix.lower(), body, digest, extracted),
                        )
                        added += 1
                        unavailable += not extracted
            connection.execute("INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        return added, skipped, unavailable
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path,
        default=Path.home() / "Documents/e-Boks/full-export-2026-09-22",
        help="Directory containing posta-pubblica/ and posta-aziende/ ZIP batches",
    )
    parser.add_argument("--db", type=Path, help="SQLite output (defaults to ROOT/eboks.sqlite)")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    db = (args.db or root / "eboks.sqlite").expanduser().resolve()
    added, skipped, unavailable = sync(root, db)
    print(f"sqlite={db} added={added} unchanged={skipped} no_text={unavailable} integrity=ok")


if __name__ == "__main__":
    main()
