# 🛒 VTEX Product Scraper

Ferramenta em Python para extrair dados de produtos de lojas baseadas na plataforma **VTEX**, utilizando a API pública de catálogo. A partir de uma lista de URLs de produtos, o scraper coleta informações como SKU, nome, GTIN, fabricante e preço, exportando tudo para um arquivo CSV.

---

## ✨ Funcionalidades

- Aceita URLs de páginas de produto comuns ou URLs já no formato de API VTEX
- Converte automaticamente URLs de vitrine para o endpoint da API de catálogo VTEX
- Extrai os seguintes dados de cada produto:
  - `sku` — ID do produto
  - `nome_produto` — Nome do produto
  - `gtin` — Código de barras (EAN)
  - `fabricante` — Marca/fabricante
  - `preco` — Preço de venda
- Exporta os resultados para `dadosProdutos.csv`
- Exibe barra de progresso durante a execução
- Trata erros por URL sem interromper o processo

---

## 📁 Estrutura do projeto

```
vtex-product-scraper/
├── scrapingVtex.py   # Script principal
├── urls.txt          # Lista de URLs de produtos (uma por linha)
└── dadosProdutos.csv # Arquivo gerado com os dados extraídos
```

---

## ⚙️ Pré-requisitos

- Python 3.7+
- pip

---

## 🚀 Instalação

1. Clone o repositório:

```bash
git clone https://github.com/kennedy-silva/vtex-product-scraper.git
cd vtex-product-scraper
```

2. Instale as dependências:

```bash
pip install requests tqdm
```

---

## 📝 Como usar

1. Adicione as URLs dos produtos no arquivo `urls.txt`, uma por linha:

```
https://www.loja.com.br/produto-exemplo/p
https://www.outra-loja.com.br/outro-produto/p
```

> As URLs podem ser tanto links de página de produto quanto endpoints da API VTEX — o script converte automaticamente.

2. Execute o script:

```bash
python scrapingVtex.py
```

3. Ao final, o arquivo `dadosProdutos.csv` será gerado na mesma pasta com os dados coletados.

---

## 📄 Exemplo de saída (`dadosProdutos.csv`)

| sku     | nome_produto         | gtin          | fabricante  | preco  |
|---------|----------------------|---------------|-------------|--------|
| 123456  | Camiseta Polo Branca | 7891234567890 | Marca XYZ   | 89.90  |
| 789012  | Tênis Running Pro    | 7899876543210 | Marca ABC   | 349.00 |

---

## 🔍 Como funciona a conversão de URL

O script detecta se a URL já aponta para a API VTEX. Caso contrário, transforma uma URL comum como:

```
https://www.loja.com.br/nome-do-produto/p
```

No endpoint da API de catálogo:

```
https://www.loja.com.br/api/catalog_system/pub/products/search/nome-do-produto/p
```

---

## ⚠️ Observações

- Este scraper funciona apenas com lojas hospedadas na plataforma **VTEX**.
- Respeite os termos de uso das lojas antes de realizar coletas em larga escala.
- Em caso de erro em uma URL, o script registra a falha no terminal e continua o processamento das demais.

---

## 📜 Licença

Este projeto está disponível sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.
