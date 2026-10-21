"""
indexnow_ping.py — Automated IndexNow Instant Search Engine Submission

Reads all live URLs from d:\\Daas\\sitemap.xml and submits them in a single
batch POST to https://api.indexnow.org/indexnow so Bing, Microsoft Copilot,
DuckDuckGo, Yandex, ChatGPT Search, and Perplexity index all 173+ SignalTender
pages (/contracts/rfp/<slug>.html, state SLED hubs, index.html, apis.html)
within minutes instead of waiting weeks for organic crawl discovery.
"""

from __future__ import annotations

import os
import re
import requests
from dotenv import load_dotenv
from error_telemetry import configure_utf8_stdio, report_error

configure_utf8_stdio()
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")

INDEXNOW_HOST = "signaltender.net"
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "8f9d2a4c6e1b3f5a7d0c9e2b4a6f8d1c").strip()
INDEXNOW_KEY_LOCATION = f"https://{INDEXNOW_HOST}/{INDEXNOW_KEY}.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


def extract_sitemap_urls(sitemap_path: str = SITEMAP_PATH) -> list[str]:
    if not os.path.exists(sitemap_path):
        return []
    with open(sitemap_path, "r", encoding="utf-8") as f:
        xml_txt = f.read()
    urls = [u.strip() for u in re.findall(r"<loc>(.*?)</loc>", xml_txt, flags=re.I) if u.strip()]
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen and url.startswith(f"https://{INDEXNOW_HOST}"):
            seen.add(url)
            ordered.append(url)
    return ordered


def submit_indexnow_urls(urls: list[str] | None = None) -> dict:
    """
    Submits all URLs from sitemap.xml to https://api.indexnow.org/indexnow.
    Returns status dictionary. Never raises so pipeline runs are never blocked.
    """
    target_urls = urls if urls is not None else extract_sitemap_urls()
    if not target_urls:
        print("[IndexNow] No URLs found in sitemap.xml to submit.", flush=True)
        return {"submitted": 0, "status_code": 0}

    payload = {
        "host": INDEXNOW_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": INDEXNOW_KEY_LOCATION,
        "urlList": target_urls[:10000],
    }

    try:
        resp = requests.post(
            INDEXNOW_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=12,
        )
        status = resp.status_code
        if status in (200, 202):
            print(
                f"[IndexNow] [+] Submitted {len(target_urls)} live SignalTender URLs to IndexNow (HTTP {status}).",
                flush=True,
            )
        else:
            print(
                f"[IndexNow] [!] IndexNow returned HTTP {status} (key file propagation may still be in progress): {resp.text[:160]}",
                flush=True,
            )
        return {"submitted": len(target_urls), "status_code": status}
    except Exception as exc:
        print(f"[IndexNow] [!] Non-blocking IndexNow ping warning: {exc}", flush=True)
        return {"submitted": 0, "status_code": 0, "error": str(exc)}


if __name__ == "__main__":
    submit_indexnow_urls()

