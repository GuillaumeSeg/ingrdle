import argparse
import gzip
import json
from pathlib import Path

from rich.console import Console

DATA_DIR = Path(__file__).resolve().parent / "data"
LEGACY_JSONL_PATH = DATA_DIR / "openfoodfacts-products.jsonl.gz"
ARCHIVE_PATTERN = "*-openfoodfact-products.jsonl.gz"
console = Console()


def find_latest_jsonl() -> Path | None:
    archives = list(DATA_DIR.glob(ARCHIVE_PATTERN))
    if LEGACY_JSONL_PATH.exists():
        archives.append(LEGACY_JSONL_PATH)
    if not archives:
        return None
    return max(archives, key=lambda archive: archive.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open the latest downloaded Open Food Facts JSONL archive."
    )
    parser.parse_args()

    archive = find_latest_jsonl()
    if archive is None:
        parser.error("No JSONL archive found. Run scripts/download_jsonl.py first.")

    try:
        with gzip.open(archive, "rt", encoding="utf-8") as products:
            first_line = products.readline()
        if not first_line:
            parser.error(f"JSONL archive is empty: {archive}")
        json.loads(first_line)
    except (OSError, EOFError, json.JSONDecodeError) as error:
        parser.exit(1, f"Unable to read JSONL archive {archive}: {error}\n")

    console.print(f"JSONL archive is readable: {archive}")


if __name__ == "__main__":
    main()
