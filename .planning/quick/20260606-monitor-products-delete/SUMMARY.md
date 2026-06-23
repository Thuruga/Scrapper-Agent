---
status: complete
---
# Quick Task: Excluir Monitoramento e Visualizar Produtos

## Action Taken
- Backend:
  - Adicionado `DELETE /monitor/category/{id}` em `routes_monitor.py` que exclui a categoria (banco ou fallback) e o JSON atrelado local de produtos.
  - Adicionado `GET /monitor/category/{id}/products` em `routes_monitor.py` que lê o snapshot dos produtos.
  - Implementado a lógica em `category_monitor_service.py` onde a função `run_category_scan` passa a de fato utilizar a engine da marca para varrer e extrair os produtos reais da categoria (`engine.run_bulk_scrape`), salvando em um arquivo `data/monitored_products_{id}.json`.
- Frontend:
  - Adicionado os métodos de requisição em `ApiClient`.
  - Inserido uma coluna extra de "Ações" na tabela de `MonitoredCategoriesPage`.
  - Adicionado os botões (ícones de Olho e Lixeira).
  - Implementado o modal de "Ver Produtos" renderizando um grid com as informações (nome, foto e preço) do *snapshot* de extração do monitoramento.
