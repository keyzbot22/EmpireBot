from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "EmpireBot is running!"}

@app.get("/health")
def health():
    return {"status": "online", "success": True}

