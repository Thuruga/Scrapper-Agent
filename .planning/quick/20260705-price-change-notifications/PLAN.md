# Sistema de Notificações — Alertas de mudança de preço + término de processos

## Contexto

O usuário não é alertado sobre mudanças de preço em nenhum dos dois tipos de monitor:

- **Monitor de produto único**: o backend JÁ detecta mudança de preço corretamente ([price_monitor_service.py:244-296](backend/services/price_monitor_service.py#L244-L296)) e grava no `history`, mas o único "alerta" é uma mensagem WebSocket `price_update` enviada para `/ws/{job_id}` — que o frontend nunca assina (a `MonitorPage` só faz polling REST de `/monitors` a cada 5s). O `ConnectionManager.send_message` ([core/websocket.py:27-33](backend/core/websocket.py#L27-L33)) descarta a mensagem silenciosamente quando não há socket conectado. **Causa raiz do item 1.**
- **Monitor de categoria**: [run_category_scan](backend/services/category_monitor_service.py#L67-L120) só grava snapshot de estoque/MAP — não existe detecção de mudança de preço. Precisa ser construída (diff entre snapshot anterior e novo).
- **Não existe sistema de notificações**: nenhuma persistência de alertas, nenhum sino/central no frontend, nenhum registro de término de varredura de categoria (o orchestrator só emite `done`/`error_done` via WS, perdido se ninguém escutar).

Arquitetura escolhida: como o frontend já é 100% polling e o backend persiste tudo em JSON, o backend ganha um **NotificationService persistente** (`notifications.json`) + rotas REST, e o frontend ganha um **notificationStore** (zustand) com polling, toasts (sonner, já instalado) e um **sino com central de notificações** no header.

Decisões de recorte:
- Notificar preço **somente quando preço muda** (efetivo, original ou desconto — início/fim de promoção é evento de preço). Mudança só de cores/tamanhos continua alimentando o `history` mas **não notifica**.
- Categoria: **1 notificação agregada por scan** ("N produtos mudaram de preço"), nunca 1 por produto.
- "Término de processo": varreduras de categoria (single + multi) e o scan inicial de um monitor de categoria recém-criado. Scans agendados do APScheduler (a cada 10 min) NÃO geram notificação de término (só de mudança de preço). Banners e buscas ficam fora — já têm toast próprio.
- Primeira checagem/primeiro scan = baseline, **nunca gera alerta**.

## Etapas de implementação (commits atômicos)

### Etapa A — Backend: núcleo (modelo + serviço + rotas)

1. **`backend/core/models.py`** — adicionar após `PriceMonitorConfig` (~linha 418):
```python
class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str            # "price_change" | "category_price_change" | "scan_finished"
    title: str
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

2. **`backend/services/notification_service.py`** (criar) — singleton `notification_service`, padrão dos demais serviços:
   - Persistência: `backend/data/notifications.json`, newest-first, truncado em `MAX_NOTIFICATIONS = 200`.
   - **`threading.Lock`** (não `asyncio.Lock`): será chamado de loops asyncio dos monitores, do job APScheduler E de thread do executor no `orchestrator_multi` (`consolidate_and_save` roda via `run_in_executor`). Métodos síncronos.
   - `add(type, title, message, metadata=None)` — engole exceções de I/O com `logger.error` (notificação nunca pode derrubar um scan).
   - `list(unread_only=False, limit=50)`, `unread_count()`, `mark_read(id)`, `mark_all_read()`, `delete(id)`. `_load` tolerante a JSON corrompido (retorna `[]`).

3. **`backend/api/routes_notifications.py`** (criar):
   - `GET /notifications?unread_only=false&limit=50` → `{"notifications": [...], "unread_count": int}`
   - `POST /notifications/{id}/read`, `POST /notifications/read-all`, `DELETE /notifications/{id}`

4. **`backend/api/__init__.py`** — registrar o router (herda `Depends(verify_api_key)` do agregador).

### Etapa B — Backend: emissão no monitor de produto único

**`backend/services/price_monitor_service.py`**, bloco linhas 243-296 — separar a detecção em flags, preservando `has_change` (e o `history`) exatamente como hoje:

```python
was_baseline = config.last_price is None
price_changed = (
    config.last_price != current_price
    or config.last_price_original != current_original_price
    or config.last_price_discount != current_discount
)
variants_changed = ...  # blocos atuais de cores/tamanhos setam esta flag
has_change = was_baseline or price_changed or variants_changed
```

Dentro do `if has_change:`, **capturar `old_price`/`old_original` ANTES de sobrescrever** `config.last_price...`. Após atualizar (WS mantido intacto):

```python
if price_changed and not was_baseline and current_price is not None:
    notification_service.add(
        type="price_change",
        title=f"Preço alterado — {config.product_name or config.brand}",
        message=f"R$ {old_price:.2f} → R$ {current_price:.2f}",
        metadata={"job_id": job_id, "url": config.url, "brand": config.brand,
                  "old_price": old_price, "new_price": current_price,
                  "old_original_price": old_original,
                  "new_original_price": current_original_price,
                  "image_url": config.image_url},
    )
```

O caminho `blocked`/`error` (linhas 304-321) não alcança este bloco e não toca `last_price` → sem falso alerta; se o preço mudar durante bloqueio, notifica na recuperação (correto).

### Etapa C — Backend: diff de preço no monitor de categoria

**`backend/services/category_monitor_service.py`**:

- Shape real do snapshot `monitored_products_{monitor_id}.json`: **lista** de dicts com `price_full`, `price_discount`, `price_discount_is_delta`, `url`, `raw_title`... Chave de identidade do diff: **`normalize_url(url)`** (helper existente em `backend/services/url_utils.py:31`) — NÃO usar `scan_product_id` (o hash inclui o título, muda se o título mudar).
- Preço efetivo: reutilizar `resolve_effective_price(price_full, price_discount, price_discount_is_delta)` de [core/models.py:14](backend/core/models.py#L14) — mesma função do monitor de produto único.
- Novos helpers: `_load_previous_snapshot(monitor_id)` (`[]` se ausente/corrompido), `_effective_price(product)`, `_detect_price_changes(previous, current)` → lista de `{"url", "title", "old_price", "new_price", "image_url"}` quando `round(old, 2) != round(new, 2)` e ambos não-None. Produtos que somem/aparecem são ignorados.
- Em `run_category_scan` (assinatura vira `async def run_category_scan(monitor: dict, notify_completion: bool = False)`):
  - Carregar `previous_products` **ANTES** do `products_file.write_text` (linha 100) — senão o diff compara o arquivo consigo mesmo.
  - Após persistir: `if previous_products and scraped_products:` (cobre 1º scan e scrape vazio) → se houver `changes`, emitir **uma** notificação `category_price_change` com `message=f"{len(changes)} produto(s) mudaram de preço..."` e `metadata={"monitor_id", "url", "brand", "change_count", "changes": changes[:50]}`.
  - No fim: `if notify_completion:` → notificação `scan_finished` ("Varredura concluída — {brand}, N produtos coletados").
- **`backend/api/routes_monitor.py`** (`create_category_monitor`): `background_tasks.add_task(run_category_scan, row, notify_completion=True)`. O `category_monitor_job` agendado continua sem o flag.

### Etapa D — Backend: término de varreduras de categoria

- **`backend/services/orchestrator.py`** — nos pontos terminais (linhas 113-132: `done`, `cancelled_done`, `error_done` "nenhum produto", `error_done` do except): emitir `scan_finished` com `metadata.status` = `"success" | "cancelled" | "error"`, marca, url, arquivo de saída, contagem de produtos.
- **`backend/services/orchestrator_multi.py`** — `consolidate_and_save` passa a retornar `True`/`False`; em `run_multi_orchestrator`, após o `run_in_executor` (linha ~218) e no ramo `else`, emitir `scan_finished` no corpo async (contexto completo: job_id, category_label, marcas, totais) com status `cancelled`/`success`/`error`.
- Sem risco de import circular: `notification_service` importa apenas `core.models`.

### Etapa E — Frontend: API client + store + polling + toasts

1. **`frontend/src/api/client.ts`** — tipo `AppNotification` + métodos estáticos: `getNotifications(unreadOnly = false, limit = 50)`, `markNotificationRead(id)`, `markAllNotificationsRead()`, `deleteNotification(id)`.
2. **`frontend/src/stores/notificationStore.ts`** (criar, padrão do [bannerStore.ts](frontend/src/stores/bannerStore.ts)):
   - Estado: `notifications`, `unreadCount`, `panelOpen`; ações `poll`, `markRead`, `markAllRead`, `remove`, `setPanelOpen`.
   - Module-level `initialized` + `seenIds: Set<string>`: no **primeiro** poll popular `seenIds` **sem toast** (não re-toastar backlog ao abrir o app); nos seguintes, toast para cada id novo:
     - `price_change` / `category_price_change` → `toast.warning(title, { description: message })`
     - `scan_finished` → por `metadata.status`: success → `toast.success`, error → `toast.error`, cancelled → `toast.info`
   - Falhas do `poll()` silenciosas (polling de fundo). `markRead`/`markAllRead` com update otimista.
3. **`frontend/src/App.tsx`** — no componente raiz `App()` (~linha 4353): `useEffect` com `poll()` imediato + `setInterval(poll, 10000)` + cleanup.

### Etapa F — Frontend: sino + central de notificações

1. **`frontend/src/App.tsx`**:
   - Imports lucide: `Bell`, `CheckCheck` (conferir duplicatas no bloco de imports 3-41).
   - Novo componente `const NotificationBell = () => {...}` (arrow-function const, padrão do arquivo): botão `Bell` + badge de não-lidas (cap "99+"); dropdown com `AnimatePresence`/`motion.div`; fechar por clique-fora (`useRef` + `mousedown`); lista com título/mensagem/tempo relativo ("há 5 min"), dot de não-lida, clique marca como lida; header do painel com "Notificações" + `CheckCheck` "Marcar todas como lidas"; estado vazio "Nenhuma notificação".
   - Montar no `<header className="content-header">` (~linha 4454), à direita.
2. **`frontend/src/App.css`** — classes `.notification-bell-wrapper`, `.notification-bell-btn`, `.notification-badge` (bg `var(--error)`), `.notification-panel` (absolute, right 0, ~380px, max-height ~480px overflow-y, padrão glass: `var(--card-bg)` + `var(--glass-border)` + blur), `.notification-item`/`.unread` (borda esquerda `var(--primary)`), header/footer/empty. Mobile: painel `position: fixed` largura quase total.

## Guardas obrigatórias (edge cases)

- Primeira checagem de monitor novo (`was_baseline`) → grava history, **não notifica**.
- Primeiro scan de categoria (snapshot inexistente) e scrape vazio → `if previous_products and scraped_products` cobre ambos.
- `current_price is None` → guarda explícita no `if` de notificação.
- Capturar preço antigo **antes** de sobrescrever `config.last_price` (senão mensagem mostra old == new).
- Comparação de floats com `round(x, 2)`.
- Anti-spam: 1 notificação agregada por scan de categoria; scans agendados sem `scan_finished`; rotação em 200 itens; `changes` capado em 50 no metadata.
- Toast duplicado: dedup por `seenIds` + primeiro poll silencioso; banners/buscas fora do escopo de emissão.

## Verificação ponta a ponta

```bash
# Backend (porta 8500)
cd backend && python app.py
# Frontend
cd frontend && npm run dev   # http://127.0.0.1:5173

# API direta
KEY=$(grep INTERNAL_API_KEY backend/.env | cut -d= -f2)
curl -s -H "X-API-Key: $KEY" http://127.0.0.1:8500/notifications | python3 -m json.tool
```

1. **Preço (produto único)**: parar backend, editar `last_price` de um monitor ativo em `backend/data/price_monitors.json` (ex.: 165.99 → 100.0), reiniciar; ou reduzir `interval_minutes` para 1. Em ~1 min: notificação `price_change` no GET + toast no front.
2. **Preço (categoria)**: editar um `price_full` em `backend/data/monitored_products_<id>.json` e disparar `run_category_scan` manualmente (script inline python) ou reduzir temporariamente o intervalo do APScheduler em `app.py:37`. Esperar 1 notificação `category_price_change` agregada.
3. **Término de processo**: iniciar varredura na aba Categorias, trocar de aba; ao concluir → toast + item no sino.
4. **Guardas**: monitor novo → 1ª checagem sem notificação; monitor de categoria novo → 1º scan gera só `scan_finished`, sem alerta de preço; marcar como lida e recarregar → badge persiste.

## Nota de processo (gsd-quick)

Tarefa invocada via `/gsd-quick`: na execução, criar `.planning/quick/YYYYMMDD-price-change-notifications/PLAN.md` a partir deste plano, commits atômicos por etapa (A→F, Conventional Commits, ex.: `feat(notifications): ...`), SUMMARY.md ao final e atualizar a tabela "Quick Tasks Completed" do STATE.md (não tocar ROADMAP.md).
