"""
Job Cancellation Manager.

Registry de threading.Event para sinalizar cancelamento de jobs em andamento.
O orquestrador verifica esses eventos entre cada tarefa de extração.
"""

import threading
from typing import Dict


# Mapa global: job_id → Event de cancelamento
JOB_CANCEL_FLAGS: Dict[str, threading.Event] = {}
