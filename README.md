# AIOps Assignment 2: Infrastructure & Containerization

All four questions use one small app: a spam-detection REST API (TF-IDF + MultinomialNB, served with FastAPI). Q3 is a separate batch workload that validates signup CSV shards. Everything runs on CPU only.

API contract (Q1, Q2, Q4):
- `POST /predict` takes `{"text": "..."}` and returns `{"label": "spam" | "ham"}`
- `GET /healthz` returns 200 once the joblib model is loaded, and 503 before that

## Layout

```
submission/
├── AI_DISCLOSURE.md
├── question1/   naive vs multi-stage Dockerfile
├── question2/   API + Redis cache with Docker Compose
├── question3/   Kubernetes Indexed Job for parallel shard validation
└── question4/   Kubernetes Deployment: self-healing and rolling update
```

Each Kubernetes question writes its outputs to its own `evidence/` folder. Q3 and Q4 also have their own `README.md` with more detail.

## Prerequisites

- Docker with the Compose plugin
- minikube and kubectl (Q3 and Q4)
- Python 3.11+ with `pip install kubernetes` (for the Q3 result collector, see `question3/requirements-collect.txt`)

`model.joblib` is already included in `question1/` and `question2/`. It was trained on `spam_dataset.csv`, which comes from the assignment's seeded generator.

---

## Question 1: Single-stage vs multi-stage Docker

| File | Purpose |
|---|---|
| `app.py` | FastAPI app; loads `model.joblib` at startup |
| `Dockerfile.naive` | Single stage on `python:3.11` |
| `Dockerfile.multi` | Builder stage `python:3.11` installs deps into `/opt/venv`; runtime stage `python:3.11-slim` copies only the venv, app and model |

```bash
cd question1
docker build -f Dockerfile.naive -t spam-api:naive .
docker build -f Dockerfile.multi -t spam-api:multi .
docker images spam-api
docker run -d -p 8000:8000 spam-api:multi
curl localhost:8000/healthz
curl -X POST localhost:8000/predict -H 'Content-Type: application/json' \
     -d '{"text":"WIN a FREE iPhone now! Click here: bit.ly/xyz123"}'
```

**Result:** the naive image is 1.47 GB and the multi-stage image is 434 MB, **70.5% smaller**. Both return the same responses. The naive image still has the full Debian build toolchain (gcc etc.) and a 68 MB pip cache. The multi-stage image has neither.

## Question 2: Docker Compose + Redis cache

| File | Purpose |
|---|---|
| `app.py` | Checks Redis for the exact input text first. On a miss it predicts and stores the result with `SETEX` (TTL 300 s). On a hit it returns the cached label. The response includes `cached: true/false` |
| `docker-compose.yml` | `api` is built from `Dockerfile.multi`. `cache` is `redis:7-alpine`. The API reaches Redis at the hostname `cache` |
| `bench.sh` | Flushes Redis, sends 20 distinct requests (misses), then repeats the same 20 (hits) |
| `bench_output.txt`, `compose_logs.txt` | Evidence |

```bash
cd question2
docker compose up -d --build
bash bench.sh
docker compose down
```

**Result:** misses average 1.50 ms and hits average 0.93 ms over 20 requests each (`bench_output.txt`). The repeated request returns `{"label":"spam","cached":true}`.

## Question 3: Indexed Job for parallel data validation

8 seeded shards of 250 signup rows each, with 5–30 invalid rows per shard (bad email or missing required field). Each pod validates one shard, chosen by `JOB_COMPLETION_INDEX`.

```bash
minikube start --nodes 2 --cpus 2 --memory 2048
cd question3
pip install -r requirements-collect.txt
./00_build_and_load.sh   # generate shards, build image, load it into minikube
./01_run_job.sh          # apply the Job, snapshot pods -o wide every 3 s
./02_collect.sh          # read each pod's logs via the Kubernetes API
```

- Manifest: `completions: 8`, `parallelism: 4`, `completionMode: Indexed`, `restartPolicy: Never`, CPU request = limit = 500m. The Downward API injects `POD_NAME` and `NODE_NAME`.
- Evidence: 4 pods Running at once (`pods_timeline.txt`, `max_concurrency.txt`). Job 8/8 Complete in 68 s.
- Results: all 8 shard counts match the ground truth, **143 invalid rows** in total (`results_table.txt`).
- Results are read from pod logs through the API instead of a shared volume. minikube's hostPath provisioner is ReadWriteOnce and each volume lives on one node's disk, so it doesn't work across 2 nodes.
- Caveat: with the docker driver, minikube reports the host's 20 CPUs per node. The 2 × 2 CPU limit is set in the manifest (parallelism and requests), not enforced by the scheduler.

See `question3/README.md` for the full parallelism calculation.

## Question 4: Deployment self-healing and rolling update

```bash
kubectl delete job signup-validator --ignore-not-found
cd question4
./00_build_and_load.sh   # spam-api:v1 (Q1 image) and spam-api:v2 (app_v2/)
./01_deploy.sh           # apply Deployment + Service, smoke test
./02_self_heal.sh        # delete a pod and watch it get replaced
./03_rolling_update.sh   # v1 -> v2 under 5 req/s of traffic
```

- `deployment.yaml`: 2 replicas, CPU and memory requests and limits, readinessProbe on `/healthz`, RollingUpdate `maxSurge: 1, maxUnavailable: 0`, and a `preStop` sleep so old pods keep serving until they are removed from the endpoints.
- `service.yaml`: NodePort 30080 → 8000.
- `app_v2/`: the Q1 app, except that `/healthz` also returns `"version": "v2"`.
- Self-healing: the deleted pod is replaced by the ReplicaSet controller within a second (`self_heal.txt`).
- Rolling update: `rollout status` reports success, and `rollout history` shows 2 revisions. During the rollout **0 of 277 requests failed** (58 served by v1, then 219 by v2) (`traffic_summary.txt`).

## Clean up

```bash
kubectl delete deploy/spam-api svc/spam-api job/signup-validator --ignore-not-found
(cd question2 && docker compose down)
minikube stop
```

## AI disclosure

See `AI_DISCLOSURE.md`.
