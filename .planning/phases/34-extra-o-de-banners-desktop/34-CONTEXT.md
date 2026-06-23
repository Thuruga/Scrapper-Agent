# Phase 34: Extração de Banners Desktop - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Transformar o protótipo validado de extração de banners desktop em uma feature do dashboard para o usuário final. A fase cobre seleção de marcas ativas, execução e cancelamento observáveis, coleta de todos os slides de imagem do hero principal, armazenamento deduplicado, histórico por 30 dias, galeria de revisão e aprovação explícita. A publicação efetiva no SharePoint pertence à Phase 35.

</domain>

<decisions>
## Implementation Decisions

### Disparo, seleção e acompanhamento
- **D-01:** A extração será iniciada por um botão em uma aba dedicada chamada **Banners** no dashboard; não será uma ferramenta restrita ao terminal.
- **D-02:** A seleção de marcas seguirá o padrão visual e comportamental da busca comparativa: todas as marcas ativas começam selecionadas e o usuário pode marcar ou desmarcar livremente antes de iniciar.
- **D-03:** Durante a execução, a interface mostrará progresso por marca e exibirá resultados conforme cada site terminar, com aviso ao final.
- **D-04:** A execução terá uma ação **Parar**. Ela cancela imediatamente, em best effort, a marca em processamento, preserva os resultados já concluídos na sessão atual e marca as marcas restantes como canceladas.

### Histórico local
- **D-05:** Cada execução integralmente concluída e aprovada cria uma entrada datada; execuções anteriores permanecem disponíveis.
- **D-06:** O histórico segue o padrão das buscas: retenção automática de 30 dias e exclusão manual pelo usuário.
- **D-07:** Clicar em uma execução histórica reabre sua galeria e seus resultados armazenados sem raspar novamente os sites.
- **D-08:** Execuções canceladas ou parciais não entram no histórico. Seus resultados parciais podem permanecer visíveis somente na sessão atual.

### Arquivos e identidade dos banners
- **D-09:** Quando houver `srcset` ou variantes, preservar a maior resolução **desktop** disponível. Registrar separadamente a URL efetivamente renderizada na viewport `1366×768`.
- **D-10:** Preservar exatamente o formato recebido (`webp`, `png`, `jpg`, `avif` etc.), sem conversão.
- **D-11:** O nome do arquivo será legível, com ordem, descrição curta e marca no final, por exemplo `01-sale-inverno-aramis.webp`. O hash não faz parte do nome.
- **D-12:** O SHA-256 permanece nos metadados e é a identidade de conteúdo para deduplicação física. O mesmo arquivo ocupa uma única cópia física, mas pode ser referenciado por múltiplas execuções históricas.

### Revisão e aprovação
- **D-13:** Uma extração concluída entra em estado de revisão e exige aprovação explícita antes de ser finalizada no histórico e ficar elegível para a Phase 35.
- **D-14:** A aprovação é por banner. Todos começam selecionados; o usuário desmarca falsos positivos e aprova os restantes.
- **D-15:** Banners desmarcados são removidos da execução final; o histórico exibe apenas os banners aprovados.
- **D-16:** A aprovação é definitiva. Correções posteriores exigem uma nova extração, em vez de editar uma execução aprovada.

### Claude's Discretion
- Estrutura interna dos módulos, nomes de endpoints e separação entre serviço, armazenamento e API.
- Política exata de retry, timeouts e concorrência, respeitando o limite de memória já documentado no `BrowserManager` e os comportamentos de cancelamento definidos acima.
- Detalhes visuais da aba Banners, desde que reutilizem os padrões existentes de chips de marca, estados de progresso, cards e notificações.
- Formato interno dos índices de conteúdo e referências históricas, desde que cumpra deduplicação SHA-256, retenção de 30 dias e reabertura sem nova coleta.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Escopo e requisitos
- `.planning/PROJECT.md` — objetivo do milestone v3.0 e limites da frente de banners.
- `.planning/REQUIREMENTS.md` — requisitos BANNER-01 a BANNER-04 da Phase 34.
- `.planning/ROADMAP.md` — boundary, dependências e critérios de sucesso da Phase 34.
- `.planning/STATE.md` — decisões acumuladas e evidência da rodada de validação nos 13 sites.

