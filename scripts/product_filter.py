def english_field(row: dict[str, str | None], field: str) -> str:
    translated = (row.get(f"{field}_en") or "").strip()
    if translated:
        return translated

    if (row.get("lc") or "").strip().lower() == "en":
        return (row.get(field) or "").strip()

    return ""


def is_qualified(row: dict[str, str | None], english_only: bool = True) -> bool:
    name = (
        english_field(row, "product_name") if english_only else row.get("product_name")
    )
    ingredients = english_field(row, "ingredients_text") if english_only else True
    image = (row.get("image_url") or "").strip()
    return bool((name or "").strip() and ingredients and image)
