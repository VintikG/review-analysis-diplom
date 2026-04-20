"""
main_simple.py
FastAPI server — Review Analysis Prototype.
Endpoints: auth, products, reviews, stats, aspects, upload/csv, report/html
"""
import os
import io
import csv
import json
import re
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from werkzeug.security import check_password_hash

from storage_simple import db
from analyzer_simple import analyze_review

# ─────────────────────────────────────────────
app = FastAPI(title="Review Analysis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"


# ── Startup ──────────────────────────────────
@app.on_event("startup")
async def startup_event():
    db.init_tables()
    db.init_test_user()
    print("✓ Сервер запущен на http://localhost:8000")


# ── Page routes ──────────────────────────────
@app.get("/", response_class=HTMLResponse)
def root():
    return (FRONTEND_DIR / "login.html").read_text(encoding="utf-8")


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return (FRONTEND_DIR / "upload.html").read_text(encoding="utf-8")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return (FRONTEND_DIR / "dashboard.html").read_text(encoding="utf-8")


# ── Auth ─────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(creds: LoginRequest):
    user = db.query_one("SELECT * FROM users WHERE email = ?", (creds.email,))
    if not user or not check_password_hash(user["password"], creds.password):
        return {"success": False, "message": "Неверный логин или пароль"}
    return {
        "success": True,
        "message": "Вход выполнен",
        "access_token": f"user_{user['id']}",
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name", ""),
    }


# ── Products ─────────────────────────────────
@app.get("/products")
def get_products():
    rows = db.query("""
        SELECT
            p.id,
            p.name,
            p.category,
            COUNT(r.id)  AS review_count,
            COUNT(a.id)  AS analyzed_count
        FROM products p
        LEFT JOIN reviews          r ON r.product_id = p.id
        LEFT JOIN analysis_results a ON a.review_id  = r.id
        GROUP BY p.id
        ORDER BY review_count DESC, p.name
    """)
    return rows


# ── Reviews ──────────────────────────────────
@app.get("/reviews")
def get_reviews(product_id: int = None, limit: int = 200):
    if product_id:
        rows = db.query(
            """
            SELECT
                r.id, r.product_id, r.customer_name,
                r.review_text, r.status, r.created_at,
                a.sentiment, a.summary, a.aspects
            FROM reviews r
            LEFT JOIN analysis_results a ON a.review_id = r.id
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (product_id, limit),
        )
    else:
        rows = db.query(
            """
            SELECT
                r.id, r.product_id, r.customer_name,
                r.review_text, r.status, r.created_at,
                a.sentiment, a.summary, a.aspects
            FROM reviews r
            LEFT JOIN analysis_results a ON a.review_id = r.id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    for row in rows:
        raw = row.get("aspects")
        if raw and isinstance(raw, str):
            try:
                row["aspects"] = json.loads(raw)
            except Exception:
                row["aspects"] = []
        elif not raw:
            row["aspects"] = []

    return rows


# ── Stats ────────────────────────────────────
@app.get("/stats")
def get_stats(product_id: int = None):
    """
    Returns sentiment statistics (excluding neutral reviews).
    Neutral reviews are stored in DB but not counted in stats/dashboard.
    """
    if product_id:
        rows = db.query(
            """
            SELECT a.sentiment, COUNT(*) AS cnt
            FROM reviews r
            JOIN analysis_results a ON a.review_id = r.id
            WHERE r.product_id = ? AND a.sentiment != 'neutral'
            GROUP BY a.sentiment
            """,
            (product_id,),
        )
    else:
        rows = db.query(
            """
            SELECT sentiment, COUNT(*) AS cnt
            FROM analysis_results
            WHERE sentiment != 'neutral'
            GROUP BY sentiment
            """
        )

    result = {"positive": 0, "negative": 0, "mixed": 0, "total": 0}
    for row in rows:
        s = row["sentiment"] or "neutral"
        result[s] = result.get(s, 0) + row["cnt"]
        result["total"] += row["cnt"]
    return result


# ── Aspects ──────────────────────────────────
@app.get("/aspects")
def get_aspects(product_id: int = None):
    """
    Returns aspect-based sentiment analysis (excluding neutral reviews).
    """
    if product_id:
        rows = db.query(
            """
            SELECT a.aspects
            FROM reviews r
            JOIN analysis_results a ON a.review_id = r.id
            WHERE r.product_id = ? AND a.aspects IS NOT NULL AND a.sentiment != 'neutral'
            """,
            (product_id,),
        )
    else:
        rows = db.query(
            "SELECT aspects FROM analysis_results WHERE aspects IS NOT NULL AND sentiment != 'neutral'"
        )

    agg: dict[str, dict] = {}
    for row in rows:
        raw = row.get("aspects")
        if not raw:
            continue
        try:
            aspects = json.loads(raw) if isinstance(raw, str) else raw
            for asp in aspects:
                cat  = asp.get("category", "").strip()
                sent = asp.get("sentiment", "neutral")
                snip = asp.get("snippet", "")
                if not cat:
                    continue
                if cat not in agg:
                    agg[cat] = {
                        "positive": 0, "negative": 0,
                        "neutral": 0, "mixed": 0, "total": 0,
                        "snippets": [],
                    }
                agg[cat][sent] = agg[cat].get(sent, 0) + 1
                agg[cat]["total"] += 1
                if snip and len(agg[cat]["snippets"]) < 3:
                    agg[cat]["snippets"].append(snip)
        except Exception:
            pass

    sorted_agg = sorted(agg.items(), key=lambda x: x[1]["total"], reverse=True)
    return [{"category": k, **v} for k, v in sorted_agg[:15]]


# ── Upload CSV ───────────────────────────────
@app.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # Try UTF-8 with BOM first, then cp1251
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = contents.decode("cp1251")

        reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
        if reader.fieldnames is None:
            return {"success": False, "error": "Не удалось определить заголовки CSV"}

        added    = 0
        analyzed = 0
        errors   = []

        for i, row in enumerate(reader, 1):
            try:
                # Normalise keys
                row = {k.strip(): (v or "").strip() for k, v in row.items() if k}

                product_name  = row.get("product_name", "").strip()
                category      = row.get("category", "Электроника").strip() or "Электроника"
                customer_name = row.get("customer_name", "Аноним").strip() or "Аноним"
                review_text   = row.get("review_text", "").strip()
                created_at    = row.get("created_at", "").strip() or None

                if not product_name:
                    errors.append(f"Строка {i}: пустое поле product_name — пропущена")
                    continue
                if not review_text or len(review_text) < 5:
                    errors.append(f"Строка {i}: слишком короткий или пустой review_text — пропущена")
                    continue

                # Get or create product
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

                # Insert review
                review_id = db.exec(
                    "INSERT INTO reviews (product_id, customer_name, review_text, status, created_at) "
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (pid, customer_name, review_text, created_at),
                )
                added += 1

                # Analyse with Ollama
                cat = row.get("category", "") or "электроника"
                sentiment, summary, aspects = analyze_review(review_text, cat)

                if sentiment in ("error", "unknown"):
                    errors.append(f"Строка {i}: ошибка анализа — {summary}")
                else:
                    aspects_json = json.dumps(aspects, ensure_ascii=False)
                    db.exec(
                        "INSERT OR REPLACE INTO analysis_results "
                        "(review_id, sentiment, summary, aspects) VALUES (?, ?, ?, ?)",
                        (review_id, sentiment, summary, aspects_json),
                    )
                    db.exec(
                        "UPDATE reviews SET status = 'analyzed' WHERE id = ?",
                        (review_id,),
                    )
                    analyzed += 1

            except Exception as e:
                errors.append(f"Строка {i}: {e}")

        return {
            "success": True,
            "message": f"Сохранено {added} отзывов, проанализировано {analyzed}",
            "added": added,
            "analyzed": analyzed,
            "errors": errors[:30],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Upload CSV with Progress (Polling-based) ────
@app.post("/upload/csv/stream")
async def upload_csv_stream(file: UploadFile = File(...)):
    """
    Загрузка CSV: первый проход добавляет отзывы, второй анализирует.
    Клиент использует polling для проверки прогресса анализа.
    Возвращает: {"total": N, "added": N, "upload_session_id": "..."}
    """
    try:
        contents = await file.read()
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = contents.decode("cp1251")

        # Парсим CSV с skipinitialspace=True для robustness
        reader = csv.DictReader(io.StringIO(text), skipinitialspace=True)
        if reader.fieldnames is None:
            return JSONResponse({"success": False, "error": "Не удалось определить заголовки CSV"}, status_code=400)

        rows = list(reader)
        total = len(rows)
        
        added = 0
        errors = []
        reviews_to_analyze = []  # Список отзывов для анализа

        # ПЕРВЫЙ ПРОХОД: Добавляем отзывы в БД (быстрый)
        for i, row in enumerate(rows, 1):
            try:
                # Очищаем ключи и значения
                clean_row = {k.strip(): (v or "").strip() for k, v in row.items() if k}

                product_name  = clean_row.get("product_name", "").strip()
                category      = clean_row.get("category", "Электроника").strip() or "Электроника"
                customer_name = clean_row.get("customer_name", "Аноним").strip() or "Аноним"
                review_text   = clean_row.get("review_text", "").strip()
                created_at    = clean_row.get("created_at", "").strip() or None

                if not product_name:
                    errors.append(f"Строка {i}: пустое поле product_name")
                    continue
                
                if not review_text or len(review_text) < 5:
                    errors.append(f"Строка {i}: слишком короткий отзыв")
                    continue

                # Получаем или создаем товар
                product = db.query_one("SELECT id FROM products WHERE name = ?", (product_name,))
                if not product:
                    pid = db.exec(
                        "INSERT INTO products (name, category) VALUES (?, ?)",
                        (product_name, category),
                    )
                else:
                    pid = product["id"]

                # Добавляем отзыв
                review_id = db.exec(
                    "INSERT INTO reviews (product_id, customer_name, review_text, status, created_at) "
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (pid, customer_name, review_text, created_at),
                )
                added += 1
                
                # Сохраняем для последующего анализа
                cat = clean_row.get("category", "") or "электроника"
                reviews_to_analyze.append((review_id, review_text, cat))

            except Exception as e:
                errors.append(f"Строка {i}: {str(e)}")

        # ВТОРОЙ ПРОХОД: Анализируем отзывы в фоне
        import threading
        def analyze_in_background():
            for review_id, review_text, category in reviews_to_analyze:
                try:
                    sentiment, summary, aspects = analyze_review(review_text, category)
                    
                    if sentiment not in ("error", "unknown"):
                        aspects_json = json.dumps(aspects, ensure_ascii=False)
                        db.exec(
                            "INSERT OR REPLACE INTO analysis_results "
                            "(review_id, sentiment, summary, aspects) VALUES (?, ?, ?, ?)",
                            (review_id, sentiment, summary, aspects_json),
                        )
                        db.exec(
                            "UPDATE reviews SET status = 'analyzed' WHERE id = ?",
                            (review_id,),
                        )
                except Exception as e:
                    # Логируем ошибку анализа
                    pass

        # Запускаем анализ в фоновом потоке
        thread = threading.Thread(target=analyze_in_background, daemon=True)
        thread.start()

        return JSONResponse({
            "success": True,
            "total": total,
            "added": added,
            "errors": errors[:30],
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── Check Upload Progress ────
@app.get("/upload/progress")
def check_upload_progress(product_id: int = None):
    """
    Проверяет прогресс анализа.
    Возвращает: {"pending": N, "analyzed": N, "total": N, "percentage": N}
    """
    if product_id:
        pending = db.query_one(
            "SELECT COUNT(*) as cnt FROM reviews WHERE product_id = ? AND status = 'pending'",
            (product_id,)
        )
        analyzed = db.query_one(
            "SELECT COUNT(*) as cnt FROM reviews WHERE product_id = ? AND status = 'analyzed'",
            (product_id,)
        )
    else:
        pending = db.query_one(
            "SELECT COUNT(*) as cnt FROM reviews WHERE status = 'pending'"
        )
        analyzed = db.query_one(
            "SELECT COUNT(*) as cnt FROM reviews WHERE status = 'analyzed'"
        )
    
    pending_cnt = pending["cnt"] if pending else 0
    analyzed_cnt = analyzed["cnt"] if analyzed else 0
    total = pending_cnt + analyzed_cnt
    
    percentage = 0
    if total > 0:
        percentage = int((analyzed_cnt / total) * 100)
    
    return {
        "pending": pending_cnt,
        "analyzed": analyzed_cnt,
        "total": total,
        "percentage": percentage,
    }


# ── HTML Report (print-to-PDF) ───────────────
@app.get("/report/html", response_class=HTMLResponse)
def get_report_html(product_id: int, user: str = ""):
    product = db.query_one("SELECT * FROM products WHERE id = ?", (product_id,))
    if not product:
        return HTMLResponse("<h1>Товар не найден</h1>", status_code=404)

    reviews = db.query(
        """
        SELECT r.customer_name, r.review_text, r.created_at,
               a.sentiment, a.summary, a.aspects
        FROM reviews r
        LEFT JOIN analysis_results a ON a.review_id = r.id
        WHERE r.product_id = ? AND a.sentiment != 'neutral'
        ORDER BY r.created_at DESC
        """,
        (product_id,),
    )

    sentiment_counts = {"positive": 0, "negative": 0, "mixed": 0}
    aspect_agg: dict[str, dict] = {}
    
    # Собираем сырые цитаты для последующей умной сортировки
    raw_snippets =[]

    for r in reviews:
        s = r.get("sentiment") or "mixed"
        if s in sentiment_counts:
            sentiment_counts[s] += 1

        raw = r.get("aspects")
        try:
            aspects = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except Exception:
            aspects =[]

        for asp in aspects:
            cat  = asp.get("category", "").strip()
            sent = asp.get("sentiment", "mixed")
            snip = asp.get("snippet", "").strip()
            
            if not cat:
                continue
                
            if cat not in aspect_agg:
                aspect_agg[cat] = {"positive": 0, "negative": 0, "mixed": 0, "total": 0}
            
            aspect_agg[cat][sent] = aspect_agg[cat].get(sent, 0) + 1
            aspect_agg[cat]["total"] += 1
            
            if snip:
                raw_snippets.append({
                    "aspect": cat, 
                    "sentiment": sent, 
                    "snippet": snip, 
                    "author": r.get("customer_name", "")
                })

    # Сортировка ТОП-5 аспектов для графиков (по общему количеству упоминаний)
    top5 = sorted(aspect_agg.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    
    # Умная сортировка цитат (Сначала негатив по популярности аспекта, затем позитив)
    # 1. Отбираем только negative и positive
    filtered_snippets =[s for s in raw_snippets if s["sentiment"] in ["negative", "positive"]]
    
    # 2. Сортируем: 
    # приоритет 1: sentiment (negative идет первым, т.к. "n" < "p" в алфавите)
    # приоритет 2: частота негативных упоминаний этого аспекта (по убыванию)
    filtered_snippets.sort(
        key=lambda x: (
            0 if x["sentiment"] == "negative" else 1,  # Сначала негативные (0), потом позитивные (1)
            -aspect_agg[x["aspect"]].get("negative", 0) if x["sentiment"] == "negative" else -aspect_agg[x["aspect"]].get("positive", 0)
        )
    )
    
    # Берем только первые 10 цитат, чтобы влезло на А4
    final_snippets = filtered_snippets[:10]

    total = sum(sentiment_counts.values())
    today = datetime.now().strftime("%d.%m.%Y")

    # Build HTML
    html = _build_report_html(product, total, today, sentiment_counts, top5, final_snippets, product_id, user)
    return HTMLResponse(content=html)


# ── Report HTML builder ──────────────────────
def _build_report_html(product, total, today, sent, top5, snippets, product_id=0, user=""):
    def badge(s):
        colors = {"positive":"#22c55e","negative":"#ef4444"}
        labels = {"positive":"Положительная","negative":"Отрицательная"}
        return f'<span style="color:{colors.get(s,"#94a3b8")};font-weight:600">{labels.get(s,s)}</span>'

    user_display = user or "пользователь"

    # Рендеринг строк таблицы цитат
    snippet_rows_html = "".join(f"""
        <tr>
          <td style="font-weight:600;color:#1e293b">{sn['aspect']}</td>
          <td>{badge(sn['sentiment'])}</td>
          <td style="color:#334155">«{sn['snippet']}»</td>
        </tr>""" for sn in snippets)

    # Данные для круговой диаграммы
    pie_data = json.dumps([sent["positive"], sent["negative"], sent["mixed"]])
    
    # Расчет CSAT для центра круга
    csat = round((sent["positive"] / total) * 100) if total > 0 else 0

    # Рендеринг ТОП-5 аспектов (Только Позитив и Негатив)
    asp_html = ""
    for cat, data in top5:
        # Для полоски берем только сумму позитива и негатива
        bar_total = data.get("positive", 0) + data.get("negative", 0)
        if bar_total == 0: 
            continue # Пропускаем, если были только смешанные
            
        pw = round(data.get("positive", 0) / bar_total * 100, 1)
        nw = round(data.get("negative", 0) / bar_total * 100, 1)
        
        asp_html += f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;font-family:'Onest',sans-serif">
            <span style="font-weight:700;color:#1e293b">{cat}</span>
            <span>
              <span style="color:#16a34a;font-weight:700">{data.get('positive',0)}</span> /
              <span style="color:#dc2626;font-weight:700">{data.get('negative',0)}</span>
            </span>
          </div>
          <div style="display:flex;height:10px;border-radius:4px;overflow:hidden;background:#e2e8f0">
            <div style="width:{pw}%;background:#22c55e;height:100%"></div>
            <div style="width:{nw}%;background:#ef4444;height:100%"></div>
          </div>
        </div>"""

    doc_title = f"{product['name']}_отчёт-{today}-{user_display}-No{product_id}"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{doc_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Onest',sans-serif}}
body{{
  background:#f1f5f9;
  display:flex;flex-direction:column;align-items:center;
  padding:56px 20px 40px;
  min-height:100vh;
}}
.toolbar{{
  position:fixed;top:0;left:0;right:0;
  display:flex;align-items:center;justify-content:space-between;
  background:#1e293b;border-bottom:1px solid #334155;
  padding:10px 20px;z-index:200;
}}
.toolbar-title{{font-size:13px;color:#94a3b8;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60%}}
.print-btn{{
  padding:7px 18px;background:#2563eb;color:#fff;
  border:none;border-radius:7px;font-size:12px;font-weight:700;
  cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:background .2s;
}}
.print-btn:hover{{background:#1d4ed8}}
.page{{
  background:#fff;width:210mm;
  padding:16mm 18mm 18mm;
  box-shadow:0 4px 24px rgba(0,0,0,.15);
  position:relative;
}}
.header{{border-bottom:2px solid #1e293b;padding-bottom:10px;margin-bottom:18px;
         display:flex;justify-content:space-between;align-items:flex-end}}
.header h1{{font-size:18px;color:#1e293b;font-weight:700;line-height:1.2}}
.hmeta{{text-align:right;font-size:11px;color:#64748b;line-height:1.7}}
.ptitle{{font-size:17px;font-weight:700;color:#2563eb;margin-bottom:3px}}
.psub{{font-size:11px;color:#64748b;margin-bottom:20px}}
h3{{font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;
    letter-spacing:.5px;margin:0 0 10px}}
.charts-row{{display:grid;grid-template-columns:180px 1fr;gap:20px;margin-bottom:20px}}
.cbox{{background:#f8fafc;border-radius:8px;padding:14px;border:1px solid #e2e8f0}}

/* Контейнер для круговой диаграммы с CSAT в центре */
.pie-container {{ position:relative;height:140px;margin-bottom:10px;display:flex;justify-content:center;align-items:center; }}
.pie-center-text {{ position:absolute;text-align:center;pointer-events:none; }}
.pie-center-value {{ font-size:22px;font-weight:700;color:#1e293b;line-height:1; }}
.pie-center-label {{ font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase; }}

.dl{{display:flex;align-items:center;gap:6px;font-size:11px;margin-bottom:5px}}
.dd{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.dn{{flex:1;color:#475569}}
.dv{{font-weight:700;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
thead tr{{background:#1e293b;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
th{{background:#1e293b !important;color:#fff !important;padding:7px 10px;text-align:left;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}}
td{{padding:7px 10px;border-bottom:1px solid #e2e8f0;color:#334155;vertical-align:top}}
tr:nth-child(even) td{{background:#f8fafc}}
.footer{{margin-top:20px;padding-top:8px;border-top:1px solid #e2e8f0;
         font-size:10px;color:#94a3b8;text-align:center}}

/* ─ PRINT ─────────────────────────── */
@page{{margin:0}}
@media print{{
  *{{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}}
  .toolbar{{display:none !important}}
  body{{background:#fff;padding:12mm 0;display:block}}
  .page{{
    box-shadow:none;width:100%;
    padding:0 12mm;
    page-break-after:avoid;
    break-after:avoid;
  }}
  th{{background:#1e293b !important;color:#fff !important}}
  thead{{display:table-header-group}}
}}
</style>
</head>
<body>

<div class="toolbar">
  <span class="toolbar-title">📄 {product['name']} — аналитический отчёт</span>
  <button class="print-btn" onclick="window.print()">🖨 Сохранить</button>
</div>

<div class="page">
  <div class="header">
    <div>
      <h1>Аналитический отчёт качества товара</h1>
      <div style="font-size:11px;color:#64748b;margin-top:3px">Подсистема интеллектуального анализа отзывов</div>
    </div>
    <div class="hmeta">
      <div><b>Дата:</b> {today}</div>
      <div><b>Автор:</b> {user_display}</div>
      <div><b>№:</b> {product_id}</div>
    </div>
  </div>

  <div class="ptitle">{product['name']}</div>
  <div class="psub">Категория: {product['category']} &nbsp;·&nbsp; Проанализировано отзывов: <b>{total}</b></div>

  <div class="charts-row">
    <div class="cbox">
      <h3>1. Тональность</h3>
      <div class="pie-container">
        <canvas id="pieChart"></canvas>
        <div class="pie-center-text">
            <div class="pie-center-value">{csat}%</div>
        </div>
      </div>
      <div class="dl"><span class="dd" style="background:#22c55e"></span><span class="dn">Положительные</span><span class="dv" style="color:#16a34a">{sent['positive']}</span></div>
      <div class="dl"><span class="dd" style="background:#ef4444"></span><span class="dn">Отрицательные</span><span class="dv" style="color:#dc2626">{sent['negative']}</span></div>
      <div class="dl"><span class="dd" style="background:#f59e0b"></span><span class="dn">Смешанные</span><span class="dv" style="color:#d97706">{sent['mixed']}</span></div>
    </div>

    <div class="cbox">
      <h3>2. Топ-5 аспектов &nbsp;<span style="font-weight:400;color:#94a3b8">(+ положительных / − отрицательных)</span></h3>
      {asp_html or '<div style="color:#94a3b8;font-size:12px;padding:8px 0">Нет данных</div>'}
    </div>
  </div>

  <h3>3. Подтверждающие выдержки из отзывов (Проблемы)</h3>
  <table>
    <thead><tr><th style="width:16%">Аспект</th><th style="width:16%">Тональность</th><th>Цитата клиента</th></tr></thead>
    <tbody>{snippet_rows_html or '<tr><td colspan="3" style="color:#94a3b8;text-align:center;padding:16px">Нет данных</td></tr>'}</tbody>
  </table>

  <div class="footer">Сгенерировано автоматически · {today} · Стр. 1 из 1</div>
</div>

<script>
document.title = "{doc_title}";
Chart.defaults.animation = false;
new Chart(document.getElementById('pieChart').getContext('2d'), {{
  type:'doughnut',
  data:{{datasets:[{{data:{pie_data},backgroundColor:['#22c55e','#ef4444','#f59e0b'],borderWidth:0}}]}},
  options:{{
    responsive:true,maintainAspectRatio:false,cutout:'70%',
    plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}}
  }}
}});
</script>
</body>
</html>"""


# ── Run ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
