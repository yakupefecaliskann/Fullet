import os
import argparse
import subprocess
import sys
import time
from pathlib import Path

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
    "shell_bot.py",
    "total_bot.py",
    "tp_bot.py",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Run Fullet scraper bots.")
    parser.add_argument(
        "--mode",
        choices=("prices", "stations", "news", "all"),
        default=os.environ.get("FULLET_BOT_MODE", "all"),
        help="Bot group to run. Defaults to FULLET_BOT_MODE or all.",
    )
    return parser.parse_args()


def run_bot(script_name, env_overrides=None, timeout=180):
    print("\n=====================================")
    print(f"Running: {script_name}")
    print("=====================================")
    start_time = time.time()

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
    if result.returncode == 0:
        print(f"[OK] {script_name} finished in {elapsed:.1f}s.")
        return True

    print(f"[FAIL] {script_name} exited with code {result.returncode} in {elapsed:.1f}s.")
    return False


def _run_bot_group(bots, *, failures, bot_env):
    for bot in bots:
        timeout = 300
        if bot == "shell_station_bot.py":
            timeout = 600
        elif bot == "shell_bot.py":
            timeout = 3600

        try:
            ok = run_bot(bot, env_overrides=bot_env, timeout=timeout)
        except subprocess.TimeoutExpired:
            ok = False
            print(f"[FAIL] {bot} timed out.")
        if not ok:
            failures.append(bot)


def _run_news_bot(*, failures):
    try:
        news_ok = run_bot("news_bot.py", timeout=90)
    except subprocess.TimeoutExpired:
        news_ok = False
        print("[FAIL] news_bot.py timed out.")
    if not news_ok:
        failures.append("news_bot.py")


def main():
    args = parse_args()
    print(f"Fullet scraper orchestrator starting. Mode: {args.mode}")
    failures = []

    bot_env = {"FULLET_PUSH_SUMMARY": "0"}

    if args.mode in ("stations", "all"):
        _run_bot_group(STATION_BOTS, failures=failures, bot_env=bot_env)

    if args.mode in ("prices", "all"):
        _run_bot_group(PRICE_BOTS, failures=failures, bot_env=bot_env)

    if args.mode in ("news", "all"):
        _run_news_bot(failures=failures)

    if failures:
        print(f"[WARN] Completed with failing/skipped bots: {', '.join(failures)}")
        return 1

    print("[OK] All configured bots completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
