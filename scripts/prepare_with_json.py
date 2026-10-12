import argparse
import gzip
import json
import random
from pathlib import Path
from typing import TextIO

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

if __package__:
    from .product_filter import is_qualified
else:
    from product_filter import is_qualified

DATA_DIR = Path(__file__).resolve().parent / "data"
LEGACY_JSONL_PATH = DATA_DIR / "openfoodfacts-products.jsonl.gz"
ARCHIVE_PATTERN = "*-openfoodfact-products.jsonl.gz"
SAMPLE_SIZE = 3
PROGRESS_UPDATE_INTERVAL = 10_000
CACHE_PATH = DATA_DIR / "qualified_products.jsonl"
CACHE_METADATA_PATH = DATA_DIR / "qualified_products.meta.json"
console = Console()


def find_latest_jsonl() -> Path | None:
    archives = list(DATA_DIR.glob(ARCHIVE_PATTERN))
    if LEGACY_JSONL_PATH.exists():
        archives.append(LEGACY_JSONL_PATH)
    if not archives:
        return None
    return max(archives, key=lambda archive: archive.stat().st_mtime)


def to_english_filter_row(product: dict[str, object]) -> dict[str, str] | None:
    primary_language = str(product.get("lang") or "").strip().lower()
    english_name = str(product.get("product_name_en") or "").strip()
    english_ingredients = str(product.get("ingredients_text_en") or "").strip()

    if primary_language == "en":
        english_name = english_name or str(product.get("product_name") or "").strip()
        english_ingredients = (
            english_ingredients or str(product.get("ingredients_text") or "").strip()
        )
    elif not english_name or not english_ingredients:
        return None

    image_url = str(product.get("image_url") or "").strip()
    if not image_url:
        images = product.get("images")
        if isinstance(images, dict):
            selected_images = images.get("selected")
            if isinstance(selected_images, dict):
                front_images = selected_images.get("front")
                if isinstance(front_images, dict) and any(
                    isinstance(image, dict) and image.get("imgid")
                    for image in front_images.values()
                ):
                    image_url = "front-image-available"

    return {
        "code": str(product.get("code") or ""),
        "lang": "en",
        "product_name": english_name,
        "brands": str(product.get("brands") or ""),
        "ingredients_text": english_ingredients,
        "image_url": image_url,
    }


