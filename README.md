# Анализ отзывов (Дипломный проект)

Данное руководство содержит пошаговую инструкцию по установке языковой модели и запуску программного комплекса.

## ШАГ 1: УСТАНОВКА МОДЕЛИ

1.  **Загрузка весов:**
    Скачайте модель по ссылке: [Qwen3-4B-Instruct-2507-GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF?show_file_info=Qwen3-4B-Instruct-2507-Q4_K_M.gguf)
2.  **Подготовка Modelfile:**
    Сохраните файл в любую доступную папку. В этой же папке рядом с `.gguf` создайте файл `Modelfile` без расширения. Запишите в него (указав путь к файлу):
    ```dockerfile
    FROM ./Qwen3-4B-Instruct-2507-Q4_K_M.gguf
    ```
3.  **Переход в каталог:**
    В `cmd` от имени администратора перейдите в папку с этими файлами.
4.  **Создание модели в Ollama:**
    Введите команду:
    ```bash
    ollama create qwen3:4b-instruct -f Modelfile
    ```
    *Ожидаемый результат: "success".*
5.  **Проверка запуска:**
    Запустите модель:
    ```bash
    ollama run qwen3:4b-instruct
    ```
    *Если отвечает без долгого рассуждения — готово.*

---

## ШАГ 2: УСТАНОВКА И ЗАПУСК ПРОГРАММЫ

1.  **Клонирование репозитория:**
    ```bash
    git clone [https://github.com/VintikG/review-analysis-diplom.git](https://github.com/VintikG/review-analysis-diplom.git)
    ```
2.  **Проверка Python:**
    ```bash
    python --version
    ```
    *(Требуется версия 3.9+)*
3.  **Создание виртуального окружения:**
    ```bash
    python -m venv .venv
    ```
4.  **Активация окружения (Windows):**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
5.  **Установка зависимостей:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Инициализация БД:**
    ```bash
    python storage_simple.py
    ```
