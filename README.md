![Main Foodgram workflow](https://github.com/BimBoBam/foodgram/actions/workflows/main.yml/badge.svg)

# Проект Foodgram
[Foodgram](https://verycoolrecipes.zapto.org)
[Ссылка на api/docs](https://verycoolrecipes.zapto.org/api/docs)
## Описание проекта
Foodgram - продуктовый помощник с базой кулинарных рецептов. Позволяет публиковать рецепты, сохранять избранные, а также формировать список покупок для выбранных рецептов. Можно подписываться на любимых авторов.

## Технологии
•	Python 3.9
•	Django==3.2.3
•	djangorestframework==3.12.4
•	nginx
•	gunicorn==20.1.0
•   djoser==2.1.0

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/BimBoBam/foodgram
```

Перейти в директорию foodgram
```
cd foodgram
```

Создать файл .evn для хранения ключей:

```
SECRET_KEY='указать секретный ключ'
ALLOWED_HOSTS='указать имя или IP хоста'
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_NAME=foodgram
DB_HOST=db
DEBUG=False
```

Перейти в директорию infra
```
cd infra
```

Запустить docker-compose.production:

```
docker compose -f docker-compose.production.yml up
```

Выполнить миграции, сбор статики:

```
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
docker compose -f docker-compose.production.yml exec backend python manage.py import_data
```

## Автор
[@BimBoBam](https://github.com/BimBoBam)
