from typing import List, Dict, Any, Optional
import numpy as np
from math import log2

from sentence_transformers import SentenceTransformer

from app.services.search import SearchService
from app.core.config import settings


class NoveltyService:
    """Compute a lightweight novelty score for a candidate paper.

    This implementation uses a heuristic composed of:
    - semantic similarity to nearby papers (via SearchService + embeddings)
    - citation/reference overlap (if references are provided)
    - lexical entropy of the text
    """

    def __init__(self):
        # Use the same embedding model as search to ensure compatibility
        try:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception:
            # Fallback to a minimal model name if config missing
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Try to initialize search service (may be heavy)
        try:
            self.search = SearchService()
        except Exception:
            self.search = None

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None: return 0.0
        # ensure float
        a = np.array(a, dtype=float)
        b = np.array(b, dtype=float)
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0: return 0.0
        return float(np.dot(a, b) / denom)

    def _entropy_norm(self, text: str) -> float:
        if not text: return 0.0
        toks = [t.lower() for t in text.split() if t.strip()]
        if not toks: return 0.0
        freq = {}
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
        total = len(toks)
        entropy = 0.0
        for v in freq.values():
            p = v / total
            entropy -= p * log2(p)
        # normalize by log2(V) where V is vocabulary size (max entropy)
        V = len(freq)
        if V <= 1: return 0.0
        return float(entropy / log2(V))

    def score_paper(self, title: str, abstract: str, references: Optional[List[str]] = None, top_k: int = 50) -> Dict[str, Any]:
        text = (title or '') + '\n' + (abstract or '')
        # compute embedding
        try:
            emb = self.embedding_model.encode(text)
        except Exception:
            emb = None

        # find candidate papers using search service if available
        candidates = []
        try:
            if self.search:
                q = (title or '') + ' ' + ((abstract or '')[:300])
                candidates = self.search.hybrid_search(q, size=top_k)
        except Exception:
            candidates = []

        # compute similarities using embeddings where possible
        similarities = []
        try:
            for c in candidates:
                c_text = (c.get('title') or '') + '\n' + (c.get('abstract') or '')
                c_emb = None
                try:
                    c_emb = self.embedding_model.encode(c_text)
                except Exception:
                    c_emb = None
                sim = self._cosine(emb, c_emb) if emb is not None and c_emb is not None else 0.0
                similarities.append({'id': str(c.get('id') or c.get('paper_id') or c.get('doi') or c.get('title')), 'title': c.get('title'), 'similarity': sim})
        except Exception:
            similarities = []

        max_similarity = max([s['similarity'] for s in similarities], default=0.0)
        similar_count = sum(1 for s in similarities if s['similarity'] >= 0.7)

        # citation/reference overlap
        overlap_score = 0.0
        max_overlap = 0
        if references and len(references) > 0 and candidates:
            refs_set = set([r.strip().lower() for r in references if r and isinstance(r, str)])
            for c in candidates:
                c_refs = c.get('references') or c.get('citations') or []
                cset = set([str(x).strip().lower() for x in (c_refs or []) if x])
                if not cset:
                    continue
                overlap = len(refs_set & cset)
                if overlap > max_overlap:
                    max_overlap = overlap
            # normalize overlap by number of references (clamp)
            overlap_score = min(1.0, max_overlap / max(1, len(references)))

        # lexical entropy normalized
        entropy_norm = self._entropy_norm(abstract or title or '')

        # combine metrics into a novelty index (higher = more novel)
        novelty = (1.0 - max_similarity) * 0.6 + (1.0 - overlap_score) * 0.2 + entropy_norm * 0.2
        novelty = max(0.0, min(1.0, novelty))

        return {
            'novelty': round(float(novelty), 4),
            'breakdown': {
                'max_similarity': round(float(max_similarity), 4),
                'similar_count': int(similar_count),
                'max_overlap': int(max_overlap),
                'overlap_score': round(float(overlap_score), 4),
                'entropy_norm': round(float(entropy_norm), 4)
            },
            'similar_examples': sorted(similarities, key=lambda x: x['similarity'], reverse=True)[:10]
        }


novelty_service = NoveltyService()
