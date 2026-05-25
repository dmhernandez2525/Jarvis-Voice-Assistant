"""Centralized logging, crash capture, and structured event log for Jarvis.

Layout in ~/Library/Logs/Jarvis-Gemma4/ :

    jarvis.log          rotating plaintext log, 10 MB x 5 files
    events.jsonl        one JSON object per line, easy grep / jq
    crashes/            unhandled-exception tracebacks, one file per crash
    faulthandler.log    C-level fault traces from sounddevice / MLX
    sessions/           per-session summary JSON written on shutdown

Public API:

    setup_logging(name="jarvis.gemma4") -> (logging.Logger, EventLog)
    EventLog.event(kind, **fields)      -> structured event emission
    install_crash_handlers()            -> excepthook + faulthandler

Import and call from the top of your entrypoint; everything else is automatic.
"""

from __future__ import annotations

import faulthandler
import json
import logging
import logging.handlers
import os
import signal
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---- paths ----

LOG_ROOT = Path(os.environ.get(
    "JARVIS_LOG_ROOT",
    Path.home() / "Library" / "Logs" / "Jarvis-Gemma4"
))
CRASH_DIR = LOG_ROOT / "crashes"
SESSION_DIR = LOG_ROOT / "sessions"
TEXT_LOG = LOG_ROOT / "jarvis.log"
EVENT_LOG = LOG_ROOT / "events.jsonl"
FAULT_LOG = LOG_ROOT / "faulthandler.log"


def _ensure_dirs() -> None:
    for p in (LOG_ROOT, CRASH_DIR, SESSION_DIR):
        p.mkdir(parents=True, exist_ok=True)


# ---- structured event log ----

class EventLog:
    """Append-only JSON-lines emitter, thread-safe.

    Each line is one JSON object with at minimum: ts, session_id, kind, pid.
    Additional fields come from caller kwargs. Never raises on write failure
    (logs the failure to the plaintext logger instead).
    """

    def __init__(self, path: Path, session_id: str, plain_logger: logging.Logger):
        self.path = path
        self.session_id = session_id
        self._lock = threading.Lock()
        self._plain = plain_logger

    def event(self, kind: str, **fields: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "pid": os.getpid(),
            "kind": kind,
            **fields,
        }
        try:
            line = json.dumps(record, default=str, ensure_ascii=False)
        except Exception as e:
            self._plain.error("EventLog json.dumps failed for kind=%s: %s", kind, e)
            return
        try:
            with self._lock:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except OSError as e:
            self._plain.error("EventLog write failed: %s", e)


# ---- crash handlers ----

def _format_exception(exc_type, exc_value, tb) -> str:
    lines = traceback.format_exception(exc_type, exc_value, tb)
    return "".join(lines)


def _write_crash_file(exc_type, exc_value, tb, session_id: str) -> Path:
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = exc_type.__name__ if exc_type else "unknown"
    path = CRASH_DIR / f"crash-{ts}-{session_id[:8]}-{short}.log"
    header = [
        f"Crash report",
        f"Timestamp:   {datetime.now(timezone.utc).isoformat()}",
        f"Session ID:  {session_id}",
        f"PID:         {os.getpid()}",
        f"Python:      {sys.version}",
        f"Executable:  {sys.executable}",
        f"Args:        {sys.argv}",
        f"Cwd:         {os.getcwd()}",
        "-" * 60,
        "",
    ]
    body = _format_exception(exc_type, exc_value, tb)
    path.write_text("\n".join(header) + body, encoding="utf-8")
    return path


