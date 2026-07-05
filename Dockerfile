FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /entrypoint.sh

USER appuser

EXPOSE 8000

CMD ["/entrypoint.sh"]
