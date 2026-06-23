# Phase 20: Motor de Relevância - Decision Gates - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Substituir o sistema de média linear rígida por uma árvore de decisão baseada em gates no cross_marketplace_service.py.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Os pesos específicos e lógicas de Gate 1, Gate 2 e Gate 3 já foram definidos nas Requirements.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `relevance_settings` no config.py pode precisar de pequenos ajustes, mas a maioria das constantes pode ser inline ou lida do environment caso necessário.

### Established Patterns
- `cross_marketplace_service.py` calcula o score em `run_visual_validation`.

### Integration Points
- `image_match_score` e `text_match_score` já estão disponíveis na função local `run_visual_validation` do motor visual, e devem ser usados como entrada para os Gates.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Seguir rigorosamente REL-01 a REL-04.

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