7.  **Запуск Ollama:**
    В отдельном терминале выполните:
    ```bash
    ollama serve
    ```
    *(Если возникнет ошибка "Error: listen tcp 127.0.0.1:11434", проверьте статус по адресу http://localhost:11434/ — должно быть "Ollama is running")*
8.  **Запуск сервера:**
    В терминале VS Code (с активным `.venv`) выполните:
    ```bash
    python -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
    ```
    *Или просто:*
    ```bash
    python main_simple.py
    ```
9.  **Доступ к приложению:**
    Откройте браузер по адресу: [http://localhost:8000](http://localhost:8000)

### Данные для авторизации:
*   **Ниже представлена переработанная версия вашего текста, приведенная к стандартному формату `README.md`. Текст и шаги сохранены без изменений, но структурированы с использованием Markdown-разметки для корректного отображения на GitHub.

---

# Анализ отзывов (Дипломный проект)

Данное руководство содержит пошаговую инструкцию по установке языковой модели и запуску программного комплекса.

## ШАГ 1: УСТАНОВКА МОДЕЛИ

1.  **Загрузка весов:**
    Скачайте модель по ссылке: [Qwen3-4B-Instruct-2507-GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF?show_file_info=Qwen3-4B-Instruct-2507-Q4_K_M.gguf)
2.  **Подготовка Modelfile:**
    Сохраните файл в любую доступную папку. В этой же папке рядом с `.gguf` создайте файл `Modelfile` без расширения. Запишите в него (указав путь к файлу):
    ```dockerfile
    FROM ./Qwen3-4B-Instruct-2507-Q4_K_M.gguf
    ```
3.  **Переход в каталог:**
    В `cmd` от имени администратора перейдите в папку с этими файлами.
4.  **Создание модели в Ollama:**
    Введите команду:
    ```bash
    ollama create qwen3:4b-instruct -f Modelfile
    ```
    *Ожидаемый результат: "success".*
5.  **Проверка запуска:**
    Запустите модель:
    ```bash
    ollama run qwen3:4b-instruct
    ```
    *Если отвечает без долгого рассуждения — готово.*

---

## ШАГ 2: УСТАНОВКА И ЗАПУСК ПРОГРАММЫ

1.  **Клонирование репозитория:**
    ```bash
    git clone [https://github.com/VintikG/review-analysis-diplom.git](https://github.com/VintikG/review-analysis-diplom.git)
    ```
2.  **Проверка Python:**
    ```bash
    python --version
    ```
    *(Требуется версия 3.9+)*
3.  **Создание виртуального окружения:**
    ```bash
    python -m venv .venv
    ```
4.  **Активация окружения (Windows):**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
5.  **Установка зависимостей:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Инициализация БД:**
    ```bash
    python storage_simple.py
    ```
7.  **Запуск Ollama:**
    В отдельном терминале выполните:
    ```bash
    ollama serve
    ```
    *(Если возникнет ошибка "Error: listen tcp 127.0.0.1:11434", проверьте статус по адресу http://localhost:11434/ — должно быть "Ollama is running")*
8.  **Запуск сервера:**
    В терминале VS Code (с активным `.venv`) выполните:
    ```bash
    python -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
    ```
    *Или просто:*
    ```bash
    python main_simple.py
    ```
9.  **Доступ к приложению:**
    Откройте браузер по адресу: [http://localhost:8000](http://localhost:8000)

### Данные для авторизации:
*   **Логин:** `Ivanov@mail.ru`
*   **Пароль:** `userНиже представлена переработанная версия вашего текста, приведенная к стандартному формату `README.md`. Текст и шаги сохранены без изменений, но структурированы с использованием Markdown-разметки для корректного отображения на GitHub.

---

# Анализ отзывов (Дипломный проект)

Данное руководство содержит пошаговую инструкцию по установке языковой модели и запуску программного комплекса.

## ШАГ 1: УСТАНОВКА МОДЕЛИ

1.  **Загрузка весов:**
    Скачайте модель по ссылке: [Qwen3-4B-Instruct-2507-GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF?show_file_info=Qwen3-4B-Instruct-2507-Q4_K_M.gguf)
2.  **Подготовка Modelfile:**
    Сохраните файл в любую доступную папку. В этой же папке рядом с `.gguf` создайте файл `Modelfile` без расширения. Запишите в него (указав путь к файлу):
    ```dockerfile
    FROM ./Qwen3-4B-Instruct-2507-Q4_K_M.gguf
    ```
3.  **Переход в каталог:**
    В `cmd` от имени администратора перейдите в папку с этими файлами.
4.  **Создание модели в Ollama:**
    Введите команду:
    ```bash
    ollama create qwen3:4b-instruct -f Modelfile
    ```
    *Ожидаемый результат: "success".*
5.  **Проверка запуска:**
    Запустите модель:
    ```bash
    ollama run qwen3:4b-instruct
    ```
    *Если отвечает без долгого рассуждения — готово.*

---

## ШАГ 2: УСТАНОВКА И ЗАПУСК ПРОГРАММЫ

1.  **Клонирование репозитория:**
    ```bash
    git clone [https://github.com/VintikG/review-analysis-diplom.git](https://github.com/VintikG/review-analysis-diplom.git)
    ```
2.  **Проверка Python:**
    ```bash
    python --version
    ```
    *(Требуется версия 3.9+)*
3.  **Создание виртуального окружения:**
    ```bash
    python -m venv .venv
    ```
4.  **Активация окружения (Windows):**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
5.  **Установка зависимостей:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Инициализация БД:**
    ```bash
    python storage_simple.py
    ```
7.  **Запуск Ollama:**
    В отдельном терминале выполните:
    ```bash
    ollama serve
    ```
    *(Если возникнет ошибка "Error: listen tcp 127.0.0.1:11434", проверьте статус по адресу http://localhost:11434/ — должно быть "Ollama is running")*
8.  **Запуск сервера:**
    В терминале VS Code (с активным `.venv`) выполните:
    ```bash
    python -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
    ```
    *Или просто:*
    ```bash
    python main_simple.py
    ```
9.  **Доступ к приложению:**
    Откройте браузер по адресу: [http://localhost:8000](http://localhost:8000)

### Данные для авторизации:
*   **Логин:** `Ivanov@mail.ru`
*   **Пароль:** `user`