### Protótipo validado
- `testes/extrair_banners.py` — detector funcional, navegação de carrossel, download, metadados, JSON/CSV, screenshot e galeria HTML.
- `testes/README.md` — modo de execução, saídas atuais e regra observável de detecção.

### Backend e persistência
- `backend/data/brands.json` — fonte atual das marcas cadastradas.
- `backend/services/brand_service.py` — acesso canônico às marcas e filtro de ativas.
- `backend/core/browser_manager.py` — configuração Playwright/Chromium e restrições de memória.
- `backend/core/job_manager.py` — flags globais de cancelamento por `job_id`.
- `backend/core/websocket.py` — streaming de mensagens por job para a interface.
- `backend/services/search_history_service.py` — padrão existente de histórico, ordenação, retenção de 30 dias e exclusão.
- `backend/api/routes_history.py` — contrato existente de listar, reabrir e excluir histórico.

### Frontend
- `frontend/src/App.tsx` — seleção de marcas da busca comparativa, `HistoryList`, navegação por abas e renderização incremental existente.
- `frontend/src/stores/searchStore.ts` — padrão Zustand, `AbortController`, identity guards, outcomes e notificações globais.
- `frontend/src/api/client.ts` — cliente autenticado e métodos do histórico.

No external specs — requirements and user-facing decisions are fully captured above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `testes/extrair_banners.py`: já validou os algoritmos de coleta de `img`, `srcset`, lazy loading, `background-image`, avanço do carrossel, distinção de vídeos e download dos originais; deve ser promovido para código de produção, não reescrito às cegas.
- `BrowserManager.CHROMIUM_ARGS`: configuração de Chromium já usada pelo projeto e pelo spike.
- `BrandManagerService.list_brands(active_only=True)`: chokepoint para obter somente marcas ativas.
- `JOB_CANCEL_FLAGS` e `ConnectionManager`: bases existentes para cancelamento cooperativo e progresso por WebSocket.
- `SearchPage` em `frontend/src/App.tsx`: chips de marcas, ações selecionar todas/desmarcar e padrão visual solicitado pelo usuário.
- `HistoryList`: padrão de listar, excluir e reabrir resultados sem nova coleta.
- `useSearchStore`: padrão para estado que sobrevive à troca de abas, cancelamento com `AbortController` e proteção contra respostas tardias.

### Established Patterns
- Operações longas usam `job_id`, feedback incremental e estado persistente fora do componente desmontável.
- Histórico é ordenado do mais recente para o mais antigo, limpo após 30 dias e excluível manualmente.
- Reabertura do histórico usa payload salvo e não repete scraping.
- Marcas inativas são excluídas pelo service-layer chokepoint, não por filtros duplicados em call sites.
- Playwright deve ser usado com concorrência controlada; o `BrowserManager` alerta contra muitos Chromiums simultâneos.

### Integration Points
- Nova rota/backend de jobs de banners para iniciar, acompanhar, parar, consultar e aprovar execuções.
- Novo serviço de banners promovendo a lógica do spike e separando coleta, armazenamento content-addressed e geração de relatórios.
- Registro da nova aba no `renderTab()`/navegação de `frontend/src/App.tsx`.
- Novo slice/store ou módulo equivalente para manter progresso, resultados, seleção e cancelamento ao trocar de aba.
- Contrato histórico de banners separado das buscas, pois imagens binárias devem ficar fora do JSON de metadados e ser referenciadas por SHA-256.

</code_context>

<specifics>
## Specific Ideas

- A seleção deve parecer e funcionar **igual à busca comparativa**.
- Exemplo de nome aprovado: `01-sale-inverno-aramis.webp`.
- A galeria deve ser a superfície de revisão: todos os banners começam marcados, o usuário remove falsos positivos e confirma os restantes.
- O conjunto empírico de referência em 2026-06-23 foi: 13/13 sites ativos, 37 imagens, 3 slides em vídeo e zero falhas de download.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 35:** usar uma conexão real com SharePoint e uma pasta/caminho temporário de teste enquanto o destino definitivo não for informado. A conexão, credenciais e publicação não fazem parte da Phase 34.

</deferred>

---

*Phase: 34-extração-de-banners-desktop*
*Context gathered: 2026-06-23*

