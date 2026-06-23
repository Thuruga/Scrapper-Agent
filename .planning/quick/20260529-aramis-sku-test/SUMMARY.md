---
status: complete
---

# Quick Task Summary: Aramis SKU Test

**Task:** Criar um código de teste para fazer a busca de um SKU no site da Aramis e trazer o produto que ele representa. Usaremos o SKU ML.05.0326046.

## What was done
1. Created `scratch/test_aramis_sku.py` to instantiate `VtexApiClient` configured for Aramis.
2. Implemented the query targeting SKU `ML.05.0326046`.
3. Tested successfully returning the correct product ("Camisa Manga Longa Regular Sarja Mista Chumbo").

## Result
The test script runs successfully and confirms that the backend's `VtexApiClient` handles SKU inputs appropriately, automatically mapping them to the specific product on the VTEX store.
