import bm25s
from bm25s import stopwords as original_stopwords
import pandas as pd
import Stemmer
import requests
import json
from usearch.index import Index
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()
import os
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    k: int = 3

@app.post("/search")
def search(request: SearchRequest) -> Dict[str, List[int]]:
    results = rrf(request.query, request.k)
    return {"results": results}

@app.get("/document/{doc_id}")
def get_document(doc_id: int) -> Dict[str, Any]:
    if doc_id < 0 or doc_id >= len(data):
        raise fastapi.HTTPException(status_code=404, detail="Document not found")
    
    row = data.iloc[doc_id]
    return {
        "id": doc_id,
        "topic": row["topic"],
        "title": row["title"], 
        "content": row["content"],
        "url": row["url"]
    }



stemmer = Stemmer.Stemmer('english')
data = pd.read_csv("wiki_dataset.csv")
stopwords = tuple(original_stopwords.STOPWORDS_EN) 
JINA_API_KEY = os.getenv("JINA_API_KEY")
documents = list(data["content"])

bm25 = bm25s.BM25.load("bm25_index_content", load_corpus=True)
url = 'https://api.jina.ai/v1/embeddings'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {JINA_API_KEY}'
}

def embed(text):
    data = {
        "model": "jina-embeddings-v3",
        "task": "text-matching",
        "dimensions": 1024,
        "late_chunking": False,
        "embedding_type": "float",
        "input": [
            text
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    embedding = response.json()['data'][0]['embedding']
    return embedding

semantic_index = Index(ndim=1024)
semantic_index.load("semantic_full.usearch")
reverse_documents = {document:i for i,document in enumerate(documents)}

def retrieve_bm25(query, k=3):
    query_tokens = bm25s.tokenize(query, stemmer=stemmer, stopwords=stopwords, show_progress=False)
    results, scores = bm25.retrieve(query_tokens, corpus=[d for d in documents], k=k, show_progress=False,return_as="tuple")
    scores = scores.squeeze().tolist()
    results = results.squeeze().tolist()
    doc_ids = [reverse_documents[doc] for doc in results]
    # pairs = [(doc_id, score) for doc_id, score in zip(doc_ids, scores) if score > 0]
    return doc_ids

def retrieve_semantic(query, index=None, k=3):
    query_embedding = np.array(embed(query))
    matches = index.search(query_embedding, k) 
    freqs = {}
    for doc in matches.keys.tolist():
        freqs[doc] = freqs.get(doc, 0) + 1
    
    sorted_docs = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in sorted_docs]

def retrieve_documents(query: str, k: int) -> Dict[str, List[int]]:
    retrieval_functions = {
        'bm25': retrieve_bm25,
        'full_text': lambda q, k: retrieve_semantic(q, semantic_index, k*2),
    }

    return {name: func(query, k) for name, func in retrieval_functions.items()}

def rrf_score(rank: int, k: int) -> float:
    return 1.0 / (k + rank)

def rrf(query: str, k: int = 3) -> List[int]:
    retrieved_docs = retrieve_documents(query, k)
    rrf_scores = defaultdict(float)
    for docs in retrieved_docs.values():
        for rank, doc in enumerate(docs):
            rrf_scores[doc] += rrf_score(rank, k)
    
    ranked_docs: List[Tuple[int, float]] = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    top_k_docs = ranked_docs[:k]

    return [doc for doc, _ in top_k_docs]