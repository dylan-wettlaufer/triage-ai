from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    print("GET / endpoint called")
    return {"message": "Hello from triageAI backend!"}
