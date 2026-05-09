import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from db_utils import clean_text, is_write_allowed, send_summary_push, supabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=akaryak%C4%B1t%20zamm%C4%B1%20OR%20benzin%20indirimi%20OR%20motorin&hl=tr&gl=TR&ceid=TR:tr"
)


def scrape_fuel_news():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] News bot started.")
    news_items = []

    try:
        response = requests.get(
            RSS_URL,
            headers={"User-Agent": "Mozilla/5.0 (Fullet news monitor)"},
            timeout=15,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            return []

        for item in channel.findall("item")[:12]:
            title = clean_text(item.findtext("title"))
            link = clean_text(item.findtext("link"))
            source = clean_text(item.findtext("source")) or "Haber"
            pub_date = clean_text(item.findtext("pubDate"))
            if not title or not link:
                continue

            clean_title = title.split(" - ")[0].strip()
            parsed_date = None
            if pub_date:
                try:
                    parsed_date = parsedate_to_datetime(pub_date).isoformat()
                except Exception:
                    parsed_date = None

            news_items.append({
                "baslik": clean_title,
                "link": link,
                "kaynak": source,
                "tarih": parsed_date,
            })
    except Exception as exc:
        print(f"[WARN] News scrape failed: {exc}")

    return news_items


def save_news(news_items):
    if os.environ.get("FULLET_DRY_RUN", "0") == "1":
        print(f"[DRY] News items: {len(news_items)}")
        return 0

    if not news_items:
        print("[FAIL] News source returned no items.")
        return -1

    if not is_write_allowed():
        print("[SAFE] DB write blocked. Set FULLET_ALLOW_DB_WRITE=1 to write live news.")
        print(f"[SAFE] Pending news items: {len(news_items)}")
        return 0

    if not supabase:
        print("[FAIL] Supabase env values are missing. News not written.")
        return -1

    inserted = 0
    write_errors = 0
    for news in news_items:
        try:
            payload = {
                "baslik": news["baslik"],
                "link": news["link"],
                "kaynak": news["kaynak"],
            }
            if news.get("tarih"):
                payload["tarih"] = news["tarih"]
            existing = (
                supabase.table("haberler")
                .select("id")
                .eq("link", news["link"])
                .limit(1)
                .execute()
                .data
            )
            if existing:
                response = (
                    supabase.table("haberler")
                    .update(payload)
                    .eq("id", existing[0]["id"])
                    .execute()
                )
            else:
                response = supabase.table("haberler").insert(payload).execute()
            if response.data:
                inserted += len(response.data)
        except Exception as exc:
            write_errors += 1
            print(f"[WARN] News write skipped: {exc}")

    if write_errors == len(news_items):
        print("[FAIL] All news writes failed.")
        return -1

    if inserted and os.environ.get("FULLET_NEWS_PUSH", "0") == "1":
        send_summary_push("Akaryakit haberleri guncellendi.", is_zam=True)

    return inserted


if __name__ == "__main__":
    items = scrape_fuel_news()
    count = save_news(items)
    if count < 0:
        raise SystemExit(1)
    print(f"[OK] News bot finished. Processed: {count}.")
