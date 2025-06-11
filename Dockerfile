# ✅ Start from an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
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
    httpx

# Expose port (optional if running FastAPI app)
EXPOSE 8000

# Command to run app
CMD ["python", "main.py"]

