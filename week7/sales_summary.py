"""
Plain-English business summary of sales_report.csv via LM Studio.
 
LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1.
Start the local server in LM Studio (Developer tab > Start Server) with a
model loaded, then run:
 
    python3 sales_summary.py
"""
 
import csv
import json
import sys
 
import requests
 
CSV_PATH = "sales_report.csv"
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
 
 
def load_report(path: str = CSV_PATH) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"{path} not found. Run the sales report first (bash run_report.sh 60).")
    if not rows:
        sys.exit(f"{path} is empty. Re-run the report with a longer window, e.g. bash run_report.sh 60")
    return rows
 
 
def build_prompt(rows: list[dict]) -> str:
    total_rev = sum(float(r["revenue"]) for r in rows)
    total_units = sum(int(r["units_sold"]) for r in rows)
    # Cap the table at 25 rows to keep the prompt small for local models
    table = "\n".join(
        f"{r['product']}: {r['units_sold']} units, ${float(r['revenue']):,.2f}"
        for r in rows[:25]
    )
    return (
        "You are a retail business analyst. Below is a sales report "
        "for an online store (paid orders, revenue after discounts, sorted "
        "by revenue).\n\n"
        f"Totals: {total_units} units sold, ${total_rev:,.2f} revenue, "
        f"{len(rows)} products.\n\n"
        f"{table}\n\n"
        "Write a concise plain-English summary for the store owner: top "
        "performers, notable patterns (e.g., revenue concentration, "
        "high-volume/low-revenue items), and one or two suggestions. "
        "No markdown, just a few short paragraphs."
    )
 
 
def summarize(prompt: str) -> str:
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 600,
    }
    try:
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit(
            "Could not reach LM Studio at localhost:1234. "
            "Open LM Studio, load a model, and start the server (Developer tab)."
        )
    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, json.JSONDecodeError):
        sys.exit(f"Unexpected response from LM Studio:\n{resp.text[:500]}")
 
 
def main() -> None:
    rows = load_report()
    print(f"Read {len(rows)} products from {CSV_PATH}. Asking LM Studio...\n")
    summary = summarize(build_prompt(rows))
    print(summary)
    with open("business_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary + "\n")
    print("\n(Saved to business_summary.txt)")
 
 
if __name__ == "__main__":
    main()
