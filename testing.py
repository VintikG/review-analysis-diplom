"""
testing.py
Скрипт для сбора и экспорта анализированных отзывов в формате JSON.
Вывод содержит для каждого отзыва: текст, тональность, summary и все аспекты с цитатами.

Usage:
  python testing.py                    # экспорт всех отзывов
  python testing.py --product 1        # экспорт отзывов конкретного товара
  python testing.py --limit 10         # экспорт первых 10 отзывов
  python testing.py --output data.json # сохранить в кастомный файл
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from storage_simple import db


def export_reviews_to_json(product_id=None, limit=None, output_file="reviews_analysis.json"):
    """
    Экспортирует все отзывы с результатами анализа в JSON формат.
    
    Args:
        product_id (int, optional): Если указано, экспортирует отзывы только этого товара
        limit (int, optional): Максимальное количество отзывов для экспорта
        output_file (str): Путь к выходному JSON файлу
    
    Returns:
        dict: Структурированные данные (также сохраняются в файл)
    """
    
    # 1. ЗАПРОС ОТЗЫВОВ ИЗ БД
    print(f"\n{'='*70}")
    print("  ЭКСПОРТ АНАЛИЗИРОВАННЫХ ОТЗЫВОВ В JSON")
    print(f"{'='*70}\n")
    
    if product_id:
        query = """
            SELECT
                r.id, r.product_id, r.customer_name, r.review_text, r.status, r.created_at,
                a.sentiment, a.summary, a.aspects,
                p.name AS product_name, p.category AS product_category
            FROM reviews r
            LEFT JOIN analysis_results a ON a.review_id = r.id
            LEFT JOIN products p ON p.id = r.product_id
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
        """
        rows = db.query(query, (product_id,))
        print(f"  📂 Товар ID {product_id}: загружено отзывов {len(rows)}\n")
    else:
        query = """
            SELECT
                r.id, r.product_id, r.customer_name, r.review_text, r.status, r.created_at,
                a.sentiment, a.summary, a.aspects,
                p.name AS product_name, p.category AS product_category
            FROM reviews r
            LEFT JOIN analysis_results a ON a.review_id = r.id
            LEFT JOIN products p ON p.id = r.product_id
            ORDER BY r.created_at DESC
        """
        rows = db.query(query)
        print(f"  📂 Все товары: загружено отзывов {len(rows)}\n")
    
    if limit:
        rows = rows[:limit]
        print(f"  ⚙️ Ограничение: экспортируются первые {limit} отзывов\n")
    
    # 2. СТРУКТУРИРОВАНИЕ ДАННЫХ
    reviews_data = []
    
    for i, row in enumerate(rows, 1):
        # Парсинг JSON аспектов
        aspects_list = []
        raw_aspects = row.get("aspects")
        
        if raw_aspects:
            try:
                aspects_json = json.loads(raw_aspects) if isinstance(raw_aspects, str) else raw_aspects
                if isinstance(aspects_json, list):
                    aspects_list = aspects_json
            except json.JSONDecodeError:
                aspects_list = []
        
        # Структура отзыва
        review_obj = {
            "review_id": row["id"],
            "product_id": row["product_id"],
            "product_name": row.get("product_name", ""),
            "product_category": row.get("product_category", ""),
            "customer_name": row.get("customer_name", "Аноним"),
            "review_text": row.get("review_text", ""),
            "status": row.get("status", "pending"),
            "created_at": row.get("created_at", ""),
            "sentiment": row.get("sentiment") or "unknown",
            "summary": row.get("summary", ""),
            "aspects": aspects_list,
        }
        
        reviews_data.append(review_obj)
        
        # Вывод прогресса в консоль
        print(f"  [{i}] Review #{row['id']} | Sentiment: {review_obj['sentiment'].upper():8s} | Aspects: {len(aspects_list)}")
    
    # 3. ФОРМИРОВАНИЕ ИТОГОВОГО JSON ОБЪЕКТА
    export_data = {
        "metadata": {
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_reviews": len(reviews_data),
            "product_id": product_id,
            "limit": limit,
        },
        "reviews": reviews_data,
    }
    
    # 4. СОХРАНЕНИЕ В ФАЙЛ
    output_path = Path(output_file)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Экспорт завершен успешно!")
        print(f"   📄 Файл сохранен: {output_path.absolute()}")
        print(f"   📊 Объем файла: {output_path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"\n❌ Ошибка при сохранении файла: {e}")
        return None
    
    # 5. ВЫВОД СТАТИСТИКИ
    sentiment_counts = {"positive": 0, "negative": 0, "mixed": 0, "unknown": 0}
    total_aspects = 0
    
    for review in reviews_data:
        sentiment = review.get("sentiment", "unknown").lower()
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
        total_aspects += len(review.get("aspects", []))
    
    print(f"\n{'='*70}")
    print("  СТАТИСТИКА")
    print(f"{'='*70}")
    print(f"  ✓ Всего отзывов:        {len(reviews_data)}")
    print(f"  ✓ Позитивные:           {sentiment_counts['positive']}")
    print(f"  ✓ Негативные:           {sentiment_counts['negative']}")
    print(f"  ✓ Смешанные:            {sentiment_counts['mixed']}")
    print(f"  ✓ Неизвестные:          {sentiment_counts['unknown']}")
    print(f"  ✓ Всего аспектов:       {total_aspects}")
    if len(reviews_data) > 0:
        print(f"  ✓ Аспектов на отзыв:    {total_aspects / len(reviews_data):.1f}")
    print(f"\n")
    
    return export_data


def pretty_print_sample(data, num_samples=2):
    """
    Выводит в консоль пример первых N отзывов в читаемом формате.
    """
    print(f"{'='*70}")
    print(f"  ПРИМЕРЫ ОТЗЫВОВ (первых {num_samples})")
    print(f"{'='*70}\n")
    
    for i, review in enumerate(data["reviews"][:num_samples], 1):
        print(f"Отзыв #{review['review_id']}:")
        print(f"  Товар: {review['product_name']} ({review['product_category']})")
        print(f"  Автор: {review['customer_name']}")
        print(f"  Дата: {review['created_at']}")
        print(f"  Статус: {review['status']}")
        print(f"  Тональность: {review['sentiment'].upper()}")
        print(f"  Summary: {review['summary']}")
        print(f"  Текст отзыва: {review['review_text'][:100]}...")
        
        if review['aspects']:
            print(f"  Аспекты ({len(review['aspects'])}):")
            for aspect in review['aspects']:
                print(f"    • {aspect['category']:20s} | {aspect['sentiment']:8s} | \"{aspect['snippet']}\"")
        else:
            print(f"  Аспекты: нет данных")
        
        print()


def main():
    """Главная функция с обработкой аргументов командной строки."""
    
    # Парсинг аргументов
    product_id = None
    limit = None
    output_file = "reviews_analysis.json"
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--product" and i + 1 < len(sys.argv):
            try:
                product_id = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                print(f"❌ Ошибка: --product требует целое число")
                sys.exit(1)
        
        elif arg == "--limit" and i + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                print(f"❌ Ошибка: --limit требует целое число")
                sys.exit(1)
        
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            sys.exit(0)
        
        else:
            print(f"❌ Неизвестный аргумент: {arg}")
            print(__doc__)
            sys.exit(1)
    
    # Экспорт
    data = export_reviews_to_json(product_id=product_id, limit=limit, output_file=output_file)
    
    if data:
        # Вывод примеров
        pretty_print_sample(data, num_samples=min(2, len(data["reviews"])))
        
        print(f"{'='*70}")
        print(f"✅ Экспорт завершен! JSON сохранен в: {output_file}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
