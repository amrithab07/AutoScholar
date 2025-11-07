from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.novelty import novelty_service

router = APIRouter()


class NoveltyRequest(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    references: Optional[List[str]] = None


@router.post('/score')
async def score_novelty(req: NoveltyRequest):
    if not req.title and not req.abstract:
        raise HTTPException(status_code=400, detail='Provide at least a title or abstract')

    try:
        result = novelty_service.score_paper(req.title or '', req.abstract or '', references=req.references or [], top_k=50)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Novelty scoring error: {str(e)}')
