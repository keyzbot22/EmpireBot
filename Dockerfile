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

# Expose FastAPI port (optional)
EXPOSE 8000

# Run the main bot (adjust as needed)
CMD ["python", "zariah_pro.py"]
