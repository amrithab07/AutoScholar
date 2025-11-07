from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.recommendations import RecommendationService

router = APIRouter()
recommendation_service = RecommendationService()

class RecommendationResponse(BaseModel):
    """Model for recommendation response"""
    papers: List[Dict[str, Any]]
    count: int

@router.get("/for-user/{user_id}", response_model=RecommendationResponse)
async def get_recommendations_for_user(
    user_id: int,
    recommendation_type: str = Query("hybrid", description="Type: content, collaborative, or hybrid"),
    limit: int = Query(10, description="Number of recommendations to return")
):
    """
    Get personalized paper recommendations for a user
    """
    try:
        if recommendation_type == "content":
            papers = recommendation_service.get_content_based_recommendations(user_id, limit=limit)
        elif recommendation_type == "collaborative":
            papers = recommendation_service.get_collaborative_recommendations(user_id, limit=limit)
        else:  # hybrid (default)
            papers = recommendation_service.get_hybrid_recommendations(user_id, limit=limit)
        
        # Ensure diversity in recommendations
        diverse_papers = recommendation_service.diversify_recommendations(papers, limit=limit)
        
        return RecommendationResponse(
            papers=diverse_papers,
            count=len(diverse_papers)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

@router.get("/trending", response_model=RecommendationResponse)
async def get_trending_papers(
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(10, description="Number of papers to return")
):
    """
    Get trending papers overall or in a specific topic
    """
    try:
        papers = recommendation_service.get_trending_papers(topic=topic, limit=limit)
        
        return RecommendationResponse(
            papers=papers,
            count=len(papers)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trending papers error: {str(e)}")