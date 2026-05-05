import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from config import settings
from core.models import PriceMonitorConfig, PriceHistoryEntry
from core.websocket import manager
from scrapers import get_scraper

# Caminho para persistência local dos monitores
STORAGE_FILE = "data/price_monitors.json"

class PriceMonitorService:
    def __init__(self):
        self.monitors: Dict[str, PriceMonitorConfig] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        # Não chamamos _load_monitors aqui para evitar loop de importação se models mudar,
        # chamaremos explicitamente na inicialização do app.

    def load_monitors(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    data = json.load(f)
                    for job_id, config_dict in data.items():
                        self.monitors[job_id] = PriceMonitorConfig(**config_dict)
                        # Se estava ativo, reinicia a task
                        if self.monitors[job_id].active:
                            # Verifica se ainda está dentro do prazo
                            end_time = datetime.fromisoformat(self.monitors[job_id].start_time) + timedelta(hours=self.monitors[job_id].duration_hours)
                            if datetime.now(timezone.utc) < end_time:
                                self.tasks[job_id] = asyncio.create_task(self._monitor_loop(job_id))
                            else:
                                self.monitors[job_id].active = False
            except Exception as e:
                print(f"Erro ao carregar monitores: {e}")

    def _save_monitors(self):
        try:
            os.makedirs("data", exist_ok=True)
            data = {job_id: config.model_dump() for job_id, config in self.monitors.items()}
            with open(STORAGE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar monitores: {e}")

    async def start_monitor(self, job_id: str, url: str, brand: str, interval: int, duration: int):
        config = PriceMonitorConfig(
            job_id=job_id,
            url=url,
            brand=brand,
            interval_minutes=interval,
            duration_hours=duration,
            active=True
        )
        self.monitors[job_id] = config
        self._save_monitors()
        
        # Inicia a task de background
        task = asyncio.create_task(self._monitor_loop(job_id))
        self.tasks[job_id] = task
        return config

    async def stop_monitor(self, job_id: str):
        if job_id in self.monitors:
            self.monitors[job_id].active = False
            self._save_monitors()
        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]

    async def _monitor_loop(self, job_id: str):
        config = self.monitors.get(job_id)
        if not config:
            return

        # Duração total em segundos
        duration_seconds = config.duration_hours * 3600
        start_dt = datetime.fromisoformat(config.start_time)
        end_dt = start_dt + timedelta(seconds=duration_seconds)
        
        try:
            scraper_module = get_scraper(config.brand)
        except Exception as e:
            await manager.send_message({"type": "error", "message": f"Erro ao carregar scraper: {e}"}, job_id)
            return

        while datetime.now(timezone.utc) < end_dt and config.active:
            try:
                # Realiza o scrape
                product = await scraper_module.scrape_competitor_product(config.url, config.brand)
                
                if product:
                    current_price = product.price_full
                    available = product.stock_availability
                    
                    # Verifica se houve mudança de preço ou disponibilidade
                    has_change = False
                    if config.last_price is None or config.last_price != current_price:
                        has_change = True
                    
                    # Registra no histórico se houve mudança
                    if has_change:
                        entry = PriceHistoryEntry(price=current_price, available=available)
                        config.history.append(entry)
                        config.last_price = current_price
                        self._save_monitors()
                        
                        # Notifica o frontend via WebSocket
                        await manager.send_message({
                            "type": "price_update",
                            "price": current_price,
                            "available": available,
                            "history": [e.model_dump() for e in config.history],
                            "message": f"Mudança detectada! Novo preço: R$ {current_price:.2f}"
                        }, job_id)
                    else:
                        # Apenas log de "tudo igual"
                        await manager.send_message({
                            "type": "info",
                            "message": f"Checagem realizada às {datetime.now().strftime('%H:%M:%S')}. Sem alterações."
                        }, job_id)
                else:
                    await manager.send_message({"type": "error", "message": "Falha ao acessar o produto."}, job_id)
                    
            except Exception as e:
                await manager.send_message({"type": "error", "message": f"Erro no monitor: {e}"}, job_id)

            # Aguarda o próximo intervalo
            await asyncio.sleep(config.interval_minutes * 60)

        # Fim do tempo de monitoramento
        config.active = False
        self._save_monitors()
        await manager.send_message({"type": "done", "message": "Tempo de monitoramento concluído."}, job_id)

# Singleton
monitor_service = PriceMonitorService()
