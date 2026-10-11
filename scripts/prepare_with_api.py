import argparse
import random

import requests
from requests.adapters import HTTPAdapter
from rich.console import Console
from rich.text import Text
from urllib3.util.retry import Retry

if __package__:
    from .product_filter import is_qualified
else:
    from product_filter import is_qualified

USER_AGENT = "Ingrdle/0.0.1 (guillaume.segado@pm.me)"
API_URL = "https://world.openfoodfacts.org/api/v2/search"
PRODUCT_FIELDS = (
    "code",
    "product_name",
    "brands",
    "ingredients_text",
    "image_url",
    "lang",
)
console = Console()


def create_api_session() -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount(API_URL, HTTPAdapter(max_retries=retry))
    return session


def normalize_product(product: dict[str, object]) -> dict[str, str]:
    return {field: str(product.get(field) or "") for field in PRODUCT_FIELDS}


def load_qualified_products(
    page_size: int,
) -> tuple[int, list[dict[str, str]]]:
    headers = {"User-Agent": USER_AGENT}
    fields = ",".join(PRODUCT_FIELDS)
    session = create_api_session()

    with console.status("Getting the Open Food Facts product count..."):
        count_response = session.get(
            API_URL,
            params={"page": 1, "page_size": page_size, "fields": "code"},
            headers=headers,
            timeout=30,
        )
        count_response.raise_for_status()
        metadata = count_response.json()
        total_products = int(metadata.get("count", 0))
        page_count = int(metadata.get("page_count", 0))

    if total_products < 1 or page_count < 1:
        return 0, []

    page = random.randint(1, page_count)
    qualified: list[dict[str, str]] = []

    with console.status(f"Loading random page {page}/{page_count}..."):
        response = session.get(
            API_URL,
            params={"page": page, "page_size": page_size, "fields": fields},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        products_response = response.json()

    products = products_response.get("products", [])
    if not isinstance(products, list):
        return page, qualified

    for product in products:
        if not isinstance(product, dict):
            continue
        normalized = normalize_product(product)
        if is_qualified(normalized):
            qualified.append(normalized)

    return page, qualified


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pick qualified products from a random Open Food Facts page."
    )
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--count", type=int, default=3, help="Products to select")
    args = parser.parse_args()

    if args.page_size < 1 or args.count < 1:
        parser.error("--page-size and --count must be positive")

    try:
        page, qualified = load_qualified_products(args.page_size)
    except requests.RequestException as error:
        parser.exit(1, f"Open Food Facts API request failed: {error}\n")

    console.print(f"Random page selected: [bold]{page}[/bold].")
    console.print(f"Found [bold]{len(qualified)}[/bold] qualified products.")

    if len(qualified) < args.count:
        console.print(
            f"Only {len(qualified)} qualified products available; selecting all."
        )
        selected = qualified
    else:
        selected = random.sample(qualified, args.count)

    console.print("\n[bold]Selected products:[/bold]")
    for index, product in enumerate(selected, start=1):
        console.print(
            f"{index}. {product['product_name']} "
            f"(brand: {product['brands']}, code: {product['code']})"
        )
        console.print(
            Text("   Ingredients (EN): ", style="dim")
            + Text(product["ingredients_text"])
        )


if __name__ == "__main__":
    main()
