# Project Concerns & Technical Debt

## Resolved / Improved (Phase 4.1)
- [x] **Event Loop Blocking**: Resolvido via `asyncio.to_thread` para exportação de Excel.
- [x] **Idiomatic Cancellation**: Migrado de `threading.Event` para `asyncio.Event`.
- [x] **Data Expansion Safety**: Adicionado tratamento de NaNs na expansão de especificações Pandas.
- [x] **Intelligence Debt**: Removido serviço legado de sugestão de categorias (Auto-Discovery agora é dinâmico por motor).

## High Priority
- **Incremental Excel Writing**: Atualmente acumulamos produtos na memória antes de salvar. Para volumes >50k itens, precisamos de escrita incremental direto no disco.
- **WAF Sensitivity**: Alguns sites Shopify estão ficando mais agressivos. Pode ser necessário rotacionar proxies com maior frequência ou usar residential proxies.

## Medium Priority
- **Price History Depth**: Atualmente salvamos apenas o último preço. Falta uma tabela histórica robusta para gráficos de variação de 30 dias no frontend.
- **Frontend State Persistence**: Se o usuário recarregar a página durante um Job, ele perde o progresso visual (embora o Job continue no backend). Necessário persistir estado do Job no LocalStorage ou via API.

## Maintenance
- **Playwright Updates**: Drivers precisam ser atualizados mensalmente para evitar detecção.
- **Brand Mapping**: O arquivo `category_mapping.py` está crescendo. Pode ser necessário mover para um banco de dados ou arquivos JSON separados por nicho.
