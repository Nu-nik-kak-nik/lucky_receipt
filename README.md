# Чек на удачу — промо-акция

Django-приложение для регистрации покупательских чеков с последующей модерацией.

## Запуск

1. `cp .env.example .env` и при необходимости отредактируйте значения (как минимум SECRET_KEY).
2. `docker compose up --build`
3. Откройте http://localhost:8000

Первый суперпользователь (модератор):

```bash
docker compose exec web python manage.py createsuperuser
