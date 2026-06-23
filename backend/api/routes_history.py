from fastapi import APIRouter, HTTPException
from typing import List
from core.models import SearchHistory
from services.search_history_service import search_history_service

router = APIRouter(prefix="/history", tags=["history"])

@router.get("", response_model=List[SearchHistory])
async def list_history():
    """Lista o histórico de pesquisas recentes."""
    return search_history_service.list_jobs()

@router.get("/{job_id}", response_model=SearchHistory)
async def get_history(job_id: str):
    """Obtém detalhes de uma pesquisa específica."""
    job = search_history_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    return job

@router.delete("/{job_id}", status_code=204)
async def delete_history(job_id: str):
    """Exclui uma pesquisa do histórico."""
    success = search_history_service.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    return None
