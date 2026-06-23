# Phase 21: IA Visual - Batching e Concorrência - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Acelerar drasticamente a inferência de imagem através do processamento em lote em `image_ai_service.py` e adaptação correspondente em `cross_marketplace_service.py`.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Garantir o uso da biblioteca correta para paralelismo (asyncio) e usar as APIs em batch do processador CLIP.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `image_ai_service.py` já possui as funções básicas para CLIP.

### Established Patterns
- Atualmente as validações em `cross_marketplace_service.py` (`run_visual_validation`) são enfileiradas via `asyncio.gather`, o que resolve I/O assíncrono para os downloads, mas passa pela IA de forma sequencial por chamada, não aproveitando tensores processados juntos na GPU/CPU.

### Integration Points
- O endpoint precisará empacotar as imagens que terminarem de baixar com sucesso e passá-las juntas para `get_embedding_async`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Seguir VIS-01 a VIS-03 rigorosamente.

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
