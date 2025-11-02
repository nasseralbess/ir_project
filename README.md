# WikiSearch - Information Retrieval System

A hybrid information retrieval system for searching Wikipedia articles using both lexical (BM25) and semantic search methods, combined with Reciprocal Rank Fusion (RRF) for optimal results.

## Features

- **Hybrid Search**: Combines BM25 (lexical) and semantic search using Jina embeddings
- **Reciprocal Rank Fusion**: Merges results from multiple retrieval methods for improved relevance
- **FastAPI Backend**: RESTful API for search functionality
- **Web Interface**: Clean, responsive search interface
- **Pre-indexed Data**: Includes Wikipedia dataset with pre-built search indices

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with your Jina API key:
```
JINA_API_KEY=your_jina_api_key_here
```

3. Ensure data files are present:
- `wiki_dataset.csv` - Wikipedia articles dataset
- `bm25_index_content/` - Pre-built BM25 index
- `semantic_full.usearch` - Pre-built semantic index

## Usage

### Start the API Server
```bash
uvicorn retriever:app --reload
```

The API will be available at `http://localhost:8000`

### Web Interface
```bash
python -m http.server 3000
```
The search interface will be available at `http://localhost:3000`

### API Endpoints

- `POST /search` - Search articles
  ```json
  {
    "query": "your search query",
    "k": 3
  }
  ```

- `GET /document/{doc_id}` - Get document by ID

