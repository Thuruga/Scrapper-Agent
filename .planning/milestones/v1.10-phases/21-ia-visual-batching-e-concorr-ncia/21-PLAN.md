# Phase 21: IA Visual - Batching e Concorrência - Plan

**Goal:** Acelerar drasticamente a inferência de imagem através do processamento em lote.

## Tasks

1. **[VIS-01] Download concorrente das imagens**
   - Arquivo: `services/cross_marketplace_service.py`
   - Ação: Ajustar o pipeline para fazer o download das imagens de todos os candidatos válidos (`top_candidates`) usando `asyncio.gather`.
   - Justificativa: Maximiza a eficiência de I/O em paralelo, garantindo que todas as imagens fiquem prontas rapidamente para a inferência em batch.

2. **[VIS-02] Processamento de embeddings em batch**
   - Arquivo: `services/image_ai_service.py`
   - Ação: Criar o método `get_embeddings_batch_async(self, images_bytes: List[bytes]) -> List[torch.Tensor]` no `ImageAIService`. O método vai empacotar todos os bytes de imagem válidos, processá-los numa única passagem no PyTorch `self.processor(...)` gerando um Tensor unificado, e retornar uma lista de embeddings.
   - Justificativa: Minimiza as sobrecargas (overheads) de execução do modelo por inferir múltiplos tensores de uma vez. Reduz drasticamente o tempo computacional em CPU/GPU.
   
3. **[VIS-03] Aplicação de Cegueira de Cor em Lote**
   - Arquivo: `services/image_ai_service.py`
   - Ação: No método de loteamento, garantir que a iteração de processamento das imagens (Pillow -> conversão pra grayscale -> RGB pseudo) se mantenha para cada imagem antes de compilar o batch final para o processador CLIP.

4. **[Integrar] Modificar cross_marketplace_service**
   - Arquivo: `services/cross_marketplace_service.py`
   - Ação: Enviar todas as imagens válidas via `get_embeddings_batch_async` e mapear os embeddings resultantes de volta aos produtos correspondentes para calcular os `image_match_score` com o `ref_embed`.

5. **Verificação Local**
   - Ação: Executar `python -m py_compile` nos arquivos editados para validar sintaxe.
