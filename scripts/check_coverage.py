#!/usr/bin/env python3
"""Gate appointment searches on e-Boks archive freshness; never prove online completeness."""
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

COPENHAGEN = ZoneInfo("Europe/Copenhagen")
SECTIONS = {"posta-pubblica", "posta-aziende"}


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must have a timezone offset")
    return timestamp


def assess(root: Path, since: date, through: date, notifications: list[datetime]) -> tuple[list[str], dict]:
    """Return blocking reasons and observed facts; never equate this with an online inbox audit."""
    if since > through:
        raise ValueError("--since must not be later than --through")
    reasons = []
    facts = {"sqlite_integrity": "unavailable", "last_check": "unavailable"}
    db = root / "eboks.sqlite"
    if not db.is_file():
        reasons.append("Indice SQLite assente")
    else:
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
                facts["sqlite_integrity"] = con.execute("PRAGMA integrity_check").fetchone()[0]
                if facts["sqlite_integrity"] != "ok":
                    reasons.append("Integrità SQLite non valida")
                newest, total = con.execute(
                    "SELECT MAX(received_date), COUNT(*) FROM documents"
                ).fetchone()
                facts["newest_document"] = newest
                facts["indexed_documents"] = total
                unreadable = con.execute(
                    "SELECT COUNT(*) FROM documents WHERE received_date BETWEEN ? AND ? AND extracted=0",
                    (since.isoformat(), through.isoformat()),
                ).fetchone()[0]
                missing_dates = con.execute(
                    "SELECT COUNT(*) FROM documents WHERE received_date IS NULL"
                ).fetchone()[0]
                if unreadable:
                    reasons.append(f"{unreadable} elementi del periodo senza testo estratto")
                if missing_dates:
                    reasons.append(f"{missing_dates} elementi senza data, impossibili da filtrare")
        except (sqlite3.Error, OSError) as exc:
            reasons.append(f"Indice non leggibile: {exc}")

    progress_path = root / "progress.json"
    try:
        progress = json.loads(progress_path.read_text())
        checkpoint = progress["last_incremental_check"]
        checked_at = parse_timestamp(checkpoint["checked_at"])
        facts["last_check"] = checked_at.isoformat()
        facts["historical_export_complete"] = all(
            progress.get("sections", {}).get(name, {}).get("complete", False)
            for name in SECTIONS
        )
        if checked_at.astimezone(COPENHAGEN).date() < through:
            reasons.append(f"Ultimo controllo inbox antecedente al {through}")
        scanned_sections = set(checkpoint.get("sections", {}))
        if not SECTIONS.issubset(scanned_sections):
            reasons.append("Ultimo controllo non include entrambe le sezioni della posta")
        after_date = date.fromisoformat(checkpoint["after_date"])
        if after_date >= since and not facts["historical_export_complete"]:
            reasons.append(f"Scansione incrementale iniziata dopo l'inizio del periodo {since}")
        if "newest_document" in facts and checkpoint.get("latest_archived_date") != facts["newest_document"]:
            reasons.append("Ultimo documento dell'export diverso da quello dell'indice SQLite")
        for notification in notifications:
            if notification > checked_at:
                reasons.append(f"Notifica Digital Post successiva al controllo: {notification.isoformat()}")
            if (facts.get("newest_document") or "") < notification.astimezone(COPENHAGEN).date().isoformat():
                reasons.append(f"Nessun documento indicizzato alla data della notifica o successivamente: {notification.date()}")
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        reasons.append(f"Stato export assente o non valido: {exc}")
    return reasons, facts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / "Documents/e-Boks/full-export-2026-09-22")
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--through", type=date.fromisoformat, default=datetime.now(COPENHAGEN).date())
    parser.add_argument("--notification-at", type=parse_timestamp, action="append", default=[],
                        help="Data/ora della notifica Digital Post ricevuta, con fuso orario (ripetibile)")
    args = parser.parse_args()
    reasons, facts = assess(args.root.expanduser(), args.since, args.through, args.notification_at)
    print(f"archive={facts.get('sqlite_integrity')} documents={facts.get('indexed_documents', '?')} "
          f"last_document={facts.get('newest_document', '?')} last_inbox_check={facts['last_check']}")
    print(f"coverage_gate={'BLOCK' if reasons else 'LOCAL_PRECHECK_OK'}")
    for reason in reasons:
        print(f"INCOMPLETO: {reason}")
    print("NOTA: anche LOCAL_PRECHECK_OK non prova che tutti i documenti online siano stati acquisiti; "
          "confrontare i messaggi sulla UI ufficiale con le notifiche e le firme degli ZIP.")
    return 2 if reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
