#!/usr/bin/env python3
"""Read-only e-Boks project/runtime inventory. Never certifies online sync."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

COMPONENTS = {
    "ui_probe_manifest": ("extension/ui-probe/manifest.json", "Documents/ChatGPT/Chrome/.eboks-ondemand-probe/manifest.json"),
    "ui_probe_worker": ("extension/ui-probe/worker.js", "Documents/ChatGPT/Chrome/.eboks-ondemand-probe/worker.js"),
    "ui_probe_native_host": ("extension/ui-probe/native_host.py", "Documents/ChatGPT/Chrome/.eboks-ondemand-probe/native_host.py"),
    "keepalive_manifest": ("extension/inbox-keepalive/manifest.json", "projects/eboks-scraper-repo/extension/inbox-keepalive/manifest.json"),
    "keepalive_worker": ("extension/inbox-keepalive/worker.js", "projects/eboks-scraper-repo/extension/inbox-keepalive/worker.js"),
    "archive_manager": ("scripts/manage_export.py", "Documents/e-Boks/full-export-2026-09-22/manage_export.py"),
}


def inventory(repo: Path, home: Path) -> tuple[list[str], list[str]]:
    lines, problems = [], []
    for name, (source, deployed) in COMPONENTS.items():
        first, second = repo / source, home / deployed
        if not first.is_file() or not second.is_file():
            status = "MISSING"
            problems.append(f"{name}: source or deployed file missing")
        elif hashlib.sha256(first.read_bytes()).digest() != hashlib.sha256(second.read_bytes()).digest():
            status = "DRIFT"
            problems.append(f"{name}: deployed copy differs from Git source")
        else:
            status = "MATCH"
        lines.append(f"component.{name}={status}")

    host = home / ".config/google-chrome/NativeMessagingHosts/com.gernalix.eboks_ui_probe.json"
    try:
        config = json.loads(host.read_text())
        expected = home / "Documents/ChatGPT/Chrome/.eboks-ondemand-probe/native_host.py"
        registered = (config.get("name") == "com.gernalix.eboks_ui_probe"
                      and Path(config["path"]) == expected
                      and "chrome-extension://imapkpjnpakmnapjgbfjoajdieahphco/"
                      in config.get("allowed_origins", []))
    except (OSError, KeyError, ValueError, TypeError):
        registered = False
    lines.append(f"probe_native_host_registered={registered}")
    if not registered:
        problems.append("Native Messaging Host not registered as expected")

    # Source files being present does not prove the keepalive was loaded into Chrome.
    prefs_path = home / ".config/google-chrome/Default/Preferences"
    try:
        prefs = json.loads(prefs_path.read_text())
        extensions = prefs.get("extensions", {}).get("settings", {})
        expected = str(home / COMPONENTS["keepalive_manifest"][1]).removesuffix("/manifest.json")
        loaded = any(value.get("path") == expected for value in extensions.values())
    except (OSError, ValueError, TypeError):
        loaded = False
    lines.append(f"keepalive_chrome_registered={loaded}")
    if not loaded:
        lines.append("keepalive_runtime=NOT_INSTALLED (code/tests do not prove live alarms)")

    archive = home / "Documents/e-Boks/full-export-2026-09-22"
    db = archive / "eboks.sqlite"
    try:
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            n, extracted, latest = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(extracted), 0), MAX(received_date) FROM documents"
            ).fetchone()
        lines.extend([f"sqlite_integrity={integrity}", f"indexed_entries={n}",
                      f"text_extracted={extracted}", f"latest_indexed_received_date={latest}"])
        if integrity != "ok":
            problems.append(f"SQLite integrity check: {integrity}")
    except (sqlite3.Error, OSError) as exc:
        lines.append(f"sqlite_error={type(exc).__name__}")
        problems.append("SQLite cannot be opened read-only")

    progress = archive / "progress.json"
    try:
        state = json.loads(progress.read_text())
        check = state.get("last_incremental_check") or {}
        lines.append(f"last_incremental_inbox_check={check.get('checked_at', 'none')}")
        lines.append("historical_export_complete=" + str(all(
            state.get("sections", {}).get(x, {}).get("complete") is True
            for x in ("posta-pubblica", "posta-aziende")
        )))
    except (OSError, ValueError, TypeError):
        lines.append("progress_state=UNAVAILABLE")
        problems.append("progress.json missing or invalid")

    lines.append("online_inbox_freshness=UNVERIFIED (must inspect both authenticated UI inboxes)")
    return lines, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    lines, problems = inventory(args.repo.expanduser(), args.home.expanduser())
    for line in lines:
        print(line)
    for problem in problems:
        print(f"BLOCKER: {problem}")
    print(f"runtime_inventory={'BLOCKED' if problems else 'LOCAL_OK'}")
    return 2 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
