# Question 4: Deployment self-healing and rolling update

## Files
| File | Purpose |
|---|---|
| `deployment.yaml` | 2 replicas, CPU/memory requests and limits, readinessProbe on `/healthz`, RollingUpdate `maxSurge: 1, maxUnavailable: 0` |
| `service.yaml` | NodePort 30080 → container port 8000 |
| `app_v2/` | The Question 1 app with `APP_VERSION = "v2"` returned by `/healthz` (the only code change) |

Image tags: `spam-api:v1` is built from `submission/question1`, and `spam-api:v2` from `app_v2/`.

## Run order (same minikube cluster as Q3)
```bash
kubectl delete job signup-validator --ignore-not-found   # after Q3 results are collected
./00_build_and_load.sh     # build v1 + v2, minikube image load
./01_deploy.sh             # apply, rollout status, smoke test /healthz + /predict
./02_self_heal.sh          # delete a pod, snapshots show the replacement appear
./03_rolling_update.sh     # v1 -> v2 with 5 req/s of background traffic; rollout status + history
```
All output is written to `evidence/`. `traffic_summary.txt` should show `non-200: 0` and a switch from v1 to v2 responses.

## Notes for the write-up
- **Self-healing.** The **ReplicaSet controller** (inside kube-controller-manager), owned by the Deployment, does this. It watches pods matching its label selector and continuously reconciles: observed count (1 after the delete) ≠ desired `replicas: 2`, so it creates a new pod from the template. See `kubectl describe rs` → `SuccessfulCreate` event.
- **Rolling update.** The Deployment controller creates a new ReplicaSet for v2. It scales it up by 1 (maxSurge) and scales the old one down only after the new pod passes its readinessProbe (maxUnavailable 0). So 2 ready pods are always serving, and `kubectl rollout undo` stays available through the revision history.
- **As a Job instead.** A Job expects its pod to exit successfully. uvicorn never exits, so the Job would never "complete". If the pod crashed, the Job would retry only up to `backoffLimit` and then give up rather than keep 2 replicas alive. A Job's pod template is immutable, so there is no rolling update: moving to v2 would mean deleting and recreating the Job, which means downtime.
- **Deployment vs Job.** Serving is long-running with no natural end, so success means "N healthy replicas at all times": self-healing and zero-downtime updates are the right semantics. The Q3 validation is batch work with a defined end, so success means "each index exited 0 once". Restarting a finished pod would be wrong, and completions/parallelism/backoff are the right controls.
