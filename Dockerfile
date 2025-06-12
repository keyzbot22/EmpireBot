# Use official Python base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
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
    httpx \
    python-dotenv \
    schedule \
    pydantic \
    openpyxl \
    fpdf

# Expose FastAPI port
EXPOSE 8000

# ✅ Run the FastAPI webhook app
CMD ["uvicorn", "webhook_bot:app", "--host", "0.0.0.0", "--port", "8000"]

