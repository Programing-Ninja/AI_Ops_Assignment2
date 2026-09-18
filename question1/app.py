'''Spam detection API'''

import os
from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_PATH = os.getenv("MODEL_PATH", "model.joblib")

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    model = joblib.load(MODEL_PATH)
    yield

app = FastAPI(lifespan=lifespan)

class PredictRequest(BaseModel):
    text: str
@app.get("/")

def root():
    return {"service": "spam-detector"}

@app.get("/healthz")
def healthz():
    if model is None:
        raise HTTPException(503, "model not loaded")
    return {"status": "ok"}

@app.post("/predict")
def predict(req: PredictRequest):
    return {"label": str(model.predict([req.text])[0])}