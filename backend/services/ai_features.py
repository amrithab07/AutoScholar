from typing import List, Dict, Any, Optional
import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForQuestionAnswering,
    pipeline
)
from sentence_transformers import SentenceTransformer

from app.core.config import settings

class AIFeatureService:
    """Service for AI-powered features like summarization and question-answering"""
    
    def __init__(self):
        # Initialize summarization model
        self.summarization_tokenizer = AutoTokenizer.from_pretrained(settings.SUMMARIZATION_MODEL)
        self.summarization_model = AutoModelForSeq2SeqLM.from_pretrained(settings.SUMMARIZATION_MODEL)
        self.summarizer = pipeline("summarization", model=self.summarization_model, tokenizer=self.summarization_tokenizer)
        
        # Initialize QA model
        self.qa_tokenizer = AutoTokenizer.from_pretrained(settings.QA_MODEL)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(settings.QA_MODEL)
        self.qa_pipeline = pipeline("question-answering", model=self.qa_model, tokenizer=self.qa_tokenizer)

        # Embedding model (sentence-transformers)
        # Load lazily because it can be large; initialize here for simplicity.
        try:
            self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception as e:
            print(f"Embedding model load failed: {e}")
            self.embedder = None
    
    def generate_summary(self, text: str, max_length: int = 150, min_length: int = 40) -> str:
        """Generate a concise summary of the given text"""
        # Check if text is too short for summarization
        if len(text.split()) < min_length:
            return text
        
        try:
            summary = self.summarizer(
                text, 
                max_length=max_length, 
                min_length=min_length, 
                do_sample=False
            )
            return summary[0]['summary_text']
        except Exception as e:
            print(f"Summarization error: {str(e)}")
            return text[:max_length * 10]  # Fallback to truncation
    
    def answer_question(self, question: str, context: str) -> Dict[str, Any]:
        """Answer a question based on the provided context"""
        try:
            result = self.qa_pipeline(
                question=question,
                context=context
            )
            return {
                "answer": result["answer"],
                "score": float(result["score"]),
                "start": result["start"],
                "end": result["end"]
            }
        except Exception as e:
            print(f"Question answering error: {str(e)}")
            return {
                "answer": "Unable to answer this question.",
                "score": 0.0,
                "start": 0,
                "end": 0
            }
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract key terms and phrases from text"""
        # This is a placeholder - in a real implementation, you would use
        # a keyword extraction model or algorithm like RAKE, YAKE, or KeyBERT
        
        # Simple frequency-based extraction for demonstration
        words = text.lower().split()
        word_freq = {}
        
        for word in words:
            if len(word) > 3:  # Filter out short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top N keywords
        return [word for word, _ in sorted_words[:top_n]]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return embedding vectors for a list of texts using sentence-transformers."""
        if not texts:
            return []
        if self.embedder is None:
            # Attempt to lazy-load if not present
            try:
                self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"Failed to load embedder: {e}")
                return [[0.0] * settings.VECTOR_DIMENSION for _ in texts]

        embs = self.embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        # Ensure list of lists
        return [list(map(float, e)) for e in embs]

    @staticmethod
    def cosine_sim(a: List[float], b: List[float]) -> float:
        a_np = np.array(a, dtype=float)
        b_np = np.array(b, dtype=float)
        if a_np.size == 0 or b_np.size == 0:
            return 0.0
        denom = (np.linalg.norm(a_np) * np.linalg.norm(b_np))
        if denom == 0:
            return 0.0
        return float(np.dot(a_np, b_np) / denom)
    
    def auto_tag_paper(self, title: str, abstract: str) -> List[str]:
        """Automatically generate tags for a paper based on title and abstract"""
        # Combine title and abstract for processing
        full_text = f"{title}. {abstract}"
        
        # Extract keywords
        keywords = self.extract_keywords(full_text, top_n=5)
        
        return keywords


# Lazy singleton for AIFeatureService to avoid reloading models on every import
_ai_service_instance: Optional[AIFeatureService] = None

def get_ai_service() -> AIFeatureService:
    """Return a singleton AIFeatureService instance (lazy-initialized)."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIFeatureService()
    return _ai_service_instance