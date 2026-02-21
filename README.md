Всем добрый день. Это демо-версия приложения,  
позволяющего объединять все места хранения криптовалют  
для отображения общего баланса и получения общей статистики.  
  
В настоящее время 40% процентов реализации проекта.   
  <img width="1902" height="911" alt="Снимок экрана 2026-02-02 121856" src="https://github.com/user-attachments/assets/475bd272-418e-4f0f-ae90-51ee699f2197" />  
  <img width="1901" height="912" alt="Снимок экрана 2026-02-02 121913" src="https://github.com/user-attachments/assets/0ec79cbc-a8ab-494a-8903-85c9453b9acc" />  
  <img width="1901" height="912" alt="Снимок экрана 2026-02-02 121928" src="https://github.com/user-attachments/assets/77f14082-43e0-4ab3-a3bc-d54f26b70b60" />  
  <img width="1902" height="911" alt="Снимок экрана 2026-02-02 121942" src="https://github.com/user-attachments/assets/2df70fbf-81f0-4b19-870f-efa13ed2a1c0" />  
  <img width="1900" height="909" alt="Снимок экрана 2026-02-02 121955" src="https://github.com/user-attachments/assets/fbef8ca7-0364-435b-ba6a-457cfe0eb397" />  
  <img width="1902" height="911" alt="Снимок экрана 2026-02-02 122139" src="https://github.com/user-attachments/assets/7ae23c18-d62a-4f17-ab3c-2d3f7f03bd57" />  
  <img width="1899" height="911" alt="Снимок экрана 2026-02-02 122208" src="https://github.com/user-attachments/assets/d93fd2cc-dc8d-44ec-844c-50729178b463" />  
  <img width="1889" height="902" alt="Снимок экрана 2026-02-02 122406" src="https://github.com/user-attachments/assets/9a328c3a-fa2f-43e0-9b6a-6aee9d09c1b9" />  
  <img width="1883" height="904" alt="Снимок экрана 2026-02-02 122419" src="https://github.com/user-attachments/assets/07f62b77-bfd8-4882-81f4-108e6016bfe6" />  
  <img width="1904" height="912" alt="Снимок экрана 2026-02-02 122629" src="https://github.com/user-attachments/assets/005357f1-4bb3-4d66-8164-0d1a00a0885f" />  
  <img width="1897" height="908" alt="Снимок экрана 2026-02-02 122642" src="https://github.com/user-attachments/assets/bb0ce38a-782c-42f7-aacf-f21323e4d8e2" />  
  <img width="1893" height="906" alt="Снимок экрана 2026-02-02 122914" src="https://github.com/user-attachments/assets/27ba5979-5c42-4e19-b78f-e55ae13c95b1" />    
  
В плане: 
1. Деплой (готово)  
2. Статистика (в процессе)  
3. Качество кода (в процессе)  
4. Оптимизация (готово)    
5. Добавление бирж и сетей (в процессе)  
6. Улучшение безопасности (в процессе)  
7. Чат-поддержка (в процессе)  
8. Валидация вводимых данных (в процессе)  
9. Переодические задачи  (готово)  
10. Иное (в процессе)    

Инструкция по запуску приложения:  
  
1.git clone https://github.com/untonedgar/cryptostats.git  
  
2.создайте файл .env.dev в директории app  
SECRET_KEY='секретный ключ Django'  
ALLOWED_HOSTS=localhost 127.0.0.1  
CSRF_TRUSTED_ORIGINS=http://localhost:8001  
  
POSTGRES_USER=django  
POSTGRES_PASSWORD=password  
POSTGRES_DB=cryptostats    
POSTGRES_PORT=5432  
  
CELERY_BROKER_URL=redis://redis:6379/0  
CELERY_RESULT_BACKEND=redis://redis:6379/1  
REDIS_URL=redis://redis:6379/2    
    
MORALIS_API_KEY = "необходимо получить api-ключ от данного сервиса"  
X_CMC_PRO_API_KEY = "необходимо получить api-ключ от данного сервиса"  
  
3.Запускаем приложение docker compose up  
Переходим по адресу http://localhost:8001/crypto  
  
Чтобы создать админа, необходимо в контейнере app-1 создать  
пользователя admin (python manage.py createsuperuser)      
