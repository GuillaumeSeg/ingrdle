import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

JSONL_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
DATA_DIR = Path(__file__).resolve().parent / "data"
LEGACY_JSONL_PATH = DATA_DIR / "openfoodfacts-products.jsonl.gz"
USER_AGENT = "Ingrdle/0.0.1 (guillaume.segado@pm.me)"
CHUNK_SIZE = 1024 * 1024
MONTHS = (
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)
console = Console()


def get_archive_path(download_date: datetime | None = None) -> Path:
    date = download_date or datetime.now(timezone.utc)
    month = MONTHS[date.month - 1]
    return DATA_DIR / f"{month}-{date.year}-openfoodfact-products.jsonl.gz"


def download_jsonl() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = get_archive_path()
    temp_path = archive_path.with_suffix(archive_path.suffix + ".part")

    if archive_path.exists():
        console.print(f"JSONL archive already present: {archive_path}")
        return

    if LEGACY_JSONL_PATH.exists():
        legacy_date = datetime.fromtimestamp(
            LEGACY_JSONL_PATH.stat().st_mtime, tz=timezone.utc
        )
        legacy_archive_path = get_archive_path(legacy_date)
        if not legacy_archive_path.exists():
            LEGACY_JSONL_PATH.replace(legacy_archive_path)
            console.print(f"Renamed existing JSONL archive: {legacy_archive_path}")
            return

    download_complete = False
    try:
        with requests.get(
            JSONL_URL,
            stream=True,
            timeout=(10, 120),
            headers={"User-Agent": USER_AGENT},
        ) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0)) or None

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading JSONL", total=total_size)
                with temp_path.open("wb") as archive:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            archive.write(chunk)
                            progress.update(task, advance=len(chunk))

        temp_path.replace(archive_path)
        download_complete = True
    finally:
        if not download_complete:
            temp_path.unlink(missing_ok=True)

    console.print(f"Downloaded JSONL archive: {archive_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the compressed Open Food Facts JSONL export."
    )
    parser.parse_args()

    try:
        download_jsonl()
    except (OSError, requests.RequestException) as error:
        parser.exit(1, f"JSONL download failed: {error}\n")


if __name__ == "__main__":
    main()
