from __future__ import annotations

import requests
from datetime import datetime, timezone
from typing import Any

from config import supabase
from normalization import clean_text

def _compact_log(value: Any, limit: int = 4000) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."

def _observability_table_missing(exc: Exception) -> bool:
    text = str(exc)
    return (
        "system_alerts" in text
        or "bot_runs" in text
        or "Could not find the table" in text
        or "relation" in text and "does not exist" in text
        or "PGRST205" in text
    )

# Bot'un ÖLÜ olmadığını gösteren durumlar. 'degraded' = "veri yazıldı ama
# hedeflerin bir kısmı okunamadı" (bkz. db_utils.MIN_TARGET_COVERAGE,
# database/add_bot_runs_degraded_status.sql) — tasarım gereği başarısızlık
# DEĞİLDİR ve ardışık-hata eskalasyonuna girmemelidir.
#
# Eskiden girerdi: 2 Ağustos 23:00 ve 23:26'daki iki degraded Shell koşusu
# üretimde 23:11'de "shell_bot.py arka arkaya başarısız" başlıklı CRITICAL
# alarm açtı — bot aslında her iki koşuda da yüzlerce fiyat yazmıştı.
# Kapsama düşüklüğünün kendi `warning` alarmı zaten var; onu bu değişiklik
# etkilemez (farklı title ile açılır ve açık kalır).
NON_FAILURE_STATUSES = ("success", "ok", "degraded")

# Migration gerektiren opsiyonel bot_runs kolonları. Kolon yoksa insert
# bunlar düşürülerek tekrarlanır (aşağıya bkz.).
_OPTIONAL_RUN_COLUMNS = ("records_written", "targets_ok", "targets_total")


def record_bot_run(
    *,
    bot_name: str,
    mode: str | None,
    status: str,
    started_at: datetime,
    finished_at: datetime | None,
    duration_seconds: float | None = None,
    exit_code: int | None = None,
    summary: str | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    records_written: int | None = None,
    targets_ok: int | None = None,
    targets_total: int | None = None,
) -> None:
    if not supabase:
        return

    # --- Ardışık Hata Tespiti (INSERT'TEN ÖNCE) ---
    # Sorgu bu koşuyu henüz içermediği için current_status listeye elle
    # eklenir. Eskiden insert SONRASI çağrılıyordu ve mevcut koşu hem
    # sorgudan hem elle ekten gelip iki kez sayılıyordu — tek hata
    # "2 ardışık hata" görünüp ilk denemede critical alarm patlatıyordu.
    if status not in NON_FAILURE_STATUSES:
        _check_consecutive_failures(bot_name, current_status=status)
    else:
        # Bot çalıştı ve veri yazdı — ardışık hata alarmını kapat.
        # 'degraded' de buraya girer: kapsama düşük olsa bile bot ÖLÜ DEĞİL.
        # Kapsama sorunu run_all_bots'un ayrı `warning` alarmıyla (farklı
        # title) açık kalmaya devam eder; buradaki resolve onu kapatmaz.
        resolve_system_alerts(source=f"bot:{bot_name}", title=f"{bot_name} arka arkaya başarısız")

    payload = {
        "bot_name": clean_text(bot_name),
        "run_mode": clean_text(mode),
        "status": status,
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "finished_at": finished_at.astimezone(timezone.utc).isoformat() if finished_at else None,
        "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
        "exit_code": exit_code,
        "summary": _compact_log(summary or "", 500),
        "stdout_excerpt": _compact_log(stdout or ""),
        "stderr_excerpt": _compact_log(stderr or ""),
    }
    if records_written is not None:
        payload["records_written"] = records_written
    # Kapsama sayıları KALICI kolona yazılır. stdout_excerpt'e güvenilemez:
    # _compact_log ilk 4000 karakteri tutar, [RECORDS] satırı ise ~150
    # hedeflik koşunun SONUNDA basılır — canlıda 20 shell_bot kaydının
    # hiçbirinde kapsama satırı yoktu. Kolon olmadan başarılı koşuların
    # kapsama trendi ölçülemiyor (bkz. add_bot_runs_target_coverage.sql).
    if targets_total is not None:
        payload["targets_ok"] = targets_ok
        payload["targets_total"] = targets_total
    try:
        supabase.table("bot_runs").insert(payload).execute()
    except Exception as exc:
        # Opsiyonel kolonlar henüz migrate edilmemişse onlarsız tekrar dene.
        # Telemetriyi TAMAMEN kaybetmektense eksik kolonla yazmak yeğdir —
        # sessiz bot arızalarını görünür kılan tek kayıt burası.
        missing = [c for c in _OPTIONAL_RUN_COLUMNS if c in str(exc) and c in payload]
        if missing:
            print(
                f"[WARN] bot_runs.{'/'.join(missing)} kolonu yok; "
                f"database/ altındaki ilgili migration'ı çalıştırın."
            )
            try:
                fallback = {k: v for k, v in payload.items() if k not in missing}
                supabase.table("bot_runs").insert(fallback).execute()
            except Exception as fallback_exc:
                if not _observability_table_missing(fallback_exc):
                    print(f"[WARN] Bot run telemetry skipped: {fallback_exc}")
        elif not _observability_table_missing(exc):
            print(f"[WARN] Bot run telemetry skipped: {exc}")


