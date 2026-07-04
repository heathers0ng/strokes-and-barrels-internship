"""
Shopify 30-day sales report.

Pulls all orders from the last 30 days via the Admin REST API,
aggregates units sold and revenue per product, and writes the
results (sorted by revenue, highest first) to sales_report.csv.

Setup:
    pip install requests

    # Set these environment variables (don't hardcode secrets!):
    #   SHOPIFY_STORE  = your-store.myshopify.com
    #   SHOPIFY_TOKEN  = shpat_xxxxxxxxxxxx  (Admin API access token)

Usage:
    python shopify_sales_report.py
"""

import csv
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

API_VERSION = "2024-10"
OUTPUT_FILE = "sales_report.csv"


def get_config():
    store = os.environ.get("SHOPIFY_STORE")
    token = os.environ.get("SHOPIFY_TOKEN")
    if not store or not token:
        sys.exit(
            "Missing config. Set environment variables first:\n"
            "  export SHOPIFY_STORE=your-store.myshopify.com\n"
            "  export SHOPIFY_TOKEN=shpat_...\n"
            "(On Windows PowerShell: $env:SHOPIFY_STORE='...' etc.)"
        )
    # Allow the user to paste the full URL or just the domain
    store = store.replace("https://", "").replace("http://", "").strip("/")
    return store, token


def fetch_orders(store: str, token: str, days: int = 30):
    """Yield all orders created in the last `days` days, handling pagination."""
    created_at_min = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat(timespec="seconds")

    session = requests.Session()
    session.headers.update(
        {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        }
    )

    url = f"https://{store}/admin/api/{API_VERSION}/orders.json"
    params = {
        "status": "any",
        "created_at_min": created_at_min,
        "limit": 250,
        # Only fetch the fields we need — faster and lighter
        "fields": "id,created_at,line_items,financial_status,cancelled_at",
    }

    page = 1
    while url:
        resp = session.get(url, params=params)

        # Basic rate-limit handling (Shopify returns 429 when throttled)
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 2))
            print(f"Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        orders = resp.json().get("orders", [])
        print(f"Page {page}: fetched {len(orders)} orders")
        yield from orders

        # Cursor pagination: follow the 'next' link if present.
        # After the first request, page_info must be the only query param.
        next_link = resp.links.get("next", {}).get("url")
        url = next_link
        params = None  # params are baked into the next_link URL
        page += 1


def aggregate(orders):
    """Return {product_title: {"units": int, "revenue": float}}."""
    stats = defaultdict(lambda: {"units": 0, "revenue": 0.0})

    for order in orders:
        # Skip cancelled orders — they aren't real sales
        if order.get("cancelled_at"):
            continue

        for item in order.get("line_items", []):
            title = item.get("title") or "Unknown product"
            qty = item.get("quantity", 0)

            # Revenue = line price * qty, minus line-level discounts
            price = float(item.get("price", 0)) * qty
            discount = sum(
                float(d.get("amount", 0))
                for d in item.get("discount_allocations", [])
            )
            stats[title]["units"] += qty
            stats[title]["revenue"] += price - discount

    return stats


def write_csv(stats, path=OUTPUT_FILE):
    rows = sorted(stats.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product", "units_sold", "revenue"])
        for title, s in rows:
            writer.writerow([title, s["units"], f"{s['revenue']:.2f}"])
    print(f"\nWrote {len(rows)} products to {path}")


def main():
    store, token = get_config()
    print(f"Fetching last 30 days of orders from {store}...")
    stats = aggregate(fetch_orders(store, token))
    if not stats:
        print("No orders found in the last 30 days.")
        return
    write_csv(stats)

    total_rev = sum(s["revenue"] for s in stats.values())
    total_units = sum(s["units"] for s in stats.values())
    print(f"Totals: {total_units} units, ${total_rev:,.2f} revenue")


if __name__ == "__main__":
    main()
