# Question 3: Indexed Job for parallel signup-data validation

## Files
| File | Purpose |
|---|---|
| `generate_shards.py` | Seeded (`random.seed(42)`) generator: 8 shards × 250 rows, with 5–30 invalid rows per shard. Ground truth goes in `shards/expected_counts.json` |
| `validator/validate.py` | Runs in each pod. Reads `shard_<JOB_COMPLETION_INDEX>.csv` and prints a `RESULT {...}` JSON line |
| `Dockerfile` | `python:3.11-slim` with the stdlib validator and the shards baked in |
| `indexed-job.yaml` | `completions: 8`, `parallelism: 4`, `completionMode: Indexed`, `restartPolicy: Never`, CPU request = limit = 500m, Downward API `POD_NAME` + `NODE_NAME` |
| `collect_results.py` | Reads every pod's log through the Kubernetes API (python `kubernetes` client) and checks it against the ground truth |

## Run order
```bash
minikube start --nodes 2 --cpus 2 --memory 2048   # 2 nodes x 2 CPU = the assignment's cluster
pip install -r requirements-collect.txt
./00_build_and_load.sh     # shards + image + minikube image load
./01_run_job.sh            # applies the Job, snapshots `kubectl get pods -o wide` every 3 s
./02_collect.sh            # per-shard invalid counts via the API
```
All output is written to `evidence/`.

Expected invalid counts: shard 0-7 = 25, 15, 12, 8, 30, 23, 14, 16 (total 143).

## Notes for the write-up (check the numbers against `evidence/node_allocation.txt`)

**Parallelism = 4 with 500m per pod.**
- Nominal capacity is 4 CPU. kube-system pods already *request* CPU: on the control-plane node the apiserver (250m), controller-manager (200m), scheduler (100m), etcd (100m), coredns (100m) and kindnet (100m) total about 850m. The worker only has kindnet (about 100m).
- Schedulable CPU is therefore about 1.15 + 1.9 = 3.05 CPU, not 4.
- The validator is single-threaded Python, so one pod can never use more than 1 core. For a 250-row shard, 500m is plenty.
- Pods that fit at once = floor(1.15/0.5) + floor(1.9/0.5) = 2 + 3 = 5. Running all 8 at once would need 4 CPU, which is impossible.
- Makespan in waves = ceil(8/p): p=4..7 all give 2 waves. p=4 is the smallest value that reaches this minimum. It uses 2 of about 3 free CPU, leaving headroom for kube-system.
- With 1 CPU per pod, only floor(1.15/1) + floor(1.9/1) = 2 pods would fit, so 4 waves.
- Request = limit means each pod is guaranteed exactly its share and cannot steal CPU from the others.

**`WORK_SECONDS=30`.** Validation itself takes milliseconds, so the pod sleeps for 30 s. Without that, it would finish before `kubectl get pods` could show pods running concurrently. Say this openly in the write-up.

**Why logs through the API and not a shared volume.** minikube's default `standard` StorageClass uses the `storage-provisioner` addon, a *hostPath* provisioner. A PV is a directory on one node's filesystem (`/tmp/hostpath-provisioner/...`) and only supports ReadWriteOnce. With 2 nodes, pods scheduled on `minikube-m02` would not see what pods on `minikube` wrote. That gives no ReadWriteMany and silently loses results. Pod logs are kept by the kubelet on whichever node ran the pod, and the API server proxies them. So `read_namespaced_pod_log` works no matter where the pod ran, with no storage setup. This is also why the Job sets no `ttlSecondsAfterFinished`: the finished pods must survive until the logs have been collected.

**If the cluster had 3 × 2 CPU.** Schedulable CPU becomes about 1.15 + 1.9 + 1.9 = 4.95, and at 500m that fits 2 + 3 + 3 = 8 pods. 8 × 500m = 4 CPU fits, so `parallelism: 8` finishes all shards in 1 wave instead of 2, halving the makespan. Parallelism above 8 is pointless because completions = 8. The change is justified because the extra node adds about 1.9 schedulable CPU, which is exactly the 2 CPU the second wave needed.
