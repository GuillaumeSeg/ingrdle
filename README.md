# Ingrdle

A daily food trivia game about the ingredients hiding in everyday products.

> **Project status: early prototype.** The repository contains Python data-preparation scripts and can generate daily product-question JSON files. The game interface, answer generation, and deployment are not implemented yet.

## The idea

Each day, players see three real food products from [Open Food Facts](https://world.openfoodfacts.org). One ingredient is hidden from each product's ingredient list, and players choose the missing ingredient from four options. Correct answers earn points; fun facts reveal more about each ingredient.

The first version is planned in English. Additional languages may follow later.

## What's in the repository today

- [`scripts/prepare_with_csv.py`](scripts/prepare_with_csv.py) downloads the CSV export and randomly selects products with English names, enough ingredients, and a front image.
- [`scripts/prepare_with_api.py`](scripts/prepare_with_api.py) selects qualified products from a random page of the Open Food Facts API.
- [`scripts/download_jsonl.py`](scripts/download_jsonl.py) downloads the compressed JSONL export with a progress bar and month-based filename.
- [`scripts/prepare_with_json.py`](scripts/prepare_with_json.py) builds or reuses a cache of qualified English products and prints a random sample. Its `--max-products` option is for quick, non-representative debug scans.
- [`scripts/generate_questions.py`](scripts/generate_questions.py) writes three date-specific product questions, including image URLs and a randomly selected hidden ingredient, to `static/questions-YYYY-MM-DD.json` and records the random seed.
- Downloaded exports and the qualified-product cache live in `scripts/data/` and are ignored by Git.
- The CSV test fixture contains 200 rows. Older fixtures without the `lang` column must be regenerated before `--use-test-csv` can filter them.

Each generated question contains the product code, English name, brand, front-image URL, an ordered array of top-level ingredient strings, and four shuffled answer choices: the hidden ingredient plus three distractors. `hidden_ingredient_index` is the zero-based index of the randomly selected ingredient in the ingredient array, and `hidden_ingredient` contains its value. Distractors use OpenRouter first, with a matching curated ingredient-family pool as prompt context; curated pools and local fallback choices fill any remaining slots if the API is unavailable or returns too few valid suggestions. Commas inside parentheses or brackets stay within their ingredient. Trivia and the game itself are not generated yet.

## Run the prototype

Requirements: Python 3 and the packages in `requirements-dev.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/prepare_with_csv.py
```

To enable OpenRouter distractors, create a local `.env` file at the repository root:

```dotenv
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openrouter/free
```

`.env` is ignored by Git; never put a real API key in a tracked file. The default `openrouter/free` router chooses from currently available free models. Free-model availability, rate limits, latency, and response quality can vary. Set `OPENROUTER_MODEL` to a specific model ID if you prefer. Distractors are generated offline while building the daily batch, not when a player answers.

Create a small test dataset once, then run against it without scanning the full export:

```bash
python scripts/prepare_with_csv.py --create-test-csv
python scripts/prepare_with_csv.py --use-test-csv
```

The CSV test fixture contains 200 products. Regenerating it requires the full CSV export; the command downloads that export if it is not already present.

Select qualified products from a random API page:

```bash
python scripts/prepare_with_api.py
python scripts/prepare_with_api.py --page-size 100 --count 3
```

The script makes two API requests: one to get the available page count, then one to fetch a randomly selected page. The API currently exposes at most 100 pages per search (up to 10,000 products at the default page size), so the selection is random within that result window, not the full 4.8-million-product catalog. With the documented search limit of 10 requests per minute, avoid running it more than five times per minute. The SDK does not currently expose this unfiltered `/api/v2/search` endpoint, so this request uses the API directly; the official SDK remains available for other product operations.

Download the full compressed JSONL export (about 13 GB compressed and 43 GB uncompressed in the current export):

```bash
python scripts/download_jsonl.py
python scripts/prepare_with_json.py
```

The first full run scans the compressed JSONL archive and builds a cache; it took about 23 minutes on the current machine. Later runs sample from the cache instead of rescanning the archive. A live progress indicator shows the number of records scanned while building the cache.

For a quicker, non-representative debug run, scan only the first 50,000 records without using or building the cache:

```bash
python scripts/prepare_with_json.py --max-products 50000
```

The qualified-products cache is rebuilt automatically when the source archive or cache schema changes. The current schema change means the next full preparation run must rebuild it once; the progress indicator will show the scan. The rebuilt cache contains real front-image URLs derived from JSONL image metadata, so generated batches need no per-product image API requests.

Generate tomorrow's question file, today's file, or choose a date explicitly:

```bash
python scripts/generate_questions.py
python scripts/generate_questions.py --date 2026-10-12
python scripts/generate_questions.py --tomorrow
```

Output is written to `static/questions-YYYY-MM-DD.json`. Each run chooses a fresh random seed, so regenerating the same date can produce different products. The seed is saved in the JSON; pass it with `--seed` to reproduce product selection and local random choices. OpenRouter model responses are not guaranteed to be identical between runs.

## Planned gameplay

- Three products per day, each with one hidden ingredient and four answer choices.
- Up to five attempts per product.
- Planned points per product: 128, 64, 32, 16, or 8, depending on the attempt used.
- A daily score out of 384 and a consecutive-day streak.
- A short, light-hearted fact about the ingredient after each answer.

These are design goals, not features available in the current prototype.

Planned: Sudden Death (weekly)
A weekly variant with a single product and escalating difficulty.

Format: 8 rounds on one product, 5 lives.

Rounds	Format	Difficulty
1–2	Yes / No (is this ingredient in the product?)	Easy
3–4	2 choices	Medium
5–6	3 choices	Hard
7–8	4 choices (mimic-format distractors)	Very hard

One life lost per wrong answer.
ALIVE if all 8 ingredients are revealed with ≥ 1 life remaining.
DEAD at round N → "Killed at round N/8" (shareable).
No points — binary outcome (ALIVE / DEAD) + weekly streak.
Uses the same pool and distractor pipeline as the classic daily mode.
Target duration: ~90 seconds.
This mode reuses all existing data (products, hidden ingredients, choices) without any additional generation cost.

### Production answer security

The prototype JSON includes `hidden_ingredient` for local development. Do not publish that answer in a static file served to players: anything sent to the browser can be inspected. In production, serve only the ingredient list and answer choices publicly; keep the correct answer in a private answer key or validate guesses on the server.

## Planned data pipeline

1. Download and filter the English Open Food Facts export.
2. Select products with enough ingredients and a front image.
3. Ask OpenRouter for three distractors, using curated ingredient-family pools as context; validate all choices and fill any missing choices from local pools.
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


© 2026 [Guillaume Se.]. All rights reserved.
