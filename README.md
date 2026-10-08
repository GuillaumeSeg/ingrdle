# Ingrdle

A daily food trivia game about the ingredients hiding in everyday products.

> **Project status: early prototype.** The repository currently contains the beginning of a Python data-preparation script. The game, question generation, and deployment are planned, but are not implemented yet.

## The idea

Each day, players see three real food products from [Open Food Facts](https://world.openfoodfacts.org). One ingredient is hidden from each product's ingredient list, and players choose the missing ingredient from four options. Correct answers earn points; fun facts reveal more about each ingredient.

The first version is planned in English. Additional languages may follow later.

## What's in the repository today

- [`scripts/prepare.py`](scripts/prepare.py) downloads the English Open Food Facts product export and scans it for rows with a product name and a front image.
- The downloaded compressed export is stored at `scripts/data/off_products.csv.gz` and is ignored by Git.
- `static/` is currently empty. There is no game frontend or generated question file yet.

The preparation script is still a work in progress: it does not yet enforce the minimum ingredient count, choose a random sample, or write questions to an output file.

## Run the prototype

Requirements: Python 3 and the `requests` package.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests
python scripts/prepare.py
```

On the first run, the script downloads the Open Food Facts export (about 1.28 GB) to `scripts/data/`. Later runs reuse the local download. The script currently scans the export but does not produce a game-ready dataset.

## Planned gameplay

- Three products per day, each with one hidden ingredient and four answer choices.
- Up to five attempts per product.
- Planned points per product: 128, 64, 32, 16, or 8, depending on the attempt used.
- A daily score out of 384 and a consecutive-day streak.
- A short, light-hearted fact about the ingredient after each answer.

These are design goals, not features available in the current prototype.

## Planned data pipeline

1. Download and filter the English Open Food Facts export.
2. Select products with enough ingredients and a front image.
3. Hide an ingredient and create three plausible distractors, using taxonomy suggestions and fallback rules.
4. Generate ingredient trivia, then review it manually.
5. Export daily questions as static JSON for the game to consume.

Open Food Facts data is available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Review its attribution and share-alike requirements before publishing derived datasets.

## Planned technology

| Area | Planned choice |
| --- | --- |
| Game frontend | SvelteKit and Tailwind CSS |
| Scores and player data | Supabase |
| Hosting | Netlify |
| Data preparation | Python |
| Trivia drafts | OpenRouter |

This stack is tentative and has not been added to the repository yet.
