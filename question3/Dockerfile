
FROM python:3.11-slim
WORKDIR /app
COPY validator/validate.py .
COPY shards/ /data/
ENV PYTHONUNBUFFERED=1
CMD ["python", "validate.py"]
