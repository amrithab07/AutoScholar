from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.services.ai_features import get_ai_service
from app.services.openalex import resolve_work, get_referenced_works
from typing import Optional

# Elasticsearch client for fetching paper metadata
from app.services.arxiv_ingest import es, INDEX_NAME

router = APIRouter()
ai_service = get_ai_service()

class SummarizationRequest(BaseModel):
    """Request model for summarization"""
    text: str
    max_length: int = 150
    min_length: int = 40

class QuestionAnswerRequest(BaseModel):
    """Request model for question answering"""
    question: str
    context: str

class KeywordExtractionRequest(BaseModel):
    """Request model for keyword extraction"""
    text: str
    top_n: int = 10

@router.post("/summarize")
async def summarize_text(request: SummarizationRequest):
    """
    Generate a concise summary of the provided text
    """
    try:
        summary = ai_service.generate_summary(
            request.text,
            max_length=request.max_length,
            min_length=request.min_length
        )
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(e)}")

@router.post("/answer")
async def answer_question(request: QuestionAnswerRequest):
    """
    Answer a question based on the provided context
    """
    try:
        answer = ai_service.answer_question(request.question, request.context)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question answering error: {str(e)}")

@router.post("/extract-keywords")
async def extract_keywords(request: KeywordExtractionRequest):
    """
    Extract key terms and phrases from text
    """
    try:
        keywords = ai_service.extract_keywords(request.text, top_n=request.top_n)
        return {"keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword extraction error: {str(e)}")

@router.post("/auto-tag")
async def auto_tag_paper(
    title: str = Body(..., embed=True),
    abstract: str = Body(..., embed=True)
):
    """
    Automatically generate tags for a paper based on title and abstract
    """
    try:
        tags = ai_service.auto_tag_paper(title, abstract)
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-tagging error: {str(e)}")


class PaperIdsRequest(BaseModel):
    paper_ids: List[str]
    max_length: Optional[int] = 200
    min_length: Optional[int] = 40


@router.post("/summarize-papers")
async def summarize_papers(request: PaperIdsRequest):
    """Summarize a list of papers by their IDs (uses paper.abstract if available)"""
    summaries = []
    for pid in request.paper_ids:
        try:
            doc = es.get(index=INDEX_NAME, id=pid)
            src = doc.get('_source', {})
        except Exception:
            src = {}

        text = src.get('abstract') or src.get('summary') or src.get('description') or src.get('title') or ''
        summary = ai_service.generate_summary(text, max_length=request.max_length, min_length=request.min_length)
        summaries.append({"paper_id": pid, "summary": summary})

    return {"summaries": summaries}


class CompareRequest(BaseModel):
    paper_ids: List[str]
    prompt: Optional[str] = None
    max_length: Optional[int] = 300
    min_length: Optional[int] = 50
    compare_mode: Optional[str] = "full"  # options: methods, results, datasets, novelty, full


