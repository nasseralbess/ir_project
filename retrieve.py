import os
import json
import pickle
from enum import Enum
from collections import defaultdict
from typing import List, Dict, Any, Tuple

from fastapi.middleware.cors import CORSMiddleware
from bm25s import stopwords as original_stopwords
from scipy.sparse import load_npz
from usearch.index import Index
from pydantic import BaseModel
from dotenv import load_dotenv
from tqdm import tqdm
import pandas as pd
import numpy as np
import requests
import Stemmer
import fastapi
import bm25s

from query_helpers import parse_query, suggest_spelling, expand_abbreviations, expand_query_with_synonyms, llm_query_expansion

load_dotenv()

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModelType(str, Enum):
    VECTOR_SPACE = "tfidf"
    LANGUAGE_MODEL = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"

class SearchRequest(BaseModel):
    query: str
    k: int = 3
    model: ModelType
    

@app.post("/search")
def search(request: SearchRequest) -> Dict[str, Any]:
    query = request.query
    parsed_query, is_phrase = parse_query(query)
    original_phrase = parsed_query
    spelling_suggestions = ""

    if not is_phrase:
        processed_query = expand_query_with_synonyms(parsed_query)
        processed_query = expand_abbreviations(parsed_query)
        spelling_suggestions = suggest_spelling(processed_query)
        if spelling_suggestions==processed_query:
            spelling_suggestions=""

        try:
            processed = llm_query_expansion(processed_query)
            origi = processed_query
            processed_query = json.loads(processed)["combined_search_string"]
            print(f"Processed Query: {processed} from Original: {origi}")
        except Exception as e:
            print(f"LLM expansion failed: {processed} with error {e}")
    else:
        processed_query = original_phrase
        results = retrieve_literal(processed_query, request.k)
        return {"results": results, "spelling_suggestions": spelling_suggestions}
    if request.model == ModelType.BM25:
        results = retrieve_bm25(processed_query, request.k)
    elif request.model == ModelType.LANGUAGE_MODEL:
        results = retrieve_semantic(processed_query, semantic_index, request.k)
    elif request.model == ModelType.VECTOR_SPACE:
        results = retrieve_tfidf(processed_query, request.k)
    elif request.model == ModelType.HYBRID:
        results = rrf(processed_query, request.k)
    else:
        raise fastapi.HTTPException(status_code=400, detail="Invalid model type")
    # print(results)
    return {"results": results, "spelling_suggestions": spelling_suggestions}

@app.get("/document/{doc_id}")
def get_document(doc_id: int) -> Dict[str, Any]:
    if doc_id < 0:
        raise fastapi.HTTPException(status_code=404, detail="Document not found")
    
    row = data[data.index == doc_id].iloc[0]
    return {
        "id": doc_id,
        "topic": row["topic"],
        "title": row["title"], 
        "content": row["content"],
        "url": row["url"]
    }



stemmer = Stemmer.Stemmer('english')
data = pd.read_csv("wiki_dataset.csv")
data.drop_duplicates(subset=["content"], inplace=True)
id_map = {k:v for k,v in zip(range(100),data.index)}
stopwords = tuple(original_stopwords.STOPWORDS_EN) 
JINA_API_KEY = os.getenv("JINA_API_KEY")
documents = list(data["content"])
tfidf_vectors = load_npz("tfidf_vectors.npz")

bm25 = bm25s.BM25.load("bm25_index_content", load_corpus=True)
with open("tfidf.pk","rb") as v:
    tfidf = pickle.load(v)
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
reverse_documents = {document:i for i,document in zip(list(data.index),documents)}

def aggregate_semantic_results(matches, alpha=0.8):
    similarities = 1 / (1 + matches.distances)
    chunk_ids = matches.keys
    doc_scores = defaultdict(list)
    
    for doc_id, score in zip(chunk_ids, similarities):
        doc_scores[doc_id].append(score)

    final_ranking = []
    
    for doc_id, scores in doc_scores.items():
        scores = np.array(scores)
        
        max_score = np.max(scores)
        sum_score = np.sum(scores)
        final_score = (alpha * max_score) + ((1 - alpha) * sum_score)
        final_ranking.append((doc_id, final_score))
        
    final_ranking.sort(key=lambda x: x[1], reverse=True)
    return final_ranking

def retrieve_literal(query, k=3):
    mask = data["content"].str.contains(query, case=False, regex=False)
    matches = data[mask]
    return matches.index.tolist()[:k]

def retrieve_bm25(query, k=3):
    query_tokens = bm25s.tokenize(query, stemmer=stemmer, stopwords=stopwords, show_progress=False)
    results, scores = bm25.retrieve(query_tokens, corpus=[d for d in documents], k=k, show_progress=False,return_as="tuple")
    scores = scores.squeeze().tolist()
    results = results.squeeze().tolist()
    doc_ids = [reverse_documents[doc] for score, doc in zip(scores,results) if score > 0]
    return doc_ids

def retrieve_semantic(query, index, k=3):
    # print(k)
    query_embedding = np.array(embed(query))
    matches = index.search(query_embedding, k) 
    agg = aggregate_semantic_results(matches)
    # print(agg)
    ids = [int(doc_id) for doc_id, score in agg if score > .77]
    print(agg)
    return ids[:k//2]

def retrieve_tfidf(query, k=3):
    query_vec = tfidf.transform([query])
    scores = (tfidf_vectors @ query_vec.T).toarray().ravel()
    sorted_idx = np.argsort(scores)[::-1]
    top_k = [i for i in sorted_idx if scores[i] > 0][:k]    
    return [id_map[i] for i in top_k]#, scores[top_k].tolist()

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