# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager # New import
from routers import upload, triage, health
from config.settings import settings
from db.database import init_db # Assuming init_db is synchronous

# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event: Initialize database tables
    print("Application startup: Initializing database...")
    await init_db() # Call your synchronous init_db() function
    print("Application startup: Database initialized.")

    # You could potentially load AI models here and store them on app.state
    # For example:
    # from models.document_analyzer import DocumentAnalyzer
    # app.state.document_analyzer = DocumentAnalyzer()
    # print("AI models loaded.")

    yield # This is where the application starts serving requests

    # Shutdown event: Clean up resources
    print("Application shutdown: Cleaning up resources...")
    # If you had global resources (like a shared AI model instance)
    # that needed explicit closing or releasing, you'd do it here.
    # For database connections managed by `get_db`, explicit closing isn't usually needed here.
    print("Application shutdown: Resources cleaned.")

# Initialize the FastAPI app with the lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="TriageAI - Intelligent Medical Document Analysis & Visual Triage Assistant",
    lifespan=lifespan # Pass the lifespan function here
)

# Include routers
#app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(triage.router, prefix="/api/v1/triage", tags=["Triage"])

# Optional: Root endpoint for basic check
@app.get("/")
async def root():
    return {"message": "Welcome to TriageAI Backend!", "version": settings.API_VERSION}