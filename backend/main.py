from fastapi import FastAPI
from routers import upload, health, triage
from config.settings import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Triage AI - Intelligent Medical Document Analysis & Visual Triage Assistant",
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(triage.router, prefix="/api/v1/triage", tags=["Triage"])

@app.get("/")
async def root():
    print("GET / endpoint called")
    return {"message": "Hello from triageAI backend!"}

