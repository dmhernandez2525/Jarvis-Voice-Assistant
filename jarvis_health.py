#!/usr/bin/env python3
"""jarvis-health: quick status summary of the Gemma 4 router logs.

Usage:
    python jarvis_health.py              # summary of today
    python jarvis_health.py --tail 50    # last 50 events
    python jarvis_health.py --crashes    # list crash files
    python jarvis_health.py --session <id>  # detail on one session

Reads from ~/Library/Logs/Jarvis-Gemma4/ . Never modifies anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG_ROOT = Path(os.environ.get(
    "JARVIS_LOG_ROOT",
    Path.home() / "Library" / "Logs" / "Jarvis-Gemma4",
))


def _iter_events(path: Path, since: datetime | None = None):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since:
                try:
                    ts = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                if ts < since:
                    continue
            yield rec


def cmd_summary(args) -> int:
    events_path = LOG_ROOT / "events.jsonl"
    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    events = list(_iter_events(events_path, since=since))

    print(f"=== Jarvis-Gemma4 health, last {args.hours}h ===")
    print(f"Log root:       {LOG_ROOT}")
    print(f"Events path:    {events_path}")
    print(f"Total events:   {len(events)}")

    if not events:
        print("\nNo events in the time window.")
        _print_log_files()
        return 0

    by_kind = Counter(e.get("kind", "?") for e in events)
    by_session = defaultdict(list)
    for e in events:
        by_session[e.get("session_id", "?")].append(e)

    print(f"\n--- Event counts ---")
    for kind, n in by_kind.most_common():
        print(f"  {kind:24s} {n}")

    print(f"\n--- Sessions ({len(by_session)}) ---")
    for sid, evts in sorted(by_session.items(), key=lambda x: x[1][0].get("ts", "")):
        start = next((e for e in evts if e.get("kind") == "session_start"), None)
        shutdown = next((e for e in evts if e.get("kind") == "shutdown"), None)
        crashes = [e for e in evts if e.get("kind") in {"crash", "thread_crash"}]
        wakes = sum(1 for e in evts if e.get("kind") == "wake_detected")
        llms = sum(1 for e in evts if e.get("kind") == "llm_response")
        status = "CRASHED" if crashes else ("EXITED" if shutdown else "IN PROGRESS or ABORTED")
        print(f"  {sid[:8]}  {start['ts'][:19] if start else '?':20s}  "
              f"wakes={wakes:2d} llms={llms:2d}  {status}")

    errors = [e for e in events if "error" in e.get("kind", "")]
    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for e in errors[-10:]:
            print(f"  {e['ts'][:19]} {e['kind']}: {e.get('error', '?')[:80]}")

    crash_count = sum(1 for e in events if e.get("kind") in {"crash", "thread_crash"})
    if crash_count:
        print(f"\n*** {crash_count} CRASHES in window. See {LOG_ROOT}/crashes/ ***")

    _print_log_files()
    return 0


def cmd_tail(args) -> int:
    events_path = LOG_ROOT / "events.jsonl"
    events = list(_iter_events(events_path))
    for e in events[-args.tail:]:
        kind = e.get("kind", "?")
        ts = e.get("ts", "")[:19]
        sid = e.get("session_id", "?")[:8]
        extra = {k: v for k, v in e.items() if k not in {"ts", "kind", "session_id", "pid"}}
        print(f"{ts} {sid} {kind:24s} {json.dumps(extra, default=str)[:200]}")
    return 0


def cmd_crashes(args) -> int:
    crash_dir = LOG_ROOT / "crashes"
    if not crash_dir.exists():
        print(f"No crash directory at {crash_dir}")
        return 0
    files = sorted(crash_dir.glob("crash-*.log"), reverse=True)
    if not files:
        print(f"No crashes in {crash_dir}")
        return 0
    print(f"=== {len(files)} crash file(s) in {crash_dir} ===")
    for f in files:
        size = f.stat().st_size
        print(f"  {f.name}  ({size} bytes)")
    if args.show and files:
        print(f"\n=== Most recent: {files[0].name} ===")
        print(files[0].read_text(encoding="utf-8"))
    return 0


def cmd_session(args) -> int:
    sess_dir = LOG_ROOT / "sessions"
    if not sess_dir.exists():
        print(f"No session directory at {sess_dir}")
        return 1
    matches = list(sess_dir.glob(f"session-{args.session}*.json"))
    if not matches:
        print(f"No session summary matching {args.session}")
        return 1
    for m in matches:
        print(f"=== {m.name} ===")
        print(m.read_text(encoding="utf-8"))
    return 0


def _print_log_files() -> None:
    print(f"\n--- Log files in {LOG_ROOT} ---")
    if not LOG_ROOT.exists():
        print("  (log root does not exist yet; run Jarvis once to create it)")
        return
    for child in sorted(LOG_ROOT.iterdir()):
        size = child.stat().st_size if child.is_file() else "-"
        print(f"  {child.name:24s}  {size}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=24,
                        help="Summary window in hours (default 24)")
    parser.add_argument("--tail", type=int, metavar="N",
                        help="Tail the last N events (stream mode)")
    parser.add_argument("--crashes", action="store_true",
                        help="List crash files")
    parser.add_argument("--show", action="store_true",
                        help="With --crashes, also print the most recent")
    parser.add_argument("--session", metavar="ID",
                        help="Show summary JSON for a specific session")
    args = parser.parse_args()

    if args.session:
        return cmd_session(args)
    if args.crashes:
        return cmd_crashes(args)
    if args.tail:
        return cmd_tail(args)
    return cmd_summary(args)


if __name__ == "__main__":
    sys.exit(main())
