#!/usr/bin/env bash
# Roll v1 -> v2 while a probe hits the Service every 0.2 s, to show no request fails.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence
URL=$(minikube service spam-api --url)

# Background traffic: timestamp, HTTP code, body of /healthz.
( end=$((SECONDS + 60))
  while [ $SECONDS -lt $end ]; do
    printf '%s %s\n' "$(date +%T.%N | cut -c1-12)" \
      "$(curl -s -m 2 -w ' HTTP%{http_code}' "$URL/healthz" || echo ' HTTP000')"
    sleep 0.2
  done ) > evidence/traffic_during_rollout.txt &
PROBE=$!
sleep 3

kubectl set image deployment/spam-api api=spam-api:v2
kubectl annotate deployment/spam-api --overwrite \
  kubernetes.io/change-cause="v2: /healthz now reports version string"
kubectl rollout status deployment/spam-api --timeout=180s | tee evidence/rollout_status.txt
kubectl rollout history deployment/spam-api | tee evidence/rollout_history.txt
kubectl rollout history deployment/spam-api --revision=2 | tee -a evidence/rollout_history.txt
kubectl get rs,pods -l app=spam-api -o wide | tee evidence/after_rollout.txt

wait $PROBE
T=evidence/traffic_during_rollout.txt
echo "--- traffic summary ---" | tee evidence/traffic_summary.txt
{ echo "requests:      $(wc -l < $T)"
  echo "non-200:       $(grep -vc 'HTTP200' $T || true)"
  echo "served by v1:  $(grep 'HTTP200' $T | grep -vc '"v2"' || true)"
  echo "served by v2:  $(grep -c '"v2"' $T || true)"
} | tee -a evidence/traffic_summary.txt
