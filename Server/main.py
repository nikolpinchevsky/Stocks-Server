from fastapi import FastAPI
from src.routes import router

app = FastAPI(title="Stocks Course Project API")
app.include_router(router)
