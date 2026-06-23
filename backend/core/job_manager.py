import asyncio
from typing import Dict


# Mapa global: job_id → Event de cancelamento
JOB_CANCEL_FLAGS: Dict[str, asyncio.Event] = {}
