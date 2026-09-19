#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python generate_shards.py
docker build -t signup-validator:v1 .
minikube image load signup-validator:v1       # loads into all nodes of the profile
minikube image ls --format table | grep signup-validator