def archive_identity(archive: Path) -> dict[str, str | int]:
    stat = archive.stat()
    return {
        "archive": archive.name,
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def cache_matches_archive(archive: Path) -> bool:
    try:
        with CACHE_METADATA_PATH.open(encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
        return metadata == archive_identity(archive) and CACHE_PATH.is_file()
    except (OSError, json.JSONDecodeError):
        return False


def save_cache_metadata(archive: Path) -> None:
    temporary_metadata_path = CACHE_METADATA_PATH.with_suffix(".json.part")
    with temporary_metadata_path.open("w", encoding="utf-8") as metadata_file:
        json.dump(archive_identity(archive), metadata_file)
    temporary_metadata_path.replace(CACHE_METADATA_PATH)


def sample_qualified_products(
    products: TextIO,
    sample_size: int = SAMPLE_SIZE,
    max_products: int | None = None,
    cache_output: TextIO | None = None,
    rng: random.Random | None = None,
) -> tuple[int, int, list[dict[str, str]]]:
    scanned = 0
    qualified_count = 0
    selected: list[dict[str, str]] = []
    selector = rng or random

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning JSONL products...", total=None)
        for line in products:
            if not line.strip():
                continue
            if max_products is not None and scanned >= max_products:
                break
            scanned += 1

            try:
                product = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(product, dict):
                continue

            candidate = to_english_filter_row(product)
            if candidate is None or not is_qualified(candidate):
                continue

            qualified_count += 1
            if cache_output is not None:
                cache_output.write(json.dumps(candidate, ensure_ascii=False) + "\n")
            if len(selected) < sample_size:
                selected.append(candidate)
            else:
                replacement_index = selector.randrange(qualified_count)
                if replacement_index < sample_size:
                    selected[replacement_index] = candidate

            if scanned % PROGRESS_UPDATE_INTERVAL == 0:
                progress.update(
                    task,
                    description=(
                        f"Scanning JSONL: {scanned:,} products "
                        f"({qualified_count:,} qualified)"
                    ),
                )

        progress.update(
            task,
            description=(
                f"Scanned {scanned:,} products; {qualified_count:,} qualified"
            ),
        )

    return scanned, qualified_count, selected


def scan_archive(
    archive: Path,
    max_products: int | None,
    rng: random.Random | None = None,
) -> tuple[int, int, list[dict[str, str]], bool]:
    if max_products is not None:
        with gzip.open(archive, "rt", encoding="utf-8") as products:
            scanned, qualified_count, selected = sample_qualified_products(
                products,
                max_products=max_products,
                rng=rng,
            )
        return scanned, qualified_count, selected, False

    if cache_matches_archive(archive):
        with CACHE_PATH.open(encoding="utf-8") as cached_products:
            scanned, qualified_count, selected = sample_qualified_products(
                cached_products, rng=rng
            )
        return scanned, qualified_count, selected, False

    temporary_cache_path = CACHE_PATH.with_suffix(".jsonl.part")
    try:
        with (
            gzip.open(archive, "rt", encoding="utf-8") as products,
            temporary_cache_path.open("w", encoding="utf-8") as cache_output,
        ):
            scanned, qualified_count, selected = sample_qualified_products(
                products,
                cache_output=cache_output,
                rng=rng,
            )
        temporary_cache_path.replace(CACHE_PATH)
        save_cache_metadata(archive)
    finally:
        temporary_cache_path.unlink(missing_ok=True)

    return scanned, qualified_count, selected, True


def print_products(products: list[dict[str, str]]) -> None:
    for index, product in enumerate(products, start=1):
        details = Text()
        details.append("Brands: ", style="dim")
        details.append(product["brands"] or "Unknown")
        details.append("    Code: ", style="dim")
        details.append(product["code"] or "Unknown")

        ingredients = Text("Ingredients (EN)\n", style="bold")
        ingredients.append(product["ingredients_text"])
        console.print(
            Panel(
                Group(
                    Text(product["product_name"], style="bold cyan"),
                    details,
                    Text(),
                    ingredients,
                ),
                title=f"Product {index}",
                border_style="cyan",
                expand=True,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Randomly select and print three qualified JSONL products."
    )
    parser.add_argument(
        "--max-products",
        type=int,
        help="Scan only the first N records for debugging; do not build or use the cache",
    )
    args = parser.parse_args()
    if args.max_products is not None and args.max_products < 1:
        parser.error("--max-products must be positive")

    archive = find_latest_jsonl()
    if archive is None:
        parser.error("No JSONL archive found. Run scripts/download_jsonl.py first.")

    try:
        scanned, qualified_count, selected, cache_built = scan_archive(
            archive,
            max_products=args.max_products,
        )
    except (OSError, EOFError, UnicodeDecodeError) as error:
        parser.exit(1, f"Unable to read JSONL archive {archive}: {error}\n")

    if args.max_products is not None:
        console.print(
            f"Debug scan limited to the first {scanned:,} records; cache untouched."
        )
    elif cache_built:
        console.print(f"Qualified-products cache built: {CACHE_PATH}")
    else:
        console.print(f"Sampled from qualified-products cache: {CACHE_PATH}")

    console.print(
        f"\nSelected {len(selected)} of {qualified_count:,} qualified products."
    )
    if len(selected) < SAMPLE_SIZE:
        console.print(
            f"Only {len(selected)} qualified products were found; displaying all."
        )
    print_products(selected)


if __name__ == "__main__":
    main()
