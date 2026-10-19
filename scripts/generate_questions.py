import argparse
import json
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

if __package__:
    from .audit_ingredients import clean_ingredient_list
    from .distractors import generate_distractors
    from .prepare_with_json import (
        SAMPLE_SIZE,
        find_latest_jsonl,
        scan_archive,
    )
    from .product_filter import parse_ingredients, truncate_nested_parentheses
else:
    from audit_ingredients import clean_ingredient_list
    from distractors import generate_distractors
    from prepare_with_json import SAMPLE_SIZE, find_latest_jsonl, scan_archive
    from product_filter import parse_ingredients, truncate_nested_parentheses

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
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
    rng = random.Random(seed)
    _, qualified_count, selected, cache_built = scan_archive(
        archive,
        max_products=None,
        rng=rng,
    )
    if len(selected) < SAMPLE_SIZE:
        raise ValueError(
            f"Need {SAMPLE_SIZE} qualified products, found {qualified_count}."
        )

    questions = []
    fallback_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Cleaning ingredients and creating choices...", total=len(selected)
        )
        for product in selected:
            ingredients = parse_ingredients(product["ingredients_text"])
            ingredients, used_fallback = clean_ingredient_list(
                ingredients,
                product["product_name"],
            )
            ingredients = [
                truncate_nested_parentheses(ingredient) for ingredient in ingredients
            ]
            fallback_count += used_fallback
            hidden_ingredient_index = rng.randrange(len(ingredients))
            hidden_ingredient = ingredients[hidden_ingredient_index]
            distractors = generate_distractors(
                hidden_ingredient,
                product["product_name"],
                ingredients,
                rng,
            )
            choices = [*distractors, hidden_ingredient]
            rng.shuffle(choices)
            questions.append(
                {
                    "product_code": product["code"],
                    "product_name": product["product_name"],
                    "brands": product["brands"],
                    "image_url": product["image_url"],
                    "ingredients": ingredients,
                    "hidden_ingredient_index": hidden_ingredient_index,
                    "hidden_ingredient": hidden_ingredient,
                    "choices": choices,
                }
            )
            progress.advance(task)

    document = {
        "date": target_date.isoformat(),
        "seed": seed,
        "questions": questions,
    }

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    output_path = STATIC_DIR / f"questions-{target_date.isoformat()}.json"
    temporary_path = output_path.with_suffix(".json.part")
    with temporary_path.open("w", encoding="utf-8") as output:
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.write("\n")
    temporary_path.replace(output_path)

    if cache_built:
        console.print("Built the qualified-products cache during this run.")
    if fallback_count:
        console.print(
            f"[yellow]Ingredient cleanup used the original lists for "
            f"{fallback_count} of {len(selected)} products.[/yellow]"
        )
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
