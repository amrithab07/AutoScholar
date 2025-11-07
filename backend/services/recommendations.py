from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.services.search import SearchService

class RecommendationService:
    """Service for generating personalized paper recommendations"""
    
    def __init__(self):
        # Initialize search service for embeddings
        self.search_service = SearchService()
    
    def get_content_based_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate content-based recommendations based on user's interests and reading history
        """
        # This is a placeholder - in a real implementation, you would:
        # 1. Get user's interests and reading history from database
        # 2. Generate embeddings for user's profile
        # 3. Find similar papers using vector similarity
        
        # Placeholder for user interests
        user_interests = ["machine learning", "natural language processing"]
        
        # Combine interests into a query
        query = " ".join(user_interests)
        
        # Use search service to find relevant papers
        recommendations = self.search_service.vector_search(query, size=limit)
        
        return recommendations
    
    def get_collaborative_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate collaborative filtering recommendations based on similar users
        """
        # This is a placeholder - in a real implementation, you would:
        # 1. Find similar users based on reading history and interests
        # 2. Get papers that similar users have read but current user hasn't
        # 3. Rank papers by frequency and similarity
        
        # Placeholder for similar users' papers
        similar_users_papers = []  # Replace with actual DB query
        
        return similar_users_papers[:limit]
    
    def get_hybrid_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate hybrid recommendations combining content-based and collaborative filtering
        """
        # Get recommendations from both approaches
        content_recs = self.get_content_based_recommendations(user_id, limit=limit)
        collab_recs = self.get_collaborative_recommendations(user_id, limit=limit)
        
        # Combine and deduplicate
        all_recs = content_recs + collab_recs
        unique_recs = {rec.get("id"): rec for rec in all_recs if rec.get("id")}
        
        # Return top recommendations
        return list(unique_recs.values())[:limit]
    
    def get_trending_papers(self, topic: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending papers overall or in a specific topic
        """
        # This is a placeholder - in a real implementation, you would:
        # 1. Query database for papers with most views/citations in recent period
        # 2. Filter by topic if provided
        
        # Placeholder for trending papers
        trending_papers = []  # Replace with actual DB query
        
        return trending_papers[:limit]
    
    def diversify_recommendations(self, recommendations: List[Dict[str, Any]], 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ensure diversity in recommendations by selecting papers from different topics
        """
        if not recommendations:
            return []
        
        # Group papers by topic
        topic_groups = {}
        for paper in recommendations:
            topics = paper.get("topics", [])
            for topic in topics:
                if topic not in topic_groups:
                    topic_groups[topic] = []
                topic_groups[topic].append(paper)
        
        # Select papers from different topics
        diverse_recs = []
        topics = list(topic_groups.keys())
        
        while len(diverse_recs) < limit and topics:
            for topic in topics[:]:
                if topic_groups[topic]:
                    diverse_recs.append(topic_groups[topic].pop(0))
                    if len(diverse_recs) >= limit:
                        break
                else:
                    topics.remove(topic)
        
        return diverse_recs[:limit]