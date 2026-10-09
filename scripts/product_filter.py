MIN_INGREDIENTS = 4


def parse_ingredients(ingredients_text: str) -> list[str]:
    return [
        ingredient.strip()
        for ingredient in ingredients_text.split(",")
        if ingredient.strip()
    ]


def is_qualified(row: dict[str, str]) -> bool:
    if (row.get("lang") or "").strip().lower() != "en":
        return False

    name = (row.get("product_name") or "").strip()
    if len(name) < 3:
        return False

    ingredients_text = (row.get("ingredients_text") or "").strip()
    if len(ingredients_text) < 10:
        return False
    if ingredients_text.startswith("_") or (
        "Ingredients" in ingredients_text and len(ingredients_text) < 15
    ):
        return False
    if len(parse_ingredients(ingredients_text)) < MIN_INGREDIENTS:
        return False

    image_url = (row.get("image_url") or "").strip()
    return bool(image_url and "invalid" not in image_url.lower())
