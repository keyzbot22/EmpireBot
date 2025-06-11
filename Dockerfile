FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir \
    python-telegram-bot \
    fastapi \
    uvicorn \
    requests \
    google-auth \
    google-api-python-client \
    notion-client \
    apscheduler \
    gspread \
    prometheus-client \
    nest_asyncio \
    httpx

CMD ["sh", "-c", "uvicorn fastapi_ai:app --host 0.0.0.0 --port 8055 & uvicorn webhook_bot:app --host 0.0.0.0 --port 8000"]

