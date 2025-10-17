import os
import re
import hashlib
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Processor Service")

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
    if not isinstance(req.documents, list):
        raise HTTPException(status_code=400, detail="'documents' must be a list")
    
    if not req.documents:
        raise HTTPException(status_code=400, detail="'documents' list cannot be empty")
    
    for idx, doc in enumerate(req.documents):
        if not isinstance(doc, dict):
            raise HTTPException(status_code=400, detail=f"Document at index {idx} must be a dict")
        if "text" not in doc:
            raise HTTPException(status_code=400, detail=f"Document at index {idx} missing 'text' field. Keys: {list(doc.keys())}")
    
    try:
        summary = summarize(req.documents)
        if not summary:
            summary = "No summary available"
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
