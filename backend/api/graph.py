from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.arxiv_ingest import es, INDEX_NAME
from app.services.openalex import resolve_work, get_citing_works, get_referenced_works

router = APIRouter()


def _node_from_source(src: dict) -> dict:
    pid = str(src.get('id') or src.get('paper_id') or src.get('doi') or src.get('title'))
    return {
        'id': pid,
        'title': src.get('title') or src.get('name') or pid,
        'authors': src.get('authors') or [],
        'year': src.get('year') or src.get('published') or None,
        'url': src.get('url') or src.get('pdf_url') or None
    }


@router.get('/citations')
async def get_citations(paper_id: str = Query(..., description='Paper ID to find citations for'), limit: int = 50):
    """Return a simple citation graph: nodes and edges where edges point from citing -> cited."""
    try:
        # try to fetch target paper from ES
        try:
            tgt = es.get(index=INDEX_NAME, id=paper_id)
            tgt_src = tgt.get('_source', {})
        except Exception:
            tgt_src = {}

        # find papers that cite this paper via references field if available
        q = {
            'query': {
                'term': {
                    'references': {
                        'value': paper_id
                    }
                }
            },
            'size': limit
        }

        resp = es.search(index=INDEX_NAME, body=q)
        hits = resp.get('hits', {}).get('hits', [])

        # Fallback: if no explicit 'references' field is available in index,
        # try a looser match searching for the title or URL in abstracts/titles.
        if not hits:
            title = (tgt_src.get('title') or '').strip()
            url = (tgt_src.get('url') or '').strip()
            fallback_should = []
            if title:
                # match phrase on title and abstract
                fallback_should.append({'match_phrase': {'title': title}})
                fallback_should.append({'match_phrase': {'abstract': title}})
            if url:
                fallback_should.append({'match': {'abstract': url}})
                fallback_should.append({'match': {'title': url}})
            # if still empty, match on tokens from title
            if title and not fallback_should:
                for tok in title.split()[:8]:
                    if len(tok) > 3:
                        fallback_should.append({'match': {'abstract': tok}})

            if fallback_should:
                fq = {
                    'query': {
                        'bool': {
                            'should': fallback_should,
                            'minimum_should_match': 1
                        }
                    },
                    'size': limit
                }
                resp = es.search(index=INDEX_NAME, body=fq)
                hits = resp.get('hits', {}).get('hits', [])

        nodes = []
        edges = []

        center_node = _node_from_source(tgt_src) if tgt_src else {'id': paper_id, 'title': str(paper_id), 'authors': [], 'year': None}
        nodes.append(center_node)
        seen = {center_node['id']}

        for h in hits:
            src = h.get('_source', {})
            n = _node_from_source(src)
            if n['id'] in seen:
                continue
            seen.add(n['id'])
            nodes.append(n)
            # edge: citing -> cited
            edges.append({'source': n['id'], 'target': center_node['id'], 'relation': 'cites'})

        # If we still have no hits, try augmenting with OpenAlex data (resolve DOI/OpenAlex id)
        if not hits:
            # attempt to resolve the target via OpenAlex using title or url
            oa = None
            # try to resolve by url, DOI or id
            if tgt_src.get('url'):
                oa = resolve_work(tgt_src.get('url'))
            if not oa and tgt_src.get('doi'):
                oa = resolve_work(tgt_src.get('doi'))
            if not oa and tgt_src.get('id'):
                # try id
                oa = resolve_work(tgt_src.get('id'))

            # If we couldn't resolve using the ES source fields, also try resolving
            # the original user-supplied paper_id (it may be a DOI or OpenAlex id).
            if not oa and paper_id:
                oa = resolve_work(paper_id)

            if oa:
                openalex_id = oa.get('id') or oa.get('openalex_id') or oa.get('id')
                # fetch citing works from OpenAlex
                citing = get_citing_works(openalex_id, per_page=limit)
                for c in citing:
                    pid = str(c.get('id') or c.get('doi') or c.get('id') or c.get('display_name'))
                    if pid in seen:
                        continue
                    seen.add(pid)
                    node = {
                        'id': pid,
                        'title': c.get('display_name') or c.get('title') or pid,
                        'authors': [a.get('author', {}).get('display_name') if isinstance(a, dict) else a for a in (c.get('authorships') or [])],
                        'year': c.get('publication_year'),
                        'url': c.get('ids', {}).get('openalex') if isinstance(c.get('ids'), dict) else c.get('id')
                    }
                    nodes.append(node)
                    edges.append({'source': node['id'], 'target': center_node['id'], 'relation': 'cites'})

        return {'nodes': nodes, 'edges': edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to fetch citations: {str(e)}')


@router.get('/similar')
async def get_similar(paper_id: str = Query(..., description='Paper ID to find similar papers for'), limit: int = 50):
    """Return papers similar by shared authors or keywords.

    This is a best-effort endpoint using term queries on `authors` and `keywords` fields.
    """
    try:
        try:
            tgt = es.get(index=INDEX_NAME, id=paper_id)
            tgt_src = tgt.get('_source', {})
        except Exception:
            tgt_src = {}

        authors = tgt_src.get('authors') or []
        keywords = tgt_src.get('keywords') or []

        should = []
        for a in (authors or [])[:5]:
            should.append({'match': {'authors': a}})
        for k in (keywords or [])[:8]:
            should.append({'match': {'keywords': k}})

        q = {
            'query': {
                'bool': {
                    'should': should,
                    'minimum_should_match': 1
                }
            },
            'size': limit
        }

        resp = es.search(index=INDEX_NAME, body=q)
        hits = resp.get('hits', {}).get('hits', [])

        nodes = []
        edges = []

        center_node = _node_from_source(tgt_src) if tgt_src else {'id': paper_id, 'title': str(paper_id), 'authors': [], 'year': None}
        nodes.append(center_node)
        seen = {center_node['id']}

        for h in hits:
            src = h.get('_source', {})
            pid = str(src.get('id') or src.get('paper_id') or src.get('doi') or src.get('title'))
            if pid == center_node['id'] or pid in seen:
                continue
            n = _node_from_source(src)
            seen.add(n['id'])
            nodes.append(n)
            # edge: similar_by -> center
            edges.append({'source': n['id'], 'target': center_node['id'], 'relation': 'similar'})

        return {'nodes': nodes, 'edges': edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to fetch similar papers: {str(e)}')
