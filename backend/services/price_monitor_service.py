import asyncio
import json
import os
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict

from pydantic import ValidationError

from core.models import (
    PriceMonitorConfig,
    PriceHistoryEntry,
    resolve_effective_price,
    resolve_original_price,
)
from core.websocket import manager
from services.engines.factory import engine_factory
from services.map_evaluator_service import EMPTY_MAP_METADATA, evaluate_map_violation
from services.map_rules_service import map_rules_service

logger = logging.getLogger("PriceMonitorService")


# Caminho para persistência local dos monitores
STORAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "price_monitors.json"

MAP_METADATA_FIELDS = (
    "map_violation",
    "map_price_floor",
    "map_rule_scope",
    "map_rule_id",
    "map_infractor",
    "map_infractor_is_default",
)

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

    def _set_map_metadata(self, config: PriceMonitorConfig, metadata: dict) -> None:
        for field in MAP_METADATA_FIELDS:
            setattr(config, field, metadata.get(field, EMPTY_MAP_METADATA.get(field)))

    def _map_metadata_payload(self, config: PriceMonitorConfig) -> dict:
        return {field: getattr(config, field) for field in MAP_METADATA_FIELDS}


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
            failure_reason = None
            try:
                config.last_checked_at = datetime.now(timezone.utc).isoformat()
                # Resolve o motor dinamicamente via factory
                engine = engine_factory.get_engine(config.brand)
                # get_pdp_product retorna o PRODUTO COMPLETO (compatível com
                # RawProductBronze). Para VTEX/Shopify/SFCC/Wake/Zara delega para
                # get_product_details; para os marketplaces (ML/Amazon/Netshoes)
                # usa o parser de PDP dedicado — get_product_details desses engines
                # devolve só {"seller": ...} (fluxo cross-marketplace) e quebraria
                # a validação.
                product_data = await engine.get_pdp_product(config.url)

                # Converte para objeto se vier como dict (para facilitar acesso).
                # A imagem não é obrigatória para resolver preço no monitor: removemos
                # image_url se vier ausente/inválida para não derrubar a validação
                # (RawProductBronze.image_url_must_be_present rejeitaria None/"").
                from core.models import RawProductBronze
                product = None
                if product_data:
                    payload = dict(product_data)
                    img = payload.get("image_url")
                    if not img or not str(img).strip() or str(img) == "None":
                        payload.pop("image_url", None)
                    try:
                        product = RawProductBronze.model_validate(payload)
                    except ValidationError as exc:
                        # Payload incompleto/ inválido: registra o motivo (visível nos
                        # logs do servidor, não só no WebSocket) e segue para o próximo
                        # ciclo. Sem isso o monitor ficava "Pendente" sem qualquer pista.
                        logger.warning(
                            "Monitor %s (%s): produto inválido em %s — %s",
                            job_id, config.brand, config.url, exc,
                        )
                        failure_reason = "Dados do produto incompletos ou inválidos."
                        await manager.send_message(
                            {"type": "error", "message": "Não foi possível extrair os dados do produto."},
                            job_id,
                        )
                        product = None
                else:
                    # get_pdp_product devolveu None: acesso bloqueado (anti-bot),
                    # 403/503 ou PDP sem dados extraíveis. O motivo detalhado (site,
                    # status, título da página) já foi logado pelo próprio engine.
                    failure_reason = (
                        "Não foi possível ler o produto — o site pode estar bloqueando "
                        "automação (anti-bot)."
                    )

                if product:
                    config.last_status = "ok"
                    config.last_error = None
                    map_metadata = evaluate_map_violation(
                        product,
                        map_rules_service.list_rules(active_only=True),
                        brand_name=config.brand,
                        marketplace=config.brand,
                    )
                    self._set_map_metadata(config, map_metadata)
                    current_price = resolve_effective_price(
                        product.price_full,
                        product.price_discount,
                        product.price_discount_is_delta,
                    )
                    current_original_price = resolve_original_price(
                        product.price_full,
                        product.price_discount,
                        product.price_discount_is_delta,
                    )
                    if (
                        current_original_price is not None
                        and current_price is not None
                        and current_original_price <= current_price
                    ):
                        current_original_price = None
                    # price_discount e um DELTA (valor positivo do desconto), nao um
                    # preco final — convencao dos engines VTEX/ML/Shopify
                    # (list_price - sale_price). Normaliza 0/None para None.
                    current_discount = (
                        current_price
                        if current_original_price is not None and current_price is not None
                        else None
                    )
                    available = product.stock_availability

                    # Atualiza metadados (imagem e nome) na config se ainda não tiver
                    if product.image_url and not config.image_url:
                        config.image_url = product.image_url
                    if product.raw_title and not config.product_name:
                        config.product_name = product.raw_title

                    current_colors = product.available_colors or []
                    current_sizes = product.available_sizes or []

                    # Verifica se houve mudança de preço, disponibilidade, cores ou tamanhos
                    has_change = False

                    if config.last_price is None or config.last_price != current_price:
                        has_change = True

                    if config.last_price_original != current_original_price:
                        has_change = True

                    # Mudanca apenas no desconto (price_full inalterado) tambem conta
                    # como mudanca — sem isso, uma promocao (D-01) era ignorada em
                    # silencio quando o preco efetivo nao mudava.
                    if config.last_price_discount != current_discount:
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
                            price_original=current_original_price,
                            last_price_discount=current_discount,
                            available=bool(available),
                            available_colors=current_colors,
                            available_sizes=current_sizes,
                            **self._map_metadata_payload(config),
                        )
                        config.history.append(entry)
                        config.last_price = current_price
                        config.last_price_original = current_original_price
                        config.last_price_discount = current_discount

                        # Notifica o frontend via WebSocket
                        await manager.send_message({
                            "type": "price_update",
                            "price": current_price,
                            "price_full": current_original_price or current_price,
                            "price_discount": current_discount,
                            "price_original": current_original_price,
                            "available": available,
                            "available_colors": current_colors,
                            "available_sizes": current_sizes,
                            "history": [e.model_dump() for e in config.history],
                            **self._map_metadata_payload(config),
                            "message": f"Mudança detectada! Preço: R$ {current_price:.2f} | Tamanhos: {len(current_sizes)}"
                        }, job_id)
                    else:
                        # Apenas log de "tudo igual"
                        await manager.send_message({
                            "type": "info",
                            **self._map_metadata_payload(config),
                            "message": f"Checagem realizada às {datetime.now().strftime('%H:%M:%S')}. Sem alterações."
                        }, job_id)
                else:
                    # Falha ao resolver o produto. Marca o estado para o front exibir
                    # algo claro ("Bloqueado") em vez de "Pendente" eterno.
                    config.last_status = "blocked"
                    config.last_error = failure_reason or "Falha ao acessar o produto."
                    self._set_map_metadata(config, EMPTY_MAP_METADATA)
                    await manager.send_message({"type": "error", "message": config.last_error}, job_id)

            except asyncio.CancelledError:
                # Cancelamento (stop/delete) deve propagar — nunca virar "erro do monitor".
                raise
            except Exception as e:
                # Loga com traceback no servidor (antes só ia para o WebSocket, invisível
                # sem cliente conectado — o que escondia a causa do "Pendente" eterno).
                logger.exception("Erro inesperado no monitor %s (%s): %s", job_id, config.brand, e)
                config.last_status = "error"
                config.last_error = f"Erro: {str(e)[:200]}"
                await manager.send_message({"type": "error", "message": f"Erro no monitor: {e}"}, job_id)

            # Persiste o estado da checagem (status/erro/preço/timestamp) a cada ciclo,
            # para o front refletir "ok"/"blocked"/"error" e o estado sobreviver a restart.
            self._save_monitors()

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
