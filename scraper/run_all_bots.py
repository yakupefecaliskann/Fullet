import os
import argparse
import concurrent.futures
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from db_utils import (
    MIN_TARGET_COVERAGE,
    create_system_alert,
    record_bot_run,
    resolve_system_alerts,
)
from known_outages import EXIT_SOURCE_GONE, active_outage_for_bot

# _run_subprocess_once / run_bot_with_retries sonuçları. Eskiden bool'du;
# "kaynağı kabul edilmiş biçimde ölü" üçüncü bir durum ve bool'a sığmıyor.
OUTCOME_OK = "ok"
OUTCOME_FAILED = "failed"
OUTCOME_OUTAGE = "outage"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRAPER_DIR = Path(__file__).resolve().parent

STATION_BOTS = [
    "total_station_bot.py",
    "tp_station_bot.py",
    "shell_station_bot.py",
    "opet_station_bot.py",
    "po_station_bot.py",
    "aytemiz_station_bot.py",
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
    # 25 Ağu 2026 — 600'den 900'e. Bot 09.08-25.08 arasında KIRIKTI ve saniyeler
    # içinde 0 kayıtla dönüyordu; 600 sn o hâlin ölçüsüydü, çalışan hâlin değil.
    # Onarılmış bot 516 bölge sayfası + 1.289 detay sayfası çekiyor ve yerelde
    # 188 sn sürüyor. CI runner'ı ve kaynak yavaşladığında 600'e çarpmak,
    # tamamlanmak üzere olan bir kazımayı öldürürdü.
    "shell_station_bot.py": 900,
    # shell_bot kendi RUN_BUDGET_SECONDS'ında (1700) temiz çıkar; buradaki
    # timeout ondan BELİRGİN ölçüde büyük olmalı, yoksa süreç kazıma bitmiş
    # ama kaydetme sürerken öldürülür ve hem veri hem kapsama raporu kaybolur.
    # 280 hedef kararı için bkz. shell_bot.DEFAULT_MAX_TARGETS_PER_RUN.
    "shell_bot.py": 2100,
    "news_bot.py": 90,
}

DEFAULT_BOT_TIMEOUT_SECONDS = 300
# Shell, en büyük marka (ops_report.py'de eşik 500 istasyon) — kalıcı
# kırılsa bile pipeline'ın kırmızıya dönmemesi kabul edilemez bir kör
# noktaydı (bkz. FULLET_KOD_MIMARI_DENETIMI.md Y1). Artık tolere edilen
# hiçbir bot yok; herhangi bir bot başarısız olursa normal "error"
# alarmı açılır ve pipeline kırmızıya döner.
TOLERATED_FAILURE_BOTS: set[str] = set()

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


