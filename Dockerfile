# Use official Python base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir \
    python-telegram-bot==20.3 \
    fastapi \
    uvicorn==0.23.2 \
    requests==2.31.0 \
    google-auth \
    google-api-python-client \
    notion-client \
    apscheduler==3.10.1 \
    gspread \
    prometheus-client \
    nest_asyncio \
    httpx \
    python-dotenv \
    schedule \
    pydantic \
    openpyxl \
    fpdf \
    flask==2.3.2 \
    metaapi-cloud-sdk==9.0.1

# Expose FastAPI port
EXPOSE 8000

# ✅ Run the FastAPI webhook app
CMD ["uvicorn", "webhook_bot:app", "--host", "0.0.0.0", "--port", "8000"]


