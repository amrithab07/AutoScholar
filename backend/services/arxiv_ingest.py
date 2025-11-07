import arxiv
from elasticsearch import Elasticsearch
from app.core.config import settings

# Connect to Elasticsearch with HTTPS and authentication
es = Elasticsearch(
    hosts=[{
        'host': settings.ELASTICSEARCH_HOST,
        'port': settings.ELASTICSEARCH_PORT,
        'scheme': 'https'
    }],
    basic_auth=("elastic", "BnKf5CZd4MIVY=Cg-MQ0"),  # <-- Replace <your-password> with your actual password
    verify_certs=False  # For local dev, disables SSL verification
)

INDEX_NAME = settings.ELASTICSEARCH_INDEX_PAPERS

def fetch_arxiv_papers(query="BERT", max_results=100):
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers = []
    for result in client.results(search):
        paper = {
            "id": result.get_short_id(),
            "title": result.title,
            "abstract": result.summary,
            "authors": [{"name": author.name} for author in result.authors],
            "published": result.published.strftime("%Y-%m-%d"),
            "url": result.entry_id,
            "keywords": [],  # arXiv does not provide keywords
        }
        papers.append(paper)
    return papers

def index_papers_to_elasticsearch(papers):
    # Ensure index exists
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME)
    count = 0
    for paper in papers:
        es.index(index=INDEX_NAME, id=paper["id"], body=paper)
        print(f"Indexed paper: {paper['title']}")
        count += 1
    print(f"Indexed {count} papers to Elasticsearch.")

if __name__ == "__main__":
    papers = fetch_arxiv_papers()
    index_papers_to_elasticsearch(papers)
