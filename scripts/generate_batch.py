import argparse
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .generate_questions import generate_questions, parse_date
else:
    from generate_questions import generate_questions, parse_date

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
BATCH_DIR = STATIC_DIR / "batches"


def positive_int(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("count must be a positive integer") from error
    if count < 1:
        raise argparse.ArgumentTypeError("count must be a positive integer")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a batch of product questions without trivia."
    )
    parser.add_argument(
        "--count",
        type=positive_int,
        default=45,
        help="Number of questions to generate (default: 45)",
    )
    parser.add_argument(
        "--date",
        type=parse_date,
        default=datetime.now(timezone.utc).date(),
        help="Batch date in YYYY-MM-DD format (default: today in UTC)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional seed to reproduce product selection and local choices",
    )
    args = parser.parse_args()
    output_path = BATCH_DIR / f"batch_{args.date.isoformat()}.json"

    try:
        generate_questions(
            args.date,
            seed=args.seed,
            question_count=args.count,
            output_path=output_path,
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Batch generation failed: {error}\n")


if __name__ == "__main__":
    main()