@router.post("/compare-papers")
async def compare_papers(request: CompareRequest):
    """Compare two or more papers and produce a concise comparison summary."""
    papers = []
    # Gather paper metadata from ES; if missing, try resolving via OpenAlex
    for pid in request.paper_ids:
        oa_work = None
        try:
            doc = es.get(index=INDEX_NAME, id=pid)
            src = doc.get('_source', {})
        except Exception:
            src = {}
        # If no ES source found, try OpenAlex resolution (arXiv/DOI/OpenAlex id)
        if not src:
            oa_work = resolve_work(pid)
            if oa_work:
                # Map OpenAlex fields to our expected source shape
                src = {
                    'title': oa_work.get('display_name') or oa_work.get('title'),
                    'abstract': oa_work.get('abstract') or oa_work.get('abstract_inverted_index') and ' '.join(oa_work.get('abstract_inverted_index', {}).keys()) or '',
                    'references': oa_work.get('referenced_works') or []
                }

        papers.append({
            "id": pid,
            "title": src.get('title'),
            "abstract": src.get('abstract') or src.get('summary') or src.get('description') or '' ,
            "_oa": oa_work
        })

    # Build a compare prompt combining titles and abstracts
    compare_text_parts = []
    for i, p in enumerate(papers, start=1):
        compare_text_parts.append(f"Paper {i}: {p.get('title','(no title)')}\nAbstract: {p.get('abstract','(no abstract)')}\n")

    # Mode-specific prompt additions
    mode_prompts = {
        "methods": "Compare the methodologies used in these papers.",
        "results": "Compare the key findings and accuracy metrics.",
        "datasets": "Focus on the datasets and experimental setup.",
        "novelty": "Identify what is novel in each paper compared to the others.",
        "full": "Please summarize the main differences and similarities between these papers, focusing on methods, data, results, and conclusions."
    }

    if request.prompt:
        compare_text_parts.append(f"Comparison prompt: {request.prompt}\n")
    else:
        compare_text_parts.append(mode_prompts.get(request.compare_mode or "full", mode_prompts["full"]))

    # Prepare semantic embeddings and overlap metrics
    texts_for_embedding = [f"{p.get('title','')}\n{p.get('abstract','')}" for p in papers]
    embeddings = ai_service.embed_texts(texts_for_embedding)

    # compute pairwise embedding similarities
    n = len(papers)
    embedding_sim_matrix = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                embedding_sim_matrix[i][j] = 1.0
            else:
                embedding_sim_matrix[i][j] = ai_service.cosine_sim(embeddings[i], embeddings[j])

    # citation and keyword overlap metrics
    # Extract references and keywords
    refs = []
    kw_sets = []
    for p in papers:
        # Prefer ES stored references; if absent, fall back to OpenAlex referenced_works
        try:
            doc = es.get(index=INDEX_NAME, id=p.get('id'))
            src = doc.get('_source', {})
        except Exception:
            src = {}
        r = src.get('references') or src.get('reference_ids') or []
        if (not r or len(r) == 0) and p.get('_oa'):
            # OpenAlex returns referenced_works as a list of ids
            oa_refs = p.get('_oa').get('referenced_works') or []
            r = oa_refs
        if isinstance(r, str):
            # sometimes stored as a comma-separated string
            r = [x.strip() for x in r.split(',') if x.strip()]
        refs.append(set([str(x) for x in (r or [])]))

        kws = ai_service.extract_keywords(p.get('abstract','') or p.get('title',''), top_n=20)
        kw_sets.append(set(kws))

    # pairwise citation overlap (normalized by min reference size)
    citation_overlap = [[0.0]*n for _ in range(n)]
    keyword_overlap = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                citation_overlap[i][j] = 1.0
                keyword_overlap[i][j] = 1.0
                continue
            a_refs = refs[i]
            b_refs = refs[j]
            if a_refs and b_refs:
                inter = a_refs.intersection(b_refs)
                denom = min(len(a_refs), len(b_refs))
                citation_overlap[i][j] = len(inter)/denom if denom > 0 else 0.0
            else:
                citation_overlap[i][j] = 0.0

            a_kw = kw_sets[i]
            b_kw = kw_sets[j]
            if a_kw or b_kw:
                interkw = a_kw.intersection(b_kw)
                unionkw = a_kw.union(b_kw)
                keyword_overlap[i][j] = len(interkw)/len(unionkw) if unionkw else 0.0
            else:
                keyword_overlap[i][j] = 0.0

    # Build an evidence-backed comparison graph
    # Nodes are the input papers; edges indicate shared/derivative ideas backed by citations
    def _resolve_ref_meta(ref_id: str) -> Dict[str, Any]:
        """Try to fetch metadata for a reference id from ES; fallback to raw id."""
        try:
            rdoc = es.get(index=INDEX_NAME, id=ref_id)
            rsrc = rdoc.get('_source', {})
            title = rsrc.get('title') or rsrc.get('name')
            authors = rsrc.get('authors') or []
            year = rsrc.get('year') or rsrc.get('published')
            return {'id': str(ref_id), 'title': title, 'authors': authors, 'year': year}
        except Exception:
            # Try OpenAlex as a fallback to enrich reference metadata
            try:
                oa = resolve_work(ref_id)
                if oa:
                    title = oa.get('display_name') or oa.get('title')
                    authors = []
                    for a in (oa.get('authorships') or []):
                        # authorship entries may be dicts
                        if isinstance(a, dict):
                            auth = a.get('author') or a.get('display_name')
                            if isinstance(auth, dict):
                                authors.append(auth.get('display_name') or auth.get('name'))
                            else:
                                authors.append(str(auth))
                        else:
                            authors.append(str(a))
                    year = oa.get('publication_year')
                    return {'id': oa.get('id') or str(ref_id), 'title': title, 'authors': authors, 'year': year}
            except Exception:
                pass
            # best-effort: return id only
            return {'id': str(ref_id), 'title': str(ref_id), 'authors': [], 'year': None}

    evidence_nodes = []
    for p in papers:
        evidence_nodes.append({'id': p.get('id'), 'title': p.get('title'), 'authors': [], 'year': None})

    evidence_edges = []
    # For each pair of papers, if they share references, add an edge with evidence
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a_refs = refs[i]
            b_refs = refs[j]
            shared = a_refs.intersection(b_refs) if a_refs and b_refs else set()
            if shared:
                evidence_list = []
                for rid in list(shared)[:10]:
                    meta = _resolve_ref_meta(rid)
                    # Build a short human-friendly citation label
                    label = None
                    try:
                        if meta.get('authors'):
                            first = meta['authors'][0]
                            if isinstance(first, dict):
                                name = first.get('name') or first.get('display_name')
                            else:
                                name = str(first)
                            # last name heuristics
                            lname = name.split()[-1] if name else name
                            if meta.get('year'):
                                label = f"{lname} et al., {meta.get('year')}"
                            else:
                                label = f"{lname} et al."
                        else:
                            label = meta.get('title') or meta.get('id')
                    except Exception:
                        label = meta.get('title') or meta.get('id')

                    evidence_list.append({'ref_id': meta.get('id'), 'label': label, 'meta': meta})

                evidence_edges.append({
                    'source': papers[i].get('id'),
                    'target': papers[j].get('id'),
                    'relation': 'shared_reference',
                    'evidence': evidence_list
                })

            # direct citation: if paper i references paper j by id
            if papers[j].get('id') in a_refs:
                evidence_edges.append({
                    'source': papers[i].get('id'),
                    'target': papers[j].get('id'),
                    'relation': 'cites',
                    'evidence': []
                })

    # Ensure we always return at least a non-empty evidence graph.
    # If no citation/shared-reference edges were found, synthesize semantic edges
    # using embedding similarity and keyword overlap so the frontend can always
    # display an evidence graph for any comparison.
    if not evidence_edges:
        for i in range(n):
            for j in range(i + 1, n):
                score = embedding_sim_matrix[i][j] if i < len(embedding_sim_matrix) and j < len(embedding_sim_matrix[i]) else 0.0
                shared_kw = list(kw_sets[i].intersection(kw_sets[j])) if i < len(kw_sets) and j < len(kw_sets) else []
                evidence_item = {
                    'ref_id': f'semantic:{i}-{j}',
                    'label': f'Semantic similarity {score:.3f}',
                    'meta': {'similarity': score, 'shared_keywords': shared_kw}
                }
                # Create a bi-directional semantic_similarity edge pair for clarity
                evidence_edges.append({
                    'source': papers[i].get('id'),
                    'target': papers[j].get('id'),
                    'relation': 'semantic_similarity',
                    'evidence': [evidence_item]
                })
                evidence_edges.append({
                    'source': papers[j].get('id'),
                    'target': papers[i].get('id'),
                    'relation': 'semantic_similarity',
                    'evidence': [evidence_item]
                })

    compare_text = "\n---\n".join(compare_text_parts)

    # Generate per-paper summaries and an overall comparison using the summarization model
    per_paper_summaries = []
    for p in papers:
        s = ai_service.generate_summary(p.get('abstract',''), max_length=150, min_length=40)
        per_paper_summaries.append({"paper_id": p.get('id'), "summary": s})

    comparison = ai_service.generate_summary(compare_text, max_length=request.max_length, min_length=request.min_length)

    metrics = {
        "embedding_similarity": embedding_sim_matrix,
        "citation_overlap": citation_overlap,
        "keyword_overlap": keyword_overlap
    }

    evidence_graph = {
        'nodes': evidence_nodes,
        'edges': evidence_edges
    }

    # Map comparative points (sentences) to supporting papers + example references.
    # This produces a lightweight "evidence mapping" rather than a full citation graph.
    def _split_sentences(text: str):
        if not text:
            return []
        import re
        parts = re.split(r"\n|\r|(?<=[\.\?\!])\s+", text)
        parts = [p.strip() for p in parts if p and len(p.strip()) > 20]
        return parts

    comparison_points = []
    sentences = _split_sentences(comparison)
    # embed sentences and reuse paper embeddings
    sent_embs = ai_service.embed_texts(sentences) if sentences else []

    support_threshold = 0.45
    for si, sent in enumerate(sentences):
        supports = []
        se = sent_embs[si] if si < len(sent_embs) else None
        for pi in range(len(papers)):
            score = 0.0
            if se is not None and embeddings and pi < len(embeddings):
                try:
                    score = ai_service.cosine_sim(se, embeddings[pi])
                except Exception:
                    score = 0.0

            if score >= support_threshold:
                # collect example refs for this paper (up to 3)
                example_refs = []
                try:
                    ref_ids = list(refs[pi])[:3]
                except Exception:
                    ref_ids = []
                for rid in ref_ids:
                    meta = _resolve_ref_meta(rid)
                    example_refs.append({'ref_id': meta.get('id'), 'label': (meta.get('title') or meta.get('id')), 'meta': meta})

                supports.append({'paper_id': papers[pi].get('id'), 'score': float(score), 'example_refs': example_refs})

        comparison_points.append({'text': sent, 'supports': supports})

    return {"papers": per_paper_summaries, "comparison": comparison, "metrics": metrics, "evidence_graph": evidence_graph, "comparison_points": comparison_points}