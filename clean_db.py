import sqlite3

def clean_database():
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    
    # Очищаем таблицы с данными
    cursor.execute("DELETE FROM analysis_results;")
    cursor.execute("DELETE FROM reviews;")
    cursor.execute("DELETE FROM products;")
    
    # Сбрасываем счетчики ID (чтобы новые отзывы снова начинались с ID=1)
    cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name IN ('analysis_results', 'reviews', 'products');")
    
    conn.commit()
    conn.close()
    print("✓ База данных очищена. Отзывы, результаты и товары удалены. Пользователь сохранен.")

if __name__ == "__main__":
    clean_database()