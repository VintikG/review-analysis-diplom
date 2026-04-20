═══════════════════════════════════════════════════════════════════════════════
ШАГ 1: УСТАНОВКА МОДЕЛИ
═══════════════════════════════════════════════════════════════════════════════

1. https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF?show_file_info=Qwen3-4B-Instruct-2507-Q4_K_M.gguf

2. Сохрани в любую доступную папку, в этой папке рядом с .gguf создай файл "Modelfile" без формата, в него запиши:

3. В cmd от имени администратора перейти в папку с этими файлами

4. Ввести ollama create qwen3:4b-instruct -f Modelfile
   - "success" - готово

5. Запускаем: ollama run qwen3:4b-instruct
   - если отвечает без долгого рассуждения - готово

═══════════════════════════════════════════════════════════════════════════════
ШАГ 2: УСТАНОВКА И ЗАПУСК ПРОГРАММЫ
═══════════════════════════════════════════════════════════════════════════════

1. Клонировать репозиторий:
   git clone https://github.com/VintikG/review-analysis-diplom.git

2. Проверьте Python:
   python --version
   (нужна версия 3.9+)

3. Создайте виртуальное окружение:
   python -m venv .venv

4. Активируйте окружение на Windows:
   .venv\Scripts\Activate.ps1

5. Установите зависимости:
   pip install -r requirements.txt

6. Инициализируйте БД:
   python storage_simple.py

7. Запустите Ollama в отдельном терминале:
   ollama serve
   - (если будет ошибка "Error: listen tcp 127.0.0.1:11434", то перейди на http://localhost:11434/ должно быть "Ollama is running")

8. Запустите сервер в терминале VS code (.venv):
   python -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
   - или просто:
     python main_simple.py

9. Откройте браузер:
   http://localhost:8000
   - логин: Ivanov@mail.ru
   - пароль: user
