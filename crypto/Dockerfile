FROM python:3.11-slim

WORKDIR /usr/src/crypto


RUN apt-get update && apt-get install -y netcat-openbsd

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i 's/\r$//g' /usr/src/crypto/entrypoint.prod.sh
RUN chmod +x /usr/src/crypto/entrypoint.prod.sh

ENTRYPOINT [ "./entrypoint.prod.sh" ]