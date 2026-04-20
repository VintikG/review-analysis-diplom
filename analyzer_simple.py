import json
import re
import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_API = f"{OLLAMA_URL}/api/generate"
MODEL      = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")

ANALYSIS_PROMPT = """\
# ROLE: Ты — эксперт по анализу текстов и извлечению данных (Aspect-Based Sentiment Analysis).
# TASK: Проанализируй отзыв об электронике (категория товара: {category}). Извлеки аспекты строго по списку категорий.


СЛОВАРЬ КАТЕГОРИЙ (используй только эти названия):
- экран: экран, матрица, яркость, цвета, блики, битые пиксели
- батарея: время автономной работы, скорость зарядки
- производительность: скорость работы, зависания, лаги, быстрая загрузка
- камера: качество фото, видео, ночная съемка, фронтальная камера
- микрофон: качество записи голоса, шумоподавление голоса
- звук: качество динамиков, громкость, басы
- дизайн: только внешний вид, цвет, красота, эстетика
- вес_и_габариты: легкий, тяжелый, широкий, компактный
- качество_сборки: надежность материалов, прочность, поверхность, скрипты
- охлаждение_и_шум: нагрев, температура, шум вентиляторов
- операционная_система: софт, программы, прошивка, интерфейс
- эргономика: удобство клавиатуры, тачпада, кнопок
- беспроводная_сеть: Wi-Fi, Bluetooth, потеря связи, стабильность сигнала
- порты_и_разъемы: USB, Type-C, нехватка гнезд, разъемы
- цена: стоимость, соотношение цена/качество
- комплектация: что лежит в коробке (чехол, зарядник, переходник)

ИНСТРУКЦИИ:
1. Запрещено придумывать категории. Если клиент пишет эмоции ("супер", "рекомендую", "ужасно")
или оценивает доставку, курьеров, гарантию — просто игнорируй и пропускай это.
2. "summary" — одно короткое предложение на русском языке с общим смыслом отзыва.
3. "snippet" — это точная цитата из текста отзыва (5-15 слов), подтверждающая аспект.
4. "sentiment" аспекта — строго одно из: positive | negative
5. "sentiment" всего отзыва — строго одно из: positive | negative | mixed.
6. Аспект "производительность" относится только к скорости работы и зависаниям
7. ОТВЕТ — ТОЛЬКО JSON-массив с одним объектом, БЕЗ markdown-разметки и пояснений.

ПРИМЕР:
Input (категория: Ноутбуки): "Ноут мощный, но шумит как пылесос. Зарядка короткая."
Output: [{{"summary":"Мощный ноутбук с шумным охлаждением и плохой комплектацией.","sentiment":"mixed","aspects":[{{"category":"производительность","sentiment":"positive","snippet":"Ноут мощный"}},{{"category":"звук","sentiment":"negative","snippet":"шумит как пылесос"}},{{"category":"комплектация","sentiment":"negative","snippet":"Зарядка короткая"}}]}}]

ШАБЛОН ОТВЕТА (верни только один JSON объект, без markdown-разметки и без текста до/после):
{{
  "summary": "текст резюме",
  "sentiment": "positive",
  "aspects":[
    {{
      "category": "батарея",
      "sentiment": "negative",
      "snippet": "разряжается за полдня"
    }}
  ]
}}

ОТЗЫВ ДЛЯ АНАЛИЗА:
{review_text}

Верни ТОЛЬКО JSON-массив без markdown-разметки и без пояснений."""


def _clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text)
    return text.strip().strip("`").strip()


def analyze_review(review_text: str, category: str = "электроника") -> tuple[str, str, list]:
    """
    Analyze review_text with Ollama ABSA.
    Determines sentiment based on aspects (strict rules):
    - neutral:  no aspects found
    - positive: ALL aspects are positive
    - negative: ALL aspects are negative
    - mixed:    both positive AND negative aspects exist
    
    Returns (sentiment, summary, aspects) or ("error", msg, []).
    """
    cat = (category or "электроника").strip()
    try:
        prompt = ANALYSIS_PROMPT.format(review_text=review_text.strip(), category=cat)
        resp = requests.post(
            OLLAMA_API,
            json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "top_p": 0.1}},
            timeout=180,
        )
        if resp.status_code != 200:
            return "error", f"Ollama HTTP {resp.status_code}", []

        raw = _clean(resp.json().get("response", ""))
        if not raw:
            return "error", "Пустой ответ от модели", []

        data = json.loads(raw)
        item = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else None)
        if not item:
            return "neutral", "Не удалось определить аспекты", []

        summary = item.get("summary", "")[:400]
        aspects = [
            a for a in item.get("aspects", [])
            if a.get("category") and a.get("sentiment") in {"positive", "negative"}
        ]
        
        # ─────────────────────────────────────────────────────────────
        # DETERMINE SENTIMENT BASED ON ASPECTS (strict rules)
        # ─────────────────────────────────────────────────────────────
        if not aspects:
            # No aspects found → neutral
            sentiment = "neutral"
        else:
            positive_count = sum(1 for a in aspects if a.get("sentiment") == "positive")
            negative_count = sum(1 for a in aspects if a.get("sentiment") == "negative")
            
            if positive_count > 0 and negative_count == 0:
                # Only positive aspects
                sentiment = "positive"
            elif negative_count > 0 and positive_count == 0:
                # Only negative aspects
                sentiment = "negative"
            elif positive_count > 0 and negative_count > 0:
                # Both positive and negative aspects
                sentiment = "mixed"
            else:
                # Fallback
                sentiment = "neutral"
        
        return sentiment, summary, aspects

    except json.JSONDecodeError as e:
        return "error", f"JSON parse error: {e}", []
    except requests.exceptions.ConnectionError:
        return "error", "Ollama недоступен (Connection refused)", []
    except requests.exceptions.Timeout:
        return "error", "Ollama timeout (>180 сек)", []
    except Exception as e:
        return "error", f"Ошибка анализатора: {e}", []