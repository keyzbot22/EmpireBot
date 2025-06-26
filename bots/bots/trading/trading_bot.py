from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "EmpireBot Trading Online ✅"}

if __name__ == "__main__":
    uvicorn.run("trading_bot:app", host="0.0.0.0", port=10000)

