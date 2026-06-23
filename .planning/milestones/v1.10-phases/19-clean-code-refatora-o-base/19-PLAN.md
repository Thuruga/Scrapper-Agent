# Phase 19: Clean Code & Refatoração Base - Plan

**Goal:** Centralizar a lógica de texto no serviço correto e limpar o serviço de marketplace.

## Tasks

1. **[NLP-01] Remover funções locais de NLP**
   - Arquivo: `services/cross_marketplace_service.py`
   - Ação: Remover as variáveis/funções não utilizadas: `_STOP_WORDS`, `_normalizar`, `_calcular_relevancia`.
   - Justificativa: A limpeza é necessária porque o score agora é centralizado via `nlp_service.py` (`text_match_score`), e essas funções estão obsoletas.

2. **[NLP-02] Confirmar centralização no nlp_service.py**
   - Arquivo: `services/nlp_service.py`
   - Ação: Verificar se `calculate_text_score` e a remoção de cores estão implementadas corretamente. Não há mudanças necessárias se já estiver implementado, apenas revisar a delegação.

3. **Verificação Local**
   - Ação: Executar `python -m pytest` ou rodar a aplicação para garantir que `cross_marketplace_service.py` funciona sem erros de importação ou referência a variáveis inexistentes.
