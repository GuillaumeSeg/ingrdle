import re

MIN_INGREDIENTS = 3
PRECAUTIONARY_STATEMENT_RE = re.compile(
    r"\b(?:may contain|contains traces of|peut contenir|peuvent contenir|"
    r"puede(?:n)? contener|contiene trazas de)\b",
    re.IGNORECASE,
)


def parse_ingredients(ingredients_text: str) -> list[str]:
    precautionary_statement = PRECAUTIONARY_STATEMENT_RE.search(ingredients_text)
    if precautionary_statement is not None:
        ingredients_text = ingredients_text[: precautionary_statement.start()]

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
            if (
                position > 0
                and position + 1 < len(ingredients_text)
                and ingredients_text[position - 1].isdigit()
                and ingredients_text[position + 1].isdigit()
            ):
                continue
            ingredient = ingredients_text[ingredient_start:position].strip()
            if ingredient:
                ingredients.append(ingredient)
            ingredient_start = position + 1

    final_ingredient = ingredients_text[ingredient_start:].strip()
    if final_ingredient:
        ingredients.append(final_ingredient)

    return ingredients


def truncate_nested_parentheses(ingredient: str) -> str:
    result = []
    depth = 0
    for character in ingredient:
        if character == "(":
            if depth == 0:
                result.append(character)
            else:
                while result and result[-1].isspace():
                    result.pop()
            depth += 1
        elif character == ")":
            if depth == 0:
                return ingredient
            depth -= 1
            if depth == 0:
                while result and result[-1].isspace():
                    result.pop()
                result.append(character)
        elif depth <= 1:
            result.append(character)

    if depth:
        return ingredient
    return "".join(result)


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
