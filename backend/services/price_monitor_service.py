import asyncio
import json
import os
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict

from core.models import PriceMonitorConfig, PriceHistoryEntry
from core.websocket import manager
from services.engines.factory import engine_factory

logger = logging.getLogger("PriceMonitorService")


# Caminho para persistência local dos monitores
STORAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "price_monitors.json"

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
                            self.tasks[job_id] = asyncio.create_task(self._monitor_loop(job_id))
            except Exception as e:
                logger.error(f"Erro ao carregar monitores do disco: {e}")


    def _save_monitors(self):
        try:
            STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {job_id: config.model_dump() for job_id, config in self.monitors.items()}
            with open(STORAGE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar monitores no disco: {e}")


    async def start_monitor(self, job_id: str, url: str, brand: str, interval: int, duration: int):
        from services.url_utils import normalize_url
        norm_url = normalize_url(url)
        for existing_id, config in self.monitors.items():
            if normalize_url(config.url) == norm_url and config.brand.lower() == brand.lower():
                if config.active:
                    return config, "already_active"
                else:
                    await self.resume_monitor(existing_id)
                    return self.monitors[existing_id], "reactivated"

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
        return config, "created"

    async def stop_monitor(self, job_id: str):
        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]
        
        if job_id in self.monitors:
            self.monitors[job_id].active = False
            self._save_monitors()

    async def delete_monitor(self, job_id: str):
        # Para se estiver rodando
        await self.stop_monitor(job_id)
        
        # Remove dos registros
        if job_id in self.monitors:
            del self.monitors[job_id]
            self._save_monitors()

    async def delete_monitors_by_brand(self, brand_key: str):
        """Para e remove todos os monitores associados a uma marca."""
        to_delete = [job_id for job_id, config in self.monitors.items() if config.brand.lower() == brand_key.lower()]
        for job_id in to_delete:
            await self.delete_monitor(job_id)

    async def resume_monitor(self, job_id: str):
        if job_id in self.monitors:
            self.monitors[job_id].active = True
            if job_id not in self.tasks or self.tasks[job_id].done():
                self.tasks[job_id] = asyncio.create_task(self._monitor_loop(job_id))
            self._save_monitors()

    async def _monitor_loop(self, job_id: str):
        config = self.monitors.get(job_id)
        if not config:
            return

        # Jitter inicial para não disparar centenas de requests ao mesmo tempo (ex: no boot do servidor)
        # Sorteia um atraso entre 5 e 45 segundos para a primeira execução, exceto se for recém-criado
        if config.last_price is None:
            logger.info(f"Monitor {job_id} recém-criado. Pulando jitter para execução imediata.")
        else:
            initial_jitter = random.uniform(5, 45)
            logger.info(f"Monitor {job_id} aguardando jitter inicial de {initial_jitter:.1f}s...")
            await asyncio.sleep(initial_jitter)

        while config.active:
            try:
                # Resolve o motor dinamicamente via factory
                engine = engine_factory.get_engine(config.brand)
                product_data = await engine.get_product_details(config.url)
                
                # Converte para objeto se vier como dict (para facilitar acesso)
                from core.models import RawProductBronze
                product = RawProductBronze.model_validate(product_data) if product_data else None
                
                if product:
                    current_price = product.price_full
                    available = product.stock_availability
                    
                    # Atualiza metadados (imagem e nome) na config se ainda não tiver
                    needs_save = False
                    if product.image_url and not config.image_url:
                        config.image_url = product.image_url
                        needs_save = True
                    if product.raw_title and not config.product_name:
                        config.product_name = product.raw_title
                        needs_save = True

                    current_colors = product.available_colors or []
                    current_sizes = product.available_sizes or []
                    
                    if needs_save:
                        self._save_monitors()

                    # Verifica se houve mudança de preço, disponibilidade, cores ou tamanhos
                    has_change = False
                    
                    if config.last_price is None or config.last_price != current_price:
                        has_change = True
                        
                    # Checa se houve alteração nas numerações/cores disponíveis
                    if sorted(config.available_colors) != sorted(current_colors):
                        has_change = True
                        config.available_colors = current_colors
                    
                    if sorted(config.available_sizes) != sorted(current_sizes):
                        has_change = True
                        config.available_sizes = current_sizes
                    
                    # Registra no histórico se houve mudança
                    if has_change:
                        entry = PriceHistoryEntry(
                            price=current_price, 
                            available=bool(available),
                            available_colors=current_colors,
                            available_sizes=current_sizes
                        )
                        config.history.append(entry)
                        config.last_price = current_price
                        self._save_monitors()
                        
                        # Notifica o frontend via WebSocket
                        await manager.send_message({
                            "type": "price_update",
                            "price": current_price,
                            "available": available,
                            "available_colors": current_colors,
                            "available_sizes": current_sizes,
                            "history": [e.model_dump() for e in config.history],
                            "message": f"Mudança detectada! Preço: R$ {current_price:.2f} | Tamanhos: {len(current_sizes)}"
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

            # Aguarda o próximo intervalo com um pequeno jitter (±5%) para evitar sincronização
            base_sleep = config.interval_minutes * 60
            jitter_range = base_sleep * 0.05
            sleep_time = base_sleep + random.uniform(-jitter_range, jitter_range)
            
            logger.info(f"Monitor {job_id} concluído. Próxima checagem em {sleep_time/60:.1f} min.")
            await asyncio.sleep(max(1, sleep_time))

        # Fim do monitoramento manual (active desativado)
        self._save_monitors()
        await manager.send_message({"type": "done", "message": "Monitoramento pausado/desativado."}, job_id)

# Singleton
monitor_service = PriceMonitorService()
