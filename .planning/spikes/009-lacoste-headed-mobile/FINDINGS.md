# Spike 009 — Conclusão autoritativa (corrige o REPORT.md automático)

> O `REPORT.md` gerado pelo `experiment.py` usou a URL de busca **errada**
> (`lacoste.com.br/search?q=`, que redireciona pra home) e por isso marcou
> `PARCIAL`. Esta é a conclusão correta, comprovada por `probe_search.py`.

## Veredito: `GO_TECHNICAL` (catálogo + preço acessíveis de graça, via IP limpo)

Reverte o `NO-GO` da Phase 36. As duas causas do NO-GO eram:
1. **IP corporativo da Aramis** marcado pelo Akamai → 403.
2. **URL de busca errada** (mesmo com 200, caía na home sem produtos).

## Evidência

Rodado do **4G do celular** (IP `187.90.218.121`, fora da Aramis), navegador
**headed** + **perfil persistente** (sessão quente). Anti-bot Akamai: **não bloqueou** (200).

| URL | Status | data-pid | product-tile | R$ |
|---|---:|---:|---:|---:|
| `https://www.lacoste.com/br/search?q=polo` ✅ | 200 | **32** | 817 | 97 |
| `https://www.lacoste.com/on/demandware.store/Sites-BRECOM-Site/pt_BR/Search-Show?q=polo` | 200 | 32 | 801 | 97 |
| `https://www.lacoste.com.br/search?q=polo` (a do 008/1ª tentativa) | 200 | 0 | 0 | 5 (→ home) |
| `https://www.lacoste.com/br/?q=polo` | 200 | 0 | 0 | 5 |

- HTML real salvo em `search_seo_canonical.html` (722 KB, 32 produtos).
- SKUs reais: `EJ2816-23-I1L`, `PF0614-23-C31`, `PH4014-23-031`, `PH4014-23-166`…
- Produtos vêm **server-side** no HTML (não é render assíncrono).

## Fatos técnicos para a integração

1. **Host canônico:** `www.lacoste.com/br/` — o `www.lacoste.com.br` faz redirect cego pra home e **perde o path**. O builder de URL precisa usar `lacoste.com/br/`, não `lacoste.com.br`.
2. **Endpoint de busca:** `https://www.lacoste.com/br/search?q=<termo>`. Site SFCC = `Sites-BRECOM-Site`, locale `pt_BR`, input `name="q"`.
3. **Estrutura:** grade SFCC padrão com `[data-pid]` + `.product-tile` + preços `R$`. O `parse_search_results`/`parse_pdp` atual precisa de ajuste para mirar `.product-tile [data-pid]` (hoje ele pega links de nav via heurística e gera URL malformada — bug do `//` protocol-relative em `parse_search_results`, linhas 478-479).

## Bloqueio que SOBRA: IP de produção (decisão de negócio)

A prova foi feita do **IP móvel**. O sistema em produção roda na **rede corporativa da Aramis**, que é justamente o IP que o Akamai bloqueia (403). Logo:

- Em produção, a raspagem da Lacoste precisa **sair por um IP limpo** (residencial/móvel).
- Não exige necessariamente gateway caro (ex.: BrightData). Como monitoramento de catálogo/preço é **baixa frequência**, opções baratas bastam: proxy residencial/móvel barato, ou um dispositivo dedicado num link residencial/4G.
- Sem egress limpo, a rota continua provada-mas-não-deployável na infra atual.

## Próximos passos sugeridos

1. **Decidir o egress de produção** (a real trava agora) — qual IP limpo a Lacoste usaria.
2. Ajustar o **SFCC URL builder** (host `lacoste.com/br/`) e o **parser** (extrair de `data-pid`/`product-tile`/preço; corrigir o bug de URL `//`).
3. Validar **D-06** (≥3 produtos reais + repetição) com a URL correta e o IP limpo.
4. Só então ativar `lacoste.is_active=true` em `brands.json`.

## Proibições respeitadas

- Headed + perfil persistente: **usados** (autorizados nesta tentativa grátis).
- **Não** usado: proxy/gateway pago, CAPTCHA solving, login, credenciais privadas, OCAPI/SCAPI, endpoint interno/mobile privado.
- Não alterou `backend/` nem `backend/data/brands.json`.
