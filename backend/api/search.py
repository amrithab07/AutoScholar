from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.search import SearchService

router = APIRouter()
search_service = SearchService()

class SearchFilters(BaseModel):
    """Model for search filters"""
    authors: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    journals: Optional[List[str]] = None

class SearchResponse(BaseModel):
    """Model for search response"""
    results: List[Dict[str, Any]]
    total: int
    page: int
    size: int

@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    search_type: str = Query("hybrid", description="Search type: keyword, vector, or hybrid"),
    page: int = Query(1, description="Page number"),
    size: int = Query(10, description="Results per page"),
    filters: Optional[SearchFilters] = None
):
    """
    Search for research papers using keyword, vector, or hybrid search
    """
    try:
        # Convert filters to dict if provided
        filter_dict = filters.dict() if filters else None
        
        # Calculate offset
        offset = (page - 1) * size
        
        # Perform search based on type
        if search_type == "keyword":
            results = search_service.keyword_search(q, filter_dict, size=size)
        elif search_type == "vector":
            results = search_service.vector_search(q, size=size)
        else:  # hybrid (default)
            results = search_service.hybrid_search(q, filter_dict, size=size)
        
        # Rerank results for better relevance
        reranked_results = search_service.rerank_results(q, results, size=size)
        
        # Return response
        return SearchResponse(
            results=reranked_results,
            total=len(results),  # In a real implementation, get total from ES
            page=page,
            size=size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., description="Partial query for autocomplete"),
    size: int = Query(5, description="Number of suggestions")
):
    """
    Get autocomplete suggestions for search queries
    """
    # This is a placeholder - in a real implementation, you would use
    # Elasticsearch's completion suggester or similar
    suggestions = [
        f"{q} research",
        f"{q} papers",
        f"{q} methodology",
        f"{q} review",
        f"{q} analysis"
    ]
    
    return {"suggestions": suggestions[:size]}