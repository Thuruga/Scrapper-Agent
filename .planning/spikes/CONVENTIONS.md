# Spike Conventions

Padrões e escolhas que se estabeleceram nas sessões de spike. Novos spikes seguem isto a menos
que a pergunta exija o contrário.

## Stack
- **Python puro**, rodado da raiz do projeto: `python .planning/spikes/NNN-nome/experiment.py`.
- **Reutilizar os serviços reais** em vez de reimplementar a lógica: `from services.nlp_service
  import nlp_service`, `from services import relevance_gates`, `from config import relevance_settings`.
  Garante que o spike mede o comportamento de produção, não uma aproximação.
- Sem dependências novas — o que o projeto já tem (rapidfuzz) basta para spikes de relevância.

## Structure
- Cada spike: `.planning/spikes/NNN-nome/` com `experiment.py` (código), `REPORT.md` (gerado pelo
  script, com tabelas), `README.md` (frontmatter + trilha de investigação + veredito).
- O `experiment.py` resolve a raiz via `os.path.join(os.path.dirname(__file__), "..","..","..")`,
  faz `sys.path.insert(0, ROOT)` e `os.chdir(ROOT)` (o vocab NLP é carregado por caminho relativo).

## Patterns
- **Medir sobre dados reais**: `data/search_history.json` (jobs `type=="cross"` têm o contrato
  completo com `search_query`, `target_sku` e itens com `text/image/final_match_score`).
- **Não confiar nos scores armazenados** — o histórico é anterior à penalidade de marca. Para
  medir comportamento atual, **recalcular ao vivo** com o `nlp_service`/`relevance_gates`.
- **Classificação por bucket de visual**: usar `image_match_score` como proxy, mas lembrar que
  visual alto = *parecença*, não *identidade* (look-alikes de concorrente pontuam alto).
- **Rotular ruído de concorrente** por presença de token de marca concorrente no título
  (lista `COMPETITOR_TOKENS`) — sinal mais confiável que o visual para identificar falso positivo.
- Saída dupla: resumo no stdout + `REPORT.md` em markdown (números/benchmark → CLI é adequado,
  não precisa de UI web).

## Tools & Libraries
- `rapidfuzz` (via `nlp_service`) — já no projeto.
- Nenhuma a evitar identificada até agora.
