# Excluir Monitoramento e Visualizar Produtos

O objetivo é adicionar a funcionalidade de deletar um monitoramento ativo e exibir os produtos atrelados a ele.

## User Review Required

Atualmente o Job assíncrono do backend (que roda a cada 10 min) ainda não está salvando os produtos extraídos em lugar nenhum, ele apenas atualiza a data da última varredura.

Para visualizar "quais produtos estão sendo monitorados", será necessário implementar a extração completa e salvar o último *snapshot* dos produtos atrelados àquele Monitor.

Decisão necessária: Posso salvar esses produtos localmente (ex: `data/monitored_products.json`) ou criar a lógica para a tabela no Supabase para salvar todos os produtos extraídos em cada varredura de 10 min?

## Proposed Changes

### Backend (`api/routes_monitor.py` e `services/category_monitor_service.py`)
- **Exclusão:** Adicionar o endpoint `DELETE /monitor/category/{id}` que remove a categoria do banco (ou do JSON local de fallback).
- **Armazenamento de Produtos:** Finalizar o `TODO` dentro de `run_category_scan` para executar a extração e salvar os produtos.
- **Listagem de Produtos:** Criar endpoint `GET /monitor/category/{id}/products` para retornar a lista.

### Frontend (`App.tsx` e `client.ts`)
- **Exclusão:** Adicionar ícone de Lixeira (Trash) na tabela.
- **Visualização:** Adicionar um botão "Ver Produtos" que abrirá um modal exibindo uma grid simples.
