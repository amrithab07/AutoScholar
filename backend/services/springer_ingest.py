import os
import math
import httpx
from app.core.config import settings

# Reuse Elasticsearch client and index name from arxiv_ingest for consistency
from app.services.arxiv_ingest import es, INDEX_NAME

SPRINGER_API_URL = "https://api.springernature.com/metadata/json"

def fetch_springer_papers(query="machine learning", max_results=100, page_size=20, api_key=None):
    """
    Fetch metadata from Springer Nature Metadata API.

    Notes:
    - Requires an API key (pass explicitly or set SPRINGER_API_KEY env var).
    - This function pages through results using 'p' (page size) and 's' (start index, 1-based).
    - Returns a list of paper dicts mapped to the project's index schema.
    """
    api_key = api_key or os.getenv('SPRINGER_API_KEY')
    if not api_key:
        raise RuntimeError('SPRINGER_API_KEY is not set in environment')

    client = httpx.Client(timeout=30.0)
    papers = []
    fetched = 0
    start = 1
    page_size = min(page_size, 100)  # API cap

    while fetched < max_results:
        params = {
            'q': query,
            'api_key': api_key,
            'p': page_size,
            's': start
        }
        try:
            r = client.get(SPRINGER_API_URL, params=params)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print('Springer fetch error:', e)
            break

        records = data.get('records') or data.get('result', {}).get('records') or []
        if not records:
            break

        for rec in records:
            if fetched >= max_results:
                break

            # Map common fields. Springer uses various keys; be defensive.
            title = rec.get('title') or (rec.get('titles') and rec['titles'][0]) or ''
            # authors: often in 'creators' or 'creator' or 'authors'
            authors_raw = rec.get('creators') or rec.get('creator') or rec.get('creators') or rec.get('authors') or []
            authors = []
            if isinstance(authors_raw, list):
                for a in authors_raw:
                    if isinstance(a, dict):
                        name = a.get('creator') or a.get('name') or a.get('fullName') or a.get('given') and a.get('family') and f"{a.get('given')} {a.get('family')}" or None
                    else:
                        name = str(a)
                    if name:
                        authors.append({'name': name})
            elif isinstance(authors_raw, str):
                authors = [{'name': x.strip()} for x in authors_raw.split(',') if x.strip()]

            # published date
            pub = rec.get('publicationDate') or rec.get('onlineDate') or rec.get('publication_date') or rec.get('date') or None
            pub_str = None
            if isinstance(pub, str):
                pub_str = pub

            # url(s)
            url = None
            # Springer may return 'url' as list of dicts with 'value'
            if 'url' in rec:
                u = rec['url']
                if isinstance(u, list) and u:
                    first = u[0]
                    if isinstance(first, dict):
                        url = first.get('value') or first.get('url')
                    else:
                        url = str(first)
                elif isinstance(u, str):
                    url = u

            # doi
            doi = rec.get('doi') or rec.get('identifier') or rec.get('ids')

            paper = {
                'id': doi or rec.get('isbn') or rec.get('printIdentifier') or f"springer-{rec.get('id', start)}-{fetched}",
                'title': title,
                'abstract': rec.get('abstract') or rec.get('description') or '',
                'authors': authors,
                'published': pub_str,
                'url': url,
                'doi': doi,
                'keywords': rec.get('keywords') or []
            }

            papers.append(paper)
            fetched += 1

        # Prepare next page
        start += page_size
        # if number of returned records less than page_size, we're done
        if len(records) < page_size:
            break

    client.close()
    return papers


def index_papers_to_elasticsearch(papers):
    if not papers:
        print('No Springer papers to index.')
        return
    # Ensure index exists
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME)
    count = 0
    for paper in papers:
        try:
            es.index(index=INDEX_NAME, id=paper['id'], body=paper)
            print(f"Indexed Springer paper: {paper.get('title')}")
            count += 1
        except Exception as e:
            print('Failed to index paper', paper.get('id'), e)
    print(f"Indexed {count} Springer papers to Elasticsearch.")


if __name__ == '__main__':
    # Simple CLI: read SPRINGER_API_KEY from env and run
    key = os.getenv('SPRINGER_API_KEY')
    if not key:
        print('Set SPRINGER_API_KEY in environment to ingest Springer metadata.')
    else:
        papers = fetch_springer_papers(query='machine learning', max_results=200, page_size=50, api_key=key)
        index_papers_to_elasticsearch(papers)
