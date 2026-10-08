# scripts/prepare.py

import requests
import random
import json
import csv
import gzip
import os
import sys

# Increase the CSV field size limit (default is 128KB, some products exceed it)
csv.field_size_limit(sys.maxsize)

# ─── CONFIG ───────────────────────────────────────────────
CSV_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
CSV_PATH = "scripts/data/off_products.csv.gz"
MIN_INGREDIENTS = 5
# ──────────────────────────────────────────────────────────

def download_csv():
    """Download the CSV once (~1.28 GB) with a progress bar."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if os.path.exists(CSV_PATH):
        print(f"✅ CSV already present: {CSV_PATH}")
        return

    print(f"⏳ Downloading CSV (~1.28 GB, first time only)...")
    resp = requests.get(
        CSV_URL,
        stream=True,
        timeout=300,
        headers={"User-Agent": "Ingrdle/0.0.1 (guillaume.segado@pm.me)"}
    )
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(CSV_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1 MB per chunk
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                mb = downloaded // (1024 * 1024)
                total_mb = total // (1024 * 1024)
                print(f"\r  {mb}/{total_mb} MB ({pct:.0f}%)", end="", flush=True)

    print(f"\n✅ Downloaded: {CSV_PATH}")

def progress_bar(current, total, width=40):
    """Render an ASCII progress bar: [████████░░░░░░░░] 33%"""
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = current / total * 100
    return f"\r  [{bar}] {pct:.0f}%  ({current:,} / {total:,})"

def load_and_pick(n=2):
    """Read the CSV and pick n random qualified products."""
    # First pass: count total rows
    print("⏳ Counting rows...")
    total_rows = 0
    with gzip.open(CSV_PATH, "rt", encoding="utf-8") as f:
        next(f)  # skip header
        for _ in f:
            total_rows += 1
    print(f"  {total_rows:,} rows total\n")

    # Second pass: parse + filter with progress
    print("⏳ Reading CSV + filtering...")
    qualified = []
    processed = 0

    with gzip.open(CSV_PATH, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed += 1

            if processed % 50_000 == 0:
                print(progress_bar(processed, total_rows), end="", flush=True)

            if not row.get("product_name"):
                continue
            if not row.get("front_image_url"):
                continue

            qualified.append({
                "code": row.get("code", ""),
                "product_name": row.get("product_name", ""),
            })

    print(progress_bar(total_rows, total_rows))
    print(f"✅ {len(qualified)} qualified products found")

    if len(qualified) < n:
        print(f"⚠️  Only {len(qualified)} qualified, picking all")
        return qualified


# ─── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Download the CSV database (one time)
    download_csv()

    # 2. Load + pick X random products
    winners = load_and_pick(n=2)