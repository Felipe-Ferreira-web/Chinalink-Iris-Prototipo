FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Roda como uid/gid 1000 (geralmente igual ao do host) para que arquivos
# gerados via bind mount (db.sqlite3, migrations, media/) não fiquem donos de root.
RUN useradd -u 1000 -m app
USER app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
