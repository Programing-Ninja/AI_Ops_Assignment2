#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence

kubectl get nodes -o wide | tee evidence/nodes.txt
kubectl describe nodes | grep -E "^Name:|^Allocatable:|^  cpu|Allocated resources|cpu  " \
  | tee evidence/node_allocation.txt

kubectl delete job signup-validator --ignore-not-found
kubectl apply -f indexed-job.yaml

: > evidence/pods_timeline.txt
for _ in $(seq 60); do   # up to 3 min
  { echo "=== $(date +%T)"; kubectl get pods -o wide -l job-name=signup-validator; } \
    | tee -a evidence/pods_timeline.txt
  [ -n "$(kubectl get job signup-validator -o jsonpath='{.status.completionTime}')" ] && break
  sleep 3
done

awk '/^===/{if(n>max)max=n; n=0} / Running /{n++} END{if(n>max)max=n; print "max concurrent Running pods:", max}' \
  evidence/pods_timeline.txt | tee evidence/max_concurrency.txt

kubectl get job signup-validator -o wide | tee evidence/job.txt
kubectl get pods -o wide -l job-name=signup-validator | tee evidence/pods_final.txt
