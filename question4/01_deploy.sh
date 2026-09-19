#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence

kubectl apply -f deployment.yaml -f service.yaml | tee evidence/apply.txt
kubectl rollout status deployment/spam-api --timeout=120s
kubectl get deploy/spam-api svc/spam-api -o wide | tee evidence/deployed.txt
kubectl get rs,pods -l app=spam-api -o wide | tee -a evidence/deployed.txt

URL=$(minikube service spam-api --url)
echo "Service URL: $URL" | tee evidence/smoke_test.txt
curl -s "$URL/healthz" | tee -a evidence/smoke_test.txt; echo | tee -a evidence/smoke_test.txt
curl -s -X POST "$URL/predict" -H 'Content-Type: application/json' \
     -d '{"text":"WIN a FREE iPhone now! Click here: bit.ly/xyz123"}' | tee -a evidence/smoke_test.txt
echo | tee -a evidence/smoke_test.txt
