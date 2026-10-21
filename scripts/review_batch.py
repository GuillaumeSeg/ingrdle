import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

BATCH_DIR = Path(__file__).resolve().parent.parent / "static" / "batches"


def load_batch(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as source:
            document = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read batch {path}: {error}") from error

    if not isinstance(document, dict) or not isinstance(
        document.get("questions"), list
    ):
        raise TypeError("Batch must be a JSON object containing a questions array.")

    required_fields = {
        "product_code",
        "product_name",
        "brands",
        "image_url",
        "ingredients",
        "hidden_ingredient_index",
        "hidden_ingredient",
        "choices",
    }
    for question_number, question in enumerate(document["questions"], start=1):
        if not isinstance(question, dict) or not required_fields.issubset(question):
            raise ValueError(f"Question {question_number} is missing required fields.")
        ingredients = question["ingredients"]
        choices = question["choices"]
        hidden_index = question["hidden_ingredient_index"]
        if not isinstance(ingredients, list) or not ingredients:
            raise ValueError(f"Question {question_number} has no ingredient list.")
        if type(hidden_index) is not int or not 0 <= hidden_index < len(ingredients):
            raise ValueError(f"Question {question_number} has an invalid hidden index.")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"Question {question_number} has no answer choices.")
    return document


def default_output_path(batch_path: Path) -> Path:
    if batch_path.stem.endswith("_validated"):
        raise ValueError("Choose a raw batch file, not an already validated batch.")
    return batch_path.with_name(f"{batch_path.stem}_validated.json")


def render_question(
    console: Console,
    question: dict[str, Any],
    question_number: int,
    total: int,
    kept_count: int,
    rejected_count: int,
    skipped_indices: set[int],
) -> None:
    if console.is_terminal:
        console.clear()

    progress = Progress(
        BarColumn(bar_width=32),
        TextColumn("{task.completed:.0f}/{task.total:.0f} decided"),
        console=console,
    )
    task = progress.add_task("Review progress", total=total)
    progress.update(task, completed=kept_count + rejected_count)

    summary = Table.grid(padding=(0, 2))
    summary.add_row(
        Text(f"KEEP  {kept_count}", style="bold green"),
        Text(f"REJECT  {rejected_count}", style="bold red"),
        Text(f"SKIPPED  {len(skipped_indices)}", style="bold yellow"),
        Text(f"LEFT  {total - kept_count - rejected_count}", style="bold cyan"),
    )

    details = Table.grid(padding=(0, 1))
    details.add_column(style="bold cyan", no_wrap=True)
    details.add_column()
    details.add_row("Product", Text(str(question["product_name"]), style="bold white"))
    details.add_row("Brand", Text(str(question["brands"] or "Unknown")))
    details.add_row("Code", Text(str(question["product_code"]), style="dim"))
    details.add_row(
        "Image",
        Text(str(question["image_url"]), style="link"),
    )

    ingredients = Text()
    hidden_index = question["hidden_ingredient_index"]
    for index, ingredient in enumerate(question["ingredients"]):
        if index:
            ingredients.append("\n")
        ingredients.append(f"{index + 1:>2}. ", style="dim")
        if index == hidden_index:
            ingredients.append(str(ingredient), style="bold yellow")
            ingredients.append("  <- HIDDEN ANSWER", style="bold yellow")
        else:
            ingredients.append(str(ingredient))

    choices = Table.grid(padding=(0, 1))
    for index, choice in enumerate(question["choices"], start=1):
        is_answer = choice == question["hidden_ingredient"]
        choices.add_row(
            Text(f"{index}.", style="dim"),
            Text(str(choice), style="bold green" if is_answer else "white"),
            Text("CORRECT", style="bold green") if is_answer else Text(),
        )

    content = Group(
        progress,
        summary,
        Text(),
        details,
        Text("INGREDIENTS", style="bold cyan"),
        ingredients,
        Text("\nANSWER CHOICES", style="bold cyan"),
        choices,
    )
    console.print(
        Panel(
            content,
            title=f"BATCH REVIEW  |  QUESTION {question_number} OF {total}",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def review_batch(
    batch_path: Path,
    output_path: Path | None = None,
    console: Console | None = None,
) -> Path | None:
    document = load_batch(batch_path)
    output_path = output_path or default_output_path(batch_path)
    if output_path.resolve() == batch_path.resolve():
        raise ValueError("The validated output must not overwrite the source batch.")
    if output_path.exists():
        raise FileExistsError(f"Output already exists: {output_path}")

    active_console = console or Console()
    questions = document["questions"]
    pending = deque(range(len(questions)))
    kept: list[dict[str, Any]] = []
    decided: set[int] = set()
    skipped: set[int] = set()

    while pending:
        index = pending.popleft()
        if index in decided:
            continue
        render_question(
            active_console,
            questions[index],
            len(decided) + 1,
            len(questions),
            len(kept),
            len(decided) - len(kept),
            skipped,
        )
        while True:
            try:
                choice = (
                    active_console.input(
                        "[bold green][K]eep[/]  [bold red][R]eject[/]  "
                        "[bold yellow][S]kip[/]  [bold cyan][Q]uit[/] > "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                active_console.print("\nReview cancelled; no file was written.")
                return None

            if choice in {"k", "r", "s", "q"}:
                break
            active_console.print("Enter K, R, S, or Q.", style="bold red")

        if choice == "q":
            active_console.print("Review stopped; no file was written.", style="yellow")
            return None
        if choice == "s":
            skipped.add(index)
            pending.append(index)
            continue

        skipped.discard(index)
        decided.add(index)
        if choice == "k":
            kept.append(questions[index])

    validated_document = {**document, "questions": kept}
    temporary_path = output_path.with_suffix(output_path.suffix + ".part")
    if temporary_path.exists():
        raise FileExistsError(f"Temporary output already exists: {temporary_path}")
    try:
        with temporary_path.open("x", encoding="utf-8") as output:
            json.dump(validated_document, output, ensure_ascii=False, indent=2)
            output.write("\n")
        if output_path.exists():
            raise FileExistsError(f"Output already exists: {output_path}")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    active_console.print(
        f"Validated batch written: {output_path} "
        f"([green]{len(kept)} kept[/], [red]{len(questions) - len(kept)} rejected[/])"
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review a batch of product questions in the terminal."
    )
    parser.add_argument("batch", type=Path, help="Raw batch JSON file to review")
    parser.add_argument(
        "--output",
        type=Path,
        help="Validated output path (default: <batch>_validated.json)",
    )
    args = parser.parse_args()
    try:
        review_batch(args.batch, args.output)
    except (FileExistsError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f"Batch review failed: {error}\n")


if __name__ == "__main__":
    main()
