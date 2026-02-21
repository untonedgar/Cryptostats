#!/bin/sh

# Проверяем, что база данных должна быть инициализирована
if [ "$POSTGRES_DB" = "wb" ]
then
    echo "Ждем запуска PostgreSQL..."

    # Ожидаем доступности порта базы данных
    while ! nc -z "db" $POSTGRES_PORT; do
      echo "Порт базы данных недоступен, ждем..."
      sleep 2
    done

    echo "Порт базы данных доступен, проверяем готовность PostgreSQL..."



    echo "PostgreSQL запущен и готов к работе."
fi
python manage.py compilemessages
# Выполняем миграции
echo "Выполнение миграций..."
python manage.py makemigrations
if [ $? -ne 0 ]; then
  echo "Ошибка при выполнении makemigrations"
  exit 1
fi

python manage.py migrate
if [ $? -ne 0 ]; then
  echo "Ошибка при выполнении migrate"
  exit 1
fi


python manage.py search_index --create
python manage.py search_index --populate -f
# Собираем статические файлы
echo "Сборка статических файлов..."
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
  echo "Ошибка при сборе статических файлов"
  exit 1
fi

exec "$@"
