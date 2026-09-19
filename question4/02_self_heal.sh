#!/usr/bin/env bash
# Delete one pod and show that the ReplicaSet recreates it (new name, new AGE).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence
OUT=evidence/self_heal.txt

VICTIM=$(kubectl get pods -l app=spam-api -o jsonpath='{.items[0].metadata.name}')
{ echo "=== before ($(date +%T))"; kubectl get pods -l app=spam-api -o wide; } | tee "$OUT"
echo "=== kubectl delete pod $VICTIM ($(date +%T))" | tee -a "$OUT"
kubectl delete pod "$VICTIM" --wait=false | tee -a "$OUT"

for i in 1 2 3 4 5 6; do
  { echo "=== +${i}x2s ($(date +%T))"; kubectl get pods -l app=spam-api -o wide; } | tee -a "$OUT"
  sleep 2
done

{ echo "=== ReplicaSet (desired vs current vs ready)"; kubectl get rs -l app=spam-api -o wide
  echo "=== ReplicaSet events"; kubectl describe rs -l app=spam-api | sed -n '/Events:/,$p'
} | tee -a "$OUT"
