from fastapi import FastAPI
from src.router import api_router
from src.module_v3.router import api_router as v3_router
from src.demo_yield import demo_router


app = FastAPI(title="Unit of Work Demo", version="3.0.0")

# Include v1 (src/module) and v3 (src/module_v3) routers
app.include_router(api_router)
app.include_router(v3_router)
app.include_router(demo_router)


@app.get("/health")
def check_health():
    return {"success": True, "message": "Service working"}
