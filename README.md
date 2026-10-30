# AI Text Editor / AI редактор текста

Локальный редактор текста с AI (русский и английский интерфейс). LLM — [Polza AI](https://polza.ai) (OpenAI-compatible API).

**Репозиторий:** [github.com/Evelinamyagdeeva/ai_text_editor](https://github.com/Evelinamyagdeeva/ai_text_editor)

## Возможности

- **Редактор** — TipTap, выделение фрагмента или правка всего документа
- **AI-инструменты** — правка, анализ, создание (секции раскрываются по клику)
- **Своя инструкция** — произвольный запрос с предпросмотром diff
- **Чаты** — переименование, закрепление, удаление (ПКМ)
- **Документы** — список в сайдбаре, переименование и удаление (ПКМ)
- **Экспорт** — TXT, Markdown, HTML, DOCX, PDF
- **Импорт** — TXT, MD, DOCX, PDF
- **Версии** — история и откат
- **Предпросмотр правки** — resizable нижняя панель, принять / отклонить

## Требования

- Python **3.9+** (лучше 3.10+)
- Node.js **20+**
- Ключ **Polza** в `backend/.env`

## Быстрый старт

### 1. Backend (порт **8001**)

```bash
cd backend
cp .env.example .env
# Вставьте POLZA_AI_API_KEY в .env

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте **http://127.0.0.1:5173** — Vite проксирует `/api` на `http://127.0.0.1:8001`.

> Не используйте порт **8000** для этого проекта, если там уже запущено другое приложение.

## Настройка

| Переменная | Описание |
|------------|----------|
| `POLZA_AI_API_KEY` | API-ключ Polza (обязательно) |
| `POLZA_AI_MODEL_NAME` | Модель, по умолчанию `openai/gpt-6-luna` |
| `POLZA_AI_BASE_URL` | Обычно `https://polza.ai/api/v1` |
| `EDITOR_UI_LOCALE` | `ru` или `en` |

В приложении: **⚙ Настройки** — URL, модель и язык (модель может сохраняться в SQLite).

Данные: `backend/data/editor.db` (не коммитится).

## Структура проекта

```
backend/
  app/           FastAPI, агенты, SQLite, экспорт/импорт
  .env.example   шаблон конфигурации
frontend/
  src/           React, TipTap, i18n
```

## API (кратко)

- `GET /api/health` — проверка
- `POST /api/workspace/bootstrap` — старт сессии
- `POST /api/documents/{id}/edit` — предложение правки
- `POST /api/documents/{id}/accept` — принять правку
- `GET /api/documents/{id}/export?format=txt|md|html|docx|pdf`

## Сборка фронтенда

```bash
cd frontend && npm run build
```

## Лицензия

Проект для личного использования; при публикации добавьте лицензию по желанию.
