import os
import argparse
import concurrent.futures
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
    "shell_bot.py": 1800,
    "news_bot.py": 90,
}

DEFAULT_BOT_TIMEOUT_SECONDS = 300
TOLERATED_FAILURE_BOTS = {
    "shell_bot.py",
    "shell_station_bot.py",
}

# Her bot bağımsız bir web sitesini kazıyor — aynı anda birden fazla botun
# ayrı subprocess olarak çalışması, tek bir botun (örn. shell_bot.py) kendi
# içindeki sıralı kazıma mantığını etkilemez. shell_bot.py'nin KENDİ hedef
# döngüsü hâlâ tek sayfa/tek tarayıcı ile sıralı çalışıyor (site eşzamanlı
# bağlantıyı engelliyor, bkz. commit b5bc23e) — burada değiştirilmiyor.
BOT_MAX_RETRIES = 1  # ek deneme sayısı — toplam deneme = 1 + BOT_MAX_RETRIES
BOT_RETRY_BACKOFF_SECONDS = 20


def parse_args():
    parser = argparse.ArgumentParser(description="Run Fullet scraper bots.")
    parser.add_argument(
        "--mode",
        choices=("prices", "stations", "news", "all"),
        default=os.environ.get("FULLET_BOT_MODE", "all"),
        help="Bot group to run. Defaults to FULLET_BOT_MODE or all.",
    )
    return parser.parse_args()


def fail_on_bot_error():
    return os.environ.get("FULLET_FAIL_ON_BOT_ERROR", "1") == "1"


def is_tolerated_failure(bot_name):
    return bot_name in TOLERATED_FAILURE_BOTS


def should_open_failure_alert(bot_name):
    return fail_on_bot_error() and not is_tolerated_failure(bot_name)


def _run_subprocess_once(script_name, env_overrides, timeout, mode):
    """Tek bir deneme: subprocess'i çalıştırır, telemetriyi kaydeder, başarı
    durumunu döner. Alarm kararı vermez — bu, retry sarmalayıcısının işi
    (aksi halde her ara deneme kendi başına gürültülü alarm açar/kapatırdı)."""
    print("\n=====================================")
    print(f"Running: {script_name}")
    print("=====================================")
    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    try:
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
    except subprocess.TimeoutExpired as exc:
        now = datetime.now(timezone.utc)
        record_bot_run(
            bot_name=script_name,
            mode=mode,
            status="timeout",
            started_at=started_at,
            finished_at=now,
            duration_seconds=timeout,
            exit_code=None,
            summary=f"{script_name} timed out after {timeout}s",
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout,
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr,
        )
        print(f"[FAIL] {script_name} timed out after {timeout}s.")
        return False

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
        print(f"[OK] {script_name} finished in {elapsed:.1f}s.")
        return True

    print(f"[FAIL] {script_name} exited with code {result.returncode} in {elapsed:.1f}s.")
    return False


def run_bot_with_retries(script_name, env_overrides=None, timeout=180, mode=None):
    """Bot'u en fazla (1 + BOT_MAX_RETRIES) kez dener, aralarında backoff
    bekler. Başarı/başarısızlık kararı ve alarm burada, tek yerde verilir."""
    ok = False
    for attempt in range(BOT_MAX_RETRIES + 1):
        if attempt > 0:
            print(
                f"[RETRY] {script_name} — deneme {attempt + 1}/{BOT_MAX_RETRIES + 1}, "
                f"{BOT_RETRY_BACKOFF_SECONDS}s bekleniyor"
            )
            time.sleep(BOT_RETRY_BACKOFF_SECONDS)
        ok = _run_subprocess_once(script_name, env_overrides, timeout, mode)
        if ok:
            break

    if ok:
        resolve_system_alerts(source=f"bot:{script_name}")
        return True

    if should_open_failure_alert(script_name):
        create_system_alert(
            severity="error",
            source=f"bot:{script_name}",
            title=f"{script_name} failed",
            message=f"{script_name} {BOT_MAX_RETRIES + 1} denemeden sonra başarısız oldu.",
            metadata={"mode": mode, "attempts": BOT_MAX_RETRIES + 1},
        )
    elif is_tolerated_failure(script_name):
        # Tolere edilen botlar pipeline'ı bloklamaz ama artık tamamen
        # sessiz de kalmaz — düşük öncelikli, görünür bir uyarı bırakılır.
        # Bir sonraki başarılı çalıştırmada (resolve_system_alerts,
        # yukarıdaki `if ok` dalı) otomatik kapanır.
        create_system_alert(
            severity="info",
            source=f"bot:{script_name}",
            title=f"{script_name} failed (tolerated)",
            message=(
                f"{script_name} {BOT_MAX_RETRIES + 1} denemeden sonra başarısız oldu. "
                "Bu bot tolere edilen listede olduğu için pipeline durmadı, "
                "ama veri tazeliği etkilenmiş olabilir."
            ),
            metadata={"mode": mode, "attempts": BOT_MAX_RETRIES + 1},
        )
    return False


def _run_bot_group(bots, *, failures, bot_env, mode):
    """Bağımsız botları paralel çalıştırır — her biri ayrı bir web sitesini
    kazıdığı için aralarında yarış durumu yok. Bir sonraki grup (örn. price
    bots), bu grubun tamamı bitmeden başlamaz (istasyon verisi fiyat
    eşleştirmesinden önce hazır olmalı)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(bots)) as executor:
        future_to_bot = {
            executor.submit(
                run_bot_with_retries,
                bot,
                bot_env,
                BOT_TIMEOUTS_SECONDS.get(bot, DEFAULT_BOT_TIMEOUT_SECONDS),
                mode,
            ): bot
            for bot in bots
        }
        for future in concurrent.futures.as_completed(future_to_bot):
            bot = future_to_bot[future]
            if not future.result():
                failures.append(bot)


def _run_news_bot(*, failures, mode):
    ok = run_bot_with_retries(
        "news_bot.py", timeout=BOT_TIMEOUTS_SECONDS["news_bot.py"], mode=mode
    )
    if not ok:
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

    if args.mode == "all":
        print("\n=====================================")
        print("Running: quarantine_old_prices.py")
        print("=====================================")
        subprocess.run(
            [sys.executable, str(SCRAPER_DIR / "quarantine_old_prices.py")],
            cwd=SCRAPER_DIR,
            env=bot_env,
        )

    if failures:
        print(f"[WARN] Completed with failing/skipped bots: {', '.join(failures)}")
        critical_failures = [bot for bot in failures if not is_tolerated_failure(bot)]
        if fail_on_bot_error() and critical_failures:
            return 1
        print("[WARN] Bot failures were recorded as telemetry; health checks decide workflow status.")
        return 0

    print("[OK] All configured bots completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
