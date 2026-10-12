import argparse
import json
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console

if __package__:
    from .prepare_with_json import (
        SAMPLE_SIZE,
        find_latest_jsonl,
        scan_archive,
    )
else:
    from prepare_with_json import SAMPLE_SIZE, find_latest_jsonl, scan_archive

QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "questions"
console = Console()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def resolve_target_date(
    requested_date: date | None,
    tomorrow: bool,
    today: date | None = None,
) -> date:
    if requested_date is not None:
        return requested_date
    current_date = today or datetime.now(timezone.utc).date()
    return current_date + timedelta(days=1) if tomorrow else current_date


def generate_questions(target_date: date, seed: int | None = None) -> Path:
    archive = find_latest_jsonl()
    if archive is None:
        raise FileNotFoundError("No JSONL archive found. Run download_jsonl.py first.")

    seed = secrets.randbits(64) if seed is None else seed
    _, qualified_count, selected, cache_built = scan_archive(
        archive,
        max_products=None,
        rng=random.Random(seed),
    )
    if len(selected) < SAMPLE_SIZE:
        raise ValueError(
            f"Need {SAMPLE_SIZE} qualified products, found {qualified_count}."
        )

    document = {
        "date": target_date.isoformat(),
        "seed": seed,
        "questions": [
            {
                "product_name": product["product_name"],
                "brands": product["brands"],
            }
            for product in selected
        ],
    }

    QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = QUESTIONS_DIR / f"{target_date.isoformat()}.json"
    temporary_path = output_path.with_suffix(".json.part")
    with temporary_path.open("w", encoding="utf-8") as output:
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.write("\n")
    temporary_path.replace(output_path)

    if cache_built:
        console.print("Built the qualified-products cache during this run.")
    console.print(f"Generated {len(selected)} questions: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a daily JSON file containing three product questions."
    )
    date_options = parser.add_mutually_exclusive_group()
    date_options.add_argument(
        "--date",
        type=parse_date,
        help="Question date in YYYY-MM-DD format",
    )
    date_options.add_argument(
        "--tomorrow",
        action="store_true",
        help="Generate questions for tomorrow (UTC)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional seed to reproduce a previous product selection",
    )
    args = parser.parse_args()
    target_date = resolve_target_date(args.date, args.tomorrow)

    try:
        generate_questions(target_date, seed=args.seed)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Question generation failed: {error}\n")


if __name__ == "__main__":
    main()
