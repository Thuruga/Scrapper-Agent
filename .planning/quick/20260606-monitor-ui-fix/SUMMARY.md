---
status: complete
---

# UI do Monitoramento Melhorada

- Atualizado `App.tsx` para mapear corretamente `p.raw_title` e `p.price_full` dos produtos vindos da API (baseado no schema `RawProductBronze`).
- Adicionado destaque de promoção na UI (preço riscado, cor verde para o valor final e uma label de desconto %).
- O layout do grid foi ajustado com flexbox (`marginTop: 'auto'`) para o preço ficar sempre alinhado ao fundo do card, e o nome tem clamp de 2 linhas.
