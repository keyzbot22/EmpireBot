from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "online", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
def root():
    return {"message": "ZariahBot Online"}