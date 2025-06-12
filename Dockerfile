FROM python:3.11-slim

# Install required build tools
RUN apt-get update && \
    apt-get install -y gcc build-essential && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "webhook_bot:app", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "webhook_bot:app", "--host", "0.0.0.0", "--port", "8000"]
