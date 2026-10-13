import json
import os
import random
import re

import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
console = Console()

CATEGORY_POOLS: dict[str, tuple[str, ...]] = {
    "gums": (
        "xanthan gum",
        "guar gum",
        "locust bean gum",
        "carrageenan",
        "pectin",
        "gellan gum",
        "agar",
        "tara gum",
    ),
    "fats": (
        "cocoa butter",
        "coconut oil",
        "shea butter",
        "palm oil",
        "sunflower oil",
        "olive oil",
        "butter",
        "rapeseed oil",
    ),
    "citrus": (
        "lemon juice",
        "lime juice",
        "orange juice",
        "citric acid",
        "malic acid",
        "vinegar",
        "ascorbic acid",
    ),
    "sweeteners": (
        "sugar",
        "glucose syrup",
        "honey",
        "dextrose",
        "fructose",
        "maple syrup",
        "maltodextrin",
    ),
    "starches": (
        "corn starch",
        "potato starch",
        "tapioca starch",
        "rice flour",
        "wheat flour",
        "modified starch",
        "arrowroot starch",
    ),
}

INGREDIENT_CATEGORIES = {
    ingredient: category
    for category, pool in CATEGORY_POOLS.items()
    for ingredient in pool
}
INGREDIENT_CATEGORIES["carob gum"] = "gums"
INGREDIENT_CATEGORIES["lemon juice from concentrate"] = "citrus"

FALLBACK_DISTRACTORS = (
    "maltodextrin",
    "rice flour",
    "pectin",
    "citric acid",
    "sunflower oil",
    "glucose syrup",
    "coconut oil",
    "vanilla extract",
    "potato starch",
    "yeast extract",
    "rice starch",
)


def normalize_ingredient(ingredient: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", ingredient.casefold()))


def _valid_candidates(candidates: list[str], excluded: set[str]) -> list[str]:
    valid: list[str] = []
    seen = set(excluded)
    for candidate in candidates:
        cleaned = candidate.strip()
        normalized = normalize_ingredient(cleaned)
        if cleaned and normalized and normalized not in seen:
            valid.append(cleaned)
            seen.add(normalized)
    return valid


def _match_hidden_format(candidate: str, hidden_ingredient: str) -> str:
    if "%" in hidden_ingredient:
        return candidate

    candidate = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s*%\s*\)\s*$", "", candidate)
    candidate = re.sub(r"\s+\d+(?:[.,]\d+)?\s*%\s*$", "", candidate)
    return " ".join(candidate.split())


def _ai_distractors(
    hidden_ingredient: str,
    product_name: str,
    excluded_ingredients: list[str],
    count: int,
    context_pool: list[str] | None = None,
) -> list[str]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    excluded_text = ", ".join(excluded_ingredients)
    pool_hint = ""
    if context_pool:
        pool_hint = (
            "\n\nCommon related ingredients include: "
            f"{', '.join(context_pool)}. Use these as inspiration, not as a "
            "required answer list."
        )
    prompt = (
        f"The hidden ingredient is '{hidden_ingredient}' in the food product "
        f"'{product_name}'. Suggest exactly {count} plausible but incorrect "
        "food ingredients that could work as quiz distractors.\n\n"
        "Rules:\n"
        "- Use real ingredient-label terms in English.\n"
        "- Match only formatting present in the hidden ingredient. If it has a "
        "percentage, include a different plausible percentage in the same "
        "format. Otherwise, do not add percentages, quantities, codes, or "
        "parenthetical details; keep each distractor as a plain ingredient name.\n"
        "- Do NOT use the hidden ingredient itself, its synonyms, or any "
        f"ingredient in the excluded list.\n"
        f"- Return only a JSON array of {count} strings, nothing else.\n\n"
        f"Excluded ingredients: [{excluded_text}]"
        f"{pool_hint}"
    )
    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip(),
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": "none"},
            "temperature": 0.4,
            "max_tokens": 200,
        },
        timeout=20,
    )
    response.raise_for_status()
    response_data = response.json()
    content = response_data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise TypeError("OpenRouter returned no text content")

    try:
        suggestions = json.loads(content)
    except json.JSONDecodeError:
        array_start = content.find("[")
        array_end = content.rfind("]")
        if array_start < 0 or array_end < array_start:
            raise ValueError("OpenRouter did not return a JSON array")
        suggestions = json.loads(content[array_start : array_end + 1])
    if not isinstance(suggestions, list) or not all(
        isinstance(suggestion, str) for suggestion in suggestions
    ):
        raise ValueError("OpenRouter returned an invalid distractor list")
    return suggestions


def generate_distractors(
    hidden_ingredient: str,
    product_name: str,
    ingredients: list[str],
    rng: random.Random,
    count: int = 3,
) -> list[str]:
    if count < 1:
        raise ValueError("count must be positive")

    normalized_hidden = normalize_ingredient(hidden_ingredient)
    excluded = {
        normalize_ingredient(ingredient)
        for ingredient in [*ingredients, hidden_ingredient]
    }
    category = INGREDIENT_CATEGORIES.get(normalized_hidden)
    pool = list(CATEGORY_POOLS[category]) if category is not None else []
    selected: list[str] = []
    try:
        suggestions = _ai_distractors(
            hidden_ingredient,
            product_name,
            [*ingredients, hidden_ingredient],
            count,
            context_pool=pool,
        )
        suggestions = [
            _match_hidden_format(suggestion, hidden_ingredient)
            for suggestion in suggestions
        ]
        ai_candidates = _valid_candidates(suggestions, excluded)
        selected.extend(ai_candidates[:count])
    except (
        IndexError,
        KeyError,
        requests.RequestException,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        if os.environ.get("OPENROUTER_API_KEY", "").strip():
            console.print(
                f"[yellow]OpenRouter distractors unavailable; using local "
                f"fallbacks ({error}).[/yellow]"
            )

    missing_count = count - len(selected)
    if missing_count:
        static_candidates = _valid_candidates(
            pool,
            excluded | {normalize_ingredient(item) for item in selected},
        )
        selected.extend(
            rng.sample(static_candidates, min(missing_count, len(static_candidates)))
        )

    missing_count = count - len(selected)
    if missing_count:
        fallback_candidates = _valid_candidates(list(FALLBACK_DISTRACTORS), excluded)
        fallback_candidates = _valid_candidates(
            fallback_candidates, {normalize_ingredient(item) for item in selected}
        )
        if len(fallback_candidates) < missing_count:
            raise ValueError(
                f"Could not find {count} unique distractors for {hidden_ingredient!r}."
            )
        selected.extend(rng.sample(fallback_candidates, missing_count))

    return selected
