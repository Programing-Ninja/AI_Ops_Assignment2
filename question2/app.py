import os
from contextlib import asynccontextmanager

import joblib
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_PATH = os.getenv("MODEL_PATH", "model.joblib")
REDIS_HOST = os.getenv("REDIS_HOST", "cache")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

model = None
cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, cache
    model = joblib.load(MODEL_PATH)
    cache = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    yield


app = FastAPI(lifespan=lifespan)


class PredictRequest(BaseModel):
    text: str


@app.get("/healthz")
def healthz():
    if model is None:
        raise HTTPException(503, "model not loaded")
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    key = f"spam:{req.text}"
    hit = cache.get(key)
    if hit is not None:
        return {"label": hit, "cached": True}
    label = str(model.predict([req.text])[0])
    cache.setex(key, CACHE_TTL, label)
    return {"label": label, "cached": False}

