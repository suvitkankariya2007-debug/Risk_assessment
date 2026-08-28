from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_layer.dual_routes import router

app = FastAPI(
    title="CyberRiskIQ Gateway",
    description="Cyber Risk Quantification & Synthesis Gateway",
    version="1.0.0",
)

# Permissive CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register router with /api/v1 prefix and also directly
app.include_router(router, prefix="/api/v1", tags=["chat"])
app.include_router(router, tags=["chat"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "CyberRiskIQ Gateway"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
