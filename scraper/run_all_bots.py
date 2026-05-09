import os
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from db_utils import create_system_alert, record_bot_run, resolve_system_alerts

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRAPER_DIR = Path(__file__).resolve().parent

STATION_BOTS = [
    "total_station_bot.py",
    "tp_station_bot.py",
    "shell_station_bot.py",
]

PRICE_BOTS = [
    "opet_bot.py",
    "po_bot.py",
    "bp_bot.py",
    "aytemiz_bot.py",
    "total_bot.py",
    "tp_bot.py",
    "shell_bot.py",
]

BOT_TIMEOUTS_SECONDS = {
    "shell_station_bot.py": 600,
    "shell_bot.py": 180,
    "news_bot.py": 90,
}

DEFAULT_BOT_TIMEOUT_SECONDS = 300


def parse_args():
    parser = argparse.ArgumentParser(description="Run Fullet scraper bots.")
    parser.add_argument(
        "--mode",
        choices=("prices", "stations", "news", "all"),
        default=os.environ.get("FULLET_BOT_MODE", "all"),
        help="Bot group to run. Defaults to FULLET_BOT_MODE or all.",
    )
    return parser.parse_args()


def run_bot(script_name, env_overrides=None, timeout=180, mode=None):
    print("\n=====================================")
    print(f"Running: {script_name}")
    print("=====================================")
    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        [sys.executable, str(SCRAPER_DIR / script_name)],
        cwd=SCRAPER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    elapsed = time.time() - start_time
    finished_at = datetime.now(timezone.utc)
    status = "success" if result.returncode == 0 else "failed"
    record_bot_run(
        bot_name=script_name,
        mode=mode,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=elapsed,
        exit_code=result.returncode,
        summary=f"{script_name} {status} in {elapsed:.1f}s",
        stdout=result.stdout,
        stderr=result.stderr,
    )
    if result.returncode == 0:
        resolve_system_alerts(source=f"bot:{script_name}")
        print(f"[OK] {script_name} finished in {elapsed:.1f}s.")
        return True

    create_system_alert(
        severity="error",
        source=f"bot:{script_name}",
        title=f"{script_name} failed",
        message=(result.stderr or result.stdout or f"{script_name} exited with code {result.returncode}")[:2000],
        metadata={"mode": mode, "exit_code": result.returncode},
    )
    print(f"[FAIL] {script_name} exited with code {result.returncode} in {elapsed:.1f}s.")
    return False


def _run_bot_group(bots, *, failures, bot_env, mode):
    for bot in bots:
        timeout = BOT_TIMEOUTS_SECONDS.get(bot, DEFAULT_BOT_TIMEOUT_SECONDS)

        try:
            ok = run_bot(bot, env_overrides=bot_env, timeout=timeout, mode=mode)
        except subprocess.TimeoutExpired as exc:
            ok = False
            now = datetime.now(timezone.utc)
            record_bot_run(
                bot_name=bot,
                mode=mode,
                status="timeout",
                started_at=now,
                finished_at=now,
                duration_seconds=timeout,
                exit_code=None,
                summary=f"{bot} timed out after {timeout}s",
                stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout,
                stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr,
            )
            create_system_alert(
                severity="error",
                source=f"bot:{bot}",
                title=f"{bot} timed out",
                message=f"{bot} timed out after {timeout} seconds.",
                metadata={"mode": mode, "timeout_seconds": timeout},
            )
            print(f"[FAIL] {bot} timed out.")
        if not ok:
            failures.append(bot)


def _run_news_bot(*, failures, mode):
    try:
        news_ok = run_bot("news_bot.py", timeout=BOT_TIMEOUTS_SECONDS["news_bot.py"], mode=mode)
    except subprocess.TimeoutExpired as exc:
        news_ok = False
        now = datetime.now(timezone.utc)
        record_bot_run(
            bot_name="news_bot.py",
            mode=mode,
            status="timeout",
            started_at=now,
            finished_at=now,
            duration_seconds=BOT_TIMEOUTS_SECONDS["news_bot.py"],
            summary="news_bot.py timed out",
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout,
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr,
        )
        create_system_alert(
            severity="error",
            source="bot:news_bot.py",
            title="news_bot.py timed out",
            message="news_bot.py timed out.",
            metadata={"mode": mode},
        )
        print("[FAIL] news_bot.py timed out.")
    if not news_ok:
        failures.append("news_bot.py")


def main():
    args = parse_args()
    print(f"Fullet scraper orchestrator starting. Mode: {args.mode}")
    failures = []

    bot_env = {"FULLET_PUSH_SUMMARY": "0"}

    if args.mode in ("stations", "all"):
        _run_bot_group(STATION_BOTS, failures=failures, bot_env=bot_env, mode=args.mode)

    if args.mode in ("prices", "all"):
        _run_bot_group(PRICE_BOTS, failures=failures, bot_env=bot_env, mode=args.mode)

    if args.mode in ("news", "all"):
        _run_news_bot(failures=failures, mode=args.mode)

    if failures:
        print(f"[WARN] Completed with failing/skipped bots: {', '.join(failures)}")
        return 1

    print("[OK] All configured bots completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
