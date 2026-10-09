## Language
- Write comments and docs in English.

## Python
- Use type hints on all function signatures.
- Use `ruff` for linting and formatting (`ruff check .` / `ruff format .`).

## Setup
- Before running or testing any code, install dev dependencies:
  `pip install -r requirements-dev.txt`

## UX / Feedback

- Any script or task that takes > 1 second must show visual progress in the terminal.
- Use `rich` for all terminal UI (progress bars, spinners, panels, tables).
- Prefer `rich.progress.Progress` for multi-step tasks, `rich.status.Status` for single long operations.
- Never leave the user staring at a blank terminal.

Example:
```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn()) as progress:
    task = progress.add_task("Processing...", total=100)
    for i in range(100):
        # work
        progress.update(task, advance=1)
```

## Conventions
- snake_case for variables and functions.
- PascalCase for classes.
- Keep modules under 220 lines; split if needed.