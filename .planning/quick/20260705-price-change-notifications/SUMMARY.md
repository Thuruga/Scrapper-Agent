---
status: complete
date: 2026-07-05
commits: [bce495a, c543da8, a855362, 442e4c5, 52774e7, a4b681c, 5ebd8f0]
---

# Summary — Sistema de Notificações (mudanças de preço + término de processos)

## O que foi feito

Sistema de notificações completo, ponta a ponta:

**Backend**
- `Notification` model (`core/models.py`) + `NotificationService` singleton (`services/notification_service.py`): persistência em `data/notifications.json`, `threading.Lock` (cobre loops asyncio, APScheduler e thread do executor), rotação em 200 itens, `add()` nunca propaga exceção.
- Rotas REST (`api/routes_notifications.py`): `GET /notifications`, `POST /{id}/read`, `POST /read-all`, `DELETE /{id}` — registradas com auth X-API-Key.
- **Monitor de produto único** (`price_monitor_service.py`): detecção separada em `was_baseline` / `price_changed` / `variants_changed`. Notifica **somente** mudança de preço (efetivo, original ou desconto) — nunca na primeira leitura, nunca por cores/tamanhos. `history` preservado idêntico.
- **Monitor de categoria** (`category_monitor_service.py`): diff de preço efetivo entre snapshot anterior e novo (chave = `normalize_url(url)`, preço via `resolve_effective_price`). 1 notificação agregada por scan (`changes` capado em 50 no metadata). Scan inicial de monitor criado pelo usuário também emite `scan_finished`.
- **Orchestrators** (single + multi): `scan_finished` com status success/cancelled/error em todos os pontos terminais.

**Frontend**
- `AppNotification` type + 4 métodos no `ApiClient`; `notificationStore` (zustand) com polling de 10s a partir do `App()`, dedup por `seenIds` (primeiro poll silencioso), toasts sonner por tipo/status; update otimista de read/delete.
- `NotificationBell` no header: badge de não-lidas (99+), painel glass com lista, tempo relativo, marcar como lida no clique, marcar todas; responsivo mobile.
- Fix: rota `/notifications` adicionada ao proxy do Vite dev server (sem isso o polling recebia index.html e a central ficava vazia em dev).

## Verificação

- Diff de categoria: 6 casos unitários com snapshot real de 245 produtos (sem mudança, 2 mudanças, URL com utm, produto novo, snapshot vazio, preço None) — todos ok.
- Ponta a ponta real: `last_price` do monitor aramis alterado para 250.0 → scrape real detectou 299.90 → notificação `price_change` criada com metadata completa; monitores sem mudança não geraram falso alerta.
- Rotas: auth obrigatória, 404 em id inexistente, read-all, mark-read persistente — validadas via curl.
- Visual (Playwright): sino renderiza no header, painel abre e mostra "Preço alterado — Camisa Manga Longa... R$ 250.00 → R$ 299.90 · há 3 min".
- `tsc -b` e `vite build` verdes.

## Follow-up (mesmo dia)

- Clique na notificação navega para a tela correspondente: `price_change` → Monitores/Produto Único; `category_price_change` e `scan_finished` de monitor de categoria → Monitores/Categorias; `scan_finished` de varredura avulsa → aba Categorias. Estado da view do monitor elevado da `MonitoringPage` para o `App`.
- Botão "Limpar histórico" no rodapé do painel: `DELETE /notifications` (novo `clear()` no serviço) + `clearAll()` otimista no store. Verificado no browser (navegação a partir da aba Banners + limpeza persistida no servidor).

## Observações

- O backend precisou ser reiniciado para carregar o novo código (estava rodando com o código antigo — reiniciado em background durante a verificação).
- Escopo de "término de processo": varreduras de categoria (single/multi) e scan inicial de monitor de categoria. Banners e buscas ficaram fora (já têm toasts próprios). Scans agendados do APScheduler não notificam término — só mudança de preço.
