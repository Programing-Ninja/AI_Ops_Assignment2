#!/usr/bin/env bash
# v1 = the unchanged Question 1 image; v2 = same app with a version string in /healthz.
set -euo pipefail
cd "$(dirname "$0")"
Q1=../question1

docker build -t spam-api:v1 -f "$Q1/Dockerfile.multi" "$Q1"
docker build -t spam-api:v2 -f app_v2/Dockerfile.multi app_v2
minikube image load spam-api:v1
minikube image load spam-api:v2
minikube image ls --format table | grep spam-api
