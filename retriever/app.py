from fastapi import FastAPI
import os

app = FastAPI(title="Retriever Service")

@app.get("/retriever")
async def retrieve():
    return {"service": "retriever", "data": [1,2,3], "detail": "Sample retrieved data"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "retriever")}