def _check_consecutive_failures(bot_name: str, current_status: str) -> None:
    """Son 3 bot çalışmasına bak; 2+ ardışık hata varsa critical alert yayınla."""
    if not supabase:
        return
    try:
        recent = (
            supabase.table("bot_runs")
            .select("status,started_at")
            .eq("bot_name", clean_text(bot_name))
            .order("started_at", desc=True)
            .limit(3)
            .execute()
            .data
            or []
        )
        # Mevcut çalışmayı (henüz insert edilmedi) dahil et
        statuses = [current_status] + [r.get("status", "") for r in recent]
        consecutive_failures = 0
        for s in statuses:
            # 'degraded' seriyi KIRAR: eksik de olsa veri yazılmış demektir.
            if s not in NON_FAILURE_STATUSES:
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= 2:
            create_system_alert(
                severity="critical",
                source=f"bot:{bot_name}",
                title=f"{bot_name} arka arkaya başarısız",
                message=(
                    f"{bot_name} son {consecutive_failures} çalışmada hata verdi. "
                    f"Son durum: {current_status}. "
                    f"Veri güncellemesi durmuş olabilir."
                ),
                metadata={"consecutive_failures": consecutive_failures, "last_status": current_status},
            )
            print(f"[CRITICAL] {bot_name} arka arkaya {consecutive_failures} kez başarısız — alarm oluşturuldu.")
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] Consecutive failure check skipped: {exc}")

def _send_discord_webhook(title: str, message: str, severity: str) -> None:
    from config import _get_env
    webhook_url = _get_env("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    color = 16711680 if severity in {"error", "critical"} else 16776960
    payload = {
        "embeds": [{
            "title": f"[{severity.upper()}] {title}",
            "description": message[:2048],
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as exc:
        print(f"[WARN] Failed to send Discord webhook: {exc}")

def create_system_alert(
    *,
    severity: str,
    source: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    _send_discord_webhook(title, message, severity)
    if not supabase:
        return
    severity = severity if severity in {"info", "warning", "error", "critical"} else "warning"
    source = clean_text(source)[:120]
    title = clean_text(title)[:160]
    payload = {
        "severity": severity,
        "source": source,
        "title": title,
        "message": _compact_log(message, 2000),
        "status": "open",
        "metadata": metadata or {},
    }
    try:
        existing = (
            supabase.table("system_alerts")
            .select("id")
            .eq("source", source)
            .eq("title", title)
            .eq("status", "open")
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            supabase.table("system_alerts").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            supabase.table("system_alerts").insert(payload).execute()
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] System alert skipped: {exc}")

def resolve_system_alerts(*, source: str, title: str | None = None) -> None:
    if not supabase:
        return
    try:
        query = (
            supabase.table("system_alerts")
            .update({
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("source", clean_text(source)[:120])
            .eq("status", "open")
        )
        if title:
            query = query.eq("title", clean_text(title)[:160])
        query.execute()
    except Exception as exc:
        if not _observability_table_missing(exc):
            print(f"[WARN] System alert resolve skipped: {exc}")
