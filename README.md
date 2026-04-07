# KSEBE Analytics — инструкция по деплою

## Что это
Веб-приложение для аналитики KSEBE, интегрированное с YCLIENTS через маркетплейс.

## Деплой на Railway (бесплатно, 5 минут)

### Шаг 1 — GitHub
1. Зайди на https://github.com
2. Нажми "+" → "New repository"
3. Назови: `ksebe-analytics`
4. Нажми "Create repository"
5. Загрузи все файлы этой папки (кнопка "uploading an existing file")

### Шаг 2 — Railway
1. Зайди на https://railway.app
2. Нажми "Start a New Project"
3. Выбери "Deploy from GitHub repo"
4. Выбери репозиторий `ksebe-analytics`
5. Railway автоматически определит Python и задеплоит

### Шаг 3 — Переменные окружения
В Railway → твой проект → Variables добавь:
- `PARTNER_TOKEN` = `HFG35p0420g7Q2Pn0K8O`
- `SECRET_KEY` = любой случайный текст, например `ksebe-super-secret-2024`

### Шаг 4 — Получи URL
В Railway → Settings → Domains → нажми "Generate Domain"
Получишь URL вида: `https://ksebe-analytics-production.up.railway.app`

### Шаг 5 — Настрой приложение в кабинете разработчика YCLIENTS
1. Зайди в кабинет разработчика YCLIENTS
2. В настройках приложения укажи:
   - **Registration redirect URL**: `https://ВАШ-URL.railway.app/connect`
   - **Disconnect URL**: `https://ВАШ-URL.railway.app/disconnect`
3. Для iframe-расширения укажи:
   - **iframe URL**: `https://ВАШ-URL.railway.app/dashboard/{salon_id}`

## Структура файлов
```
ksebe-analytics/
├── app.py              # Сервер (Flask)
├── requirements.txt    # Зависимости Python
├── Procfile            # Команда запуска
├── railway.json        # Конфиг Railway
└── templates/
    ├── index.html      # Главная страница
    ├── connect.html    # Форма подключения
    └── dashboard.html  # Дашборд аналитики
```

## API эндпоинты
- `GET  /`                  — главная страница
- `GET  /connect?salon_id=` — форма подключения (сюда редиректит YCLIENTS)
- `POST /activate`          — активация интеграции
- `POST /disconnect`        — отключение (вызывает YCLIENTS)
- `GET  /dashboard/:id`     — дашборд для филиала
- `GET  /api/data/:id`      — JSON с данными (для дашборда)
- `GET  /health`            — проверка работоспособности
