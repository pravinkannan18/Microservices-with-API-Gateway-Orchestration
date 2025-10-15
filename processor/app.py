import os
import re
import hashlib
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Processor Service")

@app.get("/")
@app.get("/docs")
async def welcome():
    return {"message": "Welcome to the Processor Service!"}

class ProcessRequest(BaseModel):
    request_id: str
    query: str
    documents: list

def summarize(docs, max_sentences=2):
    joined = " ".join(d.get("text", "") for d in docs)
    sentences = re.split(r"(?<=[.!?])\s+", joined)
    return " ".join(sentences[:max_sentences]).strip()

def label(docs):
    text = " ".join(d.get("text", "") for d in docs).lower()
    if "policy" in text:
        return "policy"
    if "gateway" in text or "kong" in text:
        return "infrastructure"
    if "microservice" in text:
        return "architecture"
    return "general"

from fastapi import HTTPException

@app.post("/process")
async def process(req: ProcessRequest):
    # Validate input
    if not isinstance(req.documents, list) or not req.documents:
        raise HTTPException(status_code=400, detail="'documents' must be a non-empty list")
    for doc in req.documents:
        if not isinstance(doc, dict) or "text" not in doc:
            raise HTTPException(status_code=400, detail="Each document must be a dict with a 'text' field")
    try:
        summary = summarize(req.documents)
        lbl = label(req.documents)
        digest = hashlib.sha1(summary.encode()).hexdigest()[:8]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    return {
        "service": "processor",
        "request_id": req.request_id,
        "summary": summary,
        "label": lbl,
        "digest": digest
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "processor")}
