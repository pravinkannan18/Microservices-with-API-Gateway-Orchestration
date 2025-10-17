import os
import json
import re
import math
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Retriever Service")

DATASET_PATH = Path(__file__).parent / "dataset.json"
if DATASET_PATH.exists():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        DATA = json.load(f)
else:
    DATA = []

class RetrieveRequest(BaseModel):
    request_id: str
    query: str

def tokenize(text: str) -> list:
    """Tokenize text into lowercase words."""
    return re.findall(r"\w+", text.lower())

def compute_tf(tokens: list) -> dict:
    """Compute term frequency."""
    tf = {}
    total = len(tokens)
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    # Normalize by total tokens
    return {k: v / total for k, v in tf.items()}

def compute_idf(documents: list) -> dict:
    """Compute inverse document frequency across all documents."""
    idf = {}
    total_docs = len(documents)
    # Count documents containing each term
    for doc in documents:
        tokens = set(tokenize(doc.get("text", "")))
        for token in tokens:
            idf[token] = idf.get(token, 0) + 1
    # Compute IDF: log(total_docs / (1 + doc_count))
    return {k: math.log(total_docs / (1 + v)) for k, v in idf.items()}

def cosine_similarity(vec1: dict, vec2: dict) -> float:
    """Compute cosine similarity between two TF-IDF vectors."""
    # Get common terms
    common_terms = set(vec1.keys()) & set(vec2.keys())
    if not common_terms:
        return 0.0
    
    # Dot product
    dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
    
    # Magnitudes
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)

def score(doc_text: str, query: str, idf: dict) -> float:
    """Compute TF-IDF cosine similarity score between document and query."""
    doc_tokens = tokenize(doc_text)
    query_tokens = tokenize(query)
    
    if not doc_tokens or not query_tokens:
        return 0.0
    
    # Compute TF for doc and query
    doc_tf = compute_tf(doc_tokens)
    query_tf = compute_tf(query_tokens)
    
    # Compute TF-IDF vectors
    doc_tfidf = {term: tf * idf.get(term, 0) for term, tf in doc_tf.items()}
    query_tfidf = {term: tf * idf.get(term, 0) for term, tf in query_tf.items()}
    
    return cosine_similarity(doc_tfidf, query_tfidf)

@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    if not DATA:
        raise HTTPException(status_code=500, detail="Dataset empty")

    # Compute IDF across all documents once
    idf = compute_idf(DATA)

    ranked = sorted(
        (
            {
                "id": idx,
                "text": d.get("text", ""),
                "score": score(d.get("text", ""), req.query, idf)
            }
            for idx, d in enumerate(DATA)
        ),
        key=lambda x: x["score"],
        reverse=True
    )
    # Return top 3 with score > 0
    top3 = [r for r in ranked[:3] if r["score"] > 0]

    # If no matches, return top 3 anyway with their scores
    if not top3:
        top3 = ranked[:3]

    # JSONL logging for traceable request flows (include full document info)
    log_entry = {
        "service": "retriever",
        "request_id": req.request_id,
        "query": req.query,
        "result_count": len(top3),
        "documents": [
            {
                "id": d["id"],
                "score": d["score"],
                "text": d["text"]
            } for d in top3
        ]
    }
    try:
        log_path = Path(__file__).parent.parent / "logs" / "audit.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        pass  # Don't fail request if logging fails

    return {"service": "retriever", "request_id": req.request_id, "query": req.query, "documents": top3}

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "retriever")}
