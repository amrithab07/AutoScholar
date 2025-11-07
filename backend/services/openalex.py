"""Simple OpenAlex client helpers for fetching works and citations.

This module provides helpers to resolve a DOI or OpenAlex id to a work and to
fetch citing works (papers that reference the target) and referenced works.

Note: OpenAlex rate limits apply; this is a lightweight client for best-effort
graph augmentation when the local index doesn't contain explicit references.
"""
from typing import List, Dict, Optional
import httpx

BASE = "https://api.openalex.org"


def _normalize_doi(doi: str) -> str:
    return doi.strip().lower()


def resolve_work(identifier: str) -> Optional[Dict]:
    """Resolve an identifier (DOI or OpenAlex id) to an OpenAlex work object.

    identifier: could be a DOI like '10.1000/xyz' or an OpenAlex id like 'https://openalex.org/W123...'
    Returns the work JSON or None on failure.
    """
    if not identifier:
        return None
    identifier = identifier.strip()
    # if looks like DOI (contains a slash and a dot)
    try:
        if '/' in identifier and '.' in identifier and not identifier.lower().startswith('https://openalex.org'):
            doi = _normalize_doi(identifier)
            url = f"{BASE}/works/doi:{doi}"
        else:
            # assume it's an OpenAlex id or path
            if identifier.startswith('http'):
                # extract path after domain
                parts = identifier.split('openalex.org/')
                if len(parts) > 1:
                    identifier = parts[1]
            url = f"{BASE}/works/{identifier}"

        with httpx.Client(timeout=20.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def get_citing_works(openalex_id: str, per_page: int = 50) -> List[Dict]:
    """Return works that cite the given OpenAlex work id.

    openalex_id should be the OpenAlex work id string (e.g., 'W2741809807').
    """
    if not openalex_id:
        return []
    # Ensure we have just the id part (no leading path)
    if openalex_id.startswith('https://'):
        parts = openalex_id.split('openalex.org/')
        openalex_id = parts[1] if len(parts) > 1 else openalex_id

    url = f"{BASE}/works"
    params = {"filter": f"referenced_works:{openalex_id}", "per_page": per_page}
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                return data.get('results', [])
    except Exception:
        return []
    return []


def get_referenced_works(openalex_id: str, per_page: int = 50) -> List[Dict]:
    """Return works referenced by the given OpenAlex work id (the references list).

    The OpenAlex work object contains 'referenced_works' (list of ids). This fetches the first `per_page` of them.
    """
    w = resolve_work(openalex_id)
    if not w:
        return []
    refs = w.get('referenced_works') or []
    refs = refs[:per_page]
    results = []
    try:
        with httpx.Client(timeout=20.0) as client:
            for rid in refs:
                r = client.get(f"{BASE}/works/{rid}")
                if r.status_code == 200:
                    results.append(r.json())
    except Exception:
        return results
    return results
