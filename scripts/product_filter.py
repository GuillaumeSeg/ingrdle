MIN_INGREDIENTS = 3


def parse_ingredients(ingredients_text: str) -> list[str]:
    ingredients: list[str] = []
    closing_brackets: list[str] = []
    opening_brackets = {"(": ")", "[": "]", "{": "}"}
    ingredient_start = 0

    for position, character in enumerate(ingredients_text):
        if character in opening_brackets:
            closing_brackets.append(opening_brackets[character])
        elif closing_brackets and character == closing_brackets[-1]:
            closing_brackets.pop()
        elif character == "," and not closing_brackets:
            ingredient = ingredients_text[ingredient_start:position].strip()
            if ingredient:
                ingredients.append(ingredient)
            ingredient_start = position + 1

    final_ingredient = ingredients_text[ingredient_start:].strip()
    if final_ingredient:
        ingredients.append(final_ingredient)

    return ingredients


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
