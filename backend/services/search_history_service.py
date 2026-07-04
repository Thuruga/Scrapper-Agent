import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from core.models import SearchHistory

logger = logging.getLogger("SearchHistoryService")
STORAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "search_history.json"

class SearchHistoryService:
    def __init__(self):
        self.history: Dict[str, SearchHistory] = {}
        self.load_history()
    
    def load_history(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.history[k] = SearchHistory(**v)
                self.cleanup_old_records()
            except Exception as e:
                logger.error(f"Erro ao carregar histórico do disco: {e}")

    def _save_history(self):
        try:
            STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump(mode="json") for k, v in self.history.items()}
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico no disco: {e}")

    def cleanup_old_records(self):
        """Retém apenas os últimos 30 dias."""
        now = datetime.now(timezone.utc)
        to_delete = []
        for job_id, record in self.history.items():
            dt = datetime.fromisoformat(record.created_at)
            if now - dt > timedelta(days=30):
                to_delete.append(job_id)
        
        if to_delete:
            for job_id in to_delete:
                del self.history[job_id]
            self._save_history()
            logger.info(f"Cleanup removeu {len(to_delete)} registros antigos.")

    def create_job(self, job_id: str, query: str, brands: List[str], type: str = "search", target_sku: Optional[str] = None) -> SearchHistory:
        record = SearchHistory(job_id=job_id, query=query, brands=brands, type=type, target_sku=target_sku)
        self.history[job_id] = record
        self._save_history()
        return record
    
    def update_job(self, job_id: str, status: str, results: Optional[Any] = None, error: Optional[str] = None):
        if job_id in self.history:
            self.history[job_id].status = status
            if results is not None:
                self.history[job_id].results = results
            if error is not None:
                self.history[job_id].error = error
            self._save_history()
            
    def get_job(self, job_id: str) -> Optional[SearchHistory]:
        return self.history.get(job_id)

    def list_jobs(self) -> List[SearchHistory]:
        # Ordena do mais recente para o mais antigo
        jobs = list(self.history.values())
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs

    def delete_job(self, job_id: str) -> bool:
        if job_id in self.history:
            del self.history[job_id]
            self._save_history()
            return True
        return False

search_history_service = SearchHistoryService()
