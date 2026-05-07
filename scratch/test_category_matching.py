import asyncio
import json
from services.category_intelligence import category_intelligence

async def test_matching():
    print("Testing Category Matching...")
    brand = "aramis" # Assuming aramis is in the registry
    suggestions = await category_intelligence.discover_and_map(brand)
    
    print(f"\nSuggestions for {brand}:")
    for s in suggestions:
        print(f"VTEX: {s['vtex_name']} -> Canonical: {s['canonical_label']} (Confidence: {s['confidence']})")

if __name__ == "__main__":
    asyncio.run(test_matching())
