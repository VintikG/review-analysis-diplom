"""
ingest_reviews.py
CLI script: read CSV → analyze with Ollama → save to SQLite.
Usage: python ingest_reviews.py [path/to/file.csv]
"""
import csv
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from storage_simple import db
from analyzer_simple import analyze_review


def ingest(csv_path: str):
    print(f"\n{'='*60}")
    print("  ЗАГРУЗКА ОТЗЫВОВ ИЗ CSV")
    print(f"{'='*60}\n")

    db.init_tables()
    db.init_test_user()

    p = Path(csv_path)
    if not p.exists():
        print(f"✗ Файл не найден: {csv_path}")
        sys.exit(1)

    try:
        text = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = p.read_text(encoding="cp1251")

    reader = csv.DictReader(text.splitlines())
    rows   = list(reader)
    print(f"📂 Загружено строк из CSV: {len(rows)}\n")

    added = analyzed = errors = 0

    for idx, row in enumerate(rows, 1):
        try:
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}

            product_name  = row.get("product_name", "").strip()
            category      = row.get("category", "Электроника").strip() or "Электроника"
            customer_name = row.get("customer_name", "Аноним").strip() or "Аноним"
            review_text   = row.get("review_text", "").strip()
            created_at    = row.get("created_at", "").strip() or None

            if not product_name or not review_text or len(review_text) < 5:
                print(f"  ⚠ Строка {idx}: пропущена (пустые поля)")
                errors += 1
                continue

            product = db.query_one(
                "SELECT id FROM products WHERE name = ?", (product_name,)
            )
            if not product:
                pid = db.exec(
                    "INSERT INTO products (name, category) VALUES (?, ?)",
                    (product_name, category),
                )
            else:
                pid = product["id"]

            review_id = db.exec(
                "INSERT INTO reviews (product_id, customer_name, review_text, status, created_at) "
                "VALUES (?, ?, ?, 'pending', ?)",
                (pid, customer_name, review_text, created_at),
            )
            added += 1

            cat = row.get("category", "") or "электроника"
            print(
                f"  [{idx}/{len(rows)}] Анализирую: «{review_text[:60]}…»",
                end="",
                flush=True,
            )
            sentiment, summary, aspects = analyze_review(review_text, cat)

            if sentiment in ("error", "unknown"):
                print(f" ✗ {summary}")
                errors += 1
                continue

            aspects_json = json.dumps(aspects, ensure_ascii=False)
            db.exec(
                "INSERT OR REPLACE INTO analysis_results "
                "(review_id, sentiment, summary, aspects) VALUES (?, ?, ?, ?)",
                (review_id, sentiment, summary, aspects_json),
            )
            db.exec(
                "UPDATE reviews SET status = 'analyzed' WHERE id = ?", (review_id,)
            )
            analyzed += 1
            print(f" ✓ {sentiment.upper()}")
            time.sleep(0.2)

        except Exception as e:
            print(f" ✗ Строка {idx}: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"  ИТОГО")
    print(f"{'='*60}")
    print(f"  ✓ Добавлено:      {added}")
    print(f"  ✓ Проанализировано: {analyzed}")
    print(f"  ✗ Ошибок:         {errors}")

    stats = db.query_one("SELECT COUNT(*) AS c FROM products")
    rc    = db.query_one("SELECT COUNT(*) AS c FROM reviews")
    ac    = db.query_one("SELECT COUNT(*) AS c FROM analysis_results")
    print(f"\n📊 БД: товаров={stats['c']}  отзывов={rc['c']}  проанализировано={ac['c']}\n")


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "reviews_raw.csv"
    ingest(csv_file)