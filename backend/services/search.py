from typing import List, Dict, Any, Optional
import numpy as np
from elasticsearch import Elasticsearch
import faiss
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.models.paper import Paper

class SearchService:
    """Service for hybrid search functionality combining BM25 and vector search"""
    
    def __init__(self):
        # Initialize Elasticsearch client with HTTPS and authentication
        self.es = Elasticsearch(
            hosts=[{
                'host': settings.ELASTICSEARCH_HOST,
                'port': settings.ELASTICSEARCH_PORT,
                'scheme': 'https'
            }],
            basic_auth=("elastic", "BnKf5CZd4MIVY=Cg-MQ0"),  # <-- Replace <your-password> with your actual password
            verify_certs=False  # For local dev, disables SSL verification
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Initialize FAISS index
        self.dimension = settings.VECTOR_DIMENSION
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product similarity
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for text"""
        return self.embedding_model.encode(text)
    
    def keyword_search(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                      size: int = 20) -> List[Dict[str, Any]]:
        """Perform keyword-based search using Elasticsearch BM25"""
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "abstract^2", "keywords"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "size": size
        }
        
        # Add filters if provided
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    search_query["query"]["bool"]["filter"] = [
                        {"terms": {field: value}}
                    ]
                else:
                    search_query["query"]["bool"]["filter"] = [
                        {"term": {field: value}}
                    ]
        
        response = self.es.search(
            index=settings.ELASTICSEARCH_INDEX_PAPERS,
            body=search_query
        )
        
        return [hit["_source"] for hit in response["hits"]["hits"]]
    
    def vector_search(self, query: str, size: int = 20) -> List[Dict[str, Any]]:
        """Perform vector-based semantic search using FAISS"""
        # Get query embedding
        query_vector = self.get_embedding(query)
        
        # Search in FAISS index
        distances, indices = self.index.search(np.array([query_vector]), size)
        
        # Get paper IDs from indices
        paper_ids = [int(idx) for idx in indices[0] if idx >= 0]
        
        # Get papers from database
        # This is a placeholder - in a real implementation, you would fetch papers from DB
        papers = []  # Replace with actual DB query
        
        return papers
    
    def hybrid_search(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                     size: int = 20, alpha: float = 0.5) -> List[Dict[str, Any]]:
        """Perform hybrid search combining BM25 and vector search results"""
        # Get keyword search results
        keyword_results = self.keyword_search(query, filters, size=size)
        
        # Get vector search results
        vector_results = self.vector_search(query, size=size)
        
        # Combine results with a simple rank fusion
        # In a real implementation, you would use a more sophisticated approach
        combined_results = {}
        
        # Add keyword results with weight (1-alpha)
        for i, result in enumerate(keyword_results):
            paper_id = result.get("id")
            if paper_id:
                combined_results[paper_id] = {
                    "paper": result,
                    "score": (1 - alpha) * (1.0 / (i + 1))  # Reciprocal rank
                }
        
        # Add vector results with weight alpha
        for i, result in enumerate(vector_results):
            paper_id = result.get("id")
            if paper_id:
                if paper_id in combined_results:
                    combined_results[paper_id]["score"] += alpha * (1.0 / (i + 1))
                else:
                    combined_results[paper_id] = {
                        "paper": result,
                        "score": alpha * (1.0 / (i + 1))
                    }
        
        # Sort by score and return papers
        sorted_results = sorted(
            combined_results.values(), 
            key=lambda x: x["score"], 
            reverse=True
        )
        
        return [item["paper"] for item in sorted_results[:size]]
    
    def rerank_results(self, query: str, results: List[Dict[str, Any]], 
                      size: int = 10) -> List[Dict[str, Any]]:
        """Rerank search results using a more sophisticated model"""
        # This is a placeholder for a reranking model
        # In a real implementation, you would use a model like BERT or T5
        
        # For now, just return the top results
        return results[:size]