def install_crash_handlers(
    session_id: str,
    plain_logger: logging.Logger,
    event_log: EventLog,
) -> None:
    """Install Python excepthook, signal handlers, and faulthandler."""
    _ensure_dirs()

    # faulthandler for C-level crashes (segfault etc.). Open in append mode so
    # crashes across multiple sessions accumulate.
    try:
        fh = FAULT_LOG.open("a")
        faulthandler.enable(file=fh, all_threads=True)
        # Also dump tracebacks on SIGUSR1 for runtime diagnostics.
        try:
            faulthandler.register(signal.SIGUSR1, file=fh, all_threads=True, chain=True)
        except (AttributeError, ValueError):
            # SIGUSR1 unavailable on some platforms; skip silently.
            pass
    except OSError as e:
        plain_logger.error("faulthandler setup failed: %s", e)

    prior_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            prior_excepthook(exc_type, exc_value, tb)
            return
        try:
            path = _write_crash_file(exc_type, exc_value, tb, session_id)
            plain_logger.critical(
                "Unhandled exception %s: %s (crash file: %s)",
                exc_type.__name__, exc_value, path,
            )
            event_log.event(
                "crash",
                exception_type=exc_type.__name__,
                message=str(exc_value),
                crash_file=str(path),
                traceback=_format_exception(exc_type, exc_value, tb),
            )
        except Exception as inner:
            # Last-ditch: don't lose the original exception if our handler fails.
            print(f"jarvis_logging: crash-handler failed: {inner}", file=sys.stderr)
            prior_excepthook(exc_type, exc_value, tb)
        else:
            prior_excepthook(exc_type, exc_value, tb)

    sys.excepthook = _excepthook

    # Thread-level crashes (threading.excepthook, 3.8+).
    def _thread_excepthook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        try:
            path = _write_crash_file(
                args.exc_type, args.exc_value, args.exc_traceback, session_id,
            )
            plain_logger.critical(
                "Unhandled thread exception in %s: %s (crash file: %s)",
                args.thread.name if args.thread else "<unknown>",
                args.exc_value, path,
            )
            event_log.event(
                "thread_crash",
                thread=args.thread.name if args.thread else None,
                exception_type=args.exc_type.__name__,
                message=str(args.exc_value),
                crash_file=str(path),
            )
        except Exception as inner:
            print(f"jarvis_logging: thread crash-handler failed: {inner}", file=sys.stderr)

    threading.excepthook = _thread_excepthook


# ---- session summary ----

def write_session_summary(
    session_id: str,
    start_time: float,
    stats: dict,
    extra: dict | None = None,
) -> Path:
    """Called on clean shutdown. Writes a JSON summary of the session."""
    _ensure_dirs()
    summary = {
        "session_id": session_id,
        "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": time.time() - start_time,
        "pid": os.getpid(),
        "stats": stats,
    }
    if extra:
        summary.update(extra)
    path = SESSION_DIR / f"session-{session_id}.json"
    path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return path


# ---- setup entrypoint ----

def setup_logging(
    name: str = "jarvis.gemma4",
    level: int = logging.INFO,
) -> tuple[logging.Logger, EventLog, str, float]:
    """Configure logging for the process. Returns (logger, event_log, session_id, start_time).

    Idempotent: if called twice the second call is a no-op that returns the
    already-configured handlers.
    """
    _ensure_dirs()

    session_id = str(uuid.uuid4())
    start_time = time.time()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if caller re-invokes.
    if not any(getattr(h, "_jarvis_marker", False) for h in logger.handlers):
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
        )

        # Rotating plaintext file: 10 MB x 5 = 50 MB retention.
        file_h = logging.handlers.RotatingFileHandler(
            TEXT_LOG, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
        )
        file_h.setLevel(level)
        file_h.setFormatter(fmt)
        file_h._jarvis_marker = True
        logger.addHandler(file_h)

        # Console handler (stderr) so iTerm also sees it.
        console_h = logging.StreamHandler()
        console_h.setLevel(level)
        console_h.setFormatter(fmt)
        console_h._jarvis_marker = True
        logger.addHandler(console_h)

    event_log = EventLog(EVENT_LOG, session_id, logger)

    install_crash_handlers(session_id, logger, event_log)

    logger.info(
        "Session start: id=%s pid=%d python=%s cwd=%s",
        session_id, os.getpid(), sys.version.split()[0], os.getcwd(),
    )
    event_log.event(
        "session_start",
        python=sys.version.split()[0],
        argv=sys.argv,
        cwd=os.getcwd(),
    )

    return logger, event_log, session_id, start_time
