# scripts/prepare.py

import argparse
import csv
import gzip
import os
import random
import sys
from typing import TextIO

import requests

# Increase the CSV field size limit (default is 128KB, some products exceed it)
csv.field_size_limit(sys.maxsize)

# ─── CONFIG ────────────────────────────────────────────────────
CSV_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
CSV_PATH = "scripts/data/off_products.csv.gz"
TEST_CSV_PATH = "scripts/data/off_products_test.csv"
TEST_PRODUCT_FIELDS = ("code", "product_name", "ingredients_text", "image_url")
MIN_INGREDIENTS = 5
# ───────────────────────────────────────────────────────────────


def download_csv() -> None:
    """Download the CSV once (~1.28 GB) with a progress bar."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if os.path.exists(CSV_PATH):
        print(f"✅ CSV already present: {CSV_PATH}")
        return

    print("⏳ Downloading CSV (~1.28 GB, first time only)...")
    resp = requests.get(
        CSV_URL,
        stream=True,
        timeout=300,
        headers={"User-Agent": "Ingrdle/0.0.1 (guillaume.segado@pm.me)"},
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


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """Render an ASCII progress bar: [████████░░░░░░░░] 33%"""
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = current / total * 100
    return f"\r  [{bar}] {pct:.0f}%  ({current:,} / {total:,})"


def open_product_file(path: str) -> TextIO:
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "rt", encoding="utf-8", newline="")


def is_qualified(row: dict[str, str | None]) -> bool:
    return bool(
        (row.get("product_name") or "").strip() and (row.get("image_url") or "").strip()
    )


def export_test_csv(n: int = 15) -> None:
    os.makedirs(os.path.dirname(TEST_CSV_PATH), exist_ok=True)
    exported = 0

    with (
        open_product_file(CSV_PATH) as source,
        open(TEST_CSV_PATH, "w", encoding="utf-8", newline="") as destination,
    ):
        reader = csv.DictReader(source, delimiter="\t")
        writer = csv.DictWriter(destination, fieldnames=TEST_PRODUCT_FIELDS)
        writer.writeheader()

        for row in reader:
            if not is_qualified(row):
                continue

            writer.writerow(
                {field: row.get(field, "") or "" for field in TEST_PRODUCT_FIELDS}
            )
            exported += 1
            if exported == n:
                break

    print(f"✅ Exported {exported} test products: {TEST_CSV_PATH}")


def load_and_pick(
    n: int = 2, csv_path: str = CSV_PATH, delimiter: str = "\t"
) -> list[dict[str, str]]:
    """Read the CSV and pick n random qualified products."""
    # First pass: count total rows
    print("⏳ Counting rows...")
    total_rows = 0
    with open_product_file(csv_path) as f:
        next(f)  # skip header
        for _ in f:
            total_rows += 1
    print(f"  {total_rows:,} rows total\n")

    # Second pass: parse + filter with progress
    print("⏳ Reading CSV + filtering...")
    qualified = []
    processed = 0

    with open_product_file(csv_path) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            processed += 1

            if processed % 50_000 == 0:
                print(progress_bar(processed, total_rows), end="", flush=True)

            if not is_qualified(row):
                continue

            qualified.append(
                {
                    "code": row.get("code", ""),
                    "product_name": row.get("product_name", ""),
                }
            )

    print(progress_bar(total_rows, total_rows))
    print(f"✅ {len(qualified)} qualified products found")

    if len(qualified) < n:
        print(f"⚠️  Only {len(qualified)} qualified, picking all")
        return qualified

    return random.sample(qualified, n)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--create-test-csv", action="store_true")
    mode.add_argument("--use-test-csv", action="store_true")
    args = parser.parse_args()

    if args.create_test_csv:
        download_csv()
        export_test_csv()
        return

    if args.use_test_csv:
        if not os.path.exists(TEST_CSV_PATH):
            parser.error("Test CSV not found. Run with --create-test-csv first.")
        winners = load_and_pick(n=2, csv_path=TEST_CSV_PATH, delimiter=",")
    else:
        download_csv()
        winners = load_and_pick(n=2)

    print("\n🎯 Selected products:")
    for index, product in enumerate(winners, start=1):
        print(f"{index}. {product['product_name']} (code: {product['code']})")


if __name__ == "__main__":
    main()
