import sys
sys.path.insert(0, '.')

try:
    from config import settings
    print("config OK")
    print("INTERNAL_API_KEY:", settings.INTERNAL_API_KEY)
    print("SUPABASE_URL:", settings.SUPABASE_URL)
    print("PLAYWRIGHT_ENABLED:", settings.PLAYWRIGHT_ENABLED)
except Exception as e:
    print("ERRO config:", e)

try:
    from api.auth import verify_api_key
    print("api.auth OK")
except Exception as e:
    print("ERRO api.auth:", e)

try:
    from api import api_router, public_router
    print("api routers OK")
except Exception as e:
    print("ERRO api:", e)

try:
    from services.brand_service import brand_service
    print("brand_service OK - marcas em memoria:", len(brand_service.brands))
except Exception as e:
    print("ERRO brand_service:", e)

try:
    from core.browser_manager import browser_manager
    print("browser_manager OK")
except Exception as e:
    print("ERRO browser_manager:", e)

print("--- Verificacao concluida ---")