def _parse_scraped_records(stdout):
    """Bot stdout'undaki '[RECORDS] scraped=N ...' satırından kayıt sayısını
    çeker (bkz. db_utils.finish_bot_run). Satır yoksa None döner — eski
    formatta çıktı veren bir bot telemetride 'bilinmiyor' olarak kalır,
    yanlışlıkla 'empty' sayılmaz."""
    if not stdout:
        return None
    match = re.search(r"^\[RECORDS\] scraped=(\d+)", stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def _parse_target_coverage(stdout):
    """'[RECORDS] ... targets_ok=A targets_total=B' -> (A, B) ya da None.

    Yalnızca hedef bazlı kazıma yapan botlar (shell_bot) bu alanları basar;
    bölgesel botlarda tek sayfa okunduğu için kapsama kavramı yoktur."""
    if not stdout:
        return None
    match = re.search(
        r"^\[RECORDS\].*\btargets_ok=(\d+) targets_total=(\d+)",
        stdout,
        re.MULTILINE,
    )
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _run_subprocess_once(script_name, env_overrides, timeout, mode):
    """Tek bir deneme: subprocess'i çalıştırır, telemetriyi kaydeder, sonucu
    (OUTCOME_*) döner. Alarm kararı vermez — bu, retry sarmalayıcısının işi
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
        return OUTCOME_FAILED

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    elapsed = time.time() - start_time
    finished_at = datetime.now(timezone.utc)
    records = _parse_scraped_records(result.stdout)

    # --- Kaynağı ölmüş bot: "kırık" değil, "yok" -----------------------------
    # EXIT_SOURCE_GONE, botun kaynağın ayakta OLMADIĞINI doğruladığı anlamına
    # gelir (shell_bot._verify_source). Bunu yalnızca known_outages.py'de
    # GEÇERLİ bir kaydı varsa hoş görürüz; kaydı yoksa ya da süresi dolmuşsa
    # bu YENİ bir haberdir ve normal bir arıza gibi gürültü çıkarmalıdır.
    outage = active_outage_for_bot(script_name)
    if result.returncode == EXIT_SOURCE_GONE and outage:
        # 'skipped' dürüst olan: bot çalıştı ama işini YAPMADI, çünkü
        # gidilecek yer yoktu. 'success' yalan, 'failed' ise bu bağlamda
        # yanlış yere işaret eder (kodda düzeltilecek bir şey yok).
        record_bot_run(
            bot_name=script_name,
            mode=mode,
            status="skipped",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=elapsed,
            exit_code=result.returncode,
            summary=f"{script_name} atlandı: kaynak kapalı ({outage.describe()})",
            stdout=result.stdout,
            stderr=result.stderr,
            records_written=records,
            escalate_failures=False,
        )
        print(
            f"[BILINEN-ARIZA] {script_name} atlandı ({elapsed:.1f}s): "
            f"{outage.describe()}."
        )
        return OUTCOME_OUTAGE

    status = "success" if result.returncode == 0 else "failed"
    # Savunma hattı: bot exit 0 dönse bile 0 kayıt scrape ettiyse bu bir
    # başarı değildir. (Botların kendisi de bu durumda exit 1 döner —
    # bkz. finish_bot_run — ama helper'ı çağırmayan/eski bir bot buradan
    # yakalanır.) 'empty' status'u bot_runs CHECK kısıtında tanımlı olmalı:
    # database/add_bot_runs_records_written.sql
    if status == "success" and records == 0:
        status = "empty"

    # Kısmi kazıma: veri yazıldı ama hedeflerin çoğu okunamadı. 'success'
    # demek yalan, 'failed' demek abartı olurdu (bkz. finish_bot_run).
    coverage = _parse_target_coverage(result.stdout)
    if status == "success" and coverage:
        targets_ok, targets_total = coverage
        ratio = targets_ok / targets_total if targets_total else 1.0
        if ratio < MIN_TARGET_COVERAGE:
            status = "degraded"
            create_system_alert(
                severity="warning",
                source=f"bot:{script_name}",
                title=f"{script_name} hedeflerin çoğunu okuyamadı",
                message=(
                    f"{script_name} {targets_total} hedeften yalnızca {targets_ok}'sini "
                    f"okuyabildi (%{ratio * 100:.0f} < %{MIN_TARGET_COVERAGE * 100:.0f}). "
                    "Yazılan veri doğru ama eksik; kapsanmayan istasyonların "
                    "fiyatları bayatlayacak."
                ),
                metadata={
                    "targets_ok": targets_ok,
                    "targets_total": targets_total,
                    "coverage": round(ratio, 3),
                },
            )
        else:
            resolve_system_alerts(
                source=f"bot:{script_name}",
                title=f"{script_name} hedeflerin çoğunu okuyamadı",
            )
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
        records_written=records,
        # Kapsama, status'ten BAĞIMSIZ olarak her koşuda yazılır: yalnızca
        # 'degraded' koşularda saklamak trendi görünmez kılar (%100'den
        # %71'e inen bir bot eşiği geçene kadar sessiz kalırdı).
        targets_ok=coverage[0] if coverage else None,
        targets_total=coverage[1] if coverage else None,
    )
    if status == "success":
        print(f"[OK] {script_name} finished in {elapsed:.1f}s.")
        return OUTCOME_OK

    if status == "degraded":
        # Kısmi veri başarısızlık değildir: yeniden denemek aynı 9 dakikalık
        # kazımayı tekrarlar ve pipeline'ı kalıcı kırmızıya boyar. Durum
        # bot_runs'ta ve açık bir system_alert'te görünür — sessiz değil.
        print(f"[DEGRADED] {script_name} finished in {elapsed:.1f}s with partial coverage.")
        return OUTCOME_OK

    if status == "empty":
        print(f"[FAIL] {script_name} exited 0 but scraped 0 records in {elapsed:.1f}s.")
    elif result.returncode == EXIT_SOURCE_GONE:
        # Kaynak öldü ama kaydı yok / kaydın süresi dolmuş: BU HABERDİR.
        print(
            f"[FAIL] {script_name} kaynağının ayakta olmadığını bildirdi ama "
            "known_outages.py'de geçerli bir kaydı yok. Ya kaynak yeni öldü "
            "(kaydı ekle) ya da mevcut kaydın gözden geçirme tarihi geçti."
        )
    else:
        print(f"[FAIL] {script_name} exited with code {result.returncode} in {elapsed:.1f}s.")
    return OUTCOME_FAILED


def run_bot_with_retries(script_name, env_overrides=None, timeout=180, mode=None):
    """Bot'u en fazla (1 + BOT_MAX_RETRIES) kez dener, aralarında backoff
    bekler. Sonuç kararı ve alarm burada, tek yerde verilir. OUTCOME_* döner."""
    outcome = OUTCOME_FAILED
    for attempt in range(BOT_MAX_RETRIES + 1):
        if attempt > 0:
            print(
                f"[RETRY] {script_name} — deneme {attempt + 1}/{BOT_MAX_RETRIES + 1}, "
                f"{BOT_RETRY_BACKOFF_SECONDS}s bekleniyor"
            )
            time.sleep(BOT_RETRY_BACKOFF_SECONDS)
        outcome = _run_subprocess_once(script_name, env_overrides, timeout, mode)
        # Kaynağın ölü olduğu doğrulandıysa yeniden denemek aynı 404'ü
        # tekrar sormaktır: tek kazandığı, günlüğü ikiye katlamak.
        if outcome in (OUTCOME_OK, OUTCOME_OUTAGE):
            break

    if outcome == OUTCOME_OUTAGE:
        # `_run_subprocess_once` bunu yalnızca geçerli bir kayıt bulduğunda
        # döner, ama kayıt tam bu iki çağrı arasında süresini doldurmuş
        # olabilir (gece yarısını geçen koşu). O durumda `None` gelir ve
        # `outage.describe()` bütün orkestratörü öldürürdü — bir raporlama
        # ayrıntısı uğruna kaybedilecek en pahalı şey koşunun kendisidir.
        outage = active_outage_for_bot(script_name)
        if outage is None:
            print(
                f"[FAIL] {script_name} kaydının süresi koşu sırasında doldu — "
                "gözden geçirilmesi gerekiyor."
            )
            return OUTCOME_FAILED
        # Kaynağın ölümünü anlatan TEK bir açık uyarı bırakılır. Ondan önce,
        # bu arıza "onarılabilir bir hata" sanıldığı dönemden kalan error ve
        # critical alarmlar kapatılır — yoksa panoda kalıcı olarak kırmızı
        # durur ve bir sonraki GERÇEK kritik alarmı görünmez kılarlar.
        for title in (
            f"{script_name} failed",
            f"{script_name} arka arkaya başarısız",
            f"{script_name} timed out",
        ):
            resolve_system_alerts(source=f"bot:{script_name}", title=title)
        create_system_alert(
            severity="warning",
            source=f"bot:{script_name}",
            title=f"{script_name} kaynağı kapalı (bilinen arıza)",
            message=(
                f"{script_name} atlandı: {outage.describe()}. "
                f"Kaynak: {outage.url}. {outage.reason} "
                "Bu kayıt gözden geçirme tarihinde kendiliğinden susturmayı "
                "bırakır ve sağlık kontrolü yeniden kırmızıya döner."
            ),
            metadata={
                "mode": mode,
                "url": outage.url,
                "since": outage.since.isoformat(),
                "review_by": outage.review_by.isoformat(),
            },
        )
        return OUTCOME_OUTAGE

    if outcome == OUTCOME_OK:
        # Yalnızca BU sarmalayıcının açtığı başarısızlık alarmlarını kapat.
        # Kaynağın tamamını körü körüne kapatmak, aynı kaynağa yazan diğer
        # alarmları (hedef kapsaması uyarısı, ardışık-hata alarmı) da
        # susturur — ops_report'ta tam bu hata vardı (yol haritası S3-1).
        for title in (
            f"{script_name} failed",
            f"{script_name} failed (tolerated)",
            f"{script_name} timed out",
            # Kaynak geri döndü: ölüm ilanı da kapanmalı. known_outages.py
            # kaydının SİLİNMESİ ayrıca backend_health_check tarafından
            # kırmızıyla istenir — bu resolve onu gizlemez, farklı title.
            f"{script_name} kaynağı kapalı (bilinen arıza)",
        ):
            resolve_system_alerts(source=f"bot:{script_name}", title=title)
        return OUTCOME_OK

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
    return OUTCOME_FAILED


def _run_bot_group(bots, *, failures, outages, bot_env, mode):
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
            outcome = future.result()
            if outcome == OUTCOME_OUTAGE:
                outages.append(bot)
            elif outcome != OUTCOME_OK:
                failures.append(bot)


def _run_news_bot(*, failures, outages, mode):
    outcome = run_bot_with_retries(
        "news_bot.py", timeout=BOT_TIMEOUTS_SECONDS["news_bot.py"], mode=mode
    )
    if outcome == OUTCOME_OUTAGE:
        outages.append("news_bot.py")
    elif outcome != OUTCOME_OK:
        failures.append("news_bot.py")


def main():
    args = parse_args()
    print(f"Fullet scraper orchestrator starting. Mode: {args.mode}")
    failures = []
    outages = []

    bot_env: dict[str, str] = {}

    if args.mode in ("stations", "all"):
        _run_bot_group(
            STATION_BOTS, failures=failures, outages=outages, bot_env=bot_env, mode=args.mode
        )

    if args.mode in ("prices", "all"):
        _run_bot_group(
            PRICE_BOTS, failures=failures, outages=outages, bot_env=bot_env, mode=args.mode
        )

    if args.mode in ("news", "all"):
        _run_news_bot(failures=failures, outages=outages, mode=args.mode)

    # Fiyat tazeliği bakımı her fiyat koşusundan sonra çalışmalı. Eskiden bu
    # blok yalnızca mode == "all" iken çalışıyordu — ama cron hiçbir zaman
    # "all" göndermiyor (prices/news/stations), yani bu adım üretimde HİÇ
    # koşmadı (yol haritası S1-5).
    if args.mode in ("prices", "all"):
        print("\n=====================================")
        print("Running: quarantine_old_prices.py")
        print("=====================================")
        # env=bot_env ortamı GENİŞLETMEZ, EZER: alt sürece yalnızca `bot_env`
        # geçiyordu; SUPABASE_URL, servis anahtarı, FULLET_ALLOW_DB_WRITE ve
        # hatta PATH yoktu. Script bunu görüp exit 1 ile çıkıyor, dönüş kodu
        # da kontrol edilmiyordu.
        quarantine_env = os.environ.copy()
        quarantine_env.update(bot_env)
        result = subprocess.run(
            [sys.executable, str(SCRAPER_DIR / "quarantine_old_prices.py")],
            cwd=SCRAPER_DIR,
            env=quarantine_env,
        )
        if result.returncode != 0:
            print(
                f"[FAIL] quarantine_old_prices.py exited with code {result.returncode}."
            )
            failures.append("quarantine_old_prices.py")
            create_system_alert(
                severity="error",
                source="bot:quarantine_old_prices.py",
                title="quarantine_old_prices.py failed",
                message=(
                    "Fiyat tazelik bakımı başarısız oldu — bayat fiyatlar "
                    "işaretlenmemiş olabilir."
                ),
                metadata={"mode": args.mode, "exit_code": result.returncode},
            )
        else:
            resolve_system_alerts(source="bot:quarantine_old_prices.py")

    # Kaynağı kabul edilmiş biçimde ölü botlar pipeline'ı KIRMIZIYA
    # DÖNDÜRMEZ ama asla sessiz de kalmaz: her koşuda adıyla ve gözden
    # geçirme tarihiyle basılır, ayrıca açık bir `warning` alarmı taşır.
    if outages:
        print(
            f"[BILINEN-ARIZA] Kaynağı kapalı olduğu için atlanan bot(lar): "
            f"{', '.join(outages)} — ayrıntı için known_outages.py."
        )

    if failures:
        print(f"[WARN] Completed with failing/skipped bots: {', '.join(failures)}")
        critical_failures = [bot for bot in failures if not is_tolerated_failure(bot)]
        if fail_on_bot_error() and critical_failures:
            return 1
        print("[WARN] Bot failures were recorded as telemetry; health checks decide workflow status.")
        return 0

    if outages:
        print("[OK] Kaynağı ayakta olan tüm botlar tamamlandı.")
    else:
        print("[OK] All configured bots completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
