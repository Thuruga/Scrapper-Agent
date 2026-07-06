"""Central de notificações persistente (mudanças de preço e término de processos).

Chamado de contextos distintos — loops asyncio dos monitores, job do APScheduler
e thread do executor no orchestrator multi — por isso os métodos são síncronos
e protegidos por threading.Lock (asyncio.Lock não cobre o caso da thread).
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.models import Notification

STORAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "notifications.json"
MAX_NOTIFICATIONS = 200

logger = logging.getLogger("NotificationService")


class NotificationService:
    def __init__(self):
        self._lock = threading.Lock()
        self._notifications: List[Notification] = self._load()

    def _load(self) -> List[Notification]:
        if not STORAGE_FILE.exists():
            return []
        try:
            raw = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
            return [Notification(**item) for item in raw]
        except Exception as e:
            logger.error("Falha ao carregar notificações: %s", e)
            return []

    def _save(self) -> None:
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STORAGE_FILE.write_text(
            json.dumps(
                [n.model_dump() for n in self._notifications],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def add(
        self,
        type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Notification]:
        """Registra uma notificação. Nunca propaga exceção — uma falha aqui
        não pode derrubar um scan ou um loop de monitoramento."""
        try:
            notification = Notification(
                type=type, title=title, message=message, metadata=metadata or {}
            )
            with self._lock:
                self._notifications.insert(0, notification)
                del self._notifications[MAX_NOTIFICATIONS:]
                self._save()
            return notification
        except Exception as e:
            logger.error("Falha ao registrar notificação '%s': %s", title, e)
            return None

    def list(self, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        with self._lock:
            items = self._notifications
            if unread_only:
                items = [n for n in items if not n.read]
            return list(items[:limit])

    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)

    def mark_read(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    if not n.read:
                        n.read = True
                        self._save()
                    return True
            return False

    def mark_all_read(self) -> int:
        with self._lock:
            unread = [n for n in self._notifications if not n.read]
            for n in unread:
                n.read = True
            if unread:
                self._save()
            return len(unread)

    def clear(self) -> int:
        with self._lock:
            count = len(self._notifications)
            if count:
                self._notifications = []
                self._save()
            return count

    def delete(self, notification_id: str) -> bool:
        with self._lock:
            before = len(self._notifications)
            self._notifications = [
                n for n in self._notifications if n.id != notification_id
            ]
            if len(self._notifications) != before:
                self._save()
                return True
            return False


# Singleton
notification_service = NotificationService()
