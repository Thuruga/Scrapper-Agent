# Testing: Intelligence Scraper

## Methodology
Atualmente o projeto utiliza **Experiential Testing** via scripts de "scratch" para validação rápida de funcionalidades e correções.

## Test Directory (`scratch/`)
- `verify_engine_abstraction.py`: Valida o funcionamento da factory e dos motores.
- `test_category_matching.py`: Testa o algoritmo de Fuzzy Matching.
- `check_buckman.py`: Script de diagnóstico rápido para novas plataformas.

## Manual Verification Flow
1. Rodar `app.py`.
2. Acessar o frontend local.
3. Testar o fluxo completo: Busca de categoria -> Seleção -> Varredura -> Download do Excel.

## Future Testing Goals
- Implementar `pytest` para os motores (usando `pytest-asyncio`).
- Adicionar Mocks para as APIs externas para rodar CI de forma estável.